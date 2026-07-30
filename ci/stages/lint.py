"""Lint stage — wraps ci.yml ruff + black changed-files check."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ci.lib.evidence import StageResult
from ci.stages._common import StageContext, python_executable, run_commands_as_stage


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


def _black_command(python: str) -> list[str]:
    override = (os.environ.get("CDB_BLACK_EXECUTABLE") or "").strip()
    if not override:
        return [python, "-m", "black"]
    executable = Path(override)
    if not executable.is_file():
        raise RuntimeError("CDB_BLACK_EXECUTABLE must name an existing executable file")
    return [str(executable)]


def run(ctx: StageContext) -> StageResult:
    py = python_executable()
    commands: list[list[str]] = [[py, "-m", "ruff", "check", "."]]
    files = _changed_python_files(ctx.repo_root)
    if files:
        commands.append(
            [
                *_black_command(py),
                "--config",
                "pyproject.toml",
                "--check",
                "--workers",
                "1",
                *files,
            ]
        )
    else:
        commands.append(
            [
                py,
                "-c",
                "print('No python changes vs origin/main; black check skipped')",
            ]
        )
    return run_commands_as_stage(ctx, name="lint", commands=commands, required=True)
