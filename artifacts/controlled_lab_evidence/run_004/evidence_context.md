# Controlled-Lab Evidence Pack — run_004

**Status:** Multi-regime signal-attributed (BUY-only)
**Evidence class:** `controlled_lab_evidence`
**Source:** `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/candles.jsonl`
**Generated:** 2026-06-13 via `strategy_replay_runner --gate-trace-path` + `build_signal_aware_candle_trace.py` + `arvp_regime_scorecard_runner`

## What this artifact shows

- **Multi-regime strategy execution:** primary_breakout_v1 run against 7,575 MEXC BTCUSDT 1m candles with 3 regime types
- **BUY signal attribution per regime:** 5 BUY signals, all in TREND regime (0 in RANGE, 0 in HIGH_VOL_CHAOTIC)
- **Strategy regime sensitivity:** The strategy requires `has_trend_regime=true` to enter — correctly filtering entries to TREND regime only
- **Scorecard status:** `ok` with per-regime observation and signal counts
- **Provenance:** MEXC same-venue data (BTCUSDT, 1m, ~5.3 days), deterministic replay confirmed
- **Reproducible:** gate-trace pipeline from candles through strategy execution to scorecard

## Regime Distribution with Signal Attribution

| Regime | Observations | Gate-trace rows | BUY signals |
|--------|-------------|:---:|:---:|
| TREND | 2,676 | 2,561 | **5** |
| RANGE | 3,366 | 3,236 | 0 |
| HIGH_VOL_CHAOTIC | 1,533 | 1,533 | 0 |
| **Total** | **7,575** | 7,330 | **5** |

Note: 245 candles fall outside gate-trace coverage (240 warmup + 5 without matching gate-trace row).

## Attribution contract

See `attribution_contract.json` for machine-readable availability flags:

| Flag | Value |
|------|-------|
| `signal_attribution_availability` | `partial` |
| `buy_entry_attribution_available` | `true` |
| `buy_entry_count` | 5 |
| `sell_signal_attribution_available` | `false` |
| `trade_closure_attribution_available` | `false` |
| `attribution_scope` | `entry_gate_buy_only` |
| `baseline_reconciled` | `true` |
| `natural_paper_evidence` | `false` |

## What this artifact does NOT show

- **SELL signal attribution is unavailable** — gate trace does not emit SELL decisions
- **Trade closure attribution is unavailable** — per-trade `entry_regime_id` and `exit_regime_id` are not emitted
- **Per-regime PnL is unavailable** — requires trade-closure attribution
- **CRISIS regime (regime_id=3)** — no CRISIS observations exist in this dataset
- **Natural paper evidence** — this remains controlled_lab_evidence only

## Reproducibility

```
# Convert MEXC calibrated candles to JSON array
python -c "import json; candles=[json.loads(l) for l in open('candles.jsonl') if l.strip()]; json.dump(candles, open('candles.json','w'))"

# Run strategy replay with gate-trace
python -m services.validation.strategy_replay_runner \
    --dataset-source file \
    --input-candles candles.jsonl \
    --gate-trace-path gate_trace.jsonl \
    --speedup-profile instant

# Build signal-aware trace
python tools/build_signal_aware_candle_trace.py \
    --input-candles candles.json \
    --gate-trace-path gate_trace.jsonl \
    --baseline-metrics baseline_metrics.json \
    --output trace.json \
    --run-id run_004

# Produce scorecard
python -m services.validation.arvp_regime_scorecard_runner \
    --run-id run_004 \
    --replay-trace trace.json \
    --output-dir artifacts/controlled_lab_evidence \
    --evidence-class controlled_lab_evidence
```

## Governance caveats

- **NOT natural_paper_evidence — cannot satisfy 5.2.4**
- No Product-Complete claim is made or implied
- LR remains NO-GO
- Board stage=trade-capable is orthogonal and does not clear live trading
- Regime IDs are estimated via offline ADX/ATR heuristic, not runtime-derived

## References

- `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/` — source dataset
- `services/validation/strategy_replay_runner.py` — replay CLI with gate-trace support
- `tools/build_signal_aware_candle_trace.py` — signal-aware trace builder
- `services/validation/arvp_regime_scorecard_runner.py` — scorecard runner
- `docs/contracts/evidence_class_contract.md` — evidence class contract
- `knowledge/governance/ARVP_PRODUCT_INTENT.md` — product intent
