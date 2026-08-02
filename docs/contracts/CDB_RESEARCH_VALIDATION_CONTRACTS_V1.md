# CDB Research Validation Contracts v1

**Status:** Wave-1 + Wave-2 + Wave-3 security/orchestration/pilot surface (#4265–#4269, #4271, #4270, #4272)
**Parent:** #4263
**Canon:** [`docs/research/CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md`](../research/CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md)
**Mode:** Schemas + examples + docs + read-only cross-contract helpers
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
| `cdb.source_evidence.v1` | `cdb_source_evidence.v1.schema.json` | `examples/cdb_source_evidence_binance_valid.json` (+5 sources) | #4267 |
| `cdb.compiler_report.v1` | `cdb_compiler_report.v1.schema.json` | `examples/cdb_compiler_report_valid.json` | #4268 |
| `cdb.candidate_registry_entry.v1` | `cdb_candidate_registry_entry.v1.schema.json` | `examples/cdb_candidate_registry_entry_valid.json` | #4269 |
| `cdb.candidate_transition.v1` | `cdb_candidate_transition.v1.schema.json` | `examples/cdb_candidate_transition_paper_valid.json` | #4269 |
| `cdb.research_security_gate.v1` | `cdb_research_security_gate.v1.schema.json` | `examples/cdb_research_security_gate_valid.json` | #4271 |
| `cdb.hermes_orchestration_run.v1` | `cdb_hermes_orchestration_run.v1.schema.json` | `examples/cdb_hermes_orchestration_run_valid.json` | #4270 |
| `cdb.research_validation_pilot.v1` | `cdb_research_validation_pilot.v1.schema.json` | `examples/cdb_research_validation_pilot_valid.json` | #4272 |

Wave-2 docs:

- [`docs/research/CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md`](../research/CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md)
- [`docs/research/CDB_STRATEGY_CANDIDATE_COMPILER_V1.md`](../research/CDB_STRATEGY_CANDIDATE_COMPILER_V1.md)
- [`docs/research/CDB_GITHUB_CANDIDATE_REGISTRY_V1.md`](../research/CDB_GITHUB_CANDIDATE_REGISTRY_V1.md)

Wave-3 security / orchestration / pilot docs:

- [`docs/research/CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md`](../research/CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md)
- [`docs/research/CDB_HERMES_VALIDATION_CHIEF_ORCHESTRATION_CONTRACT_V1.md`](../research/CDB_HERMES_VALIDATION_CHIEF_ORCHESTRATION_CONTRACT_V1.md)
- [`docs/research/CDB_RESEARCH_VALIDATION_PILOT_SPEC_V1.md`](../research/CDB_RESEARCH_VALIDATION_PILOT_SPEC_V1.md)

Cross-contract validators (relational invariants):

- `tools/research_validation/wave2_cross_contract.py`
- `tools/research_validation/security_gates_cross_contract.py`
- `tools/research_validation/hermes_orchestration_cross_contract.py`
- `tools/research_validation/pilot_spec_cross_contract.py`

## Wave-2 hardenings of Wave-1 surfaces (PMR)

| ID | Surface | Enforcement |
|---|---|---|
| PMR-01 | Candidate version lineage | `validate_candidate_lineage` — v1 null parent; vN requires exact `v{N-1}`; reject self/future |
| PMR-02 | StrategyCandidate provenance | Schema requires `research_brief_version` + `research_brief_content_hash` |
| PMR-03 | DecisionRecord `allowed_next_actions` | Narrow safe enum; live/capital/risk-bypass/auto-promotion invalid |
| PMR-04 | PAPER_CANDIDATE transition | Validator binds DecisionRecord + PASS evidence for exact candidate_version |

## Completeness / READY_FOR_VALIDATION

`cdb.strategy_candidate.v1` requires all listed candidate fields and an explicit
`completeness_status`:

- `INCOMPLETE` — not eligible for Hermes validation
- `READY_FOR_VALIDATION` — only after required fields, provenance, and
  uncertainty are present

Any candidate mutation that changes falsifiable content must mint a new
`candidate_version` (and set `parent_version` to the prior version). Lineage is
enforced by the Wave-2 validator, not by documentation alone.

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
- `overall_verdict PASS` is allowed only when all 11 required gates are present
  and each gate verdict is `PASS` or `WARNING`
- Missing gates or gate verdicts `INSUFFICIENT_DATA`, `FAIL`, or `BLOCKED`
  cannot validate as overall `PASS` (schema-enforced; the const
  `missing_evidence_cannot_pass: true` alone is not sufficient)
- Decision records must list allowed and forbidden next actions from the safe
  vocabulary (PMR-03)
- `paper_candidate_is_not_live_go` is always `true`
- Registry `PAPER_CANDIDATE` additionally requires PASS-compatible evidence
  (PMR-04)

## Security / provenance / integrity (#4271)

`cdb.research_security_gate.v1` is the fail-closed handoff gate between
SourceEvidence/Candidate compilation and validation orchestration.

Hard rules:

- External research content remains `UNTRUSTED_INPUT` (data, never instructions)
- Missing provenance or missing content/artifact hashes cannot PASS
- Injection or secret/credential suspicion cannot yield overall `PASS`
- `FAIL` / `BLOCKED` / `REVIEW_REQUIRED` on required checks cannot yield overall `PASS`
- Head / candidate / manifest / dataset drift invalidates PASS evidence
- Security/integrity PASS ≠ semantic correctness ≠ validation authority ≠ Live-Go
- Codex Security is specified as a pre-implementation review gate; this slice
  does not execute scanners (`scanner_executed: false`)

## Hermes Validation Chief orchestration (#4270)

`cdb.hermes_orchestration_run.v1` is the fail-closed orchestration envelope that
binds a validation run to candidate, manifest, security-gate, head, dataset, and
artifact hashes.

Hard rules:

- Technical and domain failures are structurally separated
- Automatic retries apply only to explicitly retryable technical failures
- Bindings are immutable across attempts; drift requires a new `run_id`
- Security-gate `FAIL` / `BLOCKED` / `REVIEW_REQUIRED` cannot yield orchestration `PASS`
- Incomplete evidence or invalidating drift cannot yield orchestration `PASS`
- Orchestration `PASS` ≠ validation authority ≠ Live-Go ≠ paper/capital promotion
- No productive Hermes/worker execution in this contract slice

## Research Validation Pilot Spec (#4272)

`cdb.research_validation_pilot.v1` is the fail-closed **SPECIFICATION_ONLY**
contract for three planned end-to-end candidates
(`breakout`, `liquidity_or_volume_filter`, `on_chain_regime_filter`).

Hard rules:

- Exactly three distinct `candidate_key` values with the issue-required source pairs
- Shared contract versions, validation profile, security gates, and Hermes path
- Fees, spread, slippage, and latency/delay required; pessimistic scenario is adverse
- Expected evidence/decision artifacts are PLANNED/NOT_RUN slots only
- No invented PASS / Decision / provider / dataset-hash claims
- TickerSage visualization-only; all authority flags false; LR NO-GO
- Pilot execution is out of scope for this contract slice

## Producer / Consumer (Wave-2)

| Contract | Producer | Consumer |
|---|---|---|
| SourceEvidence | Research adapters (future) / fixtures | Compiler |
| CompilerReport | Compiler (future) | Registry / Hermes |
| ResearchSecurityGate | Security/provenance steward (future) / fixtures | Registry / Hermes handoff |
| HermesOrchestrationRun | Hermes Validation Chief (future) / fixtures | Evidence / Decision steward |
| ResearchValidationPilot | Pilot steward (docs/fixtures only in #4272) | Future execution session (not this slice) |
| Registry entry/transition | Humans / delivery agents (repo artifacts) | Completeness / audit |

## Lineage boundary (do not replace)

| Existing surface | Issues | Relationship |
|---|---|---|
| `profitability_candidate_contract.v1` | #3034 / #3043 | Remains SSOT for profitability candidates |
| `profitability_evidence_packet.v1` | #3043 / #4022 | Remains SSOT for PEP / ARVP assembly |

Wave-1/2 contracts are adjacent orchestration envelopes. They may reference
profitability artifacts; they must not redefine or supersede them.

## Non-goals

- Runtime / runner / adapter implementation
- Productive DB registry
- Automatic strategy promotion
- Live / Paper / Echtgeld GO
- ML / RL training
- Security scanner / plugin / worker / Hermes runtime implementation
  (contract + tests only for #4271 / #4270)
- Pilot execution / provider fetches / invented evidence
  (specification + tests only for #4272)
