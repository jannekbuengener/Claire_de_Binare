"""Governance stage — MCP, Surreal, drift checks; policy-gate is mirror-only."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ci.lib.evidence import StageResult
from ci.lib.gitinfo import EXPECTED_REPOSITORY
from ci.stages._common import StageContext, python_executable, run_commands_as_stage

SURREAL_VERSION = "v3.1.5"
SURQL_FILES = (
    "infrastructure/surrealdb/context_intelligence_v0_deploy.surql",
    "infrastructure/surrealdb/context_intelligence_v0.surql",
)
DEFAULT_BRANCH = "main"
BP_BASELINE_REL = Path("docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json")


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


def probe_branch_protection_api(
    repo: str = EXPECTED_REPOSITORY, branch: str = DEFAULT_BRANCH
) -> bool:
    """Return True when live branch-protection JSON is readable via gh api."""
    if shutil.which("gh") is None:
        return False
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/{branch}/protection"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def build_drift_checks_command(
    *,
    python_exe: str,
    repo_root: Path,
    reports_dir: Path,
    repo: str = EXPECTED_REPOSITORY,
    branch: str = DEFAULT_BRANCH,
) -> list[str]:
    """Build run_ci_drift_checks command; offline BP fallback when API unavailable.

    Non-admin tokens (GitHub Actions GITHUB_TOKEN, Cloud Agent ghs_) cannot read
    classic Branch Protection. Required-contexts drift remains file-based and
    always runs. Offline BP mode compares the committed baseline to itself and
    writes an explicit live-unavailable disclosure — not a silent Fake-Green.
    Hosts with BP-read PAT keep the live check.
    """
    cmd = [python_exe, "scripts/governance/run_ci_drift_checks.py"]
    if probe_branch_protection_api(repo, branch):
        return cmd

    baseline = repo_root / BP_BASELINE_REL
    reports_dir.mkdir(parents=True, exist_ok=True)
    offline = reports_dir / "branch-protection-offline-current.json"
    if baseline.exists():
        offline.write_text(baseline.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        offline.write_text("{}\n", encoding="utf-8")
    disclosure = {
        "check": "branch_protection_drift",
        "live_status": "live_unavailable",
        "fallback": "offline_baseline_as_current",
        "baseline": BP_BASELINE_REL.as_posix(),
        "offline_current": offline.name,
        "reason": (
            "gh api branch protection not readable (typically 403 for non-admin "
            "integration tokens). Required-contexts drift still runs live against "
            "workflow files. Live BP verify remains required on hosts that publish "
            "cdb-local-ci with a PAT that can read protection."
        ),
        "required_context_contract": "cdb-local-ci",
    }
    (reports_dir / "branch-protection-live-unavailable.json").write_text(
        json.dumps(disclosure, indent=2) + "\n", encoding="utf-8"
    )
    cmd.extend(["--branch-protection-current-json", str(offline)])
    return cmd


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
    (ctx.repo_root / "artifacts" / "reports" / "governance").mkdir(
        parents=True, exist_ok=True
    )
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

    drift_cmd = build_drift_checks_command(
        python_exe=py,
        repo_root=ctx.repo_root,
        reports_dir=ctx.reports_dir,
    )

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
            drift_cmd,
        ],
        required=True,
    )
    result.artifacts.append(str(note_path.relative_to(ctx.run_dir).as_posix()))
    unavailable = ctx.reports_dir / "branch-protection-live-unavailable.json"
    if unavailable.exists():
        result.artifacts.append(str(unavailable.relative_to(ctx.run_dir).as_posix()))
    return result
