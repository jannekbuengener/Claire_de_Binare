"""Lint stage — wraps ci.yml ruff + black changed-files check."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from ci.lib.evidence import StageResult, utc_now
from ci.lib.process import EXIT_CODE_TIMEOUT, run_command
from ci.stages._common import StageContext, python_executable

# Typed fail reasons for Black (never SKIP/PASS on timeout or invalid override).
BLACK_TIMEOUT = "BLACK_TIMEOUT"
BLACK_EXECUTABLE_INVALID = "BLACK_EXECUTABLE_INVALID"
BLACK_NONZERO_EXIT = "BLACK_NONZERO_EXIT"

# Characters / patterns that make an override unsafe as an argv element.
_BLACK_OVERRIDE_UNSAFE = (";", "|", "&", "$(", "`", "\n", "\r")

_DEFAULT_BLACK_TIMEOUT_SECONDS = 120


def _changed_python_files(repo_root: Path) -> list[str]:
    base = "origin/main"
    head = "HEAD"
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=d",
            base,
            head,
            "--",
            "*.py",
            ":!.codex/**",
            ":!.opencode/**",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _validate_black_override(override: str) -> Path:
    """Fail-closed validation for CDB_BLACK_EXECUTABLE (escape hatch only)."""
    if any(token in override for token in _BLACK_OVERRIDE_UNSAFE):
        raise RuntimeError(
            f"{BLACK_EXECUTABLE_INVALID}: CDB_BLACK_EXECUTABLE contains "
            "unsafe shell metacharacters"
        )
    executable = Path(override)
    if not executable.is_file():
        raise RuntimeError(
            f"{BLACK_EXECUTABLE_INVALID}: CDB_BLACK_EXECUTABLE must name an "
            "existing executable file"
        )
    return executable


def _black_command(python: str) -> list[str]:
    """Default: ``python -m black`` (pinned black==26.5.1 in requirements-dev).

    ``CDB_BLACK_EXECUTABLE`` is a strictly validated escape hatch only.
    """
    override = (os.environ.get("CDB_BLACK_EXECUTABLE") or "").strip()
    if not override:
        return [python, "-m", "black"]
    return [str(_validate_black_override(override))]


def _black_timeout_seconds(resources: dict) -> int:
    raw = resources.get("black_timeout_seconds", _DEFAULT_BLACK_TIMEOUT_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_BLACK_TIMEOUT_SECONDS
    return value if value > 0 else _DEFAULT_BLACK_TIMEOUT_SECONDS


def _fail_stage(
    *,
    ctx: StageContext,
    started: str,
    summaries: list[str],
    combined_parts: list[str],
    exit_code: int,
    reason_code: str,
    wall_start: float,
) -> StageResult:
    summaries = [*summaries, f"reason_code={reason_code}"]
    log_path = ctx.logs_dir / "lint.log"
    log_path.write_text("\n".join(combined_parts), encoding="utf-8")
    return StageResult(
        name="lint",
        status="FAIL",
        exit_code=exit_code,
        started_at_utc=started,
        ended_at_utc=utc_now(),
        duration_seconds=round(time.perf_counter() - wall_start, 3),
        command_summary=summaries,
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[],
        skip_reason=None,
        required=True,
    )


def run(ctx: StageContext) -> StageResult:
    """Run ruff (unbounded) then Black with a resource-bounded timeout."""
    py = python_executable()
    started = utc_now()
    wall_start = time.perf_counter()
    summaries: list[str] = []
    combined_parts: list[str] = []
    black_timeout = _black_timeout_seconds(ctx.resources)

    ruff_cmd = [py, "-m", "ruff", "check", "."]
    ruff_log = ctx.logs_dir / "lint.0.log"
    ruff_result = run_command(ruff_cmd, cwd=ctx.repo_root, log_path=ruff_log)
    summaries.append(" ".join(ruff_cmd))
    combined_parts.append(ruff_log.read_text(encoding="utf-8"))
    if ruff_result.exit_code != 0:
        log_path = ctx.logs_dir / "lint.log"
        log_path.write_text("\n".join(combined_parts), encoding="utf-8")
        return StageResult(
            name="lint",
            status="FAIL",
            exit_code=ruff_result.exit_code,
            started_at_utc=started,
            ended_at_utc=utc_now(),
            duration_seconds=round(time.perf_counter() - wall_start, 3),
            command_summary=summaries,
            log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
            artifacts=[],
            skip_reason=None,
            required=True,
        )

    files = _changed_python_files(ctx.repo_root)
    if not files:
        skip_cmd = [
            py,
            "-c",
            "print('No python changes vs origin/main; black check skipped')",
        ]
        skip_log = ctx.logs_dir / "lint.1.log"
        skip_result = run_command(skip_cmd, cwd=ctx.repo_root, log_path=skip_log)
        summaries.append(" ".join(skip_cmd))
        combined_parts.append(skip_log.read_text(encoding="utf-8"))
        log_path = ctx.logs_dir / "lint.log"
        log_path.write_text("\n".join(combined_parts), encoding="utf-8")
        return StageResult(
            name="lint",
            status="PASS" if skip_result.exit_code == 0 else "FAIL",
            exit_code=skip_result.exit_code,
            started_at_utc=started,
            ended_at_utc=utc_now(),
            duration_seconds=round(time.perf_counter() - wall_start, 3),
            command_summary=summaries,
            log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
            artifacts=[],
            skip_reason=None,
            required=True,
        )

    try:
        black_prefix = _black_command(py)
    except RuntimeError as exc:
        combined_parts.append(str(exc))
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=combined_parts,
            exit_code=1,
            reason_code=BLACK_EXECUTABLE_INVALID,
            wall_start=wall_start,
        )

    black_cmd = [
        *black_prefix,
        "--config",
        "pyproject.toml",
        "--check",
        "--workers",
        "1",
        *files,
    ]
    black_log = ctx.logs_dir / "lint.1.log"
    black_result = run_command(
        black_cmd,
        cwd=ctx.repo_root,
        log_path=black_log,
        timeout=black_timeout,
    )
    summaries.append(" ".join(black_cmd))
    combined_parts.append(black_log.read_text(encoding="utf-8"))

    if black_result.timed_out or black_result.exit_code == EXIT_CODE_TIMEOUT:
        # Annotate log with the Black-specific reason (process layer writes
        # COMMAND_TIMEOUT generically).
        with black_log.open("a", encoding="utf-8") as handle:
            handle.write(f"reason_code={BLACK_TIMEOUT}\n")
        combined_parts[-1] = black_log.read_text(encoding="utf-8")
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=combined_parts,
            exit_code=EXIT_CODE_TIMEOUT,
            reason_code=BLACK_TIMEOUT,
            wall_start=wall_start,
        )

    if black_result.exit_code != 0:
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=combined_parts,
            exit_code=black_result.exit_code,
            reason_code=BLACK_NONZERO_EXIT,
            wall_start=wall_start,
        )

    log_path = ctx.logs_dir / "lint.log"
    log_path.write_text("\n".join(combined_parts), encoding="utf-8")
    return StageResult(
        name="lint",
        status="PASS",
        exit_code=0,
        started_at_utc=started,
        ended_at_utc=utc_now(),
        duration_seconds=round(time.perf_counter() - wall_start, 3),
        command_summary=summaries,
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[],
        skip_reason=None,
        required=True,
    )
