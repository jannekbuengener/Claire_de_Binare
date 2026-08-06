"""Profile-bound campaign executor providers (#4374).

Keeps StrategyReplayCampaignExecutor PB1-only. hh_hl routes only via an
explicit provider and remains blocked while execution_enabled=false.
Never opens Batch-B scenario-group paths.
"""

from __future__ import annotations

from typing import Any

from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    LEGACY_4153_PROFILE_ID,
    CampaignProfile,
    CampaignProfileError,
    assert_execution_allowed,
    load_profile,
)
from tools.arvp_vacation.sensitivity_campaign_executor import (
    CampaignRunExecutor,
    RunEnvelope,
    RunResult,
    StrategyReplayCampaignExecutor,
)

LEGACY_EXECUTOR_PROVIDER_ID = "legacy_4153_strategy_replay"
HH_HL_EXECUTOR_PROVIDER_ID = "hh_hl_single_run_replay_v1"


class PlanningOnlyExecutor:
    """Refuse all executes for planning-only profiles."""

    def __init__(self, profile: CampaignProfile) -> None:
        self.profile = profile
        self.calls: list[RunEnvelope] = []

    def execute(self, envelope: RunEnvelope) -> RunResult:
        self.calls.append(envelope)
        raise CampaignProfileError(
            f"PLANNING_ONLY_EXECUTE_FORBIDDEN:{self.profile.profile_id}"
        )


class HhHlSingleRunReplayProvider:
    """Explicit hh_hl provider bound to single-run replay surface only.

    Real invocation remains fail-closed without execution_enabled + Owner-GO.
    Does not use scenario-group / Batch-B banned paths.
    """

    def __init__(self, profile: CampaignProfile) -> None:
        if profile.profile_id != HH_HL_PREP_PROFILE_ID:
            raise CampaignProfileError(
                f"HH_HL_PROVIDER_PROFILE_MISMATCH:{profile.profile_id}"
            )
        if profile.strategy_id != HH_HL_CONTINUATION_STRATEGY_ID:
            raise CampaignProfileError("HH_HL_PROVIDER_STRATEGY_MISMATCH")
        if profile.adapter_id != BATCH_B_SHADOW_ADAPTER_ID:
            raise CampaignProfileError("HH_HL_PROVIDER_ADAPTER_MISMATCH")
        self.profile = profile
        self.calls: list[RunEnvelope] = []

    def build_single_run_request(self, envelope: RunEnvelope) -> dict[str, Any]:
        if envelope.strategy_id != HH_HL_CONTINUATION_STRATEGY_ID:
            raise CampaignProfileError(
                f"HH_HL_ENVELOPE_STRATEGY_MISMATCH:{envelope.strategy_id}"
            )
        if envelope.strategy_id == "primary_breakout_v1":
            raise CampaignProfileError("HH_HL_NO_PB1_FALLBACK")
        # Explicitly refuse scenario-group fields.
        params = dict(envelope.parameters or {})
        if "scenario_group_id" in params or "scenario_ids" in params:
            raise CampaignProfileError("HH_HL_SCENARIO_GROUP_FORBIDDEN")
        return {
            "dataset_source": "file_or_bound_window",
            "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
            "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
            "window_id": envelope.window_id,
            "parameters": params,
            "scenario_group_id": None,
            "scenario_ids": None,
            "surface": "services.validation.strategy_replay_runner.single_run",
        }

    def execute(self, envelope: RunEnvelope) -> RunResult:
        self.calls.append(envelope)
        assert_execution_allowed(self.profile)
        # Unreachable for prep profile: assert_execution_allowed raises.
        raise CampaignProfileError("HH_HL_EXECUTE_UNREACHABLE_WITHOUT_OWNER_GO")


def resolve_campaign_executor(profile: CampaignProfile) -> CampaignRunExecutor:
    """Dispatch executor by explicit profile provider id — no silent fallback."""
    if not profile.execution_enabled:
        return PlanningOnlyExecutor(profile)

    if profile.executor_provider_id == LEGACY_EXECUTOR_PROVIDER_ID:
        if profile.profile_id != LEGACY_4153_PROFILE_ID:
            raise CampaignProfileError("LEGACY_EXECUTOR_PROFILE_MISMATCH")
        if profile.strategy_id != "primary_breakout_v1":
            raise CampaignProfileError("LEGACY_EXECUTOR_STRATEGY_MISMATCH")
        return StrategyReplayCampaignExecutor(adapter_id=profile.adapter_id)

    if profile.executor_provider_id == HH_HL_EXECUTOR_PROVIDER_ID:
        return HhHlSingleRunReplayProvider(profile)

    raise CampaignProfileError(
        f"HOLD_REGISTRY_PROVIDER_MISSING:{profile.executor_provider_id}"
    )


def resolve_executor_for_profile_id(profile_id: str) -> CampaignRunExecutor:
    return resolve_campaign_executor(load_profile(profile_id))
