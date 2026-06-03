"""Unit tests for operator trust thresholds (#2856)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_evidence_memory_tools import (
    TOOL_CDB_CONTEXT_TRUST_SUMMARY,
    handle_cdb_context_trust_summary,
)
from tools.mcp.memory_output_contract import validate_memory_output_contract
from tools.surrealdb.trust_summary import (
    TrustContextSignals,
    TrustSummaryRequest,
    build_trust_summary_v1,
)

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "trust_threshold"


def _strong_inputs() -> dict:
    return {
        "evidence_result": {
            "evidence_summary": {"overall_strength": "strong"},
            "blocking_missing_ids": [],
            "stale_evidence_ids": [],
        },
        "claim_result": {
            "status_counts": {"supported": 8},
            "disputed_claim_ids": [],
            "stale_claim_ids": [],
            "missing_evidence_claim_ids": [],
        },
        "decision_result": {
            "matched_decisions": ["d1", "d2"],
            "current_decisions": ["d1", "d2"],
            "superseded_decisions": [],
            "invalidated_decisions": [],
        },
        "memory_result": {
            "trust_counts": {"source_backed": 4},
            "stale_memory_ids": [],
        },
    }


@pytest.mark.unit
def test_high_operator_trust_with_signals() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-high"),
        context_signals=TrustContextSignals(
            repo_crosscheck_present=True,
            record_source="surrealdb-local",
            freshness_ok=True,
        ),
        **_strong_inputs(),
    )
    assert result["trust_level"] == "strong"
    assert result["operator_trust_level"] == "HIGH"
    assert result["authorization_semantics"]["operational_truth_allowed"] is False
    assert result["authorization_semantics"]["no_human_go"] is True
    assert result["authorization_semantics"]["no_persist"] is True
    assert result["authorization_semantics"]["no_mutation"] is True
    assert "persist_allowed" not in result
    assert "mutation_allowed" not in result
    assert result["operator_trust_contract_version"] == "context-trust-threshold/v1"


@pytest.mark.unit
def test_medium_capped_for_repo_only_source() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-medium"),
        context_signals=TrustContextSignals(
            record_source="repo-only",
            repo_crosscheck_present=True,
        ),
        **_strong_inputs(),
    )
    assert result["operator_trust_level"] == "MEDIUM"
    assert any("below HIGH" in lim for lim in result["limitations"])


@pytest.mark.unit
def test_low_weak_legacy_and_caller_source() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-low"),
        context_signals=TrustContextSignals(caller_supplied_source_only=True),
        evidence_result={"evidence_summary": {"overall_strength": "weak"}},
    )
    assert result["trust_level"] in ("weak", "blocked")
    assert result["operator_trust_level"] == "LOW"
    assert any("operational truth" in lim for lim in result["limitations"])


@pytest.mark.unit
def test_blocked_github_mismatch() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-blocked-gh"),
        context_signals=TrustContextSignals(github_live_mismatch=True),
        **_strong_inputs(),
    )
    assert result["operator_trust_level"] == "BLOCKED"
    assert "github_live_mismatch" in result["warnings"]


@pytest.mark.unit
def test_blocked_stale_ledger_signal() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-blocked-ledger"),
        context_signals=TrustContextSignals(ledger_stale_vs_live=True),
    )
    assert result["operator_trust_level"] == "BLOCKED"


@pytest.mark.unit
def test_blocked_missing_evidence() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-blocked-ev"),
        evidence_result={
            "evidence_summary": {"overall_strength": "blocking_missing"},
            "blocking_missing_ids": ["ev-004"],
        },
    )
    assert result["trust_level"] == "blocked"
    assert result["operator_trust_level"] == "BLOCKED"


@pytest.mark.unit
def test_below_high_includes_limitations() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-trust-limits"),
        evidence_result={"evidence_summary": {"overall_strength": "moderate"}},
    )
    assert result["operator_trust_level"] != "HIGH"
    assert len(result["limitations"]) >= 2
    assert any("below HIGH" in lim for lim in result["limitations"])


@pytest.mark.unit
def test_legacy_only_mapping_without_signals() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-legacy-only"),
        evidence_result={
            "evidence_summary": {"overall_strength": "blocking_missing"},
            "blocking_missing_ids": ["ev-x"],
        },
    )
    assert result["operator_trust_mapping"]["context_signals_supplied"] is False
    assert result["operator_trust_level"] == "BLOCKED"


@pytest.mark.unit
def test_caller_source_cannot_reach_high() -> None:
    result = build_trust_summary_v1(
        TrustSummaryRequest(scope="wave14-no-caller-high"),
        context_signals=TrustContextSignals(
            caller_supplied_source_only=True,
            repo_crosscheck_present=True,
            record_source="surrealdb-local",
        ),
        **_strong_inputs(),
    )
    assert result["operator_trust_level"] != "HIGH"


@pytest.mark.unit
def test_mcp_trust_summary_exposes_operator_fields() -> None:
    response = handle_cdb_context_trust_summary(
        {
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {
                "scope": "wave14",
                "context_signals": {
                    "repo_crosscheck_present": True,
                    "record_source": "in_memory",
                },
            },
        }
    )
    assert response["status"] == "ok"
    result = response["result"]
    assert "operator_trust_level" in result
    assert result["operator_trust_level"] in ("BLOCKED", "LOW", "MEDIUM", "HIGH")
    assert "authorization_semantics" in result
    violations = validate_memory_output_contract(response)
    assert violations == [], f"violations: {violations}"


@pytest.mark.unit
def test_fixture_scenarios_match_contract() -> None:
    for path in _FIXTURE_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        signals_raw = payload.get("context_signals")
        signals = TrustContextSignals.from_mapping(signals_raw)
        result = build_trust_summary_v1(
            TrustSummaryRequest(scope=payload["scope"]),
            evidence_result=payload.get("evidence_result"),
            claim_result=payload.get("claim_result"),
            decision_result=payload.get("decision_result"),
            memory_result=payload.get("memory_result"),
            context_signals=signals,
        )
        assert result["operator_trust_level"] == payload["expected_operator_trust_level"]
