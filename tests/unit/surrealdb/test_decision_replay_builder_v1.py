"""Unit tests for Decision Replay Builder v1 (#2119)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.decision_replay_builder import (
    DecisionReplayError,
    DecisionReplayRequest,
    build_decision_replay_v1,
)


FIXTURE_PATH = Path("tests/fixtures/surrealdb/decision_replay/replay_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_replay_by_decision_id_returns_summary_and_chains() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    result = build_decision_replay_v1(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        known_claim_ids=set(fixture["known_claim_ids"]),
        evidence_summaries=fixture["evidence_summaries"],
        claim_summaries=fixture["claim_summaries"],
        stop_conditions=fixture["stop_conditions"],
    )
    assert result["schema_version"] == "decision-replay-query/v1"
    assert result["decision_summary"]["decision_id"] == "dec-002"
    assert result["current_status"]["bucket"] == "current"
    assert result["supersession_chain"] == [{"from": "dec-001", "to": "dec-002", "relation": "supersedes"}]
    assert result["stop_conditions"] == fixture["stop_conditions"]


@pytest.mark.unit
def test_replay_current_for_topic_uses_history_basis() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_current_for_topic", topic="topic:a", limit=50)
    result = build_decision_replay_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["current_decisions"]] == ["dec-002"]
    assert result["decision_chain"]


@pytest.mark.unit
def test_replay_superseded_for_topic_uses_history_basis() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_superseded_for_topic", topic="topic:a", limit=50)
    result = build_decision_replay_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["superseded_decisions"]] == ["dec-001"]


@pytest.mark.unit
def test_replay_current_for_topic_honors_date_range_at() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(
        mode="replay_current_for_topic",
        topic="topic:a",
        date_range={"at": "2026-05-01T12:00:00Z"},
        limit=50,
    )
    result = build_decision_replay_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["current_decisions"]] == ["dec-001"]
    assert result["current_status"]["current_decision_id"] == "dec-001"
    assert "date_range_out_of_history" in result["warnings"]
    assert "broken_supersession_chain" in result["warnings"]


@pytest.mark.unit
def test_missing_refs_visible_as_unresolved() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    result = build_decision_replay_v1(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        known_claim_ids=set(fixture["known_claim_ids"]),
    )
    assert result["evidence_chain"]["unresolved"] == ["ev-missing-001"]
    assert result["claim_chain"]["unresolved"] == ["cl-missing-001"]
    assert "unresolved_evidence_refs_present" in result["warnings"]
    assert "unresolved_claim_refs_present" in result["warnings"]


@pytest.mark.unit
def test_missing_supersession_target_emits_broken_chain_warning() -> None:
    fixture = _load_fixture()
    fixture["decisions"][0]["superseded_by"] = "dec-missing-target"
    req = DecisionReplayRequest(mode="replay_current_for_topic", topic="topic:a", limit=50)
    result = build_decision_replay_v1(fixture["decisions"], req)
    assert "broken_supersession_chain" in result["warnings"]


@pytest.mark.unit
def test_replay_output_strips_internal_datetime_helpers() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_current_for_topic", topic="topic:a", limit=50)
    result = build_decision_replay_v1(fixture["decisions"], req)
    for bucket in ("current_decisions", "superseded_decisions", "invalidated_decisions", "old_decisions"):
        for decision in result[bucket]:
            assert "_created_at_dt" not in decision
    json.dumps(result)


@pytest.mark.unit
def test_human_go_visible_but_non_authorizing() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-002", limit=50)
    result = build_decision_replay_v1(fixture["decisions"], req)
    assert result["decision_summary"]["human_go"]["present"] is True
    semantics = result["approval_semantics"]
    assert semantics["history_only"] is True
    assert semantics["no_approval"] is True
    assert semantics["no_live_go"] is True
    assert semantics["no_echtgeld_go"] is True


@pytest.mark.unit
def test_missing_decision_emits_warning_not_crash() -> None:
    fixture = _load_fixture()
    req = DecisionReplayRequest(mode="replay_by_decision_id", decision_id="dec-does-not-exist", limit=50)
    result = build_decision_replay_v1(fixture["decisions"], req)
    assert "missing_decision" in result["warnings"]


@pytest.mark.unit
def test_invalid_request_rejected() -> None:
    fixture = _load_fixture()
    with pytest.raises(DecisionReplayError):
        build_decision_replay_v1(fixture["decisions"], DecisionReplayRequest(mode="replay_current_for_topic"))
