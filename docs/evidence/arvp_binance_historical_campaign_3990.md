# ARVP Binance Historical Campaign — Issue #3990

**Date:** 2026-07-12  
**Issue:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990)  
**LR:** NO-GO  
**Final status:** `HISTORICAL_CAMPAIGN_COMPLETE` (stress-v2 closeout 2026-07-12)

See also: [`arvp_binance_historical_stress_v2_closeout.md`](arvp_binance_historical_stress_v2_closeout.md)

---

## Campaign

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_binance_historical_3990_2bb32b68_20260712T111944Z` |
| Source SHA | `2bb32b686fd71909620dfa73bb5ff4b5273a34d1` |
| Strategies | donchian_breakout_v1, breakout_trend_filter_v1, primary_breakout_v1 |
| Scenarios | baseline, pessimistic_execution, feed_gap |
| Datasets | 106 (window bank) |
| Jobs | 318 |
| PASS | 312 (original) + 6 (stress v2) = **318 technical** |
| FAIL | 6 (original, superseded) + 0 (v2) |
| Evidence class | controlled_lab_evidence / historical_cross_venue_research |
| `ranking_ready` | `false` |

---

## Replay Order (executed)

| Phase | Result |
|-------|--------|
| Smoke (2026-06) | PASS — 3 strategies × 3 scenarios |
| Pilot (2 monthly windows) | PASS — 6 jobs |
| Full bank | completed — 312 PASS / 6 FAIL |

---

## FAIL Analysis (6 jobs)

All failures on **stress** windows crossing month-boundary gaps in concatenated timeline:

- `binance_1m_stress_max_drawdown` × 3 strategies
- `binance_1m_stress_max_volatility` × 3 strategies

Error: `1m cadence violation` (multi-day gap between months in stress slice).

**Fix delivered in PR #3997:** cadence guards in `binance_window_bank.py`. **Stress v2 closeout (2026-07-12):** two valid v2 windows reused from `2021-05`, selective 6-job re-run PASS, original FAILs superseded. Campaign evidence: `docs/evidence/arvp_binance_historical_stress_v2_closeout.md`.

---

## Aggregated Research Verdicts

| Strategy | Monthly/Quarterly/Yearly | Stress | Overall |
|----------|--------------------------|--------|---------|
| donchian_breakout_v1 | HOLD_MORE_DATA (technically valid) | 2 FAIL (cadence) | HOLD_MORE_DATA |
| breakout_trend_filter_v1 | HOLD_MORE_DATA (technically valid) | 2 FAIL (cadence) | HOLD_MORE_DATA |
| primary_breakout_v1 | HOLD_MORE_DATA (technically valid) | 2 FAIL (cadence) | HOLD_MORE_DATA |

No strategy receives NEXT_VALIDATION_CANDIDATE on cross-venue Binance corpus alone.

---

## Cross-Venue Boundaries

- Venue: **Binance** (historical_cross_venue_research)
- Not MEXC same-venue evidence
- Not paper/live/promotion go
- LR remains NO-GO

---

## Artifacts

- Summary: `artifacts/arvp_vacation/arvp_binance_historical_3990_2bb32b68_20260712T111944Z/vacation_summary.json`
- Manifest: `artifacts/arvp_vacation/manifests/binance_historical_campaign_3990.yaml`
- Window bank: `artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/window_bank_manifest.json`
