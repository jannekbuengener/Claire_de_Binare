"""Profile-bound campaign executor providers (#4374).

Keeps StrategyReplayCampaignExecutor PB1-only. hh_hl routes only via an
explicit provider and remains blocked while execution_enabled=false.
Never opens Batch-B scenario-group paths.
"""

from __future__ import annotations

from datetime import datetime
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
from tools.arvp_vacation.hh_hl_single_run_callable import (
    build_production_single_run_callable,
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
        if not envelope.output_dir:
            raise CampaignProfileError("HOLD_EXECUTION_OUTPUT_DIR_REQUIRED")
        if not envelope.dataset_content_fingerprint:
            raise CampaignProfileError(
                "HOLD_EXECUTION_DATASET_CONTENT_FINGERPRINT_REQUIRED"
            )
        return {
            "dataset_source": "binance_window",
            "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
            "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
            "window_id": envelope.window_id,
            "run_key": envelope.run_key,
            "parameters": params,
            "output_dir": envelope.output_dir,
            "dataset_content_fingerprint": envelope.dataset_content_fingerprint,
            "scenario_group_id": None,
            "scenario_ids": None,
            "surface": self.SURFACE_ID,
        }

    def _assert_authorization_binds_envelope(
        self,
        authorization_context: AuthorizationContext,
        envelope: RunEnvelope,
    ) -> None:
        """Fail closed unless the envelope is *exactly* bound to the context.

        Every binding must be present AND exactly equal — an empty string or
        ``None`` is a HOLD, never a skip. Truthy-guarded ``if x and x != y``
        shortcuts are forbidden here: a blank envelope field can no longer slip
        past a binding check.
        """
        ctx = authorization_context
        if not isinstance(ctx, AuthorizationContext):
            raise CampaignProfileError("HOLD_EXECUTION_OWNER_GO_REQUIRED")
        if ctx.granted_capabilities != ("campaign_execution_replay_only",):
            raise CampaignProfileError("HOLD_EXECUTION_CAPABILITY_INVALID")
        # Campaign id: non-empty, equal to the context AND the bound profile.
        if not envelope.campaign_id or envelope.campaign_id != ctx.campaign_id:
            raise CampaignProfileError("HOLD_EXECUTION_CAMPAIGN_MISMATCH")
        if ctx.campaign_id != self.profile.campaign_id:
            raise CampaignProfileError("HOLD_EXECUTION_CAMPAIGN_MISMATCH")
        # Strategy/adapter are bound via the context here; the envelope-level
        # strategy match (incl. explicit PB1 refusal) stays in
        # build_single_run_request so its specific reason codes are preserved.
        if HH_HL_CONTINUATION_STRATEGY_ID not in ctx.strategy_set:
            raise CampaignProfileError("HOLD_EXECUTION_STRATEGY_MISMATCH")
        if ctx.adapter_id != BATCH_B_SHADOW_ADAPTER_ID:
            raise CampaignProfileError("HOLD_EXECUTION_ADAPTER_MISMATCH")
        # Fingerprint bindings: present AND exact (empty string rejects).
        if not envelope.manifest_fingerprint or not ctx.binds_manifest(
            envelope.manifest_fingerprint
        ):
            raise CampaignProfileError("HOLD_EXECUTION_MANIFEST_MISMATCH")
        if not envelope.run_plan_fingerprint or not ctx.binds_run_plan(
            envelope.run_plan_fingerprint
        ):
            raise CampaignProfileError("HOLD_EXECUTION_RUN_PLAN_MISMATCH")
        if (
            not envelope.authorization_fingerprint
            or envelope.authorization_fingerprint != ctx.authorization_fingerprint
        ):
            raise CampaignProfileError(
                "HOLD_EXECUTION_AUTHORIZATION_FINGERPRINT_MISMATCH"
            )
        # Execution SHA: present AND exactly the authorized commit.
        if not envelope.execution_sha or envelope.execution_sha != ctx.execution_sha:
            raise CampaignProfileError("HOLD_EXECUTION_EXECUTION_SHA_MISMATCH")
        # Non-empty run addressing.
        if not envelope.run_key:
            raise CampaignProfileError("HOLD_EXECUTION_RUN_KEY_REQUIRED")
        if not envelope.window_id:
            raise CampaignProfileError("HOLD_EXECUTION_WINDOW_ID_REQUIRED")

    def _resolve_single_run_callable(self) -> SingleRunCallable:
        if self._single_run_callable is not None:
            return self._single_run_callable
        raise CampaignProfileError("HOLD_EXECUTION_SINGLE_RUN_CALLABLE_UNSET")

    def execute(
        self,
        envelope: RunEnvelope,
        authorization_context: AuthorizationContext | None = None,
        *,
        now_utc: datetime | None = None,
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
        # Envelope/param shape gate (strategy match, PB1 refusal, scenario-group
        # ban) — all before any callable is resolved.
        request = self.build_single_run_request(envelope)
        # Re-check the finite expiry on *every* dispatch, immediately before the
        # callable: a context that lapsed between GO verification and execution
        # must never reach the single-run surface (0 callable invocations).
        try:
            authorization_context.assert_not_expired(now_utc=now_utc)
        except HhHlExecutionAuthorizationError as exc:
            raise CampaignProfileError(exc.reason_code) from exc
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
        # Production path: wire the real strategy_replay_runner single-run
        # callable. Tests may still construct HhHlSingleRunReplayProvider with an
        # injected fake callable; resolve_campaign_executor never leaves it unset.
        return HhHlSingleRunReplayProvider(
            profile,
            single_run_callable=build_production_single_run_callable(),
        )

    raise CampaignProfileError(
        f"HOLD_REGISTRY_PROVIDER_MISSING:{profile.executor_provider_id}"
    )


def resolve_executor_for_profile_id(profile_id: str) -> CampaignRunExecutor:
    return resolve_campaign_executor(load_profile(profile_id))
