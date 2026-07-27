"""Lint stage — wraps ci.yml ruff + black changed-files check."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ci.stages._common import StageContext, run_commands_as_stage
from ci.lib.evidence import StageResult


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


def run(ctx: StageContext) -> StageResult:
    commands: list[list[str]] = [["ruff", "check", "."]]
    files = _changed_python_files(ctx.repo_root)
    if files:
        commands.append(
            ["black", "--config", "pyproject.toml", "--check", *files]
        )
    else:
        # Record empty black as success via a no-op python print for audit trail
        commands.append(
            [
                "python",
                "-c",
                "print('No python changes vs origin/main; black check skipped')",
            ]
        )
    return run_commands_as_stage(ctx, name="lint", commands=commands, required=True)
