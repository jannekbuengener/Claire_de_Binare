"""Profile-bound campaign executor providers (#4374).

Keeps StrategyReplayCampaignExecutor PB1-only. hh_hl routes only via an
explicit provider and remains blocked while execution_enabled=false.
Never opens Batch-B scenario-group paths.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PROFILE_IDS,
    LEGACY_4153_PROFILE_ID,
    CampaignProfile,
    CampaignProfileError,
    assert_execution_allowed,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_execution_authorization import (
    AuthorizationContext,
    HhHlExecutionAuthorizationError,
)
from tools.arvp_vacation.sensitivity_campaign_executor import (
    CampaignRunExecutor,
    RunEnvelope,
    RunResult,
    StrategyReplayCampaignExecutor,
)

LEGACY_EXECUTOR_PROVIDER_ID = "legacy_4153_strategy_replay"
HH_HL_EXECUTOR_PROVIDER_ID = "hh_hl_single_run_replay_v1"

# Injectable single-run surface: maps a bound single-run request to a RunResult.
# Real replays remain gated behind a live Owner Execution-GO; tests inject a
# fake callable so no physical run is ever started in this slice.
SingleRunCallable = Callable[[Mapping[str, Any]], RunResult]


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

    ``execute`` fails closed with ``HOLD_EXECUTION_OWNER_GO_REQUIRED`` unless a
    live-verified :class:`AuthorizationContext` is supplied that binds this
    campaign, manifest, and run plan. Profile/manifest flags alone are never
    sufficient. Never opens scenario-group / Batch-B banned paths and never
    falls back to PB1.
    """

    SURFACE_ID = "services.validation.strategy_replay_runner.single_run"

    def __init__(
        self,
        profile: CampaignProfile,
        *,
        single_run_callable: SingleRunCallable | None = None,
    ) -> None:
        if profile.profile_id not in HH_HL_PROFILE_IDS:
            raise CampaignProfileError(
                f"HH_HL_PROVIDER_PROFILE_MISMATCH:{profile.profile_id}"
            )
        if profile.strategy_id != HH_HL_CONTINUATION_STRATEGY_ID:
            raise CampaignProfileError("HH_HL_PROVIDER_STRATEGY_MISMATCH")
        if profile.adapter_id != BATCH_B_SHADOW_ADAPTER_ID:
            raise CampaignProfileError("HH_HL_PROVIDER_ADAPTER_MISMATCH")
        self.profile = profile
        self._single_run_callable = single_run_callable
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
            "run_key": envelope.run_key,
            "parameters": params,
            "scenario_group_id": None,
            "scenario_ids": None,
            "surface": self.SURFACE_ID,
        }

    def _assert_authorization_binds_envelope(
        self,
        authorization_context: AuthorizationContext,
        envelope: RunEnvelope,
    ) -> None:
        ctx = authorization_context
        if not isinstance(ctx, AuthorizationContext):
            raise CampaignProfileError("HOLD_EXECUTION_OWNER_GO_REQUIRED")
        if ctx.granted_capabilities != ("campaign_execution_replay_only",):
            raise CampaignProfileError("HOLD_EXECUTION_CAPABILITY_INVALID")
        if ctx.campaign_id != self.profile.campaign_id:
            raise CampaignProfileError("HOLD_EXECUTION_CAMPAIGN_MISMATCH")
        if HH_HL_CONTINUATION_STRATEGY_ID not in ctx.strategy_set:
            raise CampaignProfileError("HOLD_EXECUTION_STRATEGY_MISMATCH")
        if ctx.adapter_id != BATCH_B_SHADOW_ADAPTER_ID:
            raise CampaignProfileError("HOLD_EXECUTION_ADAPTER_MISMATCH")
        if envelope.manifest_fingerprint and not ctx.binds_manifest(
            envelope.manifest_fingerprint
        ):
            raise CampaignProfileError("HOLD_EXECUTION_MANIFEST_MISMATCH")
        if envelope.run_plan_fingerprint and not ctx.binds_run_plan(
            envelope.run_plan_fingerprint
        ):
            raise CampaignProfileError("HOLD_EXECUTION_RUN_PLAN_MISMATCH")
        if (
            envelope.authorization_fingerprint
            and envelope.authorization_fingerprint != ctx.authorization_fingerprint
        ):
            raise CampaignProfileError(
                "HOLD_EXECUTION_AUTHORIZATION_FINGERPRINT_MISMATCH"
            )

    def _resolve_single_run_callable(self) -> SingleRunCallable:
        if self._single_run_callable is not None:
            return self._single_run_callable
        raise CampaignProfileError("HOLD_EXECUTION_SINGLE_RUN_CALLABLE_UNSET")

    def execute(
        self,
        envelope: RunEnvelope,
        authorization_context: AuthorizationContext | None = None,
    ) -> RunResult:
        self.calls.append(envelope)
        # Fail closed *first* on missing Owner-GO — profile/manifest flags alone
        # (even execution_enabled=true) must never reach the single-run surface.
        if authorization_context is None:
            raise CampaignProfileError("HOLD_EXECUTION_OWNER_GO_REQUIRED")
        # Structural profile gate (planning-only profiles still refuse here).
        assert_execution_allowed(self.profile)
        try:
            self._assert_authorization_binds_envelope(authorization_context, envelope)
        except HhHlExecutionAuthorizationError as exc:  # pragma: no cover - defensive
            raise CampaignProfileError(
                f"HOLD_EXECUTION_AUTHORIZATION_INVALID:{exc.reason_code}"
            ) from exc
        request = self.build_single_run_request(envelope)
        single_run = self._resolve_single_run_callable()
        result = single_run(request)
        if not isinstance(result, RunResult):
            raise CampaignProfileError("HH_HL_SINGLE_RUN_RESULT_INVALID")
        bindings = {
            "campaign_id": self.profile.campaign_id,
            "manifest_fingerprint": authorization_context.manifest_fingerprint,
            "run_plan_fingerprint": authorization_context.run_plan_fingerprint,
            "authorization_fingerprint": (
                authorization_context.authorization_fingerprint
            ),
            "window_id": envelope.window_id,
            "run_key": envelope.run_key,
            "surface": self.SURFACE_ID,
        }
        metrics = dict(result.metrics)
        metrics["campaign_bindings"] = bindings
        return RunResult(
            exit_code=result.exit_code, metrics=metrics, detail=result.detail
        )


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
