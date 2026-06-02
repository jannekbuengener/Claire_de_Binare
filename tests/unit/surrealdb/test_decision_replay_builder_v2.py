"""Unit tests for Decision Replay Builder v2 (#2800)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.decision_replay_builder import (
    DecisionReplayRequest,
    SCHEMA_VERSION_V2,
    build_decision_replay_v1,
    build_decision_replay_v2,
)


FIXTURE_PATH = Path("tests/fixtures/surrealdb/decision_replay/replay_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_v2_preserves_v1_core_fields_without_evidence_inputs() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    v1 = build_decision_replay_v1(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        known_claim_ids=set(fixture["known_claim_ids"]),
        evidence_summaries=fixture["evidence_summaries"],
        claim_summaries=fixture["claim_summaries"],
        stop_conditions=fixture["stop_conditions"],
    )
    v2 = build_decision_replay_v2(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        known_claim_ids=set(fixture["known_claim_ids"]),
        evidence_summaries=fixture["evidence_summaries"],
        claim_summaries=fixture["claim_summaries"],
        stop_conditions=fixture["stop_conditions"],
    )
    assert v2["schema_version"] == SCHEMA_VERSION_V2
    for key in (
        "query",
        "decision_summary",
        "decision_chain",
        "evidence_chain",
        "claim_chain",
        "approval_semantics",
    ):
        assert v2[key] == v1[key]
    assert v2["evidence_resolution_status"] == "partial"
    assert "ev-missing-001" in v2["unresolved_evidence_refs"]


@pytest.mark.unit
def test_v2_resolves_evidence_from_records() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    records = [
        {
            "evidence_id": "ev-002",
            "title": "Replay evidence",
            "evidence_type": "log",
            "confidence": 0.9,
            "created_at": "2026-05-02T10:00:00+00:00",
        }
    ]
    result = build_decision_replay_v2(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        evidence_records=records,
    )
    resolved_ids = {entry.get("id") for entry in result["resolved_evidence"]}
    assert "ev-002" in resolved_ids
    assert "ev-missing-001" in result["unresolved_evidence_refs"]
    assert result["evidence_resolution_status"] == "partial"
    assert "unresolved_evidence_refs_present" in result["evidence_warnings"]


@pytest.mark.unit
def test_v2_never_verifies_missing_evidence_implicitly() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    result = build_decision_replay_v2(
        fixture["decisions"],
        req,
        known_evidence_ids={"ev-missing-001", "ev-002", "ev-003"},
    )
    assert "ev-missing-001" in result["unresolved_evidence_refs"]
    resolved_ids = {entry.get("id") for entry in result["resolved_evidence"]}
    assert "ev-missing-001" not in resolved_ids


@pytest.mark.unit
def test_v2_decision_chain_hash_is_deterministic_and_excludes_as_of() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    first = build_decision_replay_v2(fixture["decisions"], req)
    second = build_decision_replay_v2(fixture["decisions"], req)
    assert first["decision_chain_hash"] == second["decision_chain_hash"]
    assert first["current_status"]["as_of"] != second["current_status"]["as_of"]


@pytest.mark.unit
def test_v2_redacts_sensitive_fields_in_resolved_evidence() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    records = [
        {
            "evidence_id": "ev-002",
            "title": "Sensitive evidence",
            "api_key": "should-not-leak",
            "password": "should-not-leak",
            "nested": {"client_secret": "nested-secret"},
            "created_at": "2026-05-02T10:00:00+00:00",
        }
    ]
    result = build_decision_replay_v2(
        fixture["decisions"],
        req,
        evidence_records=records,
    )
    record_entry = next(
        item for item in result["resolved_evidence"] if item.get("id") == "ev-002"
    )
    evidence = record_entry["evidence"]
    assert evidence["api_key"] == "[REDACTED]"
    assert evidence["password"] == "[REDACTED]"
    assert evidence["nested"]["client_secret"] == "[REDACTED]"


@pytest.mark.unit
def test_v2_human_go_visible_but_non_authorizing() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    result = build_decision_replay_v2(fixture["decisions"], req)
    assert result["decision_summary"]["human_go"]["present"] is True
    semantics = result["approval_semantics"]
    assert semantics["no_live_go"] is True
    assert semantics["no_echtgeld_go"] is True
    explain = result["replay_explainability"]
    assert explain["history_only"] is True
    assert explain["limitations"]


@pytest.mark.unit
def test_v2_hash_reflects_enriched_evidence_resolution_state() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    refs_only = build_decision_replay_v2(fixture["decisions"], req)
    with_record = build_decision_replay_v2(
        fixture["decisions"],
        req,
        evidence_records=[
            {
                "evidence_id": "ev-002",
                "title": "Resolved via record",
                "created_at": "2026-05-02T10:00:00+00:00",
            }
        ],
    )
    assert refs_only["decision_chain_hash"] != with_record["decision_chain_hash"]
    assert refs_only["evidence_resolution_status"] == "refs_only"
    assert with_record["evidence_resolution_status"] == "partial"


@pytest.mark.unit
def test_v2_refs_only_status_when_no_resolution_inputs() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    result = build_decision_replay_v2(fixture["decisions"], req)
    assert result["evidence_resolution_status"] == "refs_only"
    assert "evidence_resolution_inputs_not_provided" in result["evidence_warnings"]
