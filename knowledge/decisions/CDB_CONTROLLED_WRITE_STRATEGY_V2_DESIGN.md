# Controlled Write Strategy v2 — Design Only

| Field | Value |
| --- | --- |
| Status | **accepted** / **design-only** (no activation) |
| Date | 2026-06-02 |
| Issue | GitHub issue #2804 |
| Parent | GitHub issue #2778 (Phase-2 epic) |
| Grandparent | GitHub issue #1976 |
| Executive decision | `controlled_writes_design_only_no_activation` |
| Decision label | `NO_WRITE_ACTIVATION_ON_MAIN` |

## Scope

This document is the **single source of truth (SSOT)** for how CDB may eventually
authorize **productive SurrealDB writes** and **MCP mutation surfaces**. It is a
**governance and design** artifact only.

**In scope:**

- Threat model, forbidden write classes, future write-intent classes
- Human-GO gate model, evidence and audit requirements
- Permission guard, MCP registry, rollback, and activation blockers
- Phase-2 closeout reconciliation for epic #2778 (child matrix, deferred items)

**Out of scope (unchanged by this document):**

- Implementing write paths, adapters, or MCP handlers that persist or mutate
- Flipping `PERSIST_ALLOWED` or `MUTATION_ALLOWED` on `main`
- Productive DB writes, MCP write tool registration, or runtime activation
- LR upgrade, Echtgeld authorization, BLUE/RED changes, or trading actions
- Closing #2778 or #1976 (separate operator closeout decisions)

**Related SSOT (do not duplicate):**

- Read-only brain posture: [`CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md) (#2775)
- Managed/non-local runtime: [`CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md`](CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md) (#2803)
- MCP memory write intent (dry-run): [`docs/surrealdb/mcp-memory-write-surface-v1.md`](../../docs/surrealdb/mcp-memory-write-surface-v1.md) (#2704)
- G2 MCP Phase-2 design: [`docs/surrealdb/productive-memory-audit-trail-mcp-phase2-design-v1.md`](../../docs/surrealdb/productive-memory-audit-trail-mcp-phase2-design-v1.md) (#2739)
- Memory write gate harness: [`docs/surrealdb/memory-write-gate-v1.md`](../../docs/surrealdb/memory-write-gate-v1.md) (#2606 slice 5)
- Secret policy (Gate 0–4): GitHub issue #2821

---

## Executive decision

**`controlled_writes_design_only_no_activation`**

On `main`, after Phase-2 slice #2804:

1. **No productive SurrealDB write path is activated** by this decision or PR.
2. **`PERSIST_ALLOWED=False`** and **`MUTATION_ALLOWED=False`** remain code and policy defaults.
3. **All future write implementation** requires a **separate scoped issue**, explicit
   **Jannek-GO**, LR/HG ladder compliance where applicable, and satisfaction of
   activation blockers in this document.
4. **Context Brain output** (briefing, package, control-room signals, certification
   PASS) **does not authorize** writes, merges, issues, or runtime changes.

---

## Current default posture

| Gate / flag | Value on `main` | Evidence |
| --- | --- | --- |
| `PERSIST_ALLOWED` | `False` | `tools/surrealdb/memory_write_gate.py`; env-gated HG proofs only |
| `MUTATION_ALLOWED` | `False` | `tools/mcp/memory_write_intent_tools.py` (`MUTATION_ALLOWED = False`) |
| MCP registry | All tools `read_only=True`; `register()` rejects non-read-only | `tools/mcp/registry.py` |
| `cdb_context_memory_write_intent` | Dry-run gate evaluation only | Registry + handler; G3a refuses non-dry-run modes |
| Productive memory adapter | `PRODUCTIVE_ACTIVATED=False` (mock proofs) | #2744, #2745 |
| Managed write-capable runtime | **REJECTED** | #2803 decision matrix |
| LR | **NO-GO** | [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) |

Agents default to **`brain_source=repo-only`**, **`brain_status=not-used`** until
guarded read evidence exists (#2775). Write evaluation, if ever invoked, stays
**dry-run** until a future slice explicitly changes code gates under GO.

---

## Threat model

### Assets to protect

- Operator secrets (API keys, vault material, connection strings)
- Trading and risk state (orders, fills, positions, balances, kill-switch, allocation)
- Governance truth (LR SSOT, issue/PR state, audit trails)
- Agent trust boundary (no forged DB-backed claims, no auto-action from context)

### Threat actors / scenarios

| Scenario | Risk | Mitigation (design) |
| --- | --- | --- |
| Agent or MCP performs UPSERT/DELETE on productive SurrealDB | Data corruption, undeclared memory | Registry + PermissionGuard + statement class block; no write tools on main |
| Raw SurrealQL from agent parameters | Injection, schema destruction | Input gate on query tools; no raw SurrealQL tool surface |
| Context Brain PASS → auto persist/merge/close issue | Unauthorized governance action | Explicit: certification/control-room ≠ authorization |
| `PERSIST_ALLOWED=True` slipped via env or PR | Silent write enablement | Code review + policy-gate; separate GO per slice |
| Secrets in context tables or proof packs | Leak via GitHub/logs | Forbidden class; #2821 secret policy before managed paths |
| Trading state ingested into SurrealDB | LR boundary blur, replay pollution | Forbidden class; Postgres/Redis remain order path SSOT |
| Managed/non-local endpoint without secret policy | Credential exposure | #2803 deferred; #2821 blocker |
| Caller-forged `brain_source` / `metadata.source` | Fake DB evidence | #2638 / #2775 guards; write slices require adapter proof |

### Trust boundaries

- **Inside:** dry-run `evaluate_memory_write_gate()`, read-only MCP, in-memory builders
- **Outside (requires GO + slice):** productive adapter, T3/T4 audit persist, agent_memory UPSERT, registry `read_only=False`

---

## Forbidden write classes

The following MUST NOT be written to SurrealDB (or via Context MCP mutation) without
a **future explicit slice** and **Jannek-GO** that references this SSOT and passes
activation blockers:

1. **Secrets and credentials** — API keys, tokens, vault paths, connection strings
2. **Trading state** — orders, fills, positions, balances, exposure, PnL snapshots
3. **Risk and execution state** — kill-switch, allocation overrides, regime overrides
4. **Live-readiness or board authorization flags** — LR-Go, Echtgeld-Go, delivery approval
5. **Raw SurrealQL execution** — unconstrained query strings from agents or tools
6. **Automatic actions from Context Brain** — issue create/close, PR merge, compose up,
   label apply, or code commit triggered by briefing/package/control-room output
7. **Productive `agent_memory` content** without HG-W / memory ladder GO and audit trail
8. **Cross-tenant or cross-namespace data** without isolation design review

**Historical note:** HG-W T4 proof (#2759) wrote **audit_observation** under explicit
operator proof with `PERSIST_ALLOWED` still **False** on `main` defaults — that path
is **not** generalized by this document.

---

## Allowed future write-intent classes (not writes)

Future slices may expose **write-intent evaluation only** (dry-run or gate check)
before any persist. These are **candidates**, not approvals:

| Class | Description | Preconditions |
| --- | --- | --- |
| `memory_write_intent_dry_run` | Evaluate Human-GO + contract validity | Already on main (#2704); stays dry-run |
| `audit_observation_local` | Local T3 proof row (HG-P ladder) | Existing proof path; not default-on |
| `audit_observation_productive` | Productive T3 endpoint | G1/G3 issues + endpoint GO; spec only today |
| `agent_memory_write` | Governed agent_memory UPSERT | HG-W + #2606 criteria + audit trail |
| `context_ingestion_batch` | Deterministic import (non-trading) | Import scope canon + redaction + operator proof |
| `schema_apply_governed` | Schema migration under CLI gate | Separate schema GO; never agent-initiated raw DDL |

**None** of the above may ship as default-on productive writes on `main` under #2804.

---

## Human-GO gate model

### Gate layers (cumulative)

| Layer | Owner | Required for |
| --- | --- | --- |
| **L0 — Design** | This document (#2804) | Any write strategy discussion |
| **L1 — Slice issue + Jannek-GO** | Operator | Any implementation PR touching write gates |
| **L2 — LR SSOT** | Human via LR docs | Anything implying live capital or production trading |
| **L3 — HG ladder** | Operator proof | `audit_observation`, `agent_memory`, T4 paths |
| **L4 — Secret policy** | #2821 + decision | Managed/non-local or credential-bearing paths |
| **L5 — MCP/registry change** | Scoped issue | `read_only=False`, new mutation tool, PermissionGuard relax |

### Jannek-GO minimum content

Each write-activation slice must state in the issue or PR:

- Exact write class (from allowed-intent table or new justified class)
- Files/symbols touched (`memory_write_gate`, registry, adapter, compose if any)
- Proof plan (unit tests, operator proof, rollback steps)
- Explicit **non-goals** (no LR-Go, no trading data, no secret values in repo)

**Certification PASS**, **control-room overall PASS**, and **agent_os_readiness PASS**
are **health signals only** — they are **not** Jannek-GO and **not** write authorization.

---

## Evidence requirements

Before any future write implementation is considered **proven**:

| Requirement | Applies to |
| --- | --- |
| `source_ref` | Every persisted record (canonical source id / path) |
| `evidence_ref` | Link to tool output, proof row id, or GitHub evidence |
| `operator_id` / `human_go_ref` | Issue number or signed operator note (no raw tokens) |
| `brain_source` + `brain_status` | Only with real adapter/tool/record evidence (#2775) |
| Redaction proof | Proof packs and session logs reviewed for secrets |
| Repo crosscheck | GitHub live state matches claimed delivery |
| Limitations block | Honest gaps in Brain Evidence / session close |

Caller-supplied `brain_source`, `metadata.source`, or MCP `metadata` alone are **not**
DB evidence (issue #2638).

---

## Audit trail requirements

Any activated write path must:

1. Emit **audit_observation** or equivalent per
   [`productive-memory-audit-trail-v1.md`](../../docs/surrealdb/productive-memory-audit-trail-v1.md)
   before or with the write (design TBD per slice).
2. Use **deterministic IDs** where CDB owns identifiers (`core.utils.uuid_gen` policy).
3. Support **replay verification** — hashes or envelopes traceable to inputs.
4. **Never** log raw `human_go_token` or secret field values (#2704 guard).
5. Record **refusal reason** on blocked writes (G2 codes in memory write intent).

---

## Redaction and secret policy dependency

Writes that touch memory content, proof exports, or GitHub comments must follow:

- No secrets in issues, PRs, comments, logs, or session reports (CDB safety boundary)
- **GitHub issue #2821** — Context managed runtime secret policy (Gate 0–4) must be
  **accepted or explicitly deferred with compensating controls** before:
  - managed/non-local read activation (#2803 future paths)
  - any productive write to non-localhost endpoints
  - any credential in adapter config checked into repo

Until #2821 closes or passes review, treat **managed secret policy** as an
**activation blocker** for write-capable managed runtime.

---

## Permission guard requirements

[`tools/mcp/permission_guard.py`](../../tools/mcp/permission_guard.py) implements
defense in depth (#2099):

1. **Registry gate** — non-read-only tools blocked at registration
2. **Execute gate** — `ToolDefinition.read_only` before handler dispatch
3. **Input gate** — mutative SQL/SurrealQL patterns in free-text query parameters

**Future write activation** must NOT bypass PermissionGuard by:

- Registering `read_only=False` without registry + guard contract update
- Exempting write tools from input scan without handler-level validation
- Adding tools that accept `query`/`surql` with write keywords unchecked

`cdb_context_memory_write_intent` remains exempt from blanket input scan on record
body only; mutation flags still fail-closed.

Any new write tool requires:

- Explicit registry entry review
- PermissionGuard classification: `read-only` | `dry-run` | `blocked` | `future write-gated`
- Unit tests for refusal paths

---

## MCP registry requirements

[`tools/mcp/registry.py`](../../tools/mcp/registry.py):

- `ContextToolRegistry.register()` raises on `read_only=False`
- `assert_read_only_consistency()` after handler wiring

**#2804 does not register write tools.** Future slices that need mutation must:

1. Propose registry contract change in a dedicated issue
2. Extend PermissionGuard and MCP closeout docs (#2773 / #2605 lineage)
3. Update `claire-de-binare.mcp.json` only with operator GO
4. Re-run MCP capability matrix (§1.5.1 runbook)

Current MCP inventory remains **read-only** (27 tools in pre-Phase-2 audit; write intent
is dry-run classified).

---

## Rollback / kill switch

### Code rollback

1. Revert implementation PR; confirm `PERSIST_ALLOWED` / `MUTATION_ALLOWED` constants
   on `main` are **False**
2. Re-run `ContextToolRegistry.assert_read_only_consistency()`
3. Run `make context-certify` or equivalent; expect read-only PASS, LR NO-GO unchanged

### Operational rollback

1. Disable productive endpoint env vars / adapter config paths
2. Revoke Human-GO scope for the slice (comment on issue; do not reuse GO for rollback PR)
3. Preserve audit rows written during proof (do not delete audit trail for compliance)

### Fail-closed default

On ambiguity, **stop writes** and report `brain_status=blocked` with limitations.
Repo-only fallback is correct behavior, not failure.

---

## Testing strategy for future implementation

When a write slice is authorized (not #2804):

| Layer | Minimum |
| --- | --- |
| Unit | Gate refusal matrix; mutation flags; PermissionGuard patterns |
| Contract | Envelope hashes; no float on money paths if financial fields touched |
| Integration | Mock adapter only unless explicit local_only stack GO |
| Operator proof | Redacted session log; `audit_observation_written` yes/no explicit |
| CI | No required check depends on live productive SurrealDB without deferral doc |

#2804 adds **no new tests** — design-only delivery.

---

## Activation blockers

Do **not** activate productive writes until **all** relevant rows pass:

| Blocker | Owner issue / doc |
| --- | --- |
| This design accepted on `main` | #2804 (this document) |
| Secret policy Gate 0–4 | #2821 |
| MCP write surface contract (G2/G3) | #2739, #2741, future G3c |
| LR SSOT still NO-GO for live capital | LR audit status |
| Managed runtime not conflated with writes | #2803 |
| Epic #2778 final closeout (optional for first write slice) | #2778 operator review |
| Separate Jannek-GO per implementation slice | Per-issue |

---

## Explicit non-goals

- Default `PERSIST_ALLOWED=True` or `MUTATION_ALLOWED=True` on `main`
- Productive DB writes or MCP mutations in #2804 PR
- Raw SurrealQL agent tool
- Trading state, secrets, or risk-state in SurrealDB
- LR-Go, Echtgeld-Go, or live order path changes
- Automatic actions from Context Brain or control-room PASS
- Closing #2778 or #1976 in the #2804 PR
- Implementing #2821 secret policy in this slice

---

## Phase-2 closeout reconciliation

This section satisfies **Phase-2 final child delivery** (#2804) and prepares epic
**#2778** for operator closeout review. It does **not** close #2778.

### Child slice status matrix (#2797–#2804)

| Issue | Title (short) | GitHub state | PR | Merge SHA (squash unless noted) | Purpose |
| --- | --- | --- | --- | --- | --- |
| #2797 | Read-only Agent Brain adoption | CLOSED | #2807 | `649912bda6bb7510e02296b07a5a884e745853e2` | Adoption contract + agent surfaces |
| #2798 | Context Package v2 | CLOSED | #2816 | `c7149703df73b3916789054b7ea228c9c865440f` | `build_context_package_v2` + contract |
| #2799 | Hybrid retrieval / ranking v1 | CLOSED | #2812 | `8bc98fab3c17d40669e77e4b4d66e8722ffd91bf` | Pure builder + fixtures (MCP search deferred) |
| #2800 | Evidence-aware decision replay v2 | CLOSED | #2814 | `622fb17d0689fa89ba4429e1c371480810ac7b0f` | Replay v2 builder + MCP handler |
| #2801 | Operator certification usage | CLOSED | #2808 | `171bd74f` | Certification runbook usage on main |
| #2802 | Control-room signal layer v1 | CLOSED | #2818 | `2f1d88c6daa19e0eb42ad8107917ed9bfb4019cc` | Read-only signal envelope builder |
| #2803 | Managed/non-local runtime decision | CLOSED | #2820 | `02ce3ed73568621a33427efe84240c89880afb32` | `local_only`; managed write **NO-GO** |
| #2804 | Controlled write strategy v2 (design) | OPEN → closes with this PR | (this PR) | (pending merge) | This SSOT; **no activation** |

### Delivered artifact map (on `main` before #2804 merge)

| Area | Canonical paths (reference only) |
| --- | --- |
| Decisions | `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`, `CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md` |
| SurrealDB docs | `docs/surrealdb/context-package-model-v2.md`, `context-hybrid-retrieval-strategy-v1.md`, `decision_replay_query_contract.md`, `control-room-readonly-signal-layer-v1.md`, `context-wave20-agent-os-readiness-runbook.md` |
| Runbooks | `docs/runbooks/surrealdb_context_mcp_access.md` (§1.5, §1.6) |
| Tools (read-only / builders) | `tools/surrealdb/context_package_v2.py`, `hybrid_retrieval_ranking.py`, `decision_replay_builder.py`, `control_room_signal_layer.py`, `agent_os_readiness.py` |
| MCP | `tools/mcp/permission_guard.py`, `memory_write_intent_tools.py`, `registry.py`, decision replay tools |
| Tests | `tests/unit/surrealdb/test_context_package_v2.py`, `test_hybrid_retrieval_ranking.py`, `test_decision_replay_builder_v2.py`, `test_control_room_signal_layer.py`, `tests/unit/agents/test_agent_brain_adoption_contract.py`, etc. |
| Pre-Phase-2 audit | `docs/surrealdb/SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md` (#2780) |

### Deferred / parked / rejected

| Item | Status | Notes |
| --- | --- | --- |
| Productive writes on `main` | **REJECTED** (this doc) | Activation blockers apply |
| `managed_write_capable` runtime | **REJECTED** | #2803 matrix |
| MCP `context.search` vector wiring | **DEFERRED** | #2799 non-goal |
| Post-Phase-2 exit documentation audit | **DEFERRED** | #2780 pre-audit done; full exit report before #2778 close |
| Runbook status Draft → Active | **DEFERRED** | Non-blocking per #2780 |
| Secret policy Gate 0–4 | **OPEN** | #2821 |
| Visual control-room UI / Grafana | **OUT OF SCOPE** | #2802 pure builder only |
| Phase-2 epic close | **PENDING REVIEW** | See checklist below |

### Final docs reconciliation checklist

| Criterion | #2804 PR | Before #2778 epic close |
| --- | --- | --- |
| Controlled write SSOT exists | **Yes** (this file) | — |
| Phase-2 children #2797–#2804 documented | **Yes** (matrix above) | Verify after #2804 merge |
| `PERSIST_ALLOWED` / `MUTATION_ALLOWED` explicit in canon | **Yes** | Re-scan runbook + decisions |
| LR NO-GO explicit | **Yes** | LR SSOT unchanged |
| No doc implies default productive writes | **This PR reviews** | Post-Phase-2 exit audit (#2780 deferred list) |
| Runbooks match implemented commands | Partial | Full exit pass |
| #1976 Phase-2 status reconciled | **Comment + ledger** | Grandparent stays OPEN |
| Linked final documentation audit | **Refs #2780 pre-audit** | **New exit report link required** |

### Remaining #1976 requirements (high level)

- Grandparent epic **#1976** stays **OPEN** until Real-Task-Proof and broader epic
  criteria are met outside this slice.
- Phase-2 deliverables under #2778 are **complete** after #2804 merge (all eight
  children closed).
- Phase-2 does **not** imply LR-Go or memory write activation.

### LR NO-GO and write-gate confirmation

- **LR:** NO-GO per [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- **Board stage `trade-capable`:** not LR-Go (#1492 ratification)
- **Write gates on `main`:** `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False` (unchanged)

### Closeout readiness for #2778

**Recommended epic status after #2804 merge:** `READY_FOR_FINAL_CLOSEOUT_REVIEW`

**Do not auto-close #2778** in the #2804 PR. Operator should confirm:

1. All eight Phase-2 children closed with linked PR SHAs
2. Documentation Exit Gate: post-Phase-2 exit reconciliation (deferred item from
   #2780) completed or accepted as follow-up with explicit HOLD
3. No open blocker threads on Phase-2 PRs
4. #1976 reconcile comment updated

If exit documentation audit is not linked, status remains **HOLD_CLOSEOUT** with
exact missing item listed on #2778.

---

## References

- GitHub: #2804, #2778, #1976, #2821, #2775, #2803, #2780
- [`agents/AGENTS.md`](../../agents/AGENTS.md) — Brain Evidence Gate, write defaults
- [`docs/surrealdb/SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md`](../../docs/surrealdb/SURREALDB_PRE_PHASE2_DOCS_CANON_AUDIT.md)
- [`docs/runbooks/surrealdb_context_mcp_access.md`](../../docs/runbooks/surrealdb_context_mcp_access.md)
