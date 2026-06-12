# Controlled-Lab Evidence Pack — run_002

**Status:** Partial BUY/entry attribution only
**Evidence class:** `controlled_lab_evidence`
**Source:** `artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json`
**Generated:** 2026-06-12 via `strategy_replay_runner --gate-trace-path` + `build_signal_aware_candle_trace.py` + `arvp_regime_scorecard_runner`

## What this artifact shows

- **Signal-aware trace:** 20,160 candle observations with gate-trace-based BUY signal attribution
- **BUY attribution:** 22 entry_ready=true observations reconciled against baseline buy_signals_total=22; BUY signals attributed to TREND regime
- **Regime distribution:** 100% TREND (regime_id=0)
- **Scorecard status:** `ok`
- **Partial attribution:** `signal_attribution_availability=partial`, `attribution_scope=entry_gate_buy_only`
- Replay run (`replay-fa9e284e6660-0001`) produced identical metrics to baseline (44 signals, 22 BUY, 22 SELL, 22 closed trades); deterministic_replay_ok=True

## What this artifact does NOT show

- **SELL signal attribution is unavailable** — SELL signals return before the gate-trace callback in the current runner and are not present in the gate trace JSONL
- **Trade closure attribution is unavailable** — per-trade `entry_regime_id` and `exit_regime_id` are not emitted by the runner
- **Per-trade PnL by regime** — cannot be computed without trade closure attribution

## Attribution contract

See `attribution_contract.json` for machine-readable availability flags:

| Flag | Value |
|------|-------|
| `signal_attribution_availability` | `partial` |
| `buy_entry_attribution_available` | `true` |
| `buy_entry_count` | 22 |
| `sell_signal_attribution_available` | `false` |
| `trade_closure_attribution_available` | `false` |
| `attribution_scope` | `entry_gate_buy_only` |
| `baseline_reconciled` | `true` |
| `natural_paper_evidence` | `false` |

## Governance caveats

- **⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4**
- No Product-Complete claim is made or implied
- LR remains NO-GO (per `LR-AUDIT-STATUS-2026-03-05.md` and `CONTROL_REGISTER.md`)
- `Board stage=trade-capable` is orthogonal and does not clear live trading

## References

- `docs/evidence/arvp_controlled_lab_evidence_path_3127.md` — design doc for this evidence path
- `artifacts/backtests/primary_breakout_v1/20260418-212643/` — Candidate Source #1 (backtest dataset)
- `tools/build_signal_aware_candle_trace.py` — signal-aware trace builder (Phase 2a)
- `services/validation/arvp_regime_scorecard_runner.py` — scorecard runner
- `core/replay/arvp_regime_scorecards.py` — core scorecard module
- `docs/contracts/evidence_class_contract.md` — evidence class contract
