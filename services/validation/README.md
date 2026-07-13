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
| `profitability_evidence_packet_assembler.py` | Manual-path Evidence Packet Assembler — builds `profitability_evidence_packet.v1` from explicit validated artifact paths |
| `arvp_candidate_evidence_assembler.py` | ARVP Candidate Evidence Assembler — aggregates `arvp_strategy_metrics.v1` into deterministic PEP bundles (one PEP per candidate); `ranking_ready=false` |
| `profitability_league_scorer.py` | Offline **Strategy League scorer v1** — Formula v1 scoring from PEP(s) to `profitability_league_table_report.v1` |
| `profitability_league_table_report_assembler.py` | Governance-safe league table report assembler — ARVP rankability gates, no forced winner; uses scorer internally |

## ARVP vacation evidence pipeline (offline)

Research-only chain (no runtime service, no productive DB writes):

1. Vacation batch runner — [`tools/arvp_vacation/coordinator.py`](../../tools/arvp_vacation/coordinator.py)
2. Strategy metric extraction — [`tools/arvp_vacation/strategy_metric_extraction.py`](../../tools/arvp_vacation/strategy_metric_extraction.py) → `arvp_strategy_metrics.v1`
3. Candidate evidence assembly — `arvp_candidate_evidence_assembler.py` → `profitability_evidence_packet.v1`
4. League table report assembly — `profitability_league_table_report_assembler.py` → `profitability_league_table_report.v1`

Operator CLIs live under [`tools/arvp_vacation/`](../../tools/arvp_vacation/README.md). LR remains **NO-GO**.

## Usage

```bash
# Typisch über pytest oder dedizierte Scripts/Make-Targets
pytest -q tests/unit/validation/

# Manual-path Evidence Packet Assembler (offline, deterministisch)
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
    --out-json out/league_report.json

# ARVP candidate evidence assembly (metrics bundle or queue state)
python -m tools.arvp_vacation.candidate_evidence_assembly \
    --metrics-bundle path/to/metrics_bundle.json

python -m tools.arvp_vacation.candidate_evidence_assembly \
    --queue-state path/to/queue_state.json \
    --hash-only

# Governance-safe league table report (from assembled bundle dir)
python -m tools.arvp_vacation.league_table_report \
    --assemble-from-queue-state path/to/queue_state.json \
    --report-id pltr-arvp-historical-batch \
    --hash-only
```

### Scorer vs governance report assembler

| | `profitability_league_scorer.py` | `profitability_league_table_report_assembler.py` |
|---|---|---|
| Role | Formula v1 scoring engine / standalone CLI | Governance-safe multi-candidate report builder |
| Input | One or more PEP files | PEP bundle directory, metrics bundle, or queue state |
| Output | `profitability_league_table_report.v1` | Extended governance report with rankability gates |
| Official ranking | Applies hard gates; may emit sentinel scores | Enforces ARVP rankability; may leave `winner=null`, `official_ranking=[]` |
| Operator entry | `python -m services.validation.profitability_league_scorer` | `python -m tools.arvp_vacation.league_table_report` |

Neither component authorizes strategy promotion, live trading, or capital allocation. LR remains **NO-GO**.

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
- `tests/unit/arvp/`
- [`tools/arvp_vacation/README.md`](../../tools/arvp_vacation/README.md)
- [`docs/contracts/profitability_evidence_packet.v1.schema.json`](../../docs/contracts/profitability_evidence_packet.v1.schema.json)
- [`docs/contracts/profitability_league_table_report.v1.schema.json`](../../docs/contracts/profitability_league_table_report.v1.schema.json)
- [`docs/contracts/arvp_strategy_metrics.v1.schema.json`](../../docs/contracts/arvp_strategy_metrics.v1.schema.json)
- `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md`
- [`docs/evidence/SHADOW_SOAK_RUN_INDEX.md`](../../docs/evidence/SHADOW_SOAK_RUN_INDEX.md) (via [`docs/index.md`](../../docs/index.md))
