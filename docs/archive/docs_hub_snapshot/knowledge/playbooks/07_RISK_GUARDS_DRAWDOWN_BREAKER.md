# Risk Guards — Drawdown + Circuit Breaker (2025-12-25)

## TL;DR
Model-only ist wertlos. Guards müssen **in service integration** enforced werden + E2E Guard-Cases (#230). #226 liefert deterministischen Reset + Disable Option.

## Minimal Contract
### Drawdown Guard
- Track: `equity`, `peak_equity`
- Formula: `(peak - equity) / peak`
- Threshold: `MAX_DRAWDOWN_PCT` (env/config)

### Circuit Breaker
- Trigger: configurable (z.B. consecutive failures)
- Disable: `CIRCUIT_BREAKER_ENABLED=true|false`
- Reset: deterministisch (explicit flag oder event-time based)

## Required Integration Points (services/risk/service.py)
In `handle_order_result()`:
- On FILLED → `risk_state.apply_fill(...)` + equity update
- On REJECTED/ERROR → `risk_state.record_execution_failure(...)`
- On SUCCESS → `risk_state.record_execution_success()`

In signal evaluation / gating:
- If `circuit_breaker_active` → block
- If `current_drawdown_pct > MAX_DRAWDOWN_PCT` → block

## Required E2E Tests (tests/e2e/test_paper_trading_p0.py)
- TC-P0-003: drawdown guard blocks subsequent orders
- TC-P0-004: circuit breaker triggers and latches

## Verify (local)
```powershell
python -m pytest -q tests/unit/risk/test_guards.py -vv
E2E_RUN=1 pytest tests/e2e/test_paper_trading_p0.py -v --no-cov
```
