# Controlled-Lab Evidence Pack — run_003

**Status:** Multi-regime candle distribution
**Evidence class:** `controlled_lab_evidence`
**Source:** `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/candles.jsonl`
**Generated:** 2026-06-13 via `build_regime_trace_from_candles.py` + `arvp_regime_scorecard_runner`

## What this artifact shows

- **Multi-regime candle trace:** 7,575 observations with 3 regime types
- **Regime distribution:** TREND=2,676, RANGE=3,366, HIGH_VOL_CHAOTIC=1,533
- **Scorecard status:** `ok`
- **Source venue:** MEXC (BTCUSDT, 1m cadence)
- **Regime assignment method:** `offline_heuristic_adx_atr` (distribution_based_p75 calibration)
- **Reproducible:** deterministic pipeline, no randomness
- Addresses product criterion D (regime understanding) with actual multi-regime coverage

## What this artifact does NOT show

- **Signal attribution is unavailable** — candle-only trace, no strategy
- **Trade closure attribution is unavailable** — no trade/signal data
- **CRISIS regime (regime_id=3)** — no CRISIS observations exist in this dataset
- **Natural paper evidence** — this remains controlled_lab_evidence only

## Governance caveats

- **⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4**
- No Product-Complete claim is made or implied
- LR remains NO-GO (per `LR-AUDIT-STATUS-2026-03-05.md` and `CONTROL_REGISTER.md`)
- Board stage=trade-capable is orthogonal and does not clear live trading
- Regime IDs are estimated via offline ADX/ATR heuristic, not runtime-derived

## References

- `artifacts/candles/mexc_sample_expansion_3032_1m_cadence_regime_calibrated/` — source dataset
- `tools/controlled_lab/build_regime_trace_from_candles.py` — trace generator
- `services/validation/arvp_regime_scorecard_runner.py` — scorecard runner
- `docs/contracts/evidence_class_contract.md` — evidence class contract
- `knowledge/governance/ARVP_PRODUCT_INTENT.md` — product intent
