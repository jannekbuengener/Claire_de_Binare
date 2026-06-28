# Validation Package (`services/validation`)

Offline-/Batch-Validierung: Replay, Backtest, Paper-Runtime-Stimulus, ARVP-Scorecards und Gate-Evaluatoren.

## Current-main Scope

- **Kein** kanonischer always-on BLUE/RED-Container wie `cdb_risk` — Library + Runner-Skripte.
- Wird von CI, Makefile-Targets und Evidence-Workflows aufgerufen.
- Shadow/Paper-first; erzeugt keine Live-Kapital-Freigabe.

## Module (Auswahl)

| Module | Zweck |
|---|---|
| `pipeline.py` | Collect + aggregate Fenster |
| `strategy_replay_runner.py` | Strategie-Replay |
| `strategy_backtest_runner.py` | Backtest |
| `paper_runtime_stimulus_runner.py` | Paper-Stimulus |
| `gate_evaluator.py` | Gate-Auswertung |
| `arvp_regime_scorecard_runner.py` | ARVP-Scorecard |
| `profitability_evidence_packet_assembler.py` | Evidence Packet Assembler — deterministic offline CLI that builds `profitability_evidence_packet.v1` JSON + Markdown from explicit validated input artifact paths |

## Usage

```bash
# Typisch über pytest oder dedizierte Scripts/Make-Targets
pytest -q tests/unit/validation/

# Evidence Packet Assembler (offline, deterministisch)
python -m services.validation.profitability_evidence_packet_assembler \
    --candidate-contract path/to/candidate.json \
    --data-quality-report path/to/dq.json \
    --replay-report path/to/replay.json \
    --scenario-stress-summary path/to/scenario.json \
    --execution-economics-assessment path/to/economics.json \
    --harvester-ref path/to/harvester.json \
    --replay-vs-paper-compare path/to/compare.json \
    --regime-scorecard path/to/scorecard.json \
    --generated-at-utc 2026-06-22T12:00:00Z \
    --out-json out/packet.json \
    --out-md out/packet.md
```

## Canonical References

- `services/validation/pipeline.py`
- `tests/unit/validation/`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md`
- [`docs/evidence/SHADOW_SOAK_RUN_INDEX.md`](../../docs/evidence/SHADOW_SOAK_RUN_INDEX.md) (via [`docs/index.md`](../../docs/index.md))
