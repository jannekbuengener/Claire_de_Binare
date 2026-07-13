# ARVP Vacation Tools (`tools/arvp_vacation`)

Offline operator tooling for ARVP vacation batch campaigns and the research-only evidence pipeline.

## Scope

- **Not** a BLUE/RED runtime service — Python batch tools and CLIs only.
- Writes local campaign artifacts under operator-controlled paths (for example `artifacts/arvp_vacation/`).
- No productive database persistence, no order/fill execution, no strategy or live authorization.
- LR remains **NO-GO**.

## Pipeline overview

| Step | Module | Contract / output |
|---|---|---|
| Batch orchestration | `coordinator.py`, `job_runner.py`, `queue_store.py` | Vacation queue state and replay job artifacts |
| Metric extraction | `strategy_metric_extraction.py` | `arvp_strategy_metrics.v1` |
| Candidate evidence assembly | `candidate_evidence_assembly.py` → [`services/validation/arvp_candidate_evidence_assembler.py`](../../services/validation/arvp_candidate_evidence_assembler.py) | `profitability_evidence_packet.v1` bundle |
| League table report | `league_table_report.py` → [`services/validation/profitability_league_table_report_assembler.py`](../../services/validation/profitability_league_table_report_assembler.py) | `profitability_league_table_report.v1` |

Validation library surface: [`services/validation/README.md`](../../services/validation/README.md).

## Operator CLIs

```bash
# Extract normalized strategy metrics from a vacation queue state
python -m tools.arvp_vacation.strategy_metric_extraction --help

# Assemble candidate PEP bundles
python -m tools.arvp_vacation.candidate_evidence_assembly \
    --queue-state path/to/queue_state.json

# Build governance-safe league table report
python -m tools.arvp_vacation.league_table_report \
    --assemble-from-queue-state path/to/queue_state.json \
    --report-id pltr-arvp-historical-batch \
    --hash-only
```

Run `--help` on each module for the authoritative argument list.

## Evidence and contracts

- [`docs/evidence/arvp_3990_strategy_metric_extraction.md`](../../docs/evidence/arvp_3990_strategy_metric_extraction.md)
- [`docs/evidence/arvp_3990_candidate_evidence_assembly.md`](../../docs/evidence/arvp_3990_candidate_evidence_assembly.md)
- [`docs/evidence/arvp_3990_strategy_league_table.md`](../../docs/evidence/arvp_3990_strategy_league_table.md)
- [`docs/contracts/arvp_strategy_metrics.v1.schema.json`](../../docs/contracts/arvp_strategy_metrics.v1.schema.json)
- [`docs/contracts/profitability_evidence_packet.v1.schema.json`](../../docs/contracts/profitability_evidence_packet.v1.schema.json)
- [`docs/contracts/profitability_league_table_report.v1.schema.json`](../../docs/contracts/profitability_league_table_report.v1.schema.json)

Architecture inventory: [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md), [`knowledge/governance/SERVICE_CATALOG.md`](../../knowledge/governance/SERVICE_CATALOG.md).
