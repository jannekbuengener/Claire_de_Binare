from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from core.utils.clock import utcnow as cdb_utcnow

from .alerts import alert_report_to_markdown, build_alert_report
from .collector import EvidenceHarvesterCollector
from .models import CollectorInput, CollectorValidationError
from .snapshot import build_snapshot, snapshot_to_markdown

HEARTBEAT_SCHEMA = "cdb.evidence_harvester.runner_heartbeat.v1"
STATE_SCHEMA = "cdb.evidence_harvester.runner_state.v1"
SAFETY_BANNER = "Paper/research evidence only; no LR-Go, no Live-Go, no Echtgeld-Go."


class RunnerError(ValueError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_output_dir() -> Path:
    return _repo_root() / "artifacts" / "evidence_harvester" / "runner"


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now_utc() -> datetime:
    now = cdb_utcnow()
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RunnerError(f"Failed to read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RunnerError(f"{path.name} JSON root must be an object")
    return payload


def _format_json(payload: Mapping[str, Any], pretty: bool) -> str:
    return json.dumps(
        payload,
        indent=2 if pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )


def _emit(payload: Mapping[str, Any], pretty: bool) -> None:
    print(_format_json(payload, pretty))


def _resolve_output_dir(path: Path | None) -> Path:
    return (path or _default_output_dir()).resolve()


@dataclass(frozen=True, slots=True)
class RunnerHeartbeat:
    schema_version: str = HEARTBEAT_SCHEMA
    runner_mode: str = ""
    iteration: int = 0
    started_at_utc: str = ""
    current_run_at_utc: str = ""
    last_success_at_utc: str = ""
    last_failure_at_utc: str = ""
    last_error: str = ""
    last_collector_report: str = ""
    last_snapshot_json: str = ""
    last_snapshot_markdown: str = ""
    last_alert_json: str = ""
    last_alert_markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RunnerState:
    schema_version: str = STATE_SCHEMA
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_cycle_verdict: str = ""
    last_cycle_ended_at_utc: str = ""
    run_id: str = ""
    total_cycles_started: int = 0
    total_cycles_completed: int = 0
    total_successful_cycles: int = 0
    total_failed_cycles: int = 0
    last_cycle_started_at_utc: str = ""
    next_cycle_due_at_utc: str = ""
    last_successful_artifact_stamp: str = ""
    coordinator_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build_heartbeat(
    mode: str,
    iteration: int,
    started_at: datetime,
    current_run_at: datetime,
    last_success_at: datetime | None = None,
    last_failure_at: datetime | None = None,
    last_error: str = "",
    last_collector_report: str = "",
    last_snapshot_json: str = "",
    last_snapshot_markdown: str = "",
    last_alert_json: str = "",
    last_alert_markdown: str = "",
) -> RunnerHeartbeat:
    return RunnerHeartbeat(
        runner_mode=mode,
        iteration=iteration,
        started_at_utc=_format_ts(started_at),
        current_run_at_utc=_format_ts(current_run_at),
        last_success_at_utc=_format_ts(last_success_at) if last_success_at else "",
        last_failure_at_utc=_format_ts(last_failure_at) if last_failure_at else "",
        last_error=last_error,
        last_collector_report=last_collector_report,
        last_snapshot_json=last_snapshot_json,
        last_snapshot_markdown=last_snapshot_markdown,
        last_alert_json=last_alert_json,
        last_alert_markdown=last_alert_markdown,
    )


def _run_complete_cycle(
    fixture_path: Path,
    output_dir: Path,
    generated_at_utc: str | None,
    pretty: bool,
    iteration: int,
    started_at: datetime,
    existing_heartbeat: RunnerHeartbeat | None,
    mode: str = "run-once-fixture",
) -> tuple[RunnerHeartbeat, RunnerState]:
    prior_state = _read_state(output_dir)
    raw_input = _load_json(fixture_path)
    raw_input.setdefault("stale_after_minutes", 120)
    collector_input = CollectorInput.from_mapping(raw_input)
    report = EvidenceHarvesterCollector(
        stale_after_minutes=collector_input.stale_after_minutes,
    ).collect(collector_input)
    snapshot = build_snapshot(report.to_dict(), generated_at_utc=generated_at_utc)
    snapshot_payload = snapshot.to_dict()
    stamp = (
        snapshot_payload["metadata"]["generated_at_utc"]
        .replace("-", "")
        .replace(":", "")
    )

    collector_report_path = output_dir / f"collector_report_{stamp}.json"
    snapshot_json_path = output_dir / f"snapshot_{stamp}.json"
    snapshot_markdown_path = output_dir / f"snapshot_{stamp}.md"

    output_dir.mkdir(parents=True, exist_ok=True)
    collector_report_path.write_text(
        _format_json(report.to_dict(), pretty) + "\n", encoding="utf-8"
    )
    snapshot_json_path.write_text(
        _format_json(snapshot_payload, pretty) + "\n", encoding="utf-8"
    )
    snapshot_markdown_path.write_text(snapshot_to_markdown(snapshot), encoding="utf-8")

    alert_report = build_alert_report(
        snapshot_payload,
        evaluated_at_utc=snapshot_payload["metadata"]["generated_at_utc"],
    )
    alert_payload = alert_report.to_dict()
    alert_json_path = output_dir / f"alert_{stamp}.json"
    alert_markdown_path = output_dir / f"alert_{stamp}.md"
    alert_json_path.write_text(
        _format_json(alert_payload, pretty) + "\n", encoding="utf-8"
    )
    alert_markdown_path.write_text(
        alert_report_to_markdown(alert_report), encoding="utf-8"
    )

    now = _now_utc()
    heartbeat = _build_heartbeat(
        mode=mode,
        iteration=iteration,
        started_at=started_at,
        current_run_at=now,
        last_success_at=now,
        last_collector_report=str(collector_report_path),
        last_snapshot_json=str(snapshot_json_path),
        last_snapshot_markdown=str(snapshot_markdown_path),
        last_alert_json=str(alert_json_path),
        last_alert_markdown=str(alert_markdown_path),
    )
    state = RunnerState(
        total_runs=(prior_state.total_runs if prior_state else 0) + 1,
        successful_runs=(prior_state.successful_runs if prior_state else 0) + 1,
        failed_runs=prior_state.failed_runs if prior_state else 0,
        last_cycle_verdict="PASS",
        last_cycle_ended_at_utc=_format_ts(now),
        run_id=prior_state.run_id if prior_state else "",
        total_cycles_started=(prior_state.total_cycles_started if prior_state else 0),
        total_cycles_completed=(
            prior_state.total_cycles_completed if prior_state else 0
        ),
        total_successful_cycles=(
            prior_state.total_successful_cycles if prior_state else 0
        ),
        total_failed_cycles=prior_state.total_failed_cycles if prior_state else 0,
        last_cycle_started_at_utc=(
            prior_state.last_cycle_started_at_utc if prior_state else ""
        ),
        next_cycle_due_at_utc=(
            prior_state.next_cycle_due_at_utc if prior_state else ""
        ),
        last_successful_artifact_stamp=(
            prior_state.last_successful_artifact_stamp if prior_state else ""
        ),
        coordinator_status=prior_state.coordinator_status if prior_state else "",
    )

    _write_heartbeat(output_dir, heartbeat, pretty)
    _write_state(output_dir, state, pretty)

    return heartbeat, state


def _write_heartbeat(
    output_dir: Path, heartbeat: RunnerHeartbeat, pretty: bool
) -> Path:
    path = output_dir / "runner_heartbeat.json"
    path.write_text(_format_json(heartbeat.to_dict(), pretty) + "\n", encoding="utf-8")
    return path


def _write_state(output_dir: Path, state: RunnerState, pretty: bool) -> Path:
    path = output_dir / "runner_state.json"
    path.write_text(_format_json(state.to_dict(), pretty) + "\n", encoding="utf-8")
    return path


def _read_heartbeat(output_dir: Path) -> RunnerHeartbeat | None:
    path = output_dir / "runner_heartbeat.json"
    if not path.exists():
        return None
    payload = _load_json(path)
    return RunnerHeartbeat(
        **{k: payload.get(k, "") for k in RunnerHeartbeat.__dataclass_fields__}
    )


def _read_state(output_dir: Path) -> RunnerState | None:
    path = output_dir / "runner_state.json"
    if not path.exists():
        return None
    payload = _load_json(path)
    return RunnerState(
        **{k: payload.get(k, 0) for k in RunnerState.__dataclass_fields__}
    )


def plan_command(args: argparse.Namespace) -> int:
    fixture = args.fixture
    if fixture is not None:
        resolved = fixture.resolve()
        if not resolved.exists():
            raise RunnerError(f"fixture path does not exist: {resolved}")
    output_dir = _resolve_output_dir(args.output_dir)
    payload = {
        "mode": "plan",
        "default_mode": "dry-run",
        "fixture": str(fixture) if fixture else None,
        "output_dir": str(output_dir),
        "available_commands": [
            "plan",
            "status",
            "run-once-fixture",
            "loop-fixture",
        ],
        "artifacts": {
            "collector_report": "collector_report_<stamp>.json",
            "snapshot_json": "snapshot_<stamp>.json",
            "snapshot_markdown": "snapshot_<stamp>.md",
            "alert_json": "alert_<stamp>.json",
            "alert_markdown": "alert_<stamp>.md",
            "heartbeat": "runner_heartbeat.json",
            "state": "runner_state.json",
        },
        "safety": [
            "default-off; plan-only by default",
            "no Docker or runtime start",
            "no DB execution or mutation",
            "no secrets",
            "no Redis live read/write",
            "no LR-Go / no Live-Go / no Echtgeld-Go",
        ],
    }
    _emit(payload, args.pretty)
    return 0


def status_command(args: argparse.Namespace) -> int:
    output_dir = _resolve_output_dir(args.output_dir)
    heartbeat = None
    state = None
    artifact_count = 0
    if output_dir.exists():
        heartbeat = _read_heartbeat(output_dir)
        state = _read_state(output_dir)
        artifact_count = len(list(output_dir.glob("*.json"))) + len(
            list(output_dir.glob("*.md"))
        )
    payload = {
        "mode": "status",
        "output_dir": str(output_dir),
        "artifact_dir_exists": output_dir.exists(),
        "artifact_count": artifact_count,
        "heartbeat": heartbeat.to_dict() if heartbeat else None,
        "state": state.to_dict() if state else None,
        "safety": [
            "status is derived from local artifacts only",
            "no Docker/runtime/DB/Redis/secrets access",
        ],
    }
    _emit(payload, args.pretty)
    return 0


def run_once_fixture_command(args: argparse.Namespace) -> int:
    fixture = args.fixture.resolve()
    if not fixture.exists():
        raise RunnerError(f"fixture path does not exist: {fixture}")
    output_dir = _resolve_output_dir(args.output_dir)
    now = _now_utc()

    heartbeat, state = _run_complete_cycle(
        fixture_path=fixture,
        output_dir=output_dir,
        generated_at_utc=args.generated_at_utc,
        pretty=args.pretty,
        iteration=0,
        started_at=now,
        existing_heartbeat=None,
        mode="run-once-fixture",
    )

    payload = {
        "mode": "run-once-fixture",
        "output_dir": str(output_dir),
        "heartbeat": heartbeat.to_dict(),
        "state": state.to_dict(),
        "safety": [
            "fixture-only run",
            "no scheduler autostart",
            "no Docker/runtime/DB/Redis/secrets access",
        ],
    }
    _emit(payload, args.pretty)
    return 0


def _loop_should_stop() -> bool:
    return hasattr(_loop_should_stop, "_stop") and _loop_should_stop._stop


def _handle_signal(signum: int, frame: object) -> None:
    _loop_should_stop._stop = True


def loop_fixture_command(args: argparse.Namespace) -> int:
    fixture = args.fixture.resolve()
    if not fixture.exists():
        raise RunnerError(f"fixture path does not exist: {fixture}")
    if args.iterations < 1:
        raise RunnerError("--iterations must be >= 1")
    if args.interval_seconds < 1:
        raise RunnerError("--interval-seconds must be >= 1")

    output_dir = _resolve_output_dir(args.output_dir)
    started_at = _now_utc()
    _loop_should_stop._stop = False
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    last_heartbeat: RunnerHeartbeat | None = None
    cumulative_state = RunnerState()
    iteration = 0

    for iteration in range(1, args.iterations + 1):
        if _loop_should_stop():
            break
        run_start = _now_utc()
        try:
            hb, st = _run_complete_cycle(
                fixture_path=fixture,
                output_dir=output_dir,
                generated_at_utc=args.generated_at_utc,
                pretty=args.pretty,
                iteration=iteration,
                started_at=started_at,
                existing_heartbeat=last_heartbeat,
                mode="loop-fixture",
            )
            last_heartbeat = hb
            cumulative_state = RunnerState(
                total_runs=cumulative_state.total_runs + 1,
                successful_runs=cumulative_state.successful_runs + 1,
                failed_runs=cumulative_state.failed_runs,
                last_cycle_verdict="PASS",
                last_cycle_ended_at_utc=_format_ts(run_start),
            )
            _write_state(output_dir, cumulative_state, args.pretty)
        except (CollectorValidationError, RunnerError, Exception) as exc:
            now = _now_utc()
            last_heartbeat = _build_heartbeat(
                mode="loop-fixture",
                iteration=iteration,
                started_at=started_at,
                current_run_at=now,
                last_failure_at=now,
                last_error=str(exc),
            )
            _write_heartbeat(output_dir, last_heartbeat, args.pretty)
            cumulative_state = RunnerState(
                total_runs=cumulative_state.total_runs + 1,
                successful_runs=cumulative_state.successful_runs,
                failed_runs=cumulative_state.failed_runs + 1,
                last_cycle_verdict="FAIL",
                last_cycle_ended_at_utc=_format_ts(now),
            )
            _write_state(output_dir, cumulative_state, args.pretty)
            raise

        if iteration < args.iterations and not _loop_should_stop():
            time.sleep(args.interval_seconds)

    final_heartbeat = _build_heartbeat(
        mode="loop-fixture",
        iteration=iteration,
        started_at=started_at,
        current_run_at=_now_utc(),
        last_success_at=_now_utc() if cumulative_state.successful_runs > 0 else None,
        last_collector_report=(
            last_heartbeat.last_collector_report if last_heartbeat else ""
        ),
        last_snapshot_json=(
            last_heartbeat.last_snapshot_json if last_heartbeat else ""
        ),
        last_snapshot_markdown=(
            last_heartbeat.last_snapshot_markdown if last_heartbeat else ""
        ),
        last_alert_json=last_heartbeat.last_alert_json if last_heartbeat else "",
        last_alert_markdown=(
            last_heartbeat.last_alert_markdown if last_heartbeat else ""
        ),
    )
    _write_heartbeat(output_dir, final_heartbeat, args.pretty)

    payload = {
        "mode": "loop-fixture",
        "output_dir": str(output_dir),
        "iterations_completed": cumulative_state.total_runs,
        "heartbeat": final_heartbeat.to_dict(),
        "state": cumulative_state.to_dict(),
        "stopped_by_signal": _loop_should_stop(),
        "safety": [
            "bounded fixture loop",
            "no scheduler autostart",
            "no Docker/runtime/DB/Redis/secrets access",
        ],
    }
    _emit(payload, args.pretty)
    return 0 if cumulative_state.failed_runs == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv or [])
    if not argv:
        argv = ["plan"]

    parser = argparse.ArgumentParser(
        description="Managed evidence harvester runner (fixture / dry-run modes)."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser(
        "plan", help="Print the safe dry-run plan without running anything."
    )
    plan_parser.add_argument(
        "--fixture",
        type=Path,
        help="Optional fixture path for plan context.",
    )
    plan_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for artifacts.",
    )
    plan_parser.set_defaults(handler=plan_command)

    status_parser = subparsers.add_parser(
        "status", help="Report local artifact-based runner status."
    )
    status_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory to check.",
    )
    status_parser.set_defaults(handler=status_command)

    run_once_parser = subparsers.add_parser(
        "run-once-fixture",
        help="Run one complete collector+snapshot+alert cycle from a fixture.",
    )
    run_once_parser.add_argument(
        "--fixture", type=Path, required=True, help="Collector-input fixture path."
    )
    run_once_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for artifacts.",
    )
    run_once_parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic snapshot timestamp.",
    )
    run_once_parser.set_defaults(handler=run_once_fixture_command)

    loop_parser = subparsers.add_parser(
        "loop-fixture",
        help="Bounded fixture loop for testability.",
    )
    loop_parser.add_argument(
        "--fixture", type=Path, required=True, help="Collector-input fixture path."
    )
    loop_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for artifacts.",
    )
    loop_parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic snapshot timestamp.",
    )
    loop_parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of loop iterations (default: 3).",
    )
    loop_parser.add_argument(
        "--interval-seconds",
        type=int,
        default=1,
        help="Seconds between loop iterations (default: 1).",
    )
    loop_parser.set_defaults(handler=loop_fixture_command)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
