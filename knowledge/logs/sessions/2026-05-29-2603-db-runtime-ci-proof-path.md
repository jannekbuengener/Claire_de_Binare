# Session: #2603 DB Runtime / CI Proof Path

**Date:** 2026-05-29  
**Branch:** `feat/2603-db-runtime-ci-proof-path`  
**PR:** #2718  
**LR:** NO-GO (unchanged)  
**#2606:** OPEN (NOT_CLOSURE_READY)

---

## Deliverables

| Item | Status |
|------|--------|
| Proof-gap matrix | `docs/surrealdb/db-runtime-ci-proof-path-v1.md` |
| Operator target | `make context-memory-db-proof` |
| Runtime + CLI | `memory_db_proof_runtime.py`, `memory_db_proof_cli.py` |
| Shared local-dev | `memory_db_proof_local_dev.py` (tests re-export helpers) |
| Unit contracts | `test_local_runtime.py`, `test_memory_db_proof_runtime_contract.py` |
| Runbook cross-link | `SURREALDB_LOCAL_CONTEXT_RUNTIME.md` |
| Follow-ups | #2719 claim at rest, #2720 cross-session, #2721 optional CI workflow |

---

## Validation (local)

```text
pytest tests/unit/surrealdb/test_local_runtime.py \
  tests/unit/surrealdb/test_memory_db_proof_runtime_contract.py \
  tests/unit/surrealdb/test_context_smoke_db_contracts.py -q
# 34 passed

ruff check + black --check on changed Python: PASS
```

---

## Operator proof (redacted)

**Command:** `make context-memory-db-proof`  
**Precondition:** `cdb_surrealdb` healthy (Up 7h); secrets via default `SECRETS_PATH`

| Step | Result |
|------|--------|
| `context-env-check` | PASS |
| `local_schema_check.py --hard-mode` | 18/18 tables OK |
| `memory_db_proof_cli run-proof --confirm` | `status: ok` |

**Envelope (summary):**

- `schema_version`: `memory-db-proof-runtime/v1`
- `run_id`: `20260529171902-20132` (run-scoped; cleaned up)
- `read_proof.source`: `surrealdb-local`, `record_count`: 2
- `stale_scan`: `fresh_count` 1, `expired_count` 1, `wave16_memory_ttl.finding_count` 1
- `approval_semantics`: read_only, no_write, no_live_go

No secrets in JSON output (manual spot-check).

---

## #2606 DoD delta

| Criterion | After #2603 |
|-----------|-------------|
| DB-backed read | PARTIAL (CI); **runtime PASS** via `context-memory-db-proof` |
| DB-backed stale scan | Same |
| Productive audit trail | BLOCKED |
| Claim at rest | PARTIAL → #2719 |
| Cross-session rediscovery | PARTIAL → #2720 |
| Epic closure | **BLOCKED** — #2606 stays OPEN |

---

## Out of scope (honored)

- No productive `PERSIST_ALLOWED` write path
- No MCP mutation
- No `ci.yml` SurrealDB step
- Untracked `knowledge_refresh_*` not staged
