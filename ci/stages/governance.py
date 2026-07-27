"""Governance stage — MCP, Surreal, drift checks; policy-gate is mirror-only."""

from __future__ import annotations

import json

from ci.lib.evidence import StageResult
from ci.stages._common import StageContext, python_executable, run_commands_as_stage


def run(ctx: StageContext) -> StageResult:
    # Document GitHub-native remainder for policy-gate (no parity claim).
    note = {
        "check": "policy-gate",
        "local_status": "SKIPPED",
        "skip_reason": (
            "GitHub PR API evaluation remains GitHub-bound; "
            "local mirror must not claim full policy-gate parity (Phase 1)."
        ),
        "parity": "none",
    }
    note_path = ctx.reports_dir / "policy-gate-local-mirror.json"
    note_path.write_text(json.dumps(note, indent=2) + "\n", encoding="utf-8")

    py = python_executable()
    result = run_commands_as_stage(
        ctx,
        name="governance",
        commands=[
            # Same validator as `make mcp-config-validate` / ci.yml MCP Validation.
            [
                py,
                "tools/validate_mcp_config.py",
                "tests/fixtures/mcp_smoke_config.json",
            ],
            ["make", "surreal-validate"],
            [py, "scripts/governance/run_ci_drift_checks.py"],
        ],
        required=True,
    )
    result.artifacts.append(str(note_path.relative_to(ctx.run_dir).as_posix()))
    return result
