"""Unit stage — canonical pytest filter for local CI and thin ci.yml wrapper."""

from __future__ import annotations

from ci.lib.evidence import StageResult
from ci.stages._common import StageContext, python_executable, run_commands_as_stage


def run(ctx: StageContext) -> StageResult:
    # SSOT filter for the fast profile / GitHub ci.yml thin wrapper (#4163).
    # Invoke via the orchestrator interpreter (-m pytest) for local venv parity.
    return run_commands_as_stage(
        ctx,
        name="unit",
        commands=[
            [
                python_executable(),
                "-m",
                "pytest",
                "-q",
                "-k",
                "not test_mcp_time_server_runtime",
            ]
        ],
        required=True,
    )
