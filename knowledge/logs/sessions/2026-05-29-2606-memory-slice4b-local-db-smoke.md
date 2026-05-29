# 2026-05-29 — #2606 Slice 4b Local DB Memory Smoke

## Scope

Controlled Reality-Slice for #2606: execute the local-only DB Memory Read Smoke for
the DB-backed `agent_memory` read proof delivered by PR #2686.

No productive DB writes, no Memory-Write feature, no MCP write, no BLUE/RED
mutation, no trading runtime, and no LR status change were allowed.

## Brain Evidence

brain_source: repo-only
brain_status: partial

tools_or_queries:
- `gh issue view 2606 --json number,title,state,labels,body,updatedAt,url`
- `gh issue view 2605 --json number,title,state,updatedAt,url`
- `gh issue view 2604 --json number,title,state,updatedAt,url`
- `gh issue view 2603 --json number,title,state,updatedAt,url`
- `gh pr view 2686 --json number,title,state,mergedAt,mergeCommit,url`
- `gh pr list --state open --limit 50 --json number,title,headRefName,baseRefName,isDraft,updatedAt,url`
- `git status --short`
- `git branch --show-current`
- `git rev-parse --short HEAD`
- `rg -n "CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE|memory_db_read_proof|context-up|context-down|context-status|context-schema-check|surrealdb-local|agent_memory" tools tests docs Makefile infrastructure`
- `docker ps --format ...`
- `docker compose -f infrastructure/compose/compose.blue.yml ps --format ...`
- `docker compose -f infrastructure/compose/compose.red.yml ps --format ...`
- `make context-env-check`
- `make context-status`
- `make context-doctor`
- `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1 pytest tests/local/surrealdb/test_memory_db_read_proof.py -q`
- `debug-747a60.log`

records_or_results:
- #2606: open
- PR #2686: merged
- open PR list: empty at live check
- `context-env-check`: SurrealDB env file present with values redacted
- `context-status`: `cdb_surrealdb` container not found; local volume exists
- `context-doctor`: `config.context_query_local: missing`, `surrealdb.status: not_reachable`, `next_action: create context_query.local.yaml from context_query.local.example.yaml`
- pytest local smoke: 2 skipped
- debug log line 1: H1 confirmed, `query_config_exists=false`, `query_config_example_exists=true`

repo_crosscheck:
- `AGENTS.md`
- `agents/AGENTS.md`
- `agents/roles/CLAUDE.md`
- `knowledge/SYSTEM.CONTEXT.md`
- `CURRENT_STATUS.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `knowledge/ACTIVE_ROADMAP.md`
- `tools/surrealdb/memory_db_read_proof.py`
- `tests/local/surrealdb/test_memory_db_read_proof.py`
- `tests/local/surrealdb/memory_db_proof_helpers.py`
- `tests/fixtures/surrealdb/memory_db_proof/agent_memories.jsonl`
- `tests/fixtures/surrealdb/memory_db_proof/evidence_refs.jsonl`
- `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`
- `docs/runbooks/surrealdb_context_mcp_access.md`
- `docs/surrealdb/memory-reality-slice1-audit.md`
- `Makefile`
- `tools/surrealdb/local_schema_check.py`
- `infrastructure/config/surrealdb/context_query.local.example.yaml`

impact_on_plan:
- The Slice did not start `context-up` because the local query config required by
  the real `surrealdb-local` read path was missing.
- No `source=surrealdb-local` DB-backed evidence is claimed.
- Gordon integration was not present in the visible MCP/tool inventory; the
  session used only documented repo Context Runtime commands.

limitations:
- No real DB-backed `agent_memory` read occurred.
- H2 Sidecar availability, H3 seed/import, H4 proof contract result, and H5 MCP
  source-honesty remained untested because H1 blocked before DB access.
- The local secret values were not inspected or copied.

## Live Lage

- #2606 remained open.
- #2605, #2604, and #2603 were inspected as related context.
- PR #2686 was confirmed merged.
- No open PRs were present during the live check.
- LR remains NO-GO.
- Board stage `trade-capable` remains orthogonal and does not authorize live
  capital or trading runtime.

## Gordon / Infra Gate

- `gordon_status: unavailable`
- No Gordon integration was available in the visible MCP/tool inventory.
- Only documented Context Runtime targets were used.
- No BLUE/RED mutation was performed.

## BLUE/RED Baseline

Before and after the blocked smoke attempt, read-only Docker status showed the
existing BLUE/RED services already running. The session did not start, stop, or
restart any BLUE/RED service.

`make context-status` showed:

- `cdb_surrealdb: not found`
- `cdb_database_surrealdb_data: exists`

## Context Runtime Status

`make context-env-check` passed with secret values redacted.

`make context-doctor` failed read-only preflight:

- `mcp_server.status: reachable`
- `surrealdb.status: not_reachable`
- `config.context_query_local: missing`
- `next_action: create context_query.local.yaml from context_query.local.example.yaml`

Because the query config was missing, `make context-up`, `make context-schema-check`,
and the real DB smoke were not executed.

## Local-only Smoke Result

Command:

```powershell
$env:CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE='1'; pytest tests/local/surrealdb/test_memory_db_read_proof.py -q
```

Result:

- 2 tests collected
- 2 skipped
- runtime debug evidence line 1 confirmed missing `context_query.local.yaml`

## Source Honesty

No `source=surrealdb-local` claim was made for this run.

The only source-honesty result is negative: the session stopped before a real
adapter-backed DB read could prove `surrealdb-local`.

## Teardown / Isolation

No Context Sidecar was started by this session, so no `context-down` was needed.

Post-check again showed `cdb_surrealdb` absent and BLUE/RED still running.

## Status

DONE_FAIL_WITH_FOLLOWUPS

Blocker:

- Missing local `infrastructure/config/surrealdb/context_query.local.yaml`
  prevents a truthful local-only DB Memory Read Smoke.
