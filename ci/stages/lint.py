"""Lint stage — wraps ci.yml ruff + black changed-files check."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from ci.lib.evidence import StageResult, utc_now
from ci.lib.process import EXIT_CODE_TIMEOUT, run_command
from ci.stages._common import StageContext, python_executable

# Typed fail reasons for Black (never SKIP/PASS on timeout or invalid override).
BLACK_TIMEOUT = "BLACK_TIMEOUT"
BLACK_EXECUTABLE_MISSING = "BLACK_EXECUTABLE_MISSING"
BLACK_EXECUTABLE_INVALID = "BLACK_EXECUTABLE_INVALID"
BLACK_VERSION_MISMATCH = "BLACK_VERSION_MISMATCH"
BLACK_EXECUTION_FAILED = "BLACK_EXECUTION_FAILED"
# Backward-compatible alias used by earlier #4206 slice tests.
BLACK_NONZERO_EXIT = BLACK_EXECUTION_FAILED
CHANGED_FILES_ENUMERATION_FAILED = "CHANGED_FILES_ENUMERATION_FAILED"

# Characters / patterns that make an override unsafe as an argv element.
# Note: backslash is NOT treated as meta — Windows paths use ``\``.
_BLACK_OVERRIDE_UNSAFE = (";", "|", "&", "$(", "`", "\n", "\r")
_SHELL_META = re.compile(r"[;&|<>`$]")
_BLACK_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")

_DEFAULT_BLACK_TIMEOUT_SECONDS = 300
_BLACK_TIMEOUT_CAP_SECONDS = 900
_BLACK_TIMEOUT_ENV = "CDB_BLACK_TIMEOUT_SECONDS"
_REQUIREMENTS_DEV = "requirements-dev.txt"
_RUFF_RUNNER_ENV = "CDB_RUFF_RUNNER"
_BLACK_RUNNER_ENV = "CDB_BLACK_RUNNER"
_RUFF_DOCKER_IMAGE_ENV = "CDB_RUFF_DOCKER_IMAGE"
RUFF_RUNNER_INVALID = "RUFF_RUNNER_INVALID"
RUFF_DOCKER_IMAGE_MISSING = "RUFF_DOCKER_IMAGE_MISSING"
RUFF_DOCKER_UNAVAILABLE = "RUFF_DOCKER_UNAVAILABLE"


class BlackResolutionError(RuntimeError):
    """Fail-closed Black executable / version / changed-file resolution error."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class RuffResolutionError(RuntimeError):
    """Fail-closed Docker-Ruff runner selection error."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def pinned_black_version(repo_root: Path) -> str:
    path = repo_root / _REQUIREMENTS_DEV
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("black=="):
            return stripped.split("==", 1)[1].strip()
    raise BlackResolutionError(
        BLACK_EXECUTABLE_INVALID,
        f"No black== pin found in {_REQUIREMENTS_DEV}",
    )


def redact_path_for_evidence(path: str) -> str:
    home = str(Path.home())
    if home and path.startswith(home):
        return "$HOME" + path[len(home) :]
    return path


def _changed_python_files(repo_root: Path) -> list[str]:
    """Return sorted changed *.py paths vs origin/main (fail-closed on git error)."""
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=d",
            "origin/main",
            "HEAD",
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
        detail = (result.stderr or result.stdout or "").strip()
        raise BlackResolutionError(
            CHANGED_FILES_ENUMERATION_FAILED,
            f"git diff for changed python files failed: {detail}",
        )
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return sorted(files)


def _validate_black_override(override: str) -> Path:
    """Fail-closed validation for CDB_BLACK_EXECUTABLE (escape hatch only)."""
    if (
        any(token in override for token in _BLACK_OVERRIDE_UNSAFE)
        or _SHELL_META.search(override)
        or len(override.split()) > 1
    ):
        raise BlackResolutionError(
            BLACK_EXECUTABLE_INVALID,
            f"{BLACK_EXECUTABLE_INVALID}: CDB_BLACK_EXECUTABLE contains "
            "unsafe shell metacharacters or embedded arguments",
        )
    executable = Path(override)
    if not executable.exists():
        raise BlackResolutionError(
            BLACK_EXECUTABLE_MISSING,
            f"{BLACK_EXECUTABLE_MISSING}: CDB_BLACK_EXECUTABLE must name an "
            "existing executable file",
        )
    if not executable.is_file():
        raise BlackResolutionError(
            BLACK_EXECUTABLE_INVALID,
            f"{BLACK_EXECUTABLE_INVALID}: CDB_BLACK_EXECUTABLE must name a "
            "regular file, not a directory",
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


def pinned_ruff_version(repo_root: Path) -> str:
    """Read the single Ruff pin used by native and containerized runners."""
    path = repo_root / _REQUIREMENTS_DEV
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("ruff=="):
            return stripped.split("==", 1)[1].strip()
    raise RuffResolutionError(
        RUFF_RUNNER_INVALID,
        f"No ruff== pin found in {_REQUIREMENTS_DEV}",
    )


def _docker_lint_command(
    *, tool: str, repo_root: Path, arguments: list[str]
) -> list[str]:
    """Build a fixed, isolated container command for an allowlisted lint tool."""
    if tool not in {"ruff", "black"}:
        raise RuffResolutionError(
            RUFF_RUNNER_INVALID,
            f"{RUFF_RUNNER_INVALID}: unsupported container lint tool",
        )
    image = (os.environ.get(_RUFF_DOCKER_IMAGE_ENV) or "").strip()
    if not image:
        raise RuffResolutionError(
            RUFF_DOCKER_IMAGE_MISSING,
            f"{RUFF_DOCKER_IMAGE_MISSING}: {_RUFF_DOCKER_IMAGE_ENV} is required",
        )
    if any(token in image for token in _BLACK_OVERRIDE_UNSAFE) or _SHELL_META.search(
        image
    ):
        raise RuffResolutionError(
            RUFF_RUNNER_INVALID,
            f"{RUFF_RUNNER_INVALID}: {_RUFF_DOCKER_IMAGE_ENV} contains unsafe characters",
        )

    expected_version = (
        pinned_ruff_version(repo_root)
        if tool == "ruff"
        else pinned_black_version(repo_root)
    )

    verify_and_run = (
        "from importlib.metadata import version\n"
        "import subprocess\n"
        "import sys\n"
        f"expected = {expected_version!r}\n"
        f"actual = version({tool!r})\n"
        f"print({tool!r} + '_version=' + actual)\n"
        "if actual != expected:\n"
        "    raise SystemExit(70)\n"
        f"raise SystemExit(subprocess.run([sys.executable, '-m', {tool!r}, *{arguments!r}]).returncode)\n"
    )
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network",
        "none",
        "--read-only",
        "--mount",
        f"type=bind,src={repo_root.resolve()},dst=/workspace,readonly",
        "--workdir",
        "/workspace",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--env",
        "HOME=/tmp",
        "--env",
        "RUFF_CACHE_DIR=/tmp/ruff-cache",
        image,
        "python",
        "-c",
        verify_and_run,
    ]


def _ruff_command(*, python: str, repo_root: Path) -> list[str]:
    """Build the authoritative native or isolated Docker Ruff command."""
    runner = (os.environ.get(_RUFF_RUNNER_ENV) or "native").strip().lower()
    if runner == "native":
        return [python, "-m", "ruff", "check", "."]
    if runner != "docker":
        raise RuffResolutionError(
            RUFF_RUNNER_INVALID,
            f"{RUFF_RUNNER_INVALID}: {_RUFF_RUNNER_ENV} must be native or docker",
        )
    return _docker_lint_command(
        tool="ruff",
        repo_root=repo_root,
        arguments=["check", "."],
    )


def _black_runner_command(
    *, python: str, repo_root: Path, files: list[str]
) -> tuple[list[str], str, bool]:
    """Build native Black by default, or the same bounded Docker fallback."""
    runner = (os.environ.get(_BLACK_RUNNER_ENV) or "native").strip().lower()
    if runner == "native":
        command = _black_command(python)
        return command, ensure_black_version(command, repo_root=repo_root), False
    if runner != "docker":
        raise BlackResolutionError(
            BLACK_EXECUTABLE_INVALID,
            f"{BLACK_EXECUTABLE_INVALID}: {_BLACK_RUNNER_ENV} must be native or docker",
        )
    version = pinned_black_version(repo_root)
    return (
        _docker_lint_command(
            tool="black",
            repo_root=repo_root,
            arguments=[
                "--config",
                "pyproject.toml",
                "--check",
                "--workers",
                "1",
                *files,
            ],
        ),
        version,
        True,
    )


def _black_timeout_seconds(resources: dict) -> int:
    """Positive bounded timeout; env overrides resources; hard cap 900s."""
    env_raw = (os.environ.get(_BLACK_TIMEOUT_ENV) or "").strip()
    if env_raw:
        try:
            value = int(env_raw)
        except ValueError as exc:
            raise BlackResolutionError(
                BLACK_EXECUTABLE_INVALID,
                f"{_BLACK_TIMEOUT_ENV} must be a positive integer",
            ) from exc
        if value <= 0:
            raise BlackResolutionError(
                BLACK_EXECUTABLE_INVALID,
                f"{_BLACK_TIMEOUT_ENV} must be a positive integer",
            )
        return min(value, _BLACK_TIMEOUT_CAP_SECONDS)

    raw = resources.get("black_timeout_seconds", _DEFAULT_BLACK_TIMEOUT_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_BLACK_TIMEOUT_SECONDS
    if value <= 0:
        return _DEFAULT_BLACK_TIMEOUT_SECONDS
    return min(value, _BLACK_TIMEOUT_CAP_SECONDS)


def _probe_black_version(argv: list[str], *, cwd: Path) -> str:
    try:
        proc = subprocess.run(
            [*argv, "--version"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BlackResolutionError(
            BLACK_EXECUTABLE_INVALID,
            f"Unable to execute black --version: {exc}",
        ) from exc
    combined = f"{proc.stdout or ''}{proc.stderr or ''}"
    if proc.returncode != 0:
        raise BlackResolutionError(
            BLACK_EXECUTABLE_INVALID,
            f"black --version failed (exit {proc.returncode}): {combined.strip()}",
        )
    match = _BLACK_VERSION_RE.search(combined)
    if not match:
        raise BlackResolutionError(
            BLACK_EXECUTABLE_INVALID,
            f"Could not parse black version from: {combined.strip()!r}",
        )
    return match.group(1)


def ensure_black_version(argv: list[str], *, repo_root: Path) -> str:
    expected = pinned_black_version(repo_root)
    version = _probe_black_version(argv, cwd=repo_root)
    if version != expected:
        raise BlackResolutionError(
            BLACK_VERSION_MISMATCH,
            f"Active black {version} does not match pin {expected}",
        )
    return version


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
        reason_code=reason_code,
    )


def run(ctx: StageContext) -> StageResult:
    """Run ruff (unbounded) then Black with a resource-bounded timeout."""
    py = python_executable()
    started = utc_now()
    wall_start = time.perf_counter()
    summaries: list[str] = []
    combined_parts: list[str] = []

    try:
        black_timeout = _black_timeout_seconds(ctx.resources)
    except BlackResolutionError as exc:
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=[str(exc)],
            exit_code=1,
            reason_code=exc.reason_code,
            wall_start=wall_start,
        )

    try:
        ruff_cmd = _ruff_command(python=py, repo_root=ctx.repo_root)
    except RuffResolutionError as exc:
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=[str(exc)],
            exit_code=1,
            reason_code=exc.reason_code,
            wall_start=wall_start,
        )
    ruff_log = ctx.logs_dir / "lint.0.log"
    try:
        ruff_result = run_command(ruff_cmd, cwd=ctx.repo_root, log_path=ruff_log)
    except OSError as exc:
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=[f"{RUFF_DOCKER_UNAVAILABLE}: {exc}"],
            exit_code=1,
            reason_code=RUFF_DOCKER_UNAVAILABLE,
            wall_start=wall_start,
        )
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
            reason_code=None,
        )

    try:
        files = _changed_python_files(ctx.repo_root)
    except BlackResolutionError as exc:
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=[*combined_parts, str(exc)],
            exit_code=1,
            reason_code=exc.reason_code,
            wall_start=wall_start,
        )

    if not files:
        skip_msg = (
            "No python changes vs origin/main; black check skipped "
            "(empty changed-file set)"
        )
        skip_cmd = [py, "-c", f"print({skip_msg!r})"]
        skip_log = ctx.logs_dir / "lint.1.log"
        skip_result = run_command(skip_cmd, cwd=ctx.repo_root, log_path=skip_log)
        summaries.append(" ".join(skip_cmd))
        combined_parts.append(skip_log.read_text(encoding="utf-8"))
        log_path = ctx.logs_dir / "lint.log"
        log_path.write_text(
            f"black_timeout_seconds={black_timeout}\n" + "\n".join(combined_parts),
            encoding="utf-8",
        )
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
            reason_code=None,
        )

    try:
        black_prefix, version, black_is_docker = _black_runner_command(
            python=py,
            repo_root=ctx.repo_root,
            files=files,
        )
    except BlackResolutionError as exc:
        combined_parts.append(str(exc))
        return _fail_stage(
            ctx=ctx,
            started=started,
            summaries=summaries,
            combined_parts=combined_parts,
            exit_code=1,
            reason_code=exc.reason_code,
            wall_start=wall_start,
        )
    except RuntimeError as exc:
        # Legacy raise path from older validators.
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

    override = (os.environ.get("CDB_BLACK_EXECUTABLE") or "").strip()
    if override and not black_is_docker:
        combined_parts.append(
            f"black_override=CDB_BLACK_EXECUTABLE="
            f"{redact_path_for_evidence(override)} version={version}"
        )
    combined_parts.append(f"black_timeout_seconds={black_timeout}")
    combined_parts.append(f"black_version={version}")

    black_cmd = (
        black_prefix
        if black_is_docker
        else [
            *black_prefix,
            "--config",
            "pyproject.toml",
            "--check",
            "--workers",
            "1",
            *files,
        ]
    )
    black_log = ctx.logs_dir / "lint.1.log"
    black_result = run_command(
        black_cmd,
        cwd=ctx.repo_root,
        log_path=black_log,
        timeout=black_timeout,
        timeout_reason_code=BLACK_TIMEOUT,
    )
    summaries.append(" ".join(black_cmd))
    combined_parts.append(black_log.read_text(encoding="utf-8"))

    if black_result.timed_out or black_result.exit_code == EXIT_CODE_TIMEOUT:
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
            reason_code=BLACK_EXECUTION_FAILED,
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
        reason_code=None,
    )
