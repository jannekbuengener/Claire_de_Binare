"""Kill-switch drill simulation contract tests (#3875).

Parent #3872. Pure simulation — no real kill-switch, runtime, or alerts.
"""

from __future__ import annotations

import pytest

from tests.unit.test_pack._test_pack_contract_helpers import (
    KILL_SWITCH_STATES,
    simulate_kill_switch_drill,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_active_state_with_operator_action_produces_pass() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="active",
        operator_activated=True,
    )
    assert result.verdict == "PASS"
    assert result.kill_switch_state == "active"
    assert "VERIFY_KILL_SWITCH_ACTIVE" in result.timeline_events
    assert not result.fail_reasons


def test_inactive_state_is_not_pass() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="inactive",
        operator_activated=False,
    )
    assert result.verdict == "FAIL"
    assert "VERIFY_KILL_SWITCH_INACTIVE" in result.timeline_events
    assert any("not active" in r for r in result.fail_reasons)


def test_unknown_state_is_fail_closed_not_pass() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="unknown",
        operator_activated=False,
    )
    assert result.verdict == "FAIL"
    assert result.kill_switch_state == "unknown"
    assert "VERIFY_KILL_SWITCH_ERROR" in result.timeline_events
    assert any("not verifiable" in r for r in result.fail_reasons)


@pytest.mark.parametrize("state", sorted(KILL_SWITCH_STATES))
def test_simulation_covers_all_kill_switch_states(state: str) -> None:
    operator_ok = state == "active"
    result = simulate_kill_switch_drill(
        kill_switch_state=state,  # type: ignore[arg-type]
        operator_activated=operator_ok,
    )
    assert result.kill_switch_state == state
    assert result.verdict in {"PASS", "FAIL"}


def test_simulation_emits_timeline_evidence_artifacts() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="active",
        operator_activated=True,
    )
    assert "DRILL_START" in result.timeline_events
    assert "DRILL_END" in result.timeline_events
    assert "timeline.json" in result.evidence_artifacts
    assert "drill_verdict.json" in result.evidence_artifacts
    assert "reports/kill_switch_verification.json" in result.evidence_artifacts


def test_missing_alert_trigger_fails_even_when_kill_switch_active() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="active",
        operator_activated=True,
        alert_triggered=False,
    )
    assert result.verdict == "FAIL"
    assert any("alert" in r.lower() for r in result.fail_reasons)


def test_lr003_failure_fails_closed() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="active",
        operator_activated=True,
        lr003_passed=False,
    )
    assert result.verdict == "FAIL"
    assert any("LR-003" in r for r in result.fail_reasons)


def test_expected_operator_action_sequence_on_success_path() -> None:
    result = simulate_kill_switch_drill(
        kill_switch_state="active",
        operator_activated=True,
    )
    events = list(result.timeline_events)
    assert events.index("ALERT_TRIGGERED") < events.index("VERIFY_KILL_SWITCH_ACTIVE")
    assert events.index("VERIFY_KILL_SWITCH_ACTIVE") < events.index("DRILL_END")
