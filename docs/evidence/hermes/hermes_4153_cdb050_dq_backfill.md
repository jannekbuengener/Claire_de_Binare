# DQ CDB-050 Stage-A backfill for #4153

Date: 2026-08-04  
Scope: 39 Stage-A development windows only  
LR: NO-GO

## Why

Campaign `execute` fail-closed with `DQ_CONTENT_FINGERPRINT_MISSING` because
window `dataset_spec.json` claimed `data_quality_verdict` without a
`content_fingerprint` / `quality_report.json` sidecar (CDB-050).

## What was written (local artifacts only)

For each of the 39 Stage-A `window_ids` under:

`artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/<window_id>/`

1. Derived `content_fingerprint` from `candles.jsonl` via
   `content_fingerprint_for_candle_rows` (not invented).
2. Wrote/updated `content_fingerprint` on `dataset_spec.json`.
3. Wrote `quality_report.json` sidecar bound to the same fingerprint.

Smoke: `load_binance_window_dataset('binance_1m_month_2017_10', warmup=240)` PASS.

Full fingerprint list is kept local (large); count=39.

## Non-goals

- No Stage-B / OOS / Stress windows touched beyond the 39 Stage-A set.
- No Paper / Live / Echtgeld.
- No inventing fingerprints unrelated to candle content.
