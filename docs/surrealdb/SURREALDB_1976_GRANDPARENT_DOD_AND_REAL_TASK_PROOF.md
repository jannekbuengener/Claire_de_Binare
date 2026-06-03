# #1976 Grandparent DoD and Real-Task-Proof Readiness

| Field | Value |
| --- | --- |
| **Epic** | [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) (stays **OPEN**) |
| **Phase-2 prerequisite** | [#2778](https://github.com/jannekbuengener/Claire_de_Binare/issues/2778) **CLOSED** — [`SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md`](SURREALDB_PHASE2_FINAL_CLOSEOUT_REVIEW.md) **`PASS_CLOSEOUT`** |
| **Repo SHA** | `5face9c99eeb14b50f9d220b06728abfdd39ec3b` (`origin/main` after PR [#2834](https://github.com/jannekbuengener/Claire_de_Binare/pull/2834); recert evidence @ `1f2d361d`) |
| **Review date** | 2026-06-03 (§B recert); 2026-06-02 (initial readiness) |
| **Readiness verdict** | **`READY_FOR_REAL_TASK_PROOF_RUN`** (scoped task [#2821](https://github.com/jannekbuengener/Claire_de_Binare/issues/2821)) |
| **Epic-close verdict** | **`HOLD`** — Grandparent DoD not fully satisfied (see §B) |
| **Real-Task-Proof Gate** | **`PASS`** (scoped #2821) — see §F addendum; does **not** authorize #1976 epic close |

---

## Brain Evidence

**Current slice (2026-06-03 §B recert):** see Brain Evidence block in [`SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md`](SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md) (`brain_source: repo-only`, `brain_status: not-used` per [`agents/AGENTS.md`](../../agents/AGENTS.md)).

**Historical (2026-06-02 readiness pre-run):** archived in session log [`2026-06-02-1976-real-task-proof-readiness.md`](../../knowledge/logs/sessions/2026-06-02-1976-real-task-proof-readiness.md). Do not treat pre-run `#2821 OPEN` / SHA `f25c6f50` rows as live canon — superseded by §F and §B recert.

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

**Matrix SSOT:** [`SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md`](SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md) — full rows, Waves 8–12 pipeline, blocks/limits. Recert evidence @ `origin/main` `1f2d361d`; merged via PR [#2834](https://github.com/jannekbuengener/Claire_de_Binare/pull/2834) @ `5face9c9`. Legend: **PASS** / **PASS_WITH_LIMITS** / **ACCEPTED_HOLD** / **OPEN**.

| Area | Summary verdict |
| --- | --- |
| Wellen 1–7 | **PASS** |
| Wellen 8–20 | **PASS_WITH_LIMITS** (implementation on `main`; productive e2e/runbook depth not re-run in #2831) |
| Welle 21 | **ACCEPTED_HOLD** (vector/CI deferred per epic non-goals) |
| Phase-2 #2778 | **PASS** (`PASS_CLOSEOUT`) |
| Guardrails / #2821 design + RTP #2821 | **PASS** |
| **#2832** second RTP | **PASS** (PR #2839 @ `75e1e8e2`) — #2833 closeout still blocks epic close |
| **#2833** operator closeout | **OPEN** — ratify PASS_WITH_LIMITS / ACCEPTED_HOLD or remediate |

### Epic-close verdict: **HOLD**

#1976 must **not** close until #2832 completes and #2833 ratifies recert rows (see matrix SSOT). Phase-2 **`PASS_CLOSEOUT`** and §B recert (#2831, PR #2834) do not authorize epic close alone.

---

## C) Real-Task-Proof gate matrix (#1976 “Finales Real-Task-Proof Gate”)

**Historical pre-run snapshot (2026-06-02).** Superseded by §F for scoped RTP #2821 (**PASS**). Do not use `#2821 OPEN` or pre-run FAIL rows as live canon.

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
| #1976 | **Stays OPEN** | Epic-close **HOLD** — RTP PASS satisfies criterion (1) only; criterion (2) #2832 second RTP + #2833 closeout pending (§B recert: PASS_WITH_LIMITS / ACCEPTED_HOLD per matrix SSOT) |

**Operator rule:** Do not close #1976 from RTP PASS alone. Epic close requires #2832, #2833, and operator ratification of recert rows.

---

## G) §B recertification addendum (2026-06-03, #2831)

| Item | Status | Evidence |
| --- | --- | --- |
| Recert slice | **COMPLETE** (docs) | [`SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md`](SURREALDB_1976_WAVE_MATRIX_RECERTIFICATION_2026-06-03.md) |
| Recert evidence SHA | `1f2d361d` | Pre-merge recert baseline (post PR #2830 ledger) |
| Delivery | **MERGED** | PR [#2834](https://github.com/jannekbuengener/Claire_de_Binare/pull/2834) @ `5face9c9`; #2831 **CLOSED** |
| §B row upgrades | PARTIAL → **PASS_WITH_LIMITS** / **ACCEPTED_HOLD** | Full matrix in recert doc only |
| #1976 | **Stays OPEN** | #2832 RTP #2 + #2833 closeout pending |

---

## H) RTP #2 addendum (2026-06-03, #2832)

| Item | Status | Evidence |
| --- | --- | --- |
| Scoped task | #2513 read-only Trivy triage (no dismissals) | Issue body + `docs/security/TRIAGE_RUNBOOK.md` |
| Proof artifact | RTP **PASS** (§C matrix) | [`SURREALDB_1976_REAL_TASK_PROOF_RUN_2026-06-03.md`](SURREALDB_1976_REAL_TASK_PROOF_RUN_2026-06-03.md) |
| Delivery PR | **MERGED** | PR [#2839](https://github.com/jannekbuengener/Claire_de_Binare/pull/2839) @ `75e1e8e2`; #2832 **CLOSED** |
| #2832 | **CLOSED** | RTP **PASS** — proof doc on `main` |
| #1976 | **Stays OPEN** | #2833 operator closeout still pending |
| #2833 | **Stays OPEN** | Ratify §B rows after RTP #2 |

---

## Non-goals (this slice)

- Executing the Real-Task-Proof run itself *(completed in §F addendum via separate PR #2829)*
- Closing #1976 *(epic remains OPEN per §B)*
- Implementing Wellen 7–21 gaps or activating productive SurrealDB/MCP writes
- Closing #2832 or #2833 from #2831 alone
