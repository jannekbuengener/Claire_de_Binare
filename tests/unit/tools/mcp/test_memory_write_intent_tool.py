"""Unit tests for cdb_context_memory_write_intent MCP tool — #2704."""

from __future__ import annotations

import json

import pytest

from tools.mcp.context_bridge import ContextBridge
from tools.mcp.memory_output_contract import validate_memory_output_contract
from tools.mcp.memory_write_intent_tools import (
    MUTATION_ALLOWED,
    TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT,
    handle_cdb_context_memory_write_intent,
)
from tools.mcp.registry import ContextToolRegistry

pytestmark = pytest.mark.unit


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "agent:TEST/cursor",
        "namespace": "session",
        "memory_type": "working_memory",
        "content": "Test memory content for MCP write intent",
        "source_refs": ["docs/AGENTS.md@abc123"],
        "evidence_refs": ["ev-001"],
        "confidence": 0.9,
        "ttl": 3600,
        "expires_at": "2026-05-30T00:00:00+00:00",
        "created_by": "cursor-agent-v1",
        "created_at": "2026-05-29T04:00:00+00:00",
    }
    base.update(overrides)
    return base


def _valid_auth() -> dict:
    return {
        "human_go_token": "GO-2026-05-29-slice5",
        "authorized_by": "jannekbuengener",
        "authorized_at": "2026-05-29T11:00:00+00:00",
        "scope": "agent:TEST/cursor",
        "target_issue": "2606",
        "evidence_refs": ["github:issue/2606"],
        "operation": "create",
    }


def _request(**params) -> dict:
    return {
        "tool": TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT,
        "parameters": params,
    }


@pytest.mark.unit
def test_mutation_allowed_is_false() -> None:
    assert MUTATION_ALLOWED is False


@pytest.mark.unit
def test_default_dry_run_returns_gate_envelope() -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(record=_valid_record(), authorization=_valid_auth())
    )
    assert response["status"] == "ok"
    result = response["result"]
    assert result["gate_status"] == "approved_dry_run"
    assert result["gate_envelope"]["persist_allowed"] is False
    assert result["dry_run_only"] is True


@pytest.mark.unit
def test_blocked_without_authorization() -> None:
    response = handle_cdb_context_memory_write_intent(_request(record=_valid_record()))
    assert response["status"] == "ok"
    assert response["result"]["gate_status"] == "blocked_no_authorization"


@pytest.mark.unit
@pytest.mark.parametrize("flag", ["mutation_requested", "execute_write", "persist"])
def test_mutation_flag_blocked(flag: str) -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(record=_valid_record(), **{flag: True})
    )
    assert response["status"] == "error"
    assert response["error"]["code"] == "mutation_blocked_by_default"


@pytest.mark.unit
def test_unsafe_query_field_blocked() -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(record=_valid_record(), query="INSERT INTO agent_memory SET foo=1")
    )
    assert response["status"] == "error"
    assert response["error"]["code"] == "unsafe_input"


@pytest.mark.unit
def test_output_passes_memory_output_contract() -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(record=_valid_record(), authorization=_valid_auth())
    )
    violations = validate_memory_output_contract(response)
    assert violations == []


@pytest.mark.unit
def test_response_never_contains_raw_human_go_token() -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(record=_valid_record(), authorization=_valid_auth())
    )
    serialized = json.dumps(response)
    assert "GO-2026-05-29-slice5" not in serialized
    assert '"human_go_token"' not in serialized


@pytest.mark.unit
def test_registry_read_only_consistency() -> None:
    tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT)
    assert tool is not None
    assert tool.read_only is True
    ContextToolRegistry.assert_read_only_consistency()


@pytest.mark.unit
def test_bridge_execute_dry_run_only() -> None:
    bridge = ContextBridge()
    response = bridge.execute_tool(
        TOOL_CDB_CONTEXT_MEMORY_WRITE_INTENT,
        {"record": _valid_record(), "authorization": _valid_auth()},
    )
    assert response["status"] == "ok"
    assert response["result"]["gate_status"] == "approved_dry_run"
