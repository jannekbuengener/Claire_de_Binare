"""Report stage — write check-matrix and finalize evidence hashes."""

from __future__ import annotations

import json
import time

from ci.lib.evidence import StageResult, utc_now
from ci.stages._common import StageContext


def build_check_matrix(
    stages: list[StageResult],
    *,
    merge_evidence: bool = True,
) -> dict:
    return {
        "schema_version": "cdb-local-ci-check-matrix/v1",
        "note": (
            "Local evidence is not a GitHub Required Check in Phase 1. "
            "Branch Protection remains unchanged. "
            "Slice evidence (merge_evidence=false) is never merge proof (#4204)."
        ),
        "merge_evidence": bool(merge_evidence),
        "stages": [
            {
                "name": s.name,
                "status": s.status,
                "required": s.required,
                "skip_reason": s.skip_reason,
                "duration_seconds": s.duration_seconds,
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


def build_stage_timing_report(
    stages: list[StageResult],
    *,
    merge_evidence: bool,
    profile: str,
) -> dict:
    """Machine-readable stage duration summary (does not alter pass/fail)."""
    rows = [
        {
            "name": s.name,
            "status": s.status,
            "duration_seconds": s.duration_seconds,
            "required": s.required,
        }
        for s in stages
    ]
    total = round(sum(float(s.duration_seconds or 0.0) for s in stages), 3)
    return {
        "schema_version": "cdb-local-ci-stage-timing/v1",
        "merge_evidence": bool(merge_evidence),
        "profile": profile,
        "total_duration_seconds": total,
        "stages": rows,
    }


def run(ctx: StageContext, prior_stages: list[StageResult]) -> StageResult:
    started = utc_now()
    wall = time.perf_counter()
    matrix = build_check_matrix(prior_stages, merge_evidence=bool(ctx.merge_evidence))
    matrix_path = ctx.reports_dir / "check-matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    timing = build_stage_timing_report(
        prior_stages,
        merge_evidence=bool(ctx.merge_evidence),
        profile=ctx.profile,
    )
    timing_path = ctx.reports_dir / "stage_timing.json"
    timing_path.write_text(
        json.dumps(timing, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    log_path = ctx.logs_dir / "report.log"
    log_path.write_text(
        f"Wrote {matrix_path.relative_to(ctx.run_dir).as_posix()}\n"
        f"Wrote {timing_path.relative_to(ctx.run_dir).as_posix()}\n",
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
        command_summary=["aggregate check-matrix.json", "aggregate stage_timing.json"],
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[
            str(matrix_path.relative_to(ctx.run_dir).as_posix()),
            str(timing_path.relative_to(ctx.run_dir).as_posix()),
        ],
        skip_reason=None,
        required=True,
    )
