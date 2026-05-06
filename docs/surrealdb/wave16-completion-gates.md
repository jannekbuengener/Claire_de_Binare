# Wave-16 Completion Gates

**Status**: OPEN — awaiting PR merge (all child-issue gates satisfied)
**Authority**: Issue #2161 / Wave-16 / Epic #1976
**Parent**: #2153

This document defines and tracks the completion gates for Wave-16
(Stale Knowledge Runtime and Refresh Planning v1).

---

## 1. Scope / Purpose

Wave-16 delivers a complete, read-only stale-knowledge detection and refresh-planning
runtime for the Context Intelligence Epic (#1976). The runtime consists of:

- A deterministic scan service detecting 8 stale-knowledge types
- A CLI for local, read-only execution of scans and reports
- An MCP tool (`cdb_context_stale`) for agent access
- A refresh plan generator (recommendation-only, no writes)
- Test coverage across all four components via inline and file-backed fixtures
- An operator/agent runbook

Wave-16 completion does **not** constitute a Live-Readiness authorisation,
an Echtgeld-Go, or any trading/runtime change. LR status remains **NO-GO**.

---

## 2. Wave-16 Completion Verdict

| Criterion | Status |
|-----------|--------|
| All child issues #2154–#2160 delivered and CLOSED | **PASS** |
| All PRs #2368–#2374 merged to `main` | **PASS** |
| #2161 (this gate) open until this PR merges | **EXPECTED** |
| #2153 (parent anchor) remains open until #2161 PR merges | **CORRECT** |
| All artifacts read-only, fail-closed, no writes | **PASS** |
| `write_authorized=False` on all refresh-plan items | **PASS** |
| LR status unchanged at NO-GO | **PASS** |
| No Echtgeld scope, no Live-Go, no runtime change | **PASS** |

**Wave-16 is COMPLETE** — all child delivery gates satisfied.

**#2161 is ready for closure** pending human review and merge of this PR.
**#2153 must remain open** until this PR is merged; it may be closed separately thereafter.

---

## 3. Evidence Matrix

| Issue | Title | PR | Merge-SHA | Delivered Artifacts | Validation Evidence |
|-------|-------|----|-----------|---------------------|---------------------|
| #2154 | Stale Knowledge Scan Service v1 | #2368 | `09e43564` | `tools/surrealdb/stale_knowledge_scan.py` (856 lines) · `tests/unit/surrealdb/test_stale_knowledge_scan.py` (817 lines, 36 tests) · `tests/fixtures/surrealdb/stale_knowledge_scan/sample_bundle.json` | 36/36 unit tests PASS · ruff clean · clock-guardrail test PASS · no forbidden wall-clock calls |
| #2155 | Stale Context CLI | #2370 | `33b9897` | `tools/surrealdb/stale_context_cli.py` · `tests/unit/surrealdb/test_stale_context_cli.py` | CLI unit tests PASS · all 3 subcommands covered · JSON/Markdown output validated · exit-code contract verified |
| #2157 | Stale Context MCP Tool | #2371 | `d560929` | `tools/mcp/stale_context_tools.py` · `tools/mcp/registry.py` (updated) · `tools/mcp/context_bridge.py` (updated) · `tools/mcp/permission_guard.py` (updated) · `tests/unit/tools/mcp/test_mcp_stale_context_tool.py` | MCP unit tests PASS · registry entry confirmed · `no_live_go: true` / `no_write: true` in all MCP output · permission guard exemption for read-only tool |
| #2158 | Refresh Plan Generator | #2372 | `f8d47db` | `tools/surrealdb/stale_refresh_plan.py` · `tests/unit/surrealdb/test_stale_refresh_plan.py` | Plan unit tests PASS · `write_authorized=False` on all plan items · deterministic `plan_id` (SHA256-based) · 6 guardrail strings present in output |
| #2159 | Stale Knowledge Fixtures & Tests | #2373 | `8ac8adb` | `tests/fixtures/surrealdb/stale_knowledge_scan/all_types_bundle.json` (triggers all 8 stale types) · `tests/unit/surrealdb/test_stale_fixtures.py` | Fixture tests PASS · all 8 stale types triggered by `all_types_bundle.json` · `sample_bundle.json` triggers exactly 3 expected types · deterministic across scan calls · no secrets in fixtures |
| #2160 | Stale Knowledge Runbook | #2374 | `64e0447` | `docs/surrealdb/stale-knowledge-runbook.md` | Runbook covers: scan execution, finding interpretation, refresh plan reading, reverification workflow, stale Memory/Decision/Evidence treatment, guardrails |
| #2161 | Wave-16 Completion Gates | this PR | — | `docs/surrealdb/wave16-completion-gates.md` (this document) | Gate criteria verified against live GitHub state |

---

## 4. Child-Issue Status

| Issue | Title | State |
|-------|-------|-------|
| #2154 | [SURREALDB][CONTEXT][STALE-RUNTIME] Implement stale knowledge scan service v1 | **CLOSED** |
| #2155 | [SURREALDB][CONTEXT][STALE-CLI] Add stale context CLI | **CLOSED** |
| #2157 | [SURREALDB][CONTEXT][STALE-MCP] Implement stale context MCP tool | **CLOSED** |
| #2158 | [SURREALDB][CONTEXT][REFRESH-PLAN] Generate context refresh plan | **CLOSED** |
| #2159 | [SURREALDB][CONTEXT][STALE-TESTS] Add stale knowledge fixtures and tests | **CLOSED** |
| #2160 | [SURREALDB][CONTEXT][STALE-RUNBOOK] Add stale knowledge runbook | **CLOSED** |
| #2161 | [SURREALDB][CONTEXT][VALIDATION] Define wave-16 completion gates | **OPEN** — closes when this PR merges |
| #2153 | Wave-16 anchor: Stale knowledge runtime and refresh planning v1 | **OPEN** — closes separately after #2161 PR merges |

---

## 5. Artifact Inventory

### 5.1 Production Tools

| File | Description | Merged via |
|------|-------------|------------|
| `tools/surrealdb/stale_knowledge_scan.py` | Stale Knowledge Scan Service v1 — 8 detection rules, deterministic SHA256 IDs, `scan_stale_knowledge_v1()` public API | PR #2368 (`09e43564`) |
| `tools/surrealdb/stale_context_cli.py` | Stale Context CLI — `scan-stale-context`, `show-stale-context`, `report-stale-context`; JSON/Markdown output; exit codes 0/1/2/3 | PR #2370 (`33b9897`) |
| `tools/mcp/stale_context_tools.py` | MCP adapter — `cdb_context_stale` tool; scope-filtered, read-only, fail-closed; `no_live_go: true` on every response | PR #2371 (`d560929`) |
| `tools/surrealdb/stale_refresh_plan.py` | Refresh Plan Generator v1 — converts scan results to prioritised plan; `write_authorized=False` always; 7 canonical recommended actions | PR #2372 (`f8d47db`) |

### 5.2 MCP Registry Updates

| File | Change | Merged via |
|------|--------|------------|
| `tools/mcp/registry.py` | Wave-16 `cdb_context_stale` entry added | PR #2371 (`d560929`) |
| `tools/mcp/context_bridge.py` | Routing for Wave-16 stale-context tool | PR #2371 (`d560929`) |
| `tools/mcp/permission_guard.py` | `cdb_context_stale` exempted (read-only, no input scan required) | PR #2371 (`d560929`) |

### 5.3 Tests

| File | Tests | Merged via |
|------|-------|------------|
| `tests/unit/surrealdb/test_stale_knowledge_scan.py` | 36 unit tests — all 8 detection rules, determinism, guardrails, severity summary | PR #2368 (`09e43564`) |
| `tests/unit/surrealdb/test_stale_context_cli.py` | CLI tests — all 3 subcommands, exit codes, JSON/Markdown, fail-on-blocking, determinism | PR #2370 (`33b9897`) |
| `tests/unit/tools/mcp/test_mcp_stale_context_tool.py` | MCP tool tests — all scope values, permission guard, no_live_go semantics, registry/bridge wiring | PR #2371 (`d560929`) |
| `tests/unit/surrealdb/test_stale_refresh_plan.py` | Plan generator tests — all 8 stale types → actions, priorities, deterministic plan_ids, write_authorized=False always | PR #2372 (`f8d47db`) |
| `tests/unit/surrealdb/test_stale_fixtures.py` | Fixture integration tests — `all_types_bundle.json` triggers all 8 types, `sample_bundle.json` triggers exactly 3, no secrets, CLI and MCP tool round-trips | PR #2373 (`8ac8adb`) |

### 5.4 Fixtures

| File | Description | Merged via |
|------|-------------|------------|
| `tests/fixtures/surrealdb/stale_knowledge_scan/sample_bundle.json` | Triggers `source_hash_changed`, `source_deleted`, `evidence_expired` (3 stale types) | PR #2368 (`09e43564`) |
| `tests/fixtures/surrealdb/stale_knowledge_scan/all_types_bundle.json` | Triggers all 8 stale types — full coverage fixture | PR #2373 (`8ac8adb`) |

### 5.5 Documentation

| File | Description | Merged via |
|------|-------------|------------|
| `docs/surrealdb/stale-knowledge-runbook.md` | Operator/agent runbook: scan execution, finding interpretation, refresh plan reading, reverification workflow, guardrails | PR #2374 (`64e0447`) |
| `docs/surrealdb/wave16-completion-gates.md` | This document | this PR |

---

## 6. Validation Summary

### 6.1 Service Tests (PR #2368 — Merge `09e43564`)

- **36/36 unit tests PASS** (`tests/unit/surrealdb/test_stale_knowledge_scan.py`)
- All 8 detection rules exercise at least one triggering and one non-triggering input
- `source_deleted` produces `severity=blocking`, all others `severity=warning`
- Deterministic IDs: same input → same `stale_id` across independent calls
- Clock-guardrail test (`test_clock.py::test_guardrails_no_forbidden_calls`) PASS — no forbidden `datetime.now()` / `datetime.utcnow()` / `uuid.uuid4()` calls
- `ruff check`: all checks passed
- No write/network/DB references in service file

### 6.2 CLI Tests (PR #2370 — Merge `33b9897`)

- All CLI subcommands covered: `scan-stale-context`, `show-stale-context`, `report-stale-context`
- Exit-code contract validated: `0` (ok), `1` (blocking + `--fail-on-blocking`), `2` (input error), `3` (stale_id not found)
- JSON and Markdown output formats verified
- Guardrail note present in Markdown output
- Deterministic output with same fixture verified
- `severity_summary` and `stale_type_summary` present in report output
- CLI does not write any file — confirmed

### 6.3 MCP Tool Tests (PR #2371 — Merge `d560929`)

- `cdb_context_stale` tool registered in `registry.py`, routed in `context_bridge.py`
- All 8 scope values validated (`all`, `artifact`, `decision`, `evidence`, `memory`, `edge`, `package`, `briefing`)
- `no_live_go: true` and `no_write: true` present in every response
- Permission guard: tool is in `INPUT_SCAN_EXEMPT_TOOLS` (read-only, no permission check needed)
- Bundle-driven: no DB/network fallback; missing bundle → clean error, not empty result

### 6.4 Refresh Plan Tests (PR #2372 — Merge `f8d47db`)

- All 8 stale types mapped to canonical `recommended_action`
- `source_deleted` → priority `P0` (highest)
- `plan_id` is deterministic (SHA256-based) across repeated calls with same input
- `write_authorized=False` on every plan item — no exception path
- All 6 guardrail strings present in `to_dict()` output
- Empty findings → `status=ok`, empty plan (not an error)
- Invalid (non-Mapping) input → `status=error`, no exception propagated uncontrolled

### 6.5 Fixture Tests (PR #2373 — Merge `8ac8adb`)

- `all_types_bundle.json`: loads without error, all 8 stale types triggered
- `sample_bundle.json`: triggers exactly 3 expected types (`source_hash_changed`, `source_deleted`, `evidence_expired`)
- Stale IDs deterministic across two independent scan calls from fixture
- Fixture JSON keys contain no secret-like names
- Fixture string values contain no absolute host paths
- CLI (`scan-stale-context`, `report-stale-context`) consumes `all_types_bundle.json` correctly
- MCP tool returns findings for all 8 stale types from `all_types_bundle.json`

### 6.6 CI / CodeQL / Policy Gates (all merged PRs)

| Gate | Status |
|------|--------|
| CI (unit + integration + lint) | PASS on all PRs #2368–#2374 |
| CodeQL (Python analysis) | PASS — no new alerts introduced |
| policy-gate | PASS — docs/tools/tests only; no `allow-core-change` required for wave-16 artifacts |
| Black formatting | PASS — PR #2369 applied formatting normalisation after #2368 |

---

## 7. Anti-Criteria

The following are explicit non-goals for Wave-16. Any PR or agent action that introduces
these behaviours must be rejected.

| Anti-criterion | Detail |
|----------------|--------|
| No automatic delete | Detection never modifies, removes, or tombstones any artifact, record, or system state |
| No automatic refresh write | `write_authorized=False` on every refresh-plan item; no plan item is self-executing |
| No runtime rebuild | No changes to trading-core, risk, execution, or signal services |
| No Live-Readiness-Go | A stale finding does not constitute or unlock a Live-Readiness GO signal |
| No Echtgeld-Go | No real-money trading is authorised by Wave-16 completion |
| No DB write | No SurrealDB SDK calls; all processing is in-memory on the input bundle |
| No GitHub write by tools | No `git commit`, `git push`, or GitHub API write from detection or planning tooling |

---

## 8. Guardrail Status

| Guardrail | Status |
|-----------|--------|
| Stale Detection is signal, not authorization | **ENFORCED** — embedded in all service, CLI, and MCP outputs |
| Refresh Plan is recommendation only | **ENFORCED** — `write_authorized=False` on all plan items; confirmed by tests |
| `write_authorized=False` | **ENFORCED** — `stale_refresh_plan.py` sets this unconditionally on every `RefreshPlanItem` |
| No automatic delete | **ENFORCED** — no delete code path exists in any Wave-16 artifact |
| No automatic refresh write | **ENFORCED** — confirmed by test suite and guardrail strings in output |
| LR status remains NO-GO | **UNCHANGED** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` verdict: NO-GO |
| Board-Stage `trade-capable` is orthogonal | **CONFIRMED** — stage ratified 2026-04-08 via Issue #1492; does not authorise live capital or strategy execution; wave-16 completion does not alter this |
| No SurrealDB SDK calls | **CONFIRMED** — no `surrealdb` import in any Wave-16 file; no network access |
| DELIVERY_APPROVED.yaml not modified | **CONFIRMED** — human-controlled; this document does not touch it |

---

## 9. Completion Criteria

### 9.1 What counts as fulfilled (PASS)

- [x] All child issues #2154, #2155, #2157, #2158, #2159, #2160 are CLOSED in GitHub
- [x] All PRs #2368, #2370, #2371, #2372, #2373, #2374 are merged to `main`
- [x] All implementation artifacts are present in the working tree on `main`
- [x] Unit tests pass for all four Wave-16 components (confirmed via PR CI)
- [x] `write_authorized=False` on all refresh-plan items (confirmed by tests)
- [x] All tools are read-only; no SurrealDB writes; no network; no auto-fix
- [x] LR status remains NO-GO (unchanged)
- [x] Runbook committed to `docs/surrealdb/stale-knowledge-runbook.md`
- [x] Gates doc committed (this document)

### 9.2 What does NOT count as fulfilled (FAIL)

- [ ] Any child issue still OPEN after its PR is merged
- [ ] Any Wave-16 tool that writes to a DB, filesystem, or GitHub without explicit human GO
- [ ] Any PR that enables `write_authorized=True` on a plan item
- [ ] Any inference of Echtgeld-Go or Live-Readiness GO from Wave-16 state
- [ ] Closing #2153 before this PR (#2161) is merged to `main`
- [ ] Auto-close of #2153 by any tool without explicit human GO signal

---

## 10. Closeout Instruction

1. **#2161** may be closed by adding `Closes #2161` to the PR body of the PR that merges
   this document. No separate GitHub action is required.

2. **#2153** (Wave-16 parent anchor) must remain open until the #2161 PR is merged.
   After that PR lands, #2153 may be closed **separately** — in a dedicated GitHub
   action by Jannek or an authorised agent. This PR does **not** and must **not**
   automatically close #2153.

3. **No auto-close of #2153** from this PR, unless Jannek gives an explicit GO signal
   (`GO CLOSE PARENT` or equivalent). The default is: #2153 stays open after merge until
   Jannek confirms closure.

4. **Branch hygiene**: The branch `docs/wave16-completion-gates` should be deleted after
   the PR merges. This is a standard post-merge cleanup and is separate from issue closure.

---

## 11. Residual Uncertainties

No material uncertainties remain for Wave-16 delivery.

Specifically:

- All 6 child issues are confirmed **CLOSED** (verified via `gh issue view --json state`
  at gate-document authoring time: 2026-05-06).
- All 6 PRs (#2368, #2370, #2371, #2372, #2373, #2374) are confirmed **MERGED** (verified
  via `git log --oneline` on `main`: merge SHAs `09e43564`, `33b9897`, `d560929`,
  `f8d47db`, `8ac8adb`, `64e0447` all present as HEAD ancestry).
- Stale detection tooling is entirely in-memory and read-only; no runtime dependency on a
  live SurrealDB instance, live Redis, or live Postgres exists.
- No Wave-17+ scope has been introduced into any Wave-16 artifact.

**Post-merge follow-up (not a blocker):**

- Branch `docs/wave16-completion-gates` deletion (routine cleanup).
- #2153 anchor closure by Jannek after this PR merges (separate step, not a blocker for
  Wave-17 continuation).

---

## 12. Governance Notes

- **LR-Status**: NO-GO (unchanged — Wave-16 is context tooling, not trading infrastructure).
  Source: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Board-Stage**: `trade-capable` (ratified 2026-04-08 via Issue #1492) — orthogonal to
  LR-STATUS; does not authorise live capital, strategy execution, or Grafana gate.
- **DELIVERY_APPROVED.yaml**: human-controlled; this document does not modify it.
- **Wave-16 detection as signal**: A stale finding, a refresh plan item, or a `cdb_context_stale`
  MCP response is an informational signal. It does not substitute for a human GO, a
  governance decision, or a Live-Readiness phase completion.
- **Stale Detection is not authorization**: Confirmed by embedded guardrail strings in all
  service, CLI, and MCP outputs and enforced by test assertions.
