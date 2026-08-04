"""Deterministic run-plan expansion + fingerprint for #4153 sensitivity campaign."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.sensitivity_campaign_analyzer_contract import (
    ANALYZER_CONTRACT_VERSION,
    physical_parameter_set_fingerprint,
    slot_metadata_for_variant,
)
from tools.arvp_vacation.sensitivity_campaign_authorization import (
    ANALYZER_CONTRACT_VERSION as _AUTH_ANALYZER_VER,
    RUNNER_CONTRACT_VERSION,
)
from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    EXPECTED_UNIQUE_VARIANTS,
    STRATEGY_ID,
    VariantSpec,
    expand_runs,
    expand_variants,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import fingerprint_manifest

assert _AUTH_ANALYZER_VER == ANALYZER_CONTRACT_VERSION

EVIDENCE_NAMESPACE_ROOT = "artifacts/arvp_sensitivity/4153"
EVIDENCE_ROOT_TEMPLATE = (
    "artifacts/arvp_sensitivity/4153/{campaign_id}/"
    "{manifest_fingerprint}/{authorization_id}"
)


@dataclass(frozen=True, slots=True)
class PlannedRun:
    run_key: str
    window_id: str
    strategy_id: str
    slot_id: str
    phase: str
    label: str
    scenario_id: str
    param_set: dict[str, Any]
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


@dataclass(frozen=True, slots=True)
class RunPlan:
    campaign_id: str
    main_sha: str
    manifest_fingerprint: str
    runner_contract_version: str
    analyzer_contract_version: str
    strategy_id: str
    window_count: int
    matrix_slots: int
    physical_parameter_sets: int
    run_count: int
    run_keys: tuple[str, ...]
    slots: tuple[dict[str, Any], ...]
    runs: tuple[PlannedRun, ...]
    evidence_namespace: str
    evidence_root_template: str
    surface_requirement_profile: dict[str, Any]
    resource_budget_contract: dict[str, Any]
    resume_policy: dict[str, Any]
    reproduction_policy: dict[str, Any]
    run_plan_fingerprint: str
    holdout_runs: int = 0
    oos_runs: int = 0
    stress_runs: int = 0
    stage_b_runs: int = 0
    paper_live_order_runs: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "main_sha": self.main_sha,
            "manifest_fingerprint": self.manifest_fingerprint,
            "runner_contract_version": self.runner_contract_version,
            "analyzer_contract_version": self.analyzer_contract_version,
            "strategy_id": self.strategy_id,
            "window_count": self.window_count,
            "matrix_slots": self.matrix_slots,
            "physical_parameter_sets": self.physical_parameter_sets,
            "run_count": self.run_count,
            "run_keys": list(self.run_keys),
            "slots": list(self.slots),
            "runs": [r.as_dict() for r in self.runs],
            "evidence_namespace": self.evidence_namespace,
            "evidence_root_template": self.evidence_root_template,
            "surface_requirement_profile": dict(self.surface_requirement_profile),
            "resource_budget_contract": dict(self.resource_budget_contract),
            "resume_policy": dict(self.resume_policy),
            "reproduction_policy": dict(self.reproduction_policy),
            "run_plan_fingerprint": self.run_plan_fingerprint,
            "holdout_runs": self.holdout_runs,
            "oos_runs": self.oos_runs,
            "stress_runs": self.stress_runs,
            "stage_b_runs": self.stage_b_runs,
            "paper_live_order_runs": self.paper_live_order_runs,
        }


DEFAULT_SURFACE_REQUIREMENT_PROFILE = {
    "surface_kind": "local_owner_workstation",
    "network_mode": "offline_replay_only",
    "exchange_credentials_required": False,
    "dataset_root_required": True,
    "os_family_any_of": ["Windows", "Linux"],
    "min_cpu_count": 1,
    "min_ram_bytes": 4 * 1024**3,
    "min_free_artifact_bytes": 20 * 1024**3,
}

# Budget fields are required by the GO schema; concrete values are bound by
# a future Owner-GO. The plan exposes the contract shape, not a chosen budget.
DEFAULT_RESOURCE_BUDGET_CONTRACT = {
    "schema_version": "cdb.sensitivity_campaign_resource_budget.v1",
    "bound_by": "owner_go",
    "required_fields": [
        "max_parallelism",
        "max_in_flight_runs",
        "max_attempts_per_run",
        "max_run_wall_time_seconds",
        "max_campaign_wall_time_seconds",
        "max_artifact_bytes",
        "minimum_free_disk_bytes",
        "max_consecutive_failures",
        "max_total_failures",
        "log_retention_days",
    ],
    "hard_caps": {
        "max_parallelism": 8,
        "max_in_flight_runs": 8,
        "max_attempts_per_run": 3,
        "max_run_count": EXPECTED_RUN_COUNT,
    },
}

DEFAULT_RESUME_POLICY = {
    "allow_resume": True,
    "skip_succeeded_identical_bindings": True,
    "retry_failed": True,
    "refuse_running_without_completion": True,
    "refuse_binding_mismatch": True,
}

DEFAULT_REPRODUCTION_POLICY = {
    "enabled": True,
    "max_reproduction_attempts_per_key": 1,
    "comparison_mode": "exact_equality",
    "baseline_run_key_count": 1,
    "sample_run_key_count": 5,
    "compared_result_fields": [
        "gate_reason",
        "trade_count",
        "turnover",
        "fees",
        "spread",
        "slippage",
        "gross_pnl",
        "net_pnl",
        "profit_factor",
        "expectancy",
        "drawdown",
    ],
    "on_mismatch": "block_campaign_completion",
}


def _fingerprint_body(
    *,
    main_sha: str,
    manifest_fingerprint: str,
    runner_contract_version: str,
    run_keys: Sequence[str],
    slots: Sequence[Mapping[str, Any]],
    surface_requirement_profile: Mapping[str, Any],
    resource_budget_contract: Mapping[str, Any],
    resume_policy: Mapping[str, Any],
    reproduction_policy: Mapping[str, Any],
    analyzer_contract_version: str,
    evidence_namespace: str,
    evidence_root_template: str,
) -> dict[str, Any]:
    return {
        "main_sha": main_sha,
        "manifest_fingerprint": manifest_fingerprint,
        "runner_contract_version": runner_contract_version,
        "run_keys": list(run_keys),
        "slots": [dict(s) for s in slots],
        "surface_requirement_profile": dict(surface_requirement_profile),
        "resource_budget_contract": dict(resource_budget_contract),
        "resume_policy": dict(resume_policy),
        "reproduction_policy": dict(reproduction_policy),
        "analyzer_contract_version": analyzer_contract_version,
        "evidence_namespace": evidence_namespace,
        "evidence_root_template": evidence_root_template,
    }


def build_run_plan(
    manifest: Mapping[str, Any],
    *,
    main_sha: str,
    surface_requirement_profile: Mapping[str, Any] | None = None,
    resource_budget_contract: Mapping[str, Any] | None = None,
    resume_policy: Mapping[str, Any] | None = None,
    reproduction_policy: Mapping[str, Any] | None = None,
) -> RunPlan:
    if not re_full_sha(main_sha):
        raise ValueError(f"main_sha must be 40-hex, got {main_sha!r}")

    campaign_id = str(manifest.get("campaign_id") or "")
    if campaign_id != "arvp-sensitivity-4153-v1":
        raise ValueError(f"unexpected campaign_id: {campaign_id!r}")

    manifest_fp = str(
        manifest.get("manifest_fingerprint") or fingerprint_manifest(manifest)
    )
    window_ids = list(
        (manifest.get("development_windows") or {}).get("window_ids") or []
    )
    if len(window_ids) != 39:
        raise ValueError(f"window_count must be 39, got {len(window_ids)}")

    strategies = list(manifest.get("strategies") or [])
    if strategies != [STRATEGY_ID]:
        raise ValueError(f"strategy_set must be [{STRATEGY_ID}], got {strategies!r}")

    variants = expand_variants()
    if len(variants) != EXPECTED_UNIQUE_VARIANTS:
        raise ValueError("variant count mismatch")

    slots = [slot_metadata_for_variant(v) for v in variants]
    physical_fps = {s["physical_parameter_set_fingerprint"] for s in slots}
    if len(physical_fps) != 19:
        raise ValueError(f"physical parameter sets must be 19, got {len(physical_fps)}")

    raw_runs = expand_runs(
        campaign_id=campaign_id,
        window_ids=window_ids,
        strategy_id=STRATEGY_ID,
        variants=variants,
    )
    if len(raw_runs) != EXPECTED_RUN_COUNT:
        raise ValueError("run count mismatch")

    planned: list[PlannedRun] = []
    for run in raw_runs:
        variant: VariantSpec = run.variant
        meta = slot_metadata_for_variant(variant)
        planned.append(
            PlannedRun(
                run_key=run.run_key,
                window_id=run.window_id,
                strategy_id=run.strategy_id,
                slot_id=meta["slot_id"],
                phase=meta["phase"],
                label=meta["label"],
                scenario_id=meta["scenario_id"],
                param_set=dict(variant.param_set),
                physical_parameter_set_fingerprint=meta[
                    "physical_parameter_set_fingerprint"
                ],
            )
        )

    run_keys = tuple(r.run_key for r in planned)
    if len(set(run_keys)) != EXPECTED_RUN_COUNT:
        raise ValueError("run keys must be unique")

    surface_prof = dict(
        surface_requirement_profile or DEFAULT_SURFACE_REQUIREMENT_PROFILE
    )
    budget_contract = dict(resource_budget_contract or DEFAULT_RESOURCE_BUDGET_CONTRACT)
    resume = dict(resume_policy or DEFAULT_RESUME_POLICY)
    reproduction = dict(reproduction_policy or DEFAULT_REPRODUCTION_POLICY)

    body = _fingerprint_body(
        main_sha=main_sha,
        manifest_fingerprint=manifest_fp,
        runner_contract_version=RUNNER_CONTRACT_VERSION,
        run_keys=run_keys,
        slots=slots,
        surface_requirement_profile=surface_prof,
        resource_budget_contract=budget_contract,
        resume_policy=resume,
        reproduction_policy=reproduction,
        analyzer_contract_version=ANALYZER_CONTRACT_VERSION,
        evidence_namespace=EVIDENCE_NAMESPACE_ROOT,
        evidence_root_template=EVIDENCE_ROOT_TEMPLATE,
    )
    plan_fp = canonical_hash(body)

    return RunPlan(
        campaign_id=campaign_id,
        main_sha=main_sha,
        manifest_fingerprint=manifest_fp,
        runner_contract_version=RUNNER_CONTRACT_VERSION,
        analyzer_contract_version=ANALYZER_CONTRACT_VERSION,
        strategy_id=STRATEGY_ID,
        window_count=39,
        matrix_slots=EXPECTED_UNIQUE_VARIANTS,
        physical_parameter_sets=19,
        run_count=EXPECTED_RUN_COUNT,
        run_keys=run_keys,
        slots=tuple(slots),
        runs=tuple(planned),
        evidence_namespace=EVIDENCE_NAMESPACE_ROOT,
        evidence_root_template=EVIDENCE_ROOT_TEMPLATE,
        surface_requirement_profile=surface_prof,
        resource_budget_contract=budget_contract,
        resume_policy=resume,
        reproduction_policy=reproduction,
        run_plan_fingerprint=plan_fp,
    )


def re_full_sha(value: str) -> bool:
    if len(value) != 40:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def physical_fps_for_plan(plan: RunPlan) -> set[str]:
    return {r.physical_parameter_set_fingerprint for r in plan.runs}
