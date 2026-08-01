# CDB Research Validation Contracts v1

**Status:** Wave-1 contract surface (#4265 / #4266)  
**Parent:** #4263  
**Canon:** [`docs/research/CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md`](../research/CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md)  
**Mode:** Schemas + examples + docs only  
**Live-Readiness:** NO-GO  

## Purpose

Machine-readable handoff contracts for Research → Candidate → Validation →
Decision. Free-form agent text is never a valid handoff.

## Contract inventory

| Contract | Schema | Example | Issue |
|---|---|---|---|
| `cdb.research_brief.v1` | `cdb_research_brief.v1.schema.json` | `examples/cdb_research_brief_valid.json` | #4265 |
| `cdb.strategy_candidate.v1` | `cdb_strategy_candidate.v1.schema.json` | `examples/cdb_strategy_candidate_valid.json` | #4265 |
| `cdb.validation_manifest.v1` | `cdb_validation_manifest.v1.schema.json` | `examples/cdb_validation_manifest_valid.json` | #4266 |
| `cdb.candidate_evidence.v1` | `cdb_candidate_evidence.v1.schema.json` | `examples/cdb_candidate_evidence_valid.json` | #4266 |
| `cdb.decision_record.v1` | `cdb_decision_record.v1.schema.json` | `examples/cdb_decision_record_valid.json` | #4266 |

## Completeness / READY_FOR_VALIDATION

`cdb.strategy_candidate.v1` requires all listed candidate fields and an explicit
`completeness_status`:

- `INCOMPLETE` — not eligible for Hermes validation
- `READY_FOR_VALIDATION` — only after required fields, provenance, and
  uncertainty are present

Any candidate mutation that changes falsifiable content must mint a new
`candidate_version` (and set `parent_version` to the prior version).

## Validation gates, verdicts, decisions

Required gates in `cdb.validation_manifest.v1`:

1. contract_completeness
2. dataset_quality
3. deterministic_baseline_replay
4. execution_cost_model
5. parameter_sensitivity
6. walk_forward
7. bootstrap_or_monte_carlo
8. scenario_stress
9. arvp_replay
10. regime_scorecard
11. replay_vs_paper

Verdicts: `PASS | WARNING | FAIL | BLOCKED | INSUFFICIENT_DATA`  
Decisions: `REJECT | REVISE | PARK | PAPER_CANDIDATE`

Rules:

- Evidence must include `run_id`, `candidate_version`, and artifact hashes
- Gross and net results are separate objects
- Fees, spread, and slippage are required
- Missing evidence cannot produce overall `PASS`
- Decision records must list allowed and forbidden next actions
- `paper_candidate_is_not_live_go` is always `true`

## Lineage boundary (do not replace)

| Existing surface | Issues | Relationship |
|---|---|---|
| `profitability_candidate_contract.v1` | #3034 / #3043 | Remains SSOT for profitability candidates |
| `profitability_evidence_packet.v1` | #3043 / #4022 | Remains SSOT for PEP / ARVP assembly |

Wave-1 contracts are adjacent orchestration envelopes. They may reference
profitability artifacts; they must not redefine or supersede them.

## Non-goals

- Runtime / runner implementation
- Productive DB registry
- Automatic strategy promotion
- Live / Paper / Echtgeld GO
- ML / RL training
