"""Fixture-based Harvester→ARVP→Profitability mapping contract tests (#3828).

No live harvester, no productive evidence writes, no ranking-policy changes.
"""

from __future__ import annotations

import pytest

from tests.unit.arvp._arvp_evidence_mapping_helpers import (
    evaluate_evidence_mapping_case,
    load_evidence_mapping_cases,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize("case", load_evidence_mapping_cases(), ids=lambda c: c["case_id"])
def test_evidence_mapping_fixture_expectations(case: dict) -> None:
    result = evaluate_evidence_mapping_case(case)
    coverage = result["coverage"]
    assert coverage["coverage_report_ready"] is case["expect_coverage_ready"]
    assert coverage["ranking_inputs_complete"] is case["expect_ranking_complete"]

    for fragment in case.get("expect_limitation_substrings", []):
        joined = " ".join(result["limitations"]).lower()
        assert fragment.lower() in joined

    if "expect_recommendation_not" in case:
        assert result["recommendation"] != case["expect_recommendation_not"]


def test_harvester_gap_findings_remain_limitations_not_proofs() -> None:
    case = next(
        c for c in load_evidence_mapping_cases() if c["case_id"] == "harvester_gap_zero_paper_chains"
    )
    result = evaluate_evidence_mapping_case(case)
    assert result["coverage"]["ranking_inputs_complete"] is False
    assert "zero paper chains" in " ".join(result["limitations"]).lower()


def test_harvester_safety_boundaries_propagate() -> None:
    case = next(c for c in load_evidence_mapping_cases() if c["case_id"] == "stale_feed_blocked")
    result = evaluate_evidence_mapping_case(case)
    assert any("human gate" in s.lower() for s in result["safety_boundaries"])


def test_blocked_data_quality_prevents_coverage_ready() -> None:
    case = next(c for c in load_evidence_mapping_cases() if c["case_id"] == "stale_feed_blocked")
    result = evaluate_evidence_mapping_case(case)
    assert result["coverage"]["data_quality_ready"] is False
    assert result["coverage"]["coverage_report_ready"] is False


def test_coverage_signal_does_not_equal_profitability_proof() -> None:
    case = next(
        c
        for c in load_evidence_mapping_cases()
        if c["case_id"] == "coverage_signal_does_not_promote_to_proof"
    )
    result = evaluate_evidence_mapping_case(case)
    assert result["coverage"]["coverage_report_ready"] is True
    assert result["coverage"]["ranking_inputs_complete"] is False
    assert result["recommendation"] in {"PARK", "REVIEW", "REJECT", "UNSAFE", "NO_RECOMMENDATION"}


def test_missing_regime_keeps_gap_visible_in_readiness_summary() -> None:
    case = next(
        c for c in load_evidence_mapping_cases() if c["case_id"] == "harvester_gap_zero_paper_chains"
    )
    result = evaluate_evidence_mapping_case(case)
    assert result["coverage"]["regime_scorecard_ready"] is False
    assert "regime_scorecard_ready=False" in result["coverage"]["summary"]
