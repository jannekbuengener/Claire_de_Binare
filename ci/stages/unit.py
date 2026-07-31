"""Unit stage — canonical pytest filter for local CI and thin ci.yml wrapper."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ci.lib.evidence import StageResult
from ci.lib.slice_selection import (
    SliceSelectionResult,
    build_unit_pytest_command,
)
from ci.stages._common import StageContext, python_executable, run_commands_as_stage

# SSOT filter for the fast profile / GitHub ci.yml thin wrapper (#4163).
FULL_FAST_SELECTOR = "not test_mcp_time_server_runtime"

_DURATION_LINE_RE = re.compile(r"^\s*([\d.]+)s\s+(call|setup|teardown)\s+(.+)$")


def _selection_from_ctx(ctx: StageContext) -> SliceSelectionResult | None:
    raw = ctx.slice_selection
    if not raw:
        return None
    return SliceSelectionResult(
        schema_version=str(raw.get("schema_version") or ""),
        policy_id=raw.get("policy_id"),
        policy_schema_version=raw.get("policy_schema_version"),
        selected_test_groups=list(raw.get("selected_test_groups") or []),
        selection_reasons=list(raw.get("selection_reasons") or []),
        unclassified_paths=list(raw.get("unclassified_paths") or []),
        fallback_reason=raw.get("fallback_reason"),
        merge_evidence=False,
        pytest_paths=list(raw.get("pytest_paths") or []),
        pytest_args=list(raw.get("pytest_args") or []),
        used_full_fast=bool(raw.get("used_full_fast")),
        inputs=dict(raw.get("inputs") or {}),
    )


def build_unit_command(ctx: StageContext) -> list[str]:
    """Build the unit pytest command (full Fast-CI or slice selection)."""
    durations = int(getattr(ctx, "unit_durations", 50) or 0)
    selection = _selection_from_ctx(ctx)
    if selection is not None:
        return build_unit_pytest_command(
            selection,
            python_executable=python_executable(),
            durations=durations,
        )
    # Default Fast-CI / heavy unit selector — semantically unchanged (#4163/#4204).
    command = [
        python_executable(),
        "-m",
        "pytest",
        "-q",
        "-k",
        FULL_FAST_SELECTOR,
    ]
    if durations > 0:
        command.append(f"--durations={durations}")
    return command


def parse_pytest_durations(
    log_text: str, *, limit: int = 50
) -> list[dict[str, object]]:
    """Extract slowest pytest duration lines from a stage log (best-effort)."""
    rows: list[dict[str, object]] = []
    for line in log_text.splitlines():
        match = _DURATION_LINE_RE.match(line)
        if not match:
            continue
        rows.append(
            {
                "duration_seconds": float(match.group(1)),
                "phase": match.group(2),
                "nodeid": match.group(3).strip(),
            }
        )
    rows.sort(key=lambda r: float(r["duration_seconds"]), reverse=True)
    return rows[: max(0, int(limit))]


def write_unit_timing_report(
    ctx: StageContext,
    *,
    log_path: Path,
    command: list[str],
) -> str | None:
    """Write reports/unit_timing.json; return relative path or None."""
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    durations = parse_pytest_durations(log_text, limit=max(1, ctx.unit_durations))
    report = {
        "schema_version": "cdb-local-ci-unit-timing/v1",
        "merge_evidence": bool(ctx.merge_evidence),
        "profile": ctx.profile,
        "command": command,
        "slowest": durations,
        "slowest_count": len(durations),
    }
    out = ctx.reports_dir / "unit_timing.json"
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return str(out.relative_to(ctx.run_dir).as_posix())


def run(ctx: StageContext) -> StageResult:
    # Invoke via the orchestrator interpreter (-m pytest) for local venv parity.
    command = build_unit_command(ctx)
    env = None
    if ctx.temp_root is not None:
        basetemp = ctx.temp_root / "pytest-basetemp"
        cache_dir = ctx.temp_root / "pytest-cache"
        # Prefer controlled cache under run-scoped temp root (pytest ini via -o).
        command = list(command) + [
            "--basetemp",
            str(basetemp),
            "-o",
            f"cache_dir={cache_dir.as_posix()}",
        ]
        env = ctx.temp_env
    result = run_commands_as_stage(
        ctx,
        name="unit",
        commands=[command],
        required=True,
        env=env,
    )
    timing_rel = write_unit_timing_report(
        ctx,
        log_path=(
            ctx.run_dir / result.log_path
            if result.log_path
            else ctx.logs_dir / "unit.log"
        ),
        command=command,
    )
    if timing_rel:
        result.artifacts = list(result.artifacts) + [timing_rel]
    return result
