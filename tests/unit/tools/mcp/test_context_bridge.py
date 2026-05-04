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
            "context.self_explain",
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
        assert len(tools) == 8
        tool_names = [t["name"] for t in tools]
        assert "context.search" in tool_names
        assert "context.package" in tool_names
        assert "context.self_explain" in tool_names

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
        result = bridge.execute_tool("context.show_snapshot", {"snapshot_id": "test"})
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
        assert len(status["read_only_tools"]) == 8


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


class TestContextSelfExplainHandler:
    """Tests for context.self_explain tool handler (#2190)."""

    def test_tool_in_list_tools(self) -> None:
        """Tool is visible in list_tools()."""
        bridge = create_bridge()
        tool_names = [t["name"] for t in bridge.list_tools()]
        assert "context.self_explain" in tool_names

    def test_tool_is_read_only(self) -> None:
        """Tool is read-only."""
        bridge = create_bridge()
        schema = bridge.get_tool_schema("context.self_explain")
        assert schema is not None
        assert schema["readOnly"] is True

    def test_schema_contains_required_fields(self) -> None:
        """Input schema contains required fields."""
        bridge = create_bridge()
        schema = bridge.get_tool_schema("context.self_explain")
        required = schema["inputSchema"]["required"]
        assert "question" in required
        assert "explanation_type" in required
        assert "evidence_refs" in required

    def test_valid_call_returns_ok(self) -> None:
        """Valid call returns status ok with expected output fields."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Why is PR #1234 blocked?",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#1234", "#1235"],
                "scope": "pr-merge",
                "reasons": ["CI checks pending", "Review required"],
                "confidence": 0.8,
            },
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.self_explain"
        assert "explanation" in result
        assert "guardrails" in result
        assert "evidence_refs" in result
        assert result["explanation"]["explanation_type"] == "why_blocked"

    def test_output_contains_guardrails(self) -> None:
        """Output contains guardrail text from the builder."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test question",
                "explanation_type": "why_risky",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "ok"
        guardrails = result["guardrails"]
        assert len(guardrails) >= 1
        assert any("Handlungserlaubnis" in g for g in guardrails) or any(
            "Freigabe" in g for g in guardrails
        )

    def test_output_contains_evidence_refs(self) -> None:
        """Output contains evidence refs from input."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_stale",
                "evidence_refs": ["#ev1", "#ev2"],
            },
        )
        assert result["status"] == "ok"
        assert len(result["evidence_refs"]) == 2

    def test_invalid_explanation_type_fail_closed(self) -> None:
        """Invalid explanation_type fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "not_a_valid_type",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_explanation_type"

    def test_empty_question_fail_closed(self) -> None:
        """Empty question fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_question"

    def test_missing_question_fail_closed(self) -> None:
        """Missing question fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_question"

    def test_empty_evidence_refs_fail_closed(self) -> None:
        """Empty evidence_refs fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": [],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_evidence_refs"

    def test_missing_evidence_refs_fail_closed(self) -> None:
        """Missing evidence_refs fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_evidence_refs"

    def test_confidence_range_ok(self) -> None:
        """Confidence 0.0-1.0 is accepted."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_scope_blocked",
                "evidence_refs": ["#test"],
                "confidence": 0.95,
            },
        )
        assert result["status"] == "ok"
        assert result["confidence"] == 0.95

    def test_output_graph_path_present(self) -> None:
        """Output contains graph_path field."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_decision_current",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "ok"
        assert "graph_path" in result

    def test_output_source_refs_present(self) -> None:
        """Output contains source_refs field."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_evidence_weak",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "ok"
        assert "source_refs" in result

    def test_recommended_next_reads_present(self) -> None:
        """Output contains recommended_next_reads from input."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_agent_needs_go",
                "evidence_refs": ["#test"],
                "recommended_next_reads": ["doc_a.md", "doc_b.md"],
            },
        )
        assert result["status"] == "ok"
        assert result["recommended_next_reads"] == ["doc_a.md", "doc_b.md"]

    def test_all_nine_explanation_types_accepted(self) -> None:
        """All nine supported explanation types yield ok."""
        bridge = create_bridge()
        types = [
            "why_blocked",
            "why_risky",
            "why_stale",
            "why_decision_current",
            "why_decision_superseded",
            "why_scope_blocked",
            "why_evidence_weak",
            "why_agent_needs_go",
            "why_doc_untrusted",
        ]
        for expl_type in types:
            result = bridge.execute_tool(
                "context.self_explain",
                {
                    "question": f"Test for {expl_type}",
                    "explanation_type": expl_type,
                    "evidence_refs": ["#test"],
                },
            )
            assert result["status"] == "ok", f"Failed for type: {expl_type}"

    def test_evidence_refs_whitespace_element_fail_closed(self) -> None:
        """evidence_refs containing whitespace-only string fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#ok", "   "],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_evidence_refs"

    def test_evidence_refs_non_string_element_fail_closed(self) -> None:
        """evidence_refs containing non-string element fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#ok", 123],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_evidence_refs"

    def test_confidence_string_fail_closed(self) -> None:
        """Confidence as string fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "confidence": "0.9",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_confidence"

    def test_confidence_out_of_range_fail_closed(self) -> None:
        """Confidence > 1.0 fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "confidence": 1.5,
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_confidence"

    def test_confidence_none_is_ok(self) -> None:
        """Confidence=None yields ok with confidence: None in output."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_doc_untrusted",
                "evidence_refs": ["#test"],
                "confidence": None,
            },
        )
        assert result["status"] == "ok"
        assert result["confidence"] is None

    def test_confidence_true_fail_closed(self) -> None:
        """Confidence=True fails closed (bool is not a valid number)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "confidence": True,
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_confidence"

    def test_confidence_false_fail_closed(self) -> None:
        """Confidence=False fails closed (bool is not a valid number)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "confidence": False,
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_confidence"

    def test_reasons_non_string_fail_closed(self) -> None:
        """reasons containing non-string element fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "reasons": [42],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_reasons"

    def test_reasons_whitespace_element_fail_closed(self) -> None:
        """reasons containing whitespace-only string fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "reasons": ["valid", "   "],
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_reasons"

    def test_reasons_not_list_fail_closed(self) -> None:
        """reasons as non-list fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#test"],
                "reasons": "not-list",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_reasons"

    def test_reasons_missing_is_ok(self) -> None:
        """Missing reasons is ok — default reason derived from question."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Test with default reason",
                "explanation_type": "why_stale",
                "evidence_refs": ["#test"],
            },
        )
        assert result["status"] == "ok"
        assert len(result["explanation"]["reasons"]) >= 1


class TestContextReadinessHandler:
    """Tests for context.readiness tool handler (#2098)."""

    # --- Blocked: missing_context ---

    def test_missing_task_scope_returns_blocked_missing_context(self) -> None:
        """Missing task_scope fails closed with blocked_missing_context."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        assert result["readiness"]["status"] == "blocked_missing_context"
        assert "scope not defined" in result["readiness"]["missing_context"]

    def test_empty_task_scope_whitespace_returns_blocked_missing_context(self) -> None:
        """Whitespace-only task_scope fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "   ",
                "operation_mode": "read_only",
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"

    def test_invalid_operation_mode_returns_blocked_missing_context(self) -> None:
        """Unknown operation_mode fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Test invalid mode.",
                "operation_mode": "full_send",
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        assert any(
            "invalid operation_mode" in m
            for m in result["readiness"]["missing_context"]
        )

    def test_missing_operation_mode_returns_blocked_missing_context(self) -> None:
        """Missing operation_mode from kwargs fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Test missing mode.",
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        assert any(
            "invalid operation_mode" in m
            for m in result["readiness"]["missing_context"]
        )

    def test_missing_required_reads_returns_blocked_missing_context(self) -> None:
        """Missing minimum required reads blocks."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Inspect the risk engine.",
                "operation_mode": "read_only",
                "required_reads": ["AGENTS.md"],
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        missing = result["readiness"]["missing_context"]
        assert any("minimum required reads missing" in m for m in missing)

    def test_no_context_package_and_no_reads_blocks(self) -> None:
        """No context package and no required reads blocks."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Refactor something.",
                "operation_mode": "read_only",
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        assert any(
            "no context package and no required reads" in m
            for m in result["readiness"]["missing_context"]
        )

    def test_write_without_impact_report_returns_blocked_missing_context(self) -> None:
        """Write operation without impact report blocks."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Fix a bug.",
                "operation_mode": "write (code/docs)",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "evidence_refs": ["#1234"],
                "stop_conditions": ["S3: required reads unavailable"],
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        assert any(
            "write operation without impact report" in m
            for m in result["readiness"]["missing_context"]
        )

    def test_no_stop_conditions_blocks(self) -> None:
        """No stop conditions blocks."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Inspect logs.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        assert any(
            "no stop conditions" in m
            for m in result["readiness"]["missing_context"]
        )

    # --- Blocked: missing_evidence ---

    def test_write_without_evidence_returns_blocked_missing_evidence(self) -> None:
        """Write operation without evidence refs blocks on missing evidence."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Fix a bug in the ws service.",
                "operation_mode": "write (code/docs)",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "impact_refs": ["services/ws/"],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_evidence"
        assert any(
            "write operation without evidence" in e
            for e in result["readiness"]["missing_evidence"]
        )

    # --- Blocked: scope_drift ---

    def test_live_claim_in_scope_returns_blocked_scope_drift(self) -> None:
        """Task scope containing live/echtgeld claim is detected as scope drift."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Deploy system to production for go-live.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["status"] == "blocked_scope_drift"
        assert len(result["readiness"]["scope_drift_findings"]) >= 1

    # --- Ready states ---

    def test_read_only_with_minimum_inputs_returns_ready_for_read_only(self) -> None:
        """Full minimum inputs for read-only returns ready_for_read_only."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Inspect how the execution service handles fills.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["status"] == "ready_for_read_only"
        assert result["readiness"]["human_go_required"] is False

    def test_dry_run_returns_ready_for_dry_run(self) -> None:
        """Dry-run mode returns ready_for_dry_run."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Plan a fix for reconnect timeout.",
                "operation_mode": "dry_run",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["status"] == "ready_for_dry_run"

    def test_write_mode_with_context_returns_ready_for_human_go(self) -> None:
        """Write mode with full context returns ready_for_human_go."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Fix decimal precision bug.",
                "operation_mode": "write (code/docs)",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "evidence_refs": ["#1983"],
                "impact_refs": ["services/execution/"],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["status"] == "ready_for_human_go"
        assert result["readiness"]["human_go_required"] is True

    # --- human_go_required flag ---

    def test_human_go_required_true_for_write(self) -> None:
        """human_go_required is True for any write operation_mode."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Update config.",
                "operation_mode": "write (config/infra)",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "evidence_refs": ["#1234"],
                "impact_refs": ["infrastructure/"],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["human_go_required"] is True

    def test_human_go_required_false_for_read_only(self) -> None:
        """human_go_required is False for pure read-only non-trading scope."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Read documentation.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        assert result["readiness"]["human_go_required"] is False

    # --- Uncertainties ---

    def test_empty_uncertainties_is_ok(self) -> None:
        """uncertainties=[] is not a blocker (per correction)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Inspect log output.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
                "uncertainties": [],
            },
        )
        assert result["readiness"]["status"] == "ready_for_read_only"

    # --- Output contract compliance ---

    def test_output_contains_all_contract_fields(self) -> None:
        """Output contains all 10 contract fields."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Test output contract.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        r = result["readiness"]
        expected_fields = [
            "status", "reasons", "required_next_reads",
            "human_go_required", "stop_conditions",
            "missing_context", "missing_evidence",
            "scope_drift_findings", "uncertainties", "guardrails",
        ]
        for field in expected_fields:
            assert field in r, f"Missing output field: {field}"

    def test_guardrails_contain_boundary_text(self) -> None:
        """Guardrails always contain the readiness-is-not-authorization boundary."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Any task.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        guardrails = result["readiness"]["guardrails"]
        assert len(guardrails) >= 2
        assert any("not authorization" in g.lower() for g in guardrails)
        assert any("lr remains no-go" in g.lower() for g in guardrails)

    def test_readiness_not_authorization_explicit(self) -> None:
        """Readiness status is not an authorization signal."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Test authorization boundary.",
                "operation_mode": "read_only",
                "required_reads": [
                    "AGENTS.md",
                    "agents/AGENTS.md",
                    "agents/OPEN_CODE_AGENTS.md",
                    "docs/runbooks/CONTROL_REGISTER.md",
                    "CURRENT_STATUS.md",
                    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                ],
                "stop_conditions": ["S1: scope ambiguous"],
            },
        )
        r = result["readiness"]
        assert r["status"] != "ready_for_human_go"  # read_only => ready_for_read_only

    # --- Status determinism ---

    def test_same_inputs_same_output(self) -> None:
        """Same inputs produce identical readiness output."""
        bridge = create_bridge()
        inputs = {
            "task_scope": "Verify determinism.",
            "operation_mode": "read_only",
            "required_reads": [
                "AGENTS.md",
                "agents/AGENTS.md",
                "agents/OPEN_CODE_AGENTS.md",
                "docs/runbooks/CONTROL_REGISTER.md",
                "CURRENT_STATUS.md",
                "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
            ],
            "stop_conditions": ["S1: scope ambiguous"],
            "uncertainties": [],
        }
        r1 = bridge.execute_tool("context.readiness", inputs)
        r2 = bridge.execute_tool("context.readiness", inputs)
        assert r1 == r2
