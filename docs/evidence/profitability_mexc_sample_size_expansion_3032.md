# CDB Profitability -- MEXC Sample-Size Expansion Evidence #3032

**Date:** 2026-06-12
**Parent:** #3032
**Issue:** #3150
**Refs:** #3147, #3149, #3145, #3142
**Status:** Complete -- longer MEXC dataset exported, calibrated, replayed, and evidenced

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git switch`, `gh issue view/create/comment`, `psycopg2` via `POSTGRES_READONLY_PASSWORD_DSN` (readonly SELECT only), `make replay-shadow-run`, `python json.tool` |
| `records_or_results` | DB inventory: 123,923 BTCUSDT rows, 3718h span, 121 days, 30 gaps >5min. Longest contiguous segment: 9,567 rows (159.5h). Longest 1m-cadenced: 7,575 rows (126.2h). Calibrated ATR p75=52.59. Replay: 10 signals, 5 trades, 0 wins, profit_factor=0.0. |
| `repo_crosscheck` | `artifacts/candles/mexc_sample_expansion_3032/`, `artifacts/replay_reports/mexc_sample_expansion_3032/replay-b1472f81e943-0001/report.json` |
| `impact_on_plan` | Sample expanded from 4 to 5 trades (25%), window from 58h to 126h (2.2x). Economics fields now available (#3149). Sample still insufficient; recommendation PARK. |
| `limitations` | No SurrealDB/Context Brain. All regime labels estimated. N=5 trades insufficient for economic significance. Data fragmented: longest 1m-cadenced window only 7.6k of 123k available rows. |

## Scope and Non-goals

### In scope
- Inventory readonly `public.candles_1m` for MEXC BTCUSDT 1m coverage.
- Export longest contiguous strictly 1m-cadenced file-backed dataset.
- Apply distribution-based regime calibration (ATR p75, same methodology as #3145).
- Run file-backed replay with #3149 economics output.
- Produce evidence packet and execution economics JSON.
- Report sample-size verdict honestly.

### Non-goals
- No runtime capture.
- No Docker / compose.
- No DB writes.
- No Live-Go, no Echtgeld-Go.
- No strategy/core/schema changes.
- No threshold selection by profit.
- No production config changes.

## DB Inventory

### Coverage

| Metric | Value |
|--------|-------|
| Total BTCUSDT rows | 123,923 |
| Time span | 2026-01-08 to 2026-06-12 (3718h / ~155 days) |
| Distinct days | 121 |
| Export principal | `cdb_readonly` |
| regime_id status | All null (123,923/123,923) |

### Gap Profile

The data has 30 gaps larger than 5 minutes. The two largest:
- 2026-02-20 → 2026-03-11: 18.8 days (27,003 minutes)
- 2026-01-29 → 2026-02-14: 15.8 days (22,743 minutes)

Other gaps are 12-48h (likely weekends or capture-service restarts).

### Constraints

- The replay runner requires exact 1m cadence (gap=60,000ms). Sporadic 2-3 minute gaps within segments block replay.
- Only the longest strictly 1m-cadenced sub-segment is usable for file-backed replay.

## Selected Window

### Selection Rule
Longest strictly 1m-cadenced contiguous sub-segment of the longest >5min-gap segment (#6).

### Window Metrics

| Metric | Existing (3091) | Expansion | Delta |
|--------|----------------|-----------|-------|
| Rows | 3,496 | 7,575 | +117% |
| Hours | 58.3 | 126.2 | 2.2x |
| Start UTC | 2026-06-06 13:43 | 2026-01-16 09:39 | -- |
| End UTC | 2026-06-08 23:58 | 2026-01-22 22:13 | -- |
| BTC price range | ~$60k | $95,672 → $89,627 | -6.3% |
| Cadence | 1m strict | 1m strict | same |
| Venue | MEXC | MEXC | same |

**Note:** Original DB segment #6 had 9,567 rows (159.5h). 1,992 rows (20.8%) were trimmed to achieve strict 1m cadence. The replay runner's cadence validator is stricter than the gap threshold used for segment extraction.

## Calibration

### ATR Threshold Determination

Following the predeclared distribution-based rule from #3145/#3147:

| Statistic | Jan 2026 (BTC ~$92k) | Jun 2026 (BTC ~$60k) |
|-----------|----------------------|----------------------|
| ATR p50 | 31.95 USD | 48.01 USD |
| **ATR p75** | **52.59 USD** | 61.82 USD |
| ATR p90 | 92.87 USD | 76.84 USD |
| ATR_pct p50 | 0.0346% | -- |
| ATR_pct p75 | 0.0578% | -- |

**Selected:** ATR p75 = 52.59 USD (this dataset's 75th percentile). Not profit-optimized. Same methodology as #3145/#3147: distribution-based, not selected by replay outcome.

### Regime Distribution (ATR=52.59)

| Regime | Candles | Percentage |
|--------|---------|------------|
| TREND (0) | 2,676 | 35.3% |
| RANGE (1) | 3,366 | 44.4% |
| HIGH_VOL_CHAOTIC (2) | 1,533 | 20.2% |
| CRISIS (3) | 0 | 0.0% |

This is a dramatic improvement over the committed ATR=2.0 which produced 99.5% HVC. 35.3% TREND enables the primary_breakout_v1 strategy to generate entry signals.

## Replay Result

| Metric | Value |
|--------|-------|
| Run ID | `replay-b1472f81e943-0001` |
| Candles processed | 7,575 |
| Buy signals | 5 |
| Sell signals | 5 |
| Orders placed | 10 |
| Fills recorded | 5 |
| Closed trades | **5** |
| Trades won | 0 |
| Trades lost | 5 |
| Win rate | 0.0 |
| Profit factor | 0.0 |
| Deterministic replay | True |
| Data integrity | True |
| Gate result | FAIL |

### Return & PnL

| Metric | Value |
|--------|-------|
| Gross return (R) | -0.0109 |
| Expectancy (R) | -0.0022 |
| Fee-adj expectancy (R) | -0.0034 |
| Fee-adj profit factor | 0.0 |
| Gross PnL (USDT) | -1,029.98 |
| Net PnL (USDT) | -1,592.48 |
| Fees paid (USDT) | 562.50 |

### Sample-Size Verdict

**INSUFFICIENT.** N=5 trades over 126h. Per the replay runner's own sample_size_verdict: `weak`. This is a 25% improvement over the prior N=4 (58h) evidence, but remains 4x below the recommended threshold of >20 trades for economic assessment.

## Comparison: 3091 vs Expansion

| Metric | 3091 (#3147) | Expansion (#3150) | Delta |
|--------|-------------|-------------------|-------|
| Candles | 3,496 | 7,575 | +117% |
| Hours | 58.3 | 126.2 | +116% |
| ATR p75 | 61.82 | 52.59 | -15% |
| Trades | 4 | 5 | +25% |
| Wins | 1 | 0 | n/a |
| Profit factor | 0.517 | 0.0 | n/a |
| Fee-adj PF | 0.425 | 0.0 | n/a |
| Net PnL (USDT) | -1,217.31 | -1,592.48 | -31% |
| Fees (USDT) | 299.28 | 562.50 | +88% |

**Interpretation:** The expansion increased data volume by 2.2x but only produced 25% more trades. The BTC price context shifted from $60k (Jun) to $92k (Jan) — the Jan window was strongly bearish (-6.3% drop), which likely contributed to the all-loss outcome. The sample size remains too small to distinguish strategy weakness from market regime.

## Recommendation

**PARK.** Do not promote. The sample-size expansion succeeded as a pipeline exercise (readonly DB export, calibration, replay, evidence artifacts all work) but failed to reach the sample-size threshold needed for economic assessment.

### What was gained

1. **Pipeline proven at larger scale:** DB inventory, export, cadence filtering, calibration, replay, and evidence production all work end-to-end on a 7.6k-candle dataset.
2. **Fee economics confirmed:** The #3149 economics fields produce correct fee-adjusted returns. Fees at 0.06% taker rate are significant (562 USDT on 5 trades).
3. **Data fragmentation understood:** 123k candles exist but are fragmented into 30+ segments. The longest useful segment is 7.6k rows after cadence filtering. This is a **data architecture constraint**, not a strategy or calibration constraint.
4. **BTCUSDT price context matters:** ATR p75 changes with price level (52.59 at $92k vs 61.82 at $60k). The p75 rule is scale-adapting but produces different absolute thresholds per dataset window.

### What is still needed

1. **Longer contiguous data:** With 123k rows available but fragmented, a gap-tolerant replay mode or continuous capture beyond 1 week would be the fastest path to >20 trades.
2. **ATR_pct as first-class parameter:** The #3145 recommendation to use ATR_pct (scale-invariant) for regime classification would simplify calibration across BTC price levels. This requires implementation (separate issue).
3. **Multiple non-overlapping evidence runs:** A single 126h window is insufficient regardless of trade count. Multiple independent windows are needed for any claim of robustness.

## Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR status | **NO-GO** |
| Live-Go | false |
| Echtgeld-Go | false |
| DB writes | none |
| Runtime/Docker | none |
| Strategy changes | none |
| Config changes | none |
| Evidence class | controlled_lab_evidence |

## Produced Artifacts

| Path | Type | Description |
|------|------|-------------|
| `artifacts/candles/mexc_sample_expansion_3032/` | Dataset | Raw export (9,567 rows, longest segment #6) |
| `artifacts/candles/mexc_sample_expansion_3032_1m_cadence/` | Dataset | 1m-cadenced subset (7,575 rows) |
| `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/` | Dataset | Calibrated derived dataset (ATR=52.59) |
| `artifacts/replay_reports/mexc_sample_expansion_3032/replay-b1472f81e943-0001/` | Replay | Full replay bundle with report.json |
| `scripts/profitability/assign_regime_calibrate_3032_expansion.py` | Script | Regime assignment for expansion datasets |
| `docs/evidence/profitability_mexc_sample_size_expansion_3032.md` | Doc | This file |
| `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_sample_expansion_3032.json` | Evidence | Evidence packet |
| `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_sample_expansion_3032.json` | Evidence | Execution economics |

## Restunsicherheiten

- ATR p75 varies with BTC price level. The Jan window ($92k) and Jun window ($60k) produce different thresholds. Without scale-invariant calibration (ATR_pct), each window requires independent calibration.
- The all-loss outcome (0/5 wins) in a bearish window says more about market direction than strategy quality. Long-only strategies will struggle in 1-week bearish windows regardless of signal quality.
- Data fragmentation prevents multi-week contiguous evidence. The root cause (capture-service pauses) is outside this slice's scope.
- No claim of generalizability across time periods, price levels, or market regimes is made from this single-window evidence.
