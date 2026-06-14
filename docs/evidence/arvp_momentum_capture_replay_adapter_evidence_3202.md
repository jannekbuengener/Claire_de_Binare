# ARVP Momentum Capture Replay Adapter Evidence (#3202)

**Status:** `evidence_ready`
**PR:** TBD
**Date:** 2026-06-15
**Branch:** `evidence/momentum-replay-adapter-3202`

## Objective

Wire momentum_capture_v1 into the ARVP strategy_replay_runner so it can be
exercised via the same replay CLI dispatch as primary_breakout_v1 and
range_mean_reversion_v1.

## Evidence Summary

### Adapter Feasibility: CONFIRMED

- `evaluate_momentum_capture_candle` (`scripts/profitability/run_momentum_capture_pipeline_3166.py:150`) is a pure deterministic function with no side effects, no signal invention, no optimization.
- All state (hold_bars, entry_atr, last_entry_ts_ms) is derived from input candles + prior decisions — no external state, no network, no DB.
- Import of the pipeline script at module level is side-effect-free (verified via AST scan).

### Pattern: reuses RMR single-pass backtest pattern

- `momentum_backtest_runner.py` mirrors `rmr_backtest_runner.py` structure:
  - `run_momentum_capture_backtest(candles, ...)` — single-pass loop calling `evaluate_momentum_capture_candle` + `ExecutionSimulator`
  - `_build_full_report()` — deterministic report in `strategy_validation_report.v1` schema
  - `_build_minimal_report()` — early-exit fallback

### Changed Surfaces

| File | Lines | Change |
|------|-------|--------|
| `.gitignore:13` | +1 | Allow `momentum_backtest_runner.py` past `*test*.py` guard |
| `core/replay/historical_bridge.py:21-22` | +2 | `MOMENTUM_CAPTURE_STRATEGY_ID`, `MOMENTUM_CAPTURE_SYMBOL` |
| `services/validation/momentum_backtest_runner.py` | +295 | NEW — single-pass backtest runner |
| `services/validation/strategy_replay_runner.py` | +131/-2 | Dispatch, provenance, warmup, determinism, scenario group |

### Traceability: strategy_replay_runner.py dispatch points

| Location | Purpose |
|----------|---------|
| L107-109 | Import `MOMENTUM_CAPTURE_STRATEGY_ID`, `MOMENTUM_CAPTURE_SYMBOL` from historical_bridge |
| L125-132 | Import momentum pipeline constants (as `MOMENTUM_*`) |
| L141-143 | Import `run_momentum_capture_backtest` |
| L156 | Add to `_SUPPORTED_STRATEGY_IDS` |
| L163 | Add to `_SUPPORTED_SYMBOLS` |
| L170 | Add to `_SUPPORTED_ADAPTER_IDS` |
| L589-602 | `_build_provenance_config_snapshot` momentum branch |
| L787-806 | `_build_momentum_execution_provenance_id` |
| L1004-1009 | Warmup count dispatch |
| L1067-1072 | Execution provenance ID dispatch |
| L1134-1141 | Backtest delegation dispatch |
| L1312-1347 | Determinism check (no two-pass, like RMR) |
| L1634-1674 | `_make_momentum_run_single_fn` — scenario group factory |
| L1725-1727 | Scenario group dispatch |

### Verification

| Check | Result |
|-------|--------|
| `ruff check` (4 files) | PASS — all clean |
| `python -c` import chain | PASS — all three modules import cleanly |
| `pytest -q tests/unit/validation/` | PASS — 230/230 |
| `pytest -q tests/unit/profitability/test_momentum_capture_pipeline_3166.py` | PASS — 27/27 |
| Dry-run CLI (`--dry-run`) | PASS — config valid, dataset loaded |
| Full single-run | PASS — `status=completed`, valid `replay_report.v1` artifact bundle |
| Artifact bundle completeness | PASS — 7 artifacts: report.json, manifest.json, run_registry.jsonl, audit.log, config.resolved.json, env_redacted.txt, operator_summary.json |
| Provenance ID | `bt-d99e842ec330241e` (deterministic from candle hash + config) |
| Dataset fingerprint | `54131709debcb91595747c490636af89b88a489474c23ca67f6a25c1838506df` |

### Economics Gate

Momentum capture v1 uses a single signal function (`evaluate_momentum_capture_candle`) which is
already part of the `spread_cost.py` economics gate surface via the pipeline test suite.
The adapter introduces no new signal functions, no new fee model, no new execution path,
and no new spread logic. Impact: **none** (no change to economics gate surface).

### Candidate Status

- `momentum_capture_v1` remains **PARKED**
- No strategy code changed
- No optimization performed
- No candidate promotion

### LR Status

- LR remains **NO-GO** (unchanged)
- `trade-capable` Board stage is orthogonal and not interpreted as Live-Go

## Blockers

None. Adapter is wired and verified end-to-end.

## Provenance

- Commit: `c033b7a4` (to be updated post-merge)
- Single-run provenance: `bt-d99e842ec330241e`
