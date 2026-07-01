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

Boundaries: dry/fixture research only. LR NO-GO. No Live-Go, no Echtgeld-Go.
"""

from __future__ import annotations

import argparse
import json
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

    relaunch_count = 0
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

        if decision.action == ACTION_DONE:
            return _build_result(
                "DONE", artifact_dir, relaunch_count,
                max_relaunch_count, polls, decisions, state,
            )
        if decision.action == ACTION_STOP_FATAL:
            return _build_result(
                "STOP_FATAL", artifact_dir, relaunch_count,
                max_relaunch_count, polls, decisions, state,
            )
        if decision.action == ACTION_STOP_LIMIT:
            return _build_result(
                "STOP_LIMIT", artifact_dir, relaunch_count,
                max_relaunch_count, polls, decisions, state,
            )
        if decision.action == ACTION_RELAUNCH_RESUME:
            relaunch_count += 1
            launcher()
            continue

        polls += 1
        if max_polls is not None and polls >= max_polls:
            return _build_result(
                "WAIT_TIMEOUT", artifact_dir, relaunch_count,
                max_relaunch_count, polls, decisions, state,
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
    process_alive = bool(args.assume_process_alive)
    decision = decide_supervision(
        state,
        events,
        _now_utc(),
        process_alive,
        relaunch_count=0,
        max_relaunch_count=args.max_relaunch_count,
    )
    payload = {
        "schema_version": SUPERVISION_SCHEMA,
        "mode": "status",
        "artifact_dir": str(artifact_dir),
        "assumed_process_alive": process_alive,
        "decision": decision.to_dict(),
    }
    _emit(payload, args.pretty)
    return 0


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
        plan["note"] = "Re-run with --explicit to execute in-process resume supervision."
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
    if args.command == "supervise":
        return _cmd_supervise(args)
    raise SupervisorError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
