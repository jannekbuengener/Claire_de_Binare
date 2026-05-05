"""
Unit tests for MCP Briefing Enrichment (#2122).

Tests the honest partial enrichment logic in context_briefing_handler 
from tools.mcp.context_bridge.
"""

import pytest
from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit


class TestBriefingEnrichment:
    """Tests for briefing enrichment fields and honest runtime behavior."""

    def test_enrichment_id_present(self) -> None:
        """Briefing result includes enrichment_id."""
        result = context_briefing_handler(
            task_id="test-enrich-1",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert "enrichment_id" in briefing
        assert briefing["enrichment_id"].startswith("cdb-enrich-")
        assert "enriched_briefing_id" in briefing
        assert briefing["enriched_briefing_id"] == briefing["briefing_id"]

    def test_trust_summary_reports_partial_mode(self) -> None:
        """Trust summary indicates partial enrichment/missing resolvers."""
        result = context_briefing_handler(
            task_id="test-enrich-2",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        summary = result["briefing"]["trust_summary"]
        assert "partial mode" in summary.lower()
        assert "#2020" in summary  # Refers to missing evidence resolve issue

    def test_no_fabricated_data_for_issue_2122(self) -> None:
        """Production code must not fabricate data even for issue #2122."""
        result = context_briefing_handler(
            task_id="test-enrich-3",
            task_scope="test",
            target_issue="#2122",
            requested_depth="standard",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        
        # Must be empty as resolvers #2020 and #2121 are missing
        assert briefing["enriched_decisions"] == []
        assert briefing["enriched_evidence"] == []
        assert briefing["enriched_memory"] == []

    def test_missing_evidence_notice_and_stop_condition(self) -> None:
        """Missing resolver triggers notices and S5 stop condition."""
        result = context_briefing_handler(
            task_id="test-enrich-4",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        
        assert "evidence" in briefing["missing_evidence_notice"]
        assert "decisions" in briefing["missing_evidence_notice"]
        
        # Check for S5 stop condition
        assert any("S5: missing evidence resolution" in sc for sc in briefing["stop_conditions"])

    def test_enriched_fields_completeness(self) -> None:
        """All required enrichment fields are present in the output."""
        result = context_briefing_handler(
            task_id="test-enrich-5",
            task_scope="test",
            target_issue=None,
            requested_depth="quick",
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        fields = {
            "enrichment_id", "enriched_briefing_id", "trust_summary",
            "enriched_decisions", "enriched_evidence", "enriched_memory",
            "enriched_stop_conditions", "stale_evidence_notice",
            "contradictory_evidence_notice", "missing_evidence_notice"
        }
        for field in fields:
            assert field in briefing, f"Missing enrichment field: {field}"
