#!/usr/bin/env python3
"""Canonical local Docker CI orchestrator (Phase 1).

Windows preferred front door:
  pwsh -File ci/scripts/run_all.ps1

This does NOT publish a GitHub Required Check. Branch Protection stays unchanged.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import uuid
from pathlib import Path

# Ensure repo root is on sys.path when invoked as a script.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ci.lib.config import load_yaml, profiles_from_config  # noqa: E402
from ci.lib.evidence import (  # noqa: E402
    assert_run_id_available,
    assert_safe_cleanup_project,
    build_manifest,
    compose_project_name,
    hash_artifacts,
    load_and_validate_manifest,
    utc_now,
    write_manifest,
)
from ci.lib.gitinfo import collect_git_info  # noqa: E402
from ci.stages import containers as stage_containers  # noqa: E402
from ci.stages import docs as stage_docs  # noqa: E402
from ci.stages import governance as stage_governance  # noqa: E402
from ci.stages import integration as stage_integration  # noqa: E402
from ci.stages import lint as stage_lint  # noqa: E402
from ci.stages import report as stage_report  # noqa: E402
from ci.stages import security as stage_security  # noqa: E402
from ci.stages import unit as stage_unit  # noqa: E402
from ci.stages._common import StageContext  # noqa: E402

STAGE_RUNNERS = {
    "lint": stage_lint.run,
    "unit": stage_unit.run,
    "docs": stage_docs.run,
    "governance": stage_governance.run,
    "integration": stage_integration.run,
    "security": stage_security.run,
    "containers": stage_containers.run,
}


def _tool_version(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=30
        )
        out = (result.stdout or result.stderr or "").strip().splitlines()
        return out[0] if out else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def _docker_versions() -> tuple[str, str]:
    docker_v = _tool_version(["docker", "version", "--format", "{{.Server.Version}}"])
    compose_v = _tool_version(["docker", "compose", "version", "--short"])
    return docker_v, compose_v


def cleanup_compose_project(run_id: str, repo_root: Path) -> int:
    """Tear down only cdb_ci_<run_id> — never unrelated projects."""
    project = compose_project_name(run_id)
    assert_safe_cleanup_project(project)
    cmd = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        "infrastructure/compose/base.yml",
        "-f",
        "infrastructure/compose/test.yml",
        "down",
        "--remove-orphans",
    ]
    result = subprocess.run(cmd, cwd=str(repo_root), check=False)
    return result.returncode


def render_latest_report(artifacts_root: Path) -> int:
    runs = sorted(
        [p for p in artifacts_root.iterdir() if p.is_dir() and p.name != ".gitkeep"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not runs:
        print("No local CI runs found under ci/artifacts/")
        return 1
    latest = runs[0]
    try:
        manifest = load_and_validate_manifest(latest)
    except Exception as exc:  # noqa: BLE001 — operator-facing report
        print(f"FAIL: cannot validate {latest}: {exc}")
        return 1
    print(f"run_id={manifest['run_id']}")
    print(f"commit_sha={manifest['commit_sha']}")
    print(f"dirty_worktree={manifest['dirty_worktree']}")
    print(f"overall_status={manifest['overall_status']}")
    print(f"profile={manifest['profile']}")
    for stage in manifest.get("stages", []):
        print(
            f"  - {stage['name']}: {stage['status']} "
            f"(exit={stage.get('exit_code')}, required={stage.get('required')})"
        )
    return 0 if manifest["overall_status"] == "PASS" else 1


def run_ci(
    *,
    profile: str,
    stage: str | None,
    run_id: str | None,
    repo_root: Path,
) -> int:
    cfg_dir = repo_root / "ci" / "config"
    stages_cfg = load_yaml(cfg_dir / "stages.yaml")
    resources = load_yaml(cfg_dir / "resources.yaml")
    profiles = profiles_from_config(stages_cfg)

    if profile not in profiles:
        raise SystemExit(
            f"Unknown profile {profile!r}; expected one of {sorted(profiles)}"
        )

    git = collect_git_info(repo_root)
    artifacts_root = repo_root / "ci" / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)

    rid = (
        run_id
        or f"{utc_now().replace(':', '').replace('-', '')}_{uuid.uuid4().hex[:8]}"
    )
    run_dir = assert_run_id_available(artifacts_root, rid)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "logs").mkdir()
    (run_dir / "reports").mkdir()

    started = utc_now()
    ctx = StageContext(
        repo_root=repo_root,
        run_dir=run_dir,
        run_id=rid,
        git=git,
        profile=profile,
        resources=resources,
    )

    selected = [stage] if stage else list(profiles[profile])
    # Always append report aggregation for full/profile runs; for single-stage,
    # still produce a report unless stage==report.
    stage_results = []
    skipped_checks = [
        {
            "check": "policy-gate",
            "skip_reason": "GitHub-native PR API evaluation; local mirror only in Phase 1",
        }
    ]

    for name in selected:
        if name == "report":
            continue
        runner = STAGE_RUNNERS.get(name)
        if runner is None:
            raise SystemExit(f"Unknown stage: {name}")
        print(f"==> stage {name}")
        stage_results.append(runner(ctx))

    report_result = stage_report.run(ctx, stage_results)
    stage_results.append(report_result)

    # Hash logs + reports before finalizing manifest (exclude manifest itself).
    artifact_paths = sorted(run_dir.rglob("*"))
    artifact_paths = [p for p in artifact_paths if p.is_file()]
    artifact_hashes = hash_artifacts(artifact_paths, relative_to=run_dir)

    ended = utc_now()
    docker_v, compose_v = _docker_versions()
    manifest = build_manifest(
        run_id=rid,
        commit_sha=git.commit_sha,
        branch=git.branch,
        dirty_worktree=git.dirty_worktree,
        started_at_utc=started,
        ended_at_utc=ended,
        host_platform=platform.platform(),
        tool_versions={
            "python": platform.python_version(),
            "ruff": _tool_version(["ruff", "--version"]),
            "pytest": _tool_version([sys.executable, "-m", "pytest", "--version"]),
        },
        docker_version=docker_v,
        compose_version=compose_v,
        profile=profile if not stage else f"stage:{stage}",
        stages=stage_results,
        skipped_checks=skipped_checks,
        artifact_hashes=artifact_hashes,
        repo_name=git.repo_name,
    )
    write_manifest(run_dir, manifest)

    # Re-hash after manifest write is intentionally NOT included in artifact_hashes
    # inside manifest (manifest.sha256 covers the finalized JSON).
    print(f"overall_status={manifest['overall_status']}")
    print(f"evidence={run_dir}")
    if manifest["overall_status"] == "PASS":
        return 0
    if manifest["overall_status"] == "BLOCKED":
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CDB local Docker CI Phase 1")
    parser.add_argument(
        "--profile",
        default="fast",
        choices=["fast", "heavy"],
        help="fast=lint/unit/docs/governance; heavy adds integration/security/containers",
    )
    parser.add_argument("--stage", default=None, help="Run a single named stage")
    parser.add_argument("--run-id", default=None, help="Optional explicit run id")
    parser.add_argument(
        "--cleanup",
        metavar="RUN_ID",
        help="Cleanup compose project cdb_ci_<RUN_ID> only",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Validate and print the most recent evidence report",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root (default: inferred)",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if args.cleanup:
        return cleanup_compose_project(args.cleanup, repo_root)
    if args.report:
        return render_latest_report(repo_root / "ci" / "artifacts")
    return run_ci(
        profile=args.profile,
        stage=args.stage,
        run_id=args.run_id,
        repo_root=repo_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
