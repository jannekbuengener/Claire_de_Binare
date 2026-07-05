"""Evidence harvester sleep-stall supervisor.

Decision-and-relaunch layer that detects the Slice-B/C/D stall pattern
(``sleep_started`` without ``sleep_completed`` past ``next_cycle_due_at_utc``
with a dead coordinator process) and relaunches the coordinator in resume mode
with a bounded relaunch budget.

The decision function and supervise loop are pure and fully injectable
(launcher, process-liveness probe, clock, sleep) so they are unit-testable
without spawning any process, installing an OS scheduler, or touching Docker /
DB / Redis / secrets. The CLI ``supervise`` path is fail-closed behind
``--explicit``; the read-only ``status`` path never mutates anything.

Phase 1 (#3733) adds an external out-of-process scaffold: PID record/probe,
``supervision_state.json``, subprocess resume launcher, and
``supervise-external`` / ``plan-external`` commands. Runtime proof remains a
separate Operator Runtime-GO slice.

Boundaries: dry/fixture research only. LR NO-GO. No Live-Go, no Echtgeld-Go.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .coordinator import (
    DEFAULT_CADENCE_SECONDS,
    DEFAULT_MAX_RESTART_COUNT,
    DEFAULT_RESTART_BACKOFF_SECONDS,
    CoordinatorSummary,
    _now_utc,
    _read_coordinator_events,
    _read_runner_state,
    _repo_root,
    run_fixture_window,
)
from .runner import RunnerState

SUPERVISION_SCHEMA = "cdb.evidence_harvester.supervision.v1"
COORDINATOR_PID_SCHEMA = "cdb.evidence_harvester.coordinator_pid.v1"
SUPERVISION_STATE_SCHEMA = "cdb.evidence_harvester.supervision_state.v1"
COORDINATOR_PID_FILENAME = "coordinator_pid.json"
SUPERVISION_STATE_FILENAME = "supervision_state.json"

DEFAULT_MAX_RELAUNCH_COUNT = 5
DEFAULT_POLL_SECONDS = 60

ACTION_WAIT = "WAIT"
ACTION_RELAUNCH_RESUME = "RELAUNCH_RESUME"
ACTION_DONE = "DONE"
ACTION_STOP_FATAL = "STOP_FATAL"
ACTION_STOP_LIMIT = "STOP_LIMIT"

_TERMINAL_STATUSES = frozenset({"failed", "fatal_stop"})


class SupervisorError(ValueError):
    pass


ProcessAliveProbe = Callable[[int], bool]


@dataclass(frozen=True, slots=True)
class CoordinatorPidRecord:
    schema_version: str
    run_id: str
    pid: int
    recorded_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SupervisionStateRecord:
    schema_version: str
    run_id: str
    artifact_dir: str
    coordinator_pid: int | None
    poll_count: int
    relaunch_count: int
    last_decision: dict[str, Any]
    last_error: str
    updated_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SupervisionDecision:
    action: str
    reason: str
    coordinator_status: str
    next_cycle_due_at_utc: str
    overdue: bool
    process_alive: bool
    relaunch_count: int
    max_relaunch_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SupervisionResult:
    schema_version: str
    status: str
    artifact_dir: str
    relaunch_count: int
    max_relaunch_count: int
    polls: int
    final_coordinator_status: str
    decisions: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_ts(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def default_process_alive_probe(pid: int) -> bool:
    """Return True when ``pid`` appears to be a live OS process."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def probe_process_alive(
    pid: int,
    *,
    probe_fn: ProcessAliveProbe | None = None,
) -> bool:
    probe = probe_fn or default_process_alive_probe
    return probe(pid)


def _coordinator_pid_path(artifact_dir: Path) -> Path:
    return artifact_dir / COORDINATOR_PID_FILENAME


def _supervision_state_path(artifact_dir: Path) -> Path:
    return artifact_dir / SUPERVISION_STATE_FILENAME


def read_coordinator_pid_record(artifact_dir: Path) -> CoordinatorPidRecord | None:
    path = _coordinator_pid_path(artifact_dir)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CoordinatorPidRecord(
        schema_version=str(payload.get("schema_version", "")),
        run_id=str(payload.get("run_id", "")),
        pid=int(payload["pid"]),
        recorded_at_utc=str(payload.get("recorded_at_utc", "")),
    )


def write_coordinator_pid_record(
    artifact_dir: Path,
    *,
    pid: int,
    run_id: str,
    recorded_at_utc: str | None = None,
) -> CoordinatorPidRecord:
    if pid <= 0:
        raise SupervisorError("coordinator pid must be positive")
    record = CoordinatorPidRecord(
        schema_version=COORDINATOR_PID_SCHEMA,
        run_id=run_id,
        pid=pid,
        recorded_at_utc=recorded_at_utc
        or _now_utc().isoformat().replace("+00:00", "Z"),
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _coordinator_pid_path(artifact_dir).write_text(
        json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=True),
        encoding="utf-8",
    )
    return record


def read_supervision_state(artifact_dir: Path) -> SupervisionStateRecord | None:
    path = _supervision_state_path(artifact_dir)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    coordinator_pid = payload.get("coordinator_pid")
    return SupervisionStateRecord(
        schema_version=str(payload.get("schema_version", "")),
        run_id=str(payload.get("run_id", "")),
        artifact_dir=str(payload.get("artifact_dir", "")),
        coordinator_pid=(int(coordinator_pid) if coordinator_pid is not None else None),
        poll_count=int(payload.get("poll_count", 0)),
        relaunch_count=int(payload.get("relaunch_count", 0)),
        last_decision=dict(payload.get("last_decision", {})),
        last_error=str(payload.get("last_error", "")),
        updated_at_utc=str(payload.get("updated_at_utc", "")),
    )


def write_supervision_state(
    artifact_dir: Path,
    *,
    run_id: str,
    coordinator_pid: int | None,
    poll_count: int,
    relaunch_count: int,
    last_decision: Mapping[str, Any],
    last_error: str = "",
    updated_at_utc: str | None = None,
) -> SupervisionStateRecord:
    record = SupervisionStateRecord(
        schema_version=SUPERVISION_STATE_SCHEMA,
        run_id=run_id,
        artifact_dir=str(artifact_dir.resolve()),
        coordinator_pid=coordinator_pid,
        poll_count=poll_count,
        relaunch_count=relaunch_count,
        last_decision=dict(last_decision),
        last_error=last_error,
        updated_at_utc=updated_at_utc or _now_utc().isoformat().replace("+00:00", "Z"),
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _supervision_state_path(artifact_dir).write_text(
        json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=True),
        encoding="utf-8",
    )
    return record


def resolve_coordinator_process_alive(
    artifact_dir: Path,
    *,
    probe_fn: ProcessAliveProbe | None = None,
    assume_process_alive: bool | None = None,
) -> tuple[bool, str]:
    """Resolve coordinator liveness from explicit assumption or PID record."""
    if assume_process_alive is not None:
        return assume_process_alive, "assumed_process_alive"

    pid_record = read_coordinator_pid_record(artifact_dir)
    if pid_record is None:
        return False, "missing_coordinator_pid_record"

    state = _read_runner_state(artifact_dir)
    if state is not None and pid_record.run_id and pid_record.run_id != state.run_id:
        return False, "stale_coordinator_pid_run_id_mismatch"

    alive = probe_process_alive(pid_record.pid, probe_fn=probe_fn)
    if alive:
        return True, "coordinator_pid_alive"
    return False, "coordinator_pid_not_alive"


def decide_supervision(
    state: RunnerState | None,
    events: Sequence[Mapping[str, Any]],
    now: datetime,
    process_alive: bool,
    relaunch_count: int,
    max_relaunch_count: int,
) -> SupervisionDecision:
    """Pure decision: what should the supervisor do given durable evidence."""
    coordinator_status = str(state.coordinator_status) if state else ""
    next_due = str(state.next_cycle_due_at_utc) if state else ""

    has_final_completed = any(
        str(event.get("event_type", "")) == "final_validation_completed"
        for event in events
    )

    due_at = _parse_ts(next_due)
    if due_at is not None:
        overdue = now > due_at
    else:
        overdue = coordinator_status == "sleeping"

    def build(action: str, reason: str) -> SupervisionDecision:
        return SupervisionDecision(
            action=action,
            reason=reason,
            coordinator_status=coordinator_status,
            next_cycle_due_at_utc=next_due,
            overdue=overdue,
            process_alive=process_alive,
            relaunch_count=relaunch_count,
            max_relaunch_count=max_relaunch_count,
        )

    if coordinator_status == "completed" or has_final_completed:
        return build(ACTION_DONE, "run reached completion")
    if coordinator_status in _TERMINAL_STATUSES:
        return build(
            ACTION_STOP_FATAL,
            f"terminal coordinator_status={coordinator_status!r}",
        )

    last_type = str(events[-1].get("event_type", "")).strip() if events else ""
    stalled_sleep = coordinator_status == "sleeping" and last_type == "sleep_started"

    if stalled_sleep and overdue and not process_alive:
        if relaunch_count >= max_relaunch_count:
            return build(ACTION_STOP_LIMIT, "relaunch budget exhausted")
        return build(
            ACTION_RELAUNCH_RESUME,
            "stalled sleep past next_cycle_due_at_utc with dead process",
        )

    if process_alive:
        return build(ACTION_WAIT, "coordinator process alive")
    return build(ACTION_WAIT, "no relaunch condition met")


def _build_result(
    status: str,
    artifact_dir: Path,
    relaunch_count: int,
    max_relaunch_count: int,
    polls: int,
    decisions: list[dict[str, Any]],
    state: RunnerState | None,
) -> SupervisionResult:
    return SupervisionResult(
        schema_version=SUPERVISION_SCHEMA,
        status=status,
        artifact_dir=str(artifact_dir),
        relaunch_count=relaunch_count,
        max_relaunch_count=max_relaunch_count,
        polls=polls,
        final_coordinator_status=(str(state.coordinator_status) if state else ""),
        decisions=tuple(decisions),
    )


def supervise_loop(
    *,
    artifact_dir: Path,
    launcher: Callable[[], CoordinatorSummary],
    process_alive_fn: Callable[[], bool],
    now_fn: Callable[[], datetime] = _now_utc,
    sleep_fn: Callable[[float], None] = time.sleep,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    max_relaunch_count: int = DEFAULT_MAX_RELAUNCH_COUNT,
    max_polls: int | None = None,
    initial_relaunch_count: int = 0,
    on_poll: Callable[[SupervisionDecision, int, int], None] | None = None,
) -> SupervisionResult:
    """Poll durable state and relaunch the coordinator in resume mode on stall.

    Fully injectable for deterministic tests: ``launcher`` performs the resume
    (default binds ``run_fixture_window(resume=True)``), ``process_alive_fn``
    reports coordinator liveness, and ``sleep_fn``/``now_fn`` control timing.
    """
    if poll_seconds < 0:
        raise SupervisorError("poll_seconds must be >= 0")
    if max_relaunch_count < 0:
        raise SupervisorError("max_relaunch_count must be >= 0")
    if initial_relaunch_count < 0:
        raise SupervisorError("initial_relaunch_count must be >= 0")

    relaunch_count = initial_relaunch_count
    polls = 0
    decisions: list[dict[str, Any]] = []

    while True:
        state = _read_runner_state(artifact_dir)
        events = _read_coordinator_events(artifact_dir)
        decision = decide_supervision(
            state,
            events,
            now_fn(),
            process_alive_fn(),
            relaunch_count,
            max_relaunch_count,
        )
        decisions.append(decision.to_dict())
        if on_poll is not None:
            on_poll(decision, polls, relaunch_count)

        if decision.action == ACTION_DONE:
            return _build_result(
                "DONE",
                artifact_dir,
                relaunch_count,
                max_relaunch_count,
                polls,
                decisions,
                state,
            )
        if decision.action == ACTION_STOP_FATAL:
            return _build_result(
                "STOP_FATAL",
                artifact_dir,
                relaunch_count,
                max_relaunch_count,
                polls,
                decisions,
                state,
            )
        if decision.action == ACTION_STOP_LIMIT:
            return _build_result(
                "STOP_LIMIT",
                artifact_dir,
                relaunch_count,
                max_relaunch_count,
                polls,
                decisions,
                state,
            )
        if decision.action == ACTION_RELAUNCH_RESUME:
            relaunch_count += 1
            launcher()
            continue

        polls += 1
        if max_polls is not None and polls >= max_polls:
            return _build_result(
                "WAIT_TIMEOUT",
                artifact_dir,
                relaunch_count,
                max_relaunch_count,
                polls,
                decisions,
                state,
            )
        if poll_seconds:
            sleep_fn(poll_seconds)


def _resume_launcher(
    *,
    repo_root: Path,
    fixture_path: Path,
    artifact_dir: Path,
    iterations: int,
    cadence_seconds: int,
    max_restart_count: int,
    restart_backoff_seconds: int,
) -> Callable[[], CoordinatorSummary]:
    def _launch() -> CoordinatorSummary:
        return run_fixture_window(
            repo_root=repo_root,
            fixture_path=fixture_path,
            artifact_dir=artifact_dir,
            iterations=iterations,
            cadence_seconds=cadence_seconds,
            max_restart_count=max_restart_count,
            restart_backoff_seconds=restart_backoff_seconds,
            resume=True,
        )

    return _launch


def build_subprocess_resume_launcher(
    *,
    repo_root: Path,
    fixture_path: Path,
    artifact_dir: Path,
    iterations: int,
    cadence_seconds: int,
    max_restart_count: int,
    restart_backoff_seconds: int,
    python_executable: str | None = None,
    popen_fn: Callable[..., Any] | None = None,
    write_pid: bool = True,
) -> Callable[[], CoordinatorSummary]:
    """Spawn ``resume-fixture-window`` as a detached subprocess resume launcher."""

    def _launch() -> CoordinatorSummary:
        executable = python_executable or sys.executable
        cmd = [
            executable,
            "-m",
            "tools.evidence_harvester.coordinator",
            "resume-fixture-window",
            "--fixture",
            str(fixture_path),
            "--artifact-dir",
            str(artifact_dir),
            "--iterations",
            str(iterations),
            "--cadence-seconds",
            str(cadence_seconds),
            "--max-restart-count",
            str(max_restart_count),
            "--restart-backoff-seconds",
            str(restart_backoff_seconds),
        ]
        popen = popen_fn or subprocess.Popen
        proc = popen(
            cmd,
            cwd=str(repo_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        state = _read_runner_state(artifact_dir)
        run_id = state.run_id if state is not None else artifact_dir.name
        if write_pid:
            write_coordinator_pid_record(artifact_dir, pid=proc.pid, run_id=run_id)
        return CoordinatorSummary(
            status="LAUNCHED",
            artifact_dir=str(artifact_dir),
            completed_cycles=state.total_cycles_completed if state else 0,
            recovery_events_written=0,
            restart_count=0,
            max_restart_count=max_restart_count,
            final_validation_started=False,
            stop_reason="external_subprocess_resume_launch",
        )

    return _launch


def _external_supervision_plan(
    *,
    artifact_dir: Path,
    fixture_path: Path,
    iterations: int,
    cadence_seconds: int,
    max_restart_count: int,
    restart_backoff_seconds: int,
    max_relaunch_count: int,
    poll_seconds: int,
    explicit: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SUPERVISION_SCHEMA,
        "mode": "supervise-external",
        "artifact_dir": str(artifact_dir),
        "fixture": str(fixture_path),
        "iterations": iterations,
        "cadence_seconds": cadence_seconds,
        "max_restart_count": max_restart_count,
        "restart_backoff_seconds": restart_backoff_seconds,
        "max_relaunch_count": max_relaunch_count,
        "poll_seconds": poll_seconds,
        "explicit": explicit,
        "pid_record_path": str(_coordinator_pid_path(artifact_dir)),
        "supervision_state_path": str(_supervision_state_path(artifact_dir)),
        "safety": "dry/fixture only; LR NO-GO; no Live-Go; no Echtgeld-Go",
    }


def _make_supervision_state_writer(
    artifact_dir: Path,
) -> Callable[[SupervisionDecision, int, int], None]:
    def _write(decision: SupervisionDecision, polls: int, relaunch_count: int) -> None:
        state = _read_runner_state(artifact_dir)
        pid_record = read_coordinator_pid_record(artifact_dir)
        run_id = state.run_id if state is not None else artifact_dir.name
        pid = pid_record.pid if pid_record is not None else None
        _, liveness_reason = resolve_coordinator_process_alive(artifact_dir)
        last_error = (
            liveness_reason
            if liveness_reason == "stale_coordinator_pid_run_id_mismatch"
            else ""
        )
        write_supervision_state(
            artifact_dir,
            run_id=run_id,
            coordinator_pid=pid,
            poll_count=polls,
            relaunch_count=relaunch_count,
            last_decision=decision.to_dict(),
            last_error=last_error,
        )

    return _write


def _format_json(payload: Mapping[str, Any], pretty: bool) -> str:
    return json.dumps(
        payload,
        indent=2 if pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )


def _emit(payload: Mapping[str, Any], pretty: bool) -> None:
    print(_format_json(payload, pretty))


def _cmd_status(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    state = _read_runner_state(artifact_dir)
    events = _read_coordinator_events(artifact_dir)
    if args.use_pid_probe:
        process_alive, liveness_reason = resolve_coordinator_process_alive(artifact_dir)
        assumed_process_alive = None
    else:
        process_alive = bool(args.assume_process_alive)
        liveness_reason = "assumed_process_alive"
        assumed_process_alive = process_alive
    persisted = read_supervision_state(artifact_dir)
    decision = decide_supervision(
        state,
        events,
        _now_utc(),
        process_alive,
        relaunch_count=(persisted.relaunch_count if persisted is not None else 0),
        max_relaunch_count=args.max_relaunch_count,
    )
    payload = {
        "schema_version": SUPERVISION_SCHEMA,
        "mode": "status",
        "artifact_dir": str(artifact_dir),
        "use_pid_probe": bool(args.use_pid_probe),
        "assumed_process_alive": assumed_process_alive,
        "liveness_reason": liveness_reason,
        "supervision_state": (persisted.to_dict() if persisted is not None else None),
        "decision": decision.to_dict(),
    }
    _emit(payload, args.pretty)
    return 0


def _cmd_plan_external(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    fixture_path = args.fixture.resolve()
    plan = _external_supervision_plan(
        artifact_dir=artifact_dir,
        fixture_path=fixture_path,
        iterations=args.iterations,
        cadence_seconds=args.cadence_seconds,
        max_restart_count=args.max_restart_count,
        restart_backoff_seconds=args.restart_backoff_seconds,
        max_relaunch_count=args.max_relaunch_count,
        poll_seconds=args.poll_seconds,
        explicit=bool(args.explicit),
    )
    plan["status"] = "planned"
    plan["note"] = (
        "External out-of-process supervision scaffold (#3733). Re-run "
        "supervise-external with --explicit only under Operator Runtime-GO."
    )
    _emit(plan, args.pretty)
    return 0


def _cmd_record_coordinator_pid(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    state = _read_runner_state(artifact_dir)
    if state is None:
        raise SupervisorError(
            "record-coordinator-pid requires runner_state.json in artifact dir"
        )
    record = write_coordinator_pid_record(
        artifact_dir,
        pid=args.pid,
        run_id=state.run_id,
        recorded_at_utc=args.recorded_at_utc,
    )
    payload = {
        "schema_version": SUPERVISION_SCHEMA,
        "mode": "record-coordinator-pid",
        "record": record.to_dict(),
    }
    _emit(payload, args.pretty)
    return 0


def _cmd_supervise_external(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    fixture_path = args.fixture.resolve()
    plan = _external_supervision_plan(
        artifact_dir=artifact_dir,
        fixture_path=fixture_path,
        iterations=args.iterations,
        cadence_seconds=args.cadence_seconds,
        max_restart_count=args.max_restart_count,
        restart_backoff_seconds=args.restart_backoff_seconds,
        max_relaunch_count=args.max_relaunch_count,
        poll_seconds=args.poll_seconds,
        explicit=bool(args.explicit),
    )
    if not args.explicit:
        plan["status"] = "planned"
        plan["note"] = "Re-run with --explicit to execute external supervision."
        _emit(plan, args.pretty)
        return 0

    if not fixture_path.exists():
        raise SupervisorError(f"fixture path does not exist: {fixture_path}")
    if _read_runner_state(artifact_dir) is None:
        raise SupervisorError(
            "supervise-external --explicit requires an existing run to resume"
        )

    persisted = read_supervision_state(artifact_dir)
    launcher = build_subprocess_resume_launcher(
        repo_root=_repo_root(),
        fixture_path=fixture_path,
        artifact_dir=artifact_dir,
        iterations=args.iterations,
        cadence_seconds=args.cadence_seconds,
        max_restart_count=args.max_restart_count,
        restart_backoff_seconds=args.restart_backoff_seconds,
        python_executable=args.python_executable,
    )
    result = supervise_loop(
        artifact_dir=artifact_dir,
        launcher=launcher,
        process_alive_fn=lambda: resolve_coordinator_process_alive(artifact_dir)[0],
        poll_seconds=args.poll_seconds,
        max_relaunch_count=args.max_relaunch_count,
        max_polls=args.max_polls,
        initial_relaunch_count=(
            persisted.relaunch_count if persisted is not None else 0
        ),
        on_poll=_make_supervision_state_writer(artifact_dir),
    )
    payload = result.to_dict()
    payload["mode"] = "supervise-external"
    _emit(payload, args.pretty)
    return 0 if result.status in ("DONE", "WAIT_TIMEOUT") else 1


def _cmd_supervise(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact_dir.resolve()
    fixture_path = args.fixture.resolve()
    plan = {
        "schema_version": SUPERVISION_SCHEMA,
        "mode": "supervise",
        "artifact_dir": str(artifact_dir),
        "fixture": str(fixture_path),
        "iterations": args.iterations,
        "cadence_seconds": args.cadence_seconds,
        "max_relaunch_count": args.max_relaunch_count,
        "poll_seconds": args.poll_seconds,
        "explicit": bool(args.explicit),
        "safety": "dry/fixture only; LR NO-GO; no Live-Go; no Echtgeld-Go",
    }
    if not args.explicit:
        plan["status"] = "planned"
        plan["note"] = (
            "Re-run with --explicit to execute in-process resume supervision."
        )
        _emit(plan, args.pretty)
        return 0

    if not fixture_path.exists():
        raise SupervisorError(f"fixture path does not exist: {fixture_path}")
    if _read_runner_state(artifact_dir) is None:
        raise SupervisorError(
            "supervise --explicit requires an existing run to resume; start it "
            "first with 'coordinator run-fixture-window'"
        )

    launcher = _resume_launcher(
        repo_root=_repo_root(),
        fixture_path=fixture_path,
        artifact_dir=artifact_dir,
        iterations=args.iterations,
        cadence_seconds=args.cadence_seconds,
        max_restart_count=args.max_restart_count,
        restart_backoff_seconds=args.restart_backoff_seconds,
    )
    result = supervise_loop(
        artifact_dir=artifact_dir,
        launcher=launcher,
        process_alive_fn=lambda: False,
        poll_seconds=args.poll_seconds,
        max_relaunch_count=args.max_relaunch_count,
        max_polls=args.max_polls,
    )
    _emit(result.to_dict(), args.pretty)
    return 0 if result.status in ("DONE", "WAIT_TIMEOUT") else 1


def _add_external_supervision_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--cadence-seconds", type=int, default=DEFAULT_CADENCE_SECONDS)
    parser.add_argument(
        "--max-restart-count", type=int, default=DEFAULT_MAX_RESTART_COUNT
    )
    parser.add_argument(
        "--restart-backoff-seconds",
        type=int,
        default=DEFAULT_RESTART_BACKOFF_SECONDS,
    )
    parser.add_argument(
        "--max-relaunch-count", type=int, default=DEFAULT_MAX_RELAUNCH_COUNT
    )
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--max-polls", type=int, default=None)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evidence harvester sleep-stall supervisor (resume-mode relaunch)."
        )
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status",
        help="Read-only supervision decision for an artifact dir.",
    )
    status_parser.add_argument("--artifact-dir", type=Path, required=True)
    status_parser.add_argument(
        "--assume-process-alive",
        action="store_true",
        help="Assume the coordinator process is alive (default: assume dead).",
    )
    status_parser.add_argument(
        "--max-relaunch-count",
        type=int,
        default=DEFAULT_MAX_RELAUNCH_COUNT,
    )
    status_parser.add_argument(
        "--use-pid-probe",
        action="store_true",
        help="Resolve coordinator liveness from coordinator_pid.json.",
    )

    plan_external_parser = subparsers.add_parser(
        "plan-external",
        help="Safe plan for external out-of-process supervision (#3733).",
    )
    _add_external_supervision_args(plan_external_parser)
    plan_external_parser.add_argument(
        "--explicit",
        action="store_true",
        help="Echo explicit flag in plan payload only; does not execute.",
    )

    record_pid_parser = subparsers.add_parser(
        "record-coordinator-pid",
        help="Record coordinator PID for external liveness probing.",
    )
    record_pid_parser.add_argument("--artifact-dir", type=Path, required=True)
    record_pid_parser.add_argument("--pid", type=int, required=True)
    record_pid_parser.add_argument("--recorded-at-utc", type=str, default=None)

    external_parser = subparsers.add_parser(
        "supervise-external",
        help=(
            "Out-of-process supervision with PID probe and subprocess resume "
            "(fail-closed behind --explicit)."
        ),
    )
    _add_external_supervision_args(external_parser)
    external_parser.add_argument(
        "--python-executable",
        type=str,
        default=None,
        help="Python executable for detached resume subprocess.",
    )
    external_parser.add_argument(
        "--explicit",
        action="store_true",
        help="Required to execute external supervision.",
    )

    supervise_parser = subparsers.add_parser(
        "supervise",
        help=(
            "Resume-supervise an existing run in-process (fail-closed behind "
            "--explicit)."
        ),
    )
    supervise_parser.add_argument("--artifact-dir", type=Path, required=True)
    supervise_parser.add_argument("--fixture", type=Path, required=True)
    supervise_parser.add_argument("--iterations", type=int, required=True)
    supervise_parser.add_argument(
        "--cadence-seconds", type=int, default=DEFAULT_CADENCE_SECONDS
    )
    supervise_parser.add_argument(
        "--max-restart-count", type=int, default=DEFAULT_MAX_RESTART_COUNT
    )
    supervise_parser.add_argument(
        "--restart-backoff-seconds",
        type=int,
        default=DEFAULT_RESTART_BACKOFF_SECONDS,
    )
    supervise_parser.add_argument(
        "--max-relaunch-count", type=int, default=DEFAULT_MAX_RELAUNCH_COUNT
    )
    supervise_parser.add_argument(
        "--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS
    )
    supervise_parser.add_argument("--max-polls", type=int, default=None)
    supervise_parser.add_argument(
        "--explicit",
        action="store_true",
        help="Required to actually run supervision; otherwise prints the plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "plan-external":
        return _cmd_plan_external(args)
    if args.command == "record-coordinator-pid":
        return _cmd_record_coordinator_pid(args)
    if args.command == "supervise-external":
        return _cmd_supervise_external(args)
    if args.command == "supervise":
        return _cmd_supervise(args)
    raise SupervisorError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
