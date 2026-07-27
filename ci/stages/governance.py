"""Governance stage — MCP, Surreal, drift checks; policy-gate is mirror-only."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ci.lib.evidence import StageResult
from ci.stages._common import StageContext, python_executable, run_commands_as_stage

SURREAL_VERSION = "v3.1.5"
SURQL_FILES = (
    "infrastructure/surrealdb/context_intelligence_v0_deploy.surql",
    "infrastructure/surrealdb/context_intelligence_v0.surql",
)


def _surreal_commands(repo_root: Path) -> list[list[str]]:
    """Portable SurrealQL validate (avoid fragile Make/shell on Windows)."""
    if shutil.which("surreal"):
        return [["surreal", "validate", path] for path in SURQL_FILES]
    if shutil.which("docker"):
        image = f"ghcr.io/surrealdb/surrealdb:{SURREAL_VERSION}"
        root = str(repo_root.resolve())
        cmds: list[list[str]] = [["docker", "pull", image]]
        for path in SURQL_FILES:
            cmds.append(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{root}:/workspace",
                    image,
                    "validate",
                    f"/workspace/{path}",
                ]
            )
        return cmds
    raise RuntimeError("neither surreal CLI nor Docker available for surreal-validate")


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
    try:
        surreal_cmds = _surreal_commands(ctx.repo_root)
    except RuntimeError as exc:
        msg = str(exc)
        surreal_cmds = [
            [
                py,
                "-c",
                "import sys; print(sys.argv[1]); raise SystemExit(1)",
                msg,
            ]
        ]

    result = run_commands_as_stage(
        ctx,
        name="governance",
        commands=[
            [
                py,
                "tools/validate_mcp_config.py",
                "tests/fixtures/mcp_smoke_config.json",
            ],
            *surreal_cmds,
            [py, "scripts/governance/run_ci_drift_checks.py"],
        ],
        required=True,
    )
    result.artifacts.append(str(note_path.relative_to(ctx.run_dir).as_posix()))
    return result
