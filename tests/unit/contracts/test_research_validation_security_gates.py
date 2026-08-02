"""
Security / Provenance / Integrity gates for Research Validation (#4271).

test_id: tc_research_validation_security_gates_001
test_name: research_validation_security_provenance_integrity_gates
test_type: Wissens-Test / Schutz-Test
cdb_area: contracts
rule_ref: untrusted-input; provenance-hash; injection-fail-closed; secret-fail-closed; no-authority-escalation
decision_ref: research-validation-wave3-security
issue_ref: #4271 #4263
pr_ref: pending
evidence_ref: docs/research/CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tools.research_validation.security_gates_cross_contract import (
    FORBIDDEN_NEXT_ACTIONS,
    security_pass_grants_validation_authority,
    validate_drift_invalidates_pass,
    validate_fail_closed_verdicts,
    validate_forbidden_actions,
    validate_integrity_bindings,
    validate_security_gate_record,
    validate_source_provenance,
)
from tools.research_validation.wave2_cross_contract import (
    validate_decision_allowed_actions,
    validate_source_evidence_non_authority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = PROJECT_ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"
SCHEMA_NAME = "cdb_research_security_gate.v1.schema.json"
FIXTURE_NAME = "cdb_research_security_gate_valid.json"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _valid_gate() -> dict:
    return _load(EXAMPLES / FIXTURE_NAME)


def _errors(payload: dict) -> list:
    schema = _load(CONTRACTS / SCHEMA_NAME)
    return list(Draft7Validator(schema).iter_errors(payload))


def _set_check_verdict(gate: dict, check_id: str, verdict: str) -> None:
    for row in gate["check_results"]:
        if row["check_id"] == check_id:
            row["verdict"] = verdict
            return
    raise KeyError(check_id)


@pytest.mark.unit
def test_valid_security_gate_matches_schema_and_cross_contract() -> None:
    gate = _valid_gate()
    assert gate["schema_version"] == "cdb.research_security_gate.v1"
    assert gate["content_classification"] == "UNTRUSTED_INPUT"
    assert _errors(gate) == []
    assert validate_security_gate_record(gate) == []


@pytest.mark.unit
def test_missing_source_provenance_rejected() -> None:
    gate = _valid_gate()
    gate["source_provenance"] = []
    schema_errors = _errors(gate)
    assert schema_errors
    cross = validate_source_provenance(gate)
    assert any("source_provenance" in err for err in cross)


@pytest.mark.unit
def test_missing_source_provenance_fields_rejected() -> None:
    gate = _valid_gate()
    gate["source_provenance"] = [
        {
            "source_id": "se-incomplete",
            "provider": "binance",
            # locator missing
            "content_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
        }
    ]
    assert _errors(gate)
    cross = validate_source_provenance(gate)
    assert any("locator" in err for err in cross)


@pytest.mark.unit
def test_missing_content_or_artifact_hash_rejected() -> None:
    gate = _valid_gate()
    gate["integrity_bindings"]["artifact_hashes"] = []
    assert _errors(gate)
    cross = validate_integrity_bindings(gate)
    assert any("artifact_hashes" in err for err in cross)

    gate2 = _valid_gate()
    gate2["source_provenance"][0]["content_hash"] = "not-a-hash"
    assert _errors(gate2)
    cross2 = validate_source_provenance(gate2)
    assert any("content_hash" in err for err in cross2)


@pytest.mark.unit
def test_injection_suspicion_cannot_be_overall_pass() -> None:
    gate = _valid_gate()
    gate["injection_assessment"] = {
        "suspicion": True,
        "verdict": "REVIEW_REQUIRED",
        "notes": "Embedded instruction-like text detected in untrusted claim.",
    }
    _set_check_verdict(gate, "prompt_injection_resistance", "REVIEW_REQUIRED")
    gate["overall_verdict"] = "PASS"
    assert _errors(gate)
    cross = validate_fail_closed_verdicts(gate)
    assert any("injection" in err for err in cross)


@pytest.mark.unit
def test_secret_credential_suspicion_cannot_be_overall_pass() -> None:
    gate = _valid_gate()
    gate["sensitive_data_assessment"] = {
        "suspicion": True,
        "verdict": "BLOCKED",
        "redactions": [
            {"field_path": "payload.api_token", "data_class": "token"},
        ],
        "notes": "Credential-like field suspected; handoff blocked.",
    }
    _set_check_verdict(gate, "sensitive_data_exclusion", "BLOCKED")
    gate["overall_verdict"] = "PASS"
    assert _errors(gate)
    cross = validate_fail_closed_verdicts(gate)
    assert any("secret" in err or "credential" in err for err in cross)


@pytest.mark.unit
@pytest.mark.parametrize("blocking", ["BLOCKED", "FAIL", "REVIEW_REQUIRED"])
def test_blocking_check_prevents_pass_evaluation(blocking: str) -> None:
    gate = _valid_gate()
    _set_check_verdict(gate, "read_only_enforcement", blocking)
    gate["overall_verdict"] = "PASS"
    assert _errors(gate)
    cross = validate_fail_closed_verdicts(gate)
    assert any("PASS forbidden" in err for err in cross)


@pytest.mark.unit
def test_security_pass_does_not_grant_validation_authority() -> None:
    gate = _valid_gate()
    assert gate["overall_verdict"] == "PASS"
    assert gate["authority_boundaries"]["research_apps_validation_authority"] is False
    assert (
        gate["authority_boundaries"]["security_integrity_implies_semantic_correctness"]
        is False
    )
    assert security_pass_grants_validation_authority(gate) is False
    assert validate_security_gate_record(gate) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "drift",
    ["HEAD_DRIFT", "CANDIDATE_DRIFT", "MANIFEST_DRIFT", "DATASET_DRIFT"],
)
def test_drift_invalidates_evidence(drift: str) -> None:
    gate = _valid_gate()
    gate["drift_status"] = drift
    gate["overall_verdict"] = "PASS"
    assert _errors(gate)
    cross = validate_drift_invalidates_pass(gate)
    assert any("invalidates" in err or "drift_status" in err for err in cross)


@pytest.mark.unit
def test_forbidden_live_capital_risk_auto_promotion_actions_rejected() -> None:
    for action in sorted(FORBIDDEN_NEXT_ACTIONS):
        errors = validate_forbidden_actions([action])
        assert errors, f"expected reject for {action}"
    decision = _load(EXAMPLES / "cdb_decision_record_paper_valid.json")
    # Existing Wave-2 decision surface still rejects live/capital escalation.
    bad = deepcopy(decision)
    bad["allowed_next_actions"] = ["live_trading"]
    assert validate_decision_allowed_actions(bad)


@pytest.mark.unit
def test_wave1_and_wave2_contracts_remain_compatible() -> None:
    """Security gate slice must not break existing Wave-1/2 example surfaces."""
    wave1_examples = (
        "cdb_research_brief_valid.json",
        "cdb_strategy_candidate_valid.json",
        "cdb_validation_manifest_valid.json",
        "cdb_candidate_evidence_valid.json",
        "cdb_decision_record_valid.json",
    )
    wave1_schemas = {
        "cdb_research_brief_valid.json": "cdb_research_brief.v1.schema.json",
        "cdb_strategy_candidate_valid.json": "cdb_strategy_candidate.v1.schema.json",
        "cdb_validation_manifest_valid.json": "cdb_validation_manifest.v1.schema.json",
        "cdb_candidate_evidence_valid.json": "cdb_candidate_evidence.v1.schema.json",
        "cdb_decision_record_valid.json": "cdb_decision_record.v1.schema.json",
    }
    for example_name, schema_name in wave1_schemas.items():
        payload = _load(EXAMPLES / example_name)
        schema = _load(CONTRACTS / schema_name)
        assert list(Draft7Validator(schema).iter_errors(payload)) == []

    source = _load(EXAMPLES / "cdb_source_evidence_binance_valid.json")
    assert source["trust_classification"] == "UNTRUSTED_INPUT"
    assert validate_source_evidence_non_authority(source) == []

    pass_evidence = _load(EXAMPLES / "cdb_candidate_evidence_pass_valid.json")
    schema = _load(CONTRACTS / "cdb_candidate_evidence.v1.schema.json")
    assert list(Draft7Validator(schema).iter_errors(pass_evidence)) == []

    # Ensure wave1 example list was intentionally exercised.
    assert set(wave1_examples) == set(wave1_schemas)


@pytest.mark.unit
def test_redaction_never_embeds_raw_secret_value() -> None:
    gate = _valid_gate()
    gate["sensitive_data_assessment"]["redactions"] = [
        {
            "field_path": "payload.token",
            "data_class": "token",
            "value": "should-never-appear",
        }
    ]
    # Schema rejects unknown properties on redaction rows.
    assert _errors(gate)
    # Cross-contract also rejects raw-value keys if present via loose objects.
    loose = {
        "overall_verdict": "BLOCKED",
        "check_results": gate["check_results"],
        "injection_assessment": gate["injection_assessment"],
        "sensitive_data_assessment": {
            "suspicion": True,
            "verdict": "BLOCKED",
            "redactions": [{"field_path": "x", "data_class": "token", "secret": "x"}],
            "notes": "blocked",
        },
        "limitations": ["blocked"],
    }
    cross = validate_fail_closed_verdicts(loose)
    assert any("raw secret" in err for err in cross)
