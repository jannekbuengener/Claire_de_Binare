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

## Usage

```bash
# Typisch über pytest oder dedizierte Scripts/Make-Targets
pytest -q tests/unit/validation/
```

## Canonical References

- `services/validation/pipeline.py`
- `tests/unit/validation/`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md`
- [`docs/evidence/SHADOW_SOAK_RUN_INDEX.md`](../../docs/evidence/SHADOW_SOAK_RUN_INDEX.md) (via [`docs/index.md`](../../docs/index.md))
