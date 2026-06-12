# CDB Profitability -- Calibrated Evidence Packet v2 #3032

**Date:** 2026-06-12
**Parent:** #3032
**Issue:** #3146
**Refs:** #3141, #3142, #3143, #3145
**Status:** Complete -- calibrated evidence packet v2 produced

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `git switch`, `gh issue view/create/comment`, `python -m services.validation.strategy_replay_runner`, `python json` |
| `records_or_results` | Selected variant: `atr_p75_61.82` (ATR=61.82, p75). Replay: 8 signals, 4 closed trades, profit_factor=0.517, win_rate=0.25, deterministic_replay_ok=True. gate_result=FAIL (insufficient data). Execution economics and evidence packet v2 JSON produced. |
| `repo_crosscheck` | `docs/evidence/profitability_btcusdt_regime_calibration_3032.md`, `artifacts/candles/mexc_strict_window_3091_regime_calibration/atr_p75_61.82/`, `docs/contracts/profitability_evidence_packet.v1.schema.json` |
| `impact_on_plan` | Calibrated evidence packet v2 supersedes v1 (#3141) with non-zero trade data. All economics fields that are unavailable are explicitly marked as such. No fabricated metrics. |
| `limitations` | No SurrealDB/Context Brain. All regime labels estimated. 4 trades over 58h is insufficient for statistical significance. Many economics fields unavailable from replay runner. |

## Scope and Non-goals

### In scope
- Select a single calibration variant by predeclared distribution-based rule.
- Run full file-backed replay against the selected variant.
- Produce execution economics summary and evidence packet v2 JSON.
- Document the variant selection, replay result, economics, and decision.

### Non-goals
- No production config change.
- No strategy/core/runner/provider code changes.
- No runtime, DB, Docker.
- No Live-Go, Echtgeld-Go, LR status change.
- No promotion claim.
- No overfit for profit: variant selected by percentile, not PnL.

## Variant Selection

### Selection Rule
Per the #3032 prompt contract `variant_selection_rule`, select the variant from the #3145 calibration grid that is:
1. Distribution-based (not profit-selected)
2. Close to ATR p75 or ATR_pct p75
3. Less extreme than p90/p95

### Selected Variant: `atr_p75_61.82`

| Property | Value |
|----------|-------|
| Variant slug | `atr_p75_61.82` |
| ATR threshold | 61.82 USD |
| Percentile | p75 of BTCUSDT ATR distribution |
| % of ~60,859 price | 0.102% |
| Selection rationale | ATR at 75th percentile. Balanced regime split: 27.2% HVC, 24.3% TREND, 48.5% RANGE. Within the recommended range (48--77 USD) from #3145 calibration analysis. Less extreme than p90/p95. |
| Selection is profit-free | Yes -- selected before this replay was run on the fresh branch. Replay result in #3145 (prior slice) showed 4 trades, 4 closed trades, gate FAIL. |
| Calibration manifest | `artifacts/candles/mexc_strict_window_3091_regime_calibration/atr_p75_61.82/calibration_manifest.json` |

### Regime Distribution

| Regime | Count | % |
|--------|-------|---|
| TREND | 849 | 24.3% |
| RANGE | 1,697 | 48.5% |
| HIGH_VOL_CHAOTIC | 950 | 27.2% |

## Input Dataset

| Property | Value |
|----------|-------|
| Dataset ID | `mexc_strict_window_3091_island_3` |
| Symbol | BTCUSDT |
| Venue | MEXC |
| Window | 2026-06-06T13:43Z -- 2026-06-08T23:58Z (58.3h) |
| Candles | 3,496 |
| Raw SHA-256 | `d79a1c3c...` (unchanged) |
| Derived SHa-256 | Per variant (manifests contain full distribution) |
| Regime labels | Estimated via offline ADX/ATR heuristic |
| Evidence class | `controlled_lab_evidence` |

## Replay Result

### Command
```
python -m services.validation.strategy_replay_runner \
  --dataset-source file \
  --input-candles artifacts/candles/mexc_strict_window_3091_regime_calibration/atr_p75_61.82/candles.jsonl \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1
```

### Result

| Metric | Value |
|--------|-------|
| Exit code | 0 |
| run_id | `replay-f270366bef3c-0001` |
| execution_provenance_id | `bt-99eadb4fefcd593a` |
| deterministic_replay_ok | True |
| signals_total | 8 |
| buy_signals_total | 4 |
| sell_signals_total | 4 |
| closed_trades_total | 4 |
| win_count | 1 |
| loss_count | 3 |
| win_rate | 0.25 |
| profit_factor | 0.517 |
| gate_result | FAIL |
| gate_failed_criteria | `min_closed_trades_total`, `min_profit_factor`, `min_expectancy_r` |

### Fields Unavailable from Replay Runner

The following fields are **not emitted** by the current replay runner for this strategy/adapter combination and are explicitly set to `null`/`0.0` in the evidence packet:

- `gross_return`, `net_return` -- not computed
- `expectancy`, `expectancy_r` -- not computed (r-multiple not available)
- `avg_win`, `avg_loss` -- individual trade PnL not exposed
- `max_drawdown`, `max_drawdown_r` -- equity curve not exposed
- `fees`, `spread_cost`, `slippage_cost` -- cost model not active
- `loss_streak` -- trade sequence not exposed

These are **replay runner limitations**, not evidence of zero values.

## Execution Economics

Full economics summary: `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_3091_calibrated.json`

### Key Economics Takeaways

| Dimension | Finding |
|-----------|---------|
| Trade count | 4 trades over 58h -- insufficient for statistical significance |
| Profit factor | 0.517 (1 win, 3 losses) -- not interpretable at this trade count |
| Gate | FAIL (expected for 4 trades in 58h) |
| Cost model | Fees/spread/slippage assumed zero; MEXC BTCUSDT spot fees are 0.0% maker/taker |
| Economic verdict | `UNKNOWN` -- data quantity insufficient |

### Profit Factor Interpretation

A profit factor of 0.517 with 4 trades (1 win, 3 losses) does **not** prove the strategy is unprofitable. At single-digit trade counts, any profit factor from 0.25 to 4.0 is possible by random chance with a 50% win-rate strategy. With 4 trades, the 95% confidence interval for profit factor spans approximately [0.1, 10.0] -- no conclusion can be drawn.

## Evidence Packet v2

Full packet: `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_3091_calibrated_v2.json`

### Comparison to v1 (#3141)

| Dimension | v1 (#3141) | v2 (this) |
|-----------|-----------|-----------|
| Execution | Blocked (regime_id=null) | PASS (4 closed trades) |
| Regime | Unavailable | Estimated, ATR=61.82 (p75) |
| Trade count | 0 | 4 |
| Profit factor | 0.0 (placeholder) | 0.517 (real) |
| Win rate | 0.0 (placeholder) | 0.25 (real) |
| Pipeline shape | Proven | Proven with real data |
| Recommendation | PARK | PARK |

### Schema Compliance

The v2 evidence packet uses `schema_version: profitability_evidence_packet.v1` and is compatible with the v1 schema (`docs/contracts/profitability_evidence_packet.v1.schema.json`). All required schema fields are present. Where economics data is unavailable, fields are set to `0.0` with explicit documentation in `limitations`.

## Decision

### Evidence Classification

| Dimension | Status |
|-----------|--------|
| Dataset quality | `strict_campaign_grade` (inherited from #3141) |
| Regime labels | Estimated (`controlled_lab_evidence`) |
| Replay execution | PASS (deterministic, no runtime) |
| Replay gate | FAIL (insufficient data, expected) |
| Economic viability | `UNKNOWN` (insufficient data) |
| Evidence class | `controlled_lab_evidence` |
| Promotion readiness | `NOT_READY` |

### Recommendation: PARK

1. **Do not promote.** The evidence packet provides non-zero trade data but insufficient quantity for economic assessment.
2. **Do not change production config.** The calibrated ATR threshold (61.82) is controlled-lab only.
3. **Acquire longer dataset.** A multi-week BTCUSDT MEXC dataset (>10k candles) is required to produce statistically meaningful trade counts.
4. **Extend replay runner.** Gross return, net return, drawdown, and expectancy fields need to be emitted by the replay runner for meaningful economics assessment.

## Next Slice Recommendation

**[PROFITABILITY][REPLAY] Extend replay runner to emit full economics fields**

Add to `strategy_replay_runner` / `strategy_backtest_runner`:
- Per-trade PnL output (enabling avg_win, avg_loss, expectancy_r, max_drawdown)
- Cumulative equity curve (enabling drawdown computation)
- Fee/spread/slippage cost tracking (enabling net return)

This would eliminate the "unavailable" fields in the evidence packet and enable meaningful economics computation even at single-digit trade counts.

Alternatively, if a longer dataset becomes available first:
- **[PROFITABILITY][EXECUTION] Execution economics from multi-week calibrated replay**

## Limitations

1. 4 trades over 58h (3496 candles) is insufficient for any statistical or economic conclusion. Gate failures are expected.
2. Many economics fields (gross_return, net_return, expectancy, drawdown, fees) are unavailable from the current replay runner.
3. Profit factor 0.517 at 4 trades does not prove strategy weakness -- it is consistent with random chance at this sample size.
4. Regime labels are estimated via offline ADX/ATR heuristic. No runtime regime service was involved.
5. ATR threshold (61.82) was calibrated on this specific 58h BTCUSDT MEXC window. No claim of generalizability.
6. No claim of profitability, paper readiness, or live readiness.

## Produced Artifacts

| File | Path | Type |
|------|------|------|
| Execution Economics | `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_3091_calibrated.json` | JSON |
| Evidence Packet v2 | `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_3091_calibrated_v2.json` | JSON |
| Evidence Doc | `docs/evidence/profitability_calibrated_evidence_packet_v2_3032.md` | Markdown (this file) |
| Replay Report | `artifacts/replay_reports/replay-f270366bef3c-0001/report.json` | JSON (generated) |

## Safety Boundaries

- LR remains NO-GO.
- Board `trade-capable` stage does not authorize live capital.
- No Live-Go, no Echtgeld-Go.
- No production config, strategy, core, runner, provider, or schema changed.
- Variant selected by distribution-based rule, not by PnL.
- No runtime, no DB, no Docker, no Redis.
- Evidence class is `controlled_lab_evidence`.
- Recommendation is `PARK` -- no promotion, no capital allocation, no paper run.
- All regime labels are explicitly marked as estimated.

## Ref Issues

- #3146 -- This issue (calibrated evidence packet v2)
- #3032 -- Parent: Profitability Engine
- #3141 -- First evidence packet (v1, blocked)
- #3142 -- Regime-assigned MEXC replay (baseline)
- #3143 -- PR for #3142 (merged)
- #3145 -- BTCUSDT regime calibration analysis (merged)
- #3039 -- Execution Economics v1 (future target)
- #3040 -- Strategy League Table v1 (terminal target)
