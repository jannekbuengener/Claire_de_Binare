# Primary Breakout V1 Validation Canon

Purpose: define the minimal canonical validation surface for `primary_breakout_v1`.

Scope boundary:
- This defines metrics, report schema, and pass/fail thresholds for deterministic historical validation.
- Input bridge comes from `#1583`.
- Report population comes from the runner scope in `#1584`.
- No runtime, paper, or shadow operationalization is defined here.

## Canonical Metrics

Required metric set:
- `signals_total`
- `buy_signals_total`
- `sell_signals_total`
- `closed_trades_total`
- `win_rate` (0..1)
- `profit_factor`
- `expectancy_r`
- `max_drawdown_r`
- `market_state_fresh_ratio` (0..1)
- `regime_fresh_ratio` (0..1)
- `data_integrity_ok`
- `deterministic_replay_ok`

Rationale:
- Keep the set small, auditable, and directly tied to strategy behavior and data quality.
- Do not expand to research-heavy scorecards in v1.

## Machine-readable Report Contract

Contract file:
- `docs/contracts/strategy_validation_report_v1.schema.json`

Mandatory top-level sections:
- `schema_version`
- `strategy_id`
- `run_metadata`
- `config_snapshot`
- `dataset_summary`
- `metrics`
- `thresholds_applied`
- `gate_result`

Fail-closed contract posture:
- strict required fields
- strict enums/const values where canonical
- `additionalProperties: false` for all major objects

## Pass/Fail and Review Criteria

Threshold profile:
- `docs/evidence/primary_breakout_v1_validation_thresholds.json`

PASS/FAIL minimums:
- `closed_trades_total >= 20`
- `profit_factor >= 1.05`
- `expectancy_r >= 0.0`
- `max_drawdown_r <= 3.0`
- `market_state_fresh_ratio >= 0.99`
- `regime_fresh_ratio >= 0.99`
- `data_integrity_ok == true`
- `deterministic_replay_ok == true`

Review-only warnings (non-blocking if pass/fail is green):
- `closed_trades_total < 40`
- `profit_factor < 1.2`
- `max_drawdown_r > 2.0`

Decision mapping:
- FAIL: at least one pass/fail rule violated.
- REVIEW: pass/fail rules satisfied, but at least one review-only rule violated.
- PASS: pass/fail and review-only rules all satisfied.

## Explicitly Non-canonical for V1 Gate Core

The following are not canonical gate metrics in v1:
- `cagr`
- `sharpe_ratio`
- `sortino_ratio`
- `calmar_ratio`
- `mar_ratio`
- `pnl_usd_absolute`

These may be informative in research notes, but they do not decide v1 gate outcome.

## Dataset Summary — Period Window Semantics

The `dataset_summary` block distinguishes two timestamp boundaries:

| Field | Meaning |
|---|---|
| `requested_period_start_ts_ms` | First candle `ts_ms` in the raw input series passed to the runner |
| `requested_period_end_ts_ms` | Last candle `ts_ms` in the raw input series passed to the runner |
| `period_start_ts_ms` | First **effective** bridge evaluation timestamp — after warm-up consumption of `max(entry_lookback_minutes, exit_lookback_minutes)` candles |
| `period_end_ts_ms` | Last effective bridge evaluation timestamp (aligns with `requested_period_end_ts_ms`) |

With default config (`entry_lookback_minutes=240`, `exit_lookback_minutes=120`), the effective
period start is offset by exactly `240 × 60,000 ms = 14,400,000 ms` from the requested start.
This offset is expected and is not a data error — it reflects the warm-up window consumed by the
bridge before the first evaluable candle.
