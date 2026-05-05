"""
Unit tests for Stop Condition Resolver v1 (#2107).

Tests the resolve_stop_conditions function from tools.surrealdb.context_stop_resolver.
Pure unit tests: no DB, no network.
"""

import pytest

from tools.surrealdb.context_stop_resolver import (
    resolve_stop_conditions,
)


pytestmark = pytest.mark.unit


class TestKnownStopCodes:
    """Test that known S1-S10 and H1-H8 codes resolve correctly."""

    def test_S1_missing_scope(self) -> None:
        """S1: missing scope -> scope_drift_risk, blocking."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S1: scope ambiguous"],
            warnings=[],
            operation_mode="read_only",
        )
        assert len(resolved) >= 1
        cond = resolved[0]
        assert cond["type"] == "scope_drift_risk"
        assert cond["severity"] == "blocking"
        # Reason should mention scope
        assert "scope" in cond["reason"].lower()

    def test_S6_write_requires_human_go(self) -> None:
        """S6: write without impact report -> write_requires_human_go, blocking."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S6: write without impact report"],
            warnings=[],
            operation_mode="write (code/docs)",
        )
        assert len(resolved) >= 1
        cond = resolved[0]
        assert cond["type"] == "write_requires_human_go"
        assert cond["severity"] == "blocking"
        assert cond["human_go_required"] is True

    def test_H1_write_action_requires_go(self) -> None:
        """H1: write action requires explicit Human-GO."""
        resolved = resolve_stop_conditions(
            stop_conditions=["H1: write action requires explicit Human-GO"],
            warnings=[],
            operation_mode="write (code/docs)",
        )
        assert len(resolved) >= 1
        cond = resolved[0]
        assert cond["type"] == "write_requires_human_go"
        assert cond["severity"] == "blocking"
        assert cond["human_go_required"] is True

    def test_S10_stop_if_lr_claims(self) -> None:
        """S10: STOP if LR/Stage/Live claims surface -> blocking due to live keywords."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S10: STOP if LR/Stage/Live claims surface"],
            warnings=[],
            operation_mode="read_only",
        )
        assert len(resolved) >= 1
        cond = resolved[0]
        assert cond["type"] == "stale_context"
        # Live keywords in condition escalate severity to blocking
        assert cond["severity"] == "blocking"


class TestUnknownConditions:
    """Test that unknown conditions are handled safely."""

    def test_unknown_condition_becomes_scope_drift_risk(self) -> None:
        """Unknown condition string -> scope_drift_risk warning."""
        resolved = resolve_stop_conditions(
            stop_conditions=["some random stop condition"],
            warnings=[],
            operation_mode="read_only",
        )
        # Should produce at least one condition
        assert len(resolved) >= 1
        # The unknown condition should be mapped to scope_drift_risk or runtime_surface_touched
        types = [c["type"] for c in resolved]
        assert any(t in ("scope_drift_risk", "runtime_surface_touched") for t in types)

    def test_empty_stop_conditions_returns_empty(self) -> None:
        """Empty list returns empty list."""
        resolved = resolve_stop_conditions(
            stop_conditions=[],
            warnings=[],
            operation_mode="read_only",
        )
        assert resolved == []


class TestWarningsScanning:
    """Test that warnings are scanned for secrets/live/runtime keywords."""

    def test_secrets_keyword_in_warnings(self) -> None:
        """Warnings containing 'secrets' trigger secrets_risk."""
        resolved = resolve_stop_conditions(
            stop_conditions=[],
            warnings=["found secrets in config"],
            operation_mode="read_only",
        )
        types = [c["type"] for c in resolved]
        assert "secrets_risk" in types

    def test_live_keyword_in_warnings(self) -> None:
        """Warnings containing 'live' trigger forbidden_path."""
        resolved = resolve_stop_conditions(
            stop_conditions=[],
            warnings=["live readiness check passed"],
            operation_mode="read_only",
        )
        types = [c["type"] for c in resolved]
        assert "forbidden_path" in types

    def test_runtime_keyword_in_warnings(self) -> None:
        """Warnings containing 'runtime' trigger runtime_surface_touched."""
        resolved = resolve_stop_conditions(
            stop_conditions=[],
            warnings=["runtime service modified"],
            operation_mode="read_only",
        )
        types = [c["type"] for c in resolved]
        assert "runtime_surface_touched" in types


class TestOperationMode:
    """Test that operation_mode influences severity."""

    def test_S7_non_write_mode_becomes_warning(self) -> None:
        """S7 (trading surface touched) with read_only -> warning."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S7: trading/risk/execution scope touched"],
            warnings=[],
            operation_mode="read_only",
        )
        cond = [c for c in resolved if c["type"] == "trading_surface_touched"]
        assert len(cond) == 1
        assert cond[0]["severity"] == "warning"

    def test_S7_write_mode_stays_blocking(self) -> None:
        """S7 with write mode -> blocking."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S7: trading/risk/execution scope touched"],
            warnings=[],
            operation_mode="write (code/docs)",
        )
        cond = [c for c in resolved if c["type"] == "trading_surface_touched"]
        assert len(cond) == 1
        assert cond[0]["severity"] == "blocking"


class TestDeduplication:
    """Test that duplicate conditions are deduplicated."""

    def test_duplicate_same_condition_deduplicated(self) -> None:
        """Same stop condition string appears only once."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S1: scope ambiguous", "S1: scope ambiguous"],
            warnings=[],
            operation_mode="read_only",
        )
        # Should have only one S1 condition
        s1_conds = [c for c in resolved if "S1" in c.get("reason", "")]
        assert len(s1_conds) <= 1


class TestOutputStructure:
    """Test that each resolved condition has required keys."""

    def test_each_condition_has_required_keys(self) -> None:
        """Each condition dict contains type, severity, reason, required_action, human_go_required."""
        resolved = resolve_stop_conditions(
            stop_conditions=["S1: scope ambiguous"],
            warnings=[],
            operation_mode="read_only",
        )
        required_keys = {"type", "severity", "reason", "required_action", "human_go_required"}
        for cond in resolved:
            assert required_keys.issubset(cond.keys()), (
                f"Missing keys in condition: {required_keys - set(cond.keys())}"
            )

    def test_human_go_required_is_bool(self) -> None:
        """human_go_required field is boolean."""
        resolved = resolve_stop_conditions(
            stop_conditions=["H1: write action requires Human-GO"],
            warnings=[],
            operation_mode="write (code/docs)",
        )
        for cond in resolved:
            assert isinstance(cond["human_go_required"], bool), (
                f"human_go_required is not bool: {type(cond['human_go_required'])}"
            )


class TestReadinessResult:
    """Test that readiness_result can provide additional stop conditions."""

    def test_readiness_result_stop_conditions_added(self) -> None:
        """stop_conditions from readiness_result are included."""
        readiness = {
            "stop_conditions": ["S2: no context package and no required reads"],
        }
        resolved = resolve_stop_conditions(
            stop_conditions=[],
            warnings=[],
            readiness_result=readiness,
            operation_mode="read_only",
        )
        # Should include at least one condition from readiness_result
        assert len(resolved) >= 1
        # Check that the condition about missing context is present
        reasons = [c.get("reason", "") for c in resolved]
        assert any("context" in r.lower() for r in reasons)
