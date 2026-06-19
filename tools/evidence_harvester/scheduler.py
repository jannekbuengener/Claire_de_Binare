from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from .collector import EvidenceHarvesterCollector
from .models import CollectorInput
from .snapshot import build_snapshot, snapshot_to_markdown

TASK_NAME = "CDB Evidence Harvester"
DEFAULT_START_TIME = "04:00"


class SchedulerValidationError(ValueError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_output_dir() -> Path:
    return _repo_root() / "artifacts" / "evidence_harvester" / "scheduled"


def _format_json(payload: Mapping[str, Any], pretty: bool) -> str:
    return json.dumps(
        payload,
        indent=2 if pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )


def _emit(payload: Mapping[str, Any], pretty: bool) -> None:
    print(_format_json(payload, pretty))


def _resolve_fixture(path: Path | None, *, required: bool) -> Path | None:
    if path is None:
        if required:
            raise SchedulerValidationError("--fixture is required for this command")
        return None
    resolved = path.resolve()
    if not resolved.exists():
        raise SchedulerValidationError(f"fixture path does not exist: {resolved}")
    return resolved


def _resolve_output_dir(path: Path | None) -> Path:
    return (path or _default_output_dir()).resolve()


def _run_stamp(generated_at_utc: str) -> str:
    return generated_at_utc.replace("-", "").replace(":", "")


def _wrapper_command(
    fixture: Path | None,
    output_dir: Path,
    python_executable: str,
    generated_at_utc: str | None,
    pretty: bool,
) -> list[str]:
    script_path = _repo_root() / "scripts" / "evidence_harvester_task.ps1"
    command = [
        "pwsh.exe",
        "-NoProfile",
        "-File",
        str(script_path),
        "-Action",
        "run-once-fixture",
        "-OutputDir",
        str(output_dir),
        "-PythonExecutable",
        python_executable,
    ]
    if fixture is not None:
        command.extend(["-Fixture", str(fixture)])
    if generated_at_utc is not None:
        command.extend(["-GeneratedAtUtc", generated_at_utc])
    if pretty:
        command.append("-Pretty")
    return command


def _planned_surface(
    fixture: Path | None,
    output_dir: Path,
    python_executable: str,
    generated_at_utc: str | None,
    pretty: bool,
    start_time: str,
    task_name: str,
) -> dict[str, Any]:
    wrapper_command = _wrapper_command(
        fixture,
        output_dir,
        python_executable,
        generated_at_utc,
        pretty,
    )
    return {
        "mode": "plan",
        "task_name": task_name,
        "default_mode": "dry-run",
        "scheduled_action": "run-once-fixture",
        "explicit_required_for_install": True,
        "fixture": str(fixture) if fixture is not None else None,
        "output_dir": str(output_dir),
        "artifacts": {
            "collector_report_pattern": "collector_report_<YYYYMMDDTHHMMSSZ>.json",
            "snapshot_json_pattern": "snapshot_<YYYYMMDDTHHMMSSZ>.json",
            "snapshot_markdown_pattern": "snapshot_<YYYYMMDDTHHMMSSZ>.md",
        },
        "recommended_cadence": {
            "collector_status": "every 15 minutes (manual/read-only recommendation)",
            "snapshot_task": f"daily {start_time} local time (safe fixture snapshot only)",
        },
        "task_scheduler": {
            "schedule": "DAILY",
            "start_time": start_time,
            "wrapper_command": subprocess.list2cmdline(wrapper_command),
        },
        "install_command_preview": subprocess.list2cmdline(
            [
                "schtasks.exe",
                "/Create",
                "/TN",
                task_name,
                "/SC",
                "DAILY",
                "/ST",
                start_time,
                "/TR",
                subprocess.list2cmdline(wrapper_command),
                "/F",
            ]
        ),
        "uninstall_command_preview": subprocess.list2cmdline(
            ["schtasks.exe", "/Delete", "/TN", task_name, "/F"]
        ),
        "safety": [
            "default-off / dry-run by default",
            "no Docker or runtime start",
            "no DB execution or mutation",
            "no secrets",
            "no Redis live read/write",
            "no LR-Go / no Live-Go / no Echtgeld-Go",
        ],
    }


def _latest_snapshot_path(output_dir: Path) -> Path | None:
    candidates = sorted(output_dir.glob("snapshot_*.json"))
    if not candidates:
        return None
    return candidates[-1]


def _snapshot_summary(snapshot_path: Path) -> dict[str, Any]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    status = payload.get("status", {})
    gap_counts = status.get("gap_counts", {})
    return {
        "path": str(snapshot_path),
        "generated_at_utc": metadata.get("generated_at_utc"),
        "collector_report_id": metadata.get("collector_report_id"),
        "source_mode": metadata.get("source_mode"),
        "overall_status": status.get("overall_status"),
        "gap_counts": {
            "blocking": gap_counts.get("blocking", 0),
            "warning": gap_counts.get("warning", 0),
            "info": gap_counts.get("info", 0),
        },
    }


def plan_command(args: argparse.Namespace) -> int:
    fixture = _resolve_fixture(args.fixture, required=False)
    output_dir = _resolve_output_dir(args.output_dir)
    payload = _planned_surface(
        fixture,
        output_dir,
        args.python_executable,
        args.generated_at_utc,
        args.pretty,
        args.start_time,
        args.task_name,
    )
    _emit(payload, args.pretty)
    return 0


def status_command(args: argparse.Namespace) -> int:
    output_dir = _resolve_output_dir(args.output_dir)
    latest_snapshot = None
    if output_dir.exists():
        latest_snapshot_path = _latest_snapshot_path(output_dir)
        if latest_snapshot_path is not None:
            latest_snapshot = _snapshot_summary(latest_snapshot_path)

    payload = {
        "mode": "status",
        "task_name": args.task_name,
        "default_mode": "dry-run",
        "output_dir": str(output_dir),
        "artifact_dir_exists": output_dir.exists(),
        "artifacts_present": latest_snapshot is not None,
        "latest_snapshot": latest_snapshot,
        "safety": [
            "status is derived from local artifacts only",
            "no scheduler installation check performed",
            "no Docker/runtime/DB/Redis/secrets access",
        ],
    }
    _emit(payload, args.pretty)
    return 0


def run_once_fixture_command(args: argparse.Namespace) -> int:
    fixture = _resolve_fixture(args.fixture, required=True)
    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_input = json.loads(fixture.read_text(encoding="utf-8"))
    if not isinstance(raw_input, dict):
        raise SchedulerValidationError("fixture JSON root must be an object")

    collector_input = CollectorInput.from_mapping(raw_input)
    report = EvidenceHarvesterCollector(
        stale_after_minutes=collector_input.stale_after_minutes,
    ).collect(collector_input)
    snapshot = build_snapshot(
        report.to_dict(),
        generated_at_utc=args.generated_at_utc,
    )
    snapshot_payload = snapshot.to_dict()
    stamp = _run_stamp(snapshot_payload["metadata"]["generated_at_utc"])

    collector_report_path = output_dir / f"collector_report_{stamp}.json"
    snapshot_json_path = output_dir / f"snapshot_{stamp}.json"
    snapshot_markdown_path = output_dir / f"snapshot_{stamp}.md"

    collector_report_path.write_text(
        _format_json(report.to_dict(), args.pretty) + "\n",
        encoding="utf-8",
    )
    snapshot_json_path.write_text(
        _format_json(snapshot_payload, args.pretty) + "\n",
        encoding="utf-8",
    )
    snapshot_markdown_path.write_text(
        snapshot_to_markdown(snapshot),
        encoding="utf-8",
    )

    payload = {
        "mode": "run-once-fixture",
        "task_name": args.task_name,
        "output_dir": str(output_dir),
        "artifacts": {
            "collector_report": str(collector_report_path),
            "snapshot_json": str(snapshot_json_path),
            "snapshot_markdown": str(snapshot_markdown_path),
        },
        "latest_snapshot": _snapshot_summary(snapshot_json_path),
        "safety": [
            "fixture-only run",
            "no scheduler autostart",
            "no Docker/runtime/DB/Redis/secrets access",
        ],
    }
    _emit(payload, args.pretty)
    return 0


def _require_explicit(explicit: bool, action: str) -> None:
    if not explicit:
        raise SchedulerValidationError(f"{action} requires --explicit")


def install_command(args: argparse.Namespace) -> int:
    _require_explicit(args.explicit, "install")
    fixture = _resolve_fixture(args.fixture, required=True)
    output_dir = _resolve_output_dir(args.output_dir)
    payload = _planned_surface(
        fixture,
        output_dir,
        args.python_executable,
        args.generated_at_utc,
        args.pretty,
        args.start_time,
        args.task_name,
    )
    task_command = payload["task_scheduler"]["wrapper_command"]
    subprocess.run(
        [
            "schtasks.exe",
            "/Create",
            "/TN",
            args.task_name,
            "/SC",
            "DAILY",
            "/ST",
            args.start_time,
            "/TR",
            task_command,
            "/F",
        ],
        check=True,
    )
    _emit(
        {
            "mode": "install",
            "task_name": args.task_name,
            "installed": True,
            "fixture": str(fixture),
            "output_dir": str(output_dir),
            "start_time": args.start_time,
            "command": task_command,
            "safety": [
                "explicit flag required",
                "scheduled action remains fixture-only",
                "no Docker/runtime/DB/Redis/secrets access implied",
            ],
        },
        args.pretty,
    )
    return 0


def uninstall_command(args: argparse.Namespace) -> int:
    _require_explicit(args.explicit, "uninstall")
    subprocess.run(
        ["schtasks.exe", "/Delete", "/TN", args.task_name, "/F"],
        check=True,
    )
    _emit(
        {
            "mode": "uninstall",
            "task_name": args.task_name,
            "uninstalled": True,
            "safety": [
                "explicit flag required",
                "no runtime or evidence run triggered",
            ],
        },
        args.pretty,
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv = list(argv or [])
    if not argv:
        argv = ["plan"]

    parser = argparse.ArgumentParser(
        description="Default-off local scheduler wrapper for the evidence harvester."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(parser_obj: argparse.ArgumentParser) -> None:
        parser_obj.add_argument(
            "--task-name",
            default=TASK_NAME,
            help="Windows Task Scheduler task name.",
        )
        parser_obj.add_argument(
            "--output-dir",
            type=Path,
            help="Directory for scheduled collector/snapshot artifacts.",
        )
        parser_obj.add_argument(
            "--pretty",
            action="store_true",
            help="Pretty-print JSON output.",
        )

    plan_parser = subparsers.add_parser(
        "plan",
        help="Print the safe dry-run plan without installing anything.",
    )
    add_common(plan_parser)
    plan_parser.add_argument(
        "--fixture",
        type=Path,
        help="Collector-input fixture path for the scheduled run command.",
    )
    plan_parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used by the PowerShell wrapper.",
    )
    plan_parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic timestamp for the planned run command.",
    )
    plan_parser.add_argument(
        "--start-time",
        default=DEFAULT_START_TIME,
        help="Daily local start time for the Windows Task plan (HH:MM).",
    )
    plan_parser.set_defaults(handler=plan_command)

    status_parser = subparsers.add_parser(
        "status",
        help="Report local artifact-based scheduler status.",
    )
    add_common(status_parser)
    status_parser.set_defaults(handler=status_command)

    run_parser = subparsers.add_parser(
        "run-once-fixture",
        help="Run the collector and snapshot once from a local fixture.",
    )
    add_common(run_parser)
    run_parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Collector-input fixture path.",
    )
    run_parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic timestamp for artifact generation.",
    )
    run_parser.set_defaults(handler=run_once_fixture_command)

    install_parser = subparsers.add_parser(
        "install",
        help="Install the Windows Task Scheduler task (explicitly gated).",
    )
    add_common(install_parser)
    install_parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Collector-input fixture path for the scheduled run command.",
    )
    install_parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used by the PowerShell wrapper.",
    )
    install_parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic timestamp for the scheduled run command.",
    )
    install_parser.add_argument(
        "--start-time",
        default=DEFAULT_START_TIME,
        help="Daily local start time for the Windows Task (HH:MM).",
    )
    install_parser.add_argument(
        "--explicit",
        action="store_true",
        help="Required flag for actual task installation.",
    )
    install_parser.set_defaults(handler=install_command)

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Remove the Windows Task Scheduler task (explicitly gated).",
    )
    add_common(uninstall_parser)
    uninstall_parser.add_argument(
        "--explicit",
        action="store_true",
        help="Required flag for actual task removal.",
    )
    uninstall_parser.set_defaults(handler=uninstall_command)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
