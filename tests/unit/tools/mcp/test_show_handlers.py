"""
Unit tests for context.show_snapshot and context.show_audit handlers.

- context.show_snapshot: implemented, read-only, deterministic registry snapshot.
- context.show_audit: implemented, read-only, deterministic registry audit snapshot.
#2100 / #2605 slice-2
"""

from tools.mcp.context_bridge import create_bridge
from tools.mcp.registry import ContextToolRegistry, ToolDefinition


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
    """Tests for context.show_audit handler."""

    def test_show_audit_returns_ok(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit", {"entity_id": "context.search"}
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.show_audit"
        assert result["audit"]["target_tool"] == "context.search"
        assert result["audit"]["exists"] is True
        assert result["audit"]["read_only"] is True

    def test_show_audit_handler_status_implemented_for_snapshot(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit", {"target_tool": "context.show_snapshot"}
        )
        assert result["status"] == "ok"
        assert result["audit"]["handler_status"] == "implemented"

    def test_show_audit_handler_status_implemented_for_self(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit", {"target_tool": "context.show_audit"}
        )
        assert result["status"] == "ok"
        assert result["audit"]["handler_status"] == "implemented"

    def test_show_audit_prefers_target_tool_over_entity_id(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit",
            {"target_tool": "context.show_snapshot", "entity_id": "context.search"},
        )
        assert result["status"] == "ok"
        assert result["audit"]["target_tool"] == "context.show_snapshot"

    def test_show_audit_reports_unknown_tool(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit", {"entity_id": "context.__does_not_exist__"}
        )
        assert result["status"] == "ok"
        assert result["audit"]["exists"] is False
        assert result["audit"]["handler_status"] == "unknown_tool"

    def test_show_audit_does_not_execute_target_tool(self) -> None:
        name = "__test_show_audit_no_dispatch__"

        def boom_handler(**kwargs) -> dict:
            raise AssertionError("target tool should not be executed by show_audit")

        ContextToolRegistry._tools[name] = ToolDefinition(
            name=name,
            description="Dispatch bomb tool",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            read_only=True,
            handler=boom_handler,
        )
        try:
            bridge = create_bridge()
            result = bridge.execute_tool("context.show_audit", {"target_tool": name})
            assert result["status"] == "ok"
            assert result["audit"]["target_tool"] == name
            assert result["audit"]["handler_status"] == "implemented"
        finally:
            del ContextToolRegistry._tools[name]

    def test_show_audit_in_registry(self) -> None:
        tool = ContextToolRegistry.get_tool("context.show_audit")
        assert tool is not None
        assert tool.read_only is True
        assert "entity_id" in tool.input_schema.get("properties", {})

    def test_show_audit_schema_has_required_fields(self) -> None:
        tool = ContextToolRegistry.get_tool("context.show_audit")
        schema = tool.input_schema
        props = schema.get("properties", {})
        forbidden_top_level_keys = {"oneOf", "anyOf", "allOf", "enum", "not"}
        assert "target_tool" in props
        assert "entity_id" in props
        assert schema.get("type") == "object"
        assert forbidden_top_level_keys.isdisjoint(schema)
        assert "tool" in tool.output_schema.get("properties", {})
        assert "status" in tool.output_schema.get("properties", {})


class TestNotImplementedErrorStructure:
    """Tests for fail-closed error response structure (show_audit)."""

    def test_invalid_entity_id_error_has_tool_field(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {})
        assert result["tool"] == "context.show_audit"

    def test_invalid_entity_id_error_has_status_error(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {})
        assert result["status"] == "error"

    def test_invalid_entity_id_error_has_code_and_message(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {})
        assert isinstance(result["error"]["code"], str)
        assert isinstance(result["error"]["message"], str)
        assert len(result["error"]["code"]) > 0
        assert len(result["error"]["message"]) > 0

    def test_extra_params_do_not_break_handler(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit",
            {"entity_id": "any", "audit_type": "all", "limit": 1, "extra": "ignored"},
        )
        assert result["status"] == "ok"
        assert result["audit"]["target_tool"] == "any"
