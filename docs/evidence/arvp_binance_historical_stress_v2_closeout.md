# ARVP Binance Historical Stress-v2 Closeout — Issue #3990

**Date:** 2026-07-12  
**Parent epic:** [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)  
**Upstream:** [#3990](https://github.com/jannekbuengener/Claire_de_Binare/issues/3990) (CLOSED), [#4004](https://github.com/jannekbuengener/Claire_de_Binare/issues/4004) (CLOSED)  
**LR:** NO-GO  
**Final status:** `HISTORICAL_CAMPAIGN_COMPLETE`

---

## Brain Evidence

| Field | Value |
|-------|-------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| repo_fallback_reason | insufficient_evidence |
| live_github_verified | #3990/#4004 CLOSED; PR #3997/#3998/#4007 MERGED |

---

## Root Cause (original 6 FAIL)

Original campaign `arvp_binance_historical_3990_2bb32b68_20260712T111944Z`: **312 PASS / 6 FAIL**.

| Window | Gap index | Δ ms | Cause |
|--------|-----------|------|-------|
| `binance_1m_stress_max_drawdown` | 720 | 5_270_460_000 (~61 d) | Non-adjacent months 2018-09 + 2018-12 concatenated |
| `binance_1m_stress_max_volatility` | 2160 | ~61 d | Non-adjacent months 2020-10 + 2021-01 concatenated |

Technical window-build defect — not a strategy economics FAIL.

---

## E→D migration (#4004 / PR #4007)

| Field | Value |
|-------|-------|
| Old path (invalid) | `E:\CDB_artifacts\market_data` (removed) |
| New path | `D:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\market_data` |
| Evidence | `docs/evidence/market_data/BINANCE_HISTORICAL_DATA_RELOCATION_E_TO_D_2026-07-12.md` |
| Reconciled corpus | 107 months, 81 STRICT_COMPLETE, 26 PARTIAL_USABLE, 4_656_799 candles, 108 windows |

`artifacts/arvp_vacation` remains a junction to `E:\CDB_artifacts\arvp_vacation` (campaign artifacts only; market_data on D:).

---

## Recovery of uncommitted work

| Item | Result |
|------|--------|
| Branch `feat/3990-stress-window-v2-rebuild` | Stale @ `d84ddbe3`, no implementation commit |
| Untracked test preserved | `tests/unit/market_data/test_binance_stress_rebuild.py` |
| Implementation source | `git stash@{0}` (`wip-3990-binance`) restored into `binance_window_bank.py` |
| Closeout branch | `fix/3990-stress-window-v2-closeout` from `origin/main @ 28f33eaa` |

---

## v2 window validation (reused, not rebuilt)

Command: `python -m tools.market_data.binance_window_bank --verify-stress-v2`

### `binance_1m_stress_max_drawdown_v2`

| Check | Result |
|-------|--------|
| Candles | 10_080 |
| start_ts_ms / end_ts_ms | 1_620_885_600_000 / 1_621_490_340_000 |
| Cadence gaps | 0 |
| SHA-256 / fingerprint | `6cdfd79ad9a5090be41f7f6de3c44178a7e3989bde777467ca7ad4c699f2659b` |
| source_months | `2021-05` (STRICT_COMPLETE) |
| max_drawdown (rank metric) | 0.415 |
| storage_guard | PASS |
| FileBackedDatasetProvider | PASS |
| Path | `D:/Dev/Workspaces/Repos/Claire_de_Binare/artifacts/market_data/...` |

### `binance_1m_stress_max_volatility_v2`

| Check | Result |
|-------|--------|
| Candles | 10_080 |
| start_ts_ms / end_ts_ms | 1_621_339_200_000 / 1_621_943_940_000 |
| Cadence gaps | 0 |
| SHA-256 / fingerprint | `8b2e536369ed0e1bb75cf4aac47232b944cef8fb104b6dd10aff96fb918ec7c1` |
| source_months | `2021-05` (STRICT_COMPLETE) |
| volatility (rank metric) | 0.00336 (drawdown window: 0.00281) |
| storage_guard | PASS |
| FileBackedDatasetProvider | PASS |

**Why both from 2021-05:** After migration, stress ranking scans STRICT_COMPLETE contiguous 1m islands segment-wise. May 2021 contains the highest-ranked valid 7-day drawdown chunk and the highest-ranked valid 7-day volatility chunk within a single contiguous island. Windows differ by metric-optimal start offset (~5.25 d apart); ~1.75 d temporal overlap is expected and acceptable for distinct stress metrics.

**Dataset contract:** `venue=binance`, `historical_cross_venue_research`, `target_validation_venue=mexc`, `ranking_ready=false`, `data_quality_verdict=STRICT_COMPLETE`.

---

## Selective 6-job re-run

| Field | Value |
|-------|-------|
| Campaign ID | `arvp_binance_historical_3990_stress_v2_2bb32b68_20260712T212949Z` |
| Manifest | `artifacts/arvp_vacation/manifests/binance_stress_v2_rerun_3990.yaml` |
| Datasets | `binance_1m_stress_max_drawdown_v2`, `binance_1m_stress_max_volatility_v2` |
| Strategies | donchian_breakout_v1, breakout_trend_filter_v1, primary_breakout_v1 |
| Scenarios per job | baseline, pessimistic_execution, feed_gap |
| Jobs | 6 |
| Result | **6 PASS / 0 FAIL** |

### Job IDs

| job_id | dataset | strategy | status |
|--------|---------|----------|--------|
| `vac-donchian-breakout-v1-binance_1m_stress_max_drawdown_v2-scenarios` | drawdown_v2 | donchian_breakout_v1 | PASS |
| `vac-breakout-trend-filter-v1-binance_1m_stress_max_drawdown_v2-scenarios` | drawdown_v2 | breakout_trend_filter_v1 | PASS |
| `vac-primary-breakout-v1-binance_1m_stress_max_drawdown_v2-scenarios` | drawdown_v2 | primary_breakout_v1 | PASS |
| `vac-donchian-breakout-v1-binance_1m_stress_max_volatility_v2-scenarios` | volatility_v2 | donchian_breakout_v1 | PASS |
| `vac-breakout-trend-filter-v1-binance_1m_stress_max_volatility_v2-scenarios` | volatility_v2 | breakout_trend_filter_v1 | PASS |
| `vac-primary-breakout-v1-binance_1m_stress_max_volatility_v2-scenarios` | volatility_v2 | primary_breakout_v1 | PASS |

---

## Campaign merge

Original queue preserved; 6 original FAIL records marked `superseded_by_stress_v2_rerun=true`. Six v2 PASS jobs appended.

| Metric | Value |
|--------|-------|
| Original | 312 PASS / 6 FAIL |
| Stress-v2 re-run | 6 PASS / 0 FAIL |
| Combined technical | **318 PASS / 0 technical FAIL** |
| Queue jobs (with history) | 324 (318 original + 6 v2) |

Merge command: `python -m tools.market_data.binance_window_bank --merge-stress-v2`

---

## Research verdicts (unchanged semantics)

Technical PASS on stress v2 does **not** upgrade research verdicts. All three strategies remain `HOLD_MORE_DATA` on cross-venue Binance corpus. No `NEXT_VALIDATION_CANDIDATE`. LR **NO-GO**. No paper/live/echtgeld implication.

---

## Tests

| Suite | Result |
|-------|--------|
| `tests/unit/market_data/test_binance_stress_rebuild.py` | 10 PASS |
| `tests/unit/market_data/` + `tests/unit/arvp/` | 301 PASS |

---

## Cross-venue boundaries

- Venue: Binance (`historical_cross_venue_research`)
- Not MEXC same-venue evidence
- `ranking_ready=false`
- LR remains NO-GO
