"""hh_hl campaign run-plan builder — planning-only (#4374).

expected_run_count = window_count × variant_count. No fixed 819 assumption.
Write-free; never starts replays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import HH_HL_CONTINUATION_STRATEGY_ID
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    HH_HL_PROFILE_IDS,
    HH_HL_REPLAY_PROFILE_ID,
    CampaignProfile,
    CampaignProfileError,
    assert_profile_manifest_bind,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_sha_gate import (
    GitShaResolver,
    HhHlShaGateError,
    assert_planning_sha_format_and_distinct,
    assert_planning_sha_is_live_main,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import (
    DatasetBindingReceipt,
    build_dataset_binding_receipt,
    validate_pass_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    DesignRatificationReceipt,
)
from tools.arvp_vacation.hh_hl_campaign_grid import (
    GRID_PROVIDER_ID,
    HhHlVariantSpec,
    expand_hh_hl_variants,
)

RUN_PLAN_PROVIDER_ID = "hh_hl_run_plan_v1"
RUNNER_CONTRACT_VERSION = "cdb.hh_hl_campaign_runner.v1.prep"
ANALYZER_PROFILE_ID = "hh_hl_analyzer_prep_v1"

FINAL_RUN_PLAN_STATUS = "FINAL"
PRE_FINAL_RUN_PLAN_STATUS = "PRE_FINALIZATION"


@dataclass(frozen=True, slots=True)
class HhHlPlannedRun:
    run_key: str
    window_id: str
    strategy_id: str
    slot_id: str
    phase: str
    label: str
    scenario_id: str
    param_set: Mapping[str, Any]
    physical_parameter_set_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_key": self.run_key,
            "window_id": self.window_id,
            "strategy_id": self.strategy_id,
            "slot_id": self.slot_id,
            "phase": self.phase,
            "label": self.label,
            "scenario_id": self.scenario_id,
            "param_set": dict(self.param_set),
            "physical_parameter_set_fingerprint": (
                self.physical_parameter_set_fingerprint
            ),
        }


def make_run_key(
    *,
    campaign_id: str,
    window_id: str,
    slot_id: str,
    strategy_id: str,
    physical_parameter_set_fingerprint: str,
) -> str:
    body = {
        "campaign_id": campaign_id,
        "window_id": window_id,
        "slot_id": slot_id,
        "strategy_id": strategy_id,
        "physical_parameter_set_fingerprint": physical_parameter_set_fingerprint,
    }
    digest = canonical_hash(body)[:16]
    return f"{campaign_id}|{window_id}|{slot_id}|{strategy_id}|{digest}"


def _expand_runs(
    *,
    campaign_id: str,
    window_ids: Sequence[str],
    variants: Sequence[HhHlVariantSpec],
) -> tuple[HhHlPlannedRun, ...]:
    planned: list[HhHlPlannedRun] = []
    for window_id in window_ids:
        for variant in variants:
            run_key = make_run_key(
                campaign_id=campaign_id,
                window_id=window_id,
                slot_id=variant.slot_id,
                strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
                physical_parameter_set_fingerprint=(
                    variant.physical_parameter_set_fingerprint
                ),
            )
            planned.append(
                HhHlPlannedRun(
                    run_key=run_key,
                    window_id=window_id,
                    strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
                    slot_id=variant.slot_id,
                    phase=variant.phase,
                    label=variant.label,
                    scenario_id=variant.scenario_id,
                    param_set=variant.param_set,
                    physical_parameter_set_fingerprint=(
                        variant.physical_parameter_set_fingerprint
                    ),
                )
            )
    planned.sort(key=lambda r: r.run_key)
    keys = [r.run_key for r in planned]
    if len(keys) != len(set(keys)):
        raise CampaignProfileError("HH_HL_RUN_KEYS_NOT_UNIQUE")
    return tuple(planned)


@dataclass(frozen=True, slots=True)
class HhHlRunPlan:
    profile_id: str
    campaign_id: str
    planning_sha: str
    execution_sha: str | None
    manifest_fingerprint: str
    strategy_id: str
    window_count: int
    variant_count: int
    expected_run_count: int
    run_keys: tuple[str, ...]
    runs: tuple[HhHlPlannedRun, ...]
    evidence_namespace: str
    run_plan_fingerprint: str
    grid_status: str
    dataset_status: str
    campaign_execution_authorized: bool
    executable: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "campaign_id": self.campaign_id,
            "planning_sha": self.planning_sha,
            "execution_sha": self.execution_sha,
            "manifest_fingerprint": self.manifest_fingerprint,
            "strategy_id": self.strategy_id,
            "window_count": self.window_count,
            "variant_count": self.variant_count,
            "expected_run_count": self.expected_run_count,
            "run_keys": list(self.run_keys),
            "runs": [r.as_dict() for r in self.runs],
            "evidence_namespace": self.evidence_namespace,
            "run_plan_fingerprint": self.run_plan_fingerprint,
            "grid_status": self.grid_status,
            "dataset_status": self.dataset_status,
            "campaign_execution_authorized": self.campaign_execution_authorized,
            "executable": self.executable,
            "run_plan_provider_id": RUN_PLAN_PROVIDER_ID,
            "runner_contract_version": RUNNER_CONTRACT_VERSION,
            "analyzer_profile_id": ANALYZER_PROFILE_ID,
            "holdout_runs": 0,
            "oos_runs": 0,
            "stress_runs": 0,
            "stage_b_runs": 0,
            "paper_live_order_runs": 0,
        }


def build_hh_hl_run_plan(
    *,
    profile: CampaignProfile | None = None,
    manifest: Mapping[str, Any],
    planning_sha: str,
    dataset_receipt: DatasetBindingReceipt | None = None,
) -> HhHlRunPlan:
    prof = profile or load_profile(HH_HL_PREP_PROFILE_ID)
    if prof.profile_id not in HH_HL_PROFILE_IDS:
        raise CampaignProfileError(f"HH_HL_PROFILE_REQUIRED:{prof.profile_id}")
    if not prof.planning_enabled:
        raise CampaignProfileError("HH_HL_PLANNING_DISABLED")
    # Prep stays planning-only; the replay profile may be execution-capable but
    # still yields a non-executable plan here (no AuthorizationContext).
    if prof.profile_id == HH_HL_PREP_PROFILE_ID and prof.execution_enabled:
        raise CampaignProfileError("HH_HL_PREP_MUST_BE_PLANNING_ONLY")

    assert_profile_manifest_bind(
        prof,
        issue_number=int(manifest.get("issue_number") or 0),
        campaign_id=str(manifest.get("campaign_id") or ""),
        strategy_id=str((manifest.get("strategy_set") or [None])[0]),
        adapter_id=str(manifest.get("adapter_id") or ""),
        manifest_path=str(manifest.get("manifest_path") or prof.manifest_path),
    )
    if list(manifest.get("strategy_set") or []) != [HH_HL_CONTINUATION_STRATEGY_ID]:
        raise CampaignProfileError("HH_HL_STRATEGY_SET_INVALID")

    receipt = dataset_receipt or build_dataset_binding_receipt()
    variants = expand_hh_hl_variants()
    if prof.grid_provider_id != GRID_PROVIDER_ID:
        raise CampaignProfileError(
            f"HH_HL_GRID_PROVIDER_MISMATCH:{prof.grid_provider_id}"
        )

    expected = receipt.window_count * len(variants)
    runs = _expand_runs(
        campaign_id=prof.campaign_id,
        window_ids=receipt.ordered_window_ids,
        variants=variants,
    )
    if len(runs) != expected:
        raise CampaignProfileError(f"HH_HL_RUN_COUNT_MISMATCH:{len(runs)}!={expected}")

    manifest_fp = str(manifest.get("manifest_fingerprint") or "")
    if not manifest_fp:
        raise CampaignProfileError("HH_HL_MANIFEST_FINGERPRINT_REQUIRED")

    body = {
        "profile_id": prof.profile_id,
        "campaign_id": prof.campaign_id,
        "planning_sha": planning_sha,
        "manifest_fingerprint": manifest_fp,
        "run_keys": [r.run_key for r in runs],
        "variant_count": len(variants),
        "window_count": receipt.window_count,
        "selection_sha256": receipt.selection_sha256,
        "content_fingerprint_digest": receipt.content_fingerprint_digest,
        "dataset_status": receipt.quality_gate_status,
        "evidence_namespace": prof.evidence_namespace,
        "grid_provider_id": GRID_PROVIDER_ID,
        "run_plan_provider_id": RUN_PLAN_PROVIDER_ID,
    }
    plan_fp = canonical_hash(body)
    executable = bool(
        manifest.get("campaign_execution_authorized") is False
        and not receipt.local_proof_required
        and False  # never executable in prep profile
    )
    return HhHlRunPlan(
        profile_id=prof.profile_id,
        campaign_id=prof.campaign_id,
        planning_sha=planning_sha,
        execution_sha=None,
        manifest_fingerprint=manifest_fp,
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        window_count=receipt.window_count,
        variant_count=len(variants),
        expected_run_count=expected,
        run_keys=tuple(r.run_key for r in runs),
        runs=runs,
        evidence_namespace=prof.evidence_namespace,
        run_plan_fingerprint=plan_fp,
        grid_status=str(manifest.get("grid_status") or "DRAFT"),
        dataset_status=receipt.quality_gate_status,
        campaign_execution_authorized=False,
        executable=executable,
    )


@dataclass(frozen=True, slots=True)
class HhHlFinalRunPlan:
    """Final/pre-final run plan bound to a ratified Design-GO.

    ``executable`` is always False: structural readiness never implies
    authorization. An Owner Execution-GO (AuthorizationContext) is required at
    execute time and is intentionally not part of the run plan.
    """

    status: str
    post_merge_final: bool
    profile_id: str
    campaign_id: str
    planning_sha: str
    execution_sha: str | None
    manifest_fingerprint: str
    source_manifest_fingerprint: str
    design_body_fingerprint: str
    design_comment_id: int
    design_bound_main_sha: str
    strategy_id: str
    window_count: int
    variant_count: int
    expected_run_count: int
    run_keys: tuple[str, ...]
    evidence_namespace: str
    run_plan_fingerprint: str
    dataset_status: str
    grid_status: str
    campaign_execution_authorized: bool
    executable: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "post_merge_final": self.post_merge_final,
            "profile_id": self.profile_id,
            "campaign_id": self.campaign_id,
            "planning_sha": self.planning_sha,
            "execution_sha": self.execution_sha,
            "manifest_fingerprint": self.manifest_fingerprint,
            "source_manifest_fingerprint": self.source_manifest_fingerprint,
            "design_body_fingerprint": self.design_body_fingerprint,
            "design_comment_id": self.design_comment_id,
            "design_bound_main_sha": self.design_bound_main_sha,
            "strategy_id": self.strategy_id,
            "window_count": self.window_count,
            "variant_count": self.variant_count,
            "expected_run_count": self.expected_run_count,
            "run_keys": list(self.run_keys),
            "evidence_namespace": self.evidence_namespace,
            "run_plan_fingerprint": self.run_plan_fingerprint,
            "dataset_status": self.dataset_status,
            "grid_status": self.grid_status,
            "campaign_execution_authorized": self.campaign_execution_authorized,
            "executable": self.executable,
            "run_plan_provider_id": RUN_PLAN_PROVIDER_ID,
            "runner_contract_version": RUNNER_CONTRACT_VERSION,
            "analyzer_profile_id": ANALYZER_PROFILE_ID,
        }


def _coerce_design_receipt(
    design_receipt: DesignRatificationReceipt | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(design_receipt, DesignRatificationReceipt):
        return design_receipt.as_dict()
    if isinstance(design_receipt, Mapping):
        return dict(design_receipt)
    raise CampaignProfileError("HH_HL_DESIGN_RECEIPT_INVALID_TYPE")


def build_hh_hl_final_run_plan(
    *,
    final_manifest: Mapping[str, Any],
    design_receipt: DesignRatificationReceipt | Mapping[str, Any],
    dataset_receipt: DatasetBindingReceipt | Mapping[str, Any],
    planning_sha: str,
    pre_final: bool = False,
    profile: CampaignProfile | None = None,
    live_main_resolver: GitShaResolver | None = None,
) -> HhHlFinalRunPlan:
    """Build a FINAL (post-merge) or PRE_FINALIZATION (PR) run plan.

    FINAL requires a real post-merge ``main`` SHA that is not the pre-merge base
    the design was ratified against. For the PR deliverable use ``pre_final=True``
    which never claims a post-merge final fingerprint.

    When ``live_main_resolver`` is supplied (CLI/production default), FINAL also
    enforces the live-main gate: ``planning_sha`` must be an existing commit that
    equals the current ``origin/main`` tip. Without a resolver only the
    format/distinct checks run (pure planning unit tests); the CLI always injects
    a resolver unless ``--skip-live-git-gate`` is set for fixtures.
    """
    prof = profile or load_profile(HH_HL_REPLAY_PROFILE_ID)
    if prof.profile_id != HH_HL_REPLAY_PROFILE_ID:
        raise CampaignProfileError(
            f"HH_HL_FINAL_REQUIRES_REPLAY_PROFILE:{prof.profile_id}"
        )

    design = _coerce_design_receipt(design_receipt)
    design_body_fp = str(design.get("body_fingerprint") or "")
    if not design_body_fp:
        raise CampaignProfileError("HH_HL_DESIGN_BODY_FINGERPRINT_REQUIRED")
    design_bound_main_sha = str(design.get("bound_main_sha") or "")

    manifest_fp = str(final_manifest.get("manifest_fingerprint") or "")
    if not manifest_fp:
        raise CampaignProfileError("HH_HL_MANIFEST_FINGERPRINT_REQUIRED")
    if final_manifest.get("campaign_execution_authorized") is not False:
        raise CampaignProfileError("HH_HL_FINAL_MANIFEST_MUST_NOT_BE_AUTHORIZED")
    src_fp = str(final_manifest.get("source_manifest_fingerprint") or "")
    if src_fp != str(design.get("source_manifest_fingerprint") or ""):
        raise CampaignProfileError("HH_HL_FINAL_DESIGN_SOURCE_FP_MISMATCH")

    # Planning-SHA discipline: FINAL must bind a real post-merge main SHA that is
    # distinct from the pre-merge base. With a live resolver it must equal the
    # current origin/main tip. Otherwise require pre_final.
    if not pre_final:
        try:
            if live_main_resolver is not None:
                assert_planning_sha_is_live_main(
                    planning_sha,
                    resolver=live_main_resolver,
                    design_bound_main_sha=design_bound_main_sha,
                )
            else:
                assert_planning_sha_format_and_distinct(
                    planning_sha,
                    design_bound_main_sha=design_bound_main_sha,
                )
        except HhHlShaGateError as exc:
            raise CampaignProfileError(exc.reason_code) from exc

    if isinstance(dataset_receipt, DatasetBindingReceipt):
        receipt = validate_pass_receipt(dataset_receipt.as_dict())
    else:
        receipt = validate_pass_receipt(dict(dataset_receipt))

    base_plan = build_hh_hl_run_plan(
        profile=prof,
        manifest=final_manifest,
        planning_sha=planning_sha,
        dataset_receipt=receipt,
    )

    status = PRE_FINAL_RUN_PLAN_STATUS if pre_final else FINAL_RUN_PLAN_STATUS
    fp_body = {
        "status": status,
        "pre_final": bool(pre_final),
        "profile_id": prof.profile_id,
        "campaign_id": prof.campaign_id,
        "planning_sha": planning_sha,
        "manifest_fingerprint": manifest_fp,
        "source_manifest_fingerprint": src_fp,
        "design_body_fingerprint": design_body_fp,
        "design_comment_id": int(design.get("comment_id") or 0),
        "design_bound_main_sha": design_bound_main_sha,
        "run_keys": list(base_plan.run_keys),
        "variant_count": base_plan.variant_count,
        "window_count": base_plan.window_count,
        "dataset_selection_sha256": receipt.selection_sha256,
        "dataset_content_fingerprint_digest": receipt.content_fingerprint_digest,
        "evidence_namespace": prof.evidence_namespace,
        "run_plan_provider_id": RUN_PLAN_PROVIDER_ID,
    }
    plan_fp = canonical_hash(fp_body)

    return HhHlFinalRunPlan(
        status=status,
        post_merge_final=(not pre_final),
        profile_id=prof.profile_id,
        campaign_id=prof.campaign_id,
        planning_sha=planning_sha,
        execution_sha=None,
        manifest_fingerprint=manifest_fp,
        source_manifest_fingerprint=src_fp,
        design_body_fingerprint=design_body_fp,
        design_comment_id=int(design.get("comment_id") or 0),
        design_bound_main_sha=design_bound_main_sha,
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        window_count=base_plan.window_count,
        variant_count=base_plan.variant_count,
        expected_run_count=base_plan.expected_run_count,
        run_keys=base_plan.run_keys,
        evidence_namespace=prof.evidence_namespace,
        run_plan_fingerprint=plan_fp,
        dataset_status=receipt.quality_gate_status,
        grid_status=str(final_manifest.get("grid", {}).get("status") or "RATIFIED"),
        campaign_execution_authorized=False,
        executable=False,
    )
