"""
Unit tests for Context MCP Bridge Scaffold.

Tests the scaffold structure without requiring live SurrealDB or network.
"""

from pathlib import Path
from typing import Any
import pytest
from tools.mcp.context_bridge import ContextBridge, create_bridge
from tools.mcp.registry import ContextToolRegistry

pytestmark = pytest.mark.unit


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
            "context.briefing",
            "context.stop_resolver",
            "context.required_reads",
            "cdb_context_impact",
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
        """Valid target_id returns ok status with trace payload."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_abc123"})
        assert result["status"] == "ok"
        assert result["tool"] == "context.trace"
        assert "trace" in result
        assert "root" in result["trace"]
        assert "lineage" in result["trace"]
        assert result["trace"]["lineage"] == []

    def test_depth_parameter_accepted(self) -> None:
        """Depth parameter is accepted without inventing lineage."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace", {"target_id": "evt_abc123", "depth": 10}
        )
        assert result["status"] == "ok"
        assert result["trace"]["lineage"] == []

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

    def test_trace_root_title_is_neutral(self) -> None:
        """Trace root title must not claim mock provenance."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_test"})
        assert result["status"] == "ok"
        assert result["trace"]["root"]["title"] == "Trace target: evt_test"


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
        """Registered tool name resolves to repo-/registry-only explanation."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "context.readiness"}
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.explain_source"
        assert "explanation" in result
        assert result["explanation"]["source_ref"] == "context.readiness"
        assert result["explanation"]["source_type"] == "tool"

    def test_include_chain_default_true(self) -> None:
        """include_chain defaults to True."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "context.readiness"}
        )
        assert result["status"] == "ok"
        assert result["metadata"]["include_chain"] is True
        assert "chain" in result["explanation"]["provenance"]

    def test_include_chain_false(self) -> None:
        """include_chain=False excludes chain."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "context.readiness", "include_chain": False},
        )
        assert result["status"] == "ok"
        assert result["metadata"]["include_chain"] is False
        assert "chain" not in result["explanation"]["provenance"]

    def test_explanation_contains_required_fields(self) -> None:
        """Explanation has all required fields per #2096."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "context.readiness"}
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

    def test_tool_prefix_resolves_registered_tool(self) -> None:
        """tool:<name> resolves exactly like the bare registered tool name."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "tool:context.readiness"}
        )
        assert result["status"] == "ok"
        assert result["explanation"]["source_ref"] == "tool:context.readiness"
        assert result["explanation"]["source_type"] == "tool"

    def test_repo_relative_path_returns_ok(self) -> None:
        """Repo-relative paths resolve as file sources."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "docs/runbooks/surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "ok"
        assert result["explanation"]["source_type"] == "file"
        assert (
            result["explanation"]["provenance"]["repo_relative_path"]
            == "docs/runbooks/surrealdb_context_mcp_access.md"
        )
        assert result["explanation"]["provenance"]["exists"] is True
        assert result["explanation"]["provenance"]["resolver"] == "repo"

    def test_path_prefix_resolves_repo_relative_file(self) -> None:
        """path:<path> only resolves repo files."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "path:docs/runbooks/surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "ok"
        assert result["explanation"]["source_type"] == "file"

    def test_backslash_path_normalizes_to_forward_slashes(self) -> None:
        """Backslash separators normalize deterministically."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": r"path:docs\runbooks\surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "ok"
        assert (
            result["explanation"]["provenance"]["repo_relative_path"]
            == "docs/runbooks/surrealdb_context_mcp_access.md"
        )

    def test_tool_prefix_does_not_fallback_to_path_resolution(self) -> None:
        """tool: only checks the registry."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "tool:docs/runbooks/surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "source_not_found"

    def test_path_prefix_does_not_fallback_to_tool_resolution(self) -> None:
        """path: only checks repo-relative files."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "path:context.readiness"}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "source_not_found"

    def test_unknown_source_ref_returns_source_not_found(self) -> None:
        """Unknown non-empty refs fail closed with source_not_found."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "context.__does_not_exist__"}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "source_not_found"

    def test_absolute_path_is_rejected(self) -> None:
        """Absolute paths are rejected instead of being resolved."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": r"C:\tmp\surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_source_ref"

    def test_unc_path_is_rejected(self) -> None:
        """UNC paths are rejected instead of being resolved."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": r"\\server\share\surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_source_ref"

    def test_parent_traversal_is_rejected(self) -> None:
        """Parent traversal is rejected instead of being resolved."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "../docs/runbooks/surrealdb_context_mcp_access.md"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_source_ref"

    def test_tool_provenance_uses_registry_truth(self) -> None:
        """Tool provenance reports registry fields without dispatching the tool."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "context.readiness"}
        )
        provenance = result["explanation"]["provenance"]
        assert provenance["tool_name"] == "context.readiness"
        assert provenance["read_only"] is True
        assert provenance["handler_status"] == "implemented"
        assert isinstance(provenance["input_schema_keys"], list)
        assert isinstance(provenance["output_schema_keys"], list)

    def test_include_chain_true_only_contains_internal_resolver_steps(self) -> None:
        """Resolver chain stays internal and deterministic."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "context.readiness"}
        )
        chain = result["explanation"]["provenance"]["chain"]
        assert [step["step"] for step in chain] == [
            "input_normalized",
            "registry_checked",
            "resolved",
        ]

    def test_file_output_uses_repo_relative_paths_only(self) -> None:
        """File output never leaks absolute local paths."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "docs/runbooks/surrealdb_context_mcp_access.md"},
        )
        rendered = str(result["explanation"])
        assert str(Path.cwd()) not in rendered
        assert Path.cwd().as_posix() not in rendered


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
        """Verify list_tools returns all registered tools.

        Original count was 13 (v0 base 11 + #2110 alias + #2111 impact).
        Wave-14 (#2122) added 6 more tools; count is now derived from registry
        so this test stays correct across future additions.
        """
        bridge = ContextBridge()
        tools = bridge.list_tools()
        # Count must match the registry exactly (no hidden tools, no extras)
        expected_count = len(ContextToolRegistry.list_tool_names())
        assert len(tools) == expected_count
        tool_names = [t["name"] for t in tools]
        # Base tools (v0 set + aliases)
        assert "context.search" in tool_names
        assert "context.package" in tool_names
        assert "context.self_explain" in tool_names
        assert "cdb_context_briefing" in tool_names
        # Wave-14 tools (#2122)
        wave14_tools = [
            "cdb_context_evidence_resolve",
            "cdb_context_claim_resolve",
            "cdb_context_memory_get",
            "cdb_context_trust_summary",
            "cdb_context_decision_history",
            "cdb_context_decision_replay",
        ]
        for name in wave14_tools:
            assert name in tool_names, f"Wave-14 tool missing: {name}"

    def test_get_tool_schema(self) -> None:
        """Verify get_tool_schema returns schema."""
        bridge = ContextBridge()
        schema = bridge.get_tool_schema("context.search")
        assert schema is not None
        assert schema["name"] == "context.search"
        assert schema["readOnly"] is True

    def test_execute_show_audit_tool(self) -> None:
        """Verify executing context.show_audit returns deterministic audit output."""
        bridge = ContextBridge()
        result = bridge.execute_tool(
            "context.show_audit", {"target_tool": "context.show_audit"}
        )
        assert result["status"] == "ok"
        assert result["audit"]["handler_status"] == "implemented"

    def test_execute_unknown_tool(self) -> None:
        """Verify executing unknown tool returns error."""
        bridge = ContextBridge()
        result = bridge.execute_tool("context.unknown")
        assert result["status"] == "error"
        assert result["error"]["code"] == "unknown_tool"

    def test_read_only_status(self) -> None:
        """Verify read-only status is enforced for all registered tools.

        Count is derived from registry so it stays correct when new tools
        are added (Wave-14 brought this from 13 to 19 via #2122).
        """
        bridge = ContextBridge()
        status = bridge.get_read_only_status()
        assert status["enforced"] is True
        # All registered tools must be read-only — no hardcoded magic number
        expected_count = len(ContextToolRegistry.list_tool_names())
        assert len(status["read_only_tools"]) == expected_count


class TestDefensiveSchemaCopies:
    """Tests verifying that returned schemas are defensive copies."""

    def test_list_tools_returns_defensive_copies(self) -> None:
        """Verify list_tools returns defensive copies that caller can mutate."""
        bridge = ContextBridge()
        tools = bridge.list_tools()

        caller_schema = tools[0]["inputSchema"]

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

    def test_missing_canon_on_effective_scan_root_blocks(self, tmp_path) -> None:
        """Missing minimum canon files at effective_scan_root blocks (#2848)."""
        (tmp_path / "AGENTS.md").write_text("pointer\n", encoding="utf-8")
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Inspect the risk engine.",
                "operation_mode": "read_only",
                "stop_conditions": ["S1: unit test"],
                "repo_root": str(tmp_path),
                "required_reads": ["AGENTS.md"],
            },
        )
        assert result["readiness"]["status"] == "blocked_missing_context"
        missing = result["readiness"]["missing_context"]
        assert any("effective_scan_root" in m for m in missing)

    def test_no_context_package_and_no_reads_blocks_without_canon_on_disk(
        self, tmp_path
    ) -> None:
        """No package, empty required_reads, and no canon on scan root blocks."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Refactor something.",
                "operation_mode": "read_only",
                "stop_conditions": ["S1: unit test"],
                "repo_root": str(tmp_path),
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
            "no stop conditions" in m for m in result["readiness"]["missing_context"]
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
            "status",
            "reasons",
            "required_next_reads",
            "human_go_required",
            "stop_conditions",
            "missing_context",
            "missing_evidence",
            "scope_drift_findings",
            "uncertainties",
            "guardrails",
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


class TestContextBriefingHandler:
    """Tests for context.briefing tool handler (#2105)."""

    def test_tool_in_list_tools(self) -> None:
        """Tool is visible in list_tools()."""
        bridge = create_bridge()
        tool_names = [t["name"] for t in bridge.list_tools()]
        assert "context.briefing" in tool_names

    def test_tool_is_read_only(self) -> None:
        """Tool is read-only."""
        bridge = create_bridge()
        schema = bridge.get_tool_schema("context.briefing")
        assert schema is not None
        assert schema["readOnly"] is True

    def test_missing_task_id_fails_closed(self) -> None:
        """Missing task_id fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_scope": "Test scope.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_id"

    def test_missing_task_scope_fails_closed(self) -> None:
        """Missing task_scope fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_scope"

    def test_invalid_depth_fails_closed(self) -> None:
        """Invalid requested_depth fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Test scope.",
                "target_issue": None,
                "requested_depth": "invalid",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_depth"

    def test_invalid_operation_mode_fails_closed(self) -> None:
        """Invalid operation_mode fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Test scope.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "invalid_mode",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_operation_mode"

    def test_minimum_valid_request_returns_ok(self) -> None:
        """Minimum valid request returns ok with briefing."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-2104-land-schema",
                "task_scope": "Define the agent briefing schema v1.",
                "target_issue": "#2104",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.briefing"
        assert "briefing" in result
        b = result["briefing"]
        assert b["briefing_id"] != ""
        assert len(b["briefing_id"]) == 16

    def test_briefing_contains_session_context(self) -> None:
        """Successful response includes briefing.session_context."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-session-context",
                "task_scope": "Add structured session context.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        assert "session_context" in result["briefing"]

    def test_session_context_core_working_memory_fields(self) -> None:
        """session_context exposes stable working-memory defaults."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-working-memory",
                "task_scope": "Validate session context defaults.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["memory_type"] == "working_memory"
        assert session_context["session_only"] is True
        assert session_context["ttl_seconds"] <= 14400

    def test_missing_repo_and_github_state_degrade_without_fabrication(self) -> None:
        """Missing optional repo/github state degrades to unknown or empty values."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-missing-session-state",
                "task_scope": "Validate missing session state handling.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["repo_state"] == {
            "branch": "unknown",
            "commit": "unknown",
            "working_tree": "unknown",
        }
        assert session_context["github_state"]["target_issue"] is None
        assert session_context["github_state"]["related_prs"] == []
        assert session_context["github_state"]["open_epics"] == []

    def test_default_brain_context_is_repo_only(self) -> None:
        """Without DB or inline records, briefing stays repo-only and non-DB-backed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-default-brain-context",
                "task_scope": "Validate repo-only derived brain context.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["brain_source"] == "repo-only"
        assert session_context["brain_status"] == "not-used"
        assert session_context["agent_operating_mode"]["db_claims_allowed"] is False

    def test_repo_only_session_context_matches_brain_evidence_gate_defaults(
        self,
    ) -> None:
        """repo-only session handoff stays non-DB-backed and explicitly not-used."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-brain-evidence-defaults",
                "task_scope": "Validate Brain Evidence Gate compatibility.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["brain_status"] == "not-used"
        assert session_context["agent_operating_mode"]["db_claims_allowed"] is False
        assert any(
            "no DB-backed memory or evidence claims" in item
            for item in session_context["limitations"]
        )

    def test_inline_records_derive_in_memory_brain_source(self) -> None:
        """Inline enrichment records derive in-memory brain context without DB claims."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-inline-in-memory",
                "task_scope": "Validate in-memory derived Brain Evidence compatibility.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "memory_records": [
                    {"memory_id": "mem-001", "scope": "wave14", "content": "test"}
                ],
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["brain_source"] == "in_memory"
        assert session_context["brain_status"] == "used"
        assert session_context["agent_operating_mode"]["db_claims_allowed"] is False

    def test_db_requested_briefing_uses_surrealdb_local_metadata(
        self, monkeypatch
    ) -> None:
        """DB-backed briefing claims require real adapter metadata, not caller input."""
        monkeypatch.setattr(
            "tools.mcp.context_evidence_memory_tools.handle_cdb_context_trust_summary",
            lambda request: {
                "tool": "cdb_context_trust_summary",
                "status": "ok",
                "result": {"scope": request["parameters"]["scope"]},
                "metadata": {
                    "query_time_ms": 0,
                    "source": "surrealdb-local",
                    "read_only": True,
                },
            },
        )
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-surrealdb-derived",
                "task_scope": "Validate surrealdb-local derived claim mode.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "adapter_config_path": "infrastructure/config/surrealdb/context_query.local.example.yaml",
                "secrets_path": "D:/tmp/fake-secrets",
            },
        )
        assert result["status"] == "ok"
        session_context = result["briefing"]["session_context"]
        assert session_context["brain_source"] == "surrealdb-local"
        assert session_context["brain_status"] == "used"
        assert session_context["agent_operating_mode"]["db_claims_allowed"] is True

    def test_db_requested_briefing_propagates_adapter_config_error(
        self, monkeypatch
    ) -> None:
        """Config/auth failures on the DB-backed path fail closed on briefing."""
        monkeypatch.setattr(
            "tools.mcp.context_evidence_memory_tools.handle_cdb_context_trust_summary",
            lambda request: {
                "tool": "cdb_context_trust_summary",
                "status": "error",
                "error": {
                    "code": "adapter_config_error",
                    "message": "SURREALDB_ENV not found",
                },
                "metadata": {
                    "query_time_ms": 0,
                    "source": "in_memory",
                    "read_only": True,
                },
            },
        )
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-db-config-error",
                "task_scope": "Validate fail-closed DB config handling.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "adapter_config_path": "infrastructure/config/surrealdb/context_query.local.example.yaml",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "adapter_config_error"

    def test_db_requested_briefing_fails_closed_on_unavailable_source(
        self, monkeypatch
    ) -> None:
        """Soft-unavailable DB status still fails closed on briefing."""
        monkeypatch.setattr(
            "tools.mcp.context_evidence_memory_tools.handle_cdb_context_trust_summary",
            lambda request: {
                "tool": "cdb_context_trust_summary",
                "status": "ok",
                "result": {"scope": request["parameters"]["scope"]},
                "metadata": {
                    "query_time_ms": 0,
                    "source": "surrealdb-local-unavailable",
                    "read_only": True,
                },
            },
        )
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-db-unavailable",
                "task_scope": "Validate unavailable surrealdb claim mode.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "adapter_config_path": "infrastructure/config/surrealdb/context_query.local.example.yaml",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "adapter_unavailable"

    def test_caller_brain_source_is_ignored_without_db(self) -> None:
        """Caller-supplied surrealdb-local claims cannot fake DB readiness."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-ignore-caller-brain-source",
                "task_scope": "Validate caller claim suppression.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "brain_source": "surrealdb-local",
                "brain_status": "used",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["brain_source"] == "repo-only"
        assert session_context["brain_status"] == "not-used"
        assert session_context["agent_operating_mode"]["db_claims_allowed"] is False
        assert any(
            "caller input ignored" in item for item in session_context["limitations"]
        )

    def test_repo_state_values_are_preserved_when_provided(self) -> None:
        """Caller-provided repo_state values are preserved."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-repo-state-preserve",
                "task_scope": "Validate repo_state preservation.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "repo_state": {
                    "branch": "feature/session-context",
                    "commit": "abc123def456",
                    "working_tree": "dirty",
                },
            },
        )
        assert result["briefing"]["session_context"]["repo_state"] == {
            "branch": "feature/session-context",
            "commit": "abc123def456",
            "working_tree": "dirty",
        }

    def test_github_state_values_are_preserved_when_provided(self) -> None:
        """Caller-provided github_state values are preserved."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-github-state-preserve",
                "task_scope": "Validate github_state preservation.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "github_state": {
                    "target_issue": "#2607",
                    "related_prs": ["#2613", "#2614"],
                    "open_epics": ["#2607"],
                },
            },
        )
        assert result["briefing"]["session_context"]["github_state"] == {
            "target_issue": "#2607",
            "related_prs": ["#2613", "#2614"],
            "open_epics": ["#2607"],
        }

    def test_repo_state_branch_changes_briefing_id(self) -> None:
        """Different normalized repo_state.branch values change briefing_id."""
        bridge = create_bridge()
        base = {
            "task_id": "cdb-briefing-hash-repo-branch",
            "task_scope": "Validate briefing_id repo_state sensitivity.",
            "target_issue": "#2607",
            "requested_depth": "quick",
            "operation_mode": "read_only",
            "repo_state": {
                "commit": "abc123",
                "working_tree": "clean",
            },
        }
        r1 = bridge.execute_tool(
            "context.briefing",
            {**base, "repo_state": {**base["repo_state"], "branch": "branch-a"}},
        )
        r2 = bridge.execute_tool(
            "context.briefing",
            {**base, "repo_state": {**base["repo_state"], "branch": "branch-b"}},
        )
        assert r1["briefing"]["briefing_id"] != r2["briefing"]["briefing_id"]

    def test_github_state_changes_briefing_id(self) -> None:
        """Different normalized github_state values change briefing_id."""
        bridge = create_bridge()
        base = {
            "task_id": "cdb-briefing-hash-github-state",
            "task_scope": "Validate briefing_id github_state sensitivity.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
        }
        r1 = bridge.execute_tool(
            "context.briefing",
            {
                **base,
                "github_state": {
                    "target_issue": "#2607",
                    "related_prs": ["#2618"],
                    "open_epics": [],
                },
            },
        )
        r2 = bridge.execute_tool(
            "context.briefing",
            {
                **base,
                "github_state": {
                    "target_issue": "#2607",
                    "related_prs": ["#9999"],
                    "open_epics": [],
                },
            },
        )
        assert r1["briefing"]["briefing_id"] != r2["briefing"]["briefing_id"]

    def test_derived_brain_context_changes_briefing_id(self) -> None:
        """Different derived brain contexts change briefing_id."""
        bridge = create_bridge()
        base = {
            "task_id": "cdb-briefing-hash-brain-source",
            "task_scope": "Validate briefing_id brain_source sensitivity.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
        }
        r1 = bridge.execute_tool("context.briefing", base)
        r2 = bridge.execute_tool(
            "context.briefing",
            {
                **base,
                "memory_records": [
                    {"memory_id": "mem-001", "scope": "wave14", "content": "test"}
                ],
            },
        )
        assert r1["briefing"]["briefing_id"] != r2["briefing"]["briefing_id"]

    def test_working_assumptions_change_briefing_id(self) -> None:
        """Different working_assumptions values change briefing_id."""
        bridge = create_bridge()
        base = {
            "task_id": "cdb-briefing-hash-assumptions",
            "task_scope": "Validate briefing_id assumptions sensitivity.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
        }
        r1 = bridge.execute_tool(
            "context.briefing", {**base, "working_assumptions": ["assumption-a"]}
        )
        r2 = bridge.execute_tool(
            "context.briefing", {**base, "working_assumptions": ["assumption-b"]}
        )
        assert r1["briefing"]["briefing_id"] != r2["briefing"]["briefing_id"]

    def test_malformed_session_context_inputs_are_normalized_before_hashing(
        self,
    ) -> None:
        """Malformed session-context inputs hash by normalized, deterministic values."""
        bridge = create_bridge()
        base = {
            "task_id": "cdb-briefing-hash-malformed-session-context",
            "task_scope": "Validate normalized hashing for malformed session inputs.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
        }
        malformed_inputs = {
            "brain_source": object(),
            "brain_status": 1,
            "repo_state": "bad",
            "github_state": "bad",
            "working_assumptions": "bad",
            "limitations": "bad",
        }
        r1 = bridge.execute_tool("context.briefing", {**base, **malformed_inputs})
        r2 = bridge.execute_tool("context.briefing", {**base, **malformed_inputs})
        assert r1["briefing"]["briefing_id"] == r2["briefing"]["briefing_id"]

    def test_identical_normalized_session_context_inputs_keep_same_briefing_id(
        self,
    ) -> None:
        """Equivalent normalized inputs produce identical briefing_id."""
        bridge = create_bridge()
        inputs_a = {
            "task_id": "cdb-briefing-hash-normalized-equality",
            "task_scope": "Validate normalized session hashing equality.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
            "repo_state": {
                "branch": " feature/session-context ",
                "commit": " abc123 ",
                "working_tree": "dirty",
            },
            "github_state": {
                "target_issue": None,
                "related_prs": ["#2618"],
                "open_epics": ["#2607"],
            },
            "working_assumptions": ["assumption"],
            "limitations": ["limit", "limit"],
        }
        inputs_b = {
            "task_id": "cdb-briefing-hash-normalized-equality",
            "task_scope": "Validate normalized session hashing equality.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
            "repo_state": {
                "branch": "feature/session-context",
                "commit": "abc123",
                "working_tree": "dirty",
            },
            "github_state": {
                "target_issue": None,
                "related_prs": ["#2618"],
                "open_epics": ["#2607"],
            },
            "working_assumptions": ["assumption"],
            "limitations": ["limit"],
        }
        r1 = bridge.execute_tool("context.briefing", inputs_a)
        r2 = bridge.execute_tool("context.briefing", inputs_b)
        assert r1["briefing"]["briefing_id"] == r2["briefing"]["briefing_id"]

    def test_malformed_working_assumptions_degrade_to_empty_with_limitation(
        self,
    ) -> None:
        """Malformed working_assumptions fail closed to an empty list."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-bad-assumptions",
                "task_scope": "Validate working_assumptions degradation.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "working_assumptions": "not-a-list",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["working_assumptions"] == []
        assert any(
            "working_assumptions malformed" in item
            for item in session_context["limitations"]
        )

    def test_malformed_limitations_degrade_safely(self) -> None:
        """Malformed limitations fail closed to generated limitations only."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-bad-limitations",
                "task_scope": "Validate limitations degradation.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "limitations": "not-a-list",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert any(
            "limitations malformed" in item for item in session_context["limitations"]
        )
        assert all(isinstance(item, str) for item in session_context["limitations"])

    def test_session_context_can_populate_brain_evidence_fields(self) -> None:
        """session_context plus sibling briefing fields can fill all Brain Evidence keys."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-brain-evidence-complete",
                "task_scope": "Validate Brain Evidence handoff completeness.",
                "target_issue": "#2607",
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "repo_state": {
                    "branch": "fix/2613-noise-freeze-remaining-push-triggers",
                    "commit": "f345cf0c",
                    "working_tree": "dirty",
                },
                "github_state": {
                    "target_issue": "#2607",
                    "related_prs": ["#2613"],
                    "open_epics": ["#2607"],
                },
                "working_assumptions": [
                    "Use briefing session context before planning."
                ],
            },
        )
        briefing = result["briefing"]
        session_context = briefing["session_context"]

        brain_evidence = {
            "brain_source": session_context["brain_source"],
            "brain_status": session_context["brain_status"],
            "tools_or_queries": session_context["working_assumptions"]
            or session_context["limitations"],
            "records_or_results": [
                session_context["repo_state"]["branch"],
                session_context["repo_state"]["commit"],
                str(session_context["github_state"]["target_issue"]),
                *session_context["github_state"]["related_prs"],
                *session_context["github_state"]["open_epics"],
            ],
            "repo_crosscheck": [
                session_context["repo_state"]["branch"],
                session_context["repo_state"]["commit"],
                *briefing["required_reads"],
            ],
            "impact_on_plan": [
                *session_context["working_assumptions"],
                *session_context["limitations"],
            ],
            "limitations": session_context["limitations"],
        }

        assert brain_evidence["brain_source"] == "repo-only"
        assert brain_evidence["brain_status"] == "not-used"
        for key in (
            "tools_or_queries",
            "records_or_results",
            "repo_crosscheck",
            "impact_on_plan",
            "limitations",
        ):
            assert isinstance(brain_evidence[key], list)
            assert brain_evidence[key]

    def test_session_context_read_only_mode_sets_human_go_false(self) -> None:
        """read_only operation mode stays non-human-gated in session_context."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-read-only-mode",
                "task_scope": "Validate read-only session mode.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        session_context = result["briefing"]["session_context"]
        assert session_context["agent_operating_mode"]["operation_mode"] == "read_only"
        assert session_context["agent_operating_mode"]["human_go_required"] is False

    def test_output_contains_all_16_contract_fields(self) -> None:
        """Output contains all 16 briefing contract fields per #2104 schema."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Validate output contract.",
                "target_issue": "#2104",
                "requested_depth": "standard",
                "operation_mode": "read_only",
                "target_paths": ["docs/surrealdb/"],
                "target_symbols": ["context_briefing_handler"],
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        expected_fields = [
            "briefing_id",
            "scope_summary",
            "context_package_ref",
            "required_reads",
            "relevant_artifacts",
            "relevant_symbols",
            "relevant_docs",
            "relevant_decisions",
            "relevant_evidence",
            "dependency_paths",
            "known_risks",
            "guardrails",
            "stop_conditions",
            "validation_plan",
            "unresolved_questions",
            "human_go_required",
        ]
        for field in expected_fields:
            assert field in b, f"Missing briefing field: {field}"

    def test_depth_quick_returns_minimal(self) -> None:
        """Quick depth returns minimal briefing (no package artifacts)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-quick",
                "task_scope": "Quick briefing test.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert "quick — summary only" in b["scope_summary"].lower()
        assert b["context_package_ref"] is None
        assert b["relevant_artifacts"] == []
        assert b["relevant_symbols"] == []

    def test_depth_standard_returns_artifacts(self) -> None:
        """Standard depth returns relevant artifacts/symbols/docs."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-standard",
                "task_scope": "Standard briefing test.",
                "target_issue": "#2105",
                "requested_depth": "standard",
                "operation_mode": "read_only",
                "target_paths": ["tools/mcp/context_bridge.py"],
                "target_symbols": ["context_briefing_handler"],
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert "standard" in b["scope_summary"].lower()
        assert b["context_package_ref"] is not None  # mocked package ref
        assert len(b["relevant_artifacts"]) >= 1
        assert len(b["relevant_symbols"]) >= 1
        assert len(b["relevant_docs"]) >= 1

    def test_depth_deep_flags_mock_uncertainty(self) -> None:
        """Deep depth flags v0/mock/full-package uncertainty."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-deep",
                "task_scope": "Deep briefing test.",
                "target_issue": "#2105",
                "requested_depth": "deep",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert "deep" in b["scope_summary"].lower()
        assert any(
            "mocked/synthetic" in q.lower() or "mock" in q.lower()
            for q in b["unresolved_questions"]
        ), "Deep depth should flag v0 mock/synthetic uncertainty"

    def test_write_mode_sets_human_go_required_true(self) -> None:
        """Write operation_mode sets human_go_required to True."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-write",
                "task_scope": "Fix a bug in the execution service.",
                "target_issue": "#1983",
                "requested_depth": "standard",
                "operation_mode": "write (code/docs)",
                "target_paths": ["services/execution/"],
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert b["human_go_required"] is True

    def test_read_only_sets_human_go_required_false(self) -> None:
        """read_only operation_mode sets human_go_required to False."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-read",
                "task_scope": "Inspect the execution service.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert b["human_go_required"] is False

    def test_deterministic_briefing_id(self) -> None:
        """Same request produces same briefing_id."""
        bridge = create_bridge()
        inputs = {
            "task_id": "cdb-briefing-det-001",
            "task_scope": "Determinism test.",
            "target_issue": "#2105",
            "requested_depth": "quick",
            "operation_mode": "read_only",
        }
        r1 = bridge.execute_tool("context.briefing", inputs)
        r2 = bridge.execute_tool("context.briefing", inputs)
        assert r1["briefing"]["briefing_id"] == r2["briefing"]["briefing_id"]

    def test_guardrails_contain_boundary_text_and_no_go(self) -> None:
        """Guardrails contain boundary text and NO-GO."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-guard",
                "task_scope": "Guardrail test.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        guardrails = result["briefing"]["guardrails"]
        assert len(guardrails) >= 7
        assert any("not authorisation" in g.lower() for g in guardrails)
        assert any("no-g" in g.lower() for g in guardrails)

    def test_readiness_blocker_reflected(self) -> None:
        """Readiness blocker is reflected in stop_conditions and unresolved_questions."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-blocked",
                "task_scope": "Deploy to production for go-live.",
                "target_issue": "#9999",
                "requested_depth": "standard",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        # Readiness should detect scope drift (live claim)
        stop_conditions = b["stop_conditions"]
        all_text = " ".join(stop_conditions + b["unresolved_questions"])
        assert (
            "blocked" in all_text.lower() or "scope" in all_text.lower()
        ), "Readiness blocker should be reflected in output"

    def test_known_risks_contains_mock_note(self) -> None:
        """Known risks contains note about v0 synthetic/mock inputs."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-risks",
                "task_scope": "Risk note test.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert any(
            "synthetic" in r.lower() or "mock" in r.lower() for r in b["known_risks"]
        ), "Known risks must surface v0 mock note"

    def test_validation_plan_present_for_all_modes(self) -> None:
        """Validation plan is present for all operation modes."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-val",
                "task_scope": "Validation plan test.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        vp = result["briefing"]["validation_plan"]
        assert len(vp) >= 2
        for step in vp:
            assert "step" in step
            assert "method" in step

    def test_missing_target_issue_defaults_to_none(self) -> None:
        """Missing target_issue key now defaults to null/None."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Test scope.",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        assert (
            result["briefing"]["session_context"]["github_state"]["target_issue"]
            is None
        )

    def test_target_issue_null_is_ok(self) -> None:
        """target_issue: null (None) is explicitly allowed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-null",
                "task_scope": "Exploratory research.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"

    def test_missing_requested_depth_defaults_to_quick(self) -> None:
        """Missing requested_depth now defaults to quick."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Test scope.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        explicit_quick = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Test scope.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        assert (
            result["briefing"]["briefing_id"]
            == explicit_quick["briefing"]["briefing_id"]
        )

    def test_missing_operation_mode_returns_error(self) -> None:
        """Missing operation_mode key fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-test",
                "task_scope": "Test scope.",
                "target_issue": None,
                "requested_depth": "quick",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_operation_mode"

    def test_valid_read_only_readiness_not_blocked(self) -> None:
        """Valid read_only request does not get artificial missing-reads blocker."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-valid",
                "task_scope": "Inspect the execution service.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert b["human_go_required"] is False
        assert len(b["required_reads"]) >= 6
        # Must not contain blocked scope or artificial missing reads
        assert (
            "blocked"
            not in b["scope_summary"]
            .lower()
            .split("readiness status: ")[-1]
            .split(".")[0]
        )

    def test_different_target_paths_produce_different_briefing_id(self) -> None:
        """Different target_paths produce different briefing_id."""
        bridge = create_bridge()
        r1 = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-paths",
                "task_scope": "Path test.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "target_paths": ["docs/surrealdb/"],
            },
        )
        r2 = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-paths",
                "task_scope": "Path test.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
                "target_paths": ["tools/mcp/"],
            },
        )
        assert r1["status"] == "ok"
        assert r2["status"] == "ok"
        assert r1["briefing"]["briefing_id"] != r2["briefing"]["briefing_id"]


class TestCdbContextBriefingAlias:
    """Tests for cdb_context_briefing alias tool handler (#2110)."""

    def test_alias_tool_in_list_tools(self) -> None:
        bridge = create_bridge()
        tool_names = [t["name"] for t in bridge.list_tools()]
        assert "cdb_context_briefing" in tool_names

    def test_alias_schema_is_present_and_read_only(self) -> None:
        bridge = create_bridge()
        schema = bridge.get_tool_schema("cdb_context_briefing")
        assert schema is not None
        assert schema["readOnly"] is True

    def test_quick_standard_deep_execute_via_alias(self) -> None:
        bridge = create_bridge()
        base = {
            "task_id": "cdb-briefing-2110-alias",
            "task_scope": "Implement context briefing MCP tool alias wrapper.",
            "target_issue": "#2110",
            "operation_mode": "read_only",
        }
        for depth in ("quick", "standard", "deep"):
            result = bridge.execute_tool(
                "cdb_context_briefing",
                {**base, "requested_depth": depth},
            )
            assert result["status"] == "ok"
            assert result["tool"] == "cdb_context_briefing"
            briefing = result["briefing"]
            assert "stop_conditions" in briefing
            assert "guardrails" in briefing
            assert "human_go_required" in briefing

    def test_alias_preserves_stop_conditions_guardrails_human_go_visibility(
        self,
    ) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_briefing",
            {
                "task_id": "cdb-briefing-2110-visibility",
                "task_scope": "Scope: read-only; stop if Human-GO required.",
                "target_issue": "#2110",
                "requested_depth": "standard",
                "operation_mode": "write (MCP live)",
                "target_paths": ["tools/mcp/context_bridge.py"],
                "target_symbols": ["cdb_context_briefing_handler"],
            },
        )
        assert result["status"] == "ok"
        assert result["tool"] == "cdb_context_briefing"
        briefing = result["briefing"]
        assert isinstance(briefing["guardrails"], list) and briefing["guardrails"]
        assert isinstance(briefing["stop_conditions"], list)
        assert isinstance(briefing["known_risks"], list)
        assert isinstance(briefing["human_go_required"], bool)

    def test_alias_payload_limit_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_briefing",
            {
                "task_id": "cdb-briefing-2110-too-large",
                "task_scope": "x" * 250_000,
                "target_issue": "#2110",
                "requested_depth": "deep",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "error"
        assert result["tool"] == "cdb_context_briefing"
        assert result["error"]["code"] == "payload_too_large"


class TestContextStopResolverHandler:
    """Tests for context.stop_resolver tool handler (#2107)."""

    def test_tool_in_list_tools(self) -> None:
        """Tool is visible in list_tools()."""
        bridge = create_bridge()
        tool_names = [t["name"] for t in bridge.list_tools()]
        assert "context.stop_resolver" in tool_names

    def test_tool_is_read_only(self) -> None:
        """Tool is read-only."""
        bridge = create_bridge()
        schema = bridge.get_tool_schema("context.stop_resolver")
        assert schema is not None
        assert schema["readOnly"] is True

    def test_missing_stop_conditions_returns_empty(self) -> None:
        """Missing stop_conditions returns empty resolved list."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.stop_resolver", {})
        assert result["status"] == "ok"
        assert result["resolved"] == []

    def test_empty_stop_conditions_returns_empty(self) -> None:
        """Empty stop_conditions returns empty resolved list."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.stop_resolver", {"stop_conditions": []})
        assert result["status"] == "ok"
        assert result["resolved"] == []

    def test_s1_maps_to_scope_drift_risk_blocking(self) -> None:
        """S1 maps to scope_drift_risk with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S1: scope ambiguous"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        r = result["resolved"][0]
        assert r["type"] == "scope_drift_risk"
        assert r["severity"] == "blocking"
        assert r["human_go_required"] is True

    def test_s2_maps_to_missing_context_blocking(self) -> None:
        """S2 maps to missing_context with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S2: no context package and no required reads"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        r = result["resolved"][0]
        assert r["type"] == "missing_context"
        assert r["severity"] == "blocking"

    def test_s3_maps_to_missing_context_blocking(self) -> None:
        """S3 maps to missing_context with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S3: minimum read unavailable: AGENTS.md"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        r = result["resolved"][0]
        assert r["type"] == "missing_context"
        assert r["severity"] == "blocking"

    def test_s4_maps_to_missing_evidence_blocking(self) -> None:
        """S4 maps to missing_evidence with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S4: core assumptions lack evidence"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        r = result["resolved"][0]
        assert r["type"] == "missing_evidence"
        assert r["severity"] == "blocking"

    def test_s5_maps_to_scope_drift_risk_blocking(self) -> None:
        """S5 maps to scope_drift_risk with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S5: scope drift detected"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        r = result["resolved"][0]
        assert r["type"] == "scope_drift_risk"
        assert r["severity"] == "blocking"

    def test_s6_maps_to_write_requires_human_go_blocking(self) -> None:
        """S6 maps to write_requires_human_go with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S6: write without impact report"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        r = result["resolved"][0]
        assert r["type"] == "write_requires_human_go"
        assert r["severity"] == "blocking"

    def test_s7_trading_blocking_for_write(self) -> None:
        """S7 is blocking for write operation_mode."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {
                "stop_conditions": ["S7: trading/risk/execution scope touched"],
                "operation_mode": "write (code/docs)",
            },
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "trading_surface_touched"
        assert r["severity"] == "blocking"

    def test_s7_trading_warning_for_read_only(self) -> None:
        """S7 is warning for read_only operation_mode."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {
                "stop_conditions": ["S7: trading/risk/execution scope touched"],
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "trading_surface_touched"
        assert r["severity"] == "warning"

    def test_s8_maps_to_forbidden_path_blocking(self) -> None:
        """S8 maps to forbidden_path with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S8: live/echtgeld claims outside LR SSOT"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "forbidden_path"
        assert r["severity"] == "blocking"
        assert r["human_go_required"] is True

    def test_s9_maps_to_contradiction_risk_warning(self) -> None:
        """S9 maps to contradiction_risk with warning severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S9: material governance uncertainty"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "contradiction_risk"
        assert r["severity"] == "warning"

    def test_s10_maps_to_stale_context_warning(self) -> None:
        """S10 maps to stale_context with warning severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S10: STOP in control surfaces"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "stale_context"
        assert r["severity"] == "warning"

    def test_h1_maps_to_write_requires_human_go_blocking(self) -> None:
        """H1 maps to write_requires_human_go with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["H1: write action requires explicit Human-GO"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "write_requires_human_go"
        assert r["severity"] == "blocking"
        assert r["human_go_required"] is True

    def test_h2_maps_to_runtime_surface_touched_blocking(self) -> None:
        """H2 maps to runtime_surface_touched with blocking severity."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["H2: runtime or DB mutation requires Human-GO"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "runtime_surface_touched"
        assert r["severity"] == "blocking"

    def test_secrets_keyword_maps_to_secrets_risk_blocking(self) -> None:
        """Condition containing secrets keyword maps to secrets_risk."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["tresor-zone access detected"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "secrets_risk"
        assert r["severity"] == "blocking"
        assert r["human_go_required"] is True

    def test_token_keyword_maps_to_secrets_risk_blocking(self) -> None:
        """Condition containing token keyword maps to secrets_risk."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["GITHUB_TOKEN exposed in logs"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "secrets_risk"
        assert r["severity"] == "blocking"

    def test_live_keyword_maps_to_forbidden_path_blocking(self) -> None:
        """Condition containing live keyword without rule-ref maps to forbidden_path."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["go-live authorization missing"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "forbidden_path"
        assert r["severity"] == "blocking"

    def test_unknown_condition_maps_to_scope_drift_risk_warning(self) -> None:
        """Unknown/unmapped condition maps to scope_drift_risk with warning."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["some unexpected condition"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "scope_drift_risk"
        assert r["severity"] == "warning"

    def test_runtime_keyword_maps_to_runtime_surface_touched(self) -> None:
        """Condition containing runtime keyword without rule-ref maps correctly."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["docker compose service detected"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "runtime_surface_touched"
        assert r["severity"] == "warning"

    def test_non_string_stop_conditions_filtered(self) -> None:
        """Non-string stop conditions are filtered without crash."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": [42, None, "S1: scope ambiguous", True]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1
        assert result["resolved"][0]["type"] == "scope_drift_risk"

    def test_output_contains_all_required_fields(self) -> None:
        """Output dicts contain all five required fields."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["S1: scope ambiguous"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        for field in (
            "type",
            "severity",
            "reason",
            "required_action",
            "human_go_required",
        ):
            assert field in r, f"Missing field: {field}"
        assert r["type"] in {
            "missing_context",
            "missing_evidence",
            "scope_drift_risk",
            "runtime_surface_touched",
            "trading_surface_touched",
            "write_requires_human_go",
            "stale_context",
            "contradiction_risk",
            "forbidden_path",
            "secrets_risk",
        }
        assert r["severity"] in {"info", "warning", "blocking"}
        assert isinstance(r["human_go_required"], bool)

    def test_deterministic_same_input_same_output(self) -> None:
        """Same inputs produce identical resolved output."""
        bridge = create_bridge()
        inputs = {
            "stop_conditions": ["S1: scope ambiguous", "S4: no evidence"],
            "operation_mode": "write (code/docs)",
        }
        r1 = bridge.execute_tool("context.stop_resolver", inputs)
        r2 = bridge.execute_tool("context.stop_resolver", inputs)
        assert r1 == r2

    def test_multiple_conditions_all_resolved(self) -> None:
        """Multiple conditions are all resolved."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {
                "stop_conditions": [
                    "S1: scope ambiguous",
                    "S3: minimum read unavailable: CONTROL_REGISTER.md",
                    "S4: core assumptions lack evidence",
                    "S10: STOP in control surfaces",
                ],
            },
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 4
        types = [r["type"] for r in result["resolved"]]
        assert "scope_drift_risk" in types
        assert "missing_context" in types
        assert "missing_evidence" in types
        assert "stale_context" in types

    def test_whitespace_only_stop_conditions_filtered(self) -> None:
        """Whitespace-only strings in stop_conditions are filtered."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["   ", "\t", "S1: scope ambiguous"]},
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1

    def test_warnings_input_accepted(self) -> None:
        """Warnings parameter is accepted without error."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {
                "stop_conditions": ["S1: scope ambiguous"],
                "warnings": ["artifacts_limit_exceeded", "low confidence"],
            },
        )
        assert result["status"] == "ok"
        assert len(result["resolved"]) == 1

    def test_readiness_result_input_accepted(self) -> None:
        """readiness_result parameter is accepted and conditions extracted."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {
                "stop_conditions": ["S1: scope ambiguous"],
                "readiness_result": {
                    "stop_conditions": [
                        "S7: trading/risk/execution scope touched",
                    ],
                },
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        # S1 + S7 from readiness = 2 resolved
        assert len(result["resolved"]) == 2

    def test_briefing_stop_conditions_remain_string_array(self) -> None:
        """Briefing result stop_conditions is still a flat string[]."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-2107-test",
                "task_scope": "Test briefing stop conditions schema compliance.",
                "target_issue": "#2107",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert "stop_conditions" in b
        assert isinstance(b["stop_conditions"], list)
        for sc in b["stop_conditions"]:
            assert isinstance(
                sc, str
            ), f"stop_conditions must remain string[], got {type(sc).__name__}: {sc!r}"

    def test_resolver_does_not_mutate_input_list(self) -> None:
        """Input stop_conditions list is not mutated by resolve_stop_conditions."""
        from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

        original = ["S1: scope ambiguous", "S4: no evidence"]
        before = list(original)
        resolve_stop_conditions(stop_conditions=original)
        assert original == before, f"Input list was mutated: {before} -> {original}"

    def test_briefing_surfaces_resolver_failure(self) -> None:
        """When the resolver raises, briefing surfaces it in known_risks
        and unresolved_questions."""
        from unittest.mock import patch

        bridge = create_bridge()
        params = {
            "task_id": "cdb-briefing-err-test",
            "task_scope": "Test resolver failure surfacing.",
            "target_issue": None,
            "requested_depth": "quick",
            "operation_mode": "read_only",
        }

        with patch(
            "tools.surrealdb.context_stop_resolver.resolve_stop_conditions",
            side_effect=RuntimeError("mock resolver crash"),
        ):
            result = bridge.execute_tool("context.briefing", params)

        assert result["status"] == "ok"
        b = result["briefing"]
        assert isinstance(b["stop_conditions"], list)
        for sc in b["stop_conditions"]:
            assert isinstance(
                sc, str
            ), f"stop_conditions must remain string[] on failure"
        risk_text = " ".join(b["known_risks"]).lower()
        assert (
            "resolver unavailable" in risk_text
        ), f"known_risks should surface resolver failure, got: {b['known_risks']}"
        unresolved_text = " ".join(b["unresolved_questions"]).lower()
        assert (
            "stop condition resolver failed" in unresolved_text
        ), f"unresolved_questions should surface resolver failure, got: {b['unresolved_questions']}"

    def test_live_substring_no_false_positive_deliverable(self) -> None:
        """'deliverable' does NOT trigger forbidden_path (word-boundary fix)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["deliverable pending review"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert (
            r["type"] != "forbidden_path"
        ), f"deliverable should not trigger forbidden_path, got {r['type']}"

    def test_key_substring_no_false_positive_monkeypatch(self) -> None:
        """'monkeypatch' etc. does NOT trigger secrets_risk (word-boundary fix)."""
        from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

        for text in ("monkeypatch", "keyboard", "key result", "turkey"):
            result = resolve_stop_conditions(stop_conditions=[text])
            for r in result:
                assert (
                    r["type"] != "secrets_risk"
                ), f"{text!r} should not trigger secrets_risk, got {r['type']}"

    def test_standalone_live_still_triggers_forbidden_path(self) -> None:
        """Standalone word 'live' still triggers forbidden_path."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.stop_resolver",
            {"stop_conditions": ["live deployment requested"]},
        )
        assert result["status"] == "ok"
        r = result["resolved"][0]
        assert r["type"] == "forbidden_path"

    def test_api_key_still_triggers_secrets_risk(self) -> None:
        """'api_key' still triggers secrets_risk."""
        from tools.surrealdb.context_stop_resolver import resolve_stop_conditions

        for text in ("api_key found", "private key exposed", "secret_key leaked"):
            result = resolve_stop_conditions(stop_conditions=[text])
            assert len(result) >= 1
            assert (
                result[0]["type"] == "secrets_risk"
            ), f"{text!r} should trigger secrets_risk"


class TestContextRequiredReadsHandler:
    """Tests for context.required_reads tool handler."""

    # --- Failure tests ---

    def test_missing_task_scope_fails_closed(self) -> None:
        """Missing task_scope fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.required_reads", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_scope"

    def test_empty_task_scope_fails_closed(self) -> None:
        """Empty string task_scope fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {"task_scope": "", "target_issue": None, "operation_mode": "read_only"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_scope"

    def test_missing_target_issue_fails_closed(self) -> None:
        """Missing target_issue key fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {"task_scope": "Test scope.", "operation_mode": "read_only"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_target_issue"

    def test_target_issue_null_allowed(self) -> None:
        """target_issue=null is explicitly allowed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test scope.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"

    def test_target_issue_invalid_type_fails_closed(self) -> None:
        """target_issue with invalid type (int) fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test scope.",
                "target_issue": 123,
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_target_issue"

    def test_missing_operation_mode_fails_closed(self) -> None:
        """Missing operation_mode fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {"task_scope": "Test scope.", "target_issue": None},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_operation_mode"

    def test_invalid_operation_mode_fails_closed(self) -> None:
        """Invalid operation_mode fails closed."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test scope.",
                "target_issue": None,
                "operation_mode": "invalid_mode",
            },
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_operation_mode"

    # --- Minimum inputs ---

    def test_minimum_inputs_return_ok(self) -> None:
        """Minimum valid inputs return ok with resolved reads."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test scope.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        assert result["tool"] == "context.required_reads"
        assert "resolved_reads" in result
        assert isinstance(result["resolved_reads"], list)
        assert len(result["resolved_reads"]) >= 6

    def test_baseline_reads_are_must_read(self) -> None:
        """All 6 baseline reads are must_read."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test scope.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        baseline_paths = {
            "AGENTS.md",
            "agents/AGENTS.md",
            "agents/OPEN_CODE_AGENTS.md",
            "docs/runbooks/CONTROL_REGISTER.md",
            "CURRENT_STATUS.md",
            "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
        }
        must_reads = [
            r for r in result["resolved_reads"] if r["priority"] == "must_read"
        ]
        baseline_found = {r["path"] for r in must_reads if r["path"] in baseline_paths}
        for bp in baseline_paths:
            assert bp in baseline_found, f"Baseline read {bp} not found in must_reads"

    # --- Availability ---

    def test_existing_file_available_true(self) -> None:
        """Existing file returns available=true, warning=None."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test scope.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        for read in result["resolved_reads"]:
            if read["path"] == "AGENTS.md":
                assert read["available"] is True, f"AGENTS.md should be available"
                assert read["warning"] is None, f"AGENTS.md should have no warning"
                return
        pytest.fail("AGENTS.md not found in resolved reads")

    def test_missing_file_available_false_with_warning(self) -> None:
        """Missing file returns available=false with a warning string."""
        from tools.surrealdb.context_required_reads import _build_read_entry
        from pathlib import Path

        entry = _build_read_entry(
            path="nonexistent/file_that_does_not_exist.md",
            priority="optional",
            reason="Test missing file.",
            source_ref="#test",
            repo_root=Path(__file__).resolve().parent.parent.parent.parent,
        )
        assert entry["available"] is False
        assert entry["warning"] is not None
        assert isinstance(entry["warning"], str)

    # --- Unsafe paths ---

    def test_absolute_path_blocked(self) -> None:
        """Absolute path is marked available=false with unsafe warning."""
        from tools.surrealdb.context_required_reads import _check_availability

        available, warning = _check_availability("C:\\Windows\\System32")
        assert available is False
        assert warning is not None
        assert "blocked" in warning.lower()

    def test_path_traversal_blocked(self) -> None:
        """Path with .. traversal is marked available=false with unsafe warning."""
        from tools.surrealdb.context_required_reads import _check_availability

        available, warning = _check_availability("../etc/passwd")
        assert available is False
        assert warning is not None
        assert "blocked" in warning.lower() or "unsafe" in warning.lower()

    def test_repo_root_override_affects_availability(self) -> None:
        """repo_root parameter is actually used for availability checks."""
        from tools.surrealdb.context_required_reads import _check_availability
        from pathlib import Path

        real_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        # AGENTS.md should be found under the real repo root
        available, warning = _check_availability("AGENTS.md", repo_root=real_root)
        assert available is True, (
            f"AGENTS.md should exist under real root, got available={available}, "
            f"warning={warning}"
        )

        # Same path under a non-existent root should fail
        fake_root = Path("/nonexistent/repo/root")
        available, warning = _check_availability("AGENTS.md", repo_root=fake_root)
        assert (
            available is False
        ), f"AGENTS.md should NOT exist under fake root, got available={available}"
        assert warning is not None

    # --- Write mode ---

    def test_write_mode_adds_governance_reads(self) -> None:
        """Write operation_mode adds governance/Human-GO relevant reads."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Fix a bug.",
                "target_issue": None,
                "operation_mode": "write (code/docs)",
            },
        )
        assert result["status"] == "ok"
        paths = {r["path"] for r in result["resolved_reads"]}
        # Write mode should add governance-related reads
        assert (
            "knowledge/governance/CDB_AGENT_POLICY.md" in paths
            or len(
                [r for r in result["resolved_reads"] if r["priority"] == "must_read"]
            )
            > 6
        ), "Write mode should add extra must_read entries"

    def test_read_only_mode_does_not_add_write_reads(self) -> None:
        """read_only mode doesn't add write-mode governance reads."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Inspect code.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        # DELIVERY_APPROVED.yaml is only added for write modes
        delivery_entries = [
            r
            for r in result["resolved_reads"]
            if r["path"] == "knowledge/governance/DELIVERY_APPROVED.yaml"
            and r["priority"] == "must_read"
        ]
        assert (
            len(delivery_entries) == 0
        ), "DELIVERY_APPROVED.yaml must_read should not appear in read_only mode"

    # --- Domain scope ---

    def test_surrealdb_scope_adds_context_docs(self) -> None:
        """SurrealDB scope/path adds context docs."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Implement SurrealDB context intelligence feature.",
                "target_issue": "#2106",
                "operation_mode": "read_only",
                "target_paths": ["tools/surrealdb/context_required_reads.py"],
            },
        )
        assert result["status"] == "ok"
        paths = {r["path"] for r in result["resolved_reads"]}
        assert (
            "docs/surrealdb/context-package-model-v1.md" in paths
        ), "SurrealDB scope should add context package model doc"

    def test_ci_domain_reads_point_to_files(self) -> None:
        """CI domain reads resolve to concrete files, not directories."""
        from tools.surrealdb.context_required_reads import (
            DOMAIN_READS,
            _check_availability,
        )

        ci_reads = DOMAIN_READS.get("ci", [])
        assert len(ci_reads) > 0, "CI domain must have reads"
        for read in ci_reads:
            path = read["path"]
            assert not path.endswith(
                "/"
            ), f"CI read path must be a file, not directory: {path!r}"
            available, warning = _check_availability(path)
            assert (
                available is True
            ), f"CI read {path!r} should be available, got warning={warning!r}"

    # --- Symbols do not invent file paths ---

    def test_target_symbols_do_not_invent_file_paths(self) -> None:
        """Target symbols produce entry with available=false, not fake paths."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Refactor handler.",
                "target_issue": None,
                "operation_mode": "read_only",
                "target_symbols": [
                    "context_briefing_handler",
                    "resolve_required_reads",
                ],
            },
        )
        assert result["status"] == "ok"
        for read in result["resolved_reads"]:
            if read["source_ref"] == "target_symbols":
                assert (
                    read["available"] is False
                ), f"Symbol entry should have available=false: {read}"
                assert (
                    read["warning"] is not None
                ), f"Symbol entry should have warning: {read}"
                return
        pytest.fail("No target_symbols entry found in resolved reads")

    # --- Determinism ---

    def test_deterministic_same_input_same_output(self) -> None:
        """Same inputs produce identical outputs."""
        bridge = create_bridge()
        inputs = {
            "task_scope": "Test determinism.",
            "target_issue": "#2106",
            "operation_mode": "read_only",
            "target_paths": ["tools/surrealdb/"],
            "target_symbols": ["resolve_required_reads"],
        }
        r1 = bridge.execute_tool("context.required_reads", inputs)
        r2 = bridge.execute_tool("context.required_reads", inputs)
        assert r1 == r2, "Same inputs should produce identical outputs"

    # --- Contract fields ---

    def test_all_reads_have_required_fields(self) -> None:
        """Every resolved read has all 6 required fields."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test contract fields.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        required_fields = {
            "path",
            "priority",
            "reason",
            "source_ref",
            "available",
            "warning",
        }
        for read in result["resolved_reads"]:
            for field in required_fields:
                assert field in read, f"Read missing field {field}: {read}"

    def test_priority_values_are_valid(self) -> None:
        """All priorities are valid enum values."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.required_reads",
            {
                "task_scope": "Test priorities.",
                "target_issue": None,
                "operation_mode": "read_only",
            },
        )
        valid_priorities = {"must_read", "should_read", "optional"}
        for read in result["resolved_reads"]:
            assert (
                read["priority"] in valid_priorities
            ), f"Invalid priority {read['priority']!r} in {read['path']}"

    # --- Schema compatibility ---

    def test_briefing_required_reads_stay_string_list(self) -> None:
        """Briefing output required_reads remains string[] (schema-compatible)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "cdb-briefing-schema-test",
                "task_scope": "Test schema compatibility.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"
        b = result["briefing"]
        assert "required_reads" in b
        assert isinstance(b["required_reads"], list)
        for item in b["required_reads"]:
            assert isinstance(
                item, str
            ), f"required_reads must remain string[], got {type(item).__name__}: {item!r}"

    # --- Tool registration ---

    def test_tool_appears_in_list_tools(self) -> None:
        """context.required_reads appears in list_tools output."""
        bridge = create_bridge()
        tools = bridge.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "context.required_reads" in tool_names

    def test_tool_is_read_only(self) -> None:
        """context.required_reads is marked readOnly."""
        bridge = create_bridge()
        tools = bridge.list_tools()
        for t in tools:
            if t["name"] == "context.required_reads":
                assert t["readOnly"] is True
                return
        pytest.fail("context.required_reads not found in tool list")

    # --- Operation modes ---

    def test_all_valid_operation_modes_accepted(self) -> None:
        """All 6 valid operation_mode values are accepted."""
        bridge = create_bridge()
        valid_modes = [
            "read_only",
            "dry_run",
            "write (code/docs)",
            "write (config/infra)",
            "write (DB/migration)",
            "write (MCP live)",
        ]
        for mode in valid_modes:
            result = bridge.execute_tool(
                "context.required_reads",
                {"task_scope": "Test.", "target_issue": None, "operation_mode": mode},
            )
            assert (
                result["status"] == "ok"
            ), f"Valid mode {mode!r} should be accepted, got {result}"


class TestCdbContextImpactHandler:
    """Tests for cdb_context_impact tool handler (#2111)."""

    def test_tool_in_list_tools(self) -> None:
        bridge = create_bridge()
        tool_names = [t["name"] for t in bridge.list_tools()]
        assert "cdb_context_impact" in tool_names

    def test_tool_is_read_only(self) -> None:
        bridge = create_bridge()
        schema = bridge.get_tool_schema("cdb_context_impact")
        assert schema is not None
        assert schema["readOnly"] is True

    def test_schema_has_required_fields(self) -> None:
        bridge = create_bridge()
        schema = bridge.get_tool_schema("cdb_context_impact")
        props = schema["inputSchema"]["properties"]
        assert "target_paths" in props
        assert "target_symbols" in props
        assert "target_issue" in props
        assert "operation_mode" in props

    def test_empty_call_returns_ok(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("cdb_context_impact", {})
        assert result["status"] == "ok"
        assert result["tool"] == "cdb_context_impact"
        assert "impact" in result

    def test_output_contains_all_required_impact_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["docs/surrealdb/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        impact = result["impact"]
        required_fields = [
            "impact_id",
            "impact_level",
            "impact_type",
            "gate_risks",
            "stop_conditions",
            "required_validation",
        ]
        for field in required_fields:
            assert field in impact, f"Missing impact field: {field}"

    def test_output_contains_guardrails(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("cdb_context_impact", {})
        assert result["status"] == "ok"
        guardrails = result["guardrails"]
        assert len(guardrails) >= 1
        assert any("not authorization" in g.lower() for g in guardrails)
        assert any("no-g" in g.lower() for g in guardrails)

    def test_low_impact_case(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["docs/readme.md"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        assert result["impact"]["impact_level"] == "low"

    def test_medium_impact_case(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["tools/mcp/context_bridge.py"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        assert result["impact"]["impact_level"] == "medium"

    def test_high_impact_case(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["infrastructure/compose/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        assert result["impact"]["impact_level"] == "high"

    def test_blocking_impact_case(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {
                "target_paths": ["knowledge/governance/CDB_CONSTITUTION.md"],
                "target_issue": "#2111",
            },
        )
        assert result["status"] == "ok"
        assert result["impact"]["impact_level"] == "blocking"

    def test_gate_risks_visible_for_blocking(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["knowledge/governance/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        gate_risks = result["impact"]["gate_risks"]
        assert isinstance(gate_risks, list)
        assert len(gate_risks) >= 1
        assert "governance_touched" in gate_risks

    def test_gate_risks_visible_for_risk_surface(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["services/risk/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        gate_risks = result["impact"]["gate_risks"]
        assert "risk_surface_touched" in gate_risks

    def test_stop_conditions_visible(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["knowledge/governance/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        stop_conditions = result["impact"]["stop_conditions"]
        assert isinstance(stop_conditions, list)
        assert len(stop_conditions) >= 1

    def test_required_validation_visible(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["tools/mcp/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        rv = result["impact"]["required_validation"]
        assert isinstance(rv, dict)
        assert "docs_to_review" in rv
        assert "suggested_tests" in rv
        assert "commands_to_consider" in rv

    def test_graph_paths_present(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["tools/mcp/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        assert "graph_paths" in result["impact"]
        assert isinstance(result["impact"]["graph_paths"], list)

    def test_no_authorization_given(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["docs/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        impact = result["impact"]
        assert "approved" not in impact
        assert "authorized" not in str(impact).lower()
        guardrails = result["guardrails"]
        assert any("no live" in g.lower() or "no-g" in g.lower() for g in guardrails)

    def test_write_mode_triggers_write_stop_condition(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {
                "target_paths": ["docs/"],
                "target_issue": "#2111",
                "operation_mode": "write (code/docs)",
            },
        )
        assert result["status"] == "ok"
        stop_text = " ".join(str(sc) for sc in result["impact"]["stop_conditions"])
        assert "write" in stop_text.lower() or "human-go" in stop_text.lower()

    def test_deterministic_same_input_same_output(self) -> None:
        bridge = create_bridge()
        inputs = {
            "target_paths": ["tools/mcp/"],
            "target_issue": "#2111",
            "operation_mode": "read_only",
        }
        r1 = bridge.execute_tool("cdb_context_impact", inputs)
        r2 = bridge.execute_tool("cdb_context_impact", inputs)
        assert r1 == r2

    def test_schema_version_present(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("cdb_context_impact", {})
        assert result["status"] == "ok"
        assert result["impact"]["schema_version"] == "1.0.0"

    def test_impact_id_is_deterministic_string(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["docs/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        impact_id = result["impact"]["impact_id"]
        assert isinstance(impact_id, str)
        assert len(impact_id) == 16

    def test_confidence_is_valid_enum(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("cdb_context_impact", {})
        assert result["status"] == "ok"
        assert result["impact"]["confidence"] in ("low", "medium", "high")

    def test_impact_type_is_valid_enum(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("cdb_context_impact", {})
        assert result["status"] == "ok"
        assert result["impact"]["impact_type"] in ("HARD", "SOFT")

    def test_affected_lists_are_arrays(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["tools/mcp/"], "target_issue": "#2111"},
        )
        assert result["status"] == "ok"
        impact = result["impact"]
        assert isinstance(impact["affected_artifacts"], list)
        assert isinstance(impact["affected_symbols"], list)
        assert isinstance(impact["affected_tests"], list)
        assert isinstance(impact["affected_docs"], list)
        assert isinstance(impact["affected_decisions"], list)
        assert isinstance(impact["affected_evidence"], list)
        assert isinstance(impact["affected_memory_refs_read_only"], list)

    def test_invalid_operation_mode_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_impact",
            {"target_paths": ["docs/"], "operation_mode": "write"},
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_operation_mode"
        assert "write" in result["error"]["message"]


class TestWave14BridgeDispatch:
    """Prove that Wave-14 tools dispatch to real handlers, not registry stubs.

    Each test calls bridge.execute_tool() and asserts:
    - error code is NOT 'not_implemented' (real handler reached)
    - metadata.read_only is True (handler enforces read-only contract)

    Tests use create_bridge() so the Wave-14 handler replacement loop in
    ContextBridge.__init__() is exercised end-to-end.
    """

    _WAVE14_TOOLS = [
        "cdb_context_evidence_resolve",
        "cdb_context_claim_resolve",
        "cdb_context_memory_get",
        "cdb_context_trust_summary",
        "cdb_context_decision_history",
        "cdb_context_decision_replay",
    ]

    @pytest.mark.parametrize("tool_name", _WAVE14_TOOLS)
    def test_dispatch_reaches_real_handler(self, tool_name: str) -> None:
        """Tool must not return not_implemented."""
        bridge = create_bridge()
        result = bridge.execute_tool(tool_name, {})
        error_code = result.get("error", {}).get("code")
        assert (
            error_code != "not_implemented"
        ), f"{tool_name} returned not_implemented — registry stub not replaced"

    @pytest.mark.parametrize("tool_name", _WAVE14_TOOLS)
    def test_metadata_read_only_true(self, tool_name: str) -> None:
        """Handler must return metadata.read_only == True."""
        bridge = create_bridge()
        result = bridge.execute_tool(tool_name, {})
        metadata = result.get("metadata", {})
        assert (
            metadata.get("read_only") is True
        ), f"{tool_name} missing metadata.read_only=True in result: {result}"

    def test_evidence_resolve_with_records(self) -> None:
        """evidence_resolve accepts inline records (noop/in-memory path)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_evidence_resolve",
            {
                "evidence_records": [
                    {"id": "ev_test_1", "claim_id": "c1", "source": "unit_test"}
                ]
            },
        )
        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True

    def test_claim_resolve_with_records(self) -> None:
        """claim_resolve accepts inline records (noop/in-memory path)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_claim_resolve",
            {"claim_records": [{"id": "c1", "text": "Test claim", "status": "open"}]},
        )
        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True

    def test_memory_get_with_records(self) -> None:
        """memory_get accepts inline records (noop/in-memory path)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_memory_get",
            {
                "memory_records": [
                    {"id": "m1", "agent": "test_agent", "content": "test"}
                ]
            },
        )
        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True

    def test_trust_summary_with_scope(self) -> None:
        """trust_summary accepts a scope parameter."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_trust_summary",
            {"scope": "test_scope"},
        )
        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True

    def test_decision_history_with_events(self) -> None:
        """decision_history accepts inline events (noop/in-memory path)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_decision_history",
            {
                "decision_events": [
                    {"id": "de1", "type": "gate_decision", "outcome": "pass"}
                ]
            },
        )
        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True

    def test_decision_replay_with_events(self) -> None:
        """decision_replay accepts inline events (noop/in-memory path)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_decision_replay",
            {
                "decision_id": "de1",
                "decision_events": [
                    {"id": "de1", "type": "gate_decision", "outcome": "pass"}
                ],
            },
        )
        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True

    def test_unknown_tool_is_distinct_from_not_implemented(self) -> None:
        """unknown_tool error is different from not_implemented."""
        bridge = create_bridge()
        result = bridge.execute_tool("cdb_context_nonexistent_tool", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "unknown_tool"
        assert result["error"]["code"] != "not_implemented"

    @staticmethod
    def _minimal_payload(tool_name: str) -> dict[str, Any]:
        if tool_name == "cdb_context_evidence_resolve":
            return {
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
                "evidence_records": [
                    {
                        "evidence_id": "ev_test_1",
                        "evidence_type": "test_run",
                        "confidence": 0.8,
                        "artifact_refs": ["tools/surrealdb/evidence_lookup.py"],
                        "claim_refs": [],
                        "decision_refs": [],
                    }
                ],
            }
        if tool_name == "cdb_context_claim_resolve":
            return {
                "mode": "by_topic",
                "topic": "context_tools",
                "claim_records": [
                    {
                        "claim_id": "claim_test_1",
                        "title": "Test claim",
                        "statement": "read-only claim",
                        "status": "supported",
                        "scope": "wave14",
                        "topic": "context_tools",
                        "evidence_refs": [],
                    }
                ],
            }
        if tool_name == "cdb_context_memory_get":
            return {
                "mode": "by_scope",
                "scope": "wave14",
                "memory_records": [
                    {
                        "memory_id": "mem_test_1",
                        "scope": "wave14",
                        "memory_type": "constraint",
                        "content": "read-only memory",
                        "agent": "bridge-test",
                    }
                ],
            }
        if tool_name == "cdb_context_trust_summary":
            return {"scope": "wave14"}
        if tool_name == "cdb_context_decision_history":
            return {
                "mode": "by_topic",
                "topic": "context_tools",
                "decision_events": [
                    {
                        "decision_id": "dec_test_1",
                        "title": "Decision",
                        "topic": "context_tools",
                        "scope": "wave14",
                        "status": "approved",
                    }
                ],
            }
        if tool_name == "cdb_context_decision_replay":
            return {
                "mode": "replay_by_scope",
                "scope": "wave14",
                "decision_events": [
                    {
                        "decision_id": "dec_test_1",
                        "title": "Decision",
                        "topic": "context_tools",
                        "scope": "wave14",
                        "status": "approved",
                    }
                ],
            }
        raise AssertionError(f"Unhandled Wave-14 tool: {tool_name}")

    @pytest.mark.parametrize("tool_name", _WAVE14_TOOLS)
    def test_forged_db_claim_fields_do_not_change_in_memory_source(
        self, tool_name: str
    ) -> None:
        """Bridge-level dispatch must not let caller fields fake DB-backed mode."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            tool_name,
            {
                **self._minimal_payload(tool_name),
                "source": "surrealdb-local",
                "brain_source": "surrealdb-local",
                "brain_status": "used",
                "metadata": {"source": "surrealdb-local"},
            },
        )

        assert result.get("error", {}).get("code") != "not_implemented"
        assert result.get("metadata", {}).get("read_only") is True
        assert result.get("metadata", {}).get("source") == "in_memory"
