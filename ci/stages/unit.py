"""Unit stage — canonical pytest filter for local CI and thin ci.yml wrapper."""

from __future__ import annotations

from ci.lib.evidence import StageResult
from ci.stages._common import StageContext, python_executable, run_commands_as_stage


def run(ctx: StageContext) -> StageResult:
    # SSOT filter for the fast profile / GitHub ci.yml thin wrapper (#4163).
    # Invoke via the orchestrator interpreter (-m pytest) for local venv parity.
    command = [
        python_executable(),
        "-m",
        "pytest",
        "-q",
        "-k",
        "not test_mcp_time_server_runtime",
    ]
    env = None
    if ctx.temp_root is not None:
        basetemp = ctx.temp_root / "pytest-basetemp"
        cache_dir = ctx.temp_root / "pytest-cache"
        # Prefer controlled cache under run-scoped temp root (pytest ini via -o).
        command.extend(
            [
                "--basetemp",
                str(basetemp),
                "-o",
                f"cache_dir={cache_dir.as_posix()}",
            ]
        )
        env = ctx.temp_env
    return run_commands_as_stage(
        ctx,
        name="unit",
        commands=[command],
        required=True,
        env=env,
    )
