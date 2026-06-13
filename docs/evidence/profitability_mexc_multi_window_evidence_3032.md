# CDB Profitability -- MEXC Multi-Window Evidence #3032

**Date:** 2026-06-13T12:58:00Z
**Parent:** #3032
**Issue:** #3152
**Refs:** #3091, #3145, #3147, #3149, #3151
**Status:** Complete -- multi-window controlled-lab evidence pack built from fragmented exact-1m windows

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `git fetch`, `gh issue view/create/comment`, `python psycopg2 readonly SELECT`, `python -m services.validation.strategy_replay_runner`, `python -m json.tool` |
| `records_or_results` | DB rows=124897, exact-1m windows=130, selected windows=20, total closed trades=39, sample_size_verdict=PASS. |
| `repo_crosscheck` | `docs/evidence/mexc_future_capture_3091.md`, `docs/evidence/profitability_mexc_sample_size_expansion_3032.md`, `services/validation/strategy_replay_runner.py`, `services/validation/strategy_backtest_runner.py` |
| `impact_on_plan` | Existing readonly fragmented BTCUSDT inventory is large enough for multi-window evidence. Windows are replayed independently instead of forcing a broken continuous chain. |
| `limitations` | No SurrealDB/Context Brain used. public.candles_1m has no venue column; MEXC attribution is inherited from prior same-venue evidence. |

## Scope and Non-goals

### In scope
- Readonly DB inventory of existing BTCUSDT 1m rows.
- Exact-1m contiguous window detection.
- Export of selected windows as independent file-backed datasets.
- Per-window distribution-based ATR p75 calibration.
- Per-window file-backed replay with #3149 economics fields.
- Aggregate economics without pretending the windows form one continuous history.

### Non-goals
- No runtime capture.
- No DB writes.
- No Docker / compose.
- No production config change.
- No strategy change.
- No schema change.
- No threshold selection by profit.

## Readonly DB Inventory

| Check | Result |
|-------|--------|
| `current_user` | `cdb_readonly` |
| `session_user` | `cdb_readonly` |
| `SELECT public.candles_1m` | `True` |
| `INSERT public.candles_1m` | `False` |
| `UPDATE public.candles_1m` | `False` |
| `DELETE public.candles_1m` | `False` |
| `BTCUSDT rows` | `124897` |

Venue limitation: public.candles_1m has no source/venue column. MEXC attribution for this BTCUSDT series is inherited from prior same-venue evidence and runtime canon, not from per-row DB labels.

## Segment Detection

The inventory uses the strict continuity rule `next_ts_ms - current_ts_ms == 60000`.

| Metric | Value |
|--------|-------|
| Exact-1m windows | 130 |
| Windows >= 720 rows | 54 |
| Windows >= 1440 rows | 36 |
| Windows >= 2880 rows | 11 |
| Longest window rows | 7575 |

## Window Selection

Selection kept all exact-1m windows with at least `720` rows, then capped to the top `20` by row count.

| Selected windows | Value |
|------------------|-------|
| Count | 20 |
| Smallest selected rows | 1902 |
| Largest selected rows | 7575 |
| Total selected rows | 66358 |
| Total selected hours | 1105.97 |

Window inventory JSON: `artifacts/candles/mexc_multi_window_3032/window_inventory.json`
Selection manifest JSON: `artifacts/candles/mexc_multi_window_3032/selection_manifest.json`

## Produced Multi-Window Dataset

Raw and calibrated datasets were written under `artifacts/candles/mexc_multi_window_3032/window_###/`.
Each window contains `candles.jsonl`, `dataset_spec.json`, and `provenance_manifest.json`; the calibrated derivative lives under `regime_calibrated/` with its own `candles.jsonl`, `dataset_spec.json`, and `calibration_manifest.json`.

## Regime/Calibration Method

Each selected window was calibrated independently using the predeclared distribution-based ATR p75 rule from #3145/#3147.

- ADX thresholds remain at committed values.
- ATR threshold is derived from that window's ATR(14) distribution.
- Regime labels are `estimated=true`.
- Evidence class is controlled_lab_evidence only.
- Windows are independent fragments, not one continuous market history.

## Replay Results by Window

| Window | Segment | Rows | ATR p75 | Signals | Closed Trades | Win Rate | Profit Factor | Net PnL Quote | Fees Quote | Sample Verdict | Gate |
|--------|---------|------|---------|---------|---------------|----------|---------------|----------------|------------|----------------|------|
| window_001 | 10 | 7575 | 45.66 | 10 | 5 | 0.000 | 0.000 | -2067.29 | 562.78 | weak | FAIL |
| window_002 | 66 | 4607 | 44.00 | 3 | 1 | 0.000 | 0.000 | -384.33 | 80.29 | insufficient | FAIL |
| window_003 | 130 | 4415 | 52.74 | 9 | 4 | 0.250 | 0.841 | -424.89 | 304.23 | insufficient | FAIL |
| window_004 | 103 | 4411 | 40.78 | 5 | 2 | 0.000 | 0.000 | -735.95 | 186.47 | insufficient | FAIL |
| window_005 | 84 | 3668 | 39.63 | 3 | 1 | 0.000 | 0.000 | -281.14 | 93.20 | insufficient | FAIL |
| window_006 | 73 | 3641 | 57.48 | 4 | 2 | 0.000 | 0.000 | -981.71 | 172.65 | insufficient | FAIL |
| window_007 | 126 | 3496 | 61.82 | 8 | 4 | 0.250 | 0.517 | -1217.31 | 299.28 | insufficient | FAIL |
| window_008 | 102 | 3267 | 45.38 | 5 | 2 | 0.000 | 0.000 | -1033.89 | 195.34 | insufficient | FAIL |
| window_009 | 83 | 3156 | 66.13 | 6 | 3 | 0.333 | 3.824 | 1046.18 | 280.44 | insufficient | FAIL |
| window_010 | 55 | 2889 | 55.31 | 8 | 4 | 0.000 | 0.000 | -1368.41 | 341.07 | insufficient | FAIL |
| window_011 | 54 | 2882 | 73.00 | 6 | 3 | 0.333 | 1.803 | 150.92 | 251.44 | insufficient | FAIL |
| window_012 | 82 | 2838 | 57.99 | 3 | 1 | 0.000 | 0.000 | -591.07 | 91.57 | insufficient | FAIL |
| window_013 | 88 | 2775 | 41.50 | 6 | 3 | 0.333 | 0.325 | -518.14 | 278.00 | insufficient | FAIL |
| window_014 | 98 | 2726 | 35.23 | 0 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | no_trades | FAIL |
| window_015 | 101 | 2721 | 38.85 | 0 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | no_trades | FAIL |
| window_016 | 58 | 2683 | 47.16 | 3 | 1 | 0.000 | 0.000 | -130.58 | 79.65 | insufficient | FAIL |
| window_017 | 109 | 2359 | 34.50 | 2 | 1 | 0.000 | 0.000 | -170.64 | 92.47 | insufficient | FAIL |
| window_018 | 14 | 2309 | 59.07 | 0 | 0 | 0.000 | 0.000 | 0.00 | 0.00 | no_trades | FAIL |
| window_019 | 97 | 2038 | 50.85 | 2 | 1 | 1.000 | 655172426.195 | -43.61 | 96.02 | insufficient | FAIL |
| window_020 | 40 | 1902 | 67.63 | 2 | 1 | 0.000 | 0.000 | -507.13 | 84.48 | insufficient | FAIL |

## Aggregate Economics

| Metric | Value |
|--------|-------|
| Total windows | 20 |
| Successful windows | 20 |
| Failed windows | 0 |
| Windows with trades | 17 |
| Total closed trades | 39 |
| Total wins | 6 |
| Total losses | 33 |
| Aggregate win rate | 0.1538 |
| Aggregate gross PnL quote | -5769.61 |
| Aggregate net PnL quote | -9258.98 |
| Aggregate fees quote | 3489.37 |
| Aggregate fee-adjusted return R | -0.122156 |

## Replay + Economics Result

Machine-readable economics: `docs/evidence/profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json`
Machine-readable evidence packet: `docs/evidence/profitability_evidence_packet_primary_breakout_v1_mexc_multi_window_3032.json`

## Sample-Size Verdict

**PASS**

Rule: PASS only if total closed trades >= 20 and at least 3 windows have trades. Actual: total closed trades = 39, windows with trades = 17.

## Decision

Do not promote. This slice produces controlled_lab_evidence only. No production config change, no strategy change, no runtime capture, no Live-Go, no Echtgeld-Go, LR remains NO-GO.

## Recommended Next Step

Multi-window sample threshold reached, but aggregate economics are materially negative. Create a narrow PARK/REJECT decision slice and, if useful, a seed league-table entry explicitly marked PARK.

## Safety Boundaries

| Boundary | Status |
|----------|--------|
| Evidence class | `controlled_lab_evidence` |
| LR status | `NO-GO` |
| Live-Go | false |
| Echtgeld-Go | false |
| DB writes | none |
| Runtime capture | none |
| Docker actions | none |
| Production config change | none |
| Strategy change | none |

## Limitations

- controlled_lab_evidence only.
- Windows are independent fragments, not one continuous market history.
- public.candles_1m has no source/venue column; MEXC attribution for this BTCUSDT series is inherited from prior same-venue evidence and runtime canon, not from per-row DB labels.
- No production config change.
- No strategy change.
- No runtime capture.
- No Live-Go, no Echtgeld-Go, LR remains NO-GO.
