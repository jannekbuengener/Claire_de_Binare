"""Stage context shared by local CI stage runners."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ci.lib.evidence import StageResult, utc_now
from ci.lib.process import run_command


def python_executable() -> str:
    """Interpreter that launched the orchestrator (prefer repo .venv via front door)."""
    return sys.executable


@dataclass
class StageContext:
    repo_root: Path
    run_dir: Path
    run_id: str
    git: Any
    profile: str
    resources: dict
    temp_root: Path | None = None
    temp_env: dict[str, str] | None = None
    # Slice selection (optional). When set, unit stage uses selected paths and
    # the run is always merge_evidence=false.
    slice_selection: dict[str, Any] | None = None
    merge_evidence: bool = True
    unit_durations: int = 50

    @property
    def logs_dir(self) -> Path:
        path = self.run_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_dir(self) -> Path:
        path = self.run_dir / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _status_from_exit(code: int) -> str:
    return "PASS" if code == 0 else "FAIL"


def run_commands_as_stage(
    ctx: StageContext,
    *,
    name: str,
    commands: list[list[str]],
    required: bool = True,
    env: Mapping[str, str] | None = None,
    timeout: int | None = None,
) -> StageResult:
    """Run commands sequentially; first non-zero exit stops the stage as FAIL.

    ``timeout`` applies to each command. On ``subprocess.TimeoutExpired``,
    ``run_command`` returns exit_code 124 (never SKIP/PASS).
    """
    started = utc_now()
    log_path = ctx.logs_dir / f"{name}.log"
    summaries: list[str] = []
    exit_code = 0
    combined_parts: list[str] = []
    wall_start = time.perf_counter()
    for command in commands:
        part_log = ctx.logs_dir / f"{name}.{len(summaries)}.log"
        result = run_command(
            command,
            cwd=ctx.repo_root,
            log_path=part_log,
            env=env,
            timeout=timeout,
        )
        summaries.append(" ".join(command))
        if result.timed_out:
            summaries.append("reason_code=COMMAND_TIMEOUT")
        combined_parts.append(part_log.read_text(encoding="utf-8"))
        if result.exit_code != 0:
            exit_code = result.exit_code
            break
    duration = round(time.perf_counter() - wall_start, 3)
    log_path.write_text("\n".join(combined_parts), encoding="utf-8")
    ended = utc_now()
    return StageResult(
        name=name,
        status=_status_from_exit(exit_code),  # type: ignore[arg-type]
        exit_code=exit_code,
        started_at_utc=started,
        ended_at_utc=ended,
        duration_seconds=duration,
        command_summary=summaries,
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[],
        skip_reason=None,
        required=required,
    )


def skipped_stage(
    *,
    name: str,
    reason: str,
    required: bool,
) -> StageResult:
    now = utc_now()
    return StageResult(
        name=name,
        status="SKIPPED",
        exit_code=0,
        started_at_utc=now,
        ended_at_utc=now,
        duration_seconds=0.0,
        command_summary=[],
        log_path="",
        artifacts=[],
        skip_reason=reason,
        required=required,
    )
