"""Docs stage — onboarding/README guards + extracted conflict/canon guards."""

from __future__ import annotations

from ci.lib.evidence import StageResult
from ci.stages._common import StageContext, python_executable, run_commands_as_stage


def run(ctx: StageContext) -> StageResult:
    py = python_executable()
    return run_commands_as_stage(
        ctx,
        name="docs",
        commands=[
            [py, "-m", "tools.validate_onboarding_docs"],
            [py, "-m", "tools.validate_readme_links"],
            [py, "-m", "tools.validate_status_freshness"],
            [py, "-m", "tools.ci.docs_conflict_guard"],
            [py, "-m", "tools.ci.repository_canon_guard"],
        ],
        required=True,
    )
