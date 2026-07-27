"""Unit stage — exact ci.yml pytest command (SSOT for required gate)."""

from __future__ import annotations

from ci.stages._common import StageContext, run_commands_as_stage
from ci.lib.evidence import StageResult


def run(ctx: StageContext) -> StageResult:
    # Keep command identical to .github/workflows/ci.yml Tests step.
    return run_commands_as_stage(
        ctx,
        name="unit",
        commands=[["pytest", "-q", "-k", "not test_mcp_time_server_runtime"]],
        required=True,
    )
