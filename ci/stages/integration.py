"""Integration stage — 431B compose lab (heavy profile only)."""

from __future__ import annotations

from ci.stages._common import StageContext, run_commands_as_stage, skipped_stage
from ci.lib.evidence import StageResult


def run(ctx: StageContext) -> StageResult:
    if ctx.profile != "heavy":
        return skipped_stage(
            name="integration",
            reason="integration is heavy-profile only (431B compose lab)",
            required=False,
        )
    project = f"cdb_ci_{ctx.run_id}"
    # Unique project; no host port publish by default (compose files already avoid it).
    return run_commands_as_stage(
        ctx,
        name="integration",
        commands=[
            [
                "docker",
                "compose",
                "-p",
                project,
                "-f",
                "infrastructure/compose/base.yml",
                "-f",
                "infrastructure/compose/test.yml",
                "up",
                "--abort-on-container-exit",
                "--exit-code-from",
                "cdb_test_runner",
            ]
        ],
        required=False,
    )
