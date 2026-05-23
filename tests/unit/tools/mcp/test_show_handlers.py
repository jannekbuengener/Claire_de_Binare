"""
Unit tests for context.show_snapshot and context.show_audit handlers.

- context.show_snapshot: implemented, read-only, deterministic registry snapshot.
- context.show_audit: still stubbed (not_implemented).
#2100 / #2605 slice-1
"""

from tools.mcp.context_bridge import create_bridge
from tools.mcp.registry import ContextToolRegistry


class TestShowSnapshotHandler:
    """Tests for context.show_snapshot handler."""

    def test_show_snapshot_returns_ok(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_snapshot", {"snapshot_id": "snap_001"}
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.show_snapshot"
        assert result["snapshot"]["snapshot_id"] == "snap_001"

    def test_show_snapshot_includes_tool_names(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_snapshot", {"snapshot_id": "snap_001"}
        )
        assert result["status"] == "ok"
        assert isinstance(result["snapshot"]["tool_names"], list)
        assert "context.show_snapshot" in result["snapshot"]["tool_names"]

    def test_show_snapshot_in_registry(self) -> None:
        tool = ContextToolRegistry.get_tool("context.show_snapshot")
        assert tool is not None
        assert tool.read_only is True
        assert "snapshot_id" in tool.input_schema.get("properties", {})

    def test_show_snapshot_schema_has_required_fields(self) -> None:
        tool = ContextToolRegistry.get_tool("context.show_snapshot")
        assert "snapshot_id" in tool.input_schema.get("required", [])
        assert "tool" in tool.output_schema.get("properties", {})
        assert "status" in tool.output_schema.get("properties", {})

    def test_show_snapshot_invalid_snapshot_id_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_snapshot", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_snapshot_id"


class TestShowAuditHandler:
    """Tests for context.show_audit not-implemented handler."""

    def test_show_audit_returns_not_implemented(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {"entity_id": "ent_001"})
        assert result["status"] == "error"
        assert result["error"]["code"] == "not_implemented"

    def test_show_audit_error_mentions_tool_name(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {"entity_id": "ent_001"})
        assert "context.show_audit" in result["error"]["message"]

    def test_show_audit_in_registry(self) -> None:
        tool = ContextToolRegistry.get_tool("context.show_audit")
        assert tool is not None
        assert tool.read_only is True
        assert "entity_id" in tool.input_schema.get("properties", {})

    def test_show_audit_schema_has_required_fields(self) -> None:
        tool = ContextToolRegistry.get_tool("context.show_audit")
        assert "entity_id" in tool.input_schema.get("required", [])
        assert "tool" in tool.output_schema.get("properties", {})
        assert "status" in tool.output_schema.get("properties", {})


class TestNotImplementedErrorStructure:
    """Tests for not_implemented error response structure (show_audit)."""

    def test_not_implemented_error_has_tool_field(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {"entity_id": "ent_001"})
        assert result["tool"] == "context.show_audit"

    def test_not_implemented_error_has_status_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {"entity_id": "ent_001"})
        assert result["status"] == "error"

    def test_not_implemented_error_has_code_and_message(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {})
        assert isinstance(result["error"]["code"], str)
        assert isinstance(result["error"]["message"], str)
        assert len(result["error"]["code"]) > 0
        assert len(result["error"]["message"]) > 0

    def test_not_implemented_handler_ignores_all_params(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit",
            {"entity_id": "any", "audit_type": "all", "limit": 1, "extra": "ignored"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "not_implemented"
