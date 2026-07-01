from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.evidence_harvester.coordinator import (
    COORDINATOR_EVENT_SCHEMA,
    RECOVERY_EVENT_SCHEMA,
    CoordinatorError,
    _now_utc,
    _sleep_with_interval_check,
    run_fixture_window,
)
from tools.evidence_harvester.ops_validation import (
    _check_inconclusive_run,
    _check_sleep_lifecycle_completeness,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_cycle_artifacts(artifact_dir: Path, stamp: str) -> None:
    _write_json(artifact_dir / f"collector_report_{stamp}.json", {"stamp": stamp})
    _write_json(
        artifact_dir / f"snapshot_{stamp}.json",
        {
            "metadata": {
                "generated_at_utc": "2026-06-19T00:00:00Z",
                "schema_version": "cdb.evidence_harvester.snapshot.v1",
            },
            "safety": {
                "lr_status": "NO-GO",
                "live_status": "NO-GO",
                "echtgeld_status": "NO-GO",
                "runtime_actions": "not_allowed",
                "db_execution": "not_allowed",
                "banner": "Paper/research evidence only; no LR-Go, no Live-Go, no Echtgeld-Go.",
            },
        },
    )
    (artifact_dir / f"snapshot_{stamp}.md").write_text("# Snapshot\n", encoding="utf-8")
    _write_json(artifact_dir / f"alert_{stamp}.json", {"stamp": stamp})
    (artifact_dir / f"alert_{stamp}.md").write_text("# Alert\n", encoding="utf-8")
    _write_json(
        artifact_dir / "runner_heartbeat.json",
        {
            "schema_version": "cdb.evidence_harvester.runner_heartbeat.v1",
            "current_run_at_utc": "2026-06-19T00:00:00Z",
        },
    )
    _write_json(
        artifact_dir / "runner_state.json",
        {
            "schema_version": "cdb.evidence_harvester.runner_state.v1",
            "last_cycle_verdict": "PASS",
            "last_cycle_ended_at_utc": "2026-06-19T00:00:00Z",
        },
    )


def _pass_boot_runner(repo_root: Path, artifact_dir: Path) -> tuple[int, dict]:
    return 0, {"verdict": {"verdict": "PASS"}}


def _noop_final_validator(repo_root: Path, artifact_dir: Path) -> tuple[int, dict]:
    return 0, {"summary": {"verdict": "PASS"}}


def _pass_watchdog_runner(
    repo_root: Path,
    out_dir: Path,
    cycle_stamp: str,
    cadence_seconds: int,
) -> tuple[int, dict]:
    payload = {
        "report_name": f"watchdog_report_{cycle_stamp}.json",
        "verdict": {"verdict": "PASS"},
        "findings": [],
    }
    _write_json(out_dir / payload["report_name"], payload)
    _write_json(out_dir / "watchdog_report.json", payload)
    (out_dir / f"watchdog_report_{cycle_stamp}.md").write_text(
        "# Watchdog\n", encoding="utf-8"
    )
    (out_dir / "watchdog_report.md").write_text("# Watchdog\n", encoding="utf-8")
    return 0, payload


def _pass_write_audit_runner(
    repo_root: Path,
    out_dir: Path,
    cycle_stamp: str,
) -> tuple[int, dict]:
    payload = {
        "report_name": f"write_audit_report_{cycle_stamp}.json",
        "verdict": {"verdict": "PASS"},
        "findings": [],
    }
    _write_json(out_dir / payload["report_name"], payload)
    (out_dir / f"write_audit_report_{cycle_stamp}.md").write_text(
        "# Write Audit\n", encoding="utf-8"
    )
    return 0, payload


@pytest.mark.unit
def test_recoverable_watchdog_failure_restarts_and_progresses_beyond_cycle9(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "run"

    cycle_attempts: list[str] = []
    sleep_calls: list[float] = []
    next_due_samples: list[str] = []
    recovery_injected = {"done": False}

    def cycle_runner(
        repo_root: Path, fixture_path: Path, out_dir: Path
    ) -> tuple[int, str]:
        stamp = f"20260619T0000{len(cycle_attempts):02d}Z"
        cycle_attempts.append(stamp)
        _write_cycle_artifacts(out_dir, stamp)
        return 0, stamp

    def watchdog_runner(
        repo_root: Path,
        out_dir: Path,
        cycle_stamp: str,
        cadence_seconds: int,
    ) -> tuple[int, dict]:
        report_name = f"watchdog_report_{cycle_stamp}.json"
        payload = {
            "report_name": report_name,
            "verdict": {"verdict": "PASS"},
            "findings": [],
        }
        if len(cycle_attempts) == 9 and not recovery_injected["done"]:
            recovery_injected["done"] = True
            payload = {
                "report_name": report_name,
                "verdict": {"verdict": "FAIL"},
                "findings": [
                    {
                        "check_id": "W011",
                        "severity": "fail",
                        "field_name": "metadata.generated_at_utc",
                        "message": "Latest snapshot is 9999s old (max_age=7200s)",
                    }
                ],
            }
        _write_json(out_dir / report_name, payload)
        _write_json(out_dir / "watchdog_report.json", payload)
        (out_dir / f"watchdog_report_{cycle_stamp}.md").write_text(
            "# Watchdog\n", encoding="utf-8"
        )
        (out_dir / "watchdog_report.md").write_text("# Watchdog\n", encoding="utf-8")
        return (1 if payload["verdict"]["verdict"] == "FAIL" else 0), payload

    def write_audit_runner(
        repo_root: Path,
        out_dir: Path,
        cycle_stamp: str,
    ) -> tuple[int, dict]:
        payload = {
            "report_name": f"write_audit_report_{cycle_stamp}.json",
            "verdict": {"verdict": "PASS"},
            "findings": [],
        }
        _write_json(out_dir / payload["report_name"], payload)
        (out_dir / f"write_audit_report_{cycle_stamp}.md").write_text(
            "# Write Audit\n", encoding="utf-8"
        )
        return 0, payload

    def sleep_fn(seconds: float) -> None:
        sleep_calls.append(seconds)
        state_path = artifact_dir / "runner_state.json"
        if state_path.exists():
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            next_due = str(payload.get("next_cycle_due_at_utc", ""))
            if next_due:
                next_due_samples.append(next_due)

    summary = run_fixture_window(
        repo_root=tmp_path,
        fixture_path=fixture,
        artifact_dir=artifact_dir,
        iterations=10,
        cadence_seconds=1,
        max_restart_count=3,
        restart_backoff_seconds=7,
        sleep_fn=sleep_fn,
        boot_runner=_pass_boot_runner,
        cycle_runner=cycle_runner,
        watchdog_runner=watchdog_runner,
        write_audit_runner=write_audit_runner,
        final_validator=_noop_final_validator,
    )

    assert summary.status == "PASS"
    assert summary.completed_cycles == 10
    assert summary.recovery_events_written == 1
    assert summary.restart_count == 1
    assert 7 in sleep_calls
    assert len(cycle_attempts) == 11
    assert next_due_samples
    assert any(
        "000010Z" in p.name for p in artifact_dir.glob("collector_report_*.json")
    )

    state_payload = json.loads(
        (artifact_dir / "runner_state.json").read_text(encoding="utf-8")
    )
    assert state_payload["run_id"] == artifact_dir.name
    assert state_payload["total_cycles_started"] == 11
    assert state_payload["total_cycles_completed"] == 10
    assert state_payload["total_successful_cycles"] == 10
    assert state_payload["total_failed_cycles"] == 1
    assert state_payload["successful_runs"] == 10
    assert state_payload["failed_runs"] == 1
    assert state_payload["coordinator_status"] == "completed"

    recovery_events = sorted(artifact_dir.glob("recovery_event_*.json"))
    assert len(recovery_events) == 1
    payload = json.loads(recovery_events[0].read_text(encoding="utf-8"))
    assert payload["schema_version"] == RECOVERY_EVENT_SCHEMA
    assert payload["classification"] == "recoverable"
    assert payload["action"] == "restart_cycle"
    assert payload["restart_count"] == 1

    event_lines = (
        (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    events = [json.loads(line) for line in event_lines]
    assert events
    assert all(event["schema_version"] == COORDINATOR_EVENT_SCHEMA for event in events)
    assert [event["event_at_utc"] for event in events] == sorted(
        event["event_at_utc"] for event in events
    )
    event_types = {event["event_type"] for event in events}
    assert {
        "run_started",
        "boot_readiness_completed",
        "cycle_started",
        "runner_cycle_completed",
        "watchdog_completed",
        "write_audit_completed",
        "cycle_completed",
        "sleep_started",
        "sleep_completed",
        "next_cycle_due_at_utc",
        "recovery_started",
        "recovery_completed",
        "final_validation_started",
        "final_validation_completed",
    }.issubset(event_types)


@pytest.mark.unit
def test_fatal_safety_failure_stops_without_restart(tmp_path: Path) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "run"

    cycle_attempts: list[str] = []

    def cycle_runner(
        repo_root: Path, fixture_path: Path, out_dir: Path
    ) -> tuple[int, str]:
        stamp = "20260619T000000Z"
        cycle_attempts.append(stamp)
        _write_cycle_artifacts(out_dir, stamp)
        return 0, stamp

    def watchdog_runner(
        repo_root: Path,
        out_dir: Path,
        cycle_stamp: str,
        cadence_seconds: int,
    ) -> tuple[int, dict]:
        payload = {
            "report_name": f"watchdog_report_{cycle_stamp}.json",
            "verdict": {"verdict": "FAIL"},
            "findings": [
                {
                    "check_id": "W012",
                    "severity": "fail",
                    "field_name": "safety.live_status",
                    "message": "Expected live_status='NO-GO', got 'GO'",
                }
            ],
        }
        return 1, payload

    def write_audit_runner(
        repo_root: Path,
        out_dir: Path,
        cycle_stamp: str,
    ) -> tuple[int, dict]:
        raise AssertionError(
            "write_audit_runner should not run after fatal watchdog failure"
        )

    summary = run_fixture_window(
        repo_root=tmp_path,
        fixture_path=fixture,
        artifact_dir=artifact_dir,
        iterations=10,
        cadence_seconds=1,
        max_restart_count=3,
        restart_backoff_seconds=7,
        sleep_fn=lambda seconds: None,
        boot_runner=_pass_boot_runner,
        cycle_runner=cycle_runner,
        watchdog_runner=watchdog_runner,
        write_audit_runner=write_audit_runner,
        final_validator=_noop_final_validator,
    )

    assert summary.status == "FAIL"
    assert summary.completed_cycles == 0
    assert summary.recovery_events_written == 1
    assert summary.restart_count == 0
    assert summary.stop_reason == "fatal_watchdog_failure"
    assert len(cycle_attempts) == 1

    recovery_events = sorted(artifact_dir.glob("recovery_event_*.json"))
    assert len(recovery_events) == 1
    payload = json.loads(recovery_events[0].read_text(encoding="utf-8"))
    assert payload["classification"] == "fatal"
    assert payload["action"] == "stop"

    events = [
        json.loads(line)
        for line in (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert any(event["event_type"] == "fatal_stop" for event in events)


@pytest.mark.unit
def test_sleep_with_interval_check_accumulates_exact_duration() -> None:
    calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    overshoot = _sleep_with_interval_check(
        fake_sleep, total_seconds=300, chunk_seconds=60
    )

    assert overshoot == pytest.approx(0.0, abs=0.001)
    assert calls == [60, 60, 60, 60, 60]
    assert sum(calls) == 300


@pytest.mark.unit
def test_sleep_with_interval_check_partial_chunk() -> None:
    calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    overshoot = _sleep_with_interval_check(
        fake_sleep, total_seconds=125, chunk_seconds=60
    )

    assert overshoot == pytest.approx(0.0, abs=0.001)
    assert calls == [60, 60, 5]
    assert sum(calls) == 125


@pytest.mark.unit
def test_sleep_with_interval_check_stops_when_chunk_returns_after_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = {"value": 0.0}
    calls: list[float] = []

    def fake_monotonic() -> float:
        return now["value"]

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)
        now["value"] += 130.0

    monkeypatch.setattr(
        "tools.evidence_harvester.coordinator.time.monotonic",
        fake_monotonic,
    )

    overshoot = _sleep_with_interval_check(
        fake_sleep, total_seconds=125, chunk_seconds=60
    )

    assert calls == [60]
    assert overshoot == pytest.approx(5.0, abs=0.001)


@pytest.mark.unit
def test_sleep_with_interval_check_zero_duration() -> None:
    calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    overshoot = _sleep_with_interval_check(
        fake_sleep, total_seconds=0, chunk_seconds=60
    )

    assert overshoot == pytest.approx(0.0, abs=0.001)
    assert calls == []


@pytest.mark.unit
def test_now_utc_returns_aware_datetime_when_cdb_utcnow_is_naive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    naive_utc = datetime(2026, 6, 20, 18, 44, 13)
    assert naive_utc.tzinfo is None

    monkeypatch.setattr(
        "tools.evidence_harvester.coordinator.cdb_utcnow",
        lambda: naive_utc,
    )

    result = _now_utc()

    assert result.tzinfo is not None
    assert result.tzinfo == UTC
    assert result.hour == 18
    assert result.minute == 44
    assert result.second == 13


@pytest.mark.unit
def test_now_utc_preserves_aware_datetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aware_utc = datetime(2026, 6, 20, 18, 44, 13, tzinfo=UTC)

    monkeypatch.setattr(
        "tools.evidence_harvester.coordinator.cdb_utcnow",
        lambda: aware_utc,
    )

    result = _now_utc()

    assert result.tzinfo is not None
    assert result == aware_utc


def _counting_cycle_runner(counter: dict) -> object:
    def _runner(repo_root: Path, fixture_path: Path, out_dir: Path) -> tuple[int, str]:
        stamp = f"20260619T0000{counter['n']:02d}Z"
        counter["n"] += 1
        _write_cycle_artifacts(out_dir, stamp)
        return 0, stamp

    return _runner


class _SimulatedCrash(RuntimeError):
    pass


@pytest.mark.unit
def test_resume_after_interrupted_sleep_reaches_final_validation(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "slice-e-resume"
    counter = {"n": 0}
    cycle_runner = _counting_cycle_runner(counter)

    def crashing_sleep(seconds: float) -> None:
        raise _SimulatedCrash("process died during sleep window")

    with pytest.raises(_SimulatedCrash):
        run_fixture_window(
            repo_root=tmp_path,
            fixture_path=fixture,
            artifact_dir=artifact_dir,
            iterations=3,
            cadence_seconds=1,
            max_restart_count=3,
            restart_backoff_seconds=0,
            sleep_fn=crashing_sleep,
            boot_runner=_pass_boot_runner,
            cycle_runner=cycle_runner,
            watchdog_runner=_pass_watchdog_runner,
            write_audit_runner=_pass_write_audit_runner,
            final_validator=_noop_final_validator,
        )

    stalled = json.loads(
        (artifact_dir / "runner_state.json").read_text(encoding="utf-8")
    )
    assert stalled["coordinator_status"] == "sleeping"
    assert stalled["total_cycles_completed"] == 1
    events_before = [
        json.loads(line)
        for line in (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events_before[-1]["event_type"] == "sleep_started"

    summary = run_fixture_window(
        repo_root=tmp_path,
        fixture_path=fixture,
        artifact_dir=artifact_dir,
        iterations=3,
        cadence_seconds=1,
        max_restart_count=3,
        restart_backoff_seconds=0,
        resume=True,
        sleep_fn=lambda seconds: None,
        boot_runner=_pass_boot_runner,
        cycle_runner=cycle_runner,
        watchdog_runner=_pass_watchdog_runner,
        write_audit_runner=_pass_write_audit_runner,
        final_validator=_noop_final_validator,
    )

    assert summary.status == "PASS"
    assert summary.completed_cycles == 3

    final_state = json.loads(
        (artifact_dir / "runner_state.json").read_text(encoding="utf-8")
    )
    assert final_state["total_cycles_completed"] == 3
    assert final_state["coordinator_status"] == "completed"

    events = [
        json.loads(line)
        for line in (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    types = [event["event_type"] for event in events]
    assert "run_resumed" in types
    assert "sleep_resumed" in types
    assert types[-1] == "final_validation_completed"
    # No double counting: exactly three cycle_completed events for a 3-cycle run.
    assert types.count("cycle_completed") == 3

    recoveries = sorted(artifact_dir.glob("recovery_event_*.json"))
    sleep_stall = [
        json.loads(path.read_text(encoding="utf-8")) for path in recoveries
    ]
    assert any(
        event["failure_source"] == "sleep_stall"
        and event["action"] == "resume_cycle_window"
        for event in sleep_stall
    )


@pytest.mark.unit
def test_resume_of_completed_cycles_reruns_only_final_validation(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "resume-final"
    counter = {"n": 0}

    def crashing_final(repo_root: Path, out_dir: Path) -> tuple[int, dict]:
        raise _SimulatedCrash("process died during final validation")

    with pytest.raises(_SimulatedCrash):
        run_fixture_window(
            repo_root=tmp_path,
            fixture_path=fixture,
            artifact_dir=artifact_dir,
            iterations=2,
            cadence_seconds=1,
            max_restart_count=3,
            restart_backoff_seconds=0,
            sleep_fn=lambda seconds: None,
            boot_runner=_pass_boot_runner,
            cycle_runner=_counting_cycle_runner(counter),
            watchdog_runner=_pass_watchdog_runner,
            write_audit_runner=_pass_write_audit_runner,
            final_validator=crashing_final,
        )

    stalled = json.loads(
        (artifact_dir / "runner_state.json").read_text(encoding="utf-8")
    )
    assert stalled["total_cycles_completed"] == 2
    assert stalled["coordinator_status"] == "final_validation"

    resume_cycles = {"n": 0}

    def guard_cycle_runner(
        repo_root: Path, fixture_path: Path, out_dir: Path
    ) -> tuple[int, str]:
        resume_cycles["n"] += 1
        return 0, "unexpected"

    summary = run_fixture_window(
        repo_root=tmp_path,
        fixture_path=fixture,
        artifact_dir=artifact_dir,
        iterations=2,
        cadence_seconds=1,
        max_restart_count=3,
        restart_backoff_seconds=0,
        resume=True,
        sleep_fn=lambda seconds: None,
        boot_runner=_pass_boot_runner,
        cycle_runner=guard_cycle_runner,
        watchdog_runner=_pass_watchdog_runner,
        write_audit_runner=_pass_write_audit_runner,
        final_validator=_noop_final_validator,
    )

    assert resume_cycles["n"] == 0
    assert summary.status == "PASS"
    assert summary.completed_cycles == 2

    events = [
        json.loads(line)
        for line in (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[-1]["event_type"] == "final_validation_completed"


@pytest.mark.unit
def test_resume_fails_without_prior_state(tmp_path: Path) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    with pytest.raises(CoordinatorError, match="runner_state"):
        run_fixture_window(
            repo_root=tmp_path,
            fixture_path=fixture,
            artifact_dir=tmp_path / "empty-run",
            iterations=2,
            resume=True,
            boot_runner=_pass_boot_runner,
        )


@pytest.mark.unit
def test_resume_fails_on_run_id_mismatch(tmp_path: Path) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_json(
        artifact_dir / "runner_state.json",
        {
            "schema_version": "cdb.evidence_harvester.runner_state.v1",
            "run_id": "some-other-run",
            "coordinator_status": "sleeping",
            "total_cycles_completed": 1,
        },
    )
    with pytest.raises(CoordinatorError, match="run_id mismatch"):
        run_fixture_window(
            repo_root=tmp_path,
            fixture_path=fixture,
            artifact_dir=artifact_dir,
            iterations=2,
            resume=True,
            boot_runner=_pass_boot_runner,
        )


@pytest.mark.unit
def test_resume_refused_for_terminal_status(tmp_path: Path) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_json(
        artifact_dir / "runner_state.json",
        {
            "schema_version": "cdb.evidence_harvester.runner_state.v1",
            "run_id": "run",
            "coordinator_status": "completed",
            "total_cycles_completed": 2,
        },
    )
    with pytest.raises(CoordinatorError, match="terminal"):
        run_fixture_window(
            repo_root=tmp_path,
            fixture_path=fixture,
            artifact_dir=artifact_dir,
            iterations=2,
            resume=True,
            boot_runner=_pass_boot_runner,
        )


@pytest.mark.unit
def test_sleep_with_interval_check_propagates_interrupt() -> None:
    def interrupted_sleep(seconds: float) -> None:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        _sleep_with_interval_check(
            interrupted_sleep, total_seconds=120, chunk_seconds=60
        )


@pytest.mark.unit
def test_resumed_run_clears_sleep_and_inconclusive_validators(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "collector_input.json"
    fixture.write_text("{}", encoding="utf-8")
    artifact_dir = tmp_path / "validator-consistency"
    counter = {"n": 0}
    cycle_runner = _counting_cycle_runner(counter)

    def crashing_sleep(seconds: float) -> None:
        raise _SimulatedCrash("process died during sleep window")

    with pytest.raises(_SimulatedCrash):
        run_fixture_window(
            repo_root=tmp_path,
            fixture_path=fixture,
            artifact_dir=artifact_dir,
            iterations=2,
            cadence_seconds=1,
            max_restart_count=3,
            restart_backoff_seconds=0,
            sleep_fn=crashing_sleep,
            boot_runner=_pass_boot_runner,
            cycle_runner=cycle_runner,
            watchdog_runner=_pass_watchdog_runner,
            write_audit_runner=_pass_write_audit_runner,
            final_validator=_noop_final_validator,
        )

    # Before resume: the stalled stream would trip both validators.
    stalled_events = [
        json.loads(line)
        for line in (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    stalled_state = json.loads(
        (artifact_dir / "runner_state.json").read_text(encoding="utf-8")
    )
    pre_findings: list[tuple[str, str]] = []

    def _pre_add(name: str, severity: str, message: str, **kwargs: object) -> None:
        pre_findings.append((name, severity))

    _check_sleep_lifecycle_completeness(
        stalled_events, stalled_state, _pre_add, is_final=True
    )
    _check_inconclusive_run(stalled_state, stalled_events, 1.0, 72, _pre_add)
    assert pre_findings, "stalled run must trip O264/O303 before resume"

    run_fixture_window(
        repo_root=tmp_path,
        fixture_path=fixture,
        artifact_dir=artifact_dir,
        iterations=2,
        cadence_seconds=1,
        max_restart_count=3,
        restart_backoff_seconds=0,
        resume=True,
        sleep_fn=lambda seconds: None,
        boot_runner=_pass_boot_runner,
        cycle_runner=cycle_runner,
        watchdog_runner=_pass_watchdog_runner,
        write_audit_runner=_pass_write_audit_runner,
        final_validator=_noop_final_validator,
    )

    events = [
        json.loads(line)
        for line in (artifact_dir / "coordinator_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    state_payload = json.loads(
        (artifact_dir / "runner_state.json").read_text(encoding="utf-8")
    )

    findings: list[tuple[str, str]] = []

    def _add_finding(name: str, severity: str, message: str, **kwargs: object) -> None:
        findings.append((name, severity))

    _check_sleep_lifecycle_completeness(
        events, state_payload, _add_finding, is_final=True
    )
    _check_inconclusive_run(state_payload, events, 1.0, 72, _add_finding)

    assert findings == []
