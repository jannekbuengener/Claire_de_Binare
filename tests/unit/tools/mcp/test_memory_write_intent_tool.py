"""Unit tests for cdb_context_memory_write_intent MCP tool — #2704 / G3a #2741."""

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
    assert result["operation_mode_resolved"] == "dry_run"
    assert result["productive_audit_status"] == "not_activated"
    assert result["mcp_phase"] == "1"


@pytest.mark.unit
def test_memory_record_alias_accepted() -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(memory_record=_valid_record(), authorization=_valid_auth())
    )
    assert response["status"] == "ok"
    assert response["result"]["gate_status"] == "approved_dry_run"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("operation_mode", "code", "gate_status"),
    [
        (
            "audit_persist_productive",
            "productive_audit_not_activated",
            "blocked_productive_audit_not_implemented",
        ),
        (
            "audit_persist_local",
            "local_audit_mcp_not_activated",
            "blocked_local_audit_mcp_not_activated",
        ),
        (
            "agent_memory_write",
            "agent_memory_write_not_activated",
            "blocked_agent_memory_write_not_activated",
        ),
    ],
)
def test_non_dry_run_operation_mode_refused(
    operation_mode: str, code: str, gate_status: str
) -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(
            record=_valid_record(),
            authorization=_valid_auth(),
            operation_mode=operation_mode,
        )
    )
    assert response["status"] == "refused"
    assert response["code"] == code
    assert response["operation_mode_resolved"] == operation_mode
    assert response["gate_status"] == gate_status
    assert response["productive_audit_status"] == "not_activated"
    assert response["mcp_phase"] == "1"


@pytest.mark.unit
def test_audit_persist_productive_hg_l_refuses_hg_p_required() -> None:
    auth = {**_valid_auth(), "human_go_tier": "HG-L"}
    response = handle_cdb_context_memory_write_intent(
        _request(
            record=_valid_record(),
            authorization=auth,
            operation_mode="audit_persist_productive",
        )
    )
    assert response["status"] == "refused"
    assert response["code"] == "hg_p_required"
    assert response["gate_status"] == "blocked_hg_p_required"


@pytest.mark.unit
@pytest.mark.parametrize("invalid_mode", ["  ", "bogus_mode", 123])
def test_invalid_operation_mode(invalid_mode) -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(
            record=_valid_record(),
            operation_mode=invalid_mode,
        )
    )
    assert response["status"] == "refused"
    assert response["code"] == "operation_mode_invalid"


@pytest.mark.unit
def test_audit_persist_local_boolean_flag_still_mutation_blocked() -> None:
    response = handle_cdb_context_memory_write_intent(
        _request(record=_valid_record(), audit_persist_local=True)
    )
    assert response["status"] == "error"
    assert response["error"]["code"] == "mutation_blocked_by_default"


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
