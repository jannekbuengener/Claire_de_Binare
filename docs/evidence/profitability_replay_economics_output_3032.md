# CDB Profitability -- Replay Economics Output #3032

**Date:** 2026-06-12
**Parent:** #3032
**Issue:** #3148
**Refs:** #3147, #3145, #3143, #3141
**Status:** Complete -- replay economics output extended with 14 new fields

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git switch`, `gh issue create`, `python -m services.validation.strategy_replay_runner`, Python JSON |
| `records_or_results` | Extended `_build_report()` in strategy_backtest_runner.py with 14 new economics fields. Replay verified: all fields present, deterministic_replay_ok=True. Fee-adjusted metrics: net_pnl_quote=-1217.31 USDT, fee_adj_profit_factor=0.425, fee_adj_expectancy_r=-0.00475. |
| `repo_crosscheck` | `services/validation/strategy_backtest_runner.py:_build_report` (lines 604-644 expanded), `docs/contracts/replay_report.v1.schema.json` (metrics field unconstrained) |
| `impact_on_plan` | Evidence packets can now consume 14 additional economics fields from any replay run. No more manual JSON post-processing needed. sample_size_verdict marks 4 trades as "insufficient". |
| `limitations` | No SurrealDB/Context Brain. Equity curve and Sharpe still unavailable (need per-bar NAV tracking). Per-trade slippage breakdown not exposed. |

## Scope and Non-goals

### In scope
- Add machine-readable economics fields to the replay backtest report output.
- Compute fee-adjusted trade returns, gross/net PnL in quote currency, per-trade win/loss breakdown.
- Add `metrics_availability` and `sample_size_verdict` fields for honest evidence assessment.
- Update economics summary JSON with the new fields from a replay run.
- Keep all changes in a single file (`strategy_backtest_runner.py`).

### Non-goals
- No strategy behavior change. Existing metrics unchanged.
- No production config change.
- No runtime, DB, Docker.
- No Live-Go, Echtgeld-Go, LR status change.
- No equity curve or Sharpe ratio (needs deeper architecture).
- No per-trade slippage exposure (needs execution simulator change).

## Replay Output Surface

### Before (#3147)
The `metrics` dict in replay `report.json` contained 13 fields:

| Field | Source |
|-------|--------|
| `signals_total`, `buy/sell_signals_total`, `closed_trades_total` | Counts |
| `win_rate`, `profit_factor`, `expectancy_r`, `max_drawdown_r` | Pre-fee r-returns |
| `market_state_fresh_ratio`, `regime_fresh_ratio` | Freshness ratios |
| `data_integrity_ok`, `data_integrity_diagnostics` | Integrity check |
| `deterministic_replay_ok` | Two-pass determinism |

**Missing:** gross return, net PnL, fees total, fee-adjusted metrics, win/loss breakdown, sample size assessment, availability metadata. Evidence packet v2 (#3147) had to mark these as `null` or `0.0` and manually explain unavailability.

### After (this PR)
14 new fields added to the same `metrics` dict:

| Field | Type | Description |
|-------|------|-------------|
| `gross_return_r` | float | Cumulative sum of all trade r_returns |
| `avg_win_r` | float\|null | Average r_return of winning trades |
| `avg_loss_r` | float\|null | Average r_return of losing trades |
| `largest_win_r` | float\|null | Largest single trade winning r_return |
| `largest_loss_r` | float\|null | Largest single trade losing r_return |
| `trades_win_count` | int | Count of winning trades |
| `trades_loss_count` | int | Count of losing trades |
| `gross_pnl_quote` | float | Sum of (exit-entry)*order_size across all trades (USDT) |
| `net_pnl_quote` | float | `gross_pnl_quote - fees_total_quote` |
| `fees_total_quote` | float | Sum of entry_fee + exit_fee across all trades (USDT) |
| `fee_adjusted_expectancy_r` | float\|null | Expectancy after subtracting fees from returns |
| `fee_adjusted_profit_factor` | float\|null | Profit factor on fee-adjusted returns |
| `fee_adjusted_max_drawdown_r` | float\|null | Max drawdown on fee-adjusted cumulative returns |
| `sample_size_verdict` | string | `no_trades`, `insufficient` (<5), `weak` (<30), `usable` (<100), `adequate` (100+) |

Plus a `metrics_availability` dict with availability flags and explanatory notes for unavailable fields (equity curve, Sharpe, slippage breakdown, absolute drawdown in quote).

### Implementation Location

Single file change: `services/validation/strategy_backtest_runner.py`, function `_build_report()`.

All new fields are computed from data already in memory (the `trades` list and `run_config.order_size`). No new data collection, no cross-module changes, no schema changes.

The replay reporter (`ReplayReporter`) and replay schema (`replay_report.v1.schema.json`) accept arbitrary keys in the `metrics` dict -- no change needed.

## Calibrated Variant Run

Variant: `atr_p75_61.82` (ATR=61.82, p75 of BTCUSDT distribution). Same variant as in #3147.

### Replay Result
- `run_id`: `replay-00126958cf0e-0001`
- `deterministic_replay_ok`: True
- `gate_result`: FAIL (as expected for 4 trades)

### New Economics Fields (Actual Values)

| Field | Pre-fee | Fee-adjusted |
|-------|---------|-------------|
| gross_return_r / cum. return | -0.01422 | n/a |
| expectancy_r | -0.00355 | -0.00475 |
| profit_factor | 0.517 | 0.425 |
| max_drawdown_r | 0.0230 | 0.0230 |
| gross_pnl_quote | -918.03 USDT | n/a |
| net_pnl_quote | n/a | -1217.31 USDT |
| fees_total_quote | n/a | 299.28 USDT |

### Fee Impact
Fees (299.28 USDT on 4 trades) represent ~33% of gross loss. Including fees changes profit factor from 0.517 to 0.425 -- a meaningful difference that justifies computing fee-adjusted metrics.

## Sample Size Gate

| Verdict | `insufficient` |
|---------|----------------|
| Trades | 4 (1 win, 3 losses) |
| Threshold | < 5 → `insufficient` |
| Next threshold | < 30 → `weak` |

**4 trades over 58h is insufficient for any economic conclusion.** The profit factor 0.517 (or 0.425 fee-adjusted) at 4 trades tells us nothing about strategy profitability. At this trade count, any profit factor from 0.1 to 10.0 is statistically plausible by random chance.

## Decision

### What Was Achieved
1. **14 new economics fields** added to the replay backtest pipeline output.
2. **Fee-adjusted returns** now computed alongside pre-fee returns.
3. **`metrics_availability`** field provides honest documentation of what is and isn't computable.
4. **`sample_size_verdict`** automates the "too few trades" assessment.
5. All fields available in `report.json` from every future replay run -- no manual post-processing needed.
6. Evidence packet economics summary updated with real computed values.

### What Was NOT Changed
- Strategy logic (unchanged).
- Production config (unchanged).
- Execution simulator (unchanged).
- Gate evaluation (unchanged).
- Existing metrics (`profit_factor`, `expectancy_r`, etc.) unchanged in computation and value.

### Verdict

| Dimension | Assessment |
|-----------|------------|
| Economic viability | `UNKNOWN` (4 trades insufficient) |
| Evidence readiness | `BLOCKED_BY_DATASET_LENGTH` |
| Pipeline completeness | `IMPROVED` (14 new fields, fee-adjusted) |
| Next blocker | Longer BTCUSDT MEXC dataset |

## Follow-ups

| Priority | Title | Note |
|----------|-------|------|
| High | Acquire longer BTCUSDT MEXC dataset | >1 week, >10k candles. Only blocker for meaningful economics. |
| Medium | Add per-bar equity curve + Sharpe | Needs deeper architecture: per-bar NAV tracking in deterministic loop. |
| Low | Expose per-trade slippage breakdown | Needs execution simulator to surface slippage_bps per fill. |
| Low | Entry/exit timestamps -> holding period stats | Trade dict already has timestamps; just need aggregation in _build_report. |

## Produced Artifacts

| File | Change |
|------|--------|
| `services/validation/strategy_backtest_runner.py` | +~60 lines in `_build_report()` |
| `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_3091_calibrated.json` | Updated with new fields from replay-00126958cf0e-0001 |
| `docs/evidence/profitability_replay_economics_output_3032.md` | This file (new) |

## Safety Boundaries

- LR remains NO-GO.
- Board `trade-capable` stage does not authorize live capital.
- No Live-Go, no Echtgeld-Go.
- No strategy behavior change. Existing metrics unchanged.
- No production config, schema, runtime, DB, or Docker changes.
- All new fields are computed from existing data only (no new data collection).
- Fee-adjusted metrics are additive (existing pre-fee metrics remain available).
- `sample_size_verdict` is informational, not a gate.

## Ref Issues

- #3148 -- This issue (replay economics output)
- #3032 -- Parent: Profitability Engine
- #3147 -- Calibrated evidence packet v2
- #3145 -- BTCUSDT regime calibration analysis
- #3143 -- Regime-assigned MEXC replay
- #3141 -- First evidence packet (v1)
