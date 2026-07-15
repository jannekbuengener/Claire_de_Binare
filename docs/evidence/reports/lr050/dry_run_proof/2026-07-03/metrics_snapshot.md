# LR-050 Runtime Dry-Run — Metrics Snapshot

**Captured:** 2026-07-03T19:47:47Z UTC  
**Method:** Read-only `GET /metrics` and `GET /health` on local stack

## Service health

| Endpoint | Response |
|----------|----------|
| `http://127.0.0.1:8002/health` | `{"service":"risk_manager","status":"ok","version":"0.1.0"}` |
| `http://127.0.0.1:8003/health` | `{"service":"execution_service","status":"ok","version":"0.1.0"}` |
| `http://127.0.0.1:8006/health` | `{"service":"allocation_service","status":"ok","version":"1"}` |
| `http://127.0.0.1:8007/health` | `{"service":"candle_service","status":"ok","version":"1"}` |
| `http://127.0.0.1:8008/health` | `{"service":"regime_service","status":"ok",...}` |
| `http://127.0.0.1:8009/health` | `{"service":"market_data","status":"healthy"}` |

## Kill-switch reachability (GET only, no activation)

| Endpoint | Response |
|----------|----------|
| `http://127.0.0.1:8002/kill-switch` | `{"active":false,"activated_at":null,"reason":null,"message":"Deactivated by d4-teardown: delta4 verify done"}` |

Kill-switch endpoint reachable; state **inactive** at capture. No drill performed (out of scope for #2978).

## Execution metrics (`cdb_execution:8003/metrics`)

| Metric | Value |
|--------|-------|
| `execution_orders_received_total` | 0 |
| `execution_orders_filled_total` | 0 |
| `execution_orders_rejected_total` | 0 |
| `execution_invalid_payloads_total` | 0 |
| `execution_shadow_blocked_total` | 0 |
| `execution_uptime_seconds` | ~240990 |

## Risk metrics (`cdb_risk:8002/metrics`)

| Metric | Value |
|--------|-------|
| `orders_approved_total` | 0 |
| `orders_blocked_total` | 0 |
| `orders_skipped_total` | 0 |
| `order_results_received_total` | 0 |
| `orders_rejected_execution_total` | 0 |
| `risk_pending_orders_total` | 0 |
| `risk_kill_switch_active` | 0 |

## Redis stream envelope activity (read-only probe)

Probe executed inside `cdb_risk` container; password loaded via service secret path, **not** logged.

| Stream | Length |
|--------|--------|
| `stream.candles_1m` | 100017 |
| `stream.fills` | 10013 |
| `stream.orders` | *(present in key list)* |
| `stream.order_results` | *(present in key list)* |
| `stream.signals` | *(present in key list)* |
| `stream.regime_signals` | *(present in key list)* |
| `stream.allocation_decisions` | *(present in key list)* |
| `stream.orders_blocked` | *(present in key list)* |
| `stream.bot_shutdown` | 0 |

**Interpretation:** Pipeline streams are active; envelope/event bus operational under safe flags. Order counters at zero during capture window — consistent with risk-off regime (`HIGH_VOL_CHAOTIC`, `risk_off=True` in risk logs).

## Direct dry-run harness (local, non-stack)

```text
DRY RUN MODE - Orders will be logged but NOT executed!
DRY RUN: Would execute BTCUSDT BUY 0.001
order_id=DRY_RUN_UNKNOWN, status=FILLED, client_is_none=true
```

## Limitations

- Metrics are point-in-time; no injected synthetic order through full risk→execution path in this slice
- Regime service reports 1 consumer error (redis_connection_error) — noted, does not invalidate non-send proof
- Kill-switch latency/rollback drill deferred to #2984
