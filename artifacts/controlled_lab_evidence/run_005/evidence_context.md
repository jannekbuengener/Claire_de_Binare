# Controlled-Lab Evidence Pack — run_005

**Status:** Multi-regime trade lifecycle & PnL attribution (BUY signals + trade closures + per-regime PnL)
**Evidence class:** `controlled_lab_evidence`
**Source:** `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/candles.jsonl`
**Generated:** 2026-06-13 via patched `strategy_backtest_runner.py` (f9ed75b0, #3178) + `build_signal_aware_candle_trace.py` + `arvp_regime_scorecard_runner.py`

## What this artifact shows

- **Full trade lifecycle attribution per regime:** 7,575 MEXC BTCUSDT 1m candles with 3 regime types
- **Per-regime BUY signals + trade closes + PnL sum (R):**

| Regime | Observations | BUY signals | Trade closes | PnL sum (R) |
|--------|:---:|:---:|:---:|----------|
| TREND | 2,676 | **5** | 1 | -0.0004 |
| RANGE | 3,366 | 0 | **4** | -0.0105 |
| HIGH_VOL_CHAOTIC | 1,533 | 0 | 0 | — |
| **Total** | **7,575** | **5** | **5** | **-0.0109** |

## Per-Trade Detail

| # | Entry regime | Exit regime | r_return |
|---|:---:|:---:|----------|
| 0 | TREND (0) | RANGE (1) | -0.00227 |
| 1 | TREND (0) | RANGE (1) | -0.00402 |
| 2 | TREND (0) | RANGE (1) | -0.00247 |
| 3 | TREND (0) | TREND (0) | -0.00042 |
| 4 | TREND (0) | RANGE (1) | -0.00171 |

**Key insight:** All 5 entries occurred in TREND (regime required for entry). 4 of 5 trades closed in RANGE — the regime had shifted by the time the channel exit triggered. The sole trade that remained in TREND had the smallest loss.

## Pipeline

```
MEXC calibrated candles (JSONL, 7,575 rows)
  → strategy_backtest_runner.py (patched #3178) — gate_trace + trades
  → gate_trace.jsonl (entry pathway only)
  → build_signal_aware_candle_trace.py — BUY signal attribution
  → trade_lifecycle.json (extracted from backtest report)
  → combined trace.json (steps + trades)
  → arvp_regime_scorecard_runner.py — per-regime scorecard with PnL
```

## What this artifact does NOT show

- **Small sample:** only 5 trades, all loss-making. Not statistically meaningful — value is path proof, not strategy assessment.
- **SELL signal attribution unavailable.** Gate trace does not emit exit decisions.
- **Natural paper evidence unavailable.** This is controlled_lab_evidence only.
- **CRISIS regime (regime_id=3).** No observations in any dataset.
- **Statistical strength.** 5 trades cannot answer whether RANGE exits are systematically adverse.

## Governance caveats

- **NOT natural_paper_evidence — cannot satisfy 5.2.4**
- No Product-Complete claim is made or implied
- LR remains NO-GO
- Board stage=trade-capable is orthogonal and does not clear live trading
- Regime IDs are estimated via offline ADX/ATR heuristic, not runtime-derived
- Strategy was run in backtest (offline), not live paper mode

## References

- `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/` — source dataset
- `services/validation/strategy_backtest_runner.py` — patched runner (#3177/#3178)
- `tools/build_signal_aware_candle_trace.py` — signal-aware trace builder
- `core/replay/arvp_regime_scorecards.py` — scorecard core with trade attribution support
- `services/validation/arvp_regime_scorecard_runner.py` — scorecard CLI
- `docs/contracts/evidence_class_contract.md` — evidence class contract
