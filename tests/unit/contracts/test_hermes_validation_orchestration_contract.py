"""
Hermes Validation Chief orchestration contract (#4270).

test_id: tc_hermes_validation_orchestration_contract_001
test_name: hermes_validation_chief_orchestration_contract
test_type: Wissens-Test / Schutz-Test
cdb_area: contracts
rule_ref: technical-vs-domain-failure; retry-policy; security-gate-binding; drift-invalidates-pass; no-authority-escalation
decision_ref: research-validation-wave3-hermes-orchestration
issue_ref: #4270 #4263 #4271
pr_ref: #4291
evidence_ref: docs/research/CDB_HERMES_VALIDATION_CHIEF_ORCHESTRATION_CONTRACT_V1.md
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

from tools.research_validation.hermes_orchestration_cross_contract import (
    hermes_pass_grants_live_authority,
    hermes_pass_grants_validation_authority,
    validate_attempt_binding_stability,
    validate_evidence_and_drift_for_pass,
    validate_hermes_orchestration_run,
    validate_retry_policy,
    validate_security_gate_blocks_pass,
)
from tools.research_validation.security_gates_cross_contract import (
    validate_security_gate_record,
)
from tools.research_validation.wave2_cross_contract import (
    validate_decision_allowed_actions,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = PROJECT_ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"
SCHEMA_NAME = "cdb_hermes_orchestration_run.v1.schema.json"
FIXTURE_NAME = "cdb_hermes_orchestration_run_valid.json"
SECURITY_FIXTURE = "cdb_research_security_gate_valid.json"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _valid_run() -> dict:
    return _load(EXAMPLES / FIXTURE_NAME)


def _errors(payload: dict) -> list:
    schema = _load(CONTRACTS / SCHEMA_NAME)
    return list(Draft7Validator(schema).iter_errors(payload))


def _bindings_copy(run: dict) -> dict:
    return deepcopy(run["bindings"])


@pytest.mark.unit
def test_valid_orchestration_fixture_matches_schema_and_cross_contract() -> None:
    run = _valid_run()
    assert run["schema_version"] == "cdb.hermes_orchestration_run.v1"
    assert run["orchestrator"] == "hermes-validation-chief"
    assert _errors(run) == []
    assert validate_hermes_orchestration_run(run) == []


@pytest.mark.unit
def test_technical_retryable_failure_allows_bounded_retry() -> None:
    run = _valid_run()
    run["structured_verdict"] = {
        "verdict": "TECHNICAL_RETRY_PENDING",
        "rationale_codes": ["TECHNICAL_RETRYABLE"],
        "free_form_opinion_is_leading": False,
        "notes": "Awaiting technical retry.",
    }
    run["run_status"] = "AWAITING_TECHNICAL_RETRY"
    run["drift_status"] = "NONE"
    run["evidence_collection"] = {
        "status": "PARTIAL",
        "artifact_hashes": [],
        "missing_artifacts": ["candidate-evidence.json"],
    }
    run["bindings"]["produced_artifact_hashes"] = []
    first = run["attempts"][0]
    first["status"] = "FAILED_TECHNICAL"
    first["ended_at"] = "2026-08-01T19:02:00Z"
    first["failure"] = {
        "failure_class": "TECHNICAL",
        "code": "RUNNER_UNAVAILABLE",
        "retryable": True,
        "message": "Synthetic runner unavailable.",
    }
    first["bindings_snapshot"] = _bindings_copy(run)
    second_bindings = _bindings_copy(run)
    run["attempts"].append(
        {
            "attempt_id": "att-wave3-btc-trend-002",
            "attempt_number": 2,
            "started_at": "2026-08-01T19:03:00Z",
            "worker_type": "synthetic-fixture-worker",
            "status": "RUNNING",
            "bindings_snapshot": second_bindings,
        }
    )
    run["retry_disposition"] = {
        "retryable": True,
        "reason_code": "TECHNICAL_RETRYABLE",
        "next_attempt_allowed": True,
    }
    run["failure_records"] = [first["failure"]]
    assert _errors(run) == []
    cross = validate_hermes_orchestration_run(run)
    assert cross == []
    assert validate_retry_policy(run) == []


@pytest.mark.unit
def test_domain_failure_forbids_automatic_retry() -> None:
    run = _valid_run()
    run["structured_verdict"] = {
        "verdict": "FAIL",
        "rationale_codes": ["VALIDATION_FAILED"],
        "free_form_opinion_is_leading": False,
    }
    run["run_status"] = "FAILED"
    run["evidence_collection"]["status"] = "FAILED"
    run["attempts"][0]["status"] = "FAILED_DOMAIN"
    run["attempts"][0]["failure"] = {
        "failure_class": "DOMAIN",
        "code": "VALIDATION_FAILED",
        "retryable": False,
        "message": "Domain validation failed.",
    }
    run["retry_disposition"] = {
        "retryable": True,
        "reason_code": "TECHNICAL_RETRYABLE",
        "next_attempt_allowed": True,
    }
    cross = validate_retry_policy(run)
    assert any("domain" in err for err in cross)


@pytest.mark.unit
def test_security_blocked_prevents_pass() -> None:
    run = _valid_run()
    run["security_gate_binding"]["security_gate_verdict"] = "BLOCKED"
    run["structured_verdict"]["verdict"] = "PASS"
    assert _errors(run)
    cross = validate_security_gate_blocks_pass(run)
    assert any("security_gate_verdict" in err for err in cross)
    assert validate_hermes_orchestration_run(run)


@pytest.mark.unit
def test_head_drift_invalidates_pass() -> None:
    run = _valid_run()
    run["drift_status"] = "HEAD_DRIFT"
    assert _errors(run)
    cross = validate_evidence_and_drift_for_pass(run)
    assert any("HEAD_DRIFT" in err or "drift" in err for err in cross)


@pytest.mark.unit
def test_candidate_and_manifest_drift_invalidate_pass() -> None:
    for drift in (
        "CANDIDATE_DRIFT",
        "MANIFEST_DRIFT",
        "SECURITY_GATE_DRIFT",
        "DATASET_DRIFT",
    ):
        run = _valid_run()
        run["drift_status"] = drift
        assert _errors(run), drift
        cross = validate_evidence_and_drift_for_pass(run)
        assert cross, drift


@pytest.mark.unit
def test_missing_artifact_hashes_prevent_pass() -> None:
    run = _valid_run()
    run["bindings"]["produced_artifact_hashes"] = []
    run["evidence_collection"] = {
        "status": "COMPLETE",
        "artifact_hashes": [],
        "missing_artifacts": [],
    }
    assert _errors(run)
    cross = validate_evidence_and_drift_for_pass(run)
    assert any("artifact" in err for err in cross)


@pytest.mark.unit
def test_bindings_cannot_change_between_attempts() -> None:
    run = _valid_run()
    run["structured_verdict"]["verdict"] = "TECHNICAL_RETRY_PENDING"
    run["structured_verdict"]["rationale_codes"] = ["TECHNICAL_RETRYABLE"]
    run["run_status"] = "AWAITING_TECHNICAL_RETRY"
    run["evidence_collection"]["status"] = "PARTIAL"
    run["evidence_collection"]["missing_artifacts"] = ["candidate-evidence.json"]
    run["bindings"]["produced_artifact_hashes"] = []
    run["retry_disposition"] = {
        "retryable": True,
        "reason_code": "TECHNICAL_RETRYABLE",
        "next_attempt_allowed": True,
    }
    run["attempts"][0]["status"] = "FAILED_TECHNICAL"
    run["attempts"][0]["failure"] = {
        "failure_class": "TECHNICAL",
        "code": "NETWORK_TRANSIENT",
        "retryable": True,
        "message": "Transient network error.",
    }
    drifted = _bindings_copy(run)
    drifted["strategy_candidate_version"] = "v2"
    drifted["candidate_content_hash"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    run["attempts"].append(
        {
            "attempt_id": "att-wave3-btc-trend-002",
            "attempt_number": 2,
            "started_at": "2026-08-01T19:03:00Z",
            "worker_type": "synthetic-fixture-worker",
            "status": "RUNNING",
            "bindings_snapshot": drifted,
        }
    )
    cross = validate_attempt_binding_stability(run)
    assert any("strategy_candidate_version" in err for err in cross)


@pytest.mark.unit
def test_domain_failure_cannot_yield_pass() -> None:
    run = _valid_run()
    run["attempts"][0]["status"] = "FAILED_DOMAIN"
    run["attempts"][0]["failure"] = {
        "failure_class": "DOMAIN",
        "code": "VALIDATION_FAILED",
        "retryable": False,
        "message": "Domain validation failed.",
    }
    run["failure_records"] = [run["attempts"][0]["failure"]]
    run["retry_disposition"] = {
        "retryable": False,
        "reason_code": "DOMAIN_NOT_RETRYABLE",
        "next_attempt_allowed": False,
    }
    # Keep PASS fields otherwise intact — must still be rejected.
    cross = validate_hermes_orchestration_run(run)
    assert any("domain failure" in err for err in cross)


@pytest.mark.unit
def test_failed_status_requires_matching_failure_object() -> None:
    run = _valid_run()
    run["structured_verdict"]["verdict"] = "FAIL"
    run["structured_verdict"]["rationale_codes"] = ["VALIDATION_FAILED"]
    run["run_status"] = "FAILED"
    run["evidence_collection"]["status"] = "FAILED"
    run["attempts"][0]["status"] = "FAILED_DOMAIN"
    run["attempts"][0].pop("failure", None)
    assert _errors(run)
    cross = validate_hermes_orchestration_run(run)
    assert any("FAILED_DOMAIN requires" in err for err in cross)


@pytest.mark.unit
def test_non_retryable_technical_failure_forbids_retry_disposition() -> None:
    run = _valid_run()
    run["structured_verdict"] = {
        "verdict": "FAIL",
        "rationale_codes": ["TECHNICAL_EXHAUSTED"],
        "free_form_opinion_is_leading": False,
    }
    run["run_status"] = "FAILED"
    run["evidence_collection"]["status"] = "FAILED"
    run["attempts"][0]["status"] = "FAILED_TECHNICAL"
    run["attempts"][0]["failure"] = {
        "failure_class": "TECHNICAL",
        "code": "RUNNER_UNAVAILABLE",
        "retryable": False,
        "message": "Runner permanently unavailable.",
    }
    run["retry_disposition"] = {
        "retryable": True,
        "reason_code": "TECHNICAL_RETRYABLE",
        "next_attempt_allowed": True,
    }
    cross = validate_retry_policy(run)
    assert any("non-retryable technical" in err for err in cross)
    assert validate_hermes_orchestration_run(run)


@pytest.mark.unit
def test_hermes_pass_grants_no_validation_or_live_authority() -> None:
    run = _valid_run()
    assert hermes_pass_grants_validation_authority(run) is False
    assert hermes_pass_grants_live_authority(run) is False
    assert run["authority_boundaries"]["hermes_validation_authority"] is False
    assert run["authority_boundaries"]["hermes_live_authority"] is False
    assert (
        run["authority_boundaries"]["orchestration_pass_implies_validation_pass"]
        is False
    )
    assert run["authority_boundaries"]["real_money_go"] is False
    assert validate_hermes_orchestration_run(run) == []


@pytest.mark.unit
def test_wave1_wave2_security_contracts_remain_compatible() -> None:
    """Orchestration slice must not break prior research-validation surfaces."""
    security = _load(EXAMPLES / SECURITY_FIXTURE)
    assert validate_security_gate_record(security) == []

    decision = _load(EXAMPLES / "cdb_decision_record_valid.json")
    assert validate_decision_allowed_actions(decision) == []

    run = _valid_run()
    assert run["bindings"]["security_gate_id"] == security["gate_id"]
    assert (
        run["bindings"]["strategy_candidate_id"]
        == security["candidate_id"]
        == "sc-wave1-btc-trend-breakout"
    )
    assert (
        run["bindings"]["validation_manifest_id"]
        == security["integrity_bindings"]["validation_manifest_id"]
    )
    assert validate_hermes_orchestration_run(run) == []
