# ARVP #3031: Binance Candle Backfill for #3028 Paper Reference Window

**Status:** REPLAYABLE — external-candle reference created
**Date:** 2026-06-07
**Author:** Agent (Path A execution)

---

## Summary

backfill #3028 paper reference window (correlation_id=0c39ac88-4f4c-5d47-8d7f-a4a3ccbabfab)
with real 1m klines from Binance Spot API (public, read-only, no auth).

The replay runner no longer rejects the dataset: _validate_candle_series() 60s cadence
check passes with 244 contiguous 1m candles.

---

## Execution History

| Step | Result |
|------|--------|
| Bootloader + Control Intake | GO confirmed, LR NO-GO confirmed, trade-capable stage noted |
| Branch ix/3031-arvp-replayable-1m-candles | Created from origin/main |
| **Backfill** | 244 candles fetched from Binance (window 1780691280000–1780705860000) |
| **Manifest** | artifacts/candles/backfill_3031/manifest.json |
| **File dataset** | artifacts/candles/3028_window/candles.json (244 rows) + dataset_spec.json |
| **Replay dry-run** | PASS: config valid, dataset loaded, candles_total=244 |
| **Replay full run** | Completed: run_id=replay-577c2f83ac91-0001, deterministic_replay_ok=True, gate_result=FAIL |
| **Shadow comparison** | Aligned: fingerprint=8f74124b..., signal/order/fill deltas=-1 (venue-mismatch expected) |

---

## Backfill Provenance

| Field | Value |
|-------|-------|
| Source | binance_spot_api_v3_klines |
| Endpoint | https://api.binance.com/api/v3/klines |
| Symbol | BTCUSDT |
| Interval | 1m |
| Start ts_ms | 1780691280000 (2026-06-05 20:28:00 UTC) |
| End ts_ms | 1780705860000 (2026-06-06 00:31:00 UTC) |
| Candle count | 244 |
| Import ID | 02430e18-df0f-5a7f-b6e4-08e12ea12408 |
| Checksum SHA256 | cd5aabf840764cc0689645921aeaf718e2db8e863a31ccd0c710366732acf1eb |

---

## Key Artifacts

| Artifact | Path |
|----------|------|
| Backfill manifest | artifacts/candles/backfill_3031/manifest.json |
| File candle dataset | artifacts/candles/3028_window/candles.json |
| Dataset spec (venue_mismatch) | artifacts/candles/3028_window/dataset_spec.json |
| Replay report | artifacts/replay_reports/replay-577c2f83ac91-0001/report.json |
| Shadow comparison | artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/shadow_comparison.json |
| Shadow comparison summary | artifacts/replay_vs_paper_compare/replay-577c2f83ac91-0001/shadow_comparison_summary.md |

---

## Venue Mismatch Limitation (CRITICAL)

**The Binance candles are NOT same-venue evidence for the MEXC paper trade.**

| Aspect | Paper Trade (#3028) | This Backfill |
|--------|-------------------|---------------|
| Venue | MEXC (mock exchange) | Binance Spot |
| Candle source | DB candles_1m (MEXC feed) | Binance public klines API |
| Regime data | regime_id=2 (HIGH_VOL_CHAOTIC) | regime_id=0 (defaulted, no regime data) |
| Data quality | Real MEXC feed | Real Binance feed, different venue |

**Consequences:**
- Slight price differences between Binance and MEXC are expected
- All regime_id values are defaulted to 0 (TREND) because Binance klines have no regime data
- Original paper trade decision shows regime_id=2 (HIGH_VOL_CHAOTIC) which blocked entry — replay with regime_id=0 may behave differently
- Shadow comparison shows aligned status but signal/order/fill count deltas of -1 each

---

## Status for Blocked Issues

### #3031 (this issue) — REPLAYABLE
- Backfill successful: 244 Binance 1m candles
- Replay runner no longer rejects: dry-run PASS, full run completed
- Shadow comparison aligned
- **Not same-venue evidence** — venue_mismatch=true documented

### #2961 (calibration batch) — PARTIALLY UNBLOCKED
- Replay window #3028 is now replayable via binance-backed file dataset
- Calibration can proceed with venue-mismatch caveat
- Blocked issues remain for actual same-venue comparison

### #2971 (trading core confidence) — PARTIALLY UNBLOCKED
- Replay infrastructure validated end-to-end with external data source
- LR remains NO-GO

---

## Commands Used

`ash
# Backfill (no --apply, no DB write)
python scripts/replay/candle_continuity.py backfill-binance --symbol BTCUSDT --start-ts-ms 1780691280000 --end-ts-ms 1780705860000 --provenance-out artifacts/candles/backfill_3031/manifest.json

# Replay validation
python -m services.validation.strategy_replay_runner --input-candles artifacts/candles/3028_window/candles.json --output-dir artifacts/replay_reports --strategy-id primary_breakout_v1 --symbol BTCUSDT --adapter-id primary_breakout_runner_v1 --speedup-profile instant --deterministic-verify

# Shadow comparison
python -m services.validation.replay_vs_paper_compare_runner --replay-report artifacts/replay_reports/replay-577c2f83ac91-0001/report.json --paper-reference docs/evidence/arvp_paper_reference_window_2968_after_3026.json --output-dir artifacts/replay_vs_paper_compare
`
