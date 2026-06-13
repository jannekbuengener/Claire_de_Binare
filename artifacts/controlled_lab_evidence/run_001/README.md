# Controlled-Lab Evidence — Regime-Segment Pack (run_001)

| Field | Value |
|-------|-------|
| **Evidence Class** | `controlled_lab_evidence` |
| **Evidence Class Version** | 1.0 |
| **Warning Banner** | ⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4 |
| **Status** | `ok` |
| **Produced By** | `arvp_regime_scorecard_runner` |

## Source

| Field | Value |
|-------|-------|
| **Source Path** | `artifacts/backtests/primary_breakout_v1/20260418-212643/` |
| **Dataset Hash (SHA256)** | `3be2430b5e30845b1db8d3330fc5e6b5d2b322dabf834db4bc2efaad379b30a7` |
| **Candle Count** | 20160 (BTCUSDT, 1m, 14 days) |
| **Period** | 2026-03-29T16:00:00Z to 2026-04-12T15:59:00Z |
| **Strategy Config** | entry_lookback=240m, exit_lookback=120m, breakout_buffer=0.0005, long_only |
| **Source Generator** | `tools/controlled_lab/build_regime_trace_from_candles.py` |

## Regime Distribution

| Regime | Observations |
|--------|-------------|
| TREND (0) | 20160 |

Note: No regime transitions were observed in this 14-day dataset. All candles are classified as TREND (regime_id=0). Signal- and trade-level regime attribution is not included (`signals_available=false`, `trades_available=false`).

## Reproducibility

```powershell
# Step 1: Generate replay trace from candle data
python tools/controlled_lab/build_regime_trace_from_candles.py ^
    --candles artifacts/backtests/primary_breakout_v1/20260418-212643/dataset.candles.json ^
    --output artifacts/controlled_lab_evidence/run_001/trace.json ^
    --run-id controlled-lab-001

# Step 2: Run regime scorecard
python -m services.validation.arvp_regime_scorecard_runner ^
    --run-id run_001 ^
    --replay-trace artifacts/controlled_lab_evidence/run_001/trace.json ^
    --output-dir artifacts/controlled_lab_evidence ^
    --evidence-class controlled_lab_evidence
```

## Boundary Statement

- **NOT natural_paper_evidence** — this artifact is controlled-lab evidence, not natural paper evidence
- **NOT §5.2.4 gate** — cannot satisfy Product-Complete criterion §5.2.4
- **NOT Product-Complete** — does not close #3087 or #2974
- **NOT LR-Go, Paper-Go, or Echtgeld-Go** — LR remains NO-GO
- **No #3087 closure** — #3087 remains OPEN/BLOCKED for natural_paper_evidence
- **No silent class upgrade** — this artifact will never be interpreted as natural_paper_evidence

## Artifacts

| File | Description |
|------|-------------|
| `trace.json` | Replay trace derived from candle dataset (20160 steps) |
| `arvp_regime_scorecard.json` | Machine-readable scorecard with evidence_class metadata |
| `arvp_regime_scorecard_summary.md` | Human-readable scorecard summary |
| `README.md` | This file — operator summary |
