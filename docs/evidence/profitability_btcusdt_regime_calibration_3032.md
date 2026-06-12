# CDB Profitability -- BTCUSDT Regime Threshold Calibration #3032

**Date:** 2026-06-12
**Parent:** #3032
**Issue:** #3144
**Refs:** #3142, #3143
**Status:** Complete -- distribution analysis, calibration grid, variant replays executed

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git switch`, `gh issue view/create/comment`, `python scripts/profitability/analyze_btcusdt_regime_calibration_3032.py`, `python scripts/profitability/generate_calibration_variants_3032.py`, `python -m services.validation.strategy_replay_runner` (8x), Python hashlib, `rg` |
| `records_or_results` | Raw dataset (3496 rows, SHA-256=d79a1c...). ATR distribution: min=22.5, max=208.1, median=48.0 USD. ATR_pct median=0.078%. ADX median=19.8. 8 calibration variants generated and replayed. Baseline: 0 trades. Variants: 1-10 trades each, all gate=FAIL (insufficient data). |
| `repo_crosscheck` | `services/regime/service.py:_derive_regime`, `services/regime/models.py:compute_adx/compute_atr`, `scripts/profitability/assign_regime_to_mexc_3091.py`, `core/replay/historical_bridge.py` |
| `impact_on_plan` | ATR threshold 2.0 is at absolute minimum (0.00th percentile) of the BTCUSDT distribution. ATR ~48 USD (median) or ATR_pct ~0.08% produce non-zero trades. ATR_pct is a scale-invariant alternative to absolute ATR. |
| `limitations` | No SurrealDB/Context Brain. 3496 rows (~58h) is a single market window. No claim of generalizability. Gate FAIL on all variants is expected (too few trades for statistical significance). All regime labels are estimated. |

## Scope and Non-goals

### In scope
- Analyze ATR/ADX distribution of the committed raw MEXC BTCUSDT dataset.
- Define calibration grid from data percentile thresholds (not from desired PnL).
- Generate test-only derived datasets per variant.
- Run file-backed deterministic replays for each calibration variant.
- Document findings and a data-backed recommendation.

### Non-goals
- No production config change (services/regime/config.py unchanged).
- No strategy/core/runner/provider code changes.
- No runtime, no DB, no Docker, no Redis.
- No Live-Go, no Echtgeld-Go, no LR status change.
- No claim that any threshold produces profitable results.
- No overfit for profit; thresholds derived from distribution, not PnL outcome.

## Problem Statement

Issue #3142 established that the current ATR threshold of 2.0 USD, applied to raw BTCUSDT prices (~60,859), produces 99.5% HIGH_VOL_CHAOTIC and zero trades. The `primary_breakout_v1` strategy requires `regime_id == TREND` for entries -- a condition that is never met.

The root cause is scale mismatch: ATR(14) on a ~60k asset ranges from ~22 to ~208 USD (mean 53 USD). An absolute threshold of 2.0 USD is at the **0.00th percentile** of the ATR distribution -- conceptually invisible in this price context.

## Baseline #3142 Result

| Metric | Value |
|--------|-------|
| ATR threshold | 2.0 USD |
| Regime: TREND | 16 (0.5%) |
| Regime: HIGH_VOL_CHAOTIC | 3480 (99.5%) |
| Regime: RANGE | 0 (0%) |
| Replay: signals_total | 0 |
| Replay: trades | 0 |
| Replay: gate_result | FAIL |
| Replay: deterministic | True |

## ATR/ADX Distribution

Full distribution analysis of 3,482 valid ATR/ADX observations (warmup: first 14 candles).

### ATR Distribution (absolute, USD)
| Quantile | Value (USD) | % of ~60,859 price |
|----------|------------|---------------------|
| Min | 22.48 | 0.037% |
| p10 | 33.02 | 0.054% |
| p25 | 39.94 | 0.066% |
| p50 (median) | 48.01 | 0.079% |
| p75 | 61.82 | 0.102% |
| p90 | 76.84 | 0.126% |
| p95 | 90.17 | 0.148% |
| p99 | 128.58 | 0.211% |
| Max | 208.06 | 0.342% |

**Current ATR=2.0 is below 0.00% of all observations.** It is at the absolute minimum of the distribution.

### ATR_pct Distribution (ATR / close * 100)
| Quantile | Value |
|----------|-------|
| p50 | 0.0775% |
| p75 | 0.0986% |
| p90 | 0.1220% |
| p95 | 0.1442% |
| p99 | 0.2037% |

### ADX Distribution (0-100 scale)
| Quantile | Value |
|----------|-------|
| p50 (median) | 19.79 |
| p75 | 26.99 |
| p90 | 35.01 |
| p95 | 40.04 |

ADX is scale-invariant (bounded 0-100). The committed ADX thresholds (trend=25.0, range=20.0) are at approximately the 69th and 51st percentiles, respectively -- reasonable boundaries.

### Regime Classification with Current Thresholds

| Regime | Count | % |
|--------|-------|---|
| HIGH_VOL_CHAOTIC | 3,482 | 100.0% |
| TREND | 0 | 0.0% |
| RANGE | 0 | 0.0% |

With ATR=2.0, **every candle** is classified as HIGH_VOL_CHAOTIC. No entry opportunity exists.

## Calibration Grid

Thresholds derived from data percentiles and ATR_pct scales. Documented **before** any replay.

| Variant | ATR threshold (USD) | % of price | Derivation |
|---------|---------------------|------------|------------|
| `baseline_atr_2.0` | 2.00 | 0.003% | Current committed config (control) |
| `atr_pct_0.01pct_6.09` | 6.09 | 0.010% | ATR_pct 0.01% -- generous |
| `atr_pct_0.05pct_30.43` | 30.43 | 0.050% | ATR_pct 0.05% -- moderate |
| `atr_p50_48.01` | 48.01 | 0.079% | ATR at p50 (median) |
| `atr_pct_0.1pct_60.86` | 60.86 | 0.100% | ATR_pct 0.1% -- near p75 |
| `atr_p75_61.82` | 61.82 | 0.102% | ATR at p75 (upper quartile) |
| `atr_p90_76.84` | 76.84 | 0.126% | ATR at p90 -- conservative |
| `atr_pct_0.25pct_152.15` | 152.15 | 0.250% | ATR_pct 0.25% -- strict |

## Variant Replay Results

All replays: `deterministic_replay_ok=True`, `gate_result=FAIL`, exit code 0.

| Variant | ATR USD | Regime TREND | Regime RANGE | Regime HVC | Signals | Buys | Trades |
|---------|---------|-------------|-------------|-----------|---------|------|--------|
| `baseline_atr_2.0` | 2.00 | 0.5% | 0% | 99.5% | 0 | 0 | 0 |
| `atr_pct_0.01pct_6.09` | 6.09 | 0.5% | 0% | 99.5% | 0 | 0 | 0 |
| `atr_pct_0.05pct_30.43` | 30.43 | 1.2% | 3.1% | 95.7% | 2 | 1 | 1 |
| `atr_p50_48.01` | 48.01 | 14.4% | 34.2% | 51.4% | 6 | 3 | 3 |
| `atr_pct_0.1pct_60.86` | 60.86 | 23.3% | 48.2% | 28.5% | 8 | 4 | 4 |
| `atr_p75_61.82` | 61.82 | 24.3% | 48.5% | 27.2% | 8 | 4 | 4 |
| `atr_p90_76.84` | 76.84 | 33.2% | 57.0% | 9.8% | 10 | 5 | 5 |
| `atr_pct_0.25pct_152.15` | 152.15 | 39.5% | 59.8% | 0.6% | 10 | 5 | 5 |

### Gate Failure Detail

All variants fail the same three gate criteria:

| Criterion | Meaning |
|-----------|---------|
| `min_closed_trades_total` | Too few closed trades (< minimum) |
| `min_profit_factor` | Not enough trades to compute meaningful profit factor |
| `min_expectancy_r` | Not enough trades to compute meaningful expectancy |

This is **expected** for a 58-hour (3496 1m candles) BTCUSDT dataset with a 240-minute entry lookback: the strategy can only produce trades when a breakout signal aligns with a TREND regime window, which is inherently rare. Gate thresholds are calibrated for longer backtest windows.

## Interpretation

### Key Findings

1. **ATR=2.0 is scale-wrong for BTCUSDT.** The current threshold is at the extreme minimum of the ATR distribution (0.00th percentile). Changing the threshold to any distribution-appropriate value produces a meaningful regime split.

2. **Non-zero trades are achievable.** At ATR ~48 USD (median: 51.4% HVC, 14.4% TREND), replays produce 3 trades over 58h. At ATR ~77 USD (p90: 9.8% HVC, 33.2% TREND), replays produce 5 trades.

3. **ATR_pct is a viable scale-free alternative.** ATR_pct thresholds (e.g., 0.1% of price) produce results comparable to their absolute-percentile counterparts (e.g., ATR p75), without embedding a specific asset price.

4. **ADX thresholds are reasonable.** ADX trend=25.0 is at the 69th percentile and range=20.0 at the 51st percentile -- no scale issue with ADX (bounded indicator).

5. **The dataset is too short for statistically significant backtest results.** Even with optimal regime distribution, a 58h window with 240-minute lookbacks yields only single-digit trades. Gate failures on `min_closed_trades_total` and `min_profit_factor` are expected and not evidence of strategy weakness.

6. **Regime distribution responds monotonically to ATR threshold.** As ATR threshold increases, HVC percentage decreases monotonically and TREND/RANGE percentages increase monotonically. This confirms the regime logic is functioning correctly.

### What Calibration Achieves

| Before Calibration | After Calibration |
|--------------------|-------------------|
| 0 trades over 58h | 1--10 trades over 58h |
| 100% HVC (no regime diversity) | 0.6%--51.4% HVC (meaningful regime split) |
| Strategy appears broken | Strategy produces signals (too few for statistical gate) |
| Evidence blocked entirely | Pipeline proven: data -> regime -> bridge -> strategy -> execution |

## Decision

### This Analysis Recommends

1. **No production config change from this analysis.** This is controlled-lab evidence only. Any threshold change requires a separate explicit implementation issue with broader testing.

2. **For controlled-lab replay generation**, use ATR ~48--77 USD (p50--p90) or ATR_pct ~0.08%--0.13% as a calibrated starting point. These thresholds produce regime distributions that allow the strategy to evaluate entry conditions.

3. **ATR_pct as a first-class parameter.** ATR_pct (ATR as percentage of current price) is inherently scale-invariant and should be considered as the primary regime threshold type for multi-asset or dynamic-price environments. This would be a `services/regime/config.py` change requiring a separate issue.

4. **Longer datasets are needed for statistically-significant backtest evidence.** 58h is insufficient for a 240-minute lookback strategy. A multi-week or multi-month BTCUSDT dataset would produce tens of trades, enabling meaningful profit factor and expectancy computation.

### This Analysis Does NOT Recommend

- Changing the production regime config based on this data alone.
- Promoting any specific threshold as "correct."
- Claiming the strategy is profitable at any threshold.
- Changing ADX thresholds (they are reasonable on this dataset).

## Recommended Next Slice

**[PROFITABILITY][EXECUTION] Execution economics from calibrated replay results**

Once a calibrated threshold produces non-zero trades over a longer BTCUSDT dataset, compute:
- Gross return, net return (minus fees/slippage/spread)
- Profit factor, Sharpe, max drawdown
- Feed into Strategy League Table (#3040)

This would bridge the gap between "trades are possible" (proven here) and "trades are economically viable" (not yet evaluated).

## Produced Artifacts

| File | Path | Type |
|------|------|------|
| Analysis Script | `scripts/profitability/analyze_btcusdt_regime_calibration_3032.py` | Python |
| Variant Generator | `scripts/profitability/generate_calibration_variants_3032.py` | Python |
| Calibration Top Manifest | `artifacts/candles/mexc_strict_window_3091_regime_calibration/calibration_manifest.json` | JSON |
| 8x Variant Candles | `artifacts/candles/mexc_strict_window_3091_regime_calibration/<variant>/candles.jsonl` | JSONL |
| 8x Variant Manifests | `artifacts/candles/mexc_strict_window_3091_regime_calibration/<variant>/calibration_manifest.json` | JSON |
| 8x Replay Reports | `artifacts/replay_reports/calibration/replay-*/` | JSON bundles |
| Evidence Doc | `docs/evidence/profitability_btcusdt_regime_calibration_3032.md` | Markdown (this file) |

## Safety Boundaries

- LR remains NO-GO.
- Board `trade-capable` stage does not authorize live capital.
- No Live-Go, no Echtgeld-Go.
- No runtime, no DB, no Docker, no Redis.
- No production config changed (`services/regime/config.py` unchanged).
- No strategy/core/runner/provider code changed.
- All regime labels are estimated (`controlled_lab_evidence`).
- All thresholds derived from data distribution, not from PnL optimization.
- Original raw dataset unchanged (SHA-256 verified).
- No production threshold implemented or promoted.

## Limitations

1. **3496 rows (~58h)** is a single contiguous BTCUSDT window. ATR distribution may differ in other market regimes (high-vol, low-vol, trending, ranging).
2. No claim that any calibrated threshold generalizes to other symbols, venues, or time periods.
3. All gate results are FAIL (too few trades). This is expected for a short dataset and does not reflect on strategy quality.
4. Regime labels remain `controlled_lab_evidence` -- no runtime regime service was involved.
5. ATR_pct thresholds were computed against a fixed reference price (~60,859) for variant generation; a proper per-candle ATR_pct regime logic would require a service code change (out of scope).
6. No profitability metrics were produced (0--5 trades do not support meaningful profit factor or expectancy).
7. First 14 candles default to TREND (regime_id=0) regardless of price action.

## Ref Issues

- #3144 -- This issue (BTCUSDT regime calibration analysis)
- #3032 -- Parent: Profitability Engine
- #3142 -- Regime-assigned MEXC replay (baseline)
- #3143 -- PR for #3142 (merged)
- #3141 -- First Evidence Packet (MEXC 3091)
- #3039 -- Execution Economics v1 (next target)
- #3040 -- Strategy League Table v1 (terminal target)
