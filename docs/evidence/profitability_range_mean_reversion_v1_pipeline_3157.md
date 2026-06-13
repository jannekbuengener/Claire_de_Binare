# CDB Profitability -- Range Mean Reversion v1 Pipeline #3157

**Date:** 2026-06-13
**Parent:** #3157
**Predecessor:** #3156
**Refs:** #3152, #3032
**Status:** Complete -- controlled-lab evidence indicates this candidate does not improve on primary_breakout_v1 baseline

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `gh issue view 3157`, `git rev-parse`, `python scripts/profitability/run_range_mean_reversion_pipeline_3157.py`, `pytest tests/unit/profitability/test_range_mean_reversion_pipeline_3157.py` |
| `records_or_results` | 20 windows processed, 443 closed trades, fee_adj_return_r = -0.879, win rate 14.67%. Every window negative. |
| `repo_crosscheck` | `docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json`, `docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json`, `docs/evidence/profitability_evidence_packet_range_mean_reversion_v1_mexc_multi_window_3157.json`, `scripts/profitability/run_range_mean_reversion_pipeline_3157.py`, `tests/unit/profitability/test_range_mean_reversion_pipeline_3157.py` |
| `impact_on_plan` | Candidate does not pass minimum profitability threshold. HOLD candidate without further tuning or guard changes. |
| `limitations` | Long-only first pass only; short-side was blocked. No param sweep, no walk-forward, no regime-specific filtering beyond RANGE gate. |

## Pipeline Run Summary

| Metric | Value |
|--------|-------|
| Candidate | `range_mean_reversion_v1` |
| Direction | `long_only_first_pass` |
| Windows | 20 |
| Closed trades | 443 |
| Sample verdict | `pass` |
| Gross return R | -0.347 |
| Fee-adjusted return R | -0.879 |
| Win rate | 14.67% |
| Profit factor | 0.099 |
| Expectancy R | -0.00078 |
| Max drawdown R | 0.347 |

## Per-Window Results

| Window | Trades | Fee-adj Return R | Win Rate |
|--------|--------|------------------|----------|
| window_001 | 52 | -0.103 | 5.8% |
| window_002 | 30 | -0.062 | 10.0% |
| window_003 | 27 | -0.054 | 18.5% |
| window_004 | 30 | -0.064 | 3.3% |
| window_005 | 23 | -0.045 | 4.3% |
| window_006 | 23 | -0.033 | 34.8% |
| window_007 | 20 | -0.040 | 35.0% |
| window_008 | 26 | -0.053 | 7.7% |
| window_009 | 25 | -0.057 | 16.0% |
| window_010 | 17 | -0.032 | 29.4% |
| window_011 | 19 | -0.039 | 26.3% |
| window_012 | 20 | -0.039 | 20.0% |
| window_013 | 19 | -0.037 | 10.5% |
| window_014 | 18 | -0.036 | 5.6% |
| window_015 | 17 | -0.036 | 5.9% |
| window_016 | 17 | -0.031 | 17.6% |
| window_017 | 17 | -0.034 | 0.0% |
| window_018 | 16 | -0.032 | 0.0% |
| window_019 | 13 | -0.027 | 23.1% |
| window_020 | 14 | -0.023 | 50.0% |

All 20 windows produced negative fee-adjusted return R.

## Comparison to Baseline (primary_breakout_v1 #3152)

| Metric | primary_breakout_v1 | range_mean_reversion_v1 |
|--------|-------------------|------------------------|
| Windows | 20 | 20 |
| Closed trades | 39 | 443 |
| Fee-adj return R | -0.122 | -0.879 |
| Win rate | 51.3% | 14.7% |
| Fees (quote) | 3,489 | 40,543 |

The mean reversion strategy generated ~11x more trades but with far worse economics. The high trade count is mostly losing trades (378/443 = 85.3% loss rate). Fees dominated the PnL at 40,543 vs gross PnL of -26,646.

## Assessment

Range mean reversion v1 does not improve on the baseline. Three contributing factors:

1. **Low win rate (14.7%)**: Mean reversion entries against small RANGE movements generated many small losses and few meaningful reversions.
2. **Fee dominance**: 40,543 in fees vs -26,646 gross PnL. The strategy overtrades in the simulated 0.1% fee model.
3. **ATR stops locked losses**: Stops clipped small losses when price did not revert as expected.

## Recommendation

**HOLD.** This candidate is not viable in its current form. Potential follow-up paths (not scoped):
- Add momentum filter to avoid reversion against strong micro-trends
- Tighten entry threshold beyond z=-2.0 to reduce trade count
- Shorter cooldown / adaptive cooldown
- Commission sensitivity analysis
- Per-window optimization (not recommended without walk-forward)

## Artifacts

- Candidate contract: `docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json`
- Execution economics: `docs/evidence/profitability_execution_economics_range_mean_reversion_v1_mexc_multi_window_3157.json`
- Evidence packet: `docs/evidence/profitability_evidence_packet_range_mean_reversion_v1_mexc_multi_window_3157.json`
- Pipeline script: `scripts/profitability/run_range_mean_reversion_pipeline_3157.py`
- Unit tests: `tests/unit/profitability/test_range_mean_reversion_pipeline_3157.py`
- Per-window reports: `artifacts/replay_reports/range_mean_reversion_v1_mexc_multi_window_3157/`
