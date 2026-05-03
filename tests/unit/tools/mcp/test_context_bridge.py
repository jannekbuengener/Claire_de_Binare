"""
Unit tests for Context MCP Bridge Scaffold.

Tests the scaffold structure without requiring live SurrealDB or network.
"""

import pytest
from tools.mcp.context_bridge import ContextBridge, create_bridge
from tools.mcp.registry import ContextToolRegistry, ToolDefinition


class TestContextToolRegistry:
    """Tests for the Context Tool Registry."""

    def test_registry_contains_v0_tools(self) -> None:
        """Verify all v0 tools are registered."""
        tool_names = ContextToolRegistry.list_tool_names()
        expected_tools = [
            "context.search",
            "context.trace",
            "context.explain_source",
            "context.show_snapshot",
            "context.show_audit",
            "context.package",
            "context.readiness",
        ]
        for expected in expected_tools:
            assert expected in tool_names, f"Tool {expected} not registered"

    def test_all_tools_are_read_only(self) -> None:
        """Verify all registered tools are read-only."""
        for tool in ContextToolRegistry.list_tools():
            assert tool.read_only is True, f"Tool {tool.name} is not read-only"

    def test_get_tool_returns_definition(self) -> None:
        """Verify get_tool returns tool definition."""
        tool = ContextToolRegistry.get_tool("context.search")
        assert tool is not None
        assert tool.name == "context.search"
        assert "query" in tool.input_schema.get("properties", {})


class TestContextSearchHandler:
    """Tests for context.search tool handler."""

    def test_missing_query_returns_error(self) -> None:
        """Empty/missing query fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_query"

    def test_empty_query_returns_error(self) -> None:
        """Empty string query fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": ""})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_query"

    def test_valid_query_returns_ok(self) -> None:
        """Valid query returns ok status with empty results (mocked)."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "test"})
        assert result["status"] == "ok"
        assert result["tool"] == "context.search"
        assert "results" in result
        assert "metadata" in result

    def test_limit_is_respected(self) -> None:
        """Limit parameter is accepted (mocked adapter returns empty)."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "test", "limit": 5})
        assert result["status"] == "ok"
        assert result["metadata"]["total_hits"] == 0

    def test_filters_are_accepted(self) -> None:
        """Filters parameter is accepted without error."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search",
            {
                "query": "test",
                "filters": {"source_types": ["decision"], "date_from": "2026-01-01"},
            },
        )
        assert result["status"] == "ok"


class TestContextTraceHandler:
    """Tests for context.trace tool handler."""

    def test_missing_target_id_returns_error(self) -> None:
        """Empty/missing target_id fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "target_not_found"

    def test_empty_target_id_returns_error(self) -> None:
        """Empty string target_id fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": ""})
        assert result["status"] == "error"
        assert result["error"]["code"] == "target_not_found"

    def test_valid_target_id_returns_ok(self) -> None:
        """Valid target_id returns ok status with trace (mocked)."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_abc123"})
        assert result["status"] == "ok"
        assert result["tool"] == "context.trace"
        assert "trace" in result
        assert "root" in result["trace"]
        assert "lineage" in result["trace"]

    def test_depth_parameter_accepted(self) -> None:
        """Depth parameter is accepted and respected."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace", {"target_id": "evt_abc123", "depth": 10}
        )
        assert result["status"] == "ok"
        assert len(result["trace"]["lineage"]) <= 10

    def test_depth_exceeds_max_returns_error(self) -> None:
        """Depth exceeding 20 returns error."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace", {"target_id": "evt_abc123", "depth": 25}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "depth_exceeded"

    def test_trace_root_contains_id(self) -> None:
        """Trace root contains the target_id."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_test"})
        assert result["status"] == "ok"
        assert result["trace"]["root"]["id"] == "evt_test"


class TestContextExplainSourceHandler:
    """Tests for context.explain_source tool handler."""

    def test_missing_source_ref_returns_error(self) -> None:
        """Empty/missing source_ref fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.explain_source", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_source_ref"

    def test_empty_source_ref_returns_error(self) -> None:
        """Empty string source_ref fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.explain_source", {"source_ref": ""})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_source_ref"

    def test_valid_source_ref_returns_ok(self) -> None:
        """Valid source_ref returns ok status with explanation (mocked)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_abc123"}
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.explain_source"
        assert "explanation" in result
        assert result["explanation"]["source_ref"] == "src_abc123"

    def test_include_chain_default_true(self) -> None:
        """include_chain defaults to True."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_abc123"}
        )
        assert result["status"] == "ok"
        assert result["metadata"]["include_chain"] is True
        assert "chain" in result["explanation"]["provenance"]

    def test_include_chain_false(self) -> None:
        """include_chain=False excludes chain."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "src_abc123", "include_chain": False},
        )
        assert result["status"] == "ok"
        assert result["metadata"]["include_chain"] is False
        assert "chain" not in result["explanation"]["provenance"]

    def test_explanation_contains_required_fields(self) -> None:
        """Explanation has all required fields per #2096."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_abc123"}
        )
        assert result["status"] == "ok"
        expl = result["explanation"]
        assert "source_ref" in expl
        assert "source_type" in expl
        assert "provenance" in expl
        assert "source_refs" in expl
        assert "confidence" in expl
        assert "warnings" in expl
        assert "stale" in expl
        assert "tombstone" in expl


class TestContextBridge:
    """Tests for the Context Bridge."""

    def test_bridge_creation(self) -> None:
        """Verify bridge can be created."""
        bridge = ContextBridge()
        assert bridge is not None

    def test_factory_function(self) -> None:
        """Verify factory function creates bridge."""
        bridge = create_bridge()
        assert isinstance(bridge, ContextBridge)

    def test_list_tools_returns_v0_tools(self) -> None:
        """Verify list_tools returns all v0 tools."""
        bridge = ContextBridge()
        tools = bridge.list_tools()
        assert len(tools) == 7
        tool_names = [t["name"] for t in tools]
        assert "context.search" in tool_names
        assert "context.package" in tool_names

    def test_get_tool_schema(self) -> None:
        """Verify get_tool_schema returns schema."""
        bridge = ContextBridge()
        schema = bridge.get_tool_schema("context.search")
        assert schema is not None
        assert schema["name"] == "context.search"
        assert schema["readOnly"] is True

    def test_execute_not_implemented_tool(self) -> None:
        """Verify executing stub tool returns not_implemented error."""
        bridge = ContextBridge()
        result = bridge.execute_tool("context.package", {"artifacts": []})
        assert result["status"] == "error"
        assert result["error"]["code"] == "not_implemented"

    def test_execute_unknown_tool(self) -> None:
        """Verify executing unknown tool returns error."""
        bridge = ContextBridge()
        result = bridge.execute_tool("context.unknown")
        assert result["status"] == "error"
        assert result["error"]["code"] == "unknown_tool"

    def test_read_only_status(self) -> None:
        """Verify read-only status is enforced."""
        bridge = ContextBridge()
        status = bridge.get_read_only_status()
        assert status["enforced"] is True
        assert len(status["read_only_tools"]) == 7


class TestDefensiveSchemaCopies:
    """Tests verifying that returned schemas are defensive copies."""

    def test_list_tools_returns_defensive_copies(self) -> None:
        """Verify list_tools returns defensive copies that caller can mutate."""
        bridge = ContextBridge()
        tools = bridge.list_tools()

        caller_schema = tools[0]["inputSchema"]
        original_properties = caller_schema.get("properties", {}).copy()

        caller_schema["properties"]["caller_added_field"] = {"type": "string"}

        tools_after = bridge.list_tools()
        returned_schema = tools_after[0]["inputSchema"]

        assert "caller_added_field" not in returned_schema.get(
            "properties", {}
        ), "Caller mutation should not affect returned schemas"

    def test_get_tool_schema_returns_defensive_copy(self) -> None:
        """Verify get_tool_schema returns defensive copy that caller can mutate."""
        bridge = ContextBridge()
        schema = bridge.get_tool_schema("context.search")

        caller_input = schema["inputSchema"]
        original_type = caller_input.get("type")

        caller_input["type"] = "mutated_by_caller"

        schema_after = bridge.get_tool_schema("context.search")
        assert (
            schema_after["inputSchema"]["type"] == original_type
        ), "Caller mutation should not affect returned schema"

    def test_mutation_of_returned_list_tools_does_not_affect_registry(self) -> None:
        """Verify mutating returned list_tools does not affect registry."""
        bridge = ContextBridge()

        tools = bridge.list_tools()
        tools[0]["name"] = "mutated_name"

        tools_after = bridge.list_tools()
        assert (
            tools_after[0]["name"] != "mutated_name"
        ), "Registry should not be affected by caller mutation"

    def test_mutation_of_returned_schema_does_not_affect_registry(self) -> None:
        """Verify mutating returned schema does not affect registry."""
        bridge = ContextBridge()

        schema = bridge.get_tool_schema("context.search")
        schema["inputSchema"]["properties"]["new_field"] = {"type": "string"}

        schema_after = bridge.get_tool_schema("context.search")
        assert "new_field" not in schema_after["inputSchema"].get(
            "properties", {}
        ), "Registry schema should not be mutated by caller"
