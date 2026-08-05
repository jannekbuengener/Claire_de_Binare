# Slim Evidence — `hh_hl_continuation_v1` Slice 1 (#4372)

**Date:** 2026-08-05  
**Bound main SHA:** `279b7100df899276a92386ee83161734811e9e7c`  
**Owner-GO:** `GO_BATCH_B_IMPLEMENTATION_DUAL` comment `5196985942` (`jannekbuengener`)  
**LR:** NO-GO  
**execution_authorized:** false  
**campaign_authorized:** false  

## Digests

| Item | Value |
|---|---|
| Spec path | `docs/evidence/arvp_hh_hl_continuation_v1_spec_4372.md` |
| Spec SHA-256 (git blob, LF) | `67af97491a031ca8673a5ca17e3f7ec17ffe7ece5e4125db24cf45a29339fcc3` |
| Registry digest (canonical JSON of executable record fields, not file SHA) | `9709328df38aab623e0812a796a096d2a117fb4c119663eff76453285b290445` |
| Result digest (canonical trades/metrics) | `939ef5355c180d17dc9fa308bcb23a43387279be212796790ef0644dea81e542` |
| Execution provenance id | `bt-fe453d1f676db2e1` |
| Dataset file SHA-256 | `3be2430b5e30845b1db8d3330fc5e6b5d2b322dabf834db4bc2efaad379b30a7` |
| Dataset content fingerprint | `503e55865057bec4d42d6659e1c971923fddc3247c2017360bc818ab7438f046` |
| Dataset request fingerprint | `5cf0e892e8be02890bee31efbab5f3c3cdea9962777d1ad3290e16c63aa5e495` |

## Registry entry

- `strategy_id`: `hh_hl_continuation_v1`
- `adapter_id`: `batch_b_shadow_runner_v1` (shadow)
- `runner_module`: `services.validation.hh_hl_continuation_backtest_runner`
- `implementation_status`: `implemented`
- Frozen params: `swing_left_bars=2`, `swing_right_bars=2`, `min_minutes_between_entries=60`, `trade_side_mode=long_only`

## Implementation paths

- `docs/evidence/arvp_hh_hl_continuation_v1_spec_4372.md`
- `core/replay/hh_hl_continuation_common.py`
- `core/replay/batch_b_strategy_registry.py`
- `services/validation/hh_hl_continuation_backtest_runner.py`
- `services/validation/strategy_replay_runner.py` (Batch-B dispatch)
- `tools/arvp_vacation/contract.py` (allowlist)
- `docs/contracts/batch_b_funnel_manifest.v1.json` (hh_hl metadata only)
- Tests under `tests/unit/validation/`, `tests/unit/replay/`, `tests/unit/contracts/`

## Tests

- New hh_hl unit/contract/registry tests: PASS
- Batch-A registry + Campaign-to-PR orchestrator regression: PASS (52 passed / 1 skipped in combined run)
- Prefix-invariance: structural entries/exits equal on prefix vs full (series_end_closeout excluded)
- Fail-closed OHLC/NaN/Inf/cadence: PASS

## Dataset inventory (single-run)

- Path (repo-backed, not committed as evidence copy): `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json`
- Symbol: `BTCUSDT`
- Venue context: historical Binance-style research candle fixture already used by Pack-A / primary breakout replay tooling
- Candle count: `20160`
- Selection: pre-existing repo fixture (not chosen by result)
- Quality: usable for adapter reachability; not Stage-A ranking evidence
- Limitations: not the locked 39-window Batch-B development bank single window; fixture reused for executable single-run proof only

## Single-run provenance

- `strategy_id`: `hh_hl_continuation_v1`
- `adapter_id`: `batch_b_shadow_runner_v1`
- CLI: `python -m services.validation.strategy_replay_runner --dataset-source file --input-candles <dataset> --strategy-id hh_hl_continuation_v1 --adapter-id batch_b_shadow_runner_v1 --symbol BTCUSDT --speedup-profile instant`
- Exit code: `0` (twice)
- Descriptive metrics only: `closed_trades_total=197` (**executability proof only — not quality, not ranking, not Stage-A evidence**), `gate_result=NOT_RANKING_READY`
- Two independent runs: identical canonical result digest `939ef535…`
- Local bundle dirs under `artifacts/replay_reports/hh_hl_4372_run{1,2}/` — **not committed**

## Allowed claims

- Spec/registry/replay adapter for `hh_hl_continuation_v1` are reviewable and executable offline
- Deterministic same-input same-output for the single-run fixture
- Owner Dual-GO scope respected (one candidate; no campaign/execution)

## Forbidden claims

- Profitability, promotability, Stage-A survivor, campaign authorization, merge readiness

## Remaining gates

- Remaining Batch-B candidates still `spec_required`
- Stage-A Dual-GO / campaign authorization still false
- No Campaign-to-PR for this strategy yet
