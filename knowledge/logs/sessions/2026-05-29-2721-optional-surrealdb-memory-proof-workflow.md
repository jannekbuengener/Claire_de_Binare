# Session: #2721 optional SurrealDB memory proof workflow

**Date:** 2026-05-29  
**Base:** `origin/main` @ `bfac3758`  
**PR:** #2727  
**Merge SHA:** `6bc74f4f`  
**LR:** NO-GO (unchanged)  
**#2721:** CLOSED (via PR #2727)  
**#2606:** OPEN (NOT_CLOSURE_READY)

---

## Deliverables

| Item | Path / artifact |
|------|-----------------|
| Optional GHA workflow | `.github/workflows/surrealdb-memory-proof.yml` |
| Workflow shape tests | `tests/unit/scripts/test_surrealdb_memory_proof_workflow.py` (10 unit tests) |
| Proof matrix row 6 | `docs/surrealdb/db-runtime-ci-proof-path-v1.md` → **PASS WITH LIMITS** |
| Runbook section | `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md` — Optional GitHub Actions proof |

**Workflow behavior:**
- Trigger: `workflow_dispatch` only
- Runner: `[self-hosted, cdb, docker]`
- Permissions: `contents: read`
- Job: `continue-on-error: true` (non-required)
- Preflight: all three proof CLIs with `--confirm`
- Optional runtime: `make context-memory-db-proof`, `context-claim-evidence-proof`, `context-memory-rediscovery-proof`
- Artifacts: `proof_plan.json`, `summary.json`, `summary.md`, redacted logs

---

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/unit/scripts/test_surrealdb_memory_proof_workflow.py -v` | 10 passed (local pre-merge) |
| `git diff --check` | PASS |
| `ruff check` (touched test file) | PASS |
| PR #2727 `ci (Unit/Integration + Lint gesammelt)` | PASS |
| PR #2727 `policy-gate` | PASS |
| Self-hosted workflow_dispatch runtime proof | Not executed this session (opt-in operator step) |

---

## Boundaries (unchanged)

- No changes to required `ci.yml`
- No productive `agent_memory` write; `PERSIST_ALLOWED=False`
- No MCP mutation; no Auto-Memory; no BLUE/RED compose changes
- #2606 not closed; productive audit trail remains **BLOCKED**
- Board `trade-capable` ≠ LR GO

---

## #2606 DoD delta (row 6 only)

| Criterion | Before | After #2721 |
|-----------|--------|-------------|
| CI/runtime SurrealDB in required CI | PARTIAL (mock-only required CI) | Unchanged — required CI mock-only |
| Optional non-required GHA proof path | **NEEDS_FOLLOW_UP** | **PASS WITH LIMITS** — workflow landed; runtime proof depends on self-hosted secrets/Docker |
