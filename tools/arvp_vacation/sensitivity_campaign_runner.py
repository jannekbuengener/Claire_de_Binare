"""Manifest-consuming sensitivity campaign runner (#4153).

CLI:
  python -m tools.arvp_vacation.sensitivity_campaign_runner plan --manifest PATH
  python -m tools.arvp_vacation.sensitivity_campaign_runner validate-authorization ...
  python -m tools.arvp_vacation.sensitivity_campaign_runner adopt-primary-evidence ...
  python -m tools.arvp_vacation.sensitivity_campaign_runner execute ...
  python -m tools.arvp_vacation.sensitivity_campaign_runner probe-surface ...

``plan`` and ``validate-authorization`` are write-free.
``adopt-primary-evidence`` writes inventory + phase only (no primary rewrite).
``execute`` requires a live-verified Owner-GO. Default executor is the real
``StrategyReplayCampaignExecutor`` (still auth-gated; no GO ⇒ no runs).
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
from tools.arvp_vacation.sensitivity_campaign_analyzer import (
    SensitivityAnalyzerError,
    analyze_campaign,
)
from tools.arvp_vacation.sensitivity_campaign_to_pr import (
    CampaignToPrError,
    DEFAULT_HANDOFF_SUBDIR,
    prepare_delivery,
)
from tools.arvp_vacation.sensitivity_campaign_authorization import (
    DEFAULT_REPO,
    ISSUE_NUMBER,
    MANIFEST_ID,
    MANIFEST_PATH,
    RUNNER_CONTRACT_VERSION,
    SensitivityAuthorizationError,
    assert_absolute_bans_intact,
    assert_author_in_owner_allowlist,
    assert_authorization_lifetime_covers_budget,
    assert_authorization_not_expired_for_next_attempt,
    campaign_execution_requires_owner_go,
    verify_owner_go_comment,
)
from tools.arvp_vacation.sensitivity_campaign_budget import (
    SensitivityBudgetError,
    assert_disk_budget,
    assert_failure_thresholds,
    validate_resource_budget,
)
from tools.arvp_vacation.sensitivity_campaign_dataset_root import (
    DatasetRootIdentity,
    SensitivityDatasetRootError,
    resolve_and_verify_dataset_root,
)
from tools.arvp_vacation.sensitivity_campaign_executor import (
    ATTEMPT_KIND_PRIMARY,
    ATTEMPT_KIND_REPRODUCTION,
    CampaignRunExecutor,
    RunEnvelope,
    StrategyReplayCampaignExecutor,
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
from tools.arvp_vacation.sensitivity_campaign_primary_adoption import (
    SensitivityAdoptionError,
    adopt_primary_evidence,
    assert_adoption_inventory_allows_reproduction,
)
from tools.arvp_vacation.sensitivity_campaign_reproduction import (
    SensitivityReproductionError,
    build_reproduction_plan,
    compare_reproduction_results,
)
from tools.arvp_vacation.sensitivity_campaign_run_plan import (
    EVIDENCE_NAMESPACE_ROOT,
    build_run_plan,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_ENVELOPE_NAME,
    CAMPAIGN_PHASE_BLOCKED,
    CAMPAIGN_PHASE_COMPLETED,
    CAMPAIGN_PHASE_PLANNED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_PLANNED,
    CAMPAIGN_PHASE_PRIMARY_RUNNING,
    CAMPAIGN_PHASE_REPRODUCTION_COMPLETE,
    CAMPAIGN_PHASE_REPRODUCTION_PLANNED,
    CAMPAIGN_PHASE_REPRODUCTION_RUNNING,
    CampaignBindings,
    SensitivityStateError,
    acquire_campaign_lock,
    assert_namespace_startable,
    commit_successful_reproduction_result,
    commit_successful_result,
    count_primary_succeeded,
    evidence_root_for,
    inspect_reproduction_for_resume,
    inspect_run_for_resume,
    persist_reproduction_result,
    read_campaign_phase,
    read_json,
    release_campaign_lock,
    reproduction_dir,
    result_path,
    run_dir,
    update_campaign_phase,
    write_campaign_envelope,
    write_comparison_evidence,
    write_reproduction_envelope,
    write_run_envelope,
)
from tools.arvp_vacation.sensitivity_campaign_surface import (
    SensitivitySurfaceError,
    assert_surface_matches_authorization,
    probe_execution_surface,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import (
    SensitivityManifestError,
    load_manifest,
    validate_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class SensitivityRunnerError(ValueError):
    """Fail-closed runner error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


def _bind_executor_dataset_root(
    *,
    executor: CampaignRunExecutor | None,
    resolved_bank_root: Path | None,
) -> CampaignRunExecutor:
    """Ensure the production replay adapter consumes the verified dataset root.

    CLI historically constructed ``StrategyReplayCampaignExecutor()`` before
    ``dataset_root`` resolution; without rebinding, surface identity would
    reflect the external root while replays still used the repo-local bank.
    """
    if executor is None:
        return StrategyReplayCampaignExecutor(window_bank_root=resolved_bank_root)
    if resolved_bank_root is None:
        return executor
    if isinstance(executor, StrategyReplayCampaignExecutor):
        existing = executor.window_bank_root
        if existing is None:
            return StrategyReplayCampaignExecutor(
                replay_invoker=executor._replay_invoker,
                metrics_loader=executor._metrics_loader,
                adapter_id=executor._adapter_id,
                symbol=executor._symbol,
                speedup_profile=executor._speedup_profile,
                window_bank_root=resolved_bank_root,
            )
        if Path(existing).resolve() != Path(resolved_bank_root).resolve():
            raise SensitivityRunnerError(
                "RUNNER_DATASET_EXECUTOR_ROOT_MISMATCH",
                f"executor={existing} verified={resolved_bank_root}",
            )
        return executor
    return executor


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
    if not authorizing_github_login:
        raise SensitivityAuthorizationError("AUTH_EXPECTED_LOGIN_REQUIRED")
    expected["authorizing_github_login"] = assert_author_in_owner_allowlist(
        authorizing_github_login
    )
    if surface_id:
        expected["execution_surface_id"] = surface_id
    if surface_capability_fingerprint:
        expected["surface_capability_fingerprint"] = surface_capability_fingerprint
    if resource_budget is not None:
        expected["resource_budget"] = dict(validate_resource_budget(resource_budget))

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


def _load_primary_result(evidence_root: Path, run_key: str) -> dict[str, Any]:
    """Load the persisted primary result for a run key.

    Fail-closed if the marker/result is missing (partial success would already
    have been rejected during ``count_primary_succeeded``).
    """
    rpath = result_path(evidence_root, run_key)
    if not rpath.exists():
        raise SensitivityRunnerError("RUNNER_PRIMARY_RESULT_MISSING", f"{rpath}")
    body = read_json(rpath)
    if not isinstance(body.get("result"), Mapping):
        raise SensitivityRunnerError("RUNNER_PRIMARY_RESULT_MALFORMED", str(rpath))
    return dict(body["result"])


def _run_primary_loop(
    *,
    plan: Any,
    evidence_root: Path,
    bindings: CampaignBindings,
    budget: Mapping[str, Any],
    active_executor: CampaignRunExecutor,
    manifest: Mapping[str, Any],
    auth_fp: str,
    sha: str,
    auth_expiry: Any,
    now_utc_provider: Any,
) -> dict[str, Any]:
    consecutive_failures = 0
    total_failures = 0
    succeeded = 0
    skipped = 0
    failed = 0
    eff_fp = str(manifest.get("effective_config_snapshot_fingerprint") or "")

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

        # Pre-attempt authorization expiry gate.
        assert_authorization_not_expired_for_next_attempt(
            auth_expiry, now_utc=now_utc_provider()
        )

        attempt = 1
        env_path = run_dir(evidence_root, planned.run_key) / "run_envelope.json"
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
            output_dir=str(run_dir(evidence_root, planned.run_key)),
            run_plan_fingerprint=plan.run_plan_fingerprint,
            authorization_fingerprint=auth_fp,
            attempt=attempt,
            reproduction_attempt=0,
            attempt_kind=ATTEMPT_KIND_PRIMARY,
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
                return {
                    "phase_outcome": "BLOCKED",
                    "reason_code": str(exc),
                    "succeeded": succeeded,
                    "failed": failed,
                    "skipped": skipped,
                }
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

    return {
        "phase_outcome": "PRIMARY_COMPLETE",
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
    }


def _find_planned_run(plan: Any, run_key: str) -> Any:
    for planned in plan.runs:
        if planned.run_key == run_key:
            return planned
    raise SensitivityRunnerError("RUNNER_REPRO_RUN_KEY_UNKNOWN", run_key)


def _run_reproduction_loop(
    *,
    plan: Any,
    reproduction_plan: Mapping[str, Any],
    evidence_root: Path,
    bindings: CampaignBindings,
    budget: Mapping[str, Any],
    active_executor: CampaignRunExecutor,
    manifest: Mapping[str, Any],
    auth_fp: str,
    sha: str,
    auth_expiry: Any,
    now_utc_provider: Any,
) -> dict[str, Any]:
    eff_fp = str(manifest.get("effective_config_snapshot_fingerprint") or "")
    repro_succeeded = 0
    repro_failed = 0
    repro_skipped = 0
    mismatches: list[dict[str, Any]] = []
    on_mismatch = str(reproduction_plan.get("on_mismatch") or "")
    compared_fields = list(reproduction_plan.get("compared_result_fields") or [])

    for item in reproduction_plan.get("reproduction_items", []):
        run_key = str(item["run_key"])
        repro_attempt = int(item["reproduction_attempt"])

        try:
            action = inspect_reproduction_for_resume(
                evidence_root,
                run_key=run_key,
                reproduction_attempt=repro_attempt,
                bindings=bindings,
                max_attempts=int(budget["max_attempts_per_run"]),
                retry_failed=bool(plan.resume_policy.get("retry_failed")),
            )
        except SensitivityStateError as exc:
            raise SensitivityRunnerError(
                "RUNNER_REPRO_RESUME_BLOCKED", str(exc)
            ) from exc

        if action == "skip":
            repro_skipped += 1
            continue

        if action == "finalize":
            # Crash window after PASS comparison, before success marker.
            env_path = (
                reproduction_dir(evidence_root, run_key, repro_attempt)
                / "run_envelope.json"
            )
            prev = json.loads(env_path.read_text(encoding="utf-8"))
            repro_result_body = read_json(
                reproduction_dir(evidence_root, run_key, repro_attempt) / "result.json"
            )
            commit_successful_reproduction_result(
                evidence_root,
                run_key=run_key,
                reproduction_attempt=repro_attempt,
                bindings=bindings,
                attempt=int(prev.get("attempt") or 1),
                envelope=dict(prev.get("envelope") or {}),
                result=dict(repro_result_body.get("result") or {}),
                exit_code=0,
            )
            repro_succeeded += 1
            continue

        # Pre-attempt expiry gate.
        assert_authorization_not_expired_for_next_attempt(
            auth_expiry, now_utc=now_utc_provider()
        )

        planned = _find_planned_run(plan, run_key)
        attempt = 1
        env_path = (
            reproduction_dir(evidence_root, run_key, repro_attempt)
            / "run_envelope.json"
        )
        if env_path.exists() and action == "retry":
            prev = json.loads(env_path.read_text(encoding="utf-8"))
            attempt = int(prev.get("attempt") or 0) + 1

        envelope = RunEnvelope(
            run_key=run_key,
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
            output_dir=str(reproduction_dir(evidence_root, run_key, repro_attempt)),
            run_plan_fingerprint=plan.run_plan_fingerprint,
            authorization_fingerprint=auth_fp,
            attempt=attempt,
            reproduction_attempt=repro_attempt,
            attempt_kind=ATTEMPT_KIND_REPRODUCTION,
        )
        write_reproduction_envelope(
            evidence_root,
            run_key=run_key,
            reproduction_attempt=repro_attempt,
            bindings=bindings,
            status="RUNNING",
            attempt=attempt,
            envelope=envelope.as_dict(),
        )

        result = active_executor.execute(envelope)
        if result.exit_code != 0:
            repro_failed += 1
            write_reproduction_envelope(
                evidence_root,
                run_key=run_key,
                reproduction_attempt=repro_attempt,
                bindings=bindings,
                status="FAILED",
                attempt=attempt,
                envelope=envelope.as_dict(),
                exit_code=result.exit_code,
            )
            if on_mismatch == "block_campaign_completion":
                return {
                    "phase_outcome": "BLOCKED",
                    "reason_code": "REPRODUCTION_EXECUTION_FAILED",
                    "succeeded": repro_succeeded,
                    "failed": repro_failed,
                    "skipped": repro_skipped,
                    "mismatches": mismatches,
                }
            continue

        # Persist result while still RUNNING; SUCCEEDED only after PASS comparison.
        persist_reproduction_result(
            evidence_root,
            run_key=run_key,
            reproduction_attempt=repro_attempt,
            bindings=bindings,
            result=result.metrics,
        )

        # Load primary and compare, with bindings validation.
        primary_result_body = read_json(result_path(evidence_root, run_key))
        primary_result = dict(primary_result_body.get("result") or {})
        # Bindings comparison uses the envelope-level identifiers already
        # written by both primary and reproduction paths.
        primary_bindings = {
            "run_key": run_key,
            "manifest_fingerprint": primary_result_body.get("manifest_fingerprint"),
            "run_plan_fingerprint": primary_result_body.get("run_plan_fingerprint"),
            "authorization_fingerprint": (
                primary_result_body.get("authorization_fingerprint")
            ),
        }
        reproduction_bindings = {
            "run_key": run_key,
            "manifest_fingerprint": bindings.manifest_fingerprint,
            "run_plan_fingerprint": bindings.run_plan_fingerprint,
            "authorization_fingerprint": bindings.authorization_fingerprint,
        }
        try:
            comparison = compare_reproduction_results(
                primary={**primary_result, **primary_bindings},
                reproduction={**dict(result.metrics), **reproduction_bindings},
                compared_fields=compared_fields,
                bindings=True,
            )
        except SensitivityReproductionError as exc:
            raise SensitivityRunnerError(
                "RUNNER_REPRO_STRUCTURAL_FAILURE", str(exc)
            ) from exc
        write_comparison_evidence(
            evidence_root,
            run_key=run_key,
            reproduction_attempt=repro_attempt,
            comparison=comparison,
        )

        if comparison["status"] == "MISMATCH":
            write_reproduction_envelope(
                evidence_root,
                run_key=run_key,
                reproduction_attempt=repro_attempt,
                bindings=bindings,
                status="FAILED",
                attempt=attempt,
                envelope=envelope.as_dict(),
                exit_code=0,
            )
            mismatches.append(
                {
                    "run_key": run_key,
                    "reproduction_attempt": repro_attempt,
                    "reason_code": comparison["reason_code"],
                    "mismatched_fields": comparison["mismatched_fields"],
                }
            )
            if on_mismatch == "block_campaign_completion":
                return {
                    "phase_outcome": "BLOCKED",
                    "reason_code": "REPRODUCTION_RESULT_MISMATCH",
                    "succeeded": repro_succeeded,
                    "failed": repro_failed,
                    "skipped": repro_skipped,
                    "mismatches": mismatches,
                }
            continue

        commit_successful_reproduction_result(
            evidence_root,
            run_key=run_key,
            reproduction_attempt=repro_attempt,
            bindings=bindings,
            attempt=attempt,
            envelope=envelope.as_dict(),
            result=result.metrics,
            exit_code=0,
        )
        repro_succeeded += 1

    return {
        "phase_outcome": "REPRODUCTION_COMPLETE",
        "succeeded": repro_succeeded,
        "failed": repro_failed,
        "skipped": repro_skipped,
        "mismatches": mismatches,
    }


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
    now_utc_provider: Any = None,
    skip_campaign_to_pr_handoff: bool = False,
    campaign_to_pr_issue: int = 4366,
) -> dict[str, Any]:
    """Execute only with valid Owner-GO + budget + surface. Default: real adapter.

    Reproduction is executed as part of this call when the campaign policy
    enables it. Completion is gated on all-primary succeeded plus all
    reproduction attempts PASSing exact-equality comparison against the bound
    primary results.

    After ``COMPLETED``, prepare-delivery handoff runs by default (no ``gh``).
    Opt out with ``skip_campaign_to_pr_handoff=True``.
    """
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    if max_runs_override is not None and max_runs_override != EXPECTED_RUN_COUNT:
        # Tests may pass a subset only via FakeExecutor orchestration helpers —
        # production path forbids altering run count.
        raise SensitivityRunnerError(
            "RUNNER_RUN_COUNT_OVERRIDE_FORBIDDEN", str(max_runs_override)
        )

    from core.utils.clock import utcnow as _cdb_utcnow

    now_provider = now_utc_provider or _cdb_utcnow

    authorizing_github_login = assert_author_in_owner_allowlist(
        authorizing_github_login
    )

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
    # Internal consistency of the plan (not a duplicate of the manifest guard,
    # which is enforced in build_run_plan against EXPECTED_RUN_COUNT).
    if plan.run_count != len(plan.run_keys) or plan.run_count != len(plan.runs):
        raise SensitivityRunnerError(
            "RUNNER_RUN_COUNT_INVALID",
            (
                f"run_count={plan.run_count} run_keys={len(plan.run_keys)} "
                f"runs={len(plan.runs)}"
            ),
        )
    if "CDB-021" in str(manifest.get("strategies")) or (
        (manifest.get("parameter_grid") or {}).get("cdb_021") not in (None, "OUT")
        and (manifest.get("parameter_grid") or {}).get("cdb_021") != "OUT"
    ):
        pg = manifest.get("parameter_grid") or {}
        if pg.get("cdb_021") != "OUT":
            raise SensitivityRunnerError("RUNNER_CDB021_NOT_OUT")

    budget = validate_resource_budget(resource_budget)
    if int(budget["max_parallelism"]) < 1:
        raise SensitivityRunnerError("RUNNER_PARALLELISM_INVALID")

    # Surface probe for Owner-GO binding must match the fingerprint captured at
    # GO issuance (lightweight dataset path identity, not full content binding).
    # Full dataset resolve for the replay adapter is deferred until after
    # adoption/resume gates.
    dataset_identity: DatasetRootIdentity | None = None
    resolved_bank_root: Path | None = None

    probe = probe_execution_surface(
        repo_root=root,
        dataset_root=Path(dataset_root) if dataset_root is not None else None,
        surface_id=surface_id,
        exchange_credentials_present=False,
        window_availability={"expected_windows": 39},
        manifest=None,
        dataset_identity=None,
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
        now_utc=now_provider(),
    )
    auth_fp = str(auth["authorization_fingerprint"])
    auth_id = auth_fp[:16]
    comment_updated_at = str(auth["comment_updated_at"])
    auth_expiry = auth.get("expires_at_utc")

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
    if mode == "resume":
        existing_env = read_json(evidence_root / CAMPAIGN_ENVELOPE_NAME)
        bound_updated = str(existing_env.get("comment_updated_at") or "")
        verify_owner_go_comment(
            comment_id=go_comment_id,
            expected=expected,
            repository=repository,
            issue=ISSUE_NUMBER,
            fetcher=fetcher,
            expected_comment_updated_at=bound_updated or None,
        )
        if bound_updated and bound_updated != comment_updated_at:
            raise SensitivityRunnerError(
                "RUNNER_AUTH_COMMENT_MUTATED",
                f"bound={bound_updated} live={comment_updated_at}",
            )

    # Lifetime vs budget: fresh campaigns require finite expiry. Resume of
    # adopted primary evidence produced under null-expiry Owner-GO may continue
    # when adoption inventory verifies (adoption contract v1).
    if mode == "resume" and auth_expiry is None:
        try:
            assert_adoption_inventory_allows_reproduction(
                evidence_root, bindings=bindings
            )
        except SensitivityAdoptionError:
            assert_authorization_lifetime_covers_budget(
                auth_expiry, budget, now_utc=now_provider()
            )
    else:
        assert_authorization_lifetime_covers_budget(
            auth_expiry, budget, now_utc=now_provider()
        )

    trust_manifest_fps = False
    if mode == "resume":
        try:
            assert_adoption_inventory_allows_reproduction(
                evidence_root, bindings=bindings
            )
            trust_manifest_fps = True
        except SensitivityAdoptionError:
            trust_manifest_fps = False

    if dataset_root is not None:
        try:
            dataset_identity = resolve_and_verify_dataset_root(
                dataset_root=Path(dataset_root),
                manifest=manifest,
                repo_root=root,
                trust_manifest_content_fingerprints=trust_manifest_fps,
            )
        except SensitivityDatasetRootError as exc:
            raise SensitivityRunnerError(
                f"RUNNER_DATASET_{exc.reason_code}", str(exc)
            ) from exc
        resolved_bank_root = Path(dataset_identity.window_bank_root)

    active_executor = _bind_executor_dataset_root(
        executor=executor,
        resolved_bank_root=resolved_bank_root,
    )

    lock_held = False
    acquire_campaign_lock(evidence_root, holder_token=auth_fp)
    lock_held = True
    try:
        envelope_extra: dict[str, Any] = {
            "namespace_mode": mode,
            "github_comment_id": go_comment_id,
            "comment_updated_at": comment_updated_at,
            "authorizing_github_login": authorizing_github_login,
            "expires_at_utc": auth_expiry,
            "dataset_trust_manifest_content_fingerprints": trust_manifest_fps,
        }
        if dataset_identity is not None:
            envelope_extra["dataset_root_identity"] = dataset_identity.as_dict()
        write_campaign_envelope(
            evidence_root,
            bindings=bindings,
            run_count=plan.run_count,
            extra=envelope_extra,
        )

        current_phase = read_campaign_phase(evidence_root)
        if current_phase in {CAMPAIGN_PHASE_COMPLETED, CAMPAIGN_PHASE_BLOCKED}:
            payload = {
                "command": "execute",
                "status": current_phase,
                "campaign_phase": current_phase,
                "reason_code": f"RUNNER_ALREADY_{current_phase}",
                "lr_status": "NO-GO",
            }
            _emit(payload, out)
            return payload

        primary_succeeded = 0
        primary_failed = 0
        primary_skipped = 0
        run_primary = current_phase in {
            CAMPAIGN_PHASE_PLANNED,
            CAMPAIGN_PHASE_PRIMARY_PLANNED,
            CAMPAIGN_PHASE_PRIMARY_RUNNING,
        }

        if run_primary:
            # Fresh start or mid-primary resume — never re-enter from later phases.
            if current_phase != CAMPAIGN_PHASE_PRIMARY_RUNNING:
                update_campaign_phase(
                    evidence_root,
                    bindings=bindings,
                    phase=CAMPAIGN_PHASE_PRIMARY_RUNNING,
                )

            primary_outcome = _run_primary_loop(
                plan=plan,
                evidence_root=evidence_root,
                bindings=bindings,
                budget=budget,
                active_executor=active_executor,
                manifest=manifest,
                auth_fp=auth_fp,
                sha=sha,
                auth_expiry=auth_expiry,
                now_utc_provider=now_provider,
            )
            primary_succeeded = int(primary_outcome.get("succeeded", 0))
            primary_failed = int(primary_outcome.get("failed", 0))
            primary_skipped = int(primary_outcome.get("skipped", 0))

            if primary_outcome["phase_outcome"] == "BLOCKED":
                update_campaign_phase(
                    evidence_root,
                    bindings=bindings,
                    phase=CAMPAIGN_PHASE_BLOCKED,
                    extra={"blocked_reason": primary_outcome.get("reason_code")},
                )
                payload = {
                    "command": "execute",
                    "status": "BLOCKED",
                    "reason_code": str(primary_outcome.get("reason_code")),
                    "campaign_phase": CAMPAIGN_PHASE_BLOCKED,
                    "succeeded": primary_succeeded,
                    "failed": primary_failed,
                    "skipped": primary_skipped,
                    "lr_status": "NO-GO",
                }
                _emit(payload, out)
                return payload

            confirmed_primary = count_primary_succeeded(
                evidence_root,
                bindings=bindings,
                expected_run_keys=list(plan.run_keys),
            )
            if confirmed_primary != plan.run_count:
                update_campaign_phase(
                    evidence_root,
                    bindings=bindings,
                    phase=CAMPAIGN_PHASE_BLOCKED,
                    extra={
                        "blocked_reason": "PRIMARY_SUCCESS_COUNT_MISMATCH",
                        "expected_run_count": plan.run_count,
                        "confirmed_primary": confirmed_primary,
                    },
                )
                payload = {
                    "command": "execute",
                    "status": "BLOCKED",
                    "reason_code": "PRIMARY_SUCCESS_COUNT_MISMATCH",
                    "campaign_phase": CAMPAIGN_PHASE_BLOCKED,
                    "succeeded": primary_succeeded,
                    "failed": primary_failed,
                    "skipped": primary_skipped,
                    "confirmed_primary": confirmed_primary,
                    "lr_status": "NO-GO",
                }
                _emit(payload, out)
                return payload

            update_campaign_phase(
                evidence_root,
                bindings=bindings,
                phase=CAMPAIGN_PHASE_PRIMARY_COMPLETE,
            )
        else:
            # Resume past primary: require a complete primary ledger.
            confirmed_primary = count_primary_succeeded(
                evidence_root,
                bindings=bindings,
                expected_run_keys=list(plan.run_keys),
            )
            if confirmed_primary != plan.run_count:
                update_campaign_phase(
                    evidence_root,
                    bindings=bindings,
                    phase=CAMPAIGN_PHASE_BLOCKED,
                    extra={
                        "blocked_reason": "PRIMARY_SUCCESS_COUNT_MISMATCH",
                        "expected_run_count": plan.run_count,
                        "confirmed_primary": confirmed_primary,
                    },
                )
                payload = {
                    "command": "execute",
                    "status": "BLOCKED",
                    "reason_code": "PRIMARY_SUCCESS_COUNT_MISMATCH",
                    "campaign_phase": CAMPAIGN_PHASE_BLOCKED,
                    "confirmed_primary": confirmed_primary,
                    "lr_status": "NO-GO",
                }
                _emit(payload, out)
                return payload
            primary_succeeded = confirmed_primary
            # Adopted primary evidence lands in PRIMARY_EVIDENCE_COMPLETE;
            # promote to PRIMARY_COMPLETE before reproduction.
            if current_phase == CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE:
                assert_adoption_inventory_allows_reproduction(
                    evidence_root, bindings=bindings
                )
                update_campaign_phase(
                    evidence_root,
                    bindings=bindings,
                    phase=CAMPAIGN_PHASE_PRIMARY_COMPLETE,
                )

        reproduction_enabled = bool(plan.reproduction_policy.get("enabled"))
        reproduction_summary: dict[str, Any] = {"enabled": reproduction_enabled}
        current_phase = read_campaign_phase(evidence_root)

        if reproduction_enabled:
            if current_phase == CAMPAIGN_PHASE_REPRODUCTION_COMPLETE:
                reproduction_summary["phase_outcome"] = "REPRODUCTION_COMPLETE"
                reproduction_summary["resumed_complete"] = True
            else:
                if current_phase == CAMPAIGN_PHASE_PRIMARY_COMPLETE:
                    update_campaign_phase(
                        evidence_root,
                        bindings=bindings,
                        phase=CAMPAIGN_PHASE_REPRODUCTION_PLANNED,
                    )
                    current_phase = CAMPAIGN_PHASE_REPRODUCTION_PLANNED

                reproduction_plan = build_reproduction_plan(
                    run_keys=list(plan.run_keys),
                    policy=plan.reproduction_policy,
                )
                if current_phase == CAMPAIGN_PHASE_REPRODUCTION_PLANNED:
                    update_campaign_phase(
                        evidence_root,
                        bindings=bindings,
                        phase=CAMPAIGN_PHASE_REPRODUCTION_RUNNING,
                        extra={
                            "reproduction_plan_fingerprint": reproduction_plan.get(
                                "reproduction_plan_fingerprint"
                            ),
                            "reproduction_item_count": len(
                                reproduction_plan.get("reproduction_items", [])
                            ),
                        },
                    )
                elif current_phase == CAMPAIGN_PHASE_REPRODUCTION_RUNNING:
                    # Idempotent resume into reproduction.
                    update_campaign_phase(
                        evidence_root,
                        bindings=bindings,
                        phase=CAMPAIGN_PHASE_REPRODUCTION_RUNNING,
                        extra={
                            "reproduction_plan_fingerprint": reproduction_plan.get(
                                "reproduction_plan_fingerprint"
                            ),
                            "reproduction_item_count": len(
                                reproduction_plan.get("reproduction_items", [])
                            ),
                        },
                    )
                else:
                    raise SensitivityRunnerError(
                        "RUNNER_PHASE_UNSUPPORTED_RESUME",
                        current_phase,
                    )

                repro_outcome = _run_reproduction_loop(
                    plan=plan,
                    reproduction_plan=reproduction_plan,
                    evidence_root=evidence_root,
                    bindings=bindings,
                    budget=budget,
                    active_executor=active_executor,
                    manifest=manifest,
                    auth_fp=auth_fp,
                    sha=sha,
                    auth_expiry=auth_expiry,
                    now_utc_provider=now_provider,
                )
                reproduction_summary.update(repro_outcome)

                if repro_outcome["phase_outcome"] == "BLOCKED":
                    update_campaign_phase(
                        evidence_root,
                        bindings=bindings,
                        phase=CAMPAIGN_PHASE_BLOCKED,
                        extra={
                            "blocked_reason": repro_outcome.get("reason_code"),
                            "reproduction_mismatches": repro_outcome.get("mismatches"),
                        },
                    )
                    payload = {
                        "command": "execute",
                        "status": "BLOCKED",
                        "reason_code": str(repro_outcome.get("reason_code")),
                        "campaign_phase": CAMPAIGN_PHASE_BLOCKED,
                        "succeeded": primary_succeeded,
                        "failed": primary_failed,
                        "skipped": primary_skipped,
                        "reproduction": reproduction_summary,
                        "run_count": plan.run_count,
                        "evidence_root": str(evidence_root),
                        "authorization_fingerprint": auth_fp,
                        "run_plan_fingerprint": plan.run_plan_fingerprint,
                        "lr_status": "NO-GO",
                    }
                    _emit(payload, out)
                    return payload

                update_campaign_phase(
                    evidence_root,
                    bindings=bindings,
                    phase=CAMPAIGN_PHASE_REPRODUCTION_COMPLETE,
                )

        update_campaign_phase(
            evidence_root,
            bindings=bindings,
            phase=CAMPAIGN_PHASE_COMPLETED,
        )

        payload = {
            "command": "execute",
            "status": "COMPLETED",
            "campaign_phase": CAMPAIGN_PHASE_COMPLETED,
            "succeeded": primary_succeeded,
            "failed": primary_failed,
            "skipped": primary_skipped,
            "reproduction": reproduction_summary,
            "run_count": plan.run_count,
            "evidence_root": str(evidence_root),
            "authorization_fingerprint": auth_fp,
            "run_plan_fingerprint": plan.run_plan_fingerprint,
            "lr_status": "NO-GO",
        }
        if not skip_campaign_to_pr_handoff:
            handoff_dir = Path(evidence_root) / DEFAULT_HANDOFF_SUBDIR
            try:
                if handoff_dir.exists():
                    # Idempotent re-entry: require empty or reuse only if absent.
                    # Fail closed on non-empty leftover from a partial prior attempt.
                    if any(handoff_dir.iterdir()):
                        raise CampaignToPrError(
                            "HOLD_RAW_RUN_TREE_REJECT",
                            f"handoff output_dir not empty: {handoff_dir}",
                        )
                delivery = prepare_delivery(
                    evidence_root=Path(evidence_root),
                    output_dir=handoff_dir,
                    issue_number=int(campaign_to_pr_issue),
                    batch_key="validation-research",
                    commit_sha=str(bindings.execution_sha),
                    output_rel="docs/evidence/arvp/campaign-to-pr/",
                )
                payload["campaign_to_pr"] = {
                    "verdict": delivery.get("verdict"),
                    "handoff_path": delivery.get("handoff_path"),
                    "handoff_fingerprint": (delivery.get("handoff") or {}).get(
                        "handoff_fingerprint"
                    ),
                    "classification": delivery.get("classification"),
                    "forbidden_actions": delivery.get("forbidden_actions"),
                    "lr_status": "NO-GO",
                }
            except CampaignToPrError as exc:
                # COMPLETED stands; handoff is HOLD for the external agent.
                payload["campaign_to_pr"] = {
                    "verdict": exc.reason_code,
                    "ok": False,
                    "detail": str(exc),
                    "lr_status": "NO-GO",
                }
        else:
            payload["campaign_to_pr"] = {
                "verdict": "SKIPPED",
                "reason_code": "SKIP_CAMPAIGN_TO_PR_HANDOFF",
                "lr_status": "NO-GO",
            }
        _emit(payload, out)
        return payload
    finally:
        if lock_held:
            release_campaign_lock(evidence_root, holder_token=auth_fp)


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


def adopt_primary_evidence_command(
    *,
    evidence_root: Path,
    manifest_path: Path | str = MANIFEST_PATH,
    main_sha: str | None = None,
    authorization_fingerprint: str,
    reproduction_code_sha: str | None = None,
    promote_to_primary_complete: bool = True,
    power_off_recovery_json: str | None = None,
    repo_root: Path | None = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """Adopt audited primary evidence into the phase machine (no primary rewrite)."""
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    sha = main_sha or _git_head_sha(root)
    code_sha = reproduction_code_sha or _git_head_sha(root)
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    plan = build_run_plan(manifest, main_sha=sha)
    env = read_json(Path(evidence_root) / CAMPAIGN_ENVELOPE_NAME)
    bindings = CampaignBindings(
        campaign_id=str(env.get("campaign_id") or plan.campaign_id),
        manifest_fingerprint=str(env.get("manifest_fingerprint") or ""),
        run_plan_fingerprint=str(env.get("run_plan_fingerprint") or ""),
        authorization_fingerprint=str(
            env.get("authorization_fingerprint") or authorization_fingerprint
        ),
        execution_sha=str(env.get("execution_sha") or sha),
        main_sha=str(env.get("main_sha") or sha),
    )
    if bindings.authorization_fingerprint != authorization_fingerprint:
        raise SensitivityAdoptionError(
            "ADOPT_AUTH_FP_CLI_MISMATCH",
            "CLI --authorization-fingerprint must match campaign envelope",
        )
    if bindings.manifest_fingerprint != plan.manifest_fingerprint:
        raise SensitivityAdoptionError(
            "ADOPT_MANIFEST_FP_MISMATCH",
            "recomputed manifest fingerprint != envelope",
        )
    if bindings.run_plan_fingerprint != plan.run_plan_fingerprint:
        raise SensitivityAdoptionError(
            "ADOPT_RUN_PLAN_FP_MISMATCH",
            "recomputed run-plan fingerprint != envelope "
            "(pass the frozen --main-sha used for primary)",
        )
    recovery = {}
    if power_off_recovery_json:
        recovery = json.loads(power_off_recovery_json)
    payload = adopt_primary_evidence(
        evidence_root=Path(evidence_root),
        expected_run_keys=list(plan.run_keys),
        bindings=bindings,
        reproduction_code_sha=code_sha,
        promote_to_primary_complete=promote_to_primary_complete,
        power_off_recovery=recovery,
    )
    _emit(payload, out)
    return payload


def analyze_campaign_command(
    *,
    evidence_root: Path,
    manifest_path: Path | str = MANIFEST_PATH,
    main_sha: str | None = None,
    repo_root: Path | None = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """Run deterministic analyzer against an adopted+reproduced evidence namespace."""
    root = repo_root or PROJECT_ROOT
    out = stream or sys.stdout
    sha = main_sha or _git_head_sha(root)
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest)
    plan = build_run_plan(manifest, main_sha=sha)
    env = read_json(Path(evidence_root) / CAMPAIGN_ENVELOPE_NAME)
    payload = analyze_campaign(
        evidence_root=Path(evidence_root),
        expected_run_keys=list(plan.run_keys),
        manifest_fingerprint=str(env.get("manifest_fingerprint") or ""),
        run_plan_fingerprint=str(env.get("run_plan_fingerprint") or ""),
        authorization_fingerprint=str(env.get("authorization_fingerprint") or ""),
    )
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
    p_exec.add_argument(
        "--skip-campaign-to-pr-handoff",
        action="store_true",
        help="Do not auto-run prepare-delivery after COMPLETED (default: wire-on)",
    )
    p_exec.add_argument(
        "--campaign-to-pr-issue",
        type=int,
        default=4366,
        help="Issue number recorded in delivery handoff",
    )
    # Intentionally NO --force / --yes / --admin / --resume-anyway flags.

    p_probe = sub.add_parser("probe-surface", help="Read-only surface capability probe")
    p_probe.add_argument("--surface-id", required=True)
    p_probe.add_argument("--dataset-root", type=Path, default=None)

    p_adopt = sub.add_parser(
        "adopt-primary-evidence",
        help=(
            "Write primary evidence inventory and transition PLANNED → "
            "PRIMARY_EVIDENCE_COMPLETE → PRIMARY_COMPLETE (no primary rewrite)"
        ),
    )
    p_adopt.add_argument("--evidence-root", type=Path, required=True)
    p_adopt.add_argument("--manifest", type=Path, default=Path(MANIFEST_PATH))
    p_adopt.add_argument(
        "--main-sha",
        required=True,
        help="Frozen primary bound_main_sha / execution SHA",
    )
    p_adopt.add_argument("--authorization-fingerprint", required=True)
    p_adopt.add_argument(
        "--reproduction-code-sha",
        default=None,
        help="Git SHA of reproduction tooling (defaults to HEAD)",
    )
    p_adopt.add_argument(
        "--no-promote-primary-complete",
        action="store_true",
        help="Stop at PRIMARY_EVIDENCE_COMPLETE without promoting",
    )
    p_adopt.add_argument(
        "--power-off-recovery-json",
        default=None,
        help="Optional JSON operator note for interrupt recovery history",
    )

    p_analyze = sub.add_parser(
        "analyze",
        help="Deterministic campaign analyzer (requires COMPLETED + reproduction)",
    )
    p_analyze.add_argument("--evidence-root", type=Path, required=True)
    p_analyze.add_argument("--manifest", type=Path, default=Path(MANIFEST_PATH))
    p_analyze.add_argument(
        "--main-sha",
        required=True,
        help="Frozen primary bound_main_sha used for run-plan expansion",
    )

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
        if args.command == "adopt-primary-evidence":
            adopt_primary_evidence_command(
                evidence_root=args.evidence_root,
                manifest_path=args.manifest,
                main_sha=args.main_sha,
                authorization_fingerprint=args.authorization_fingerprint,
                reproduction_code_sha=args.reproduction_code_sha,
                promote_to_primary_complete=not args.no_promote_primary_complete,
                power_off_recovery_json=args.power_off_recovery_json,
            )
            return 0
        if args.command == "analyze":
            analyze_campaign_command(
                evidence_root=args.evidence_root,
                manifest_path=args.manifest,
                main_sha=args.main_sha,
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
            # Production CLI uses the real strategy-replay adapter; Owner-GO still
            # blocks execution when missing/invalid.
            execute_campaign(
                manifest_path=args.manifest,
                go_comment_id=args.go_comment_id,
                executor=None,
                repository=args.repository,
                authorizing_github_login=args.authorizing_github_login,
                surface_id=args.surface_id,
                surface_capability_fingerprint=args.surface_capability_fingerprint,
                resource_budget=budget,
                dataset_root=args.dataset_root,
                artifacts_base=args.artifacts_base,
                main_sha=args.main_sha,
                skip_campaign_to_pr_handoff=bool(args.skip_campaign_to_pr_handoff),
                campaign_to_pr_issue=int(args.campaign_to_pr_issue),
            )
            return 0
        parser.error(f"unknown command {args.command}")
        return 2
    except (
        SensitivityRunnerError,
        SensitivityAuthorizationError,
        SensitivityAdoptionError,
        SensitivityAnalyzerError,
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
