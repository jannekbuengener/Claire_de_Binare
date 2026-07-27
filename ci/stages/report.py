"""Report stage — write check-matrix and finalize evidence hashes."""

from __future__ import annotations

import json
import time

from ci.lib.evidence import StageResult, utc_now
from ci.stages._common import StageContext


def build_check_matrix(stages: list[StageResult]) -> dict:
    return {
        "schema_version": "cdb-local-ci-check-matrix/v1",
        "note": (
            "Local evidence is not a GitHub Required Check in Phase 1. "
            "Branch Protection remains unchanged."
        ),
        "stages": [
            {
                "name": s.name,
                "status": s.status,
                "required": s.required,
                "skip_reason": s.skip_reason,
                "command_summary": s.command_summary,
            }
            for s in stages
        ],
        "github_native_remainder": [
            "policy-gate (PR API)",
            "CodeQL Security-tab upload",
            "Dependabot",
            "Secret Scanning (platform)",
            "GHCR publishing",
            "required-checks-audit / auto-milestone",
        ],
    }


def run(ctx: StageContext, prior_stages: list[StageResult]) -> StageResult:
    started = utc_now()
    wall = time.perf_counter()
    matrix = build_check_matrix(prior_stages)
    matrix_path = ctx.reports_dir / "check-matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    log_path = ctx.logs_dir / "report.log"
    log_path.write_text(
        f"Wrote {matrix_path.relative_to(ctx.run_dir).as_posix()}\n",
        encoding="utf-8",
    )
    ended = utc_now()
    return StageResult(
        name="report",
        status="PASS",
        exit_code=0,
        started_at_utc=started,
        ended_at_utc=ended,
        duration_seconds=round(time.perf_counter() - wall, 3),
        command_summary=["aggregate check-matrix.json"],
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[str(matrix_path.relative_to(ctx.run_dir).as_posix())],
        skip_reason=None,
        required=True,
    )
