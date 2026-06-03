# #1976 Grandparent DoD and Real-Task-Proof Readiness

| Field | Value |
| --- | --- |
| **Epic** | [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) (stays **OPEN**) |
| **Phase-2 prerequisite** | [#2778](https://github.com/jannekbuengener/Claire_de_Binare/issues/2778) **CLOSED** — [`SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md`](SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md) **`PASS_CLOSEOUT`** |
| **Repo SHA** | `1f2d361d529f8cd6ef33938c523e302eca25e07f` (`origin/main` post §B recert #2831) |
| **Review date** | 2026-06-03 (§B recert); 2026-06-02 (initial readiness) |
| **Readiness verdict** | **`READY_FOR_REAL_TASK_PROOF_RUN`** (scoped task [#2821](https://github.com/jannekbuengener/Claire_de_Binare/issues/2821)) |
| **Epic-close verdict** | **`HOLD`** — Grandparent DoD not fully satisfied (see §B) |
| **Real-Task-Proof Gate** | **`PASS`** (scoped #2821) — see §F addendum; does **not** authorize #1976 epic close |

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

Re-certified 2026-06-03 against `origin/main` @ `1f2d361d`. Full matrix: [`SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md`](SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md). Legend: **PASS** / **PASS_WITH_LIMITS** / **ACCEPTED_HOLD** / **OPEN** (follow-up).

| DoD group | Expectation (epic) | Status | Evidence / gap |
| --- | --- | --- | --- |
| Planungsanker Wellen 1–6 | Docs, contracts, models | **PASS** | Wave issues **CLOSED**; contracts on `main` |
| Welle 7 — Repo landing | Architecture, roadmap, schema draft, handoff | **PASS** | #2034–#2043 **CLOSED**; canon docs on `main` |
| Welle 8 — Indexer scaffold | CLI, scope, hash, chunk, JSONL, snapshot | **PASS_WITH_LIMITS** | [`context_indexer.py`](../../tools/surrealdb/context_indexer.py); epic e2e validation not re-run |
| Welle 9 — Symbol/graph export | AST, edges, graph JSONL | **PASS_WITH_LIMITS** | Export modules on `main`; productive DB apply not default |
| Welle 10 — Import/reconcile/apply | Controlled SurrealDB import pipeline | **PASS_WITH_LIMITS** | [`context_importer.py`](../../tools/surrealdb/context_importer.py); `PERSIST_ALLOWED=False` |
| Welle 11–12 — Query CLI / MCP | Read-only query + MCP bridge | **PASS_WITH_LIMITS** | `context_query.py`, MCP 27 read-only; #2773/#2774 closeout |
| Welle 13–14 — Briefing, evidence, memory, trust | Agent intelligence layer | **PASS_WITH_LIMITS** | Wave 14 + Phase-2 v2/replay on `main` |
| Welle 15–18 — Governance runtime | Contradiction, stale, scope, quality, architect | **PASS_WITH_LIMITS** | Runtime modules + closed anchors; runbook depth spot-check |
| Welle 19–20 — Control room, self-explanation, Agent OS | Reports + readiness | **PASS_WITH_LIMITS** | Builders + #2802 signal layer on `main` |
| Welle 21 — Cross-cutting | Search, CI, perf, backup plans | **ACCEPTED_HOLD** | #2205 **CLOSED**; vector/CI deferred per epic non-goals |
| Phase-2 overlay (#2778) | Read-only adoption, retrieval, ops | **PASS** | `PASS_CLOSEOUT` on `main` |
| Guardrails LR / writes / secrets | Fail-closed | **PASS** | LR NO-GO; gates False; #2803/#2804 |
| **#2821 secret policy (Gates 0–4)** | Managed/non-local prerequisite | **PASS** (design) | Policy doc; PR #2829; #2821 **CLOSED** |
| **Real-Task-Proof Gate (#2821)** | Live task under repo/GitHub context | **PASS** (scoped) | RTP run 2026-06-02; not second RTP |
| **Follow-up #2832** | Second RTP (other task type) | **OPEN** | [#2832](https://github.com/jannekbuengener/Claire_de_Binare/issues/2832) |
| **Follow-up #2833** | Close vs HOLD | **OPEN** | [#2833](https://github.com/jannekbuengener/Claire_de_Binare/issues/2833); blocked on #2832 |

### Epic-close verdict: **HOLD**

#1976 must **not** close until:

1. **Real-Task-Proof** — first scoped **PASS** (#2821) satisfied; second RTP [#2832](https://github.com/jannekbuengener/Claire_de_Binare/issues/2832) still **OPEN**, and
2. Operator closeout [#2833](https://github.com/jannekbuengener/Claire_de_Binare/issues/2833) ratifies **PASS_WITH_LIMITS** / **ACCEPTED_HOLD** rows or orders remediation.

Phase-2 **`PASS_CLOSEOUT`** and §B recert (#2831) do not authorize epic close alone.

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

**Real-Task-Proof status (2026-06-02 pre-run snapshot):** **not PASS** — superseded by §F after PR [#2829](https://github.com/jannekbuengener/Claire_de_Binare/pull/2829).  
**Readiness status (pre-run):** **`READY_FOR_REAL_TASK_PROOF_RUN`** — historical; see §F for post-run canon.

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
| Grandparent DoD (#1976) | **HOLD** — §B recert 2026-06-03; #2832/#2833 open; productive paths not activated |
| Real-Task-Proof Gate | **PASS** (scoped #2821) — §F; epic close still **HOLD** |
| **Readiness for proof run** | **Completed** — see §F; #2821 delivery via PR #2829 |

---

## Safety boundaries (unchanged)

- **LR:** NO-GO per [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
- **Board `trade-capable`:** not LR-Go
- **Writes:** `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`; no managed/non-local activation (#2803)
- **#2821:** activation blocker for **future** writes only; does **not** block this readiness assessment

---

## Governance postscript (2026-06-02, after PR #2827 merge)

GitHub **auto-closed** #1976 when PR #2827 merged (squash subject referenced `#1976`; PR body stated non-goals “does not close #1976”). That close was **not** Real-Task-Proof PASS or Grandparent DoD satisfaction. **#1976 was reopened** the same day with an explicit issue comment. Epic status on GitHub remains **OPEN**; ledger lines must not treat the transient close as canon.

---

## F) Real-Task-Proof run addendum (2026-06-02 UTC, PR #2829)

Post-run update to this SSOT. Supersedes §C/E **pre-run** FAIL rows for #2821 policy and RTP gate only.

| Item | Status | Evidence |
| --- | --- | --- |
| Scoped task | #2821 secret policy (design) | [`CDB_CONTEXT_MANAGED_RUNTIME_SECRET_POLICY_GATES_0_4.md`](../../knowledge/decisions/CDB_CONTEXT_MANAGED_RUNTIME_SECRET_POLICY_GATES_0_4.md) |
| Proof artifact | RTP **PASS** (§C matrix) | [`SURREALDB_1976_REAL_TASK_PROOF_RUN_2026-06-02.md`](SURREALDB_1976_REAL_TASK_PROOF_RUN_2026-06-02.md) |
| Delivery PR | [#2829](https://github.com/jannekbuengener/Claire_de_Binare/pull/2829) | Branch `real-task-proof-2821-secret-policy` @ `05483b5d` (pre-merge) |
| #2821 | Closes on merge | PR `Closes #2821` |
| #1976 | **Stays OPEN** | Epic-close **HOLD** per §B — RTP PASS satisfies criterion (1) only; criterion (2) FAIL/PARTIAL waves still open |

**Operator rule:** Do not close #1976 from RTP PASS alone. Comment on #1976 with proof link; remediate or accept §B gaps before epic closeout.

---

## G) §B recertification addendum (2026-06-03, #2831)

| Item | Status | Evidence |
| --- | --- | --- |
| Recert slice | **COMPLETE** (docs) | [`SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md`](SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md) |
| `origin/main` SHA | `1f2d361d` | Post PR #2830 ledger |
| §B row upgrades | PARTIAL → **PASS_WITH_LIMITS** / **ACCEPTED_HOLD** where current main supports | See recert doc |
| #2831 | Closes on merge | PR `Closes #2831` |
| #1976 | **Stays OPEN** | #2832 RTP #2 + #2833 closeout pending |

---

## Non-goals (this slice)

- Executing the Real-Task-Proof run itself *(completed in §F addendum via separate PR #2829)*
- Closing #1976 *(epic remains OPEN per §B)*
- Implementing Wellen 7–21 gaps or activating productive SurrealDB/MCP writes
- Closing #2832 or #2833 from #2831 alone
