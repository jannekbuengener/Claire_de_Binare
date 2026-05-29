# Session: #2606 campaign — #2719 claim evidence + #2720 cross-session rediscovery

**Date:** 2026-05-29  
**Base:** `origin/main` @ `a1453f38` (post-#2723 ledger)  
**PRs:** #2724, #2725  
**LR:** NO-GO (unchanged)  
**#2606:** OPEN (NOT_CLOSURE_READY)

---

## Deliverables

| Issue | PR | Merge SHA | Operator target |
|-------|-----|-----------|-----------------|
| #2719 Claim evidence at rest | #2724 | `d308bf6a` | `make context-claim-evidence-proof` |
| #2720 Cross-session rediscovery | #2725 | `0cc53336` | `make context-memory-rediscovery-proof` |

**Proof matrix:** [`docs/surrealdb/db-runtime-ci-proof-path-v1.md`](../../../docs/surrealdb/db-runtime-ci-proof-path-v1.md) rows 4–5 updated to **PASS WITH LIMITS** (local operator; CI unit/mock only).

**Docs:** `docs/surrealdb/claim-evidence-at-rest-v1.md`, `docs/surrealdb/cross-session-memory-rediscovery-v1.md`; runbook section in `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`.

---

## Verification (session)

| Check | Result |
|-------|--------|
| Unit: `test_claim_evidence_at_rest.py`, `test_claim_evidence_proof_runtime_contract.py` | PASS (Phase 1) |
| Unit: `test_memory_cross_session_rediscovery_contract.py` (5 tests) | PASS (Phase 2) |
| `ruff check` (touched files) | PASS |
| `black` (touched files) | Applied |
| PR #2724 CI (`ci`, `policy-gate`) | PASS → merged |
| PR #2725 CI (`ci`, `policy-gate`) | PASS → merged |
| Local SurrealDB operator proofs | Not re-run this close slice (optional `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1`) |

---

## GitHub

- #2719: closed (acceptance comment posted in campaign)
- #2720: closed (auto/merge-linked)
- #2606: campaign DoD delta comments; **not closed**
- #2721: referenced only — optional non-required CI SurrealDB workflow; not implemented

---

## Boundaries (unchanged)

- No productive `agent_memory` write; `PERSIST_ALLOWED=False`
- No MCP mutation; no Auto-Memory; no BLUE/RED compose changes
- Required `ci.yml` unchanged (no live SurrealDB in required CI)
- Board `trade-capable` ≠ LR GO

---

## Rest status after campaign

- **DONE_CAMPAIGN_MERGED** for #2719 + #2720 scope
- **#2606** remains OPEN: productive audit trail BLOCKED; #2721 follow-up; parent DoD audit #2705 not fully green for epic closure
