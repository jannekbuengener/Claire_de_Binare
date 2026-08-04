"""Manifest-consuming sensitivity campaign runner (#4153).

CLI:
  python -m tools.arvp_vacation.sensitivity_campaign_runner plan --manifest PATH
  python -m tools.arvp_vacation.sensitivity_campaign_runner validate-authorization ...
  python -m tools.arvp_vacation.sensitivity_campaign_runner execute ...
  python -m tools.arvp_vacation.sensitivity_campaign_runner probe-surface ...

``plan`` and ``validate-authorization`` are write-free.
``execute`` requires a live-verified Owner-GO and an injected executor; the
default production executor refuses real replays in this contract slice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from tools.arvp_vacation.sensitivity_campaign_analyzer_contract import (
    classify_overlap_slots,
)
from tools.arvp_vacation.sensitivity_campaign_authorization import (
    DEFAULT_REPO,
    ISSUE_NUMBER,
    MANIFEST_ID,
    MANIFEST_PATH,
    RUNNER_CONTRACT_VERSION,
    SensitivityAuthorizationError,
    assert_absolute_bans_intact,
    campaign_execution_requires_owner_go,
    verify_owner_go_comment,
)
from tools.arvp_vacation.sensitivity_campaign_budget import (
    SensitivityBudgetError,
    assert_disk_budget,
    assert_failure_thresholds,
    validate_resource_budget,
)
from tools.arvp_vacation.sensitivity_campaign_executor import (
    CampaignRunExecutor,
    RefusingRealExecutor,
    RunEnvelope,
)
from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    MAX_RUN_COUNT,
)
from tools.arvp_vacation.sensitivity_campaign_preflight import (
    VERDICT_READY,
    VERDICT_READY_CAMPAIGN,
    run_manifest_preflight,
    run_repo_preflight,
)
from tools.arvp_vacation.sensitivity_campaign_reproduction import (
    build_reproduction_plan,
)
from tools.arvp_vacation.sensitivity_campaign_run_plan import (
    EVIDENCE_NAMESPACE_ROOT,
    build_run_plan,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    CampaignBindings,
    SensitivityStateError,
    assert_namespace_startable,
    commit_successful_result,
    evidence_root_for,
    inspect_run_for_resume,
    write_campaign_envelope,
    write_run_envelope,
)
from tools.arvp_vacation.sensitivity_campaign_surface import (
    SensitivitySurfaceError,
    assert_surface_matches_authorization,
    probe_execution_surface,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import (
    SensitivityManifestError,
    fingerprint_manifest,
    load_manifest,
    validate_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SensitivityRunnerError(ValueError):
    """Fail-closed runner error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


def _git_head_sha(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        raise SensitivityRunnerError("RUNNER_GIT_HEAD_UNAVAILABLE", str(exc)) from exc
    sha = out.strip()
    if len(sha) != 40:
        raise SensitivityRunnerError("RUNNER_GIT_HEAD_INVALID", sha)
    return sha


def _window_content_fp(manifest: Mapping[str, Any], window_id: str) -> str:
    for binding in manifest.get("window_bindings") or []:
        if binding.get("window_id") == window_id:
            return str(binding.get("content_fingerprint") or "")
    return ""


def _seed_for(campaign_id: str, window_id: str, variant_id: str) -> str:
    raw = f"{campaign_id}|{window_id}|{variant_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _emit(payload: Mapping[str, Any], stream: TextIO) -> None:
    stream.write(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n")


def _preflight_ready(repo_root: Path, manifest: Mapping[str, Any]) -> None:
    repo_report = run_repo_preflight(repo_root)
    repo_verdict = str((repo_report or {}).get("verdict") or "")
    if repo_verdict != VERDICT_READY:
        raise SensitivityRunnerError("RUNNER_REPO_PREFLIGHT_NOT_READY", repo_verdict)

    man_report = run_manifest_preflight(dict(manifest), repo_root)
    man_verdict = str((man_report or {}).get("verdict") or "")
    if man_verdict != VERDICT_READY_CAMPAIGN:
        raise SensitivityRunnerError("RUNNER_MANIFEST_PREFLIGHT_NOT_READY", man_verdict)


def plan_campaign(
    *,
    manifest_path: Path,
    repo_root: Path | None = None,
    main_sha: str | None = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """Write-free dry plan: validates + expands; creates zero files."""
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    assert_absolute_bans_intact(manifest)
    if not campaign_execution_requires_owner_go(manifest):
        raise SensitivityRunnerError("RUNNER_AUTH_POLICY_INCONSISTENT")

    _preflight_ready(root, manifest)
    sha = main_sha or _git_head_sha(root)
    plan = build_run_plan(manifest, main_sha=sha)
    overlap = classify_overlap_slots()
    reproduction = build_reproduction_plan(
        run_keys=plan.run_keys, policy=plan.reproduction_policy
    )

    payload = {
        "command": "plan",
        "writes": False,
        "replays": False,
        "main_sha": plan.main_sha,
        "manifest_path": str(manifest_path),
        "manifest_id": manifest.get("campaign_id"),
        "manifest_fingerprint": plan.manifest_fingerprint,
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "runner_contract_version": RUNNER_CONTRACT_VERSION,
        "strategy_set": [plan.strategy_id],
        "window_count": plan.window_count,
        "matrix_slots": plan.matrix_slots,
        "physical_parameter_sets": plan.physical_parameter_sets,
        "run_count": plan.run_count,
        "run_keys_count": len(plan.run_keys),
        "expected_run_count": EXPECTED_RUN_COUNT,
        "max_run_count": MAX_RUN_COUNT,
        "holdout_runs": 0,
        "oos_runs": 0,
        "stress_runs": 0,
        "stage_b_runs": 0,
        "paper_live_order_runs": 0,
        "evidence_namespace": EVIDENCE_NAMESPACE_ROOT,
        "evidence_root_template": plan.evidence_root_template,
        "surface_requirement_profile": plan.surface_requirement_profile,
        "resource_budget_contract": plan.resource_budget_contract,
        "resume_policy": plan.resume_policy,
        "reproduction_plan": reproduction,
        "analyzer_plan": {
            "matrix_slots": overlap["matrix_slots"],
            "physical_parameter_sets": overlap["physical_parameter_sets"],
            "overlaps": overlap["overlaps"],
            "rules": overlap["rules"],
        },
        "required_authorization_fields": [
            "schema_version",
            "status",
            "bound_main_sha",
            "manifest_fingerprint",
            "run_plan_fingerprint",
            "execution_surface_id",
            "surface_capability_fingerprint",
            "resource_budget",
        ],
        "lr_status": "NO-GO",
        "campaign_execution_authorized": False,
    }
    _emit(payload, out)
    return payload


def validate_authorization_command(
    *,
    manifest_path: Path,
    go_comment_id: int,
    repo_root: Path | None = None,
    main_sha: str | None = None,
    repository: str = DEFAULT_REPO,
    authorizing_github_login: str | None = None,
    surface_id: str | None = None,
    surface_capability_fingerprint: str | None = None,
    resource_budget: Mapping[str, Any] | None = None,
    fetcher: Any = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    assert_absolute_bans_intact(manifest)
    _preflight_ready(root, manifest)
    sha = main_sha or _git_head_sha(root)
    plan = build_run_plan(manifest, main_sha=sha)

    expected: dict[str, Any] = {
        "bound_main_sha": sha,
        "manifest_path": MANIFEST_PATH,
        "manifest_id": MANIFEST_ID,
        "manifest_fingerprint": plan.manifest_fingerprint,
        "correctness_baseline_sha": manifest.get("correctness_baseline_sha"),
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "runner_contract_version": RUNNER_CONTRACT_VERSION,
        "strategy_set": [plan.strategy_id],
        "selection_sha256": (manifest.get("development_windows") or {}).get(
            "selection_sha256"
        ),
        "window_count": 39,
        "matrix_slots": 21,
        "run_keys": 819,
        "expected_run_count": 819,
        "max_run_count": 819,
        "evidence_namespace": EVIDENCE_NAMESPACE_ROOT,
        "analyzer_contract_version": plan.analyzer_contract_version,
        "resume_policy": plan.resume_policy,
        "reproduction_policy": plan.reproduction_policy,
    }
    if authorizing_github_login:
        expected["authorizing_github_login"] = authorizing_github_login
    if surface_id:
        expected["execution_surface_id"] = surface_id
    if surface_capability_fingerprint:
        expected["surface_capability_fingerprint"] = surface_capability_fingerprint
    if resource_budget is not None:
        expected["resource_budget"] = dict(resource_budget)

    try:
        result = verify_owner_go_comment(
            comment_id=go_comment_id,
            expected=expected,
            repository=repository,
            issue=ISSUE_NUMBER,
            fetcher=fetcher,
        )
    except SensitivityAuthorizationError as exc:
        payload = {
            "command": "validate-authorization",
            "valid": False,
            "reason_code": exc.reason_code,
            "detail": str(exc),
            "writes": False,
            "replays": False,
            "lr_status": "NO-GO",
        }
        _emit(payload, out)
        return payload

    payload = {
        "command": "validate-authorization",
        "valid": True,
        "reason_code": "AUTH_GO_VALID",
        "authorization_fingerprint": result["authorization_fingerprint"],
        "github_comment_id": go_comment_id,
        "authorizing_github_login": result["authorizing_github_login"],
        "comment_updated_at": result["comment_updated_at"],
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "manifest_fingerprint": plan.manifest_fingerprint,
        "writes": False,
        "replays": False,
        "lr_status": "NO-GO",
    }
    _emit(payload, out)
    return payload


def execute_campaign(
    *,
    manifest_path: Path,
    go_comment_id: int,
    executor: CampaignRunExecutor | None = None,
    repo_root: Path | None = None,
    artifacts_base: Path | None = None,
    main_sha: str | None = None,
    repository: str = DEFAULT_REPO,
    authorizing_github_login: str,
    surface_id: str,
    surface_capability_fingerprint: str | None = None,
    resource_budget: Mapping[str, Any] | None = None,
    dataset_root: Path | None = None,
    fetcher: Any = None,
    stream: TextIO | None = None,
    max_runs_override: int | None = None,
) -> dict[str, Any]:
    """Execute only with valid Owner-GO + budget + surface. Default executor refuses."""
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    if max_runs_override is not None and max_runs_override != EXPECTED_RUN_COUNT:
        # Tests may pass a subset only via FakeExecutor orchestration helpers —
        # production path forbids altering run count.
        raise SensitivityRunnerError(
            "RUNNER_RUN_COUNT_OVERRIDE_FORBIDDEN", str(max_runs_override)
        )

    # Hard reject generic force pathways (no such flags accepted by argparse).
    active_executor = executor if executor is not None else RefusingRealExecutor()

    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    assert_absolute_bans_intact(manifest)
    bans = manifest.get("explicit_bans") or {}
    for key in (
        "campaign_execution_auto_start",
        "orders",
        "exchange_execution",
        "paper",
        "live",
        "echtgeld",
        "holdout",
        "oos",
        "stress",
        "stage_b",
        "promotion",
    ):
        if bans.get(key) is not True:
            raise SensitivityRunnerError("RUNNER_ABSOLUTE_BAN_INACTIVE", key)

    _preflight_ready(root, manifest)
    sha = main_sha or _git_head_sha(root)
    plan = build_run_plan(manifest, main_sha=sha)
    if plan.run_count != 819 or len(plan.run_keys) != 819:
        raise SensitivityRunnerError("RUNNER_RUN_COUNT_INVALID", str(plan.run_count))
    if "CDB-021" in str(manifest.get("strategies")) or (
        (manifest.get("parameter_grid") or {}).get("cdb_021") not in (None, "OUT")
        and (manifest.get("parameter_grid") or {}).get("cdb_021") != "OUT"
    ):
        # CDB-021 must remain OUT.
        pg = manifest.get("parameter_grid") or {}
        if pg.get("cdb_021") != "OUT":
            raise SensitivityRunnerError("RUNNER_CDB021_NOT_OUT")

    budget = validate_resource_budget(resource_budget)

    probe = probe_execution_surface(
        repo_root=root,
        dataset_root=dataset_root,
        surface_id=surface_id,
        exchange_credentials_present=False,
        window_availability={"expected_windows": 39},
    )
    expected_fp = surface_capability_fingerprint or probe.surface_capability_fingerprint
    assert_surface_matches_authorization(
        probe=probe,
        expected_surface_id=surface_id,
        expected_capability_fingerprint=expected_fp,
    )
    assert_disk_budget(
        budget=budget,
        free_disk_bytes=int(probe.surface.get("free_artifact_bytes") or 0),
        projected_artifact_bytes=0,
    )

    expected = {
        "authorizing_github_login": authorizing_github_login,
        "bound_main_sha": sha,
        "manifest_path": MANIFEST_PATH,
        "manifest_id": MANIFEST_ID,
        "manifest_fingerprint": plan.manifest_fingerprint,
        "correctness_baseline_sha": manifest.get("correctness_baseline_sha"),
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "runner_contract_version": RUNNER_CONTRACT_VERSION,
        "strategy_set": [plan.strategy_id],
        "selection_sha256": (manifest.get("development_windows") or {}).get(
            "selection_sha256"
        ),
        "window_count": 39,
        "matrix_slots": 21,
        "run_keys": 819,
        "expected_run_count": 819,
        "max_run_count": 819,
        "execution_surface_id": surface_id,
        "surface_capability_fingerprint": expected_fp,
        "resource_budget": dict(budget),
        "evidence_namespace": EVIDENCE_NAMESPACE_ROOT,
        "analyzer_contract_version": plan.analyzer_contract_version,
        "resume_policy": plan.resume_policy,
        "reproduction_policy": plan.reproduction_policy,
    }
    auth = verify_owner_go_comment(
        comment_id=go_comment_id,
        expected=expected,
        repository=repository,
        issue=ISSUE_NUMBER,
        fetcher=fetcher,
    )
    auth_fp = str(auth["authorization_fingerprint"])
    auth_id = auth_fp[:16]

    base = artifacts_base if artifacts_base is not None else root
    evidence_root = evidence_root_for(
        base=base,
        campaign_id=plan.campaign_id,
        manifest_fingerprint=plan.manifest_fingerprint,
        authorization_id=auth_id,
    )
    bindings = CampaignBindings(
        campaign_id=plan.campaign_id,
        manifest_fingerprint=plan.manifest_fingerprint,
        run_plan_fingerprint=plan.run_plan_fingerprint,
        authorization_fingerprint=auth_fp,
        execution_sha=sha,
        main_sha=sha,
    )
    mode = assert_namespace_startable(
        evidence_root,
        bindings=bindings,
        allow_resume=bool(plan.resume_policy.get("allow_resume")),
    )
    write_campaign_envelope(
        evidence_root,
        bindings=bindings,
        run_count=plan.run_count,
        extra={"namespace_mode": mode, "github_comment_id": go_comment_id},
    )

    consecutive_failures = 0
    total_failures = 0
    succeeded = 0
    skipped = 0
    failed = 0
    eff_fp = str(manifest.get("effective_config_snapshot_fingerprint") or "")

    # Parallelism is hard-capped; this slice runs sequentially but enforces the
    # configured max_parallelism as an upper bound (no fan-out above budget).
    if int(budget["max_parallelism"]) < 1:
        raise SensitivityRunnerError("RUNNER_PARALLELISM_INVALID")

    for planned in plan.runs:
        try:
            action = inspect_run_for_resume(
                evidence_root,
                run_key=planned.run_key,
                bindings=bindings,
                max_attempts=int(budget["max_attempts_per_run"]),
                retry_failed=bool(plan.resume_policy.get("retry_failed")),
            )
        except SensitivityStateError as exc:
            raise SensitivityRunnerError("RUNNER_RESUME_BLOCKED", str(exc)) from exc

        if action == "skip":
            skipped += 1
            continue

        attempt = 1
        env_path = evidence_root / "runs" / planned.run_key / "run_envelope.json"
        if env_path.exists() and action == "retry":
            prev = json.loads(env_path.read_text(encoding="utf-8"))
            attempt = int(prev.get("attempt") or 0) + 1

        envelope = RunEnvelope(
            run_key=planned.run_key,
            campaign_id=plan.campaign_id,
            manifest_fingerprint=plan.manifest_fingerprint,
            execution_sha=sha,
            window_id=planned.window_id,
            strategy_id=planned.strategy_id,
            parameters=dict(planned.param_set),
            slot_id=planned.slot_id,
            phase=planned.phase,
            label=planned.label,
            physical_parameter_set_fingerprint=(
                planned.physical_parameter_set_fingerprint
            ),
            effective_config_fingerprint=eff_fp,
            dataset_content_fingerprint=_window_content_fp(manifest, planned.window_id),
            seed=_seed_for(plan.campaign_id, planned.window_id, planned.slot_id),
            output_dir=str(evidence_root / "runs" / planned.run_key),
            run_plan_fingerprint=plan.run_plan_fingerprint,
            authorization_fingerprint=auth_fp,
            attempt=attempt,
            reproduction_attempt=0,
        )
        write_run_envelope(
            evidence_root,
            run_key=planned.run_key,
            bindings=bindings,
            status="RUNNING",
            attempt=attempt,
            envelope=envelope.as_dict(),
        )
        result = active_executor.execute(envelope)
        if result.exit_code != 0:
            failed += 1
            consecutive_failures += 1
            total_failures += 1
            write_run_envelope(
                evidence_root,
                run_key=planned.run_key,
                bindings=bindings,
                status="FAILED",
                attempt=attempt,
                envelope=envelope.as_dict(),
                exit_code=result.exit_code,
            )
            try:
                assert_failure_thresholds(
                    budget=budget,
                    consecutive_failures=consecutive_failures,
                    total_failures=total_failures,
                )
            except SensitivityBudgetError as exc:
                payload = {
                    "command": "execute",
                    "status": "BLOCKED",
                    "reason_code": str(exc),
                    "succeeded": succeeded,
                    "failed": failed,
                    "skipped": skipped,
                    "lr_status": "NO-GO",
                }
                _emit(payload, out)
                return payload
            continue

        consecutive_failures = 0
        commit_successful_result(
            evidence_root,
            run_key=planned.run_key,
            bindings=bindings,
            attempt=attempt,
            envelope=envelope.as_dict(),
            result=result.metrics,
            exit_code=0,
        )
        succeeded += 1

    payload = {
        "command": "execute",
        "status": "COMPLETED" if failed == 0 else "COMPLETED_WITH_FAILURES",
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "run_count": plan.run_count,
        "evidence_root": str(evidence_root),
        "authorization_fingerprint": auth_fp,
        "run_plan_fingerprint": plan.run_plan_fingerprint,
        "lr_status": "NO-GO",
    }
    _emit(payload, out)
    return payload


def probe_surface_command(
    *,
    surface_id: str,
    repo_root: Path | None = None,
    dataset_root: Path | None = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    probe = probe_execution_surface(
        repo_root=root,
        dataset_root=dataset_root,
        surface_id=surface_id,
    )
    payload = probe.as_dict()
    payload["command"] = "probe-surface"
    payload["writes"] = False
    _emit(payload, out)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.arvp_vacation.sensitivity_campaign_runner",
        description=(
            "Replay-only #4153 sensitivity campaign runner "
            "(plan / validate-authorization / execute). LR=NO-GO."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Write-free dry plan (no files, no replays)")
    p_plan.add_argument(
        "--manifest",
        type=Path,
        default=Path(MANIFEST_PATH),
        help="Path to executable campaign manifest",
    )
    p_plan.add_argument("--main-sha", default=None)

    p_val = sub.add_parser(
        "validate-authorization",
        help="Validate structured GitHub Owner-GO (no writes, no replays)",
    )
    p_val.add_argument("--manifest", type=Path, default=Path(MANIFEST_PATH))
    p_val.add_argument("--go-comment-id", type=int, required=True)
    p_val.add_argument("--repository", default=DEFAULT_REPO)
    p_val.add_argument("--authorizing-github-login", required=True)
    p_val.add_argument("--surface-id", required=True)
    p_val.add_argument("--surface-capability-fingerprint", required=True)
    p_val.add_argument(
        "--resource-budget-json",
        required=True,
        help="JSON object with required budget fields",
    )
    p_val.add_argument("--main-sha", default=None)

    p_exec = sub.add_parser(
        "execute",
        help="Execute campaign only with valid Owner-GO (refuses without executor GO)",
    )
    p_exec.add_argument("--manifest", type=Path, default=Path(MANIFEST_PATH))
    p_exec.add_argument("--go-comment-id", type=int, required=True)
    p_exec.add_argument("--repository", default=DEFAULT_REPO)
    p_exec.add_argument("--authorizing-github-login", required=True)
    p_exec.add_argument("--surface-id", required=True)
    p_exec.add_argument("--surface-capability-fingerprint", required=True)
    p_exec.add_argument("--resource-budget-json", required=True)
    p_exec.add_argument("--dataset-root", type=Path, default=None)
    p_exec.add_argument("--artifacts-base", type=Path, default=None)
    p_exec.add_argument("--main-sha", default=None)
    # Intentionally NO --force / --yes / --admin / --resume-anyway flags.

    p_probe = sub.add_parser("probe-surface", help="Read-only surface capability probe")
    p_probe.add_argument("--surface-id", required=True)
    p_probe.add_argument("--dataset-root", type=Path, default=None)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "plan":
            plan_campaign(manifest_path=args.manifest, main_sha=args.main_sha)
            return 0
        if args.command == "probe-surface":
            probe_surface_command(
                surface_id=args.surface_id, dataset_root=args.dataset_root
            )
            return 0
        if args.command == "validate-authorization":
            budget = json.loads(args.resource_budget_json)
            result = validate_authorization_command(
                manifest_path=args.manifest,
                go_comment_id=args.go_comment_id,
                repository=args.repository,
                authorizing_github_login=args.authorizing_github_login,
                surface_id=args.surface_id,
                surface_capability_fingerprint=args.surface_capability_fingerprint,
                resource_budget=budget,
                main_sha=args.main_sha,
            )
            return 0 if result.get("valid") else 2
        if args.command == "execute":
            budget = json.loads(args.resource_budget_json)
            # Production CLI uses refusing executor — no real campaign in this slice.
            execute_campaign(
                manifest_path=args.manifest,
                go_comment_id=args.go_comment_id,
                executor=RefusingRealExecutor(),
                repository=args.repository,
                authorizing_github_login=args.authorizing_github_login,
                surface_id=args.surface_id,
                surface_capability_fingerprint=args.surface_capability_fingerprint,
                resource_budget=budget,
                dataset_root=args.dataset_root,
                artifacts_base=args.artifacts_base,
                main_sha=args.main_sha,
            )
            return 0
        parser.error(f"unknown command {args.command}")
        return 2
    except (
        SensitivityRunnerError,
        SensitivityAuthorizationError,
        SensitivityBudgetError,
        SensitivitySurfaceError,
        SensitivityStateError,
        SensitivityManifestError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        err = {
            "status": "BLOCKED",
            "reason_code": getattr(exc, "reason_code", type(exc).__name__),
            "detail": str(exc),
            "lr_status": "NO-GO",
        }
        _emit(err, sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
