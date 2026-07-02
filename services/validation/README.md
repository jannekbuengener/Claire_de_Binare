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
| `profitability_league_scorer.py` | Offline **Strategy League scorer v1** — fail-closed; turns the Formula v1 rules (#3682) into an executable scorer that reads `profitability_evidence_packet.v1` and emits a schema-validated `profitability_league_table_report.v1`. Decision support only. |

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

# Offline Strategy League scorer v1 (read-only, fail-closed)
python -m services.validation.profitability_league_scorer \
    --pep path/to/evidence_packet_a.json \
    --pep path/to/evidence_packet_b.json \
    --report-id pltr-my-league-run-1 \
    --out-json out/league_report.json   # omit --out-json to print to stdout
```

### Offline Strategy League scorer v1

- **Where:** `services/validation/profitability_league_scorer.py`
  (formula: [`docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md`](../../docs/strategy/CDB_PROFITABILITY_LEAGUE_SCORING_FORMULA_V1.md)).
- **What it can do:** compute the six `dimension_scores` and the weighted
  `total_score` from `profitability_evidence_packet.v1` inputs, apply the
  fail-closed hard gates, and emit a schema-validated
  `profitability_league_table_report.v1`. Hard-gate failure ⇒ sentinel mode
  (`ranking_ready=false`, all scores `0.0`). `PARK` is treated as a research
  hold; a missing paper reference (`replay_vs_paper_status=not_run`/
  `missing_reference`, `simulator_drift=not_assessed`/`unusable`) is a blocker.
- **What it does NOT authorize:** no runtime, no BLUE/RED change, no DB/secrets
  mutation, no candidate promotion, no capital allocation.
  `PROMOTE_TO_NEXT_RESEARCH_GATE` stays an advisory label. LR remains **NO-GO**.

## Canonical References

- `services/validation/pipeline.py`
- `tests/unit/validation/`
- `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md`
- [`docs/evidence/SHADOW_SOAK_RUN_INDEX.md`](../../docs/evidence/SHADOW_SOAK_RUN_INDEX.md) (via [`docs/index.md`](../../docs/index.md))
