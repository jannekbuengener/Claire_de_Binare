"""
Unit tests for core.safety.kill_switch module
Tests emergency stop mechanism with persistent state.
"""

import os
import tempfile
import pytest
from pathlib import Path
from core.safety.kill_switch import (
    KillSwitch,
    KillSwitchState,
    KillSwitchReason,
    get_kill_switch_state,
    activate_kill_switch,
    _sanitize_for_log,
)


class TestKillSwitchBasics:
    """Tests for basic kill-switch functionality"""

    def test_initial_state_is_inactive(self, tmp_path):
        """Test kill-switch starts in INACTIVE state"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        assert ks.is_active() is False

    def test_activate_sets_active(self, tmp_path):
        """Test activation changes state to ACTIVE"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        result = ks.activate(KillSwitchReason.MANUAL, "Test activation")

        assert result is True
        assert ks.is_active() is True

    def test_deactivate_sets_inactive(self, tmp_path):
        """Test deactivation changes state to INACTIVE"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.MANUAL, "Test activation")
        assert ks.is_active() is True

        result = ks.deactivate("admin", "Test complete")

        assert result is True
        assert ks.is_active() is False

    def test_deactivate_requires_operator(self, tmp_path):
        """Test deactivation fails without operator"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.MANUAL, "Test")

        # Missing operator
        result = ks.deactivate("", "Justification")
        assert result is False
        assert ks.is_active() is True  # Still active

    def test_deactivate_requires_justification(self, tmp_path):
        """Test deactivation fails without justification"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.MANUAL, "Test")

        # Missing justification
        result = ks.deactivate("admin", "")
        assert result is False
        assert ks.is_active() is True  # Still active


class TestKillSwitchPersistence:
    """Tests for state persistence across restarts"""

    def test_state_persists_after_restart(self, tmp_path):
        """Test kill-switch state survives object recreation"""
        state_file = tmp_path / "test_kill_switch.state"

        # First instance - activate
        ks1 = KillSwitch(state_file=str(state_file))
        ks1.activate(KillSwitchReason.CIRCUIT_BREAKER, "Test persistence")
        assert ks1.is_active() is True

        # Second instance (simulates restart) - should still be active
        ks2 = KillSwitch(state_file=str(state_file))
        assert ks2.is_active() is True

    def test_inactive_state_persists(self, tmp_path):
        """Test inactive state also persists"""
        state_file = tmp_path / "test_kill_switch.state"

        # First instance - activate then deactivate
        ks1 = KillSwitch(state_file=str(state_file))
        ks1.activate(KillSwitchReason.MANUAL, "Test")
        ks1.deactivate("admin", "Resolved")
        assert ks1.is_active() is False

        # Second instance - should be inactive
        ks2 = KillSwitch(state_file=str(state_file))
        assert ks2.is_active() is False

    def test_state_file_created_if_missing(self, tmp_path):
        """Test state file is created on first use"""
        state_file = tmp_path / "new_kill_switch.state"

        assert not state_file.exists()

        ks = KillSwitch(state_file=str(state_file))

        assert state_file.exists()
        assert ks.is_active() is False  # Default state


class TestKillSwitchReasons:
    """Tests for different activation reasons"""

    def test_manual_reason(self, tmp_path):
        """Test manual activation reason"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.MANUAL, "Operator intervention")

        state, reason, message, activated_at = ks.get_state()
        assert state == KillSwitchState.ACTIVE
        assert reason == KillSwitchReason.MANUAL.value
        assert "Operator intervention" in message

    def test_circuit_breaker_reason(self, tmp_path):
        """Test circuit breaker activation reason"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.CIRCUIT_BREAKER, "Daily loss limit exceeded")

        state, reason, message, activated_at = ks.get_state()
        assert state == KillSwitchState.ACTIVE
        assert reason == KillSwitchReason.CIRCUIT_BREAKER.value
        assert "loss limit" in message

    def test_risk_limit_reason(self, tmp_path):
        """Test risk limit activation reason"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.RISK_LIMIT, "Exposure exceeded 30%")

        state, reason, message, activated_at = ks.get_state()
        assert state == KillSwitchState.ACTIVE
        assert reason == KillSwitchReason.RISK_LIMIT.value

    def test_operator_recorded_in_message(self, tmp_path):
        """Test operator name is recorded in activation message"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(
            KillSwitchReason.MANUAL, "Emergency stop", operator="john.doe@example.com"
        )

        state, reason, message, activated_at = ks.get_state()
        assert "operator: john.doe@example.com" in message


class TestKillSwitchState:
    """Tests for get_state() method"""

    def test_get_state_inactive(self, tmp_path):
        """Test get_state() for inactive kill-switch"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        state, reason, message, activated_at = ks.get_state()

        assert state == KillSwitchState.INACTIVE
        assert reason is None
        assert activated_at is None

    def test_get_state_active(self, tmp_path):
        """Test get_state() for active kill-switch"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.SYSTEM_ERROR, "Critical error detected")

        state, reason, message, activated_at = ks.get_state()

        assert state == KillSwitchState.ACTIVE
        assert reason == KillSwitchReason.SYSTEM_ERROR.value
        assert "Critical error" in message
        assert activated_at is not None

    def test_activated_at_is_iso8601(self, tmp_path):
        """Test activated_at timestamp is ISO 8601 format"""
        state_file = tmp_path / "test_kill_switch.state"
        ks = KillSwitch(state_file=str(state_file))

        ks.activate(KillSwitchReason.MANUAL, "Test")

        state, reason, message, activated_at = ks.get_state()

        # Should be valid ISO 8601 (e.g., "2025-12-27T14:30:00.123456")
        assert activated_at is not None
        assert "T" in activated_at
        assert "-" in activated_at


class TestGlobalFunctions:
    """Tests for global helper functions"""

    def test_get_kill_switch_state_default(self, tmp_path, monkeypatch):
        """Test global get_kill_switch_state() function"""
        state_file = tmp_path / "global_test.state"

        # Reset global singleton
        from core.safety import kill_switch as _ks_mod

        _ks_mod._global_kill_switch = None

        # Monkeypatch Path.cwd() to use tmp_path
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        # Should be inactive by default
        assert get_kill_switch_state(str(state_file)) is False

    def test_activate_kill_switch_global(self, tmp_path, monkeypatch):
        """Test global activate_kill_switch() function"""
        state_file = tmp_path / "global_test.state"

        # Reset global singleton
        from core.safety import kill_switch as _ks_mod

        _ks_mod._global_kill_switch = None

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        # Activate globally
        result = activate_kill_switch(KillSwitchReason.MANUAL, "Global test")

        assert result is True
        assert get_kill_switch_state(str(state_file)) is True


class TestErrorHandling:
    """Tests for error handling and recovery"""

    def test_corrupted_state_file_defaults_to_active(self, tmp_path):
        """Test corrupted state file defaults to ACTIVE (safe default)"""
        state_file = tmp_path / "corrupted.state"

        # Create corrupted file
        with open(state_file, "w") as f:
            f.write("garbage data that is not valid\n")

        ks = KillSwitch(state_file=str(state_file))

        # Should default to ACTIVE for safety
        assert ks.is_active() is True

    def test_empty_state_file_defaults_to_inactive(self, tmp_path):
        """Test empty state file defaults to INACTIVE"""
        state_file = tmp_path / "empty.state"

        # Create empty file
        state_file.touch()

        ks = KillSwitch(state_file=str(state_file))

        # Empty file should default to INACTIVE
        assert ks.is_active() is False


class TestRealWorldScenarios:
    """Integration-like tests for real-world scenarios"""

    def test_circuit_breaker_workflow(self, tmp_path):
        """Test complete circuit breaker workflow"""
        state_file = tmp_path / "circuit_breaker.state"
        ks = KillSwitch(state_file=str(state_file))

        # 1. Normal operation
        assert ks.is_active() is False

        # 2. Circuit breaker triggers
        ks.activate(
            KillSwitchReason.CIRCUIT_BREAKER, "Daily loss -5.2% exceeded limit -5.0%"
        )
        assert ks.is_active() is True

        # 3. Service restarts (simulate)
        ks2 = KillSwitch(state_file=str(state_file))
        assert ks2.is_active() is True  # Still active after restart

        # 4. Operator investigates and resolves
        result = ks2.deactivate(
            "risk_manager", "Issue resolved, risk limits adjusted"
        )
        assert result is True
        assert ks2.is_active() is False

        # 5. Service restarts again
        ks3 = KillSwitch(state_file=str(state_file))
        assert ks3.is_active() is False  # Stays inactive

    def test_manual_emergency_stop(self, tmp_path):
        """Test manual emergency stop by operator"""
        state_file = tmp_path / "manual_stop.state"
        ks = KillSwitch(state_file=str(state_file))

        # Operator notices unusual market activity
        ks.activate(
            KillSwitchReason.MANUAL,
            "Unusual market volatility detected",
            operator="trader@example.com",
        )

        assert ks.is_active() is True

        # Verify operator is recorded
        state, reason, message, activated_at = ks.get_state()
        assert "trader@example.com" in message
        assert reason == KillSwitchReason.MANUAL.value


class TestLogInjectionSanitization:
    """Tests for log injection prevention via _sanitize_for_log."""

    def test_sanitize_cr_in_message(self, tmp_path, caplog):
        """CR in message is neutralized in log output (alert #4051)."""
        import logging

        state_file = tmp_path / "test_sanitize.state"
        ks = KillSwitch(state_file=str(state_file))

        with caplog.at_level(logging.WARNING):
            ks.activate(
                KillSwitchReason.MANUAL, "Emergency\rstop"
            )

        logged_messages = [r.message for r in caplog.records]
        assert not any("\r" in m for m in logged_messages)
        assert any("Emergency\\rstop" in m for m in logged_messages)

    def test_sanitize_lf_in_message(self, tmp_path, caplog):
        """LF in message is neutralized in log output (alert #4051)."""
        import logging

        state_file = tmp_path / "test_sanitize.state"
        ks = KillSwitch(state_file=str(state_file))

        with caplog.at_level(logging.WARNING):
            ks.activate(
                KillSwitchReason.MANUAL, "Emergency\nstop"
            )

        logged_messages = [r.message for r in caplog.records]
        assert not any("\n" in m for m in logged_messages)
        assert any("Emergency\\nstop" in m for m in logged_messages)

    def test_sanitize_crlf_in_operator(self, tmp_path, caplog):
        """CRLF in operator is neutralized in log output (alert #4052)."""
        import logging

        state_file = tmp_path / "test_sanitize.state"
        ks = KillSwitch(state_file=str(state_file))

        with caplog.at_level(logging.WARNING):
            ks.activate(
                KillSwitchReason.MANUAL,
                "Test",
                operator="admin\r\nEVIL",
            )

        logged_messages = [r.message for r in caplog.records]
        assert not any("\r" in m or "\n" in m for m in logged_messages)

    def test_sanitize_control_chars_in_justification(self, tmp_path, caplog):
        """Control chars in justification are stripped in log output (alert #4053)."""
        import logging

        state_file = tmp_path / "test_sanitize.state"
        ks = KillSwitch(state_file=str(state_file))
        ks.activate(KillSwitchReason.MANUAL, "Test")

        with caplog.at_level(logging.WARNING):
            ks.deactivate("admin", "OK\x00\x01\x02\x03")

        logged_messages = [r.message for r in caplog.records]
        assert not any("\x00" in m or "\x01" in m or "\x02" in m or "\x03" in m for m in logged_messages)
        assert any("OK" in m for m in logged_messages)

    def test_sanitize_multiline_injection(self, tmp_path, caplog):
        """Multiline injection payload in message is neutralized (alert #4050)."""
        import logging

        state_file = tmp_path / "test_sanitize.state"
        ks = KillSwitch(state_file=str(state_file))

        with caplog.at_level(logging.WARNING):
            ks.activate(
                KillSwitchReason.CIRCUIT_BREAKER,
                "Real message\r\nFAKE: CRITICAL: system compromised",
            )

        logged_messages = [r.message for r in caplog.records]
        assert not any("\r" in m or "\n" in m for m in logged_messages)
        assert any("Real message\\r\\nFAKE" in m for m in logged_messages)

    def test_sanitize_function_directly(self):
        """_sanitize_for_log directly neutralizes CR, LF, and control chars."""
        assert _sanitize_for_log("hello\rworld") == "hello\\rworld"
        assert _sanitize_for_log("hello\nworld") == "hello\\nworld"
        assert _sanitize_for_log("hello\r\nworld") == "hello\\r\\nworld"
        assert _sanitize_for_log("ok\x00\x01\x02") == "ok"
        assert _sanitize_for_log("clean message") == "clean message"
        assert _sanitize_for_log("") == ""

    def test_state_file_content_unaffected_by_log_sanitization(self, tmp_path, caplog):
        """Sanitization is log-only; state file stores message as-is (no \n breakage).

        The state file format is key=value\\n so messages containing literal newlines
        corrupt the format. That is a pre-existing limitation, not introduced by this
        fix. This test verifies that sanitization targets log output, not the
        state file write path.
        """
        import logging

        state_file = tmp_path / "test_state_preserved.state"
        ks = KillSwitch(state_file=str(state_file))

        injection_msg = "Dangerous\rmessage"
        with caplog.at_level(logging.WARNING):
            ks.activate(KillSwitchReason.MANUAL, injection_msg)

        logged_messages = [r.message for r in caplog.records]
        assert not any("\r" in m for m in logged_messages)

        _state, _reason, stored_message, _activated_at = ks.get_state()
        assert "Dangerous" in stored_message

    def test_write_state_error_log_sanitized(self, tmp_path, caplog):
        """_write_state exception log sanitizes message (alert #4050).

        Force a write failure by pointing state_file at a path whose parent
        directory does not exist, so the temp-file write raises. The error
        handler logs message content which must be sanitized.
        """
        import logging
        import shutil

        nested_dir = tmp_path / "nonexistent_sub"
        state_file = nested_dir / "kill.state"

        ks = KillSwitch.__new__(KillSwitch)
        ks.state_file = state_file

        with caplog.at_level(logging.CRITICAL):
            ks._write_state(
                KillSwitchState.ACTIVE,
                KillSwitchReason.MANUAL,
                "Real\r\nFAKE",
                None,
            )

        logged_messages = [r.message for r in caplog.records]
        assert not any("\r" in m or "\n" in m for m in logged_messages)
        assert any("Real\\r\\nFAKE" in m for m in logged_messages)
