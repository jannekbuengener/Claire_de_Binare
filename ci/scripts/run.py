#!/usr/bin/env python3
"""Canonical local Docker CI orchestrator (Phase 1).

Windows preferred front door:
  pwsh -File ci/scripts/run_all.ps1

This does NOT publish a GitHub Required Check. Branch Protection stays unchanged.
"""

from __future__ import annotations

import argparse
import json
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
    StageResult,
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
from ci.lib.slice_selection import (  # noqa: E402
    default_policy_path,
    normalize_changed_paths,
    select_slice_test_groups,
)
from ci.lib.temp_preflight import (  # noqa: E402
    prepare_ci_temp_root,
    temp_env_for,
    write_temp_preflight_report,
)
from ci.stages import containers as stage_containers  # noqa: E402
from ci.stages import docs as stage_docs  # noqa: E402
from ci.stages import governance as stage_governance  # noqa: E402
from ci.stages import integration as stage_integration  # noqa: E402
from ci.stages import lint as stage_lint  # noqa: E402
from ci.stages import mcp_dependency_closure  # noqa: E402
from ci.stages import report as stage_report  # noqa: E402
from ci.stages import security as stage_security  # noqa: E402
from ci.stages import unit as stage_unit  # noqa: E402
from ci.stages._common import StageContext  # noqa: E402

STAGE_RUNNERS = {
    "mcp_dependency_closure": mcp_dependency_closure.run,
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


def _changed_paths_vs_base(repo_root: Path, base_ref: str = "origin/main") -> list[str]:
    """Return sorted changed paths vs base_ref (name-status, including renames)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Fail closed: empty list triggers unclassified/full fallback upstream.
        return []
    return list(normalize_changed_paths(result.stdout.splitlines()))


def run_ci(
    *,
    profile: str,
    stage: str | None,
    run_id: str | None,
    repo_root: Path,
    slice_mode: bool = False,
    changed_paths: list[str] | None = None,
    routing_lane: str = "",
    validation_profile: str = "",
    unit_durations: int = 50,
) -> int:
    cfg_dir = repo_root / "ci" / "config"
    stages_cfg = load_yaml(cfg_dir / "stages.yaml")
    resources = load_yaml(cfg_dir / "resources.yaml")
    profiles = profiles_from_config(stages_cfg)

    if slice_mode and profile == "fast":
        profile = "slice"
    if profile not in profiles:
        raise SystemExit(
            f"Unknown profile {profile!r}; expected one of {sorted(profiles)}"
        )

    merge_evidence = profile != "slice" and not slice_mode
    slice_selection_payload = None
    if profile == "slice" or slice_mode:
        merge_evidence = False
        paths = list(
            normalize_changed_paths(
                changed_paths
                if changed_paths is not None
                else _changed_paths_vs_base(repo_root)
            )
        )
        selection = select_slice_test_groups(
            changed_paths=paths,
            routing_lane=routing_lane,
            validation_profile=validation_profile,
            policy_path=default_policy_path(repo_root),
        )
        slice_selection_payload = selection.to_dict()
        print(
            f"slice_selection groups={selection.selected_test_groups} "
            f"fallback={selection.fallback_reason!r} merge_evidence=false"
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

    if slice_selection_payload is not None:
        slice_report = run_dir / "reports" / "slice_selection.json"
        slice_report.write_text(
            json.dumps(slice_selection_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    started = utc_now()
    ctx = StageContext(
        repo_root=repo_root,
        run_dir=run_dir,
        run_id=rid,
        git=git,
        profile=profile,
        resources=resources,
        slice_selection=slice_selection_payload,
        merge_evidence=merge_evidence,
        unit_durations=unit_durations,
    )

    selected = [stage] if stage else list(profiles[profile])
    # Always append report aggregation for full/profile runs; for single-stage,
    # still produce a report unless stage==report.
    stage_results: list[StageResult] = []
    skipped_checks = [
        {
            "check": "policy-gate",
            "skip_reason": "GitHub-native PR API evaluation; local mirror only in Phase 1",
        }
    ]
    if not merge_evidence:
        skipped_checks.append(
            {
                "check": "merge_evidence",
                "skip_reason": "slice_profile_merge_evidence_false",
            }
        )

    # Temp-root preflight before any pytest/unit collection (#4205).
    print("==> stage temp_preflight")
    preflight_started = utc_now()
    preflight = prepare_ci_temp_root(run_dir, rid, repo_root=repo_root)
    preflight_report = run_dir / "reports" / "temp_preflight.json"
    write_temp_preflight_report(preflight_report, preflight)
    preflight_ended = utc_now()
    preflight_stage = StageResult(
        name="temp_preflight",
        status="PASS" if preflight.ok else "FAIL",
        exit_code=0 if preflight.ok else 1,
        started_at_utc=preflight_started,
        ended_at_utc=preflight_ended,
        duration_seconds=0.0,
        command_summary=[f"prepare_ci_temp_root:{preflight.reason_code}"],
        log_path="",
        artifacts=["reports/temp_preflight.json"],
        skip_reason=None if preflight.ok else preflight.reason_code,
        required=True,
    )
    stage_results.append(preflight_stage)
    skipped_checks.append(
        {
            "check": "temp_root",
            "skip_reason": f"{preflight.reason_code}:{preflight.redacted_root}",
        }
    )

    if not preflight.ok:
        print(f"temp_preflight FAIL reason_code={preflight.reason_code}")
        report_result = stage_report.run(ctx, stage_results)
        stage_results.append(report_result)
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
            merge_evidence=merge_evidence,
        )
        write_manifest(run_dir, manifest)
        print(f"overall_status={manifest['overall_status']}")
        print(f"evidence={run_dir}")
        return 1

    ctx.temp_root = preflight.temp_root
    ctx.temp_env = temp_env_for(preflight.temp_root)

    if "unit" in selected:
        print("==> stage mcp_dependency_closure", flush=True)
        result = mcp_dependency_closure.run(ctx)
        print(
            f"<== stage mcp_dependency_closure status={result.status} exit={result.exit_code}",
            flush=True,
        )
        stage_results.append(result)
        if result.status != "PASS":
            report_result = stage_report.run(ctx, stage_results)
            stage_results.append(report_result)
            artifact_paths = sorted(run_dir.rglob("*"))
            artifact_paths = [path for path in artifact_paths if path.is_file()]
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
                    "pytest": _tool_version(
                        [sys.executable, "-m", "pytest", "--version"]
                    ),
                },
                docker_version=docker_v,
                compose_version=compose_v,
                profile=profile if not stage else f"stage:{stage}",
                stages=stage_results,
                skipped_checks=skipped_checks,
                artifact_hashes=artifact_hashes,
                repo_name=git.repo_name,
                merge_evidence=merge_evidence,
            )
            write_manifest(run_dir, manifest)
            print(f"overall_status={manifest['overall_status']}", flush=True)
            print(f"evidence={run_dir}", flush=True)
            return 1

    for name in selected:
        if name == "report":
            continue
        runner = STAGE_RUNNERS.get(name)
        if runner is None:
            raise SystemExit(f"Unknown stage: {name}")
        print(f"==> stage {name}", flush=True)
        result = runner(ctx)
        print(
            f"<== stage {name} status={result.status} exit={result.exit_code}",
            flush=True,
        )
        stage_results.append(result)

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
        merge_evidence=merge_evidence,
    )
    write_manifest(run_dir, manifest)

    # Re-hash after manifest write is intentionally NOT included in artifact_hashes
    # inside manifest (manifest.sha256 covers the finalized JSON).
    print(f"overall_status={manifest['overall_status']}", flush=True)
    print(f"merge_evidence={manifest.get('merge_evidence')}", flush=True)
    print(f"evidence={run_dir}", flush=True)
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
        choices=["fast", "slice", "heavy"],
        help=(
            "fast=full lint/unit/docs/governance (merge evidence eligible); "
            "slice=same stages with path-selected unit tests (merge_evidence=false); "
            "heavy adds integration/security/containers"
        ),
    )
    parser.add_argument("--stage", default=None, help="Run a single named stage")
    parser.add_argument("--run-id", default=None, help="Optional explicit run id")
    parser.add_argument(
        "--slice",
        action="store_true",
        help="Enable slice selection (forces merge_evidence=false)",
    )
    parser.add_argument(
        "--changed-path",
        action="append",
        default=None,
        dest="changed_paths",
        help="Changed path for slice selection (repeatable); default: git vs origin/main",
    )
    parser.add_argument(
        "--routing-lane",
        default="",
        help="PR-router lane input for slice selection",
    )
    parser.add_argument(
        "--validation-profile",
        default="",
        help="PR-router validation_profile input for slice selection",
    )
    parser.add_argument(
        "--unit-durations",
        type=int,
        default=50,
        help="Pass --durations=N to pytest unit stage (0 disables)",
    )
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
        slice_mode=bool(args.slice),
        changed_paths=args.changed_paths,
        routing_lane=args.routing_lane,
        validation_profile=args.validation_profile,
        unit_durations=int(args.unit_durations),
    )


if __name__ == "__main__":
    raise SystemExit(main())
