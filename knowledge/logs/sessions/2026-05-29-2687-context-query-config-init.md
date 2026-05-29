# 2026-05-29 — #2687 Context Query Config Init

## Scope

Follow-up for #2606 Slice 4b after the local-only DB Memory Read Smoke stopped
truthfully on missing `infrastructure/config/surrealdb/context_query.local.yaml`.

Allowed scope was limited to a small, secret-free config-template/runbook/doctor
fix for #2687. No productive DB writes, no Memory-Write feature, no MCP write,
no BLUE/RED mutation, no trading runtime, and no LR status change were allowed.

## Brain Evidence

brain_source: repo-only
brain_status: partial

tools_or_queries:
- `git fetch origin main`
- `git status --short`
- `git log --oneline origin/main..HEAD`
- `gh pr view 2688 --json number,title,state,mergedAt,mergeCommit,url`
- `gh pr view 2686 --json number,title,state,mergedAt,mergeCommit,url`
- `gh issue view 2687 --json number,title,state,labels,body,updatedAt,url`
- `gh issue view 2606 --json number,title,state,closedAt,updatedAt,url`
- `rg -n "Gordon|gordon|Docker AI|Ask Gordon|native AI" ...`
- MCP descriptor reads for `context.readiness` and `context.required_reads`
- `context.readiness` and `context.required_reads`

records_or_results:
- #2606: open
- #2687: open
- PR #2686: merged
- PR #2688: merged
- Gordon decommission follow-up issue created as #2689 after open-issue dedupe
- No `source=surrealdb-local` DB-backed read occurred in this session

repo_crosscheck:
- `AGENTS.md`
- `agents/AGENTS.md`
- `agents/roles/CLAUDE.md`
- `knowledge/SYSTEM.CONTEXT.md`
- `CURRENT_STATUS.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `knowledge/ACTIVE_ROADMAP.md`
- `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`
- `docs/runbooks/surrealdb_context_query.md`
- `docs/runbooks/surrealdb_context_mcp_access.md`
- `infrastructure/config/surrealdb/context_query.local.example.yaml`
- `tools/surrealdb/memory_db_read_proof.py`
- `tests/local/surrealdb/test_memory_db_read_proof.py`
- `tests/local/surrealdb/memory_db_proof_helpers.py`
- `Makefile`

impact_on_plan:
- The missing local query config was treated as an operator-local bootstrap gap,
  not as a reason to commit a real local config or infer secrets.
- The fix provides `make context-query-config-init`, updates doctor guidance, and
  keeps `context_query.local.yaml` gitignored.
- The real local DB smoke remains a separate operator/runtime verification step.

limitations:
- No real `surrealdb-local` DB read was performed.
- The local sidecar was not started and no local secret values were inspected.
- #2606 remains open; this does not prove Slice 4b DB-backed memory evidence.

## Result

Implemented a small, secret-free #2687 fix:

- Added `tools/surrealdb/local_query_config_init.py`.
- Added `make context-query-config-init`.
- Added `.gitignore` protection for
  `infrastructure/config/surrealdb/context_query.local.yaml`.
- Updated `context_onboarding_doctor` next-action guidance.
- Updated SurrealDB local context runbooks to use the init target.
- Added unit coverage for config creation, idempotency, missing examples, and
  secret-value absence.

## Validation

Local checks run before PR creation:

- `python -m pytest -q tests/unit/surrealdb/test_local_query_config_init.py tests/unit/surrealdb/test_context_onboarding_doctor.py::test_prioritize_next_action tests/unit/surrealdb/test_context_query_config.py::test_example_config_loads_successfully`
- `ruff check tools/surrealdb/local_query_config_init.py tools/surrealdb/context_onboarding_doctor.py tests/unit/surrealdb/test_local_query_config_init.py tests/unit/surrealdb/test_context_onboarding_doctor.py`
- `make -n context-query-config-init`
- `git check-ignore -v infrastructure/config/surrealdb/context_query.local.yaml`

PR #2690 was opened with `Refs #2687, Refs #2606`; #2606 was not closed.

## Status

DONE_WITH_PR

