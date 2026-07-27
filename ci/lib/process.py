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


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str


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
        handle.write(f"\nexit_code={proc.returncode}\n")
    duration = time.perf_counter() - started
    return CommandResult(
        command=list(command),
        exit_code=proc.returncode,
        duration_seconds=round(duration, 3),
        stdout="",
        stderr="",
    )
