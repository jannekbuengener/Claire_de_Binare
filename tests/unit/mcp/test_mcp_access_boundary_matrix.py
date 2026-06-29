"""
Test-first boundary matrix for #3481.

Use case: CDB has a machine-readable MCP access boundary that separates
allowed read-only tools from forbidden, future, blocked, and unknown tools.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_bridge import create_bridge
from tools.mcp_access_boundary import (
    build_mcp_access_boundary,
    export_mcp_access_boundary_json,
    export_mcp_access_boundary_markdown,
)

pytestmark = pytest.mark.unit


REQUIRED_MATRIX_FIELDS = {
    "tool_name",
    "tool_family",
    "repo_present",
    "exposed",
    "callable_status",
    "operational_status",
    "decision",
    "mutation_risk",
    "allowed_mode",
    "handler_path",
    "permission_evidence",
    "source_evidence",
    "gap_reason",
}


def _entries_by_name(matrix: list[dict]) -> dict[str, dict]:
    return {entry["tool_name"]: entry for entry in matrix}


def test_mcp_boundary_matrix_exists(tmp_path: Path) -> None:
    result = build_mcp_access_boundary()

    assert "matrix" in result
    assert "groups" in result
    assert "summary" in result
    assert isinstance(result["matrix"], list)
    assert result["matrix"], "matrix must not be empty"

    first_entry = result["matrix"][0]
    assert REQUIRED_MATRIX_FIELDS <= set(first_entry.keys())

    json_path = tmp_path / "mcp_access_boundary_matrix.json"
    md_path = tmp_path / "mcp_access_boundary_matrix.md"

    export_mcp_access_boundary_json(result, json_path)
    export_mcp_access_boundary_markdown(result, md_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["matrix"]
    assert "# CDB MCP Access Boundary" in md_path.read_text(encoding="utf-8")


def test_all_exposed_context_tools_are_listed() -> None:
    bridge = create_bridge()
    result = build_mcp_access_boundary()

    exposed_by_bridge = {tool["name"] for tool in bridge.list_tools()}
    matrix_entries = _entries_by_name(result["matrix"])
    grouped_exposed = set(result["groups"]["exposed_tools"])

    assert exposed_by_bridge <= grouped_exposed

    for tool_name in exposed_by_bridge:
        entry = matrix_entries[tool_name]
        assert entry["repo_present"] is True
        assert entry["exposed"] is True


def test_repo_present_not_exposed_tools_are_separated() -> None:
    result = build_mcp_access_boundary()

    repo_present_not_exposed = set(result["groups"]["repo_present_not_exposed"])
    exposed = set(result["groups"]["exposed_tools"])

    assert repo_present_not_exposed.isdisjoint(exposed)
    assert {
        "cdb_context_search",
        "cdb_context_package",
        "cdb_context_trace",
    } <= repo_present_not_exposed

    matrix_entries = _entries_by_name(result["matrix"])
    for tool_name in repo_present_not_exposed:
        entry = matrix_entries[tool_name]
        assert entry["repo_present"] is True
        assert entry["exposed"] is False
