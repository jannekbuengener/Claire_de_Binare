# Productive Memory Audit Trail v1 — Contract (#2730)

**Issue:** [#2730](https://github.com/jannekbuengener/Claire_de_Binare/issues/2730)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (stays OPEN)  
**Status:** Spec / governance design — **NOT ACTIVATED**  
**LR:** NO-GO ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md))  
**Board stage:** `trade-capable` is orthogonal; not live authorization.

---

## 1. Purpose and scope

This document defines the **productive memory audit trail** contract: what
audit evidence must exist before any future productive Memory Write surface may
be considered, without enabling productive writes in this slice.

**In scope (this issue):**

- Formal semantics for a productive-tier audit trail
- Fail-closed defaults and Human-GO tier separation
- Evidence requirements for future productive write readiness
- Activation gate ladder (spec-only; no code flip)

**Out of scope (explicit):**

- Enabling productive `agent_memory` UPSERT
- Flipping `PERSIST_ALLOWED` in code (remains `False` on `main`)
- MCP mutation execution (`MUTATION_ALLOWED` remains `False`)
- Auto-Memory, BLUE/RED runtime changes, LR upgrade, Echtgeld go

Operator procedures: [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md).

---

## 2. Terminology ladder

Surfaces are ordered. Higher tiers inherit lower-tier constraints; lower tiers
**do not** imply authorization for higher tiers.

| Tier | Name | Persistence | Host / runtime | Tables touched |
| --- | --- | --- | --- | --- |
| T0 | Gate evaluation (in-memory) | None | Any | None |
| T1 | Dry-run (zero SQL) | None | Any | None |
| T2 | Local `audit_observation` | Opt-in UPSERT | `127.0.0.1:8010` only | `audit_observation` |
| T3 | **Productive audit trail** (this spec) | Durable, non-localhost | Governed SurrealDB endpoint (future) | `audit_observation` only |
| T4 | Productive `agent_memory` write (future) | Durable | Governed endpoint (future) | `agent_memory` + linked refs |

```text
T0 GateEvaluation → T1 dry_run → T2 local audit_observation → T3 productive audit trail → T4 productive agent_memory write
```

Current `main` delivery stops at **T2**. **T3 is specified here but not activated.**

---

## 3. Productive audit trail semantics

### 3.1 Definition

The **productive memory audit trail** is the durable, queryable record of every
Human-GO-gated memory write **intent evaluation** (pass or block) on a
**governed non-localhost** SurrealDB context runtime — independent of whether
`agent_memory` is eventually written.

An audit trail row is an **`audit_observation`** with
`observation_type: memory_write_gate_evaluation` (see
[`audit-observation-model-v1.md`](audit-observation-model-v1.md) §3).

### 3.2 Allowed record classes (T3 contract)

| Record type | Allowed in T3 productive audit? | Notes |
| --- | --- | --- |
| `audit_observation` (`memory_write_gate_evaluation`) | **Yes** | Primary audit trail unit |
| `evidence_ref` (linked from observation) | **Reference only** | Via `evidence_refs`; no standalone write in T3 |
| `agent_memory` | **No** | T4 only; separate gate chain |
| `claim`, `decision_event` | **No** | Out of T3 scope unless explicitly linked in `evidence_refs` |

### 3.3 Required fields (minimum productive audit row)

Aligned with [`audit-observation-model-v1.md`](audit-observation-model-v1.md) and
gate envelope in [`memory-write-gate-v1.md`](memory-write-gate-v1.md) §5:

| Field | Requirement |
| --- | --- |
| `observation_id` | Stable; deterministic from gate payload where applicable |
| `observation_type` | `memory_write_gate_evaluation` |
| `subject_ref` | `agent_memory:{memory_id}` when known; else documented fallback |
| `severity` | `info` (approved dry-run path) or `blocking` (gate blocked) |
| `message` | Human-readable block reason or approval note (no raw token) |
| `evidence_refs` | Non-empty on pass; merged record + authorization refs |
| `observed_by` | e.g. `memory_write_gate/v1` or governed path id (future) |
| `observed_at` | ISO-8601 UTC |
| `status` | `open` on create; lifecycle per observation model §5 |
| `created_at` | Set at persist time |

**Productive-tier extensions (metadata in `comment` or structured extension — future schema slice):**

| Extension | Purpose |
| --- | --- |
| `target_issue` | GitHub issue driving the intent (e.g. `2606`) |
| `git_commit_sha` | Repo SHA at evaluation time |
| `gate_status` | `blocked_*` or `approved_dry_run` |
| `authorization_scope` | Must match record scope |
| `human_go_token_present` | Boolean only — **never** raw token |
| `run_id` / `workflow_run_id` | Optional CI/operator run correlation |

Materializer reference (local T2 today):
[`tools/surrealdb/audit_observation_from_gate.py`](../../tools/surrealdb/audit_observation_from_gate.py).

### 3.4 Retention and immutability

| Rule | Productive audit (T3 spec) |
| --- | --- |
| Delete | **Forbidden** for productive rows (use `status: superseded` / `resolved`) |
| Update | Status transitions only; core observation payload append-only by convention |
| Retention | Minimum retention policy TBD in implementation slice; spec requires **no silent drop** |
| Local T2 rows | Run-scoped DELETE allowed per [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md) |

### 3.5 Reference conventions

| Field | Convention |
| --- | --- |
| `observed_by` | Tool/module id + version (e.g. `memory_write_path/v1`) |
| `subject_ref` | `agent_memory:{memory_id}` per runbook §8 |
| Issue ref | GitHub issue number in metadata / evidence pack, not as live-go |
| Commit ref | Full SHA in evidence pack; optional in row metadata |

---

## 4. Fail-closed default matrix

Default when no explicit productive-tier Human-GO and activation gate pass:
**no SQL, no MCP mutation, no `agent_memory` write.**

| Mode / surface | Default | SQL | `agent_memory` | MCP mutation |
| --- | --- | --- | --- | --- |
| `evaluate_memory_write_gate()` | Fail-closed on missing GO | No | No | No |
| Write path v1 `dry_run` | Default | No | No | No |
| Write path v1 `audit_persist_local` | Opt-in; localhost only | Yes (audit only) | No | No |
| MCP `cdb_context_memory_write_intent` | Dry-run only | No | No | **Blocked** |
| Productive audit trail (T3) | **Not activated** | N/A | No | No |
| Productive `agent_memory` write (T4) | **Repo-backed HG-W proof path; blocked by default** | No | No | No |

Module constants on `main` (unchanged by this spec):

- `PERSIST_ALLOWED = False` in [`memory_write_gate.py`](../../tools/surrealdb/memory_write_gate.py)
- `MUTATION_ALLOWED = False` in MCP write intent handler

---

## 5. `PERSIST_ALLOWED` governance

`PERSIST_ALLOWED` is a **code-level fail-closed guard**. It remains **`False`**
until a future maintainer gate chain (G3 below) approves a code change in a
**separate issue/PR**.

| Rule | Detail |
| --- | --- |
| Current value | `False` (module constant) |
| This issue | **Must not** change the constant |
| Meaning when `False` | Gate pass = `approved_dry_run` only; no importer/adapter persist from gate module |
| T2 local smoke / path | Env-gated operator paths (`CDB_RUN_REAL_SURREALDB_MEMORY_WRITE`, `CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT`) are **orthogonal** env flags — not a `PERSIST_ALLOWED` flip |
| Future flip | Not required for the 2026-05-31 HG-W proof path; any permanent-on or code-level activation still requires a separate issue/PR + evidence pack + explicit LR review (LR upgrade **not** implied) |

---

## 6. Human-GO tiers

Human-GO tokens use pattern `GO-YYYY-MM-DD[-suffix]`. Tiers are **not transferable**.

| Tier | Name | Authorizes | Does **not** authorize |
| --- | --- | --- | --- |
| HG-L | Local operator GO | T2 local proofs, Slice 6 localhost smoke, local audit persist | Productive audit, productive write, MCP mutation |
| HG-P | Productive audit GO (future) | T3 audit trail persist on governed endpoint | `agent_memory` write, `PERSIST_ALLOWED` flip |
| HG-W | Productive write GO (future) | T4 `agent_memory` write on governed endpoint | LR live-go, Echtgeld, trading runtime |

Invalid as memory-write GO (unchanged from gate v1):

- `DELIVERY_APPROVED.yaml`
- `decision_event.human_go`
- `context.readiness` hints
- Agent self-asserted fields on the memory record

---

## 7. Future productive write evidence checklist

Before any **T4 productive `agent_memory` write** activation slice, evidence must
include **all** items (implementation issue — not #2730):

- [ ] Git commit SHA and issue ref with explicit maintainer Human-GO (HG-W)
- [ ] Gate unit tests green: `test_memory_write_gate.py`, `test_memory_write_path_v1.py`
- [ ] Audit materializer tests green: `test_audit_observation_from_gate.py`
- [ ] MCP write intent tests green; mutation still blocked until separate MCP GO
- [ ] Proof that raw `human_go_token` never appears in logs, audit rows, or MCP responses
- [ ] Operator evidence pack per readiness runbook
- [ ] Rollback / cleanup procedure documented and exercised on non-prod
- [ ] Explicit statement: **LR remains NO-GO** unless changed via LR SSOT only
- [ ] Parent #2606 DoD matrix re-audit with criterion 6 re-evaluated
- [ ] No implication from Board stage `trade-capable`

---

## 8. Abgrenzung table

| Surface | Host | Env gate | Tables | Productive? | Canon doc |
| --- | --- | --- | --- | --- | --- |
| Gate in-memory | Any | None | None | No | `memory-write-gate-v1.md` |
| Path v1 dry_run | Any | None | None | No | `memory-write-path-v1-runbook.md` |
| Path v1 audit_persist_local | `127.0.0.1:8010` | `CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT=1` | `audit_observation` | **No** (local proof) | `memory-write-path-v1-runbook.md` |
| Slice 6 write smoke | `127.0.0.1:8010` | `CDB_RUN_REAL_SURREALDB_MEMORY_WRITE=1` | `evidence_ref`, `agent_memory` | **No** (local proof) | `memory-write-gate-v1.md` §8 |
| MCP write intent | N/A | None | None | No (dry-run) | `mcp-memory-write-surface-v1.md` |
| **Productive audit trail (T3)** | Governed endpoint (future) | HG-P + activation gate | `audit_observation` | **Spec only** | **this document** |
| **Productive memory write (T4)** | Governed endpoint | HG-W + `CDB_PERSIST_ALLOWED=1` + `CDB_PERSIST_PRODUCTIVE_AGENT_MEMORY=1` | `audit_observation`, `agent_memory` + refs | **Operator-scoped proof path; default blocked** | [`memory-write-path-t4-runbook-v1.md`](memory-write-path-t4-runbook-v1.md) |

---

## 9. Activation gates (status)

| Gate | Name | Deliverable | #2730 |
| --- | --- | --- | --- |
| G0 | Spec | This contract + readiness runbook | **This issue** |
| G1 | Non-local audit endpoint design | Endpoint, TLS, namespace, credentials policy | [#2735](https://github.com/jannekbuengener/Claire_de_Binare/issues/2735) — [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) |
| G2 | MCP Phase 2 design | Mutation guard + audit wiring spec | [#2739](https://github.com/jannekbuengener/Claire_de_Binare/issues/2739) — [`productive-memory-audit-trail-mcp-phase2-design-v1.md`](productive-memory-audit-trail-mcp-phase2-design-v1.md) |
| G3 | Env-gated persist guard | `approved_for_persist()` + proof scope + fail-closed env gates; module constant still `False` | [#2759](https://github.com/jannekbuengener/Claire_de_Binare/issues/2759) / [#2762](https://github.com/jannekbuengener/Claire_de_Binare/pull/2762) |
| G4 | Productive `agent_memory` write | Repo-backed proof executor + rollback on governed endpoint; default fail-closed on `main` | [#2758](https://github.com/jannekbuengener/Claire_de_Binare/issues/2758) / [#2759](https://github.com/jannekbuengener/Claire_de_Binare/issues/2759) / [#2763](https://github.com/jannekbuengener/Claire_de_Binare/pull/2763) |

**Rule:** No gate may be skipped. G0 did not activate T3/T4; the 2026-05-31 HG-W proof path stayed operator-scoped and fail-closed on `main`.

---

## 10. LR / live / Echtgeld boundaries

| SSOT | Rule |
| --- | --- |
| [`LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md) | Operative Go/No-Go for Echtgeld; remains **NO-GO** |
| [`CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md) | Board stage; not live authorization |
| This contract | Audit trail spec does not imply LR-GO or strategy release |

---

## 11. Cross-references

| Document | Role |
| --- | --- |
| [`audit-observation-model-v1.md`](audit-observation-model-v1.md) | Observation type catalog |
| [`memory-write-gate-v1.md`](memory-write-gate-v1.md) | Gate + Human-GO |
| [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md) | T2 operator path |
| [`mcp-memory-write-surface-v1.md`](mcp-memory-write-surface-v1.md) | MCP dry-run / Phase 2 |
| [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md) | Proof matrix row 3 |
| [`memory-reality-slice1-audit.md`](memory-reality-slice1-audit.md) | Slice history §22 |
| [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md) | Operator readiness |
| [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) | G1 endpoint design (#2735) |
| [`productive-memory-audit-trail-mcp-phase2-design-v1.md`](productive-memory-audit-trail-mcp-phase2-design-v1.md) | G2 MCP Phase 2 design (#2739) |

---

## Provenance

| Source | Role |
| --- | --- |
| GitHub #2730 | Spec delivery issue |
| GitHub #2606 | Parent epic (NOT_CLOSURE_READY) |
| Parent closure audit #2705 | Criterion 6 PARTIAL — no production audit stream |
| `tools/surrealdb/memory_write_gate.py` | `PERSIST_ALLOWED = False` anchor |
