# Runtime Risk Guards

Note: PSM is not wired yet; the risk manager uses a local equity fallback (mark-to-market from last fill prices). This is interim only and not the canonical financial source of truth.

Env (defaults + meaning):
```
RISK_NAMESPACE=                          # optional prefix for risk streams/state keys
RISK_STATE_KEY=risk_state                # Redis key for persisted risk state
RISK_RESET_STREAM=stream.risk_reset      # operator-only reset stream
MAX_DAILY_DRAWDOWN_PCT=0.05              # drawdown threshold (fraction)
MAX_BOT_EXPOSURE_PCT=0.30                # bot exposure cap (fraction)
MAX_SYMBOL_EXPOSURE_PCT=0.10             # symbol exposure cap (fraction)
CIRCUIT_MAX_CONSECUTIVE_FAILURES=3       # trigger after consecutive execution failures
CIRCUIT_MAX_FAILURES_PER_WINDOW=5        # trigger after failures per window
CIRCUIT_FAILURE_WINDOW_SEC=3600          # sliding window in seconds
CIRCUIT_COOLDOWN_SEC=0                   # auto-reset cooldown (0=disabled)
```

Mini-runbook (operator-only):
Use `redis-cli XADD stream.risk_reset * reset_type all` to clear latched circuit breaker/shutdown state; do not expose this stream to automated writers. To detect a latched circuit breaker, check `GET /status` on the risk service and inspect `risk_state.circuit_breaker`, `risk_state.circuit_breaker_reason`, and `risk_state.circuit_breaker_triggered_at` (execution will reject orders with BOT_SHUTDOWN while latched).
