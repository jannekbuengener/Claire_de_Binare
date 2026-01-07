"""
Integration tests for emergency stop mechanism.
Tests kill-switch integration with trading services.
"""

import pytest
import tempfile
from pathlib import Path
from core.safety.kill_switch import (
    KillSwitch,
    KillSwitchReason,
    KillSwitchState,
    get_kill_switch_state,
)


class TestEmergencyStopIntegration:
    """Integration tests for emergency stop workflow"""

    def test_kill_switch_blocks_new_orders(self, tmp_path):
        """
        Test that activated kill-switch prevents new order processing.

        This is a simplified integration test. In a full E2E test,
        this would verify actual order blocking in risk/execution services.
        """
        state_file = tmp_path / "integration_test.state"
        ks = KillSwitch(state_file=str(state_file))

        # Normal operation - kill-switch inactive
        assert ks.is_active() is False
        # In real integration: orders would be processed

        # Emergency stop activated
        ks.activate(KillSwitchReason.MANUAL, "Emergency stop test")
        assert ks.is_active() is True
        # In real integration: orders would be blocked

        # Resume trading
        ks.deactivate("test_operator", "Test complete")
        assert ks.is_active() is False
        # In real integration: orders would be processed again

    def test_kill_switch_survives_service_restart(self, tmp_path):
        """
        Test that kill-switch state persists across service restarts.
        """
        state_file = tmp_path / "restart_test.state"

        # Service 1: Activate kill-switch
        ks1 = KillSwitch(state_file=str(state_file))
        ks1.activate(KillSwitchReason.CIRCUIT_BREAKER, "Daily loss limit exceeded")
        assert ks1.is_active() is True

        # Simulate service restart (new KillSwitch instance)
        ks2 = KillSwitch(state_file=str(state_file))
        assert ks2.is_active() is True  # State persisted

        # Deactivate in restarted service
        ks2.deactivate("admin", "Issue resolved")
        assert ks2.is_active() is False

        # Another restart
        ks3 = KillSwitch(state_file=str(state_file))
        assert ks3.is_active() is False  # Inactive state persisted

    def test_multiple_services_see_same_state(self, tmp_path):
        """
        Test that multiple services (risk, execution) see the same kill-switch state.
        """
        state_file = tmp_path / "multi_service.state"

        # Simulate risk service
        risk_ks = KillSwitch(state_file=str(state_file))

        # Simulate execution service
        exec_ks = KillSwitch(state_file=str(state_file))

        # Both see inactive initially
        assert risk_ks.is_active() is False
        assert exec_ks.is_active() is False

        # Risk service activates kill-switch
        risk_ks.activate(KillSwitchReason.RISK_LIMIT, "Total exposure exceeded 30%")

        # Execution service should see the activation
        assert exec_ks.is_active() is True

        # Execution service deactivates
        exec_ks.deactivate("risk_manager", "Exposure reduced to safe levels")

        # Risk service should see deactivation
        assert risk_ks.is_active() is False

    def test_concurrent_activation_handling(self, tmp_path):
        """
        Test that concurrent activations don't corrupt state.
        """
        state_file = tmp_path / "concurrent.state"

        ks1 = KillSwitch(state_file=str(state_file))
        ks2 = KillSwitch(state_file=str(state_file))

        # Both try to activate (simulate race condition)
        result1 = ks1.activate(KillSwitchReason.CIRCUIT_BREAKER, "Reason 1")
        result2 = ks2.activate(KillSwitchReason.RISK_LIMIT, "Reason 2")

        assert result1 is True
        assert result2 is True

        # Both should see active state
        assert ks1.is_active() is True
        assert ks2.is_active() is True

        # State file should not be corrupted
        ks3 = KillSwitch(state_file=str(state_file))
        assert ks3.is_active() is True

    def test_audit_trail_completeness(self, tmp_path):
        """
        Test that all activation/deactivation events maintain audit trail.
        """
        state_file = tmp_path / "audit.state"
        ks = KillSwitch(state_file=str(state_file))

        # Activation 1
        ks.activate(KillSwitchReason.MANUAL, "Test activation 1", operator="operator1")
        state1, reason1, message1, activated_at1 = ks.get_state()

        assert reason1 == KillSwitchReason.MANUAL.value
        assert "operator1" in message1
        assert activated_at1 is not None

        # Deactivation 1
        ks.deactivate("operator2", "First issue resolved")
        state2, reason2, message2, activated_at2 = ks.get_state()

        assert reason2 is None
        assert "operator2" in message2
        assert "First issue resolved" in message2

        # Activation 2 (different reason)
        ks.activate(KillSwitchReason.SYSTEM_ERROR, "Critical error")
        state3, reason3, message3, activated_at3 = ks.get_state()

        assert reason3 == KillSwitchReason.SYSTEM_ERROR.value
        assert "Critical error" in message3
        assert activated_at3 != activated_at1  # Different timestamp

    def test_emergency_stop_workflow_end_to_end(self, tmp_path):
        """
        Test complete emergency stop workflow from detection to resolution.
        """
        state_file = tmp_path / "e2e.state"

        # Phase 1: Normal operation
        ks = KillSwitch(state_file=str(state_file))
        assert ks.is_active() is False

        # Phase 2: Auto-trigger (circuit breaker)
        ks.activate(
            KillSwitchReason.CIRCUIT_BREAKER,
            "Daily PnL: -$5,200 exceeded limit -$5,000",
        )
        assert ks.is_active() is True

        # Phase 3: Operator notified, investigates
        state, reason, message, activated_at = ks.get_state()
        assert reason == KillSwitchReason.CIRCUIT_BREAKER.value

        # Phase 4: System restarts during investigation (state must persist)
        ks_restart = KillSwitch(state_file=str(state_file))
        assert ks_restart.is_active() is True

        # Phase 5: Operator resolves issue and deactivates
        result = ks_restart.deactivate(
            "senior_trader",
            "Root cause: faulty signal, issue fixed, safe to resume",
        )
        assert result is True
        assert ks_restart.is_active() is False

        # Phase 6: Verify deactivation persists
        ks_final = KillSwitch(state_file=str(state_file))
        assert ks_final.is_active() is False


@pytest.mark.skipif(
    not Path(".cdb_kill_switch.state").exists(),
    reason="Requires actual .cdb_kill_switch.state file for production test",
)
class TestProductionKillSwitch:
    """Tests for production kill-switch (if state file exists)"""

    def test_production_kill_switch_readable(self):
        """Test that production kill-switch state file is readable"""
        ks = KillSwitch()  # Uses default state file
        state, reason, message, activated_at = ks.get_state()

        # Should not crash, state should be valid
        assert state in (KillSwitchState.ACTIVE, KillSwitchState.INACTIVE)
