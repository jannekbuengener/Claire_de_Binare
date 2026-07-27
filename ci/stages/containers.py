"""Containers stage — scoped test image build only; no GHCR push."""

from __future__ import annotations

from ci.stages._common import StageContext, run_commands_as_stage, skipped_stage
from ci.lib.evidence import StageResult


def run(ctx: StageContext) -> StageResult:
    if ctx.profile != "heavy":
        return skipped_stage(
            name="containers",
            reason="containers is heavy-profile only; no GHCR push; no BLUE/RED default",
            required=False,
        )
    return run_commands_as_stage(
        ctx,
        name="containers",
        commands=[
            [
                "docker",
                "build",
                "-f",
                "ci/Dockerfile",
                "-t",
                f"cdb-local-ci:{ctx.run_id}",
                ".",
            ]
        ],
        required=False,
    )
