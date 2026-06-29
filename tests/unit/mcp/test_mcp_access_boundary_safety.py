"""
Safety tests for the MCP access boundary in #3481.
"""

from __future__ import annotations

import pytest

from tools.mcp_access_boundary import (
    DECISION_VALUES,
    BoundaryEntry,
    build_mcp_access_boundary,
)

pytestmark = pytest.mark.unit


def _entries_by_name(matrix: list[dict]) -> dict[str, dict]:
    return {entry["tool_name"]: entry for entry in matrix}


def test_standard_mutating_surrealdb_tools_are_forbidden() -> None:
    result = build_mcp_access_boundary()
    entries = _entries_by_name(result["matrix"])

    for tool_name in {"create", "insert", "upsert", "update", "delete", "relate", "run"}:
        entry = entries[tool_name]
        assert entry["decision"] == "FORBIDDEN_MUTATION"
        assert entry["mutation_risk"] != "none"


def test_raw_upstream_tools_stay_blocked() -> None:
    result = build_mcp_access_boundary()
    entries = _entries_by_name(result["matrix"])

    for tool_name in {"query", "select", "list", "use", "info"}:
        entry = entries[tool_name]
        assert entry["decision"] == "BLOCKED"
        assert entry["callable_status"] == "NOT_EXPOSED"
        assert entry["operational_status"] == "BLOCKED_RAW_MCP"


def test_readonly_tools_have_evidence() -> None:
    result = build_mcp_access_boundary()

    for entry in result["matrix"]:
        if entry["decision"] != "ALLOWED_READONLY":
            continue
        assert entry["handler_path"], f"{entry['tool_name']} missing handler_path"
        assert entry["permission_evidence"], f"{entry['tool_name']} missing permission evidence"
        assert entry["source_evidence"], f"{entry['tool_name']} missing source evidence"
        assert "tools/mcp/permission_guard.py" in entry["permission_evidence"]


def test_tool_decision_enum_is_strict() -> None:
    assert DECISION_VALUES == {
        "ALLOWED_READONLY",
        "FORBIDDEN_MUTATION",
        "FUTURE",
        "BLOCKED",
        "UNKNOWN",
    }


def test_unknown_requires_reason() -> None:
    with pytest.raises(ValueError, match="gap_reason"):
        BoundaryEntry(
            tool_name="future.unknown",
            tool_family="test",
            repo_present=False,
            exposed=False,
            callable_status="UNKNOWN",
            operational_status="UNKNOWN",
            decision="UNKNOWN",
            mutation_risk="unknown",
            allowed_mode="none",
            handler_path="",
            permission_evidence=[],
            source_evidence=[],
            gap_reason="",
        )

    entry = BoundaryEntry(
        tool_name="future.unknown",
        tool_family="test",
        repo_present=False,
        exposed=False,
        callable_status="UNKNOWN",
        operational_status="UNKNOWN",
        decision="UNKNOWN",
        mutation_risk="unknown",
        allowed_mode="none",
        handler_path="",
        permission_evidence=[],
        source_evidence=[],
        gap_reason="No grounded repo or upstream evidence yet.",
    )
    assert entry.gap_reason


def test_callable_operational_not_confused() -> None:
    result = build_mcp_access_boundary()
    entries = _entries_by_name(result["matrix"])

    show_audit = entries["context.show_audit"]
    assert show_audit["exposed"] is True
    assert show_audit["callable_status"] == "CALLABLE"
    assert show_audit["operational_status"] != "CALLABLE"

    cdb_context_search = entries["cdb_context_search"]
    assert cdb_context_search["exposed"] is False
    assert cdb_context_search["callable_status"] == "NOT_EXPOSED"


def test_no_live_db_claim_without_adapter_evidence() -> None:
    result = build_mcp_access_boundary()

    for entry in result["matrix"]:
        if entry["operational_status"] != "DB_BACKED_READONLY_PROVEN":
            continue
        evidence_blob = " ".join(entry["permission_evidence"] + entry["source_evidence"])
        assert "adapter" in evidence_blob.lower()
        assert entry["decision"] == "ALLOWED_READONLY"
