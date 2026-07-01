from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.evidence_harvester.coordinator import CoordinatorSummary
from tools.evidence_harvester.runner import RunnerState
from tools.evidence_harvester.supervisor import (
    ACTION_DONE,
    ACTION_RELAUNCH_RESUME,
    ACTION_STOP_FATAL,
    ACTION_STOP_LIMIT,
    ACTION_WAIT,
    SupervisorError,
    decide_supervision,
    parse_args,
    supervise_loop,
)

NOW = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)
PAST = "2026-06-30T11:00:00Z"
FUTURE = "2026-06-30T13:00:00Z"


def _state(**changes: object) -> RunnerState:
    return RunnerState(run_id="run", **changes)


def _events(*types: str) -> list[dict[str, str]]:
    return [
        {
            "schema_version": "cdb.evidence_harvester.coordinator_event.v1",
            "event_at_utc": f"2026-06-30T10:00:0{index}Z",
            "run_id": "run",
            "event_type": event_type,
        }
        for index, event_type in enumerate(types)
    ]


def _dummy_summary(artifact_dir: Path) -> CoordinatorSummary:
    return CoordinatorSummary(
        status="FAIL",
        artifact_dir=str(artifact_dir),
        completed_cycles=1,
        recovery_events_written=1,
        restart_count=0,
        max_restart_count=3,
        final_validation_started=False,
        stop_reason="",
    )


def _write_state(artifact_dir: Path, **changes: object) -> None:
    payload = {
        "schema_version": "cdb.evidence_harvester.runner_state.v1",
        "run_id": "run",
        "total_cycles_completed": 1,
    }
    payload.update(changes)
    (artifact_dir / "runner_state.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_events(artifact_dir: Path, *types: str) -> None:
    lines = [json.dumps(event) for event in _events(*types)]
    (artifact_dir / "coordinator_events.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


# --- decide_supervision matrix -------------------------------------------------


@pytest.mark.unit
def test_decision_done_via_status() -> None:
    decision = decide_supervision(
        _state(coordinator_status="completed"), [], NOW, False, 0, 5
    )
    assert decision.action == ACTION_DONE


@pytest.mark.unit
def test_decision_done_via_final_validation_event() -> None:
    decision = decide_supervision(
        _state(coordinator_status="final_validation"),
        _events("cycle_completed", "final_validation_completed"),
        NOW,
        False,
        0,
        5,
    )
    assert decision.action == ACTION_DONE


@pytest.mark.unit
def test_decision_stop_fatal_on_terminal_status() -> None:
    decision = decide_supervision(
        _state(coordinator_status="fatal_stop"), [], NOW, False, 0, 5
    )
    assert decision.action == ACTION_STOP_FATAL


@pytest.mark.unit
def test_decision_relaunch_resume_on_stalled_sleep() -> None:
    decision = decide_supervision(
        _state(coordinator_status="sleeping", next_cycle_due_at_utc=PAST),
        _events("cycle_completed", "sleep_started"),
        NOW,
        False,
        0,
        5,
    )
    assert decision.action == ACTION_RELAUNCH_RESUME
    assert decision.overdue is True


@pytest.mark.unit
def test_decision_stop_limit_when_budget_exhausted() -> None:
    decision = decide_supervision(
        _state(coordinator_status="sleeping", next_cycle_due_at_utc=PAST),
        _events("cycle_completed", "sleep_started"),
        NOW,
        False,
        5,
        5,
    )
    assert decision.action == ACTION_STOP_LIMIT


@pytest.mark.unit
def test_decision_wait_when_process_alive() -> None:
    decision = decide_supervision(
        _state(coordinator_status="sleeping", next_cycle_due_at_utc=PAST),
        _events("cycle_completed", "sleep_started"),
        NOW,
        True,
        0,
        5,
    )
    assert decision.action == ACTION_WAIT
    assert decision.reason == "coordinator process alive"


@pytest.mark.unit
def test_decision_wait_when_future_due_and_alive() -> None:
    decision = decide_supervision(
        _state(coordinator_status="sleeping", next_cycle_due_at_utc=FUTURE),
        _events("cycle_completed", "sleep_started"),
        NOW,
        True,
        0,
        5,
    )
    assert decision.action == ACTION_WAIT
    assert decision.overdue is False


@pytest.mark.unit
def test_decision_wait_when_dead_but_not_stalled_sleep() -> None:
    decision = decide_supervision(
        _state(coordinator_status="running"),
        _events("cycle_started"),
        NOW,
        False,
        0,
        5,
    )
    assert decision.action == ACTION_WAIT
    assert decision.reason == "no relaunch condition met"


# --- supervise_loop ------------------------------------------------------------


@pytest.mark.unit
def test_supervise_loop_relaunches_then_done(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_state(
        artifact_dir, coordinator_status="sleeping", next_cycle_due_at_utc=PAST
    )
    _write_events(artifact_dir, "cycle_completed", "sleep_started")

    launches: list[int] = []

    def launcher() -> CoordinatorSummary:
        launches.append(1)
        _write_state(artifact_dir, coordinator_status="completed")
        _write_events(
            artifact_dir,
            "cycle_completed",
            "sleep_resumed",
            "final_validation_completed",
        )
        return _dummy_summary(artifact_dir)

    result = supervise_loop(
        artifact_dir=artifact_dir,
        launcher=launcher,
        process_alive_fn=lambda: False,
        now_fn=lambda: NOW,
        sleep_fn=lambda seconds: None,
        poll_seconds=0,
        max_relaunch_count=5,
        max_polls=10,
    )

    assert result.status == "DONE"
    assert result.relaunch_count == 1
    assert len(launches) == 1


@pytest.mark.unit
def test_supervise_loop_stops_at_relaunch_limit(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_state(
        artifact_dir, coordinator_status="sleeping", next_cycle_due_at_utc=PAST
    )
    _write_events(artifact_dir, "cycle_completed", "sleep_started")

    launches: list[int] = []

    def launcher() -> CoordinatorSummary:
        launches.append(1)
        # Launcher fails to clear the stall -> loop keeps seeing a stalled sleep.
        return _dummy_summary(artifact_dir)

    result = supervise_loop(
        artifact_dir=artifact_dir,
        launcher=launcher,
        process_alive_fn=lambda: False,
        now_fn=lambda: NOW,
        sleep_fn=lambda seconds: None,
        poll_seconds=0,
        max_relaunch_count=2,
        max_polls=50,
    )

    assert result.status == "STOP_LIMIT"
    assert result.relaunch_count == 2
    assert len(launches) == 2


@pytest.mark.unit
def test_supervise_loop_wait_timeout(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_state(
        artifact_dir, coordinator_status="sleeping", next_cycle_due_at_utc=FUTURE
    )
    _write_events(artifact_dir, "cycle_completed", "sleep_started")

    sleeps: list[float] = []

    def launcher() -> CoordinatorSummary:  # pragma: no cover - must not run
        raise AssertionError("launcher must not run while waiting")

    result = supervise_loop(
        artifact_dir=artifact_dir,
        launcher=launcher,
        process_alive_fn=lambda: True,
        now_fn=lambda: NOW,
        sleep_fn=lambda seconds: sleeps.append(seconds),
        poll_seconds=30,
        max_relaunch_count=5,
        max_polls=3,
    )

    assert result.status == "WAIT_TIMEOUT"
    assert result.polls == 3
    assert result.relaunch_count == 0
    assert sleeps == [30, 30]


@pytest.mark.unit
def test_supervise_loop_rejects_negative_relaunch(tmp_path: Path) -> None:
    with pytest.raises(SupervisorError):
        supervise_loop(
            artifact_dir=tmp_path,
            launcher=lambda: _dummy_summary(tmp_path),
            process_alive_fn=lambda: False,
            max_relaunch_count=-1,
        )


# --- CLI arg parsing -----------------------------------------------------------


@pytest.mark.unit
def test_parse_args_status_defaults() -> None:
    args = parse_args(["status", "--artifact-dir", "runs/x"])
    assert args.command == "status"
    assert args.assume_process_alive is False


@pytest.mark.unit
def test_parse_args_supervise_requires_explicit_flag() -> None:
    args = parse_args(
        [
            "supervise",
            "--artifact-dir",
            "runs/x",
            "--fixture",
            "f.json",
            "--iterations",
            "288",
        ]
    )
    assert args.command == "supervise"
    assert args.explicit is False
    assert args.iterations == 288
