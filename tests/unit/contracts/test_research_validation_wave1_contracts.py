"""
Wave-1 Research Validation contracts (#4264/#4265/#4266).

test_id: tc_research_validation_wave1_001
test_name: research_validation_wave1_contract_surfaces
test_type: Wissens-Test / Bauteil-Test
cdb_area: contracts
rule_ref: free-form-text-not-valid-handoff; missing-evidence-no-pass; paper-candidate-not-live-go
decision_ref: research-validation-wave1
issue_ref: #4264 #4265 #4266
pr_ref: pending
evidence_ref: docs/contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md
security_relevant: false
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = PROJECT_ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"
CANON = (
    PROJECT_ROOT / "docs" / "research" / "CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md"
)
OVERVIEW = CONTRACTS / "CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md"

CONTRACT_SPECS = (
    (
        "cdb.research_brief.v1",
        "cdb_research_brief.v1.schema.json",
        "cdb_research_brief_valid.json",
    ),
    (
        "cdb.strategy_candidate.v1",
        "cdb_strategy_candidate.v1.schema.json",
        "cdb_strategy_candidate_valid.json",
    ),
    (
        "cdb.validation_manifest.v1",
        "cdb_validation_manifest.v1.schema.json",
        "cdb_validation_manifest_valid.json",
    ),
    (
        "cdb.candidate_evidence.v1",
        "cdb_candidate_evidence.v1.schema.json",
        "cdb_candidate_evidence_valid.json",
    ),
    (
        "cdb.decision_record.v1",
        "cdb_decision_record.v1.schema.json",
        "cdb_decision_record_valid.json",
    ),
)

REQUIRED_GATES = {
    "contract_completeness",
    "dataset_quality",
    "deterministic_baseline_replay",
    "execution_cost_model",
    "parameter_sensitivity",
    "walk_forward",
    "bootstrap_or_monte_carlo",
    "scenario_stress",
    "arvp_replay",
    "regime_scorecard",
    "replay_vs_paper",
}


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("schema_version", "schema_name", "example_name"),
    CONTRACT_SPECS,
)
def test_schema_valid_and_example_passes(
    schema_version: str, schema_name: str, example_name: str
) -> None:
    schema = _load(CONTRACTS / schema_name)
    example = _load(EXAMPLES / example_name)
    Draft7Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert example["schema_version"] == schema_version
    errors = list(Draft7Validator(schema).iter_errors(example))
    assert errors == []


@pytest.mark.unit
def test_free_form_text_is_not_valid_strategy_candidate() -> None:
    schema = _load(CONTRACTS / "cdb_strategy_candidate.v1.schema.json")
    payload = {"text": "just an agent idea, promote please"}
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


@pytest.mark.unit
def test_incomplete_candidate_rejected_when_required_fields_missing() -> None:
    schema = _load(CONTRACTS / "cdb_strategy_candidate.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    del payload["falsifiable_hypothesis"]
    del payload["validation_plan"]
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


@pytest.mark.unit
def test_candidate_version_change_requires_new_version_field() -> None:
    payload = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    mutated = deepcopy(payload)
    mutated["candidate_version"] = "v2"
    mutated["parent_version"] = "v1"
    mutated["parameters"] = {**payload["parameters"], "breakout_buffer": 0.001}
    schema = _load(CONTRACTS / "cdb_strategy_candidate.v1.schema.json")
    assert list(Draft7Validator(schema).iter_errors(mutated)) == []
    assert mutated["candidate_version"] != payload["candidate_version"]
    assert mutated["parent_version"] == payload["candidate_version"]


@pytest.mark.unit
def test_validation_manifest_requires_all_gates() -> None:
    schema = _load(CONTRACTS / "cdb_validation_manifest.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_validation_manifest_valid.json")
    assert set(payload["requested_gates"]) == REQUIRED_GATES
    payload["requested_gates"] = sorted(REQUIRED_GATES - {"walk_forward"})
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


@pytest.mark.unit
def test_evidence_requires_run_id_version_hashes_and_friction() -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    for key in (
        "run_id",
        "candidate_version",
        "artifact_hashes",
        "fees",
        "spread",
        "slippage",
    ):
        assert key in payload
    assert "return_ratio" in payload["gross_results"]
    assert "return_ratio" in payload["net_results"]
    assert set(payload["gross_results"]) == {"return_ratio", "max_drawdown"}
    assert set(payload["net_results"]) == {"return_ratio", "max_drawdown"}
    broken = deepcopy(payload)
    del broken["artifact_hashes"]
    assert list(Draft7Validator(schema).iter_errors(broken))


@pytest.mark.unit
def test_missing_evidence_cannot_claim_pass_without_safety_flag() -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    payload["overall_verdict"] = "PASS"
    payload["safety_boundaries"]["missing_evidence_cannot_pass"] = False
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


def _pass_compatible_gate_results() -> list[dict]:
    return [
        {
            "gate": gate,
            "verdict": "PASS",
            "notes": f"{gate} complete for PASS fixture.",
        }
        for gate in sorted(REQUIRED_GATES)
    ]


@pytest.mark.unit
def test_overall_pass_requires_all_required_gates_pass_compatible() -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    payload["overall_verdict"] = "PASS"
    payload["gate_results"] = _pass_compatible_gate_results()
    # One WARNING remains PASS-compatible.
    payload["gate_results"][0]["verdict"] = "WARNING"
    assert list(Draft7Validator(schema).iter_errors(payload)) == []


@pytest.mark.unit
def test_overall_pass_rejected_when_required_gate_insufficient() -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    payload["overall_verdict"] = "PASS"
    # Live fixture mixes PASS/WARNING/INSUFFICIENT_DATA — must not validate as PASS.
    assert any(row["verdict"] == "INSUFFICIENT_DATA" for row in payload["gate_results"])
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


@pytest.mark.unit
def test_overall_pass_rejected_when_required_gates_missing() -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    payload["overall_verdict"] = "PASS"
    payload["gate_results"] = [
        {
            "gate": "contract_completeness",
            "verdict": "PASS",
            "notes": "Only one gate present.",
        }
    ]
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


@pytest.mark.unit
@pytest.mark.parametrize("bad_verdict", ["FAIL", "BLOCKED", "INSUFFICIENT_DATA"])
def test_overall_pass_rejected_for_non_pass_compatible_gate(
    bad_verdict: str,
) -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    payload["overall_verdict"] = "PASS"
    payload["gate_results"] = _pass_compatible_gate_results()
    payload["gate_results"][3]["verdict"] = bad_verdict
    errors = list(Draft7Validator(schema).iter_errors(payload))
    assert errors


@pytest.mark.unit
def test_non_pass_overall_still_allows_insufficient_gate_evidence() -> None:
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    assert payload["overall_verdict"] == "INSUFFICIENT_DATA"
    assert list(Draft7Validator(schema).iter_errors(payload)) == []


@pytest.mark.unit
def test_decision_record_forbids_live_go_semantics() -> None:
    schema = _load(CONTRACTS / "cdb_decision_record.v1.schema.json")
    payload = _load(EXAMPLES / "cdb_decision_record_valid.json")
    assert payload["paper_candidate_is_not_live_go"] is True
    assert "live_capital_allocation" in payload["forbidden_next_actions"]
    broken = deepcopy(payload)
    broken["paper_candidate_is_not_live_go"] = False
    assert list(Draft7Validator(schema).iter_errors(broken))


@pytest.mark.unit
def test_canon_and_overview_document_roles_and_lineage() -> None:
    canon = CANON.read_text(encoding="utf-8")
    overview = OVERVIEW.read_text(encoding="utf-8")
    for needle in (
        "Hermes",
        "TickerSage",
        "Tarot",
        "Gmail",
        "Calendar",
        "READY_FOR_VALIDATION",
        "profitability_candidate_contract.v1",
    ):
        assert needle in canon
    assert (
        "does not replace" in overview.lower() or "do not replace" in overview.lower()
    )
    assert "PAPER_CANDIDATE" in overview
    assert "profitability_evidence_packet.v1" in overview
    assert "overall_verdict PASS" in overview
    assert "`PASS` or `WARNING`" in overview
    assert "missing_evidence_cannot_pass" in overview


@pytest.mark.unit
def test_lineage_schemas_still_present_not_replaced() -> None:
    assert (CONTRACTS / "profitability_candidate_contract.v1.schema.json").is_file()
    assert (CONTRACTS / "profitability_evidence_packet.v1.schema.json").is_file()
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    evidence = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    assert (
        candidate["lineage_refs"]["profitability_candidate_contract"]
        == "profitability_candidate_contract.v1"
    )
    assert (
        evidence["lineage_refs"]["profitability_evidence_packet"]
        == "profitability_evidence_packet.v1"
    )
