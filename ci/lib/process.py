"""Subprocess helpers for local CI stages.

Streams stdout/stderr to log files to avoid holding large pytest output in RAM
(important on 16 GB Windows hosts).
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

# Conventional exit code when a subprocess hits its wall-clock timeout.
# Matches GNU timeout(1); stages map this to a typed reason_code (never SKIP).
EXIT_CODE_TIMEOUT = 124


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    timed_out: bool = False


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    env: Mapping[str, str] | None = None,
    timeout: int | None = None,
) -> CommandResult:
    # Fail-closed UTF-8 on Windows consoles (emoji in existing scripts).
    base_env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    merged = base_env if env is None else {**base_env, **dict(env)}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"$ {' '.join(command)}\n")
        handle.flush()
        try:
            proc = subprocess.run(
                list(command),
                cwd=str(cwd),
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=merged,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            # Never re-raise: callers treat exit_code=124 as FAIL, not SKIP/PASS.
            handle.write("\nreason_code=COMMAND_TIMEOUT\n")
            handle.write(f"exit_code={EXIT_CODE_TIMEOUT}\n")
            duration = time.perf_counter() - started
            return CommandResult(
                command=list(command),
                exit_code=EXIT_CODE_TIMEOUT,
                duration_seconds=round(duration, 3),
                stdout="",
                stderr="",
                timed_out=True,
            )
        handle.write(f"\nexit_code={proc.returncode}\n")
    duration = time.perf_counter() - started
    return CommandResult(
        command=list(command),
        exit_code=proc.returncode,
        duration_seconds=round(duration, 3),
        stdout="",
        stderr="",
        timed_out=False,
    )
