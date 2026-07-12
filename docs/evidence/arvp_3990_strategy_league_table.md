# ARVP Binance Historical Strategy League Table (#4017)

**Issue:** [#4017](https://github.com/jannekbuengener/Claire_de_Binare/issues/4017)  
**Parent:** [#4013](https://github.com/jannekbuengener/Claire_de_Binare/issues/4013)  
**Epic:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)  
**Evidence class:** `historical_cross_venue_research`  
**Exit status:** `HISTORICAL_LEAGUE_PARTIAL_NO_RANKABLE_WINNER`  
**LR:** NO-GO · **promotion_status:** NOT_AUTHORIZED

## Source and bundle hashes

| Field | Value |
|---|---|
| Campaign ID | `arvp_binance_historical_3990_2bb32b68_20260712T111944Z` |
| Source contract | `arvp_strategy_metrics.v1` |
| Source content hash | `ad3d4ccc449e81e4aa5ec81185d6b3229d12a9e05b2e4970dd352b7471e5b7ad` |
| Scenario records | 954 (318 jobs × 3 scenarios) |
| Candidate bundle hash | `4e7b4b88427d3fed84493721f97f82d0502c5a93ee96b81b8af8dab0671e26a4` |
| Report content hash (full campaign) | `0252caea15ea5eb614bceda1bc0aeb3131fca896136079b67349c5724c296533` |

Determinism: two identical CLI runs with the same `--report-id` reproduced the same
`report_content_hash` locally.

## Scoring formula and dimensions

Normative Formula v1: [`docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md`](../strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md)

| Formula dimension | Weight % |
|---|---:|
| NET_ECONOMICS | 25.0 |
| ROBUSTNESS | 20.0 |
| EVIDENCE_COMPLETENESS | 15.0 |
| SAFETY_STATUS | 15.0 |
| PAPER_REFERENCE_CONFIDENCE | 15.0 |
| EXECUTION_REALISM | 10.0 |

Implementation: `services/validation/profitability_league_scorer.py`  
Governance assembler: `services/validation/profitability_league_table_report_assembler.py`  
CLI: `python -m tools.arvp_vacation.league_table_report`

Comparison table dimensions (raw + descriptive, not ranking weights):

`net_economic_result`, `drawdown`, `expectancy`, `profit_factor`,
`stability_across_windows`, `cost_sensitivity`, `feed_gap_sensitivity`,
`sample_size`, `split_coverage`, `stress_behavior`, `evidence_quality`

## Rankability gates and league result

Report-level gates (enforced, not overridden by scores):

| Field | Value |
|---|---|
| `table_status` | `PARTIAL` |
| `ranking_ready` | `false` |
| `official_ranking` | `[]` |
| `winner` | `null` |
| `officially_ranked_count` | `0` |

| Strategy | rankability_status | official_rank | total_score |
|---|---|---:|---:|
| `breakout_trend_filter_v1` | NOT_RANKABLE | null | null (withheld) |
| `donchian_breakout_v1` | NOT_RANKABLE | null | null (withheld) |
| `primary_breakout_v1` | PARTIAL_EVIDENCE | null | null (sentinel / withheld) |

Hard-gate sentinel applies to all three PEPs because `replay_vs_paper_status=not_run`,
`simulator_drift=not_assessed`, and `regime_scorecard.status=unavailable`. Scores are
emitted as `0.0` sentinel components where applicable; `total_score` is withheld for
`NOT_RANKABLE` candidates and not used as an official ranking input.

## Why no official winner

1. Zero candidates satisfy `rankability_status=RANKABLE_FOR_CROSS_VENUE_COMPARISON`.
2. Two candidates are `NOT_RANKABLE` (no rankable baseline windows).
3. One candidate is `PARTIAL_EVIDENCE` only — visible for comparison, not promotable.
4. Paper reference and MEXC same-venue confirmation remain `not_run`.
5. `promotion_status=NOT_AUTHORIZED`; LR remains NO-GO.

## Missing evidence for honest full ranking

- MEXC same-venue replay/paper reference (`same_venue_status=not_run`)
- Paper-reference alignment (`paper_reference_status=not_run`)
- Strategy regime scorecard artifacts (`regime_scorecard.status=unavailable`)
- Rankable baseline windows with complete required metrics for all candidates
- Independent (non-overlapping) sample design — current windows are descriptive only

## Safety boundaries

- Binance historical research ≠ MEXC production confirmation
- No strategy promotion, paper-go, live-go, or capital authorization
- Overlapping window quote PnL is never summed into total return
- Month/quarter/year and dev/validation/OOS/stress splits remain separate in PEP slices
- Descriptive `candidate_rows` must not be read as an official ranking

## Validation

```text
pytest -q tests/unit/arvp/test_league_table_report_assembly.py
pytest -q tests/unit/arvp/test_candidate_evidence_assembly.py
pytest -q tests/unit/validation/test_profitability_league_scorer.py
python -m tools.arvp_vacation.league_table_report \
  --assemble-from-queue-state artifacts/arvp_vacation/.../queue_state.json \
  --report-id pltr-arvp-binance-historical-4017 --hash-only
```

Full-campaign hash evidence depends on local `artifacts/arvp_vacation/`; CI uses slice
fixtures under `tests/fixtures/arvp/`.
