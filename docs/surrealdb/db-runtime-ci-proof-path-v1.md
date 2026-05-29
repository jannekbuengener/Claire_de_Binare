# DB Runtime / CI Proof Path v1 (#2603)

**Status:** Campaign deliverable  
**Epic:** [#2603](https://github.com/jannekbuengener/Claire_de_Binare/issues/2603)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (stays OPEN)  
**LR:** NO-GO (unchanged)  
**Board stage:** `trade-capable` is not live-go.

---

## Purpose

Formal proof-gap matrix for the six #2606 PARTIAL/BLOCKED axes, plus the smallest
reproducible operator path for DB-backed memory **read** and **stale scan** against
local SurrealDB (`127.0.0.1:8010`), with CI-safe unit/contract tests that do not
require a live database in the required `ci` job.

**Non-goals:** productive `agent_memory` write; MCP mutation; Auto-Memory; BLUE/RED
compose changes; closing #2606; SurrealDB in required CI (~26 min `context-smoke-db`).

---

## Proof-gap matrix (#2606 restgaps)

| # | Restgap | Current evidence | CI / runtime today | #2603 target | Decision |
|---|---------|------------------|-------------------|--------------|----------|
| 1 | DB read proof | `memory_db_read_proof.py`; unit mocks; `tests/local/.../test_memory_db_read_proof.py` | CI: mocks only; runtime: `local_only` + `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1` | Operator: `make context-memory-db-proof`; contracts in unit tests | **IMPLEMENTABLE_NOW** — local PASS path; CI stays **PARTIAL** |
| 2 | DB stale scan proof | `memory_db_stale_scan.py`; #2708 on main | Same boundary as (1) | Same operator path | **IMPLEMENTABLE_NOW** — local PASS path; CI **PARTIAL** |
| 3 | Productive audit trail | Gate + local `audit_observation` only | By design blocked | Document **BLOCKED** | **BLOCKED** (no activation) |
| 4 | Claim evidence at rest | `claim_evidence_at_rest.py`; unit mocks; optional `context-claim-evidence-proof` | CI: mocks only; runtime: local operator path | `make context-claim-evidence-proof`; see [`claim-evidence-at-rest-v1.md`](claim-evidence-at-rest-v1.md) | **PASS WITH LIMITS** — local operator path; CI **PARTIAL** |
| 5 | Cross-session rediscovery | Depends on (1); `memory_id`+`scope` in helpers | Not CI-proven across sessions | Follow-up #2720 | **NEEDS_FOLLOW_UP** (until #2720 lands) |
| 6 | CI/runtime SurrealDB service | `context-smoke-db` needs Docker + secrets; not in `ci.yml` | Self-hosted `docker` label; no SurrealDB step | Document boundary; optional non-required workflow | **NEEDS_FOLLOW_UP** |

---

## CI vs local boundaries

| Layer | What it proves | Required CI? |
|-------|----------------|--------------|
| Unit: `test_memory_db_read_proof.py`, `test_memory_db_stale_scan.py` | Tool contracts, mocks | Yes |
| Unit: `test_local_runtime.py`, `test_memory_db_proof_runtime_contract.py` | Makefile targets, CLI, env parity, `local_schema_check` hard/soft | Yes |
| Unit: `test_context_smoke_db_contracts.py` | `context-smoke-db` recipe (#2460) | Yes |
| `make context-smoke-db` | Full context pipeline + DB write + query min-count | No (operator; ~26 min) |
| `make context-memory-db-proof` | Narrow read + stale on run-scoped fixtures | No (operator; minutes) |
| `make context-claim-evidence-proof` | Claim evidence at rest on run-scoped fixtures (#2719) | No (operator; minutes) |
| `pytest -m local_only` memory proof tests | Same as CLI cycle with env gate | No |

**CI policy:** Do not add live SurrealDB to required `.github/workflows/ci.yml`.
Canonical gate remains `pytest -q -k "not test_mcp_time_server_runtime"`.

---

## Operator commands

Prerequisites: `make context-up`, secrets with `SURREALDB_ENV`, query config at
`infrastructure/config/surrealdb/context_query.local.yaml`.

```bash
make context-env-check
make context-memory-db-proof
```

Equivalent CLI (explicit operator GO without env typo):

```bash
python -m tools.surrealdb.memory_db_proof_cli preflight --confirm
python -m tools.surrealdb.memory_db_proof_cli run-proof --confirm
```

Optional env instead of `--confirm`:

```bash
export CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1
pytest -m local_only tests/local/surrealdb/test_memory_db_read_proof.py \
  tests/local/surrealdb/test_memory_db_stale_scan.py -q
```

---

## Target comparison

| Target | Proves |
|--------|--------|
| `make context-smoke-db` | Full context import + `show-snapshot` (heavy; #2460 infra) |
| `make context-memory-db-proof` | #2606 read + stale on `memory_db_proof` fixtures only |

---

## #2603 epic-body reconcile (stale on GitHub)

On `main` as of campaign merge:

- `make context-smoke-db` — **delivered** (#2460 / #2677)
- `tests/unit/surrealdb/test_context_smoke_db_contracts.py` — **delivered**
- `make context-memory-db-proof` + this doc — **#2603 campaign**

---

## #2606 DoD delta (expected after #2603)

| Criterion | Before | After #2603 |
|-----------|--------|-------------|
| DB-backed read | PARTIAL (local_only only) | PARTIAL globally; **runtime PASS** via `context-memory-db-proof` |
| DB-backed stale scan | PARTIAL (same) | Same pattern |
| Productive audit trail | BLOCKED | BLOCKED |
| Claim at rest | PARTIAL | PARTIAL + follow-up |
| Cross-session rediscovery | PARTIAL | PARTIAL + follow-up |
| Epic closure | BLOCKED | **still BLOCKED** |

---

## References

- Runbook: [`docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md)
- Slice 1 audit: [`memory-reality-slice1-audit.md`](memory-reality-slice1-audit.md)
- Tools: `tools/surrealdb/memory_db_proof_runtime.py`, `memory_db_proof_cli.py`, `memory_db_proof_local_dev.py`
