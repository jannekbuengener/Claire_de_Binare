# ARVP #3990 Metric Availability Matrix

**Date:** 2026-07-13  
**Issue:** [#4014](https://github.com/jannekbuengener/Claire_de_Binare/issues/4014)  
**Parent:** [#4013](https://github.com/jannekbuengener/Claire_de_Binare/issues/4013)  
**Blocks:** [#4015](https://github.com/jannekbuengener/Claire_de_Binare/issues/4015)  
**LR:** NO-GO  
**Evidence class:** `historical_cross_venue_research`  
**Outcome:** `READY_FOR_METRIC_EXTRACTION`  
**ranking_ready:** `false` (unchanged)

---

## Brain Evidence

| Field | Value |
|-------|-------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| context_brain_used | false |
| repo_fallback_reason | insufficient_evidence |
| records_found | none |

Repo crosscheck: `artifacts/arvp_vacation/arvp_binance_historical_3990_2bb32b68_20260712T111944Z/queue_state.json`, `tools/arvp_vacation/summary.py`, `tools/arvp_vacation/job_runner.py`, live GitHub issues #4013/#4014/#4015.

---

## Campaign Boundary

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_binance_historical_3990_2bb32b68_20260712T111944Z` |
| Queue records | 324 |
| Canonical jobs | **318** |
| Superseded excluded | **6** |
| Strategies | `donchian_breakout_v1`, `breakout_trend_filter_v1`, `primary_breakout_v1` |
| Scenarios | `baseline`, `pessimistic_execution`, `feed_gap` |
| Venues | Binance historical only — **not** MEXC same-venue confirmation |

Technical PASS on 318 jobs does **not** imply profitable or promotion-ready strategies.

---

## Canonical Job Selection Contract

| Rule | Definition |
|------|------------|
| Selector | `superseded_by_stress_v2_rerun != true` |
| Canonical count | 318 |
| Superseded count | 6 |
| Fail-closed | Unknown/non-boolean `superseded_by_stress_v2_rerun` rejects job |
| Aggregation ban | Original + stress-v2 replacement must never be aggregated together |
| Zero trades | `closed_trades_total == 0` is valid; missing field is not zero |
| Rankable | `rankable=false` when `closed_trades_total == 0` or field missing |
| Stress-only legacy | Six superseded FAIL jobs are excluded from all downstream extraction |

Excluded superseded job IDs (informative):

- `vac-donchian-breakout-v1-binance_1m_stress_max_drawdown-scenarios`
- `vac-breakout-trend-filter-v1-binance_1m_stress_max_drawdown-scenarios`
- `vac-primary-breakout-v1-binance_1m_stress_max_drawdown-scenarios`
- `vac-donchian-breakout-v1-binance_1m_stress_max_volatility-scenarios`
- `vac-breakout-trend-filter-v1-binance_1m_stress_max_volatility-scenarios`
- `vac-primary-breakout-v1-binance_1m_stress_max_volatility-scenarios`

Machine-readable schema: [`docs/contracts/arvp_vacation_job_metrics.v1.schema.json`](../contracts/arvp_vacation_job_metrics.v1.schema.json)

---

## Artifact Inventory

| Artifact | Schema / version | Role |
|----------|------------------|------|
| `queue_state.json` | `1.0` | Job status, `scenario_metrics` mirror, superseded flags |
| `{scenario}_metrics.json` | `arvp_vacation_job_metrics.v1` | Per-scenario economics payload |
| `scenario_group_manifest.json` | replay group manifest | Scenario pass/fail counts |
| `dataset_spec.json` | `dataset_spec.v2` | `purpose`, `overlap_class`, `regime_distribution` |
| `window_bank_manifest.json` | `binance_window_bank.v1` | `temporal_split` Dev/Val/OOS mapping |
| `vacation_summary.json` | `1.0` | MVP summary; **known field-alias gap** (`trade_count`/`net_pnl`) |

Field path convention:

- File artifact: `jobs/<job_id>/replay/<group_id>/{scenario}_metrics.json`
- Queue mirror: `queue_state.jobs[].scenario_metrics.{scenario}.metrics.<field>`

---

## Metric Availability Matrix

| metric | classification | artifact_type | field_path | unit | sign_convention | aggregation_rule | missing_semantics | limitations |
|--------|----------------|---------------|------------|------|-----------------|------------------|-------------------|-------------|
| gross_pnl_quote | directly_available | scenario_metrics_json | metrics.gross_pnl_quote | quote_currency | positive_profit_negative_loss | per_job_per_scenario | absent=missing; 0 with zero trades valid | Binance historical only |
| net_pnl_quote | directly_available | scenario_metrics_json | metrics.net_pnl_quote | quote_currency | positive_profit_negative_loss | per_job_per_scenario | absent=missing; 0 with zero trades valid | Summary alias bug deferred to #4015 |
| fees_total_quote | directly_available | scenario_metrics_json | metrics.fees_total_quote | quote_currency | non_negative_cost | per_job_per_scenario sum | absent=missing; 0 valid at zero trades | Slippage embedded, not itemized |
| slippage | not_available | scenario_metrics_json | metrics_availability.slippage_per_trade_available | n/a | n/a | not_aggregable | always missing standalone | `slippage_note` only |
| max_drawdown_r | directly_available | scenario_metrics_json | metrics.max_drawdown_r | r_multiple | non_negative_depth | per_job_per_scenario | absent=missing; 0 valid at zero trades | Point-estimate drawdown only |
| fee_adjusted_max_drawdown_r | directly_available | scenario_metrics_json | metrics.fee_adjusted_max_drawdown_r | r_multiple | non_negative_depth | per_job when present | null/absent=missing | primary_breakout only; absent on donchian/btf |
| profit_factor | directly_available | scenario_metrics_json | metrics.profit_factor | ratio | non_negative | per_job_per_scenario | absent=missing; 0 valid at zero trades | Not profitability proof |
| fee_adjusted_profit_factor | directly_available | scenario_metrics_json | metrics.fee_adjusted_profit_factor | ratio | non_negative | per_job when present | null/absent=missing on zero-trade primary_breakout | Adapter-dependent emission |
| expectancy_r | directly_available | scenario_metrics_json | metrics.expectancy_r | r_multiple | signed | per_job_per_scenario | absent=missing; 0 valid at zero trades | Point-estimate only |
| fee_adjusted_expectancy_r | directly_available | scenario_metrics_json | metrics.fee_adjusted_expectancy_r | r_multiple | signed | per_job when present | null/absent=missing on zero-trade primary_breakout | Adapter-dependent emission |
| closed_trades_total | directly_available | scenario_metrics_json | metrics.closed_trades_total | count | non_negative_integer | per_job_per_scenario | absent=missing; **0 is valid zero** | Zero-trade jobs rankable=false |
| win_rate | directly_available | scenario_metrics_json | metrics.win_rate | ratio_0_1 | non_negative | per_job_per_scenario | absent=missing; 0 valid at zero trades | Not cross-scenario weighted |
| avg_win_r | directly_available | scenario_metrics_json | metrics.avg_win_r | r_multiple | typically_positive | per_job when wins exist | null/absent when no wins | Missing ≠ 0 |
| avg_loss_r | directly_available | scenario_metrics_json | metrics.avg_loss_r | r_multiple | typically_negative | per_job when losses exist | null/absent when no losses | Missing ≠ 0 |
| exposure_or_time_in_market | derivable_with_assumption | scenario_metrics_json+dataset_spec | metrics.signals_total / dataset_summary.candles_live | ratio_proxy | non_negative | proxy only | needs both fields | No per-bar occupancy |
| regime_behavior | directly_available | dataset_spec_json | regime_distribution | candle_count_by_regime | non_negative_counts | per_dataset window | dataset_spec missing=missing | Window-level only |
| scenario_sensitivity | deterministically_derivable | queue_state.scenario_metrics | scenario_metrics.*.metrics.net_pnl_quote deltas | quote_currency_delta | delta_vs_baseline | intra-job scenario compare | partial if scenario missing | Windows not independent |
| window_stability | derivable_with_assumption | campaign_aggregate | cross-job dispersion (#4015) | policy_defined | n/a | deferred | single-job scope N/A | League/extraction stage |

---

## Sample Validation (12 Jobs)

Validated read-only against campaign artifacts. Overlapping calendar windows are **not** treated as independent statistical samples.

| # | strategy_id | window_class | dataset_id | job_id | baseline closed_trades_total | rankable |
|---|-------------|--------------|------------|--------|------------------------------|----------|
| 1 | donchian_breakout_v1 | monthly | binance_1m_month_2017_10 | vac-donchian-breakout-v1-binance_1m_month_2017_10-scenarios | 563 | true |
| 2 | donchian_breakout_v1 | quarterly | binance_1m_quarter_2020_Q3 | vac-donchian-breakout-v1-binance_1m_quarter_2020_Q3-scenarios | 2087 | true |
| 3 | donchian_breakout_v1 | yearly | binance_1m_year_2022 | vac-donchian-breakout-v1-binance_1m_year_2022-scenarios | 7553 | true |
| 4 | donchian_breakout_v1 | stress_v2 | binance_1m_stress_max_drawdown_v2 | vac-donchian-breakout-v1-binance_1m_stress_max_drawdown_v2-scenarios | 140 | true |
| 5 | breakout_trend_filter_v1 | monthly | binance_1m_month_2017_10 | vac-breakout-trend-filter-v1-binance_1m_month_2017_10-scenarios | 464 | true |
| 6 | breakout_trend_filter_v1 | quarterly | binance_1m_quarter_2020_Q3 | vac-breakout-trend-filter-v1-binance_1m_quarter_2020_Q3-scenarios | 1674 | true |
| 7 | breakout_trend_filter_v1 | yearly | binance_1m_year_2022 | vac-breakout-trend-filter-v1-binance_1m_year_2022-scenarios | 5890 | true |
| 8 | breakout_trend_filter_v1 | stress_v2 | binance_1m_stress_max_drawdown_v2 | vac-breakout-trend-filter-v1-binance_1m_stress_max_drawdown_v2-scenarios | 100 | true |
| 9 | primary_breakout_v1 | monthly | binance_1m_month_2017_10 | vac-primary-breakout-v1-binance_1m_month_2017_10-scenarios | 3 | true |
| 10 | primary_breakout_v1 | quarterly | binance_1m_quarter_2020_Q3 | vac-primary-breakout-v1-binance_1m_quarter_2020_Q3-scenarios | 2 | true |
| 11 | primary_breakout_v1 | yearly | binance_1m_year_2022 | vac-primary-breakout-v1-binance_1m_year_2022-scenarios | 0 | false |
| 12 | primary_breakout_v1 | stress_v2 | binance_1m_stress_max_drawdown_v2 | vac-primary-breakout-v1-binance_1m_stress_max_drawdown_v2-scenarios | 0 | false |

Canonical campaign baseline snapshot (informative, not promotion evidence):

- 89 zero-trade baseline jobs among canonical 318
- 229 traded baseline jobs
- 223 negative net_pnl_quote among traded baseline jobs

---

## Temporal Split Mapping

Dev/Val/OOS assignment uses:

- `dataset_spec.purpose` (`development`, `validation`, `out_of_sample`, `stress`)
- `window_bank_manifest.temporal_split` month lists

Stress-v2 windows (`*_v2`) carry `purpose=stress` and must not be mixed with superseded legacy stress FAIL jobs.

---

## Known Gaps (Out of #4014 Scope)

| Gap | Owner |
|-----|-------|
| `summary.py` reads `trade_count`/`net_pnl` instead of `metrics.closed_trades_total`/`metrics.net_pnl_quote` | #4015 extractor + summary fix |
| Deterministic 318-job hash manifest | #4015 |
| PEP assembly | #4016 |
| League table | #4017 |

---

## Safety Boundaries

- LR remains **NO-GO**
- `ranking_ready` remains **false**
- Binance results are cross-venue research, not MEXC confirmation
- No paper/live/promotion language authorized
- Technical PASS ≠ economic success
- 223 negative traded baseline jobs are baseline evidence only, not optimization input

---

## Validation

```bash
python -m pytest -q tests/unit/arvp/test_vacation_metric_availability_contract.py
ruff check tests/unit/arvp/test_vacation_metric_availability_contract.py
python -m json.tool docs/contracts/arvp_vacation_job_metrics.v1.schema.json
```

Contract test fixtures: `tests/fixtures/arvp/vacation_metrics/` (redacted deterministic subsets).

---

## Restunsicherheiten

- `fee_adjusted_max_drawdown_r` absence on donchian/breakout_trend_filter is artifact reality, not proof those metrics are theoretically impossible.
- `window_stability` policy is intentionally deferred; cross-window correlation/overlap not resolved in this issue.
- Local `queue_state.json` contains absolute Windows paths in some fields; extractor must normalize paths in #4015.
