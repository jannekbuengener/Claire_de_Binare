"""Fail-closed Kill-Switch invariants for Issue #4152 (S1).

Missing, empty, corrupt, and unreadable state must never evaluate as
permissive inactive on the production reader path used by Risk/Execution.
"""

from __future__ import annotations

import pytest

from core.safety.kill_switch import (
    KillSwitch,
    KillSwitchReason,
    KillSwitchState,
    get_kill_switch_details,
)


@pytest.mark.unit
class TestKillSwitchFailClosedProductionPath:
    def test_missing_state_file_blocks_when_create_if_missing_false(self, tmp_path):
        missing = tmp_path / "does_not_exist.state"
        assert not missing.exists()

        active, reason, message, _activated_at = get_kill_switch_details(
            state_file=str(missing), create_if_missing=False
        )

        assert active is True
        assert reason == KillSwitchReason.SYSTEM_ERROR.value
        assert "missing" in message.lower()

    def test_empty_state_file_blocks_via_get_state_and_details(self, tmp_path):
        state_file = tmp_path / "empty.state"
        state_file.touch()

        ks = KillSwitch(state_file=str(state_file))
        state, reason, message, _ = ks.get_state()
        assert state == KillSwitchState.ACTIVE
        assert reason == KillSwitchReason.SYSTEM_ERROR.value
        assert "empty" in message.lower()
        assert ks.is_active() is True

        active, details_reason, details_message, _ = get_kill_switch_details(
            state_file=str(state_file), create_if_missing=False
        )
        assert active is True
        assert details_reason == KillSwitchReason.SYSTEM_ERROR.value
        assert "empty" in details_message.lower()

    def test_corrupt_state_without_state_key_blocks_get_state(self, tmp_path):
        state_file = tmp_path / "corrupt.state"
        state_file.write_text("garbage data that is not valid\n", encoding="utf-8")

        ks = KillSwitch(state_file=str(state_file))
        state, reason, message, _ = ks.get_state()
        assert state == KillSwitchState.ACTIVE
        assert ks.is_active() is True
        assert reason == KillSwitchReason.SYSTEM_ERROR.value

        active, _, _, _ = get_kill_switch_details(
            state_file=str(state_file), create_if_missing=False
        )
        assert active is True

    def test_unknown_state_value_blocks(self, tmp_path):
        state_file = tmp_path / "unknown.state"
        state_file.write_text(
            "state=bogus\nreason=none\nmessage=bad\nactivated_at=none\n",
            encoding="utf-8",
        )

        ks = KillSwitch(state_file=str(state_file))
        state, reason, message, _ = ks.get_state()
        assert state == KillSwitchState.ACTIVE
        assert reason == KillSwitchReason.SYSTEM_ERROR.value
        assert "unknown" in message.lower() or "invalid" in message.lower()
        assert ks.is_active() is True

    def test_unreadable_state_blocks(self, tmp_path):
        state_file = tmp_path / "unreadable.state"
        state_file.write_text(
            "state=inactive\nreason=none\nmessage=ok\nactivated_at=none\n",
            encoding="utf-8",
        )
        ks = KillSwitch(state_file=str(state_file))

        with pytest.MonkeyPatch.context() as mp:

            def _raise_open(*_args, **_kwargs):
                raise OSError("unreadable")

            mp.setattr("builtins.open", _raise_open)
            state, reason, message, _ = ks.get_state()
            assert state == KillSwitchState.ACTIVE
            assert reason == KillSwitchReason.SYSTEM_ERROR.value
            assert ks.is_active() is True

    def test_explicit_inactive_file_allows_trading(self, tmp_path):
        state_file = tmp_path / "ok.state"
        ks = KillSwitch(state_file=str(state_file))
        assert ks.is_active() is False

        active, _reason, message, _ = get_kill_switch_details(
            state_file=str(state_file), create_if_missing=False
        )
        assert active is False
        assert message

    def test_corrupt_cannot_be_more_permissive_than_valid_inactive(self, tmp_path):
        """Property: corrupting state must not yield a more permissive verdict."""
        good = tmp_path / "good.state"
        bad = tmp_path / "bad.state"
        KillSwitch(state_file=str(good))  # creates verified inactive
        bad.write_text("not=a=valid=kill=switch\n", encoding="utf-8")

        good_active, _, _, _ = get_kill_switch_details(
            state_file=str(good), create_if_missing=False
        )
        bad_active, _, _, _ = get_kill_switch_details(
            state_file=str(bad), create_if_missing=False
        )
        assert good_active is False
        assert bad_active is True
