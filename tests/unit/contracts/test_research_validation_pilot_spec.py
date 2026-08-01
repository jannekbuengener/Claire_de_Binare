"""
Research Validation Pilot Spec contract (#4272).

test_id: tc_research_validation_pilot_spec_001
test_name: research_validation_three_candidate_pilot_spec
test_type: Wissens-Test / Schutz-Test
cdb_area: contracts
rule_ref: three-candidate-pilot; specification-only; shared-gates; economics-stress; no-fake-evidence; tickersage-non-authority
decision_ref: research-validation-wave3-pilot-spec
issue_ref: #4272 #4263 #4270 #4271
evidence_ref: docs/research/CDB_RESEARCH_VALIDATION_PILOT_SPEC_V1.md
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

from tools.research_validation.pilot_spec_cross_contract import (
    pilot_spec_grants_live_authority,
    pilot_spec_grants_validation_authority,
    validate_candidate_set,
    validate_economics_and_scenarios,
    validate_no_executed_claims,
    validate_research_validation_pilot,
    validate_source_pairs,
    validate_tickersage_and_authority,
    validate_time_and_provenance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = PROJECT_ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"
SCHEMA_NAME = "cdb_research_validation_pilot.v1.schema.json"
FIXTURE_NAME = "cdb_research_validation_pilot_valid.json"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _valid_pilot() -> dict:
    return _load(EXAMPLES / FIXTURE_NAME)


def _errors(payload: dict) -> list:
    schema = _load(CONTRACTS / SCHEMA_NAME)
    return list(Draft7Validator(schema).iter_errors(payload))


def _candidate(pilot: dict, key: str) -> dict:
    for item in pilot["candidate_specs"]:
        if item["candidate_key"] == key:
            return item
    raise AssertionError(f"candidate {key} missing")


@pytest.mark.unit
def test_valid_pilot_fixture_matches_schema_and_cross_contract() -> None:
    pilot = _valid_pilot()
    assert pilot["schema_version"] == "cdb.research_validation_pilot.v1"
    assert pilot["spec_status"] == "PLANNED"
    assert pilot["execution_status"] == "SPECIFICATION_ONLY"
    assert _errors(pilot) == []
    assert validate_research_validation_pilot(pilot) == []


@pytest.mark.unit
def test_three_candidates_share_same_contract_set() -> None:
    pilot = _valid_pilot()
    assert len(pilot["candidate_specs"]) == 3
    keys = {item["candidate_key"] for item in pilot["candidate_specs"]}
    assert keys == {
        "breakout",
        "liquidity_or_volume_filter",
        "on_chain_regime_filter",
    }
    assert pilot["common_gate_bindings"]["same_contract_versions_for_all_candidates"]
    assert pilot["validation_profile"] == "validation-research-v1"
    assert validate_candidate_set(pilot) == []
    assert validate_source_pairs(pilot) == []


@pytest.mark.unit
def test_specification_only_state_is_accepted() -> None:
    pilot = _valid_pilot()
    assert pilot["safety_boundaries"]["pilot_execution"] is False
    assert validate_no_executed_claims(pilot) == []
    assert pilot_spec_grants_validation_authority(pilot) is False
    assert pilot_spec_grants_live_authority(pilot) is False


@pytest.mark.unit
def test_missing_candidate_is_rejected() -> None:
    pilot = _valid_pilot()
    pilot["candidate_specs"] = pilot["candidate_specs"][:2]
    cross = validate_candidate_set(pilot)
    assert any("exactly 3" in err or "missing required" in err for err in cross)


@pytest.mark.unit
def test_duplicate_candidate_key_is_rejected() -> None:
    pilot = _valid_pilot()
    pilot["candidate_specs"][1]["candidate_key"] = "breakout"
    cross = validate_candidate_set(pilot)
    assert any("duplicate" in err for err in cross)


@pytest.mark.unit
def test_wrong_source_pair_is_rejected() -> None:
    pilot = _valid_pilot()
    cand = _candidate(pilot, "breakout")
    cand["required_sources"] = ["token_terminal", "bigdata_com"]
    cross = validate_source_pairs(pilot)
    assert any("breakout" in err and "required_sources" in err for err in cross)


@pytest.mark.unit
def test_source_specific_gate_bypass_is_rejected() -> None:
    pilot = _valid_pilot()
    pilot["common_gate_bindings"]["source_specific_gate_bypass_allowed"] = True
    # Schema const false should already fail; also cross-contract.
    assert _errors(pilot)
    cross = validate_research_validation_pilot(pilot)
    assert any("bypass" in err for err in cross)


@pytest.mark.unit
def test_missing_fees_spread_slippage_rejected() -> None:
    pilot = _valid_pilot()
    cand = _candidate(pilot, "breakout")
    del cand["economics_components"]["fees"]
    cross = validate_economics_and_scenarios(pilot)
    assert any("fees" in err for err in cross)

    pilot = _valid_pilot()
    cand = _candidate(pilot, "breakout")
    del cand["economics_components"]["spread"]
    cross = validate_economics_and_scenarios(pilot)
    assert any("spread" in err for err in cross)

    pilot = _valid_pilot()
    cand = _candidate(pilot, "breakout")
    del cand["economics_components"]["slippage"]
    cross = validate_economics_and_scenarios(pilot)
    assert any("slippage" in err for err in cross)


@pytest.mark.unit
def test_missing_pessimistic_delay_is_rejected() -> None:
    pilot = _valid_pilot()
    for scenario in pilot["scenario_specs"]:
        if scenario["scenario_key"] == "pessimistic_liquidity_and_delay":
            scenario["additional_execution_delay_required"] = False
    assert _errors(pilot)
    cross = validate_economics_and_scenarios(pilot)
    assert any("additional_execution_delay" in err for err in cross)


@pytest.mark.unit
def test_executed_pass_without_evidence_is_rejected() -> None:
    pilot = _valid_pilot()
    pilot["expected_artifacts"][0]["status"] = "PASS"
    cross = validate_research_validation_pilot(pilot)
    assert any("PASS" in err or "execution" in err for err in cross)


@pytest.mark.unit
def test_invented_decision_verdict_in_specification_only_is_rejected() -> None:
    pilot = _valid_pilot()
    pilot["decision_verdict"] = "PAPER_CANDIDATE"
    cross = validate_no_executed_claims(pilot)
    assert any("decision_verdict" in err for err in cross)


@pytest.mark.unit
def test_token_terminal_partial_success_without_error_classification_rejected() -> None:
    pilot = _valid_pilot()
    cand = _candidate(pilot, "on_chain_regime_filter")
    cand["token_terminal_partial_success_policy"] = "ignore partial success"
    cross = validate_time_and_provenance(pilot)
    assert any("Token Terminal" in err or "partial-success" in err for err in cross)


@pytest.mark.unit
def test_missing_as_of_cutoff_is_rejected() -> None:
    pilot = _valid_pilot()
    cand = _candidate(pilot, "breakout")
    del cand["time_causality"]["decision_time"]
    cross = validate_time_and_provenance(pilot)
    assert any("decision_time" in err for err in cross)


@pytest.mark.unit
def test_tickersage_validation_or_decision_authority_rejected() -> None:
    pilot = _valid_pilot()
    mutated = deepcopy(pilot)
    mutated["visualization_policy"]["validation_authority"] = True
    assert _errors(mutated)
    cross = validate_tickersage_and_authority(mutated)
    assert any("validation_authority" in err for err in cross)

    mutated = deepcopy(pilot)
    mutated["visualization_policy"]["decision_authority"] = True
    assert _errors(mutated)
    cross = validate_tickersage_and_authority(mutated)
    assert any("decision_authority" in err for err in cross)


@pytest.mark.unit
def test_paper_live_capital_promotion_authority_rejected() -> None:
    pilot = _valid_pilot()
    for field in (
        "paper_go",
        "live_go",
        "capital_go",
        "automatic_strategy_promotion",
        "real_money_go",
    ):
        mutated = deepcopy(pilot)
        mutated["authority_boundaries"][field] = True
        assert _errors(mutated)
        cross = validate_tickersage_and_authority(mutated)
        assert any(field in err for err in cross)


@pytest.mark.unit
def test_wave_contracts_remain_loadable() -> None:
    """Lightweight compatibility: prior wave fixtures still parse as JSON objects."""
    for name in (
        "cdb_research_brief_valid.json",
        "cdb_strategy_candidate_valid.json",
        "cdb_research_security_gate_valid.json",
        "cdb_hermes_orchestration_run_valid.json",
        "cdb_source_evidence_binance_valid.json",
    ):
        payload = _load(EXAMPLES / name)
        assert isinstance(payload, dict)
        assert "schema_version" in payload
