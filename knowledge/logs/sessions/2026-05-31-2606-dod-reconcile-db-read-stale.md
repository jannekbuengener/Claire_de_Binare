# Session Log — #2606 DoD Reconcile (#2/#3 DB read/stale)

**Date:** 2026-05-31  
**Scope:** DoD reconcile for #2606 criteria DB-backed read + DB stale scan  
**LR:** NO-GO  
**Branch:** `docs/2606-dod-reconcile-db-read-stale`

---

## Goal

Ratify PASS for #2606 criteria #2/#3 per #2603 reality: required-CI unit +
integration fixture adapter + documented operator path. No live SurrealDB in
required `ci.yml`. Epic stays OPEN (NOT_CLOSURE_READY).

---

## Hygiene

- **#2606 reopened** after false close via PR #2755 `closingIssuesReferences`
  (comment on issue 2026-05-31).
- Future docs PRs: no closing keyword for #2606.

---

## Delivered

1. **Integration tests** (required CI):
   - `tests/integration/surrealdb/memory_db_proof_fixture_helpers.py`
   - `tests/integration/surrealdb/test_memory_db_read_proof_fixture_adapter.py`
   - `tests/integration/surrealdb/test_memory_db_stale_scan_fixture_adapter.py`
   - Fixtures: `tests/fixtures/surrealdb/memory_db_proof/agent_memories.jsonl`

2. **Docs:**
   - `docs/surrealdb/db-runtime-ci-proof-path-v1.md` — matrix rows 1–2, CI layer,
     `#2606 DoD delta` reconcile section
   - `docs/surrealdb/memory-reality-slice1-audit.md` — § addendum 2026-05-31

3. **Ledger:** `CURRENT_STATUS.md`, #2606 GitHub body refresh

---

## Validation (local)

```text
pytest tests/integration/surrealdb/test_memory_db_read_proof_fixture_adapter.py \
  tests/integration/surrealdb/test_memory_db_stale_scan_fixture_adapter.py -q
# 2 passed
```

---

## Operator proof (context-memory-db-proof)

**Attempted:** 2026-05-31 — `make context-env-check` PASS; `make context-memory-db-proof` **FAIL**
(exit 6).

**Redacted summary:**

- Schema check: 18/18 v0 tables present on local context sidecar (127.0.0.1:8010).
- Run-scoped seed: `agent_memory` creates applied (2); `evidence_ref` creates **failed**
  (schema: `scope` field not on table — pre-existing importer/schema drift).
- Read+stale proof step did not complete; operator refresh **not** re-proven this session.

**Reconcile evidence:** Required-CI integration fixture tests (2 passed) + prior #2603
operator PASS (2026-05-29). No fake PASS claimed for operator refresh.

---

## DoD matrix (reconcile)

| Criterion | Before | After |
| --- | --- | --- |
| #2 DB-backed read | PARTIAL | **PASS** (reconciled) |
| #3 DB stale scan | PARTIAL | **PASS** (reconciled) |
| #6 production-auditable write | PASS WITH LIMITS | **PASS WITH LIMITS** (unchanged) |
| #8 claim at rest | PASS WITH LIMITS | **PASS WITH LIMITS** (unchanged) |
| #9 cross-session | PASS WITH LIMITS | **PASS WITH LIMITS** (unchanged) |

**Epic close:** No — strict DoD blockers #6/#8/#9 remain.

---

## Boundaries

- `PERSIST_ALLOWED=False` unchanged
- No MCP mutation, no BLUE/RED, no T3 re-proof, no productive `agent_memory` write
- No live SurrealDB added to required CI

---

## Non-goals

- Epic closure
- #2747/G3c re-run
- Strict PASS for #6/#8/#9
