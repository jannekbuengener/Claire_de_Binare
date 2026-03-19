# LR-003 Kill-Switch + Limit Controls Drill

- drill_id: `lr003_kill_switch_limit_controls`
- verdict: `PASS`
- passed: `7/7`

| Scenario | Verdict | Expected | Actual |
| --- | --- | --- | --- |
| `risk_kill_switch_active_blocks` | `PASS` | active=True, code=KILL_SWITCH_ACTIVE, reason=manual | active=True, code=KILL_SWITCH_ACTIVE, reason=manual |
| `risk_kill_switch_eval_error_fails_closed` | `PASS` | active=True, code=KILL_SWITCH_UNEVALUABLE, fail-closed message | active=True, code=KILL_SWITCH_UNEVALUABLE, message=kill-switch evaluation error: state file corrupt |
| `execution_kill_switch_active_blocks` | `PASS` | REJECTED before executor with persisted order_result | status=REJECTED, published=1, executor_calls=0 |
| `deny_max_notional` | `PASS` | {"decision": 0, "reason_codes": ["RC_LIMIT_NOTIONAL"]} | {"decision": 0, "reason_codes": ["RC_LIMIT_NOTIONAL"]} |
| `deny_max_exposure` | `PASS` | {"decision": 0, "reason_codes": ["RC_LIMIT_EXPOSURE"]} | {"decision": 0, "reason_codes": ["RC_LIMIT_EXPOSURE"]} |
| `deny_max_drawdown` | `PASS` | {"decision": 0, "reason_codes": ["RC_LIMIT_DRAWDOWN"]} | {"decision": 0, "reason_codes": ["RC_LIMIT_DRAWDOWN"]} |
| `allow_reduce_only_sell` | `PASS` | {"decision": 1, "reason_codes": []} | {"decision": 1, "reason_codes": []} |

Scope notes:
- Uses existing risk/execution kill-switch gates and the existing decision contract vectors.
- Read-only drill: no live endpoints, no exchange access, no state outside temporary kill-switch files.
- Fail-closed expectation: kill-switch evaluation error must block; limit vectors must keep exact deterministic outputs.
