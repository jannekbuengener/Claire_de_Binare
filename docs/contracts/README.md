# Contracts (`docs/contracts/`)

Repo-backed JSON/YAML schemas und Contract-Dokumente für Messages, Replay und Context Tooling.

## Layout

| Area | Path | Notes |
|---|---|---|
| Message schemas | `market_data.schema.json`, `signal.schema.json`, … | CI/validation |
| PR acceptance | `pr_acceptance_skill_family.v1.schema.json (wiring, gap, completeness, conductor)` | PR-Acceptance Skill Family v1 envelope (#4207/#4208) |
| Context tooling | [`context_tooling/`](context_tooling/) | MCP evidence contracts |
| Examples | [`examples/`](examples/) | Valid/invalid fixtures |
| Replay | [`REPLAY_CONTRACTS_AND_DETERMINISM.md`](REPLAY_CONTRACTS_AND_DETERMINISM.md) | Determinism rules |
| Profitability | `profitability_candidate_contract.v1.schema.json`, `profitability_evidence_packet.v1.schema.json` | Strategy candidate and evidence packet research contracts |
| Research Validation (Wave 1) | `cdb_research_brief.v1.schema.json`, `cdb_strategy_candidate.v1.schema.json`, `cdb_validation_manifest.v1.schema.json`, `cdb_candidate_evidence.v1.schema.json`, `cdb_decision_record.v1.schema.json` | Research-to-Hermes orchestration contracts (#4264–#4266); adjacent to profitability lineage, does not replace it — see [`CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md`](CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md) |
| Research Validation (Wave 2) | `cdb_source_evidence.v1.schema.json`, `cdb_compiler_report.v1.schema.json`, `cdb_candidate_registry_entry.v1.schema.json`, `cdb_candidate_transition.v1.schema.json` | SourceEvidence adapters, Strategy Candidate Compiler report, GitHub-backed registry entry/transition (#4267–#4269); extends Wave 1 without replacing profitability/ARVP — see [`CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md`](CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md) |
| Research Validation (Wave 3 / Security) | `cdb_research_security_gate.v1.schema.json` | Security, provenance and integrity gate for untrusted research handoff (#4271); security PASS ≠ validation authority — see [`CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md`](../research/CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md) |
| Research Validation (Wave 3 / Hermes Orchestration) | `cdb_hermes_orchestration_run.v1.schema.json` | Hermes Validation Chief orchestration run (#4270); technical/domain failure split, retry policy, security-gate + drift bindings; orchestration PASS ≠ validation/live authority — see [`CDB_HERMES_VALIDATION_CHIEF_ORCHESTRATION_CONTRACT_V1.md`](../research/CDB_HERMES_VALIDATION_CHIEF_ORCHESTRATION_CONTRACT_V1.md) |
| Profitability evidence inputs | `profitability_replay_report.v1.schema.json`, `profitability_harvester_ref.v1.schema.json`, `shadow_comparison.v1.schema.json`, `arvp_regime_scorecard.v1.schema.json` | Offline assembler input contracts for canonical replay, harvester provenance, compare, and regime scorecard artifacts |
| Profitability data quality | `profitability_dataset_quality_report.v1.schema.json` | Dataset quality gate report for candidate validation |
| Profitability ARVP batch | `profitability_arvp_batch_manifest.v1.schema.json`, `profitability_arvp_batch_summary.v1.schema.json` | Multi-candidate ARVP batch runner design contracts |
| Profitability scenario packs | `profitability_scenario_pack_catalog.v1.schema.json`, `profitability_scenario_stress_summary.v1.schema.json` | Stress-scenario catalog and candidate stress summary contracts |
| Profitability execution economics | `profitability_execution_economics_model.v1.schema.json`, `profitability_execution_economics_assessment.v1.schema.json` | Net-economics model and candidate cost-attribution contracts |
| Profitability league table | `profitability_league_table_model.v1.schema.json`, `profitability_league_table_report.v1.schema.json` | Ranking model and recommendation report contracts |
| Profitability capital sleeves | `profitability_capital_sleeve_model.v1.schema.json`, `profitability_paper_accounting_report.v1.schema.json` | Sleeve-governance model and paper-accounting report contracts |
| Profitability control room | `profitability_control_room_requirements.v1.schema.json`, `profitability_control_room_snapshot.v1.schema.json` | Control-room requirements and read-only snapshot contracts |
| ARVP Gearbox (design) | `strategy_gear_registry.v1.schema.json`, `selector_decision.v1.schema.json`, `gear_reason_codes.v1.schema.json`, `protective_idle.v1.schema.json`, `loop_boundary.v1.schema.json` | Design-only gearbox contracts ([#3913](https://github.com/jannekbuengener/Claire_de_Binare/issues/3913)); selector output is not trade approval |

## Related canon (not duplicated here)

| Domain | Canonical path |
|---|---|
| Strategy contracts (narrative) | [`knowledge/contracts/README.md`](../../knowledge/contracts/README.md) |
| Runtime decision bundle | [`core/contracts/`](../../core/contracts/) (`decision_contract_v1`) |
| Market state (risk input) | [`docs/governance/MARKET_STATE_CONTRACT_V1.md`](../governance/MARKET_STATE_CONTRACT_V1.md) |

## SSOT boundary

Contracts definieren Verhalten; sie ersetzen weder LR-Verdikt noch Board-Stage. LR **NO-GO**.
