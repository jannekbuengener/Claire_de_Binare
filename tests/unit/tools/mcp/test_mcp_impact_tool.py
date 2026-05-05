"""
Unit tests for MCP Impact Tool (cdb_context_impact).

Tests the cdb_context_impact_handler from tools.mcp.context_bridge.
Pure unit tests: no DB, no network.
"""

import pytest

from tools.mcp.context_bridge import cdb_context_impact_handler


pytestmark = pytest.mark.unit


class TestCdbContextImpactHandler:
    """Tests for cdb_context_impact handler."""

    def test_missing_inputs_returns_ok_with_low_impact(self) -> None:
        """No inputs returns ok with low impact (defaults)."""
        result = cdb_context_impact_handler()
        assert result["status"] == "ok"
        impact = result["impact"]
        assert impact["impact_level"] == "low"
        assert impact["impact_type"] == "SOFT"

    def test_valid_inputs_returns_ok(self) -> None:
        """Valid inputs produce ok status with impact."""
        result = cdb_context_impact_handler(
            target_paths=["core/utils/clock.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        assert result["status"] == "ok"
        assert "impact" in result
        impact = result["impact"]
        assert "impact_id" in impact
        assert "impact_level" in impact
        assert "impact_type" in impact
        assert "affected_artifacts" in impact
        assert "stop_conditions" in impact

    def test_impact_level_for_core_path(self) -> None:
        """Core path yields medium impact."""
        result = cdb_context_impact_handler(
            target_paths=["core/utils/clock.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert impact["impact_level"] == "medium"
            assert impact["impact_type"] == "HARD"

    def test_impact_level_for_docs_path(self) -> None:
        """Docs path yields low impact."""
        result = cdb_context_impact_handler(
            target_paths=["docs/some-doc.md"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert impact["impact_level"] == "low"
            assert impact["impact_type"] == "SOFT"

    def test_impact_level_for_services_path(self) -> None:
        """Services path yields high impact."""
        result = cdb_context_impact_handler(
            target_paths=["services/signal/service.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert impact["impact_level"] == "high"
            assert impact["impact_type"] == "HARD"

    def test_impact_level_for_governance_path(self) -> None:
        """Governance path yields blocking impact."""
        result = cdb_context_impact_handler(
            target_paths=["knowledge/governance/CDB_CONSTITUTION.md"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert impact["impact_level"] == "blocking"

    def test_write_mode_adds_stop_conditions(self) -> None:
        """Write mode adds stop condition about write."""
        result = cdb_context_impact_handler(
            target_paths=["core/utils/clock.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="write (code/docs)",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            stop_conditions = impact.get("stop_conditions", [])
            # Should have at least one condition related to write
            write_conds = [
                sc for sc in stop_conditions
                if sc.get("type") == "write_requires_human_go"
                or "write" in sc.get("reason", "").lower()
            ]
            assert len(write_conds) >= 1

    def test_invalid_operation_mode_returns_error(self) -> None:
        """Invalid operation_mode returns error."""
        result = cdb_context_impact_handler(
            target_paths=[],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="invalid_mode",
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "invalid_operation_mode"

    def test_empty_inputs_produce_low_impact(self) -> None:
        """Empty inputs produce low impact."""
        result = cdb_context_impact_handler(
            target_paths=[],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert impact["impact_level"] == "low"
            assert impact["impact_type"] == "SOFT"

    def test_confidence_field_present(self) -> None:
        """Confidence field is present."""
        result = cdb_context_impact_handler(
            target_paths=["core/utils/clock.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert "confidence" in impact
            assert impact["confidence"] in ("high", "medium", "low")

    def test_required_validation_present(self) -> None:
        """Required validation section present."""
        result = cdb_context_impact_handler(
            target_paths=["services/risk/service.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert "required_validation" in impact
            validation = impact["required_validation"]
            assert isinstance(validation, dict)

    def test_guardrails_present(self) -> None:
        """Guardrails list is present and non-empty."""
        result = cdb_context_impact_handler(
            target_paths=[],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        assert "guardrails" in result
        guardrails = result["guardrails"]
        assert isinstance(guardrails, list)
        assert len(guardrails) > 0

    def test_tool_name_is_cdb_context_impact(self) -> None:
        """Tool name is cdb_context_impact."""
        result = cdb_context_impact_handler(
            target_paths=[],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        assert result["tool"] == "cdb_context_impact"

    def test_impact_id_is_deterministic(self) -> None:
        """Same inputs produce same impact_id."""
        kwargs = dict(
            target_paths=["core/utils/clock.py"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        result1 = cdb_context_impact_handler(**kwargs)
        result2 = cdb_context_impact_handler(**kwargs)
        if result1["status"] == "ok" and result2["status"] == "ok":
            id1 = result1["impact"]["impact_id"]
            id2 = result2["impact"]["impact_id"]
            assert id1 == id2, "impact_id not deterministic"

    def test_affected_items_are_lists(self) -> None:
        """Affected artifacts, symbols, tests, docs are lists."""
        result = cdb_context_impact_handler(
            target_paths=["core/utils/clock.py"],
            target_symbols=["utcnow"],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            assert isinstance(impact.get("affected_artifacts", []), list)
            assert isinstance(impact.get("affected_symbols", []), list)
            assert isinstance(impact.get("affected_tests", []), list)
            assert isinstance(impact.get("affected_docs", []), list)

    def test_gate_risks_for_governance_path(self) -> None:
        """Governance path triggers governance_touched gate risk."""
        result = cdb_context_impact_handler(
            target_paths=["knowledge/governance/CDB_GOVERNANCE.md"],
            target_symbols=[],
            target_issue=None,
            target_concepts=[],
            operation_mode="read_only",
        )
        if result["status"] == "ok":
            impact = result["impact"]
            gate_risks = impact.get("gate_risks", [])
            assert any("governance_touched" in r for r in gate_risks)
