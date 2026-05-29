# 2026-05-29 — #2691 optional agent_memory fields DB proof

## Scope

Fix #2691 for #2606 local-only DB Memory Read Smoke after #2687/#2690 resolved
the missing local query config blocker.

Guardrails: local `surrealdb-local` only, no Memory-Write feature, no MCP write,
no productive DB write, no BLUE/RED mutation, no Trading-/Live-/LR change.
LR remains `NO-GO`.

## Brain Evidence

brain_source: repo-only
brain_status: partial

tools_or_queries:
- `ReadFile` for bootloader/read-order files and #2691 files.
- `gh issue view 2691/2687/2689/2606`, `gh pr view 2690/2688/2686`,
  `gh pr list --state open`.
- `git fetch origin main`, `git status --short`, `git branch --show-current`,
  `git rev-parse --short HEAD`, `git rev-parse --short origin/main`.
- Runtime debug logs in `debug-899172.log` during reproduction and verification.
- `make context-query-config-init`, `make context-doctor`, `make context-env-check`,
  `make context-up`, `make context-status`, `make context-schema-check`.
- `pytest tests/local/surrealdb/test_memory_db_read_proof.py -q` with and
  without `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1`.

records_or_results:
- #2691: open at start.
- #2606: open at start.
- #2687: closed.
- #2689: open and out of scope.
- PR #2686/#2688/#2690: merged.
- No open PRs at start.
- `HEAD` and `origin/main`: `8500417d`.
- Post-fix smoke: `1 passed, 1 skipped` against `surrealdb-local`.

repo_crosscheck:
- `tools/surrealdb/memory_contract.py`
- `tools/surrealdb/memory_db_read_proof.py`
- `tests/local/surrealdb/test_memory_db_read_proof.py`
- `tests/local/surrealdb/memory_db_proof_helpers.py`
- `tests/fixtures/surrealdb/memory_db_proof/agent_memories.jsonl`
- `tests/fixtures/surrealdb/memory_db_proof/evidence_refs.jsonl`
- `infrastructure/surrealdb/context_intelligence_v0.surql`
- `docs/surrealdb/memory-reality-slice1-audit.md`

impact_on_plan:
- The fix stayed in the optional `agent_memory` schema/contract surface.
- No fixture fake-freshness or write-path workaround was added.

limitations:
- MCP resources were not used; DB-backed claim is limited to the explicit
  local smoke result.
- The local schema apply target is not idempotent on an already-seeded volume;
  local field updates were applied with targeted `DEFINE FIELD OVERWRITE`.

## Runtime evidence

Pre-fix reproduction:

- Smoke command: `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1 pytest tests/local/surrealdb/test_memory_db_read_proof.py -q`.
- Result: `1 skipped, 1 error`.
- Importer evidence: `adapter=surrealdb-local`, `real_surrealdb_adapter_available=true`,
  `apply_executed=true`, `counts.applied=2`, `counts.failed=2`.
- Error: `stale_after`: `Expected int but found NONE`.

Debug evidence:

- `agent_memory` payload logs showed `payload_has_stale_after=false`,
  `surql_contains_stale_after=false`, `surql_contains_null=false`.
- After fixing `stale_after`, the next optional schemafull field surfaced:
  `superseded_by`: `Expected string but found NONE`.
- Follow-up debug logs showed `payload_has_superseded_by=false`,
  `surql_contains_superseded_by=false`, `surql_contains_null=false`.

Conclusion:

- The bug was not caused by fixture values, helper injection, or JSON `null`.
- SurrealDB schemafull validation treats omitted optional fields as `NONE`;
  optional `agent_memory` fields must use `option<T>`.

## Fix

- `agent_memory.stale_after`: `TYPE int` -> `TYPE option<int>`.
- `agent_memory.superseded_by`: `TYPE string` -> `TYPE option<string>`.
- `validate_memory_record()` accepts explicit `None` for both optional fields.
- Unit coverage added for missing/`None` optional values and schema declarations.

No memory write API, MCP write path, production DB write, BLUE/RED mutation, or
LR status change was introduced.

## Validation

Passed:

- `pytest tests/unit/surrealdb/test_memory_db_read_proof.py -q`
- `pytest tests/unit/surrealdb/test_memory_contract.py tests/unit/surrealdb/test_memory_freshness.py tests/unit/surrealdb/test_memory_read_characterization.py tests/unit/surrealdb/test_wave14_context_record_schemas.py -q`
- `pytest tests/local/surrealdb/test_memory_db_read_proof.py -q` without env gate:
  `1 passed, 1 skipped`
- `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1 pytest tests/local/surrealdb/test_memory_db_read_proof.py -q`:
  `1 passed, 1 skipped`, source path exercised via `surrealdb-local`
- `ruff check tools/surrealdb/memory_contract.py tests/unit/surrealdb/test_memory_contract.py tests/unit/surrealdb/test_wave14_context_record_schemas.py tests/unit/surrealdb/test_memory_db_read_proof.py tests/local/surrealdb/test_memory_db_read_proof.py`
- `black --check tools/surrealdb/memory_contract.py tests/unit/surrealdb/test_memory_contract.py tests/unit/surrealdb/test_wave14_context_record_schemas.py tests/unit/surrealdb/test_memory_db_read_proof.py tests/local/surrealdb/test_memory_db_read_proof.py`

Known note:

- The successful real smoke emitted an existing `datetime.utcnow()` deprecation
  warning from `core/utils/clock.py`; it did not affect #2691.

## Local runtime and cleanup

- `make context-up` started only `cdb_surrealdb` on `127.0.0.1:8010`.
- `make context-status` showed `cdb_surrealdb` running and using
  `cdb_database_surrealdb_data`.
- Failed run-scoped partial `evidence_ref` rows were removed with the test-local
  cleanup helper.
- Debug instrumentation was removed after post-fix verification, and
  `debug-899172.log` was deleted.

## Status

DONE_NO_PR at log-write time; PR and issue lifecycle actions pending.
