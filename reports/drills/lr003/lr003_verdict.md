# LR-003 Kill-Switch + Limit Controls Verdict

- status: `PASS`
- generated_at: `2026-03-10T18:30:25.988473+00:00`
- scenario_count: `5`
- passed: `5`
- failed: `0`

| Scenario | Family | Status | Key observation |
|---|---|---|---|
| `risk_kill_switch_blocks_signal` | `kill_switch` | `PASS` | order_created=False, alert_code=KILL_SWITCH_ACTIVE, orders_blocked_total=1 |
| `execution_kill_switch_blocks_order` | `kill_switch` | `PASS` | executor_called=False, result_status=REJECTED, error_message=Order blocked: kill-switch active (risk_limit) |
| `exposure_limit_blocks_signal` | `limit_control` | `PASS` | order_created=False, alert_code=RISK_LIMIT, auto_unwind_checked=True, signals_blocked=1 |
| `drawdown_limit_triggers_shutdown` | `limit_control` | `PASS` | order_created=False, alert_code=CIRCUIT_BREAKER, shutdown_emitted=True, circuit_breaker_active=True |
| `execution_shutdown_blocks_order` | `shutdown` | `PASS` | executor_called=False, result_status=REJECTED, error_message=Order blocked by bot shutdown |

Scope boundary:
- This drill is repo-local and non-live.
- It verifies fail-closed control paths only; it does not trigger a real operator alert channel.
- Real operator alerting remains a separate drill/mechanism concern.
