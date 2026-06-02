# Session: #2801 Operator Certification Usage

Date: 2026-06-02
Issue: #2801
PR: #2808 (merged)
Merge SHA: 171bd74f8af21c6123e53a6171f8fe289f2c66f8

## Scope

Integrate optional `context-certify` proof pack as adoption signal in `evaluate_agent_os_readiness_v1`; document PASS/WARN/FAIL/BLOCKED/SKIPPED semantics.

## Delivered

- `_evaluate_operator_certification` in `tools/surrealdb/agent_os_readiness.py`
- Bundle keys: `operator_certification` (primary), `context_certification` (alias)
- Docs: `docs/runbooks/surrealdb_context_mcp_access.md`, `docs/surrealdb/context-wave20-agent-os-readiness-runbook.md`
- Unit + MCP passthrough tests

## Review fixes (69d68805)

- P2 r3338352561: non-blocking gate failures + `adoption_status=warn` append `required_validation`
- P2 r3338368803: `adoption_status=pass` without `final_verdict` no longer silent green

## Validation

- `pytest -q tests/unit/surrealdb/test_agent_os_readiness.py tests/unit/tools/mcp/test_agent_os_readiness_tools.py` → 78 passed
- CI required: `ci`, `policy-gate` green on merge
- `make context-certify` → certified (local, non-blocking)

## Boundaries

- No productive DB/MCP mutations; LR NO-GO unchanged
- Certification = adoption gate, not LR-Go

## Follow-ups

- #2778 progress comment posted; #1976 remains open
