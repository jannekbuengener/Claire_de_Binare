# Controlled-Lab Evidence Pack — run_001

**Status:** Observation-only regime scorecard with unavailable signal/trade attribution
**Evidence class:** `controlled_lab_evidence`
**Source:** `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json`
**Generated:** 2026-06-12 via `tools/build_candle_trace.py` + `arvp_regime_scorecard_runner`

## What this artifact shows

- **Observation-only trace:** 20,160 candle observations from the 14-day BTCUSDT backtest dataset (2026-04-01 through 2026-04-14)
- **Regime distribution:** 100% TREND (regime_id=0) — the entire period was classified as TREND regime
- **Scorecard status:** `ok`
- All fields are populated from real market tick data aggregated to 1m candles

## What this artifact does NOT show

- **Per-step signal counts are unavailable** — the observation-only trace sets `signals_available=false` and omits `signals_emitted` from steps. The original backtest produced 44 signals (22 BUY + 22 SELL) but these cannot be attributed to individual candles without re-running.
- **Per-trade closure attribution is unavailable** — the observation-only trace sets `trades_available=false` and carries `trades=[]` only as an empty placeholder list. The original backtest produced 22 closed trades but individual trade records are not exposed.
- **No signal/trade attribution to regimes** — this scorecard cannot answer "how many signals fired in TREND vs RANGE?" or "what was the PnL distribution per regime?"

## Governance caveats

- **⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4**
- No Product-Complete claim is made or implied
- LR remains NO-GO (per `LR-AUDIT-STATUS-2026-03-05.md` and `CONTROL_REGISTER.md`)
- `Board stage=trade-capable` is orthogonal and does not clear live trading

## Phase 2 — Signal-aware evidence (planned, not implemented)

A follow-up PR/Issue will add signal attribution to the regime scorecard:

1. **Phase 2a (preferred):** Re-run `strategy_replay_runner` against the same candle dataset with `--gate-trace-path`, then merge gate trace with candle data to produce `signals_emitted` counts. This captures BUY signal emissions per candle but still lacks per-trade `exit_regime_id` and SELL signal attribution.
2. **Phase 2b (if 2a insufficient):** Modify `strategy_backtest_runner.py` to emit per-step signal counts and per-trade exit regime data, then repeat the evidence pack with full attribution.

## References

- `docs/evidence/arvp_controlled_lab_evidence_path_3127.md` — design doc for this evidence path
- `artifacts/backtests/primary_breakout_v1/20260418-212643/` — Candidate Source #1
- `tools/build_candle_trace.py` — trace builder used to generate this pack
- `services/validation/arvp_regime_scorecard_runner.py` — scorecard runner
- `core/replay/arvp_regime_scorecards.py` — core scorecard module
- `docs/contracts/evidence_class_contract.md` — evidence class contract
