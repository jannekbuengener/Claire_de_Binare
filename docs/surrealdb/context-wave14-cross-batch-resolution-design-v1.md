# Context Intelligence — DB-Aware Wave-14 Cross-Batch Reference Resolution Design v1

**Status**: Design (Wave-14 Follow-up)
**Authority**: Issue #2567 / Follow-up Arc of PR #2565
**Parent**: Epic #1976
**Depends On**:
- `docs/surrealdb/context-evidence-ref-semantics-v1.md` (#2568)
- `docs/surrealdb/context-claim-generator-policy-v1.md` (#2569)
- `docs/surrealdb/context-decision-event-generator-policy-v1.md` (#2570)
- `docs/surrealdb/context-agent-memory-import-policy-v1.md` (#2571)
**Guardrail**: No trading state, no secrets, no Live-Go, no Echtgeld-Go, no runtime change.

---

## 1. Purpose and Scope

PR #2565 introduced within-batch cross-reference validation for Wave-14 records with
intentionally warning-only severity. The rationale: the JSONL importer has no DB context.
A reference to an `evidence_id` that is absent from the current batch may still be valid
if the referenced record was created in a previous import batch.

This document designs the next step: a **DB-aware cross-batch reference resolution path**
that can, when explicitly enabled, escalate missing-reference warnings to blocking findings.

**Scope:**
- Problem statement and current-state description
- Design of the DB-aware adapter boundary
- Escalation policy (warning → blocking) with and without DB context
- Identification of the four candidate reference chains
- Non-goals and hard guardrails
- Minimal safe implementation slice for a future PR

**Non-Goals** (hard):
- No implementation in this PR (design only)
- No DB writes
- No schema apply
- No real import execution
- No network/remote DB access by default
- Apply remains hard-blocked
- LR remains NO-GO
- No Echtgeld scope
- No automatic Human-GO
- JSONL validation (`validate_jsonl()`) remains DB-independent

---

## 2. Current State

### 2.1 What PR #2565 Implemented

`context_importer.py` (post-PR #2565) performs within-batch cross-reference checks for:

| Referencing Record | Field | Target Table | Target ID Field |
|---|---|---|---|
| `claim` | `evidence_refs[*]` | `evidence_ref` | `evidence_id` |
| `decision_event` | `evidence_refs[*]` | `evidence_ref` | `evidence_id` |
| `decision_event` | `claim_refs[*]` | `claim` | `claim_id` |
| `agent_memory` | `evidence_refs[*]` | `evidence_ref` | `evidence_id` |

All four checks produce **warning-level findings** when a referenced ID is absent from the
current batch. They are never blocking, because the importer has no visibility into previously
imported records.

### 2.2 The Cross-Batch Gap

A referenced `evidence_id` can be absent from the current batch for two reasons:

1. **Valid cross-batch reference**: The record exists from a prior import. The current
   warning is a false positive and should be silenced.
2. **Invalid dangling reference**: The record does not exist anywhere. The current warning
   under-reports severity — this should eventually be blocking.

Without DB context, the importer cannot distinguish between these two cases.

---

## 3. Design: DB-Aware Adapter Boundary

### 3.1 Principle

DB-aware validation MUST be a **separate, opt-in phase** that runs after JSONL validation.
It MUST NOT be embedded into `validate_jsonl()`. The rationale:

- `validate_jsonl()` is a pure, stateless, in-memory function. It must remain so for
  testability, offline use, and CI safety.
- DB access is expensive, environment-dependent, and potentially unavailable (offline dev,
  CI without DB, dry-run scenarios).
- Mixing DB access into JSONL validation would break the NoopAdapter pattern used throughout
  Wave-14.

### 3.2 `DBContextAdapter` Interface

A future implementation MUST define a `DBContextAdapter` interface with the following
minimal contract:

```python
class DBContextAdapter(Protocol):
    def evidence_id_exists(self, evidence_id: str) -> bool: ...
    def claim_id_exists(self, claim_id: str) -> bool: ...
    def decision_id_exists(self, decision_id: str) -> bool: ...
```

Two implementations:
- **`NoopDBContextAdapter`** (default): always returns `True` (no DB access; all cross-batch
  warnings remain warnings). This is the safe default for offline and CI use.
- **`SurrealDBContextAdapter`** (future, explicit opt-in): performs read-only lookups against
  a running local SurrealDB instance. MUST be opt-in via CLI flag `--db-context`.

### 3.3 Activation Boundary

| Mode | DB Access | Cross-Batch Severity | Use Case |
|---|---|---|---|
| Default (no flag) | None | Warning | CI, offline, dry-run |
| `--db-context` (explicit) | Read-only local | Warning or Blocking (see Section 4) | Pre-import review with running local DB |
| Remote DB | Never | N/A | Remote DB access is **prohibited** by default |

---

## 4. Escalation Policy

When `--db-context` is active and a `SurrealDBContextAdapter` is available, the following
escalation rules apply:

| Reference Chain | Target Absent from Batch | Target Found in DB | Result |
|---|---|---|---|
| `claim.evidence_refs[*]` → `evidence_id` | ✅ | ✅ Found | Resolved — no finding |
| `claim.evidence_refs[*]` → `evidence_id` | ✅ | ❌ Not found | **Blocking** — dangling reference |
| `decision_event.evidence_refs[*]` → `evidence_id` | ✅ | ✅ Found | Resolved — no finding |
| `decision_event.evidence_refs[*]` → `evidence_id` | ✅ | ❌ Not found | **Blocking** — dangling reference |
| `decision_event.claim_refs[*]` → `claim_id` | ✅ | ✅ Found | Resolved — no finding |
| `decision_event.claim_refs[*]` → `claim_id` | ✅ | ❌ Not found | **Blocking** — dangling reference |
| `agent_memory.evidence_refs[*]` → `evidence_id` | ✅ | ✅ Found | Resolved — no finding |
| `agent_memory.evidence_refs[*]` → `evidence_id` | ✅ | ❌ Not found | **Blocking** — dangling reference |
| `evidence_ref.validates[*]` → `claim_id` or `decision_id` | ✅ | ✅ Found | Resolved — no finding |
| `evidence_ref.validates[*]` → `claim_id` or `decision_id` | ✅ | ❌ Not found | **Blocking** |
| `evidence_ref.invalidates[*]` → target | ✅ | ❌ Not found | **Blocking** |
| `evidence_ref.related_decisions[*]` → `decision_id` | ✅ | ❌ Not found | **Blocking** |
| DB unavailable / connection failure | Any | N/A | **Fail-safe**: degrade to warning; do NOT block |

**Fail-safe rule**: If the DB context adapter fails or is unavailable mid-run, the phase
MUST degrade gracefully to warning-only mode. It MUST NOT treat a DB failure as a blocking
condition. DB unavailability means "we cannot confirm existence" — not "the record does
not exist."

---

## 5. Relationship to Semantic Definitions (#2568–#2571)

This design depends on the four semantic documents produced in this PR:

| Document | Provides |
|---|---|
| `context-evidence-ref-semantics-v1.md` | Defines `validates`/`invalidates`/`related_decisions` target domains and severity policy |
| `context-claim-generator-policy-v1.md` | Defines valid `claim_id` domains and mandatory fields |
| `context-decision-event-generator-policy-v1.md` | Defines valid `decision_id` domains and `human_go` semantics |
| `context-agent-memory-import-policy-v1.md` | Defines `agent_memory.evidence_refs` validation gates |

The DB-aware escalation policy in Section 4 is only coherent once these four policies are
defined, because it escalates warnings from the cross-reference chains they govern.

---

## 6. Minimal Safe Implementation Slice (Future PR)

When implementing this design, the minimal safe slice is:

1. Define `DBContextAdapter` Protocol in `tools/surrealdb/context_importer.py` (or a
   new `tools/surrealdb/db_context_adapter.py` module).
2. Implement `NoopDBContextAdapter` (default, always-true lookups).
3. Add `validate_wave14_refs_with_db_context()` function — separate from `validate_jsonl()`.
4. Add `--db-context` CLI flag to the importer.
5. Wire `NoopDBContextAdapter` as default; `SurrealDBContextAdapter` only when
   `--db-context` is explicitly set.
6. Tests MUST cover:
   - Default mode (NoopAdapter): warnings unchanged
   - DB-context mode with found targets: warnings resolved
   - DB-context mode with not-found targets: escalated to blocking
   - DB unavailability: degrades to warnings (fail-safe)

**Scope boundaries for the implementation slice:**
- No changes to `validate_jsonl()` signature or behaviour
- No network access in default mode
- No schema changes
- No `SurrealDBContextAdapter` implementation required in the first slice (NoopAdapter only)
- Apply remains hard-blocked
- LR remains NO-GO

---

## 7. Guardrail Review (G1–G10)

| # | Guardrail | Result |
|---|---|---|
| G1 | No trading state | ✅ No orders/positions/fills/balances |
| G2 | No secrets | ✅ No credentials or keys |
| G3 | No Live-Go | ✅ LR remains NO-GO; DB-context does not grant LR |
| G4 | No Echtgeld-Go | ✅ DB resolution does not grant Echtgeld approval |
| G5 | No runtime change | ✅ No service or compose change |
| G6 | No autonomy without Human Gate | ✅ `--db-context` is explicit opt-in; default is safe |
| G7 | No Board-Stage to LR-Go mapping | ✅ Not mentioned as Live-Go |
| G8 | No productive apply | ✅ No SurrealDB apply commands; `SurrealDBContextAdapter` is read-only |
| G9 | Git/Repo is SSoT | ✅ Issues and schema cited as authority |
| G10 | Hash-backed evidence | ✅ Design requires evidence_refs on all Wave-14 records |

---

## 8. Provenance

| Source | Type | Status |
|---|---|---|
| Issue #2567 | Authority | OPEN (closed by this document) |
| PR #2565 | Context | MERGED |
| PR #2573 | Context | MERGED |
| `tools/surrealdb/context_importer.py` | Reference implementation | PRESENT |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema | PRESENT |
| `docs/surrealdb/context-evidence-ref-semantics-v1.md` | Dependency | This PR |
| `docs/surrealdb/context-claim-generator-policy-v1.md` | Dependency | This PR |
| `docs/surrealdb/context-decision-event-generator-policy-v1.md` | Dependency | This PR |
| `docs/surrealdb/context-agent-memory-import-policy-v1.md` | Dependency | This PR |
| `docs/surrealdb/context-wave14-completion-gates.md` | Wave-14 context | PRESENT |
| Epic #1976 | Parent | OPEN |
