"""Docs stage — onboarding/README guards + extracted Docs Conflict/Hub guards."""

from __future__ import annotations

from ci.stages._common import StageContext, run_commands_as_stage
from ci.lib.evidence import StageResult


def run(ctx: StageContext) -> StageResult:
    return run_commands_as_stage(
        ctx,
        name="docs",
        commands=[
            ["python", "-m", "tools.validate_onboarding_docs"],
            ["python", "-m", "tools.validate_readme_links"],
            ["python", "-m", "tools.ci.docs_conflict_guard"],
            ["python", "-m", "tools.ci.repository_canon_guard"],
        ],
        required=True,
    )
