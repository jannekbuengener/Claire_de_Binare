# Session — Research Validation Security Gates (#4271)

**Date:** 2026-08-01  
**Issue:** #4271 (Parent #4263)  
**Mode:** Delivery slice (no merge, no issue close)  
**Branch:** `cloud-cursor/research-security-provenance-gates-4271-7268`  
**Base:** `origin/main` @ `6ac6b767f0f57d6c0e795fab81da8b2b1d2ebe1e`

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: tool_blocked
context_tool_status: blocked
context_trust_level: none
records_found: none
```

`cdb_context` MCP failed during live tool discovery.

## Router

```text
routing_decision: CREATE_DEDICATED_PR
lane: runtime-risk
reason_codes: [DEDICATED_RULE_MATCH]
target_branch_recommended: dedicated/runtime-risk-issue-4271
```

Cloud-agent branch policy used `cloud-cursor/research-security-provenance-gates-4271-7268`.

## Delivered

- Canon: `docs/research/CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md`
- Schema + fixture: `cdb.research_security_gate.v1`
- Cross-contract: `tools/research_validation/security_gates_cross_contract.py`
- Tests: `tests/unit/contracts/test_research_validation_security_gates.py`
- Canon/inventory link updates

## Validation

- `pytest` security + wave1 + wave2: 94 passed
- `ruff check` / `black --check` on touched Python: PASS
- `git diff --check`: clean

## Boundaries

- No merge, no issue close
- No scanner execution, no secrets access, no runtime/trading changes
- LR NO-GO unchanged
