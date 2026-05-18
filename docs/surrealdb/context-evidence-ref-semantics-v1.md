# Context Intelligence — `evidence_ref` Semantic Fields v1

**Status**: Design (Wave-14 Follow-up)
**Authority**: Issue #2568 / Follow-up Arc of PR #2565
**Parent**: Epic #1976
**Schema Reference**: `infrastructure/surrealdb/context_intelligence_v0.surql` (`evidence_ref` table)
**Guardrail**: No trading state, no secrets, no Live-Go, no Echtgeld-Go, no runtime change.

---

## 1. Purpose and Scope

This document defines the semantics for three intentionally-blank fields on the `evidence_ref`
schema:

- `evidence_ref.validates`
- `evidence_ref.invalidates`
- `evidence_ref.related_decisions`

The Wave-14 file-level evidence generator (`context_indexer.py`) deliberately does not populate
these fields because the semantics were undefined at implementation time (PR #2565).

This document closes that gap by specifying target ID domains, allowed producers, validation
behaviour, and what must remain out of scope.

**Scope:**
- Define ID domains for `validates`, `invalidates`, `related_decisions`
- Define allowed producers
- Define validation severity for missing targets
- Define authoring constraints

**Non-Goals:**
- No implementation of a new evidence generator
- No schema changes
- No JSONL import changes
- No auto-population of these fields by the repo indexer
- No DB writes
- No Live-Readiness assertion
- No Echtgeld-Go
- No `trade-capable` → Live-Go mapping

---

## 2. Field Semantics

### 2.1 `validates` — Positive Assertion Array

**Type**: `array` of ID strings
**Semantics**: The evidence record positively supports the referenced target. The target either
becomes more credible or would be invalidated if this evidence were absent.

**Allowed target ID domains:**
- `claim_id` (from the `claim` table) — the evidence supports the truth of the claim
- `decision_id` (from the `decision_event` table) — the evidence justifies the decision

**Excluded domains:**
- `artifact_id` — artefact association uses `related_artifacts`, not `validates`
- Any LR-state identifier — evidence cannot validate a Live-Readiness verdict
- Any Echtgeld/trading approval identifier

**Example valid entry:**
```json
{ "evidence_id": "ev-wave14-001", "validates": ["claim-risk-001", "dec-risk-001"] }
```

### 2.2 `invalidates` — Counter-Evidence Array

**Type**: `array` of ID strings
**Semantics**: The evidence record contradicts or undermines the referenced target. A `invalidates`
entry does not automatically change the status of the referenced claim or decision — it signals
that human review is required.

**Allowed target ID domains:** Same as `validates` (`claim_id`, `decision_id`).

**Constraint**: Setting `invalidates` for a target does not supersede the target record.
The referenced claim or decision remains valid until explicitly updated by its author.

**Excluded domains:** Same as `validates`.

### 2.3 `related_decisions` — Non-Directional Association Array

**Type**: `array` of `decision_id` strings
**Semantics**: The evidence is contextually relevant to the referenced decisions without
asserting validation or invalidation. Use when evidence informs but does not strictly support
or contradict a decision.

**Allowed target ID domains:** `decision_id` only.

**Distinction from `validates`/`invalidates`:** `related_decisions` carries no assertion
about direction or strength. It is a soft association for navigation and audit purposes.

---

## 3. Allowed Producers

| Producer | Conditions | Result |
|---|---|---|
| Human author | Explicit manual authoring of JSONL | All three fields may be set |
| Agent (with Human-GO) | Agent drafts entry, human reviews and signs off | All three fields may be set |
| Automated repo indexer | File scan, test detection, source-hash indexing | Fields MUST remain empty — no automated inference |

**Key constraint:** The automated file-level evidence generator MUST NOT populate
`validates`, `invalidates`, or `related_decisions`. Test existence alone does not constitute
a validation assertion. Commit existence does not constitute a decision linkage.

---

## 4. Validation Behaviour

### 4.1 Within-Batch Validation (current — PR #2565)

The JSONL importer currently performs within-batch cross-reference checks for Wave-14 records
(warning-only). This covers `claim.evidence_refs`, `decision_event.evidence_refs`, and
`agent_memory.evidence_refs`.

For `evidence_ref.validates`, `evidence_ref.invalidates`, and `evidence_ref.related_decisions`,
the importer does NOT yet check whether the referenced IDs exist in the batch or in the DB.

### 4.2 Recommended Validation Policy

| Condition | Severity | Rationale |
|---|---|---|
| Target ID in `validates` missing from current batch | Warning | Target may exist from prior import |
| Target ID in `invalidates` missing from current batch | Warning | Same cross-batch rule |
| Target ID in `related_decisions` missing from current batch | Warning | Non-blocking association |
| Target ID not found in DB (with DB context) | Blocking | Dangling reference is invalid at import time |
| Field populated by automated indexer | Blocking | Violates producer policy |
| `validates` references an `artifact_id` | Warning | Wrong domain; should use `related_artifacts` |
| `validates`/`invalidates` references an LR-state identifier | Blocking | LR assertions are not permitted as evidence targets |

### 4.3 DB-Aware Escalation

When a DB-aware validation pass is available (see
`context-wave14-cross-batch-resolution-design-v1.md`), missing-target warnings for
`validates`, `invalidates`, and `related_decisions` SHOULD escalate to blocking findings
if the referenced ID is not found in the DB. Until that path exists, warnings remain
the maximum severity for cross-batch reference gaps.

---

## 5. Guardrail Review (G1–G10)

| # | Guardrail | Result |
|---|---|---|
| G1 | No trading state | ✅ No orders/positions/fills/balances |
| G2 | No secrets | ✅ No credentials or keys |
| G3 | No Live-Go | ✅ LR remains NO-GO; no assertion otherwise |
| G4 | No Echtgeld-Go | ✅ No trading approval derived |
| G5 | No runtime change | ✅ No service or compose change |
| G6 | No autonomy without Human Gate | ✅ Automated producer explicitly forbidden |
| G7 | No Board-Stage to LR-Go mapping | ✅ `trade-capable` not mentioned as Live-Go |
| G8 | No productive apply | ✅ No SurrealDB apply commands |
| G9 | Git/Repo is SSoT | ✅ Schema and issues cited as authority |
| G10 | Hash-backed evidence | ✅ Producers must include source_refs with hashes |

---

## 6. Provenance

| Source | Type | Status |
|---|---|---|
| Issue #2568 | Authority | OPEN (closed by this document) |
| PR #2565 | Context | MERGED |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema | PRESENT |
| `docs/surrealdb/context-wave14-completion-gates.md` | Wave-14 context | PRESENT |
| `docs/surrealdb/context-evidence-claim-memory-runbook.md` | Retrieval runbook | PRESENT |
| Epic #1976 | Parent | OPEN |
