"""Unit tests for Wave-19 Visual Control Room MCP adapter.

Issues:
    #2185 — [SURREALDB][CONTEXT][CONTROL-ROOM-TESTS] Add control room report tests
    Parent: #2179 (Wave-19 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/mcp/control_room_tools.py.
    All fixtures are inline — no file loading.
    No DB access. No SurrealDB SDK. No networking. No writes.

Coverage:
    - handle_control_room_view returns dict with status='ok' for valid inputs.
    - handle_control_room_view returns status='error' for invalid bundle.
    - handle_control_room_view with view_type returns single view.
    - handle_control_room_view without view_type returns all 9 views.
    - Error response contains guardrails.
    - Schema version present on all responses.
    - tool name present in all responses.
    - unknown view_type returns error dict (not exception).
    - Missing bundle returns error dict.
    - guardrails in response are non-empty.
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.mcp.control_room_tools import (
    SCHEMA_VERSION,
    TOOL_CDB_CONTROL_ROOM_VIEW,
    handle_control_room_view,
)

_AS_OF = "2026-05-08T12:00:00+00:00"


def _minimal_bundle(scope_id: str = "test-scope") -> dict[str, Any]:
    return {"meta": {"scope_id": scope_id, "level": "system"}}


def _clean_bundle() -> dict[str, Any]:
    return {
        "meta": {"scope_id": "wave19-mcp-test", "level": "system"},
        "sources": [{"source_path": "core/service.py", "has_documentation": True, "has_tests": True, "status": "current"}],
        "decisions": [{"decision_id": "dec-001", "status": "current", "evidence_refs": ["ev-001"]}],
        "evidence_items": [{"evidence_id": "ev-001", "strength": "strong", "expired": False}],
        "quality_scores": [
            {"scope_id": "wave19-mcp-test", "overall_grade": "good", "overall_score": 0.85, "blocking_dimensions": [], "watch_dimensions": [], "scored_at": _AS_OF}
        ],
    }


# ── Response contract ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestHandleControlRoomViewContract:
    def test_returns_dict(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert isinstance(result, dict)

    def test_tool_name_in_response(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert result["tool"] == TOOL_CDB_CONTROL_ROOM_VIEW

    def test_schema_version_in_response(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert result["schema_version"] == SCHEMA_VERSION

    def test_guardrails_non_empty_on_success(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert isinstance(result["guardrails"], list)
        assert len(result["guardrails"]) > 0

    def test_status_ok_for_valid_input(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert result["status"] == "ok"

    def test_metadata_present(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert "metadata" in result
        assert "schema_version" in result["metadata"]


# ── All-views mode ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAllViewsMode:
    def test_all_views_returns_9(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert result["view_count"] == 9

    def test_all_views_has_views_key(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert "views" in result
        assert isinstance(result["views"], list)

    def test_all_views_view_type_all(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        assert result["view_type"] == "all"


# ── Single view mode ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSingleViewMode:
    def test_single_view_returns_view_key(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), view_type="knowledge_graph_view", as_of=_AS_OF)
        assert "view" in result
        assert isinstance(result["view"], dict)

    def test_single_view_correct_view_type(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), view_type="architecture_map", as_of=_AS_OF)
        assert result["view_type"] == "architecture_map"

    def test_single_view_status_ok(self) -> None:
        result = handle_control_room_view(bundle=_clean_bundle(), view_type="quality_score_dashboard", as_of=_AS_OF)
        assert result["status"] == "ok"

    def test_single_view_schema_version_in_view(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), view_type="knowledge_graph_view", as_of=_AS_OF)
        assert "schema_version" in result["view"]

    def test_all_9_view_types_single_mode(self) -> None:
        from tools.surrealdb.control_room_view_builder import VIEW_TYPES

        for vt in VIEW_TYPES:
            result = handle_control_room_view(bundle=_minimal_bundle(), view_type=vt, as_of=_AS_OF)
            assert result["status"] == "ok", f"view_type {vt} returned error: {result.get('message')}"


# ── Error handling ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestErrorHandling:
    def test_missing_bundle_returns_error(self) -> None:
        result = handle_control_room_view(bundle=None, as_of=_AS_OF)
        assert result["status"] == "error"
        assert "bundle" in result["message"].lower()

    def test_invalid_bundle_type_returns_error(self) -> None:
        result = handle_control_room_view(bundle="not-a-dict", as_of=_AS_OF)  # type: ignore[arg-type]
        assert result["status"] == "error"

    def test_unknown_view_type_returns_error(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), view_type="nonexistent_view", as_of=_AS_OF)
        assert result["status"] == "error"
        assert "error_code" in result

    def test_error_response_has_tool_name(self) -> None:
        result = handle_control_room_view(bundle=None, as_of=_AS_OF)
        assert result["tool"] == TOOL_CDB_CONTROL_ROOM_VIEW

    def test_error_response_has_guardrails(self) -> None:
        result = handle_control_room_view(bundle=None, as_of=_AS_OF)
        assert isinstance(result["guardrails"], list)
        assert len(result["guardrails"]) > 0

    def test_error_response_has_schema_version(self) -> None:
        result = handle_control_room_view(bundle=None, as_of=_AS_OF)
        assert result["schema_version"] == SCHEMA_VERSION

    def test_missing_meta_returns_error(self) -> None:
        result = handle_control_room_view(bundle={}, as_of=_AS_OF)
        assert result["status"] == "error"

    def test_empty_scope_id_returns_error(self) -> None:
        result = handle_control_room_view(bundle={"meta": {"scope_id": ""}}, as_of=_AS_OF)
        assert result["status"] == "error"


# ── Guardrails safety checks ──────────────────────────────────────────────────


@pytest.mark.unit
class TestGuardrailsSafety:
    def test_no_trading_console_in_guardrails(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        guardrail_text = " ".join(result["guardrails"]).lower()
        assert "no trading" in guardrail_text or "trading console" in guardrail_text

    def test_no_live_go_in_guardrails(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        guardrail_text = " ".join(result["guardrails"]).lower()
        assert "live-readiness-go" in guardrail_text or "no live-readiness" in guardrail_text

    def test_no_echtgeld_in_guardrails(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        guardrail_text = " ".join(result["guardrails"]).lower()
        assert "echtgeld" in guardrail_text

    def test_read_only_in_guardrails(self) -> None:
        result = handle_control_room_view(bundle=_minimal_bundle(), as_of=_AS_OF)
        guardrail_text = " ".join(result["guardrails"]).lower()
        assert "read-only" in guardrail_text or "no mutations" in guardrail_text


# ── ContextBridge registry + wiring ──────────────────────────────────────────


@pytest.mark.unit
class TestContextBridgeRegistration:
    """Prove cdb_control_room_view is reachable through ContextBridge."""

    def _bridge(self):
        from tools.mcp.context_bridge import ContextBridge
        return ContextBridge()

    def test_tool_in_list_tools(self) -> None:
        bridge = self._bridge()
        names = [t["name"] for t in bridge.list_tools()]
        assert TOOL_CDB_CONTROL_ROOM_VIEW in names

    def test_tool_is_read_only(self) -> None:
        from tools.mcp.registry import ContextToolRegistry
        tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTROL_ROOM_VIEW)
        assert tool is not None
        assert tool.read_only is True

    def test_execute_tool_returns_ok(self) -> None:
        bridge = self._bridge()
        result = bridge.execute_tool(
            TOOL_CDB_CONTROL_ROOM_VIEW,
            {"bundle": _minimal_bundle(), "as_of": _AS_OF},
        )
        assert isinstance(result, dict)
        assert result["status"] == "ok"

    def test_execute_tool_single_view_type(self) -> None:
        bridge = self._bridge()
        result = bridge.execute_tool(
            TOOL_CDB_CONTROL_ROOM_VIEW,
            {
                "bundle": _minimal_bundle(),
                "view_type": "knowledge_graph_view",
                "as_of": _AS_OF,
            },
        )
        assert result["status"] == "ok"
        assert result["view_type"] == "knowledge_graph_view"
        assert "view" in result

    def test_execute_tool_missing_bundle_fail_closed(self) -> None:
        bridge = self._bridge()
        result = bridge.execute_tool(
            TOOL_CDB_CONTROL_ROOM_VIEW,
            {"as_of": _AS_OF},
        )
        assert result["status"] == "error"

    def test_execute_tool_unknown_view_type_fail_closed(self) -> None:
        bridge = self._bridge()
        result = bridge.execute_tool(
            TOOL_CDB_CONTROL_ROOM_VIEW,
            {"bundle": _minimal_bundle(), "view_type": "no_such_view", "as_of": _AS_OF},
        )
        assert result["status"] == "error"

    def test_no_write_semantics_in_tool_description(self) -> None:
        from tools.mcp.registry import ContextToolRegistry
        tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTROL_ROOM_VIEW)
        assert tool is not None
        desc_lower = tool.description.lower()
        assert "no db" in desc_lower or "read-only" in desc_lower

    def test_no_live_go_in_tool_description(self) -> None:
        from tools.mcp.registry import ContextToolRegistry
        tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTROL_ROOM_VIEW)
        assert tool is not None
        desc_lower = tool.description.lower()
        assert "no live-go" in desc_lower or "no live" in desc_lower
