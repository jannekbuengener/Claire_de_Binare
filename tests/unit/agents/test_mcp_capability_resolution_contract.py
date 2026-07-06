"""MCP capability resolution contract tests (#3870).

Guards the MCP Capability Resolution protocol: config surface, bridge tool
inventory, in-process handler dispatch, and distinct fallback semantics
(blocked vs unavailable vs insufficient_evidence). No live MCP mutation,
no productive DB writes, no subprocess stdio server required in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.agents._agent_os_contract_helpers import (
    MCP_CAPABILITY_CONTEXT_TOOLS,
    MCP_CAPABILITY_RUNBOOK_ANCHORS,
    MCP_CONFIG_PATH,
)
from tests.unit.agents._bootloader_read_order_helpers import REPO_FALLBACK_REASONS
from tools.context_tool_inventory import build_inventory, classify_tools, discover_tools_from_repo
from tools.mcp.context_bridge import create_bridge
from tools.mcp.context_bridge import (
    _normalize_brain_evidence_fields,
    context_briefing_handler,
)
from tools.mcp import server as mcp_server

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]


def _mcp_config_path() -> Path:
    return REPO_ROOT / MCP_CONFIG_PATH


# ---------------------------------------------------------------------------
# Config exists / host knows config
# ---------------------------------------------------------------------------


def test_mcp_config_file_exists_and_declares_cdb_context_server() -> None:
    """Host MCP config exists with cdb_context stdio entry (#3870)."""
    path = _mcp_config_path()
    assert path.is_file(), f"missing MCP config: {MCP_CONFIG_PATH}"
    config = json.loads(path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    assert "cdb_context" in servers, "mcpServers must include cdb_context"
    entry = servers["cdb_context"]
    assert entry.get("enabled") is True
    args = entry.get("args", [])
    assert "-m" in args and "tools.mcp.server" in args


def test_mcp_capability_runbook_documents_resolution_protocol() -> None:
    """Runbook §1.5 anchors capability resolution; repo presence ≠ availability."""
    text = (
        REPO_ROOT / "docs" / "runbooks" / "surrealdb_context_mcp_access.md"
    ).read_text(encoding="utf-8")
    for anchor in MCP_CAPABILITY_RUNBOOK_ANCHORS:
        assert anchor in text, f"runbook missing capability anchor: {anchor!r}"


# ---------------------------------------------------------------------------
# Server surface + tool inventory
# ---------------------------------------------------------------------------


def test_context_bridge_lists_capability_resolution_tools() -> None:
    """Active bridge inventory exposes briefing / required_reads / readiness."""
    bridge = create_bridge()
    names = {tool["name"] for tool in bridge.list_tools()}
    missing = set(MCP_CAPABILITY_CONTEXT_TOOLS) - names
    assert not missing, f"bridge missing capability tools: {sorted(missing)}"
    for tool_name in MCP_CAPABILITY_CONTEXT_TOOLS:
        schema = bridge.get_tool_schema(tool_name)
        assert schema is not None
        assert schema["readOnly"] is True


def test_mcp_server_list_tools_includes_context_bridge_surface() -> None:
    """stdio server module exposes the same context tools as the bridge."""
    import asyncio

    server_names = {t.name for t in asyncio.run(mcp_server.list_tools())}
    bridge_names = {t["name"] for t in create_bridge().list_tools()}
    required = set(MCP_CAPABILITY_CONTEXT_TOOLS)
    assert required <= bridge_names
    assert required <= server_names


def test_tool_inventory_keeps_capability_levels_distinct() -> None:
    """Inventory separates present / exposed / callable / operational (#3870)."""
    classification = classify_tools()
    for key in ("present", "exposed", "callable", "operational"):
        assert key in classification
        assert isinstance(classification[key], list)

    inv = build_inventory()
    summary = inv["summary"]
    assert summary["session_callable_count"] >= len(MCP_CAPABILITY_CONTEXT_TOOLS) - 1
    assert summary["operational_count"] == 0
    assert summary["db_backed_count"] == 0


def test_session_callable_tools_do_not_imply_db_backed() -> None:
    """Callable inventory tier must not upgrade backing to DB_BACKED (#3870)."""
    tools = {t.tool_name: t for t in discover_tools_from_repo()}
    for name in ("context.required_reads", "context.readiness"):
        entry = tools[name]
        assert entry.callability_status == "session_callable"
        assert entry.backing_status != "DB_BACKED"


# ---------------------------------------------------------------------------
# Tool call works (in-process, no DB)
# ---------------------------------------------------------------------------


def test_context_required_reads_handler_returns_canon_list() -> None:
    """context.required_reads dispatches to a real handler with canon paths."""
    bridge = create_bridge()
    result = bridge.execute_tool(
        "context.required_reads",
        {
            "task_scope": "contract #3870",
            "target_issue": "#3870",
            "operation_mode": "read_only",
        },
    )
    assert result["status"] == "ok", result
    resolved = result.get("resolved_reads", [])
    paths = [item.get("path", "") for item in resolved if isinstance(item, dict)]
    assert paths
    assert any("agents/AGENTS.md" in p for p in paths)


def test_context_readiness_handler_read_only_mode() -> None:
    """context.readiness returns a readiness status for read_only scope."""
    bridge = create_bridge()
    result = bridge.execute_tool(
        "context.readiness",
        {
            "task_scope": "MCP capability contract #3870",
            "operation_mode": "read_only",
            "repo_root": str(REPO_ROOT),
        },
    )
    assert result["status"] == "ok", result
    readiness_status = result["readiness"]["status"]
    assert readiness_status in {
        "ready_for_read_only",
        "ready",
        "blocked_missing_context",
        "blocked",
        "degraded",
        "not_ready",
        "hold",
    }


def test_context_briefing_handler_emits_brain_evidence_without_db_records() -> None:
    """context.briefing works in-memory; no records → repo-only, not DB-proof."""
    result = context_briefing_handler(
        task_id="contract-3870",
        task_scope="MCP capability resolution contract",
        target_issue="#3870",
        requested_depth="quick",
        operation_mode="read_only",
    )
    assert result["status"] == "ok"
    block = result["briefing"]["brain_evidence_block"]
    assert block["brain_source"] == "repo-only"
    assert block["brain_status"] == "not-used"
    assert block["records_found"] == "none"
    assert block["context_available"] is False


# ---------------------------------------------------------------------------
# blocked vs unavailable vs insufficient_evidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "brain_source,brain_status,operator_trust,records,expected_reason,db_claim_allowed",
    [
        ("repo-only", "not-used", "LOW", 0, "insufficient_evidence", False),
        ("unavailable", "blocked", "BLOCKED", 0, "tool_blocked", False),
        ("unavailable", "not-used", "BLOCKED", 0, "unavailable", False),
        ("in_memory", "used", "MEDIUM", 2, "none", False),
    ],
)
def test_fallback_reasons_stay_distinct_and_never_imply_db_proof_when_blocked(
    brain_source: str,
    brain_status: str,
    operator_trust: str,
    records: int,
    expected_reason: str,
    db_claim_allowed: bool,
) -> None:
    """tool_blocked ≠ unavailable ≠ insufficient_evidence; blocked ≠ DB-proof (#3870)."""
    fields = _normalize_brain_evidence_fields(
        brain_source=brain_source,
        brain_status=brain_status,
        operator_trust_level=operator_trust,
        records_found=records,
    )
    assert fields["repo_fallback_reason"] in REPO_FALLBACK_REASONS
    assert fields["repo_fallback_reason"] == expected_reason
    if expected_reason == "tool_blocked":
        assert fields["context_tool_status"] == "blocked"
        assert fields["context_available"] is False
    if expected_reason == "insufficient_evidence":
        assert fields["repo_fallback_reason"] != "unavailable"
        assert fields["context_available"] is False
    assert fields.get("context_brain_used") is not True or records > 0


def test_tool_blocked_posture_does_not_authorize_surrealdb_local_claims() -> None:
    """tool_blocked must not be read as surrealdb-local / DB-backed proof."""
    brain_source = "unavailable"
    fields = _normalize_brain_evidence_fields(
        brain_source=brain_source,
        brain_status="blocked",
        operator_trust_level="BLOCKED",
        records_found=0,
    )
    assert fields["repo_fallback_reason"] == "tool_blocked"
    assert brain_source != "surrealdb-local"
    assert fields["context_available"] is False


def test_mcp_server_unknown_tool_returns_error_not_db_proof() -> None:
    """unknown_tool dispatch is fail-closed, not evidence of DB availability."""
    import asyncio

    result = asyncio.run(mcp_server.call_tool("cdb_context_nonexistent_tool_xyz", {}))
    payload = json.loads(result[0].text)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "unknown_tool"
