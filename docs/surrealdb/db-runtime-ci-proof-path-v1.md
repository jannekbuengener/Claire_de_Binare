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
| 1 | DB read proof | `memory_db_read_proof.py`; unit mocks; integration fixture adapter (`tests/integration/surrealdb/`); `tests/local/.../test_memory_db_read_proof.py` | Required CI: unit + integration fixtures; runtime: `local_only` + operator `make context-memory-db-proof` | Operator: `make context-memory-db-proof`; contracts in unit + integration tests | **PASS** (#2606 DoD reconcile 2026-05-31; live SurrealDB in required CI remains out of scope per #2603) |
| 2 | DB stale scan proof | `memory_db_stale_scan.py`; #2708 on main; integration fixture adapter | Same boundary as (1) | Same operator path | **PASS** (same reconcile as row 1) |
| 3 | Productive audit trail | Gate + local `audit_observation` only; spec [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md) (#2730); G1 [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) (#2735); G2 MCP [`productive-memory-audit-trail-mcp-phase2-design-v1.md`](productive-memory-audit-trail-mcp-phase2-design-v1.md) (#2739) | By design not activated | **DESIGN-READY (G1+G2 MCP) / NOT ACTIVATED** | **DESIGN-READY (G1+G2)**; runtime **NOT ACTIVATED** |
| 4 | Claim evidence at rest | `claim_evidence_at_rest.py`; unit mocks; optional `context-claim-evidence-proof` | CI: mocks only; runtime: local operator path | `make context-claim-evidence-proof`; see [`claim-evidence-at-rest-v1.md`](claim-evidence-at-rest-v1.md) | **PASS WITH LIMITS** — local operator path; CI **PARTIAL** |
| 5 | Cross-session rediscovery | `memory_cross_session_rediscovery.py`; manifest + subprocess prove | CI: mocks only; runtime: local operator | `make context-memory-rediscovery-proof`; see [`cross-session-memory-rediscovery-v1.md`](cross-session-memory-rediscovery-v1.md) | **PASS WITH LIMITS** — local two-process proof; CI **PARTIAL** |
| 6 | CI/runtime SurrealDB service | `context-smoke-db` needs Docker + secrets; not in `ci.yml` | Self-hosted `docker` label; optional workflow | `.github/workflows/surrealdb-memory-proof.yml` (`workflow_dispatch`, non-required); preflight + optional `make context-memory-db-proof` / `context-claim-evidence-proof` / `context-memory-rediscovery-proof`; manual fallback in runbook | **PASS WITH LIMITS** — opt-in GHA path; required CI stays mock-only |

---

## CI vs local boundaries

| Layer | What it proves | Required CI? |
|-------|----------------|--------------|
| Unit: `test_memory_db_read_proof.py`, `test_memory_db_stale_scan.py` | Tool contracts, mocks | Yes |
| Integration: `tests/integration/surrealdb/test_memory_db_*_fixture_adapter.py` | Read + stale against committed fixture rows via adapter (not MagicMock-only) | Yes |
| Unit: `test_local_runtime.py`, `test_memory_db_proof_runtime_contract.py` | Makefile targets, CLI, env parity, `local_schema_check` hard/soft | Yes |
| Unit: `test_context_smoke_db_contracts.py` | `context-smoke-db` recipe (#2460) | Yes |
| `make context-smoke-db` | Full context pipeline + DB write + query min-count | No (operator; ~26 min) |
| `make context-memory-db-proof` | Narrow read + stale on run-scoped fixtures | No (operator; minutes) |
| `make context-claim-evidence-proof` | Claim evidence at rest on run-scoped fixtures (#2719) | No (operator; minutes) |
| `make context-memory-rediscovery-proof` | Cross-session memory_id+scope rediscovery (#2720) | No (operator; minutes) |
| `pytest -m local_only` memory proof tests | Same as CLI cycle with env gate | No |
| `.github/workflows/surrealdb-memory-proof.yml` | Preflight + optional operator proofs on self-hosted Docker runner | No (opt-in `workflow_dispatch` only) |

**CI policy:** Do not add live SurrealDB to required `.github/workflows/ci.yml`.
Optional proof workflow: `surrealdb-memory-proof.yml` (#2721) — `continue-on-error: true`,
not a branch-protection required check.
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

## #2606 DoD delta (after #2603 + reconcile 2026-05-31)

| Criterion | Before #2603 | After #2603 | After DoD reconcile (#2/#3) |
|-----------|--------------|-------------|------------------------------|
| DB-backed read (#2606 §2) | PARTIAL (local_only only) | PARTIAL globally; operator PASS via `context-memory-db-proof` | **PASS** — unit contracts + required-CI integration fixture adapter + documented operator path; **no** live SurrealDB in `ci.yml` |
| DB-backed stale scan (#2606 §3) | PARTIAL (same) | Same pattern | **PASS** (same three-layer evidence) |
| Productive audit trail (#2606 §6) | BLOCKED (undocumented) | **DESIGN-READY / NOT ACTIVATED** (#2730) | **PASS** — HG-W governed proof path delivered via #2759 / PR #2763; `audit_observation_written=yes`, `agent_memory_written=yes`, rollback verified; `PERSIST_ALLOWED=False` remains fail-closed on `main` |
| Claim at rest (#2606 §8) | PARTIAL | PASS WITH LIMITS (#2719) | **PASS WITH LIMITS** (unchanged) |
| Cross-session rediscovery (#2606 §9) | PARTIAL | PASS WITH LIMITS (#2720) | **PASS WITH LIMITS** (unchanged) |
| Epic closure | BLOCKED | **still BLOCKED** | **NOT_CLOSURE_READY** — criterion #6 reconciled; remaining non-#6 rest axes still prevent full closure |

**Reconcile policy (ratified 2026-05-31):** #2606 criteria #2/#3 PASS is coupled to #2603 reality — operator path plus required-CI fixture-backed integration tests. Live SurrealDB in required CI is explicitly **not** a PASS blocker.

---

## References

- Runbook: [`docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md)
- Slice 1 audit: [`memory-reality-slice1-audit.md`](memory-reality-slice1-audit.md)
- Tools: `tools/surrealdb/memory_db_proof_runtime.py`, `memory_db_proof_cli.py`, `memory_db_proof_local_dev.py`
