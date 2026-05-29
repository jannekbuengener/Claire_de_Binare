# Session Log: #2603 Runtime Smoke Slice 1

**Date:** 2026-05-29  
**Issue:** #2603 (Epic — SurrealDB Context Runtime)  
**Branch:** `feat/2603-runtime-smoke-slice1`  
**LR:** NO-GO (unchanged)  
**Board stage:** trade-capable (orthogonal; no live capital)

## Scope

Local SurrealDB context runtime proof only. BLUE/RED read-only; no trading/live changes.

## Preflight

| Check | Result |
|-------|--------|
| `make context-env-check` | PASS (credentials redacted) |
| `make context-doctor` | EXIT 1 — missing `context_query.local.yaml` (MCP onboarding; non-blocking for runtime slice) |
| BLUE/RED baseline | 27 containers up including `cdb_surrealdb` |

## Runtime

| Step | Result |
|------|--------|
| `make context-up` | PASS (idempotent, 127.0.0.1:8010) |
| `make context-status` | `cdb_surrealdb` healthy, volume present |
| `make context-schema-check` (soft) | 18/18 tables, exit 0 |
| Hard schema check | 18/18 tables, exit 0 (extra: `config_reference`, `doc_code_link`) |
| `make context-schema-apply` | Not required |

## Smoke DB

### First run (pre-fix)

- `make context-smoke-db` → **EXIT 2** at import
- Root cause: Makefile used parse-time `$(shell gen_run_id.py …)` so import `--run-id` did not match post-scan snapshot → `run_id_mismatch`
- Artifact: `artifacts/context-intelligence/2603-smoke-db-output.txt`

### Fix applied

- `context-smoke-db` step 3: resolve `run_id` at recipe runtime (Windows `pwsh` + Unix `RUN_ID=$$(…)`)
- `context-down`: Windows `pwsh` branch (was bash-only)
- Contract tests updated (`test_context_smoke_db_contracts.py`)

### Second run (post-fix)

- `make context-smoke-db` → **EXIT 0** (~26 min; large smoke scope)
- Step 3: `"adapter": "surrealdb-local"`, local-dev apply OK
- Step 4: `"source": "surrealdb-local"`, `"status": "ok"`, `repo_artifact` records returned (min-count satisfied)
- Artifact: `artifacts/context-intelligence/2603-smoke-db-output-fixed.txt`

## Teardown / isolation

| Step | Result |
|------|--------|
| `make context-down` | PASS (Windows pwsh path) |
| BLUE/RED diff | Only `cdb_surrealdb` removed (27→26 containers); all other `cdb_*` unchanged |

## Deliverables

- Code fix + unit tests on branch `feat/2603-runtime-smoke-slice1`
- PR (Refs #2603; epic not closed)
- GitHub comment on #2603 with PASS matrix

## Follow-ups (not in Slice 1)

- `context-doctor` exit 1 for missing `infrastructure/config/surrealdb/context_query.local.yaml` → #2605 / MCP onboarding scope
- Epic body stale (claims `context-smoke-db` missing) — update in separate docs pass if desired

## Status

**DONE_WITH_FIX_PR** — runtime proof PASS after Makefile Windows/run_id fix.
