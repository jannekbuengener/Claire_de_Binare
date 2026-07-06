# SurrealDB read-only context query harness (#3776)

Local-only integration surface for read-only Context Intelligence queries against
`surrealdb-local`. Standard CI does **not** require a live SurrealDB instance.

## Scope

| In scope | Out of scope |
| --- | --- |
| `local_only` read-only query probes | Productive SurrealDB writes |
| Namespace/DB isolation contract | Retrieval ranking regression (#3777) |
| Fail-closed repo-fallback posture | Stale-doc drift suite (#3779) |
| Unit/adapter tests without live DB | MCP live mutation |

## Safety defaults

- `MUTATION_ALLOWED=False` (module constant in `tools/mcp/memory_write_intent_tools.py`)
- Harness module has **no** productive write imports (`context_importer`, write gates, smoke writers)
- LR remains **NO-GO**; no trading-state tables, no sensitive values in fixtures

## Test layers

| Layer | Marker | Live DB | Command |
| --- | --- | --- | --- |
| Unit contract | `unit` + `contract` | No | `pytest -q tests/unit/surrealdb/test_context_readonly_query_harness.py` |
| Local integration | `local_only` | Opt-in | see below |

### Standard CI

`.github/workflows/ci.yaml` runs:

```bash
pytest -v -m "not e2e and not local_only" ...
```

`local_only` tests are excluded from required CI.

### Local read-only harness (opt-in)

Prerequisites:

1. Local SurrealDB on `http://127.0.0.1:8010`
2. `infrastructure/config/surrealdb/context_query.local.yaml` (see `make context-query-config-init`)
3. Secrets dir with `SURREALDB_ENV` (`SECRETS_PATH` or canon store)
4. Opt-in env flag: `CDB_RUN_REAL_SURREALDB_READONLY_QUERY=1`

```bash
# Unit contract (CI-safe)
pytest -q tests/unit/surrealdb/test_context_readonly_query_harness.py

# Local integration (skipped unless env + DB ready)
export CDB_RUN_REAL_SURREALDB_READONLY_QUERY=1
pytest -q -m local_only tests/local/surrealdb/test_context_readonly_query_harness.py

# Or all local_only tests
make test-local
```

PowerShell:

```powershell
$env:CDB_RUN_REAL_SURREALDB_READONLY_QUERY = "1"
pytest -q -m local_only tests/local/surrealdb/test_context_readonly_query_harness.py
```

## Harness contract

Module: `tools/surrealdb/context_readonly_query_harness.py`

| Case | Behavior |
| --- | --- |
| `local_only` marker | Local integration file marked `pytest.mark.local_only` |
| Standard CI exclusion | Verified via `standard_ci_excludes_local_only()` |
| Read-only default | Classifier denies `CREATE`/`UPSERT` before HTTP |
| Unreachable DB | `classify_db_evidence_posture()` → `repo-only`, no false DB claims |
| Namespace isolation | `cdb_context_local` / `cdb_context_intel` envelope |
| No productive write path | Static import guard on harness module |
| Adapter modes | `embedded`, `file`, `mem` (unit); `live` (local_only only) |

## Related surfaces

- `tools/surrealdb/context_query.py` — read-only query adapter + classifier
- `tests/local/surrealdb/test_memory_db_read_proof.py` — memory read proof (separate opt-in flag)
- `tests/local/tools/mcp/test_wave14_real_surrealdb_smoke.py` — Wave-14 MCP smoke (write seed + cleanup)

Issue: [#3776](https://github.com/jannekbuengener/Claire_de_Binare/issues/3776)
Parent: [#3771](https://github.com/jannekbuengener/Claire_de_Binare/issues/3771)
