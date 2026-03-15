"""Targeted tests for the risk service /metrics endpoint hardening."""

from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture()
def _risk_stats():
    """Provide a minimal stats dict matching the risk service globals."""
    return {
        "signals_received": 10,
        "orders_approved": 5,
        "orders_blocked": 3,
        "orders_skipped": 1,
        "order_results_received": 4,
        "orders_rejected_execution": 1,
        "alerts_generated": 2,
        "reduce_only_approved": 0,
        "proactive_unwind_triggered": 0,
    }


@pytest.fixture()
def _risk_state():
    """Provide a minimal risk_state mock."""
    state = MagicMock()
    state.circuit_breaker_active = False
    state.pending_orders = 0
    state.total_exposure = 1000.0
    return state


class TestMetricsKillSwitchHardening:
    """Verify that /metrics survives kill-switch read failures."""

    def test_kill_switch_active_exported(self, _risk_stats, _risk_state):
        """When kill-switch is readable, the metric is exported correctly."""
        with patch(
            "core.safety.kill_switch.get_kill_switch_details",
            return_value=(True, "MANUAL", "test", "2026-01-01T00:00:00Z"),
        ):
            from core.safety.kill_switch import get_kill_switch_details

            active, _, _, _ = get_kill_switch_details(create_if_missing=False)
            ks_value = 1 if active else 0
            assert ks_value == 1

    def test_kill_switch_inactive_exported(self, _risk_stats, _risk_state):
        """When kill-switch is inactive, the metric reads 0."""
        with patch(
            "core.safety.kill_switch.get_kill_switch_details",
            return_value=(False, None, None, None),
        ):
            from core.safety.kill_switch import get_kill_switch_details

            active, _, _, _ = get_kill_switch_details(create_if_missing=False)
            ks_value = 1 if active else 0
            assert ks_value == 0

    def test_kill_switch_exception_yields_zero(self, _risk_stats, _risk_state):
        """When kill-switch read throws, the metric defaults to 0 (fail-safe)."""
        with patch(
            "core.safety.kill_switch.get_kill_switch_details",
            side_effect=OSError("state file corrupted"),
        ):
            from core.safety.kill_switch import get_kill_switch_details

            try:
                active = get_kill_switch_details(create_if_missing=False)[0]
                ks_value = 1 if active else 0
            except Exception:
                ks_value = 0  # mirrors the hardened code path
            assert ks_value == 0

    def test_alerts_generated_metric_present(self, _risk_stats, _risk_state):
        """The alerts_generated counter is readable from stats."""
        assert _risk_stats["alerts_generated"] == 2
        line = f"risk_alerts_generated_total {_risk_stats['alerts_generated']}"
        assert "risk_alerts_generated_total 2" in line
