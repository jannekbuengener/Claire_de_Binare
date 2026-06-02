# #1976 Grandparent DoD and Real-Task-Proof Readiness

| Field | Value |
| --- | --- |
| **Epic** | [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) (stays **OPEN**) |
| **Phase-2 prerequisite** | [#2778](https://github.com/jannekbuengener/Claire_de_Binare/issues/2778) **CLOSED** — [`SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md`](SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md) **`PASS_CLOSEOUT`** |
| **Repo SHA** | `f25c6f50751fbb6d7bc8e19b81e84cefedb08b9d` (`origin/main` at readiness review) |
| **Review date** | 2026-06-02 |
| **Readiness verdict** | **`READY_FOR_REAL_TASK_PROOF_RUN`** (scoped task [#2821](https://github.com/jannekbuengener/Claire_de_Binare/issues/2821)) |
| **Epic-close verdict** | **`HOLD`** — Grandparent DoD not fully satisfied; Real-Task-Proof **not PASS** |

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: used
tools_or_queries:
  - gh issue view 1976 --json state; gh issue view 2778 --json state; gh issue view 2821 --json state (2026-06-02)
  - gh issue list --state open (context band #2034–#2205 → none open)
  - git rev-parse HEAD → f25c6f50751fbb6d7bc8e19b81e84cefedb08b9d
  - PYTHONPATH=. python: create_bridge().list_tools() → 27 tools, all_readonly=True
  - pytest -q tests/unit/surrealdb/test_context_package_v2.py tests/unit/agents/test_agent_brain_adoption_contract.py -m unit → 23 passed
records_or_results:
  - #2778: CLOSED (GitHub live)
  - #1976, #2821: OPEN
  - Context wave #2034–#2205: no open issues in gh list
  - Phase-2 closeout on main: PASS_CLOSEOUT (doc + C1–C14)
repo_crosscheck:
  - docs/surrealdb/SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md
  - knowledge/decisions/CDB_CONTEXT_* + CDB_CONTROLLED_WRITE_STRATEGY_V2_DESIGN.md
  - tools/surrealdb/context_indexer.py, context_importer.py, context_package_v2.py, agent_os_readiness.py
  - tools/mcp/context_bridge.py, permission_guard.py
  - tests/unit/surrealdb/test_context_package_v2.py, tests/unit/agents/test_agent_brain_adoption_contract.py
impact_on_plan:
  - Phase-2 closeout ≠ #1976 Grandparent DoD; epic stays OPEN
  - Real-Task-Proof run not yet executed → no PASS claim
  - Next step: scoped read-only proof on #2821 (separate Run-GO for execution)
limitations:
  - No surrealdb-local query/record IDs in this readiness slice
  - Grandparent wave matrix uses repo + GitHub issue closure; not full re-validation of every wave gate artifact
```

---

## A) Prerequisite: Phase-2 (#2778)

| Item | Status | Evidence |
| --- | --- | --- |
| Phase-2 children #2797–#2804 | **CLOSED** | Closeout matrix; `gh issue view` 2026-06-02 |
| Closeout doc on `main` | **PASS** | [`SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md`](SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md), decision **`PASS_CLOSEOUT`**, C1–C14 |
| Merge chain | **Recorded** | #2807–#2825, ledger #2826 @ `f25c6f50` |

**Explicit boundary:** Phase-2 closeout satisfies the **#2778** epic only. It does **not** satisfy the full **#1976** “Definition of Done” (Wellen 7–21 end-to-end validation + Real-Task-Proof Gate).

---

## B) Grandparent DoD matrix (#1976 body)

Grouped status against `main` + GitHub (2026-06-02). Legend: **PASS** = belegt und konsistent; **PARTIAL** = Teillieferung oder nicht produktiv validiert; **FAIL** = fehlt oder widerspricht; **N/A** = Planungs-only-Slice.

| DoD group | Expectation (epic) | Status | Evidence / gap |
| --- | --- | --- | --- |
| Planungsanker Wellen 1–6 | Docs, contracts, models | **PASS** | Wave issues closed; `knowledge/decisions/`, `docs/surrealdb/` contracts |
| Welle 7 — Repo landing | Architecture, roadmap, schema draft, handoff | **PASS** | Wave #2034–#2043 **CLOSED**; canon docs on `main` |
| Welle 8 — Indexer scaffold | CLI, scope, hash, chunk, JSONL, snapshot | **PARTIAL** | [`tools/surrealdb/context_indexer.py`](../../tools/surrealdb/context_indexer.py) (local-only v0); full wave validation vs epic “validated” wording not re-run here |
| Welle 9 — Symbol/graph export | AST, edges, graph JSONL | **PARTIAL** | Modules under `tools/surrealdb/`; export path exists; productive graph DB apply **not** default |
| Welle 10 — Import/reconcile/apply | Controlled SurrealDB import pipeline | **PARTIAL** | [`context_importer.py`](../../tools/surrealdb/context_importer.py); **`PERSIST_ALLOWED=False`** on `main`; explicit apply not production-active |
| Welle 11–12 — Query CLI / MCP | Read-only query + MCP bridge | **PARTIAL** | Phase-2 builders + MCP bridge (27 tools, all read-only); not full wave 11–12 runbook re-certification in this slice |
| Welle 13–14 — Briefing, evidence, memory, trust | Agent intelligence layer | **PARTIAL** | Wave 14 delivered per repo history (`evidence_lookup`, `claim_resolver`, `memory_read`, `trust_summary`); Phase-2 adds package v2 / replay v2 |
| Welle 15–18 — Governance runtime | Contradiction, stale, scope, quality, architect | **PARTIAL** | `contradiction_scan.py`, `stale_knowledge_scan.py`, `scope_drift_*.py`, `quality_scoring.py`, `architect_signals.py` on `main`; wave anchors **CLOSED** on GitHub; runbook completeness not re-audited |
| Welle 19–20 — Control room, self-explanation, Agent OS | Reports + readiness | **PARTIAL** | `control_room_view_builder.py`, `context_self_explanation.py`, `evaluate_agent_os_readiness_v1` in [`agent_os_readiness.py`](../../tools/surrealdb/agent_os_readiness.py); #2802 signal layer orthogonal |
| Welle 21 — Cross-cutting | Search, CI, perf, backup plans | **PARTIAL** | Anchor #2205 **CLOSED**; vector search / CI integration largely **plan/design** per epic non-goals |
| Guardrails LR / writes / secrets | Fail-closed | **PASS** | LR NO-GO SSOT; `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`; #2803 `local_only`; #2804 design-only writes |
| **#2821 secret policy (Gates 0–4)** | Managed/non-local prerequisite | **FAIL** (open work) | [#2821](https://github.com/jannekbuengener/Claire_de_Binare/issues/2821) **OPEN** — design-only policy not landed |
| **Real-Task-Proof Gate** | Live task under repo/GitHub context | **FAIL** (not run) | This document is **readiness only**; see §C |

### Epic-close verdict: **HOLD**

#1976 must **not** close until:

1. **Real-Task-Proof Gate** reaches **PASS** (or explicit **BLOCKED** with fail-closed evidence), and  
2. Remaining **FAIL/PARTIAL** items above are accepted as out-of-scope for close **or** remediated with evidence.

Phase-2 **`PASS_CLOSEOUT`** does not override (1).

---

## C) Real-Task-Proof gate matrix (#1976 “Finales Real-Task-Proof Gate”)

| Criterion | Required | Evidence today (2026-06-02) | Gap |
| --- | --- | --- | --- |
| Echtes offenes CDB-Issue | Yes | **#2821 OPEN** (design-only secret policy) | None for task selection |
| Read Order + GitHub-live reads | Yes | Readiness slice: `agents/AGENTS.md`, LR/CONTROL SSOT, `gh issue view` timestamped | Full run must repeat at proof execution time |
| Branch/repo status, scope, guardrails | Yes | Worktree @ `f25c6f50`; `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False` | Proof run must re-state branch/SHA |
| Brain Evidence (honest source) | Yes | This block: **repo-only** | Run may add `in_memory` if fixtures only |
| Konkreter Plan/Patch-Entwurf | Yes | **Missing** — scoped plan in §D only | Delivered in `SURREALDB_1976_REAL_TASK_PROOF_RUN_<date>.md` after run |
| Validierungsplan + Ergebnis | Yes | Slice: pytest 23 passed; MCP 27 read-only | Run must execute full plan + policy checklist |
| Restunsicherheiten fail-closed | Yes | Documented in §B/C limitations | Run must list per-task uncertainties |
| No false LR/DB/live claims | Yes | LR NO-GO explicit | Run must re-check |

**Real-Task-Proof status today:** **not PASS** (no documented live task execution).  
**Readiness status:** **`READY_FOR_REAL_TASK_PROOF_RUN`** — blockers for *starting* a scoped read-only run are cleared; execution is a **separate Run-GO**.

---

## D) Scoped Real-Task-Proof run — [#2821](https://github.com/jannekbuengener/Claire_de_Binare/issues/2821)

**Title:** Context managed runtime secret policy (design)  
**Why this task:** Open; Context/SurrealDB lineage (#2778 → #2803); design-only matches read-only proof without write-GO; no BLUE/RED / LR soak / Echtgeld.

| Field | Content |
| --- | --- |
| **Issue** | #2821 |
| **Mode** | Read-only analysis + policy doc **draft** (no commit without Run-GO) |
| **Read Order** | [`agents/AGENTS.md`](../../agents/AGENTS.md) § Read Order; [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md); [`docs/runbooks/CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md) |
| **File targets** | [`knowledge/decisions/CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md`](../../knowledge/decisions/CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md); [`docs/runbooks/surrealdb_context_mcp_access.md`](../runbooks/surrealdb_context_mcp_access.md); new policy addendum under `knowledge/decisions/` (Gates 0–4 from #2803) |
| **Symbol / tool targets** | `tools/mcp/permission_guard.py`; `create_bridge()` in [`tools/mcp/context_bridge.py`](../../tools/mcp/context_bridge.py); `build_context_package_v2` in [`tools/surrealdb/context_package_v2.py`](../../tools/surrealdb/context_package_v2.py); `evaluate_agent_os_readiness_v1` in [`tools/surrealdb/agent_os_readiness.py`](../../tools/surrealdb/agent_os_readiness.py) |
| **Context use** | MCP `list_tools()` enumerate (read-only); optional `build_context_package_v2` with #2821-scoped fixture request — **`brain_source`** only `repo-only` / `in_memory` unless adapter returns verifiable record IDs |
| **Validation plan** | `pytest -q tests/unit/surrealdb/test_context_package_v2.py tests/unit/agents/test_agent_brain_adoption_contract.py -m unit`; policy checklist vs #2821 acceptance (no secrets in output); `ruff check` on touched `.py` if any |
| **Stop conditions** | Any write path; managed activation; secret values in issues/PR/logs; LR-Go or productive DB/MCP mutation claims |

**Deliverable after run (not this slice):** `docs/surrealdb/SURREALDB_1976_REAL_TASK_PROOF_RUN_<date>.md` + #1976 comment with **PASS / PARTIAL / FAIL / BLOCKED** only when run completes.

---

## E) Verdict summary

| Verdict | Value |
| --- | --- |
| Phase-2 prerequisite (#2778) | **Satisfied** (`PASS_CLOSEOUT` on `main`) |
| Grandparent DoD (#1976) | **HOLD** — partial wave delivery; #2821 open; productive paths not activated |
| Real-Task-Proof Gate | **Not PASS** — run not executed |
| **Readiness for proof run** | **`READY_FOR_REAL_TASK_PROOF_RUN`** on **#2821** (read-only) |

---

## Safety boundaries (unchanged)

- **LR:** NO-GO per [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- **Board `trade-capable`:** not LR-Go
- **Writes:** `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`; no managed/non-local activation (#2803)
- **#2821:** activation blocker for **future** writes only; does **not** block this readiness assessment

---

## Non-goals (this slice)

- Executing the Real-Task-Proof run itself
- Closing #1976 or #2821
- Implementing Wellen 7–21 gaps or activating productive SurrealDB/MCP writes
