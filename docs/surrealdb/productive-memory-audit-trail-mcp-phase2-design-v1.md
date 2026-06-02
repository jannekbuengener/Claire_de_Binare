# Productive Memory Audit Trail — MCP Phase 2 Design v1 (#2739)

**Issue:** [#2739](https://github.com/jannekbuengener/Claire_de_Binare/issues/2739)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (CLOSED 2026-05-31; design doc historical)  
**Builds on:** G0 [#2730](https://github.com/jannekbuengener/Claire_de_Binare/issues/2730) — [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md); G1 [#2735](https://github.com/jannekbuengener/Claire_de_Binare/issues/2735) — [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md)  
**Status:** **DESIGN ONLY — G2 MCP PHASE 2 — NOT ACTIVATED**  
**LR:** NO-GO ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md))  
**Board stage:** `trade-capable` is orthogonal; not live authorization.

---

## 1. Purpose and non-goals

This document defines the **MCP Phase 2 surface contract** for wiring
Human-GO-gated memory write intent to the **T3 productive audit trail**
(governed non-local endpoint from G1). It is the G2 deliverable in the
activation ladder (§9 of the G0 contract).

**In scope (G2 design only):**

- MCP tool surface and `operation_mode` capability resolution (spec level)
- Permission model extensions (registry / PermissionGuard — design only)
- Request, response, and error/refusal contracts
- Fail-closed matrix for productive audit modes via MCP
- Audit trail record semantics when MCP initiates a future T3 persist
- Evidence prerequisites before G3 runtime implementation
- Operator UX and readiness hooks

**Out of scope (explicit):**

- Handler, registry, or PermissionGuard **code** changes
- MCP mutation execution; `MUTATION_ALLOWED` remains `False` on `main`
- SQL against governed endpoint; productive adapter (G3)
- Flipping `PERSIST_ALLOWED` (G3, separate issue)
- Productive `agent_memory` write (T4 / G4)
- Closing parent epic #2606
- LR upgrade, Echtgeld-go, BLUE/RED runtime changes

**Rule:** G2 authorizes **documentation only**. Phase 2 productive audit
persist via MCP remains **NOT ACTIVATED** until G3 implementation with HG-P
and activation evidence.

---

## 2. Relationship to G0 and G1

| Layer | Canon | G2 uses |
| --- | --- | --- |
| G0 | [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md) | T0–T4 ladder, HG tiers, fail-closed matrix, activation gates |
| G1 | [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) | Governed endpoint, TLS, `cdb`/`audit_trail`, T2→T3 field mapping |
| Phase 1 MCP | [`mcp-memory-write-surface-v1.md`](mcp-memory-write-surface-v1.md) | `cdb_context_memory_write_intent`, dry-run default, mutation flags blocked |
| Bridge | [`context-mcp-bridge-contract.md`](context-mcp-bridge-contract.md) | Read-only default, three-layer PermissionGuard |
| Gate | [`memory-write-gate-v1.md`](memory-write-gate-v1.md) | `evaluate_memory_write_gate()` envelope |

G2 does **not** reopen G0 semantics or G1 endpoint topology. It specifies
how MCP exposes (and refuses) future T3 audit wiring.

---

## 3. MCP tool surface (design default)

### 3.1 Single-tool extension (recommended)

| Field | Design value |
| --- | --- |
| Tool ID | `cdb_context_memory_write_intent` (unchanged from Phase 1) |
| Registry `read_only` | **`True` on `main` through G2**; flip only in G3 issue with maintainer GO |
| Module constant | `MUTATION_ALLOWED = False` (unchanged) |
| Handler anchor | [`memory_write_intent_tools.py`](../../tools/mcp/memory_write_intent_tools.py) |

**Rejected alternative:** Separate tool `cdb_context_memory_audit_trail_intent` —
adds registry surface area and duplicate gate logic; defer unless G3 proves
single-tool mode resolution insufficient.

### 3.2 Phase 1 vs Phase 2 (design)

| Phase | Behavior on `main` | SQL | T3 productive audit |
| --- | --- | --- | --- |
| Phase 1 (active) | `operation_mode` omitted → dry-run gate only | No | No |
| Phase 2 (G2 spec) | Modes defined; non-dry-run **refused** until G3 | No on `main` | Not activated |

Phase 1 continues to block legacy mutation flags (`mutation_requested`,
`execute_write`, `persist`, `audit_persist_local`, etc.) with
`mutation_blocked_by_default`. G2 adds **spec-level** `operation_mode` as the
canonical capability selector (future G3).

---

## 4. Capability resolution (`operation_mode`)

### 4.1 Mode ladder

| `operation_mode` | Tier | Human-GO | SQL | Status on `main` |
| --- | --- | --- | --- | --- |
| `dry_run` (default) | T0/T1 | HG-L or HG-P (gate eval only) | No | **Active** (Phase 1) |
| `audit_persist_local` | T2 | HG-L | Yes (`127.0.0.1:8010`, audit only) | **Blocked via MCP** until separate local-MCP GO issue |
| `audit_persist_productive` | T3 | **HG-P** | Yes (governed endpoint, audit only) | **NOT ACTIVATED** (G3) |
| `agent_memory_write` | T4 | HG-W | Yes (governed endpoint) | **NOT ACTIVATED** (G4) |

Omitted or empty `operation_mode` → **`dry_run`** (backward compatible with Phase 1).

Invalid values → **`operation_mode_invalid`** (fail-closed; no SQL).

### 4.2 Resolution flow (design)

```text
MCP request
  → PermissionGuard (read_only registry + input gate)
  → parse operation_mode (default dry_run)
  → if not dry_run: refuse on main (G2/G3 boundary)
  → evaluate_memory_write_gate()  [always for dry_run path]
  → if G3+ and audit_persist_productive + HG-P + env gates:
        memory_write_path_productive → governed endpoint → audit_observation only
```

On `main` after G2 merge, flow **stops** after gate evaluation for all modes
except implicit `dry_run` success path.

---

## 5. Read-only vs write-zone separation

| Zone | MCP role in G2 design |
| --- | --- |
| Read zone | Default: all MCP context tools + write **intent** evaluation |
| Write zone | Future: governed SQL persist **outside** agent autonomous scope |

Principles:

1. **Parent-agent enforcement:** Agents must not pass raw SQL/SurrealQL via MCP
   parameters to bypass gate (`query`, `sql`, `surql`, `statement` remain
   forbidden injection fields per Phase 1).
2. **No silent write:** Productive persist requires explicit `operation_mode`,
   HG-P token, env opt-in (G3), and maintainer GO — not implied by gate pass.
3. **Registry truth:** [`context-mcp-bridge-contract.md`](context-mcp-bridge-contract.md)
   — write-capable registration is a **G3 code change**, not G2.
4. **GitHub / repo writes:** MCP remains gatekeeper; no repo mutation via this tool.

---

## 6. Permission model (spec level)

Align with [`permission_guard.py`](../../tools/mcp/permission_guard.py) three-layer defense:

| Layer | Phase 1 (main) | G2 design (future G3) |
| --- | --- | --- |
| Registry Gate | `read_only=True` blocks non-read-only tools | Productive audit execution requires **new** registration decision + GO |
| Execute Gate | `read_only` + input scan before dispatch | Unchanged default; execute path for T3 only after registry GO |
| Input Gate | Mutation flags + SQL injection fields blocked | Add `operation_mode` allowlist validation at handler |

**Exemption (unchanged):** `cdb_context_memory_write_intent` remains exempt from
blanket keyword scan on memory record body; handler enforces mutation flags and
injection fields.

**G3 registry change (not G2):** If a dedicated execute-capable variant is ever
required, it must be a **separate tool ID** with explicit audit trail in issue +
PR + readiness pack — not a silent `read_only=False` on the existing tool.

---

## 7. Jannek-GO, LOCK, and Brain Evidence gates

| Gate | G2 design rule |
| --- | --- |
| Human-GO | HG-P required for future `audit_persist_productive`; HG-L **insufficient** for T3 |
| Jannek-GO / maintainer GO | Required for G3 implementation PR; G2 doc does not substitute |
| Single-Writer LOCK | `LOCK: agent=… issue=#2739 mode=single-writer` on G2 PR; repeat on G3 |
| Brain Evidence | Session log + evidence pack before G3 operator proof |
| Invalid GO sources | Unchanged from G0 §6 (`DELIVERY_APPROVED.yaml`, `context.readiness`, etc.) |

---

## 8. Module constants (unchanged on `main`)

| Constant | Location | G2 rule |
| --- | --- | --- |
| `MUTATION_ALLOWED` | `memory_write_intent_tools.py` | **`False`** — G2 does not flip |
| `PERSIST_ALLOWED` | `memory_write_gate.py` | **`False`** — G3 separate issue |

Gate pass continues to mean **`approved_dry_run`** only from the gate module
perspective.

---

## 9. Request schema (spec level)

JSON parameters for `cdb_context_memory_write_intent` (illustrative):

```json
{
  "memory_record": {
    "memory_id": "uuid-or-stable-id",
    "scope": "issue:2606",
    "namespace": "cdb",
    "content": "…",
    "authorization": {
      "human_go_token": "GO-2026-05-30-g2-design"
    }
  },
  "operation_mode": "dry_run",
  "target_issue": "2606",
  "git_commit_sha": "f23240cc60ee6ba8e7bd732706051dc25b1d8d21",
  "run_id": "optional-ci-or-operator-run-id"
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `memory_record` | Yes | Same contract as Phase 1 / gate v1 |
| `memory_record.authorization.human_go_token` | Yes for pass path | Never echoed raw in response |
| `operation_mode` | No (default `dry_run`) | See §4 |
| `target_issue` | Recommended | Metadata for future T3 row |
| `git_commit_sha` | Recommended | Full SHA |
| `run_id` | Optional | Correlation |

**Forbidden parameter keys (fail-closed):** `query`, `sql`, `surql`, `statement`,
plus Phase 1 mutation flags unless explicitly redesigned in G3.

---

## 10. Response schema (spec level)

Success path (dry-run on `main`):

```json
{
  "status": "ok",
  "gate_status": "approved_dry_run",
  "operation_mode_resolved": "dry_run",
  "productive_audit_status": "not_activated",
  "mcp_phase": "1",
  "memory_id": "…",
  "limitations": ["no_persistence", "no_mcp_mutation", "t3_productive_audit_not_activated"],
  "metadata": {
    "source": "in_memory",
    "read_only": true,
    "tool": "cdb_context_memory_write_intent"
  }
}
```

Refusal path (non-dry-run on `main` after G2 spec):

```json
{
  "status": "refused",
  "code": "productive_audit_not_activated",
  "operation_mode_resolved": "audit_persist_productive",
  "gate_status": "blocked_productive_audit_not_implemented",
  "productive_audit_status": "not_activated",
  "message": "MCP Phase 2 productive audit persist is design-only; G3 implementation required."
}
```

**Redaction:** Responses must never contain raw `human_go_token` values (Phase 1
rule preserved). Use `human_go_token_present: true` in nested audit materialization only.

---

## 11. Error and refusal contract

| Code | When | HTTP-style severity |
| --- | --- | --- |
| `mutation_blocked_by_default` | Legacy mutation flags set | Refusal |
| `productive_audit_not_activated` | `audit_persist_productive` on `main` | Refusal |
| `hg_p_required` | T3 mode without HG-P tier token | Refusal |
| `operation_mode_invalid` | Unknown mode | Refusal |
| `unsafe_input` | Injection fields / embedded SQL keywords in params | Refusal |
| `gate_blocked` | `evaluate_memory_write_gate()` blocked | Refusal |
| `local_audit_mcp_not_activated` | `audit_persist_local` via MCP (until separate GO) | Refusal |

No fallback: refused productive mode must **not** downgrade to T2 localhost SQL via MCP.

---

## 12. Fail-closed matrix (MCP-specific)

| Condition | MCP behavior on `main` |
| --- | --- |
| Default call (no mode) | Dry-run gate only |
| `audit_persist_productive` | **Refuse** — G3 required |
| `audit_persist_local` | **Refuse** — not MCP-authorized in G2 design |
| `agent_memory_write` | **Refuse** — T4 / G4 |
| HG-L token + T3 mode | **Refuse** — `hg_p_required` |
| Missing Human-GO | Gate block; no SQL |
| `MUTATION_ALLOWED=False` | All execute paths blocked |
| MCP mutation flags | `mutation_blocked_by_default` |

---

## 13. Audit trail record semantics

When G3 implements productive persist, MCP-initiated T3 rows must match G0/G1:

| Aspect | Rule |
| --- | --- |
| Table | `audit_observation` only |
| `observation_type` | `memory_write_gate_evaluation` |
| `observed_by` | e.g. `cdb_context_memory_write_intent/v2` or `memory_write_path_productive/v1` |
| Materializer | [`audit_observation_from_gate.py`](../../tools/surrealdb/audit_observation_from_gate.py) + G3 metadata extensions |
| Endpoint | Governed non-localhost per G1 |
| `agent_memory` | **Never** written in T3 MCP path |

MCP is an **audit signal initiator**, not an authorization source
([`audit-observation-model-v1.md`](audit-observation-model-v1.md) §1).

---

## 14. Idempotency, replay, and determinism

| Topic | Design assumption |
| --- | --- |
| Idempotency key | `observation_id` from gate envelope (stable hash) |
| Replay | Same inputs + same gate version → same observation_id (G3 tests) |
| Determinism | Canonical JSON for audit bundles per [`core/replay/canonical_json.py`](../../core/replay/canonical_json.py) (G3 evidence) |
| Duplicate MCP calls | G3 must document UPSERT vs reject policy on governed endpoint |

G2 does not implement idempotency; it requires G3 proof.

---

## 15. Secrets and credential boundaries

- Human-GO token: request only; never in logs/responses
- Governed endpoint URL: `SURREALDB_AUDIT_TRAIL_ENV` per G1 — not in MCP params
- MCP server must not read productive writer credentials in G2/G3 design without
  explicit env/secrets path documented in G1 §6

---

## 16. Operator UX

Add to readiness evidence pack ([`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md)):

- [ ] Phase 1 dry-run MCP test command documented
- [ ] Proof that `audit_persist_productive` returns `productive_audit_not_activated` on `main` (G3 test)
- [ ] HG-P tier recorded for any future T3 MCP proof
- [ ] Registry diff reviewed if G3 changes `read_only`

Operator preflight: read G2 doc before any G3 MCP registry discussion.

---

## 17. Required evidence before G3 runtime activation

Not satisfied by G2. G3 issue must prove:

- [ ] G0 + G1 + G2 design docs merged on `main`
- [ ] Handler implements `operation_mode` resolution per this spec
- [ ] PermissionGuard / registry change with maintainer GO (if needed)
- [ ] Productive adapter wired per G1; localhost rejected on T3 path
- [ ] HG-P maintainer GO + env opt-in flag
- [ ] Unit tests: refusal codes on `main`; integration on governed endpoint (operator)
- [ ] No raw token in MCP responses or persisted rows
- [ ] `agent_memory_written: false` on all T3 MCP proofs
- [ ] Rollback doc exercised
- [ ] LR remains NO-GO unless changed via LR SSOT only
- [ ] #2606 re-audit; criterion 6 re-evaluated with runtime evidence

Optional `PERSIST_ALLOWED` flip remains **G3 code issue** — not implied by G2 or MCP design alone.

---

## 18. G3 and G4 follow-up slices

| Gate | Issue | Scope |
| --- | --- | --- |
| **G2** | **#2739 (this doc)** | MCP Phase 2 design — **NOT ACTIVATED** |
| G3 | Future | Handler + adapter + tests + HG-P proof; optional `PERSIST_ALLOWED` flip |
| G4 | Future | Productive `agent_memory` write (HG-W) |

---

## 19. Why #2606 remains NOT_CLOSURE_READY

G2 specifies MCP wiring only. Parent [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)
criterion 6 stays **PARTIAL** until:

- T3 runtime persist exists with operator evidence, and
- MCP surface matches implemented behavior (post-G3)

G2 merge does **not** close #2606.

---

## 20. LR / live / Echtgeld boundaries

| SSOT | Rule |
| --- | --- |
| LR audit status | **NO-GO** — unchanged by G2 |
| Board stage | Not live authorization |
| MCP Phase 2 design | Does not imply LR-GO, Echtgeld, or strategy release |

---

## Cross-references

| Document | Role |
| --- | --- |
| [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md) | G0 contract |
| [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) | G1 endpoint |
| [`mcp-memory-write-surface-v1.md`](mcp-memory-write-surface-v1.md) | Phase 1 MCP surface |
| [`context-mcp-bridge-contract.md`](context-mcp-bridge-contract.md) | Bridge + PermissionGuard |
| [`memory-reality-slice1-audit.md`](memory-reality-slice1-audit.md) | §22.3 G2 addendum |
| [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md) | Proof matrix row 3 |

---

## Provenance

| Source | Role |
| --- | --- |
| GitHub #2739 | G2 design delivery issue |
| GitHub #2735 / PR #2738 | G1 endpoint design |
| GitHub #2730 | G0 spec |
| `tools/mcp/memory_write_intent_tools.py` | Phase 1 handler anchor |
| `tools/mcp/permission_guard.py` | Three-layer defense anchor |
