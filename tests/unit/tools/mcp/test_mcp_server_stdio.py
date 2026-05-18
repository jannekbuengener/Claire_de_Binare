"""
MCP stdio server surface smoke-test.

Validates that tools/mcp/server.py's async MCP handler functions:
- expose all 6 Wave-14 cdb_context_* tools via list_tools()
- route call_tool to real handlers (not not_implemented stubs)
- return list[TextContent] with parseable JSON
- carry no_echtgeld_go semantics in the default in-memory mode
- fail gracefully (error payload, no exception) for unknown tool names

Requires: no DB, no Docker, no SurrealDB runtime, no subprocess.
Default adapter is noop/in-memory (ContextBridge default).

Issue linkage: #2559 (feat: expose context bridge via read-only stdio server)
"""
from __future__ import annotations

import asyncio
import json

import pytest
from mcp.types import TextContent

from tools.mcp import server as mcp_server

_WAVE14_TOOLS = [
    "cdb_context_evidence_resolve",
    "cdb_context_claim_resolve",
    "cdb_context_memory_get",
    "cdb_context_trust_summary",
    "cdb_context_decision_history",
    "cdb_context_decision_replay",
]


# ── list_tools surface ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_server_list_tools_exposes_all_wave14() -> None:
    """server.list_tools() returns all 6 Wave-14 cdb_context_* tool names."""
    tools = asyncio.run(mcp_server.list_tools())
    names = {t.name for t in tools}
    missing = set(_WAVE14_TOOLS) - names
    assert not missing, f"Wave-14 tools missing from server list_tools: {missing}"


@pytest.mark.unit
def test_server_list_tools_wave14_have_descriptions() -> None:
    """Each Wave-14 tool returned by list_tools() has a non-empty description."""
    tools = asyncio.run(mcp_server.list_tools())
    wave14 = {t.name: t for t in tools if t.name in _WAVE14_TOOLS}
    for name, tool in wave14.items():
        assert tool.description, f"Tool {name} has empty description"


# ── call_tool dispatch ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_server_call_tool_trust_summary_ok() -> None:
    """call_tool dispatches cdb_context_trust_summary to a real handler.

    Verifies:
    - result is list[TextContent]
    - payload is valid JSON
    - status == "ok"
    - no_echtgeld_go is True (read-only contract enforced at server surface)
    """
    result = asyncio.run(
        mcp_server.call_tool("cdb_context_trust_summary", {"scope": "wave14"})
    )
    assert isinstance(result, list) and len(result) == 1
    assert isinstance(result[0], TextContent)
    payload = json.loads(result[0].text)
    assert payload["status"] == "ok", f"Unexpected status: {payload}"
    assert payload["result"]["approval_semantics"]["no_echtgeld_go"] is True


@pytest.mark.unit
def test_server_call_tool_unknown_tool_returns_error_payload() -> None:
    """Calling an unknown tool returns an error payload, not an unhandled exception.

    Proves fail-closed semantics: unknown_tool error code surfaced via TextContent,
    not a Python traceback propagating out of call_tool().
    """
    result = asyncio.run(
        mcp_server.call_tool("cdb_context_does_not_exist", {})
    )
    assert isinstance(result, list) and len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "unknown_tool"


@pytest.mark.unit
def test_server_call_tool_default_mode_no_db_error() -> None:
    """Default (noop/in-memory) mode completes without any DB connection error.

    Proves that the server handles a tool call without Docker, SurrealDB,
    or any adapter_config_path — the default bridge is noop/in-memory.
    """
    result = asyncio.run(
        mcp_server.call_tool("cdb_context_trust_summary", {"scope": "smoke-noop"})
    )
    assert isinstance(result, list) and len(result) == 1
    payload = json.loads(result[0].text)
    raw = json.dumps(payload).lower()
    assert "connection" not in raw, f"Unexpected connection error in response: {payload}"
    assert "database_error" not in raw, f"Unexpected DB error in response: {payload}"
    assert payload["status"] in ("ok", "error")
