"""Wave-14 MCP query return contract tests (#2643)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.unit.surrealdb import wave14_contract_constants as contracts
from tools.mcp.context_decision_tools import (
    TOOL_CDB_CONTEXT_DECISION_HISTORY,
    TOOL_CDB_CONTEXT_DECISION_REPLAY,
    handle_cdb_context_decision_history,
    handle_cdb_context_decision_replay,
)
from tools.mcp.context_evidence_memory_tools import (
    TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
    TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
    TOOL_CDB_CONTEXT_MEMORY_GET,
    TOOL_CDB_CONTEXT_TRUST_SUMMARY,
    handle_cdb_context_claim_resolve,
    handle_cdb_context_evidence_resolve,
    handle_cdb_context_memory_get,
    handle_cdb_context_trust_summary,
)
from tools.surrealdb.context_query import QueryAdapter

FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")
_FAKE_CONFIG_PATH = "infrastructure/config/surrealdb/context_query.local.example.yaml"
_DECISION_FIXTURE_RECORDS: list[dict[str, Any]] = [
    {
        "decision_id": "dec-001",
        "title": "Wave-14 stop resolver gate",
        "question": "Is context_stop_resolver fail-closed?",
        "answer": "Yes — incomplete inputs block.",
        "decision_type": "architectural",
        "status": "approved",
        "scope": "wave14",
        "topic": "context_tools",
        "topics": ["context_tools", "stop_conditions"],
        "evidence_refs": ["ev-001"],
        "claim_refs": ["claim-001"],
        "affected_artifacts": ["tools/surrealdb/context_stop_resolver.py"],
        "agent": "copilot",
        "human_go": False,
        "created_at": "2024-11-01T12:30:00Z",
    },
    {
        "decision_id": "dec-002",
        "title": "Decision history determinism gate",
        "question": "Is decision history deterministic?",
        "answer": "Yes for identical inputs.",
        "decision_type": "implementation",
        "status": "approved",
        "scope": "wave14",
        "topic": "context_tools",
        "topics": ["context_tools", "decision_history"],
        "evidence_refs": ["ev-002"],
        "claim_refs": ["claim-002"],
        "affected_artifacts": ["tools/surrealdb/decision_history_query.py"],
        "agent": "codex",
        "human_go": False,
        "created_at": "2024-11-02T12:30:00Z",
    },
]
_FORGED_DB_CLAIM_FIELDS: dict[str, Any] = {
    "source": "surrealdb-local",
    "brain_source": "surrealdb-local",
    "brain_status": "used",
    "metadata": {"source": "surrealdb-local"},
}

_WAVE14_HANDLERS: dict[str, Any] = {
    TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE: handle_cdb_context_evidence_resolve,
    TOOL_CDB_CONTEXT_CLAIM_RESOLVE: handle_cdb_context_claim_resolve,
    TOOL_CDB_CONTEXT_MEMORY_GET: handle_cdb_context_memory_get,
    TOOL_CDB_CONTEXT_TRUST_SUMMARY: handle_cdb_context_trust_summary,
    TOOL_CDB_CONTEXT_DECISION_HISTORY: handle_cdb_context_decision_history,
    TOOL_CDB_CONTEXT_DECISION_REPLAY: handle_cdb_context_decision_replay,
}


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _assert_mcp_ok_envelope(payload: dict[str, Any], *, tool: str) -> None:
    assert contracts.MCP_OK_ENVELOPE_KEYS <= frozenset(payload.keys())
    assert payload["tool"] == tool
    assert payload["status"] == "ok"
    assert isinstance(payload["result"], dict)
    assert contracts.MCP_METADATA_KEYS <= frozenset(payload["metadata"].keys())
    assert payload["metadata"]["read_only"] is True
    assert payload["metadata"]["source"] in contracts.ALLOWED_MCP_SOURCES
    assert isinstance(payload["metadata"]["query_time_ms"], int)


def _assert_mcp_error_envelope(payload: dict[str, Any], *, tool: str) -> None:
    assert contracts.MCP_ERROR_ENVELOPE_KEYS <= frozenset(payload.keys())
    assert payload["tool"] == tool
    assert payload["status"] == "error"
    assert "code" in payload["error"]
    assert "message" in payload["error"]
    assert contracts.MCP_METADATA_KEYS <= frozenset(payload["metadata"].keys())
    assert payload["metadata"]["read_only"] is True
    assert payload["metadata"]["source"] in contracts.ALLOWED_MCP_SOURCES


def _in_memory_parameters(tool: str, fx: dict[str, Any]) -> dict[str, Any]:
    if tool == TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE:
        return {
            "mode": "by_artifact",
            "artifact": "tools/surrealdb/context_stop_resolver.py",
            "evidence_records": fx["evidence_records"],
        }
    if tool == TOOL_CDB_CONTEXT_CLAIM_RESOLVE:
        return {
            "mode": "by_topic",
            "topic": "stop_conditions",
            "claim_records": fx["claim_records"],
        }
    if tool == TOOL_CDB_CONTEXT_MEMORY_GET:
        return {
            "mode": "by_scope",
            "scope": "wave14",
            "memory_records": fx["memory_records"],
        }
    if tool == TOOL_CDB_CONTEXT_TRUST_SUMMARY:
        return {"scope": "wave14", "topic": "context_tools"}
    if tool == TOOL_CDB_CONTEXT_DECISION_HISTORY:
        return {
            "mode": "by_topic",
            "topic": "context_tools",
            "decision_events": _DECISION_FIXTURE_RECORDS,
        }
    if tool == TOOL_CDB_CONTEXT_DECISION_REPLAY:
        return {
            "mode": "replay_by_scope",
            "scope": "wave14",
            "decision_events": _DECISION_FIXTURE_RECORDS,
        }
    raise AssertionError(f"Unhandled Wave-14 tool: {tool}")


@pytest.mark.unit
@pytest.mark.parametrize("tool", list(contracts.WAVE14_QUERY_RESULT_KEYS.keys()))
def test_wave14_ok_response_matches_query_contract(tool: str) -> None:
    fx = _load_fixture()
    handler = _WAVE14_HANDLERS[tool]
    result = handler({"tool": tool, "parameters": _in_memory_parameters(tool, fx)})

    _assert_mcp_ok_envelope(result, tool=tool)
    expected_keys = contracts.WAVE14_QUERY_RESULT_KEYS[tool]
    missing = expected_keys - frozenset(result["result"].keys())
    assert not missing, f"{tool} missing result keys: {sorted(missing)}"

    if "schema_version" in result["result"]:
        assert result["result"]["schema_version"] == contracts.SERVICE_SCHEMA_VERSIONS[tool]

    semantics = result["result"].get("approval_semantics") or {}
    assert semantics.get("no_echtgeld_go") is True


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool", "missing_key", "error_code"),
    [
        (TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE, "evidence_records", "missing_evidence_records"),
        (TOOL_CDB_CONTEXT_CLAIM_RESOLVE, "claim_records", "missing_claim_records"),
        (TOOL_CDB_CONTEXT_MEMORY_GET, "memory_records", "missing_memory_records"),
        (TOOL_CDB_CONTEXT_DECISION_HISTORY, "decision_events", "missing_decision_events"),
        (TOOL_CDB_CONTEXT_DECISION_REPLAY, "decision_events", "missing_decision_events"),
    ],
)
def test_wave14_missing_record_lists_fail_closed(
    tool: str, missing_key: str, error_code: str
) -> None:
    handler = _WAVE14_HANDLERS[tool]
    params = {"mode": "by_scope", "scope": "wave14"}
    if tool == TOOL_CDB_CONTEXT_CLAIM_RESOLVE:
        params = {"mode": "by_topic", "topic": "x"}
    if tool == TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE:
        params = {"mode": "by_artifact", "artifact": "some/path"}
    if tool in {TOOL_CDB_CONTEXT_DECISION_HISTORY, TOOL_CDB_CONTEXT_DECISION_REPLAY}:
        params = {"mode": "by_topic", "topic": "context_tools"}

    result = handler({"tool": tool, "parameters": params})
    _assert_mcp_error_envelope(result, tool=tool)
    assert result["error"]["code"] == error_code


@pytest.mark.unit
def test_trust_summary_missing_scope_is_structured_error() -> None:
    result = handle_cdb_context_trust_summary(
        {"tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY, "parameters": {}}
    )
    _assert_mcp_error_envelope(result, tool=TOOL_CDB_CONTEXT_TRUST_SUMMARY)
    assert result["error"]["code"] == "missing_scope"


@pytest.mark.unit
@pytest.mark.parametrize("tool", list(contracts.WAVE14_QUERY_RESULT_KEYS.keys()))
def test_wave14_wrong_tool_name_returns_invalid_tool(tool: str) -> None:
    handler = _WAVE14_HANDLERS[tool]
    result = handler({"tool": "wrong_tool", "parameters": {}})
    _assert_mcp_error_envelope(result, tool=tool)
    assert result["error"]["code"] == "invalid_tool"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tool", "records_key"),
    [
        (TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE, "evidence_records"),
        (TOOL_CDB_CONTEXT_CLAIM_RESOLVE, "claim_records"),
        (TOOL_CDB_CONTEXT_MEMORY_GET, "memory_records"),
        (TOOL_CDB_CONTEXT_DECISION_HISTORY, "decision_events"),
        (TOOL_CDB_CONTEXT_DECISION_REPLAY, "decision_events"),
    ],
)
def test_wave14_malformed_record_list_returns_error(tool: str, records_key: str) -> None:
    handler = _WAVE14_HANDLERS[tool]
    result = handler(
        {
            "tool": tool,
            "parameters": {
                "mode": "by_scope",
                "scope": "wave14",
                records_key: ["not-a-mapping"],
            },
        }
    )
    _assert_mcp_error_envelope(result, tool=tool)
    assert result["error"]["code"] == f"missing_{records_key}"


@pytest.mark.unit
def test_evidence_resolve_empty_match_is_ok_with_warning_not_fake_success() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "mode": "by_run_id",
                "run_id": "run-does-not-exist",
                "evidence_records": fx["evidence_records"],
            },
        }
    )
    _assert_mcp_ok_envelope(result, tool=TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE)
    assert result["result"]["matched_evidence"] == []
    assert "no_evidence_matched" in result["result"]["warnings"]


@pytest.mark.unit
def test_claim_resolve_empty_match_is_ok_with_warning_not_fake_success() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_claim_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "mode": "by_topic",
                "topic": "topic-with-no-claims",
                "claim_records": fx["claim_records"],
            },
        }
    )
    _assert_mcp_ok_envelope(result, tool=TOOL_CDB_CONTEXT_CLAIM_RESOLVE)
    assert result["result"]["matched_claims"] == []
    assert "no_claims_matched" in result["result"]["warnings"]


@pytest.mark.unit
def test_memory_get_empty_match_is_ok_with_warning_not_fake_success() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_memory_get(
        {
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "mode": "by_scope",
                "scope": "scope-with-no-memory",
                "memory_records": fx["memory_records"],
            },
        }
    )
    _assert_mcp_ok_envelope(result, tool=TOOL_CDB_CONTEXT_MEMORY_GET)
    assert result["result"]["matched_memory"] == []
    assert "no_memory_matched" in result["result"]["warnings"]


@pytest.mark.unit
@pytest.mark.parametrize("tool", list(contracts.WAVE14_QUERY_RESULT_KEYS.keys()))
def test_wave14_in_memory_ignores_forged_db_source_claims(
    monkeypatch, tool: str
) -> None:
    mock_adapter = MagicMock(spec=QueryAdapter)
    mock_adapter.status = "surrealdb-local"
    mock_adapter.execute.return_value = []
    patch_target = (
        "tools.mcp.context_decision_tools.build_adapter_from_params"
        if tool
        in {TOOL_CDB_CONTEXT_DECISION_HISTORY, TOOL_CDB_CONTEXT_DECISION_REPLAY}
        else "tools.mcp.context_evidence_memory_tools.build_adapter_from_params"
    )
    monkeypatch.setattr(patch_target, lambda params, tool_name: (mock_adapter, None))

    fx = _load_fixture()
    handler = _WAVE14_HANDLERS[tool]
    result = handler(
        {
            "tool": tool,
            "parameters": {
                **_in_memory_parameters(tool, fx),
                **_FORGED_DB_CLAIM_FIELDS,
            },
        }
    )

    _assert_mcp_ok_envelope(result, tool=tool)
    assert result["metadata"]["source"] == "in_memory"
    mock_adapter.execute.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("tool", list(contracts.WAVE14_QUERY_RESULT_KEYS.keys()))
def test_wave14_invalid_adapter_config_stays_fail_closed(tool: str) -> None:
    fx = _load_fixture()
    handler = _WAVE14_HANDLERS[tool]
    result = handler(
        {
            "tool": tool,
            "parameters": {
                "adapter_config_path": "/nonexistent/path/config.yaml",
                **_in_memory_parameters(tool, fx),
                **_FORGED_DB_CLAIM_FIELDS,
            },
        }
    )
    _assert_mcp_error_envelope(result, tool=tool)
    assert result["error"]["code"] == "adapter_config_error"
    assert result["metadata"]["source"] == "in_memory"


@pytest.mark.unit
def test_evidence_resolve_invalid_limit_returns_invalid_parameters(monkeypatch) -> None:
    mock_adapter = MagicMock(spec=QueryAdapter)
    mock_adapter.status = "surrealdb-local"
    monkeypatch.setattr(
        "tools.mcp.context_evidence_memory_tools.build_adapter_from_params",
        lambda params, tool_name: (mock_adapter, None),
    )

    result = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "adapter_config_path": _FAKE_CONFIG_PATH,
                "mode": "by_artifact",
                "artifact": "some/path",
                "limit": "bad",
            },
        }
    )
    _assert_mcp_error_envelope(result, tool=TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE)
    assert result["error"]["code"] == "invalid_parameters"
    mock_adapter.execute.assert_not_called()


@pytest.mark.unit
def test_decision_history_invalid_mode_returns_invalid_request() -> None:
    fx = _load_fixture()
    result = handle_cdb_context_decision_history(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_HISTORY,
            "parameters": {
                "mode": "bad_mode",
                "decision_events": _DECISION_FIXTURE_RECORDS,
            },
        }
    )
    _assert_mcp_error_envelope(result, tool=TOOL_CDB_CONTEXT_DECISION_HISTORY)
    assert result["error"]["code"] == "invalid_request"
