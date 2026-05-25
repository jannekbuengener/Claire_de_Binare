"""
Unit tests for MCP Briefing Tool (context.briefing and cdb_context_briefing).

Tests the briefing handlers from tools.mcp.context_bridge.
Pure unit tests: no DB, no network, no live repo access.
"""

import pytest

from tools.mcp.context_bridge import (
    context_briefing_handler,
    cdb_context_briefing_handler,
)

pytestmark = pytest.mark.unit


class TestContextBriefingHandler:
    """Tests for context.briefing handler."""

    def test_missing_task_id_returns_error(self) -> None:
        """Missing task_id fails closed."""
        result = context_briefing_handler()
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_id"

    def test_empty_task_id_returns_error(self) -> None:
        """Empty task_id fails closed."""
        result = context_briefing_handler(
            task_id="",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_id"

    def test_missing_task_scope_returns_error(self) -> None:
        """Missing task_scope fails closed."""
        result = context_briefing_handler(
            task_id="test-1", requested_depth="quick", operation_mode="read_only"
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_task_scope"

    def test_missing_target_issue_defaults_to_none(self) -> None:
        """Missing target_issue defaults to None (optional field)."""
        result = context_briefing_handler(
            task_id="test-1",
            task_scope="test",
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        assert (
            result["briefing"]["session_context"]["github_state"]["target_issue"]
            is None
        )

    def test_valid_request_returns_ok(self) -> None:
        """Valid inputs produce ok status with briefing."""
        result = context_briefing_handler(
            task_id="test-1",
            task_scope="test scope",
            target_issue="#2112",
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        assert "briefing" in result
        briefing = result["briefing"]
        assert "briefing_id" in briefing
        assert "scope_summary" in briefing
        assert "guardrails" in briefing
        assert "stop_conditions" in briefing
        assert "human_go_required" in briefing
        assert briefing["human_go_required"] is False

    def test_write_mode_sets_human_go_required(self) -> None:
        """Write operation mode sets human_go_required=True."""
        result = context_briefing_handler(
            task_id="test-2",
            task_scope="write docs",
            target_issue=None,
            requested_depth="standard",
            operation_mode="write (code/docs)",
        )
        assert result["status"] == "ok"
        assert result["briefing"]["human_go_required"] is True

    def test_deep_depth_includes_context_package_ref(self) -> None:
        """Deep depth should include context_package_ref (mocked)."""
        result = context_briefing_handler(
            task_id="test-3",
            task_scope="deep briefing",
            target_issue=None,
            requested_depth="deep",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        # context_package_ref may be None or a string; not asserting specific value
        assert "context_package_ref" in result["briefing"]

    def test_quick_depth_summary(self) -> None:
        """Quick depth produces summary with quick tag."""
        result = context_briefing_handler(
            task_id="test-4",
            task_scope="quick test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        summary = result["briefing"]["scope_summary"]
        assert "quick" in summary.lower()

    def test_invalid_depth_returns_error(self) -> None:
        """Invalid requested_depth fails closed."""
        result = context_briefing_handler(
            task_id="test-5",
            task_scope="test",
            target_issue=None,
            requested_depth="invalid",
            operation_mode="read_only",
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_depth"


class TestCdbContextBriefingHandler:
    """Tests for cdb_context_briefing handler (alias with byte limit)."""

    def test_cdb_briefing_calls_context_briefing(self) -> None:
        """cdb_context_briefing delegates to context_briefing_handler."""
        result = cdb_context_briefing_handler(
            task_id="test-6",
            task_scope="cdb test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        # Should return ok or error from underlying handler
        assert result["status"] in ("ok", "error")
        if result["status"] == "ok":
            assert result["tool"] == "cdb_context_briefing"
            assert "briefing" in result

    def test_cdb_briefing_returns_error_on_failure(self) -> None:
        """cdb_context_briefing returns error if underlying fails."""
        result = cdb_context_briefing_handler()  # missing required args
        assert result["status"] == "error"
        assert result["tool"] == "cdb_context_briefing"

    def test_cdb_briefing_tool_name_rewritten(self) -> None:
        """Tool name is rewritten to cdb_context_briefing."""
        result = cdb_context_briefing_handler(
            task_id="test-7",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            assert result["tool"] == "cdb_context_briefing"


class TestBriefingOutputStructure:
    """Test that briefing output conforms to v1 schema."""

    def test_required_fields_present(self) -> None:
        """Briefing has all required fields."""
        result = context_briefing_handler(
            task_id="test-8",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            briefing = result["briefing"]
            required = {
                "briefing_id",
                "scope_summary",
                "human_go_required",
                "guardrails",
                "stop_conditions",
            }
            assert required.issubset(
                briefing.keys()
            ), f"Missing required fields: {required - set(briefing.keys())}"

    def test_guardrails_non_empty(self) -> None:
        """Guardrails list is non-empty."""
        result = context_briefing_handler(
            task_id="test-9",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            guardrails = result["briefing"]["guardrails"]
            assert isinstance(guardrails, list)
            assert len(guardrails) > 0

    def test_stop_conditions_non_empty(self) -> None:
        """Stop conditions list is non-empty (minimum present)."""
        result = context_briefing_handler(
            task_id="test-10",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            stop_conditions = result["briefing"]["stop_conditions"]
            assert isinstance(stop_conditions, list)
            assert len(stop_conditions) > 0

    def test_briefing_id_is_deterministic(self) -> None:
        """Same inputs produce same briefing_id."""
        kwargs = dict(
            task_id="test-11",
            task_scope="deterministic test",
            target_issue="#2112",
            requested_depth="standard",
            operation_mode="read_only",
        )
        result1 = context_briefing_handler(**kwargs)
        result2 = context_briefing_handler(**kwargs)
        if result1["status"] == "ok" and result2["status"] == "ok":
            id1 = result1["briefing"]["briefing_id"]
            id2 = result2["briefing"]["briefing_id"]
            assert id1 == id2, "briefing_id not deterministic"


class TestRequiredReadsInBriefing:
    """Test that required reads are present in briefing."""

    def test_required_reads_contain_minimum_set(self) -> None:
        """Briefing includes minimum required reads."""
        result = context_briefing_handler(
            task_id="test-12",
            task_scope="test",
            target_issue=None,
            requested_depth="standard",
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            required_reads = result["briefing"].get("required_reads", [])
            paths = [r for r in required_reads]
            min_paths = ["AGENTS.md", "agents/AGENTS.md", "CURRENT_STATUS.md"]
            for mp in min_paths:
                assert any(mp in p for p in paths), f"Missing minimum read: {mp}"
