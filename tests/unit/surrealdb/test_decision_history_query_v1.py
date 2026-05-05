"""Unit tests for Decision History Query v1 (#2118)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.decision_history_query import (
    DecisionHistoryQueryRequest,
    DecisionHistoryQueryError,
    query_decision_history_v1,
)


FIXTURE_PATH = Path("tests/fixtures/surrealdb/decision_history/decisions_v1.json")


def _load_fixture() -> dict:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload


@pytest.mark.unit
def test_by_decision_id() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_decision_id", decision_id="dec-002")
    result = query_decision_history_v1(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        known_claim_ids=set(fixture["known_claim_ids"]),
    )
    assert result["mode"] == "by_decision_id"
    assert [d["decision_id"] for d in result["matched_decisions"]] == ["dec-002"]


@pytest.mark.unit
def test_by_topic() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_topic", topic="topic:a")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert {d["decision_id"] for d in result["matched_decisions"]} == {"dec-001", "dec-002"}


@pytest.mark.unit
def test_by_scope() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_scope", scope="topic_b")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert {d["decision_id"] for d in result["matched_decisions"]} == {"dec-003", "dec-004"}


@pytest.mark.unit
def test_by_artifact() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(
        mode="by_artifact", artifact="infrastructure/surrealdb/context_intelligence_v0.surql"
    )
    result = query_decision_history_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["matched_decisions"]] == ["dec-003"]


@pytest.mark.unit
def test_by_issue() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_issue", issue="#2119")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["matched_decisions"]] == ["dec-002"]


@pytest.mark.unit
def test_by_status() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_status", status="invalidated")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["matched_decisions"]] == ["dec-003"]
    assert [d["decision_id"] for d in result["invalidated_decisions"]] == ["dec-003"]


@pytest.mark.unit
def test_current_for_topic() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="current_for_topic", topic="topic:a")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["current_decisions"]] == ["dec-002"]
    assert [d["decision_id"] for d in result["superseded_decisions"]] == []


@pytest.mark.unit
def test_superseded_for_topic() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="superseded_for_topic", topic="topic:a")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["matched_decisions"]] == ["dec-001"]
    assert [d["decision_id"] for d in result["superseded_decisions"]] == ["dec-001"]


@pytest.mark.unit
def test_unresolved_evidence_and_claim_refs_visible() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_decision_id", decision_id="dec-002")
    result = query_decision_history_v1(
        fixture["decisions"],
        req,
        known_evidence_ids=set(fixture["known_evidence_ids"]),
        known_claim_ids=set(fixture["known_claim_ids"]),
    )
    assert result["unresolved_evidence_refs"] == ["ev-missing-001"]
    assert result["unresolved_claim_refs"] == ["cl-missing-001"]
    assert "unresolved_evidence_refs_present" in result["warnings"]
    assert "unresolved_claim_refs_present" in result["warnings"]


@pytest.mark.unit
def test_human_go_visible_but_non_authorizing() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_decision_id", decision_id="dec-002")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert result["human_go"][0]["human_go"] is True
    semantics = result["approval_semantics"]
    assert semantics["history_only"] is True
    assert semantics["no_approval"] is True
    assert semantics["no_live_go"] is True


@pytest.mark.unit
def test_deterministic_ordering() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_topic", topic="topic:a")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert [d["decision_id"] for d in result["matched_decisions"]] == ["dec-001", "dec-002"]


@pytest.mark.unit
def test_empty_result_emits_warning_not_crash() -> None:
    fixture = _load_fixture()
    req = DecisionHistoryQueryRequest(mode="by_topic", topic="topic:does-not-exist")
    result = query_decision_history_v1(fixture["decisions"], req)
    assert result["matched_decisions"] == []
    assert "no_decisions_matched" in result["warnings"]


@pytest.mark.unit
def test_invalid_request_rejected() -> None:
    fixture = _load_fixture()
    with pytest.raises(DecisionHistoryQueryError):
        query_decision_history_v1(fixture["decisions"], DecisionHistoryQueryRequest(mode="by_topic"))
