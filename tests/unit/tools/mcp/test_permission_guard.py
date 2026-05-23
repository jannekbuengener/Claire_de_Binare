"""
Tests for Read-only Permission Guardrails (#2099).

Three-layer defense-in-depth:
1. Registry Gate: non-read-only ToolDefinitions are blocked.
2. Execute Gate: read_only check + input scan before handler dispatch.
3. Input Gate: mutative query/operation patterns in tool parameters are blocked.

Input scanning applies to query/command tools (context.search, context.trace,
context.explain_source, context.package, context.show_snapshot, context.show_audit).
Structural tools (context.readiness, context.briefing, context.self_explain,
context.stop_resolver, context.required_reads) are exempt because their
handlers validate inputs with operation_mode enums and structural checks.

Reference: Issue #2099
"""

import pytest

from tools.mcp.context_bridge import ContextBridge, create_bridge
from tools.mcp.permission_guard import (
    FORBIDDEN_RUNTIME_OPERATIONS,
    FORBIDDEN_SQL_KEYWORDS,
    INPUT_SCAN_EXEMPT_TOOLS,
    INPUT_SCAN_TOOLS,
    PermissionCheckResult,
    PermissionGuard,
)
from tools.mcp.registry import ContextToolRegistry, ToolDefinition

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Registry Gate
# ---------------------------------------------------------------------------


class TestRegistryGate:
    """Registry blocks non-read-only tools and asserts consistency."""

    def test_register_rejects_non_read_only_tool(self) -> None:
        """register() raises ValueError for non-read-only tool."""
        tool = ToolDefinition(
            name="context.write_mutate",
            description="Forbidden write tool",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            read_only=False,
        )
        with pytest.raises(ValueError, match="Cannot register non-read-only tool"):
            ContextToolRegistry.register(tool)

    def test_register_accepts_read_only_tool(self) -> None:
        """register() accepts read-only tool (does not raise)."""
        existing_names = set(ContextToolRegistry.list_tool_names())
        name = "__test_permission_readonly__"
        if name not in existing_names:
            tool = ToolDefinition(
                name=name,
                description="Test read-only tool",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                read_only=True,
            )
            ContextToolRegistry.register(tool)
            assert ContextToolRegistry.get_tool(name) is not None
            del ContextToolRegistry._tools[name]

    def test_assert_read_only_consistency_passes_when_all_read_only(self) -> None:
        """assert_read_only_consistency succeeds when all tools are read-only."""
        ContextToolRegistry.assert_read_only_consistency()

    def test_assert_read_only_consistency_fails_when_write_tool_injected(self) -> None:
        """assert_read_only_consistency raises if a non-read-only tool bypasses register()."""
        name = "__test_bypass_injection__"
        tool = ToolDefinition(
            name=name,
            description="Injected write tool",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            read_only=False,
        )
        ContextToolRegistry._tools[name] = tool
        with pytest.raises(ValueError, match="Registry consistency violation"):
            ContextToolRegistry.assert_read_only_consistency()
        del ContextToolRegistry._tools[name]


class TestBridgeInitConsistency:
    """ContextBridge.__init__() asserts registry consistency after replacements."""

    def test_bridge_init_asserts_read_only_consistency(self) -> None:
        """Bridge creation runs assert_read_only_consistency without error."""
        bridge = ContextBridge()
        status = bridge.get_read_only_status()
        assert status["enforced"] is True
        assert all(t.read_only for t in ContextToolRegistry.list_tools())


# ---------------------------------------------------------------------------
# 2. Execute Gate
# ---------------------------------------------------------------------------


class TestExecuteGate:
    """Execute gate rejects non-read-only tools and forbidden input patterns."""

    def test_execute_unknown_tool_returns_error(self) -> None:
        """Unknown tool returns error with code unknown_tool."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.nonexistent", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "unknown_tool"

    def test_execute_not_implemented_tool_returns_error(self) -> None:
        """Stub tool returns not_implemented error."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {"entity_id": "test"})
        assert result["status"] == "error"
        assert result["error"]["code"] == "not_implemented"

    def test_execute_search_with_forbidden_keyword_blocked(self) -> None:
        """context.search with INSERT in query is blocked by input gate."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "INSERT INTO table_x"})
        assert result["status"] == "error"
        assert result["error"]["code"] in (
            "forbidden_keyword",
            "forbidden_query_pattern",
        )

    def test_execute_search_with_forbidden_runtime_operation_blocked(self) -> None:
        """context.search with git_push in query is blocked."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search", {"query": "run git_push to remote"}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "forbidden_runtime_operation"

    def test_execute_search_with_forbidden_repo_pattern_blocked(self) -> None:
        """context.search with 'git push' pattern is blocked."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search", {"query": "run git push origin main"}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] in (
            "forbidden_keyword",
            "forbidden_query_pattern",
            "forbidden_runtime_operation",
            "forbidden_repo_pattern",
        )

    def test_execute_search_with_allowed_query_passes(self) -> None:
        """Normal read-only query passes the input gate."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search", {"query": "find decisions about risk limits"}
        )
        assert result["status"] == "ok"

    def test_execute_search_with_deploy_keyword_blocked(self) -> None:
        """context.search with 'deploy' in query is blocked (query tool)."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "deploy the service"})
        assert result["status"] == "error"
        assert result["error"]["code"] == "forbidden_runtime_operation"

    def test_execute_readiness_with_deploy_keyword_passes(self) -> None:
        """context.readiness with 'Deploy' in task_scope passes (exempt tool)."""
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
        assert result["status"] == "ok"
        assert result["readiness"]["status"] == "blocked_scope_drift"

    def test_execute_readiness_with_write_operation_mode_passes(self) -> None:
        """context.readiness with 'write (code/docs)' passes (exempt tool)."""
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
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# 3. Input Gate — Tool Classification
# ---------------------------------------------------------------------------


class TestInputGateToolClassification:
    """Input gate applies scanning only to query/command tools."""

    def test_scan_tools_include_query_tools(self) -> None:
        """Query/command tools are in INPUT_SCAN_TOOLS."""
        assert "context.search" in INPUT_SCAN_TOOLS
        assert "context.trace" in INPUT_SCAN_TOOLS
        assert "context.explain_source" in INPUT_SCAN_TOOLS
        assert "context.package" in INPUT_SCAN_TOOLS

    def test_exempt_tools_include_structural_tools(self) -> None:
        """Structural tools are in INPUT_SCAN_EXEMPT_TOOLS."""
        assert "context.readiness" in INPUT_SCAN_EXEMPT_TOOLS
        assert "context.briefing" in INPUT_SCAN_EXEMPT_TOOLS
        assert "cdb_context_briefing" in INPUT_SCAN_EXEMPT_TOOLS
        assert "context.self_explain" in INPUT_SCAN_EXEMPT_TOOLS
        assert "context.stop_resolver" in INPUT_SCAN_EXEMPT_TOOLS
        assert "context.required_reads" in INPUT_SCAN_EXEMPT_TOOLS

    def test_scan_and_exempt_are_disjoint(self) -> None:
        """No tool is in both INPUT_SCAN_TOOLS and INPUT_SCAN_EXEMPT_TOOLS."""
        overlap = INPUT_SCAN_TOOLS & INPUT_SCAN_EXEMPT_TOOLS
        assert len(overlap) == 0

    def test_exempt_tool_returns_empty_violations(self) -> None:
        """Structural tools always return empty violations regardless of input."""
        results = PermissionGuard.check_tool_inputs(
            "context.readiness",
            {"task_scope": "Deploy system to production for go-live."},
        )
        assert len(results) == 0

    def test_briefing_exempt_tool_returns_empty_violations(self) -> None:
        """context.briefing is exempt from input scanning."""
        results = PermissionGuard.check_tool_inputs(
            "context.briefing",
            {"task_scope": "Update config infrastructure"},
        )
        assert len(results) == 0

    def test_cdb_context_briefing_exempt_tool_returns_empty_violations(self) -> None:
        """cdb_context_briefing is exempt from input scanning (alias)."""
        results = PermissionGuard.check_tool_inputs(
            "cdb_context_briefing",
            {
                "task_scope": (
                    "Plan: write (code/docs) only with Human-GO; "
                    "no docker compose up; no DB writes."
                )
            },
        )
        assert len(results) == 0

    def test_scan_tool_with_forbidden_keyword_returns_violation(self) -> None:
        """Query tools with forbidden keywords return violations."""
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "INSERT INTO context"}
        )
        assert len(results) >= 1


_WAVE14_EXEMPT_TOOLS = [
    "cdb_context_evidence_resolve",
    "cdb_context_claim_resolve",
    "cdb_context_memory_get",
    "cdb_context_trust_summary",
    "cdb_context_decision_history",
    "cdb_context_decision_replay",
]


class TestInputGateWave14Exemption:
    """Wave-14 record context tools are exempt from mutation keyword scanning."""

    def test_all_wave14_tools_in_exempt_set(self) -> None:
        """All 6 Wave-14 tool names are in INPUT_SCAN_EXEMPT_TOOLS."""
        missing = [t for t in _WAVE14_EXEMPT_TOOLS if t not in INPUT_SCAN_EXEMPT_TOOLS]
        assert not missing, f"Wave-14 tools missing from exempt set: {missing}"

    def test_wave14_tools_not_in_scan_set(self) -> None:
        """No Wave-14 tool is in INPUT_SCAN_TOOLS (disjoint check)."""
        overlap = [t for t in _WAVE14_EXEMPT_TOOLS if t in INPUT_SCAN_TOOLS]
        assert not overlap, f"Wave-14 tools must not be in INPUT_SCAN_TOOLS: {overlap}"

    @pytest.mark.parametrize("tool_name", _WAVE14_EXEMPT_TOOLS)
    def test_wave14_tool_allows_mutation_keywords_in_title(
        self, tool_name: str
    ) -> None:
        """Wave-14 tools must not be blocked when record titles contain create/update/delete."""
        results = PermissionGuard.check_tool_inputs(
            tool_name,
            {
                "evidence_records": [
                    {"evidence_id": "ev-1", "title": "Create migration evidence"},
                    {"evidence_id": "ev-2", "title": "Update runbook decision"},
                    {
                        "evidence_id": "ev-3",
                        "title": "Delete branch warning in historical note",
                    },
                ]
            },
        )
        assert len(results) == 0, (
            f"Tool {tool_name} must not block records with mutation keywords in titles, "
            f"got violations: {results}"
        )

    def test_wave14_evidence_resolve_mutation_claim_passes(self) -> None:
        """cdb_context_evidence_resolve passes claims containing decision keywords."""
        results = PermissionGuard.check_tool_inputs(
            "cdb_context_evidence_resolve",
            {"claim": "Drop deprecated migration schema", "mode": "by_claim"},
        )
        assert len(results) == 0

    def test_wave14_decision_history_mutation_scope_passes(self) -> None:
        """cdb_context_decision_history passes scope strings with mutation words."""
        results = PermissionGuard.check_tool_inputs(
            "cdb_context_decision_history",
            {"scope": "create-or-update-runbook", "mode": "by_scope"},
        )
        assert len(results) == 0

    def test_non_exempt_tool_still_blocked(self) -> None:
        """context.search (non-exempt) is still blocked by mutation keywords."""
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "DROP TABLE evidence"}
        )
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# 4. Input Gate — Forbidden Keywords
# ---------------------------------------------------------------------------


class TestInputGateForbiddenKeywords:
    """Input gate detects forbidden SQL/mutation keywords in query tools."""

    @pytest.mark.parametrize("keyword", sorted(FORBIDDEN_SQL_KEYWORDS))
    def test_forbidden_keyword_detected_standalone(self, keyword: str) -> None:
        """Each forbidden keyword in a parameter triggers a result."""
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": f"{keyword} something"}
        )
        assert len(results) >= 1
        assert results[0].code == "forbidden_keyword"

    def test_forbidden_keyword_case_insensitive(self) -> None:
        """Keywords are detected regardless of case."""
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "insert INTO table_x"}
        )
        assert len(results) >= 1
        assert any(r.code == "forbidden_keyword" for r in results)

    def test_forbidden_keyword_in_nested_parameter(self) -> None:
        """Keywords in nested dict parameters are detected in query tools."""
        results = PermissionGuard.check_tool_inputs(
            "context.search",
            {
                "filters": {
                    "source_types": ["decision"],
                    "date_from": "DELETE FROM logs",
                }
            },
        )
        assert len(results) >= 1
        assert results[0].code == "forbidden_keyword"

    def test_forbidden_keyword_in_list_parameter(self) -> None:
        """Keywords in list parameters are detected in query tools."""
        results = PermissionGuard.check_tool_inputs(
            "context.package",
            {"artifacts": ["DROP TABLE decisions"]},
        )
        assert len(results) >= 1

    def test_normal_readonly_query_no_violation(self) -> None:
        """Normal read-only queries produce no violations."""
        results = PermissionGuard.check_tool_inputs(
            "context.search",
            {"query": "find decisions about risk limits"},
        )
        assert len(results) == 0

    def test_empty_parameters_no_violation(self) -> None:
        """Empty parameters produce no violations."""
        results = PermissionGuard.check_tool_inputs("context.search", {})
        assert len(results) == 0

    def test_word_boundary_prevents_false_positive(self) -> None:
        """Substring matches within words are not flagged (word-boundary check)."""
        results = PermissionGuard.check_tool_inputs(
            "context.search",
            {"query": "understanding the architecture"},
        )
        assert all(r.code != "forbidden_keyword" for r in results)


# ---------------------------------------------------------------------------
# 5. Input Gate — Forbidden Query Patterns
# ---------------------------------------------------------------------------


class TestInputGateForbiddenQueryPatterns:
    """Input gate detects forbidden SurrealQL/SQL mutation patterns."""

    def test_insert_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "INSERT INTO decisions"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_update_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "UPDATE decisions SET status='blocked'"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_delete_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "DELETE FROM context WHERE id=1"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_create_table_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "CREATE TABLE new_entity"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_drop_table_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "DROP TABLE decisions"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_merge_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "MERGE INTO context"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_define_table_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "DEFINE TABLE context_entry"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)

    def test_remove_table_pattern_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "REMOVE TABLE old_entry"}
        )
        assert any(r.code == "forbidden_query_pattern" for r in results)


# ---------------------------------------------------------------------------
# 6. Input Gate — Forbidden Runtime/Repo Operations (query tools only)
# ---------------------------------------------------------------------------


class TestInputGateForbiddenRuntimeOperations:
    """Input gate detects forbidden runtime/GitHub/repo operations in query tools."""

    @pytest.mark.parametrize("op", sorted(FORBIDDEN_RUNTIME_OPERATIONS))
    def test_forbidden_runtime_operation_detected(self, op: str) -> None:
        """Each forbidden runtime operation in a query tool parameter is detected."""
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": f"perform {op} on target"}
        )
        assert len(results) >= 1
        assert any(r.code == "forbidden_runtime_operation" for r in results)

    def test_git_commit_detected_in_query_tool(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "run git_commit to save changes"}
        )
        assert any(r.code == "forbidden_runtime_operation" for r in results)

    def test_docker_build_detected_in_query_tool(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "run docker_build for deployment"}
        )
        assert any(r.code == "forbidden_runtime_operation" for r in results)

    def test_repo_pattern_git_push_detected_in_query_tool(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "then git push origin main"}
        )
        assert any(r.code == "forbidden_repo_pattern" for r in results)

    def test_repo_pattern_gh_issue_create_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "then gh issue create for tracking"}
        )
        assert len(results) >= 1

    def test_repo_pattern_docker_compose_up_detected(self) -> None:
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "then docker compose up -d"}
        )
        assert any(r.code == "forbidden_repo_pattern" for r in results)

    def test_runtime_operation_not_detected_in_exempt_tool(self) -> None:
        """Runtime operations are not flagged in exempt structural tools."""
        results = PermissionGuard.check_tool_inputs(
            "context.readiness",
            {"task_scope": "Deploy system to production"},
        )
        assert len(results) == 0

    def test_deploy_not_flagged_in_briefing_task_scope(self) -> None:
        """'deploy' in briefing task_scope is not flagged (exempt tool)."""
        results = PermissionGuard.check_tool_inputs(
            "context.briefing",
            {"task_scope": "Deploy the service"},
        )
        assert len(results) == 0


# ---------------------------------------------------------------------------
# 7. Tool Definition Check
# ---------------------------------------------------------------------------


class TestToolDefinitionCheck:
    """check_tool_definition rejects non-read-only tools."""

    def test_read_only_tool_passes(self) -> None:
        result = PermissionGuard.check_tool_definition("context.search", read_only=True)
        assert result is None

    def test_non_read_only_tool_blocked(self) -> None:
        result = PermissionGuard.check_tool_definition(
            "context.write_mutate", read_only=False
        )
        assert result is not None
        assert result.code == "non_read_only_tool"
        assert "context.write_mutate" in result.message
        assert result.details["read_only"] is False


# ---------------------------------------------------------------------------
# 8. Registry Consistency Check
# ---------------------------------------------------------------------------


class TestRegistryConsistencyCheck:
    """check_registry_consistency detects non-read-only tools in the registry."""

    def test_all_read_only_registry_passes(self) -> None:
        result = PermissionGuard.check_registry_consistency(ContextToolRegistry._tools)
        assert result is None

    def test_registry_with_write_tool_fails(self) -> None:
        fake_tools: dict[str, ToolDefinition] = {
            "context.write_bad": ToolDefinition(
                name="context.write_bad",
                description="Bad write tool",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                read_only=False,
            ),
        }
        result = PermissionGuard.check_registry_consistency(fake_tools)
        assert result is not None
        assert result.code == "registry_inconsistency"
        assert "context.write_bad" in result.details["non_read_only_tools"]


# ---------------------------------------------------------------------------
# 9. PermissionCheckResult Structure
# ---------------------------------------------------------------------------


class TestPermissionCheckResult:
    """PermissionCheckResult has agent-readable error structure."""

    def test_result_fields(self) -> None:
        result = PermissionCheckResult(
            code="forbidden_keyword",
            message="Test message",
            tool_name="context.search",
            details={"parameter": "query", "keyword": "INSERT"},
        )
        assert result.code == "forbidden_keyword"
        assert result.message == "Test message"
        assert result.tool_name == "context.search"
        assert result.details["keyword"] == "INSERT"

    def test_result_is_frozen(self) -> None:
        result = PermissionCheckResult(
            code="forbidden_keyword",
            message="Test",
            tool_name="context.search",
        )
        with pytest.raises(AttributeError):
            result.code = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 10. All Current Tools Pass Input Gate with Normal Parameters
# ---------------------------------------------------------------------------


class TestAllCurrentToolsPassInputGate:
    """All 11 registered tools pass the input gate with normal parameters."""

    @pytest.fixture
    def bridge(self) -> ContextBridge:
        return create_bridge()

    def test_context_search_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.search", {"query": "risk decisions", "limit": 5}
        )
        assert result["status"] == "ok"

    def test_context_trace_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.trace", {"target_id": "evt_001", "depth": 3}
        )
        assert result["status"] == "ok"

    def test_context_explain_source_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_001"}
        )
        assert result["status"] == "ok"

    def test_context_package_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["a1", "a2"], "format": "json"}
        )
        assert result["status"] == "ok"

    def test_context_readiness_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Inspect code.",
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
        assert result["status"] == "ok"

    def test_context_self_explain_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.self_explain",
            {
                "question": "Why is PR #1234 blocked?",
                "explanation_type": "why_blocked",
                "evidence_refs": ["#1234"],
            },
        )
        assert result["status"] == "ok"

    def test_context_briefing_normal_passes(self, bridge: ContextBridge) -> None:
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "test-001",
                "task_scope": "Inspect code.",
                "target_issue": None,
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# 11. Error Codes Are Agent-Readable
# ---------------------------------------------------------------------------


class TestErrorCodesAreAgentReadable:
    """All permission violation error codes are structured and agent-readable."""

    def test_forbidden_keyword_error_structure(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search", {"query": "INSERT INTO fake_table"}
        )
        assert result["status"] == "error"
        error = result["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
        assert "all_violations" in error
        assert isinstance(error["all_violations"], list)
        assert len(error["all_violations"]) >= 1
        violation = error["all_violations"][0]
        assert "code" in violation
        assert "message" in violation
        assert "details" in violation

    def test_forbidden_runtime_operation_error_structure(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace", {"target_id": "git_commit target"}
        )
        assert result["status"] == "error"
        error = result["error"]
        assert error["code"] == "forbidden_runtime_operation"
        assert "git_commit" in error["message"] or "git_commit" in str(error["details"])

    def test_non_read_only_error_structure(self) -> None:
        result = PermissionGuard.check_tool_definition(
            "context.bad_tool", read_only=False
        )
        assert result is not None
        assert result.code == "non_read_only_tool"
        assert "context.bad_tool" in result.message
        assert (
            "read-only" in result.message.lower()
            or "not read-only" in result.message.lower()
        )

    def test_registry_inconsistency_error_structure(self) -> None:
        result = PermissionGuard.check_registry_consistency(
            {
                "context.bad": ToolDefinition(
                    name="context.bad",
                    description="Bad tool",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                    read_only=False,
                )
            }
        )
        assert result is not None
        assert result.code == "registry_inconsistency"
        assert "non_read_only_tools" in result.details


# ---------------------------------------------------------------------------
# 12. No Write Path in Any Handler
# ---------------------------------------------------------------------------


class TestNoWritePathInAnyHandler:
    """Verify that no handler produces mutations — code review via scan."""

    FORBIDDEN_WRITE_CALLS = [
        "open(",
        "write(",
        "subprocess.",
        "os.system",
        "os.remove",
        "os.mkdir",
        "shutil.",
        "git.",
        "requests.post",
        "requests.put",
        "requests.delete",
        "requests.patch",
    ]

    def test_handlers_do_not_contain_write_calls(self) -> None:
        """No handler source contains direct write/IO calls."""
        import inspect

        from tools.mcp.context_bridge import (
            context_briefing_handler,
            context_explain_source_handler,
            context_package_handler,
            context_readiness_handler,
            context_required_reads_handler,
            context_search_handler,
            context_self_explain_handler,
            context_stop_resolver_handler,
            context_trace_handler,
        )

        handlers = [
            context_search_handler,
            context_trace_handler,
            context_explain_source_handler,
            context_package_handler,
            context_self_explain_handler,
            context_readiness_handler,
            context_briefing_handler,
            context_stop_resolver_handler,
            context_required_reads_handler,
        ]
        for handler in handlers:
            source = inspect.getsource(handler)
            for forbidden in self.FORBIDDEN_WRITE_CALLS:
                assert forbidden not in source, (
                    f"Handler {handler.__name__} contains forbidden call: "
                    f"{forbidden}"
                )


# ---------------------------------------------------------------------------
# 13. Allowed Read-Only Inputs Pass
# ---------------------------------------------------------------------------


class TestAllowedReadOnlyInputsPass:
    """Common read-only input patterns produce no permission violations."""

    @pytest.mark.parametrize(
        "query",
        [
            "find decisions about risk limits",
            "SELECT * FROM context WHERE type='decision'",
            "search for evidence about PR #1234",
            "trace lineage of event evt_abc",
            "explain source of document src_def",
            "how is the risk engine structured",
            "what is the current status of LR audit",
            "show me the control register",
        ],
    )
    def test_read_only_queries_pass(self, query: str) -> None:
        """Common read-only queries produce no violations in search tool."""
        results = PermissionGuard.check_tool_inputs("context.search", {"query": query})
        violations = [
            r
            for r in results
            if r.code
            in (
                "forbidden_keyword",
                "forbidden_query_pattern",
                "forbidden_runtime_operation",
                "forbidden_repo_pattern",
            )
        ]
        assert len(violations) == 0, (
            f"Expected no violations for query: {query!r}, "
            f"got: {[(v.code, v.message) for v in violations]}"
        )

    def test_select_query_passes(self) -> None:
        """SELECT query (read-only) passes without violation."""
        results = PermissionGuard.check_tool_inputs(
            "context.search", {"query": "SELECT * FROM decisions WHERE id=1"}
        )
        keyword_violations = [r for r in results if r.code == "forbidden_keyword"]
        pattern_violations = [r for r in results if r.code == "forbidden_query_pattern"]
        assert len(keyword_violations) == 0, (
            f"SELECT should not trigger forbidden_keyword: " f"{keyword_violations}"
        )
        assert len(pattern_violations) == 0, (
            f"SELECT should not trigger forbidden_query_pattern: "
            f"{pattern_violations}"
        )

    def test_context_search_read_only_operation_mode(self) -> None:
        """operation_mode=read_only passes in exempt tool."""
        results = PermissionGuard.check_tool_inputs(
            "context.readiness",
            {"operation_mode": "read_only"},
        )
        violations = [r for r in results if r.code == "forbidden_runtime_operation"]
        assert len(violations) == 0

    def test_dry_run_operation_mode_not_flagged(self) -> None:
        """operation_mode=dry_run is not flagged as a forbidden keyword."""
        results = PermissionGuard.check_tool_inputs(
            "context.readiness",
            {"operation_mode": "dry_run"},
        )
        assert len(results) == 0

    def test_write_operation_mode_exempt_in_readiness(self) -> None:
        """operation_mode='write (code/docs)' is not flagged in readiness (exempt)."""
        results = PermissionGuard.check_tool_inputs(
            "context.readiness",
            {"operation_mode": "write (code/docs)"},
        )
        assert len(results) == 0

    def test_update_keyword_in_readiness_task_scope_exempt(self) -> None:
        """'Update' in readiness task_scope is not flagged (exempt tool)."""
        results = PermissionGuard.check_tool_inputs(
            "context.readiness",
            {"task_scope": "Update config."},
        )
        assert len(results) == 0

    def test_deploy_keyword_in_briefing_task_scope_exempt(self) -> None:
        """'Deploy' in briefing task_scope is not flagged (exempt tool)."""
        results = PermissionGuard.check_tool_inputs(
            "context.briefing",
            {"task_scope": "Deploy the service"},
        )
        assert len(results) == 0


# ---------------------------------------------------------------------------
# 14. Integration: Bridge blocks forbidden inputs in query tools
# ---------------------------------------------------------------------------


class TestBridgeIntegrationInputGate:
    """End-to-end tests for the input gate via ContextBridge.execute_tool."""

    def test_bridge_blocks_insert_query(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "INSERT INTO context"})
        assert result["status"] == "error"
        assert result["error"]["code"] in (
            "forbidden_keyword",
            "forbidden_query_pattern",
        )

    def test_bridge_blocks_delete_query(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "DELETE FROM context"})
        assert result["status"] == "error"
        assert result["error"]["code"] in (
            "forbidden_keyword",
            "forbidden_query_pattern",
        )

    def test_bridge_blocks_git_push_in_trace(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace", {"target_id": "evt_git_push_remote"}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "forbidden_runtime_operation"

    def test_bridge_blocks_issue_create_in_package(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.package", {"artifacts": ["issue_create new ticket"]}
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "forbidden_runtime_operation"

    def test_bridge_blocks_deploy_in_search(self) -> None:
        """Deploy in search query is blocked (query tool)."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "deploy the service"})
        assert result["status"] == "error"
        assert result["error"]["code"] == "forbidden_runtime_operation"

    def test_bridge_allows_deploy_in_readiness(self) -> None:
        """'Deploy' in readiness task_scope passes (exempt tool)."""
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "Deploy the service to production.",
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
        assert result["status"] == "ok"

    def test_bridge_allows_normal_trace(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_abc123"})
        assert result["status"] == "ok"

    def test_bridge_allows_normal_search(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "risk decisions"})
        assert result["status"] == "ok"

    def test_bridge_error_includes_all_violations(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search",
            {"query": "INSERT INTO context AND git_push origin main"},
        )
        assert result["status"] == "error"
        assert "all_violations" in result["error"]
        assert len(result["error"]["all_violations"]) >= 1


# ---------------------------------------------------------------------------
# 15. Regression: None parameters does not crash
# ---------------------------------------------------------------------------


class TestNoneParametersRegression:
    """Calling execute_tool without explicit parameters must not crash.

    Regression test for #2099 blocker where PermissionGuard.check_tool_inputs
    was called before parameters was normalized from None to {}.
    """

    def test_execute_tool_none_parameters_no_crash(self) -> None:
        """execute_tool with parameters=None returns structured error, not TypeError."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_snapshot")
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "error"
        assert result["error"]["code"] in (
            "not_implemented",
            "invalid_snapshot_id",
            "invalid_query",
            "target_not_found",
            "invalid_source_ref",
            "invalid_artifacts",
        )

    def test_execute_tool_explicit_none_no_crash(self) -> None:
        """execute_tool with parameters=None returns structured error, not TypeError."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_snapshot", None)
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "error"

    def test_execute_tool_empty_dict_no_crash(self) -> None:
        """execute_tool with parameters={} returns structured error, not TypeError."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_snapshot", {})
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "error"

    def test_execute_known_tool_with_none_no_crash(self) -> None:
        """Known tool called without parameters returns structured error."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search")
        assert isinstance(result, dict)
        assert result["status"] == "error"

    def test_input_gate_none_parameters_handled(self) -> None:
        """PermissionGuard.check_tool_inputs handles empty parameters dict."""
        results = PermissionGuard.check_tool_inputs("context.search", {})
        assert isinstance(results, list)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# 16. Regression: Non-dict parameters returns structured error
# ---------------------------------------------------------------------------


class TestNonDictParametersRegression:
    """Calling execute_tool with non-dict parameters must not crash.

    Regression test for #2099 Codex review P1: list/string parameters
    would cause AttributeError inside _walk_parameters because .items()
    is called on non-dict values before the try/except block.
    """

    def test_execute_tool_list_parameters_returns_error(self) -> None:
        """execute_tool with parameters=['bad'] returns structured error."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_snapshot", ["bad"])  # type: ignore[arg-type]
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_parameters"

    def test_execute_tool_string_parameters_returns_error(self) -> None:
        """execute_tool with parameters='x' returns structured error."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", "x")  # type: ignore[arg-type]
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_parameters"

    def test_execute_tool_int_parameters_returns_error(self) -> None:
        """execute_tool with parameters=42 returns structured error."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", 42)  # type: ignore[arg-type]
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_parameters"

    def test_execute_tool_empty_dict_parameters_passes(self) -> None:
        """execute_tool with parameters={} returns structured error (not crash)."""
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {})
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_query"
