"""
Unit tests for output contract compliance of Context MCP tools.

Validates that handler outputs conform to the v1 contract structure
defined in docs/surrealdb/context-tool-contracts-v1.md and the
implemented v0 structure.
#2100
"""

import pytest
from tools.mcp.context_bridge import create_bridge

pytestmark = pytest.mark.unit


COMMON_OK_FIELDS = {"tool", "status"}


class TestSearchOutputContract:
    """Verify context.search output matches contract structure."""

    def test_ok_output_has_tool_field(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "risk"})
        assert result["tool"] == "context.search"

    def test_ok_output_has_status_field(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "risk"})
        assert result["status"] == "ok"

    def test_ok_results_have_required_item_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.search",
            {"query": "risk", "limit": 5},
        )
        assert "results" in result
        assert "metadata" in result
        assert "query_time_ms" in result["metadata"]
        assert "total_hits" in result["metadata"]

    def test_error_output_has_code_and_message(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {})
        assert result["status"] == "error"
        assert "code" in result["error"]
        assert "message" in result["error"]

    def test_metadata_has_query_time_and_total_hits(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.search", {"query": "test"})
        meta = result["metadata"]
        assert isinstance(meta["query_time_ms"], int)
        assert isinstance(meta["total_hits"], int)


class TestTraceOutputContract:
    """Verify context.trace output matches contract structure."""

    def test_ok_output_has_tool_and_status(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_001"})
        assert result["tool"] == "context.trace"
        assert result["status"] == "ok"

    def test_trace_has_root_with_id_type_title(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {"target_id": "evt_001"})
        root = result["trace"]["root"]
        assert "id" in root
        assert "type" in root
        assert "title" in root

    def test_trace_has_lineage_with_relationship(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.trace", {"target_id": "evt_001", "depth": 3}
        )
        for item in result["trace"]["lineage"]:
            assert "id" in item
            assert "relationship" in item
            assert "depth" in item

    def test_error_output_has_target_not_found_code(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.trace", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "target_not_found"


class TestExplainSourceOutputContract:
    """Verify context.explain_source output matches contract structure."""

    def test_ok_output_has_tool_and_status(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_001"}
        )
        assert result["tool"] == "context.explain_source"
        assert result["status"] == "ok"

    def test_explanation_has_source_ref_type_provenance(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_001"}
        )
        expl = result["explanation"]
        assert "source_ref" in expl
        assert "source_type" in expl
        assert "provenance" in expl

    def test_explanation_has_confidence_warnings_stale_tombstone(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_001"}
        )
        expl = result["explanation"]
        assert "confidence" in expl
        assert "warnings" in expl
        assert "stale" in expl
        assert "tombstone" in expl

    def test_source_refs_is_list(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source", {"source_ref": "src_001"}
        )
        assert isinstance(result["explanation"]["source_refs"], list)

    def test_include_chain_false_removes_chain(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.explain_source",
            {"source_ref": "src_001", "include_chain": False},
        )
        provenance = result["explanation"]["provenance"]
        assert "chain" not in provenance


class TestPackageOutputContract:
    """Verify context.package output matches contract structure."""

    def test_ok_output_has_package_with_format_items_created_at(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {"artifacts": ["art_001"]})
        pkg = result["package"]
        assert "format" in pkg
        assert "items" in pkg
        assert "created_at" in pkg
        assert "package_id" in pkg

    def test_package_id_is_string(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {"artifacts": ["art_001"]})
        assert isinstance(result["package"]["package_id"], str)

    def test_error_output_has_invalid_artifacts_code(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.package", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_artifacts"


class TestReadinessOutputContract:
    """Verify context.readiness output matches contract structure."""

    def test_ok_output_has_all_contract_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "review documentation",
                "operation_mode": "read_only",
                "stop_conditions": ["S10"],
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
        for field in (
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
        ):
            assert field in result["readiness"], f"Missing field: {field}"

    def test_status_values_are_valid(self) -> None:
        bridge = create_bridge()
        valid_statuses = {
            "ready_for_read_only",
            "ready_for_dry_run",
            "ready_for_human_go",
            "blocked_missing_context",
            "blocked_missing_evidence",
            "blocked_scope_drift",
        }
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "review documentation",
                "operation_mode": "read_only",
                "stop_conditions": ["S10"],
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
        assert result["readiness"]["status"] in valid_statuses

    def test_guardrails_contain_no_go_text(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.readiness",
            {
                "task_scope": "review documentation",
                "operation_mode": "read_only",
                "stop_conditions": ["S10"],
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
        guardrails_text = " ".join(result["readiness"]["guardrails"])
        assert (
            "NO-GO" in guardrails_text
            or "No-Go" in guardrails_text
            or "no_go" in guardrails_text.lower()
        )


class TestBriefingOutputContract:
    """Verify context.briefing output matches contract structure."""

    def test_ok_output_has_briefing_id(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "task_001",
                "target_issue": None,
                "task_scope": "review docs",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert "briefing" in result
        assert "briefing_id" in result["briefing"]

    def test_briefing_id_is_deterministic(self) -> None:
        bridge = create_bridge()
        params = {
            "task_id": "task_002",
            "target_issue": None,
            "task_scope": "review docs",
            "requested_depth": "standard",
            "operation_mode": "write (code/docs)",
        }
        r1 = bridge.execute_tool("context.briefing", params)
        r2 = bridge.execute_tool("context.briefing", params)
        assert r1["briefing"]["briefing_id"] == r2["briefing"]["briefing_id"]

    def test_briefing_has_guardrails(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.briefing",
            {
                "task_id": "task_003",
                "target_issue": None,
                "task_scope": "check status",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert "guardrails" in result["briefing"]
        assert isinstance(result["briefing"]["guardrails"], list)
        assert len(result["briefing"]["guardrails"]) > 0


class TestCdbContextBriefingAliasOutputContract:
    """Verify cdb_context_briefing alias output matches briefing contract."""

    def test_ok_output_has_briefing_id_and_alias_tool_name(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_briefing",
            {
                "task_id": "task_alias_001",
                "target_issue": None,
                "task_scope": "review docs",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["tool"] == "cdb_context_briefing"
        assert "briefing" in result
        assert "briefing_id" in result["briefing"]

    def test_alias_briefing_has_guardrails(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_briefing",
            {
                "task_id": "task_alias_002",
                "target_issue": None,
                "task_scope": "check status",
                "requested_depth": "quick",
                "operation_mode": "read_only",
            },
        )
        assert result["tool"] == "cdb_context_briefing"
        assert "guardrails" in result["briefing"]
        assert isinstance(result["briefing"]["guardrails"], list)
        assert len(result["briefing"]["guardrails"]) > 0


class TestShowSnapshotOutputContract:
    """Verify context.show_snapshot output matches contract structure."""

    def test_ok_output_has_tool_and_status(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_snapshot", {"snapshot_id": "snap_contract_001"}
        )
        assert result["tool"] == "context.show_snapshot"
        assert result["status"] == "ok"

    def test_snapshot_has_required_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_snapshot", {"snapshot_id": "snap_contract_001"}
        )
        snap = result["snapshot"]
        assert snap["snapshot_id"] == "snap_contract_001"
        assert isinstance(snap["tools_count"], int)
        assert isinstance(snap["tool_names"], list)
        assert "context.show_snapshot" in snap["tool_names"]

    def test_invalid_snapshot_id_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_snapshot", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_snapshot_id"


class TestShowAuditOutputContract:
    """Verify context.show_audit output matches contract structure."""

    def test_ok_output_has_tool_and_status(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit", {"entity_id": "context.show_snapshot"}
        )
        assert result["tool"] == "context.show_audit"
        assert result["status"] == "ok"

    def test_audit_has_required_fields(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool(
            "context.show_audit", {"entity_id": "context.show_snapshot"}
        )
        audit = result["audit"]
        for field in (
            "audit_id",
            "target_tool",
            "audit_type",
            "limit",
            "exists",
            "read_only",
            "handler_status",
            "input_schema_keys",
            "output_schema_keys",
            "guard",
            "source",
            "limitations",
        ):
            assert field in audit, f"Missing field: {field}"
        assert audit["target_tool"] == "context.show_snapshot"
        assert isinstance(audit["audit_id"], str)
        assert isinstance(audit["audit_type"], str)
        assert isinstance(audit["limit"], int)
        assert isinstance(audit["exists"], bool)
        assert isinstance(audit["read_only"], bool)
        assert isinstance(audit["input_schema_keys"], list)
        assert isinstance(audit["output_schema_keys"], list)
        assert isinstance(audit["guard"], dict)
        assert audit["source"] == "registry"

    def test_audit_id_is_deterministic_for_identical_inputs(self) -> None:
        bridge = create_bridge()
        params = {
            "target_tool": "context.show_snapshot",
            "audit_type": "all",
            "limit": 50,
        }
        r1 = bridge.execute_tool("context.show_audit", params)
        r2 = bridge.execute_tool("context.show_audit", params)
        assert r1["audit"]["audit_id"] == r2["audit"]["audit_id"]

    def test_audit_id_changes_when_target_tool_changes(self) -> None:
        bridge = create_bridge()
        r1 = bridge.execute_tool(
            "context.show_audit", {"target_tool": "context.show_snapshot"}
        )
        r2 = bridge.execute_tool(
            "context.show_audit", {"target_tool": "context.search"}
        )
        assert r1["audit"]["audit_id"] != r2["audit"]["audit_id"]

    def test_audit_id_changes_when_audit_type_changes(self) -> None:
        bridge = create_bridge()
        r1 = bridge.execute_tool(
            "context.show_audit",
            {"target_tool": "context.show_snapshot", "audit_type": "all"},
        )
        r2 = bridge.execute_tool(
            "context.show_audit",
            {"target_tool": "context.show_snapshot", "audit_type": "handler"},
        )
        assert r1["audit"]["audit_id"] != r2["audit"]["audit_id"]

    def test_audit_id_changes_when_limit_changes(self) -> None:
        bridge = create_bridge()
        r1 = bridge.execute_tool(
            "context.show_audit",
            {"target_tool": "context.show_snapshot", "limit": 1},
        )
        r2 = bridge.execute_tool(
            "context.show_audit",
            {"target_tool": "context.show_snapshot", "limit": 2},
        )
        assert r1["audit"]["audit_id"] != r2["audit"]["audit_id"]

    def test_invalid_entity_id_fails_closed(self) -> None:
        bridge = create_bridge()
        result = bridge.execute_tool("context.show_audit", {})
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_entity_id"
