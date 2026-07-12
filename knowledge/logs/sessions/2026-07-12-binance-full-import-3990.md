# Session 2026-07-12 — Binance full archive import #3990

**Issue:** #3990 (CLOSED)  
**PR:** #3997 (MERGED @ `10bb00d6`)  
**Human-GO:** `HISTORICAL-DATA-GO #3990 Binance BTCUSDT 1m full archive import`  
**Final status:** `FULL_IMPORT_PASS_CAMPAIGN_PARTIAL`

## Delivered

- Full Binance BTCUSDT 1m import tooling + 107-month runtime import (81 STRICT_COMPLETE)
- ARVP window bank: 106 windows, vacation manifest, campaign 312/318 PASS
- Evidence docs + runbook + 17 unit tests

## Validation

- `pytest` market_data unit tests: 17 PASS
- CI PR #3997: all required checks green
- Smoke/pilot/full campaign executed offline

## Boundaries

- Cross-venue research only; LR NO-GO; no paper/live
- Artifacts on `E:\CDB_artifacts` via junction (not in git)

## Follow-ups

- Rebuild stress windows after cadence fix and re-run 6 failed jobs
- 26 PARTIAL_USABLE early months remain documented, excluded from bank
