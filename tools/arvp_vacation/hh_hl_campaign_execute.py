"""hh_hl campaign execute entry-point (#4374).

Supervised offline-replay orchestration:

* ``preflight`` — verify Owner-GO + wiring + plan/state; 0 replays
* ``execute``   — re-verify GO, then run at most 39 bound baseline replays
* ``status``    — read-only progress; 0 replays

Never posts or edits an Owner-GO. Never bypasses AuthorizationContext.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
    frozen_hh_hl_parameters,
)
from tools.arvp_vacation.campaign_executor_providers import (
    HhHlSingleRunReplayProvider,
    resolve_campaign_executor,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_REPLAY_PROFILE_ID,
    CampaignProfileError,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import (
    HhHlDatasetBindingError,
    load_pass_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    HhHlDesignAuthorizationError,
    build_reference_design_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_execution_authorization import (
    CAMPAIGN_ID,
    DEFAULT_REPO,
    ISSUE_NUMBER,
    AuthorizationContext,
    HhHlExecutionAuthorizationError,
    OwnerGoFetcher,
    authorization_context_from_verified_go,
    default_gh_comment_fetcher,
    verify_owner_execution_go_comment,
)
from tools.arvp_vacation.hh_hl_campaign_final_manifest import PROJECT_ROOT
from tools.arvp_vacation.hh_hl_campaign_lifecycle import (
    HH_HL_EXPECTED_RUN_COUNT,
    HhHlLifecycleError,
    assert_startable,
    bindings_from_authorization,
    hh_hl_evidence_root_for,
    plan_resume_actions,
    reverify_owner_go_for_resume_or_start,
    validate_primary_run_keys,
)
from tools.arvp_vacation.hh_hl_campaign_run_plan import (
    build_hh_hl_final_run_plan,
    build_hh_hl_run_plan,
)
from tools.arvp_vacation.hh_hl_campaign_sha_gate import (
    GitShaResolver,
    HhHlShaGateError,
    assert_checked_out_matches_execution_sha,
    assert_execution_sha_exists,
    resolve_live_git_sha_resolver,
)
from tools.arvp_vacation.hh_hl_campaign_surface import measure_free_disk_bytes
from tools.arvp_vacation.sensitivity_campaign_budget import (
    SensitivityBudgetError,
    assert_failure_thresholds,
    validate_resource_budget,
)
from tools.arvp_vacation.sensitivity_campaign_executor import (
    ATTEMPT_KIND_PRIMARY,
    RunEnvelope,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    SensitivityStateError,
    commit_successful_result,
    write_campaign_envelope,
    write_run_envelope,
)

DEFAULT_MANIFEST_REL = "config/arvp/hh_hl_campaign_4374_v1.json"
DEFAULT_DATASET_RECEIPT_REL = (
    "docs/evidence/arvp_hh_hl_dataset_local_proof_receipt_4374.json"
)
DEFAULT_DESIGN_GO_COMMENT_ID = 5206657394

# Injectable test surfaces (never argparse / never env). Production leaves these
# None. Private Python test seams only — not a production CLI surface.
_TEST_OWNER_GO_FETCHER: OwnerGoFetcher | None = None
_TEST_GIT_SHA_RESOLVER: GitShaResolver | None = None
_TEST_NOW_UTC: datetime | None = None
_TEST_WINDOW_BANK_ROOT: Path | None = None
_TEST_SINGLE_RUN_CALLABLE = None
_TEST_FREE_DISK_BYTES: int | None = None

HOLD_FREE_DISK_BELOW_MINIMUM = "HOLD_EXECUTION_FREE_DISK_BELOW_MINIMUM"


class HhHlCampaignExecuteError(ValueError):
    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


def _test_set_owner_go_fetcher(fetcher: OwnerGoFetcher | None) -> None:
    global _TEST_OWNER_GO_FETCHER
    _TEST_OWNER_GO_FETCHER = fetcher


def _test_set_git_sha_resolver(resolver: GitShaResolver | None) -> None:
    global _TEST_GIT_SHA_RESOLVER
    _TEST_GIT_SHA_RESOLVER = resolver


def _test_set_now_utc(now_utc: datetime | None) -> None:
    global _TEST_NOW_UTC
    _TEST_NOW_UTC = now_utc


def _test_set_window_bank_root(root: Path | None) -> None:
    global _TEST_WINDOW_BANK_ROOT
    _TEST_WINDOW_BANK_ROOT = root


def _test_set_single_run_callable(callable_) -> None:
    global _TEST_SINGLE_RUN_CALLABLE
    _TEST_SINGLE_RUN_CALLABLE = callable_


def _test_set_free_disk_bytes(free_disk_bytes: int | None) -> None:
    global _TEST_FREE_DISK_BYTES
    _TEST_FREE_DISK_BYTES = free_disk_bytes


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n")
    sys.stdout.flush()


def _repo_root(args: argparse.Namespace) -> Path:
    root = getattr(args, "repo_root", None)
    return Path(root) if root else PROJECT_ROOT


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HhHlCampaignExecuteError("HOLD_JSON_ROOT_INVALID", str(path))
    return payload


def _now_utc() -> datetime:
    if _TEST_NOW_UTC is not None:
        return _TEST_NOW_UTC
    return datetime.now(timezone.utc)


def _owner_go_fetcher(_args: argparse.Namespace | None = None) -> OwnerGoFetcher:
    """Resolve the Owner-GO fetcher.

    Production always uses ``default_gh_comment_fetcher``. The only non-live
    substitution is the private ``_test_set_owner_go_fetcher`` seam used by unit
    tests — never argparse, never environment variables.
    """
    if _TEST_OWNER_GO_FETCHER is not None:
        return _TEST_OWNER_GO_FETCHER
    return default_gh_comment_fetcher


def _git_resolver(repo_root: Path) -> GitShaResolver:
    if _TEST_GIT_SHA_RESOLVER is not None:
        return _TEST_GIT_SHA_RESOLVER
    return resolve_live_git_sha_resolver(repo_root)


def _load_design_receipt(
    repo_root: Path, args: argparse.Namespace
) -> Mapping[str, Any]:
    """Resolve the frozen Design-GO ratification receipt (no CLI fixture path)."""
    comment_id = int(
        getattr(args, "design_go_comment_id", None) or DEFAULT_DESIGN_GO_COMMENT_ID
    )
    receipt = build_reference_design_receipt(comment_id=comment_id, repo_root=repo_root)
    return receipt.as_dict()


def _current_free_disk_bytes(repo_root: Path) -> int:
    if _TEST_FREE_DISK_BYTES is not None:
        return int(_TEST_FREE_DISK_BYTES)
    return int(measure_free_disk_bytes(repo_root))


def assert_free_disk_meets_budget(
    *,
    budget: Mapping[str, Any],
    free_disk_bytes: int,
) -> int:
    """Fresh runtime free-disk gate (threshold check, not receipt byte-equality)."""
    minimum = int(budget.get("minimum_free_disk_bytes") or 0)
    free = int(free_disk_bytes)
    if free < minimum:
        raise HhHlCampaignExecuteError(
            HOLD_FREE_DISK_BELOW_MINIMUM,
            f"free_disk_bytes={free} < minimum_free_disk_bytes={minimum}",
        )
    return free


def _verify_execution_go(
    args: argparse.Namespace,
) -> tuple[AuthorizationContext, dict[str, Any]]:
    comment_id = int(getattr(args, "execution_go_comment_id") or 0)
    if comment_id <= 0:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_OWNER_GO_REQUIRED", "missing --execution-go-comment-id"
        )
    expected_path = getattr(args, "expected_bindings_json", None)
    expected: Mapping[str, Any] | None = None
    if expected_path:
        expected = _load_json(Path(expected_path))
    verified = verify_owner_execution_go_comment(
        comment_id=comment_id,
        expected=expected or {},
        repository=DEFAULT_REPO,
        issue=ISSUE_NUMBER,
        fetcher=_owner_go_fetcher(args),
        now_utc=_now_utc(),
    )
    ctx = authorization_context_from_verified_go(verified)
    ctx.assert_not_expired(now_utc=_now_utc())
    return ctx, dict(verified)


def _assert_production_provider_wired(profile_id: str = HH_HL_REPLAY_PROFILE_ID) -> str:
    provider = resolve_campaign_executor(load_profile(profile_id))
    if not isinstance(provider, HhHlSingleRunReplayProvider):
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_SURFACE_NOT_WIRED_AT_AUTHORIZED_SHA",
            f"got {type(provider).__name__}",
        )
    # Resolve without invoking — unset still raises.
    provider._resolve_single_run_callable()
    return provider.SURFACE_ID


def _rebuild_bound_plans(
    *,
    repo_root: Path,
    args: argparse.Namespace,
    ctx: AuthorizationContext,
) -> tuple[Any, Any, Mapping[str, str]]:
    manifest = _load_json(
        repo_root / (getattr(args, "manifest", None) or DEFAULT_MANIFEST_REL)
    )
    dataset_receipt = load_pass_receipt(
        repo_root
        / (getattr(args, "dataset_receipt", None) or DEFAULT_DATASET_RECEIPT_REL)
    )
    design_receipt = _load_design_receipt(repo_root, args)
    resolver = _git_resolver(repo_root)
    assert_execution_sha_exists(ctx.execution_sha, resolver=resolver)
    assert_checked_out_matches_execution_sha(ctx.execution_sha, resolver=resolver)

    final_plan = build_hh_hl_final_run_plan(
        final_manifest=manifest,
        design_receipt=design_receipt,
        dataset_receipt=dataset_receipt,
        planning_sha=ctx.bound_main_sha,
        pre_final=False,
        live_main_resolver=None,  # already checked out + existence gated above
        profile=load_profile(HH_HL_REPLAY_PROFILE_ID),
    )
    if final_plan.run_plan_fingerprint != ctx.run_plan_fingerprint:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_RUN_PLAN_MISMATCH",
            f"plan={final_plan.run_plan_fingerprint} go={ctx.run_plan_fingerprint}",
        )
    if final_plan.manifest_fingerprint != ctx.manifest_fingerprint:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_MANIFEST_MISMATCH",
            f"plan={final_plan.manifest_fingerprint} go={ctx.manifest_fingerprint}",
        )
    if str(dataset_receipt.selection_sha256) != str(
        ctx.payload.get("dataset_selection_sha256") or ""
    ):
        raise HhHlCampaignExecuteError("HOLD_EXECUTION_DATASET_DRIFT", "selection")
    if str(dataset_receipt.content_fingerprint_digest) != str(
        ctx.payload.get("dataset_content_fingerprint_digest") or ""
    ):
        raise HhHlCampaignExecuteError("HOLD_EXECUTION_DATASET_DRIFT", "content_digest")
    # Live surface identity: authorized execution_surface_id must match the
    # production provider surface. surface_capability_fingerprint on the
    # AuthorizationContext remains the Owner-authorized *historical*
    # post-merge surface-receipt binding — it is retained on ctx and must not
    # be treated as proof of the current physical execution surface (a
    # payload↔ctx self-compare would be tautological).
    if (
        str(ctx.payload.get("execution_surface_id") or "")
        != HhHlSingleRunReplayProvider.SURFACE_ID
    ):
        raise HhHlCampaignExecuteError("HOLD_EXECUTION_SURFACE_BINDING_MISMATCH")

    budget = validate_resource_budget(ctx.resource_budget)
    # Fresh free-disk threshold check (not byte-equality to a past receipt).
    assert_free_disk_meets_budget(
        budget=budget,
        free_disk_bytes=_current_free_disk_bytes(repo_root),
    )
    if int(budget["max_parallelism"]) != 1 or int(budget["max_in_flight_runs"]) != 1:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_RESOURCE_BUDGET_INVALID", "parallelism"
        )
    if int(budget["max_attempts_per_run"]) != 1:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_RESOURCE_BUDGET_INVALID", "attempts"
        )
    if int(ctx.expected_run_count) != HH_HL_EXPECTED_RUN_COUNT:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_RUN_COUNT_MISMATCH", str(ctx.expected_run_count)
        )
    if int(ctx.payload.get("max_run_count") or 0) != HH_HL_EXPECTED_RUN_COUNT:
        raise HhHlCampaignExecuteError("HOLD_EXECUTION_MAX_RUN_COUNT_MISMATCH")

    run_plan = build_hh_hl_run_plan(
        profile=load_profile(HH_HL_REPLAY_PROFILE_ID),
        manifest=manifest,
        planning_sha=ctx.bound_main_sha,
        dataset_receipt=dataset_receipt,
    )
    keys = validate_primary_run_keys(final_plan.run_keys)
    if tuple(run_plan.run_keys) != keys:
        raise HhHlCampaignExecuteError(
            "HOLD_EXECUTION_RUN_KEYS_MISMATCH", "final vs operational plan"
        )
    per_window = dict(dataset_receipt.per_window_content_fingerprints or {})
    return final_plan, run_plan, per_window


def _evidence_root_for(ctx: AuthorizationContext, repo_root: Path) -> Path:
    return hh_hl_evidence_root_for(
        base=repo_root,
        campaign_id=ctx.campaign_id,
        manifest_fingerprint=ctx.manifest_fingerprint,
        authorization_id=ctx.authorization_fingerprint,
    )


def _seed_for(campaign_id: str, window_id: str, slot_id: str) -> str:
    return canonical_hash(
        {
            "campaign_id": campaign_id,
            "window_id": window_id,
            "slot_id": slot_id,
            "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
        }
    )


def cmd_preflight(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args)
    try:
        surface_id = _assert_production_provider_wired()
        ctx, verified = _verify_execution_go(args)
        final_plan, run_plan, _per_window = _rebuild_bound_plans(
            repo_root=repo_root, args=args, ctx=ctx
        )
        bindings = bindings_from_authorization(ctx)
        evidence_root = _evidence_root_for(ctx, repo_root)
        startable = assert_startable(
            evidence_root,
            bindings=bindings,
            allow_resume=bool(ctx.resume_policy.get("allow_resume", True)),
        )
        actions = plan_resume_actions(
            evidence_root,
            bindings=bindings,
            run_keys=final_plan.run_keys,
            max_attempts=1,
            retry_failed=bool(ctx.resume_policy.get("retry_failed", True)),
        )
    except (
        HhHlCampaignExecuteError,
        HhHlExecutionAuthorizationError,
        HhHlLifecycleError,
        HhHlDatasetBindingError,
        HhHlDesignAuthorizationError,
        HhHlShaGateError,
        CampaignProfileError,
        SensitivityBudgetError,
        SensitivityStateError,
        ValueError,
    ) as exc:
        reason = getattr(exc, "reason_code", None) or str(exc)
        _emit(
            {
                "ok": False,
                "command": "preflight",
                "reason_code": reason,
                "replays": False,
            }
        )
        return 1

    _emit(
        {
            "ok": True,
            "command": "preflight",
            "replays": False,
            "surface_id": surface_id,
            "authorization_fingerprint": ctx.authorization_fingerprint,
            "github_comment_id": ctx.github_comment_id,
            "comment_updated_at": ctx.comment_updated_at,
            "expires_at_utc": ctx.expires_at_utc,
            "execution_sha": ctx.execution_sha,
            "run_plan_fingerprint": final_plan.run_plan_fingerprint,
            "expected_run_count": HH_HL_EXPECTED_RUN_COUNT,
            "run_key_count": len(run_plan.run_keys),
            "evidence_root": evidence_root.as_posix(),
            "startable": startable,
            "resume_actions": actions,
            "verified_reason_code": verified.get("reason_code"),
        }
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args)
    try:
        ctx, _verified = _verify_execution_go(args)
        final_plan, _run_plan, _per_window = _rebuild_bound_plans(
            repo_root=repo_root, args=args, ctx=ctx
        )
        bindings = bindings_from_authorization(ctx)
        evidence_root = _evidence_root_for(ctx, repo_root)
        startable = assert_startable(
            evidence_root,
            bindings=bindings,
            allow_resume=bool(ctx.resume_policy.get("allow_resume", True)),
        )
        actions = plan_resume_actions(
            evidence_root,
            bindings=bindings,
            run_keys=final_plan.run_keys,
            max_attempts=1,
            retry_failed=bool(ctx.resume_policy.get("retry_failed", True)),
        )
    except (
        HhHlCampaignExecuteError,
        HhHlExecutionAuthorizationError,
        HhHlLifecycleError,
        HhHlDatasetBindingError,
        HhHlDesignAuthorizationError,
        HhHlShaGateError,
        CampaignProfileError,
        SensitivityBudgetError,
        SensitivityStateError,
        ValueError,
    ) as exc:
        reason = getattr(exc, "reason_code", None) or str(exc)
        _emit(
            {"ok": False, "command": "status", "reason_code": reason, "replays": False}
        )
        return 1

    counts = {"start": 0, "skip": 0, "retry": 0}
    for action in actions.values():
        counts[action] = counts.get(action, 0) + 1
    _emit(
        {
            "ok": True,
            "command": "status",
            "replays": False,
            "authorization_fingerprint": ctx.authorization_fingerprint,
            "evidence_root": evidence_root.as_posix(),
            "startable": startable,
            "action_counts": counts,
            "resume_actions": actions,
        }
    )
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args)
    try:
        _assert_production_provider_wired()
        # Fresh verify first to capture bound updated_at, then resume-safe reverify.
        ctx, verified = _verify_execution_go(args)
        ctx = reverify_owner_go_for_resume_or_start(
            comment_id=int(args.execution_go_comment_id),
            expected=(
                _load_json(Path(args.expected_bindings_json))
                if getattr(args, "expected_bindings_json", None)
                else dict(verified.get("payload") or {})
            ),
            fetcher=_owner_go_fetcher(args),
            bound_comment_updated_at=str(verified.get("comment_updated_at") or ""),
            now_utc=_now_utc(),
            repository=DEFAULT_REPO,
            issue=ISSUE_NUMBER,
        )
        final_plan, run_plan, per_window = _rebuild_bound_plans(
            repo_root=repo_root, args=args, ctx=ctx
        )
        bindings = bindings_from_authorization(ctx)
        evidence_root = _evidence_root_for(ctx, repo_root)
        startable = assert_startable(
            evidence_root,
            bindings=bindings,
            allow_resume=bool(ctx.resume_policy.get("allow_resume", True)),
        )
        actions = plan_resume_actions(
            evidence_root,
            bindings=bindings,
            run_keys=final_plan.run_keys,
            max_attempts=1,
            retry_failed=bool(ctx.resume_policy.get("retry_failed", True)),
        )
        budget = validate_resource_budget(ctx.resource_budget)

        profile = load_profile(HH_HL_REPLAY_PROFILE_ID)
        if _TEST_SINGLE_RUN_CALLABLE is not None:
            provider = HhHlSingleRunReplayProvider(
                profile, single_run_callable=_TEST_SINGLE_RUN_CALLABLE
            )
        else:
            from tools.arvp_vacation.hh_hl_single_run_callable import (
                build_production_single_run_callable,
            )

            provider = HhHlSingleRunReplayProvider(
                profile,
                single_run_callable=build_production_single_run_callable(
                    window_bank_root=_TEST_WINDOW_BANK_ROOT
                ),
            )

        write_campaign_envelope(
            evidence_root,
            bindings=bindings,
            run_count=HH_HL_EXPECTED_RUN_COUNT,
            extra={
                "campaign_id": CAMPAIGN_ID,
                "startable": startable,
                "phase": "PRIMARY",
            },
        )

        planned_by_key = {r.run_key: r for r in run_plan.runs}
        succeeded = 0
        skipped = 0
        failed = 0
        consecutive_failures = 0
        total_failures = 0
        dispatched = 0

        for run_key in final_plan.run_keys:
            if dispatched >= HH_HL_EXPECTED_RUN_COUNT:
                raise HhHlCampaignExecuteError("HOLD_SCOPE_GROWTH", "run_40_forbidden")
            action = actions[run_key]
            if action == "skip":
                skipped += 1
                continue

            ctx.assert_not_expired(now_utc=_now_utc())
            planned = planned_by_key[run_key]
            window_fp = str(per_window.get(planned.window_id) or "")
            if not window_fp:
                raise HhHlCampaignExecuteError(
                    "HOLD_EXECUTION_DATASET_DRIFT",
                    f"missing window fp:{planned.window_id}",
                )

            attempt = 1
            envelope = RunEnvelope(
                run_key=planned.run_key,
                campaign_id=ctx.campaign_id,
                manifest_fingerprint=ctx.manifest_fingerprint,
                execution_sha=ctx.execution_sha,
                window_id=planned.window_id,
                strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
                parameters=dict(frozen_hh_hl_parameters()),
                slot_id=planned.slot_id,
                phase=planned.phase,
                label=planned.label,
                physical_parameter_set_fingerprint=(
                    planned.physical_parameter_set_fingerprint
                ),
                effective_config_fingerprint=ctx.manifest_fingerprint,
                dataset_content_fingerprint=window_fp,
                seed=_seed_for(ctx.campaign_id, planned.window_id, planned.slot_id),
                output_dir=str(evidence_root / "runs" / planned.run_key),
                run_plan_fingerprint=ctx.run_plan_fingerprint,
                authorization_fingerprint=ctx.authorization_fingerprint,
                attempt=attempt,
                reproduction_attempt=0,
                attempt_kind=ATTEMPT_KIND_PRIMARY,
            )
            # Persist bound envelope beside the run for audit.
            out_dir = Path(envelope.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "bound_run_envelope.json").write_text(
                json.dumps(envelope.as_dict(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            write_run_envelope(
                evidence_root,
                run_key=run_key,
                bindings=bindings,
                status="RUNNING",
                attempt=attempt,
                envelope=envelope.as_dict(),
            )
            dispatched += 1
            result = provider.execute(
                envelope, authorization_context=ctx, now_utc=_now_utc()
            )
            if result.exit_code != 0:
                failed += 1
                consecutive_failures += 1
                total_failures += 1
                write_run_envelope(
                    evidence_root,
                    run_key=run_key,
                    bindings=bindings,
                    status="FAILED",
                    attempt=attempt,
                    envelope=envelope.as_dict(),
                    exit_code=result.exit_code,
                )
                assert_failure_thresholds(
                    budget=budget,
                    consecutive_failures=consecutive_failures,
                    total_failures=total_failures,
                )
                continue

            consecutive_failures = 0
            commit_successful_result(
                evidence_root,
                run_key=run_key,
                bindings=bindings,
                attempt=attempt,
                envelope=envelope.as_dict(),
                result=result.metrics,
                exit_code=0,
            )
            succeeded += 1

        if succeeded + skipped + failed > HH_HL_EXPECTED_RUN_COUNT:
            raise HhHlCampaignExecuteError("HOLD_SCOPE_GROWTH", "extra_runs")

        complete = succeeded + skipped == HH_HL_EXPECTED_RUN_COUNT and failed == 0
        _emit(
            {
                "ok": complete,
                "command": "execute",
                "phase_outcome": (
                    "PRIMARY_COMPLETE" if complete else "PRIMARY_INCOMPLETE"
                ),
                "authorization_fingerprint": ctx.authorization_fingerprint,
                "evidence_root": evidence_root.as_posix(),
                "succeeded": succeeded,
                "skipped": skipped,
                "failed": failed,
                "dispatched": dispatched,
                "expected_run_count": HH_HL_EXPECTED_RUN_COUNT,
                "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
                "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
            }
        )
        return 0 if complete else 1
    except (
        HhHlCampaignExecuteError,
        HhHlExecutionAuthorizationError,
        HhHlLifecycleError,
        HhHlDatasetBindingError,
        HhHlDesignAuthorizationError,
        HhHlShaGateError,
        CampaignProfileError,
        SensitivityBudgetError,
        SensitivityStateError,
        ValueError,
    ) as exc:
        reason = getattr(exc, "reason_code", None) or str(exc)
        _emit({"ok": False, "command": "execute", "reason_code": reason})
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hh_hl_campaign_execute",
        description="hh_hl authorized offline-replay campaign entry-point",
    )
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST_REL)
    parser.add_argument("--dataset-receipt", default=DEFAULT_DATASET_RECEIPT_REL)
    parser.add_argument(
        "--execution-go-comment-id",
        type=int,
        required=False,
        default=None,
        help="Required for preflight/execute/status (Owner Execution-GO comment id).",
    )
    parser.add_argument("--expected-bindings-json", default=None)
    parser.add_argument(
        "--design-go-comment-id", type=int, default=DEFAULT_DESIGN_GO_COMMENT_ID
    )
    # Intentionally absent from the public production CLI:
    # --fixture-json, --design-go-fixture-json, --skip-*, --offline, --fake-*,
    # and any env-based Owner-GO bypass. Unit tests inject via
    # _test_set_owner_go_fetcher / _test_set_free_disk_bytes only.
    sub = parser.add_subparsers(dest="command", required=True)

    p_pre = sub.add_parser("preflight", help="Verify GO/wiring/plan/state; 0 replays")
    p_pre.set_defaults(func=cmd_preflight)

    p_ex = sub.add_parser("execute", help="Start/resume bound 39-run offline campaign")
    p_ex.set_defaults(func=cmd_execute)

    p_st = sub.add_parser("status", help="Read-only campaign status; 0 replays")
    p_st.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "execution_go_comment_id", None):
        _emit(
            {
                "ok": False,
                "reason_code": "HOLD_EXECUTION_OWNER_GO_REQUIRED",
                "detail": "missing --execution-go-comment-id",
            }
        )
        return 1
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
