"""Unit tests for Decision MCP tool adapters v1 (#2124)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_decision_tools import (
    TOOL_CDB_CONTEXT_DECISION_HISTORY,
    TOOL_CDB_CONTEXT_DECISION_REPLAY,
    handle_cdb_context_decision_history,
    handle_cdb_context_decision_replay,
)


FIXTURE_PATH = Path("tests/fixtures/surrealdb/decision_mcp/decision_mcp_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _inject_shared_inputs(req: dict, fixture: dict) -> dict:
    out = dict(req)
    params = dict(out.get("parameters") or {})
    params["decision_events"] = fixture["decision_events"]
    params["known_evidence_ids"] = fixture["known_evidence_ids"]
    params["known_claim_ids"] = fixture["known_claim_ids"]
    params["evidence_summaries"] = fixture["evidence_summaries"]
    params["claim_summaries"] = fixture["claim_summaries"]
    params["stop_conditions"] = fixture["stop_conditions"]
    out["parameters"] = params
    return out


@pytest.mark.unit
def test_cdb_context_decision_history_returns_history_output() -> None:
    fixture = _load_fixture()
    req = _inject_shared_inputs(fixture["cases"]["history_by_decision_id"], fixture)
    result = handle_cdb_context_decision_history(req)
    assert result["tool"] == TOOL_CDB_CONTEXT_DECISION_HISTORY
    assert result["status"] == "ok"
    assert result["metadata"]["read_only"] is True
    assert result["result"]["mode"] == "by_decision_id"
    assert [d["decision_id"] for d in result["result"]["matched_decisions"]] == ["dec-002"]


@pytest.mark.unit
def test_cdb_context_decision_replay_returns_replay_output() -> None:
    fixture = _load_fixture()
    req = _inject_shared_inputs(fixture["cases"]["replay_by_decision_id"], fixture)
    result = handle_cdb_context_decision_replay(req)
    assert result["tool"] == TOOL_CDB_CONTEXT_DECISION_REPLAY
    assert result["status"] == "ok"
    assert result["metadata"]["read_only"] is True
    assert result["result"]["schema_version"] == "decision-replay-query/v2"
    assert result["result"]["decision_summary"]["decision_id"] == "dec-002"


@pytest.mark.unit
def test_current_and_superseded_are_visible() -> None:
    fixture = _load_fixture()

    current_req = _inject_shared_inputs(fixture["cases"]["current_for_topic"], fixture)
    current = handle_cdb_context_decision_history(current_req)
    assert current["status"] == "ok"
    assert [d["decision_id"] for d in current["result"]["current_decisions"]] == ["dec-002"]
    assert current["result"]["superseded_decisions"] == []

    superseded_req = _inject_shared_inputs(fixture["cases"]["superseded_for_topic"], fixture)
    superseded = handle_cdb_context_decision_history(superseded_req)
    assert superseded["status"] == "ok"
    assert [d["decision_id"] for d in superseded["result"]["superseded_decisions"]] == ["dec-001"]


@pytest.mark.unit
def test_unresolved_evidence_and_claim_visible() -> None:
    fixture = _load_fixture()
    req = _inject_shared_inputs(fixture["cases"]["history_by_decision_id"], fixture)
    result = handle_cdb_context_decision_history(req)
    assert result["status"] == "ok"
    assert result["result"]["unresolved_evidence_refs"] == ["ev-missing-001"]
    assert result["result"]["unresolved_claim_refs"] == ["cl-missing-001"]
    assert "unresolved_evidence_refs_present" in result["result"]["warnings"]
    assert "unresolved_claim_refs_present" in result["result"]["warnings"]


@pytest.mark.unit
def test_approval_semantics_no_live_no_echtgeld_and_human_go_non_authorizing() -> None:
    fixture = _load_fixture()

    history_req = _inject_shared_inputs(fixture["cases"]["history_by_decision_id"], fixture)
    history = handle_cdb_context_decision_history(history_req)
    assert history["status"] == "ok"
    semantics = history["result"]["approval_semantics"]
    assert semantics["history_only"] is True
    assert semantics["no_approval"] is True
    assert semantics["no_live_go"] is True
    assert semantics["no_echtgeld_go"] is True
    assert any(x["decision_id"] == "dec-002" and x["human_go"] is True for x in history["result"]["human_go"])

    replay_req = _inject_shared_inputs(fixture["cases"]["replay_by_decision_id"], fixture)
    replay = handle_cdb_context_decision_replay(replay_req)
    assert replay["status"] == "ok"
    replay_semantics = replay["result"]["approval_semantics"]
    assert replay_semantics["history_only"] is True
    assert replay_semantics["no_approval"] is True
    assert replay_semantics["no_live_go"] is True
    assert replay_semantics["no_echtgeld_go"] is True
    assert replay["result"]["decision_summary"]["human_go"]["present"] is True


@pytest.mark.unit
def test_invalid_request_gives_controlled_error() -> None:
    fixture = _load_fixture()
    req = _inject_shared_inputs(fixture["cases"]["invalid_input_mode"], fixture)
    result = handle_cdb_context_decision_history(req)
    assert result["tool"] == TOOL_CDB_CONTEXT_DECISION_HISTORY
    assert result["status"] == "error"
    assert result["error"]["code"] in {"invalid_request", "invalid_parameters"}


@pytest.mark.unit
def test_no_db_runtime_network_or_write_dependency() -> None:
    fixture = _load_fixture()
    req = _inject_shared_inputs(fixture["cases"]["replay_by_decision_id"], fixture)
    result = handle_cdb_context_decision_replay(req)
    assert result["status"] == "ok"
    assert result["metadata"]["source"] == "in_memory"
    assert result["metadata"]["read_only"] is True
