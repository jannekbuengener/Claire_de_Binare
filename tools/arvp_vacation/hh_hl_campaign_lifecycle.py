"""hh_hl campaign lifecycle / state / resume adapter (#4374).

Thin composition over the frozen #4153 state primitives in
:mod:`tools.arvp_vacation.sensitivity_campaign_state`. Reuses the
``CampaignBindings`` carrier, the resume-inspection state machine, and the
namespace-startable guard. Only the evidence namespace differs: hh_hl uses
``artifacts/arvp_campaign/hh_hl_continuation/4374`` instead of the #4153
``artifacts/arvp_sensitivity/4153`` root (the latter's ``evidence_root_for`` is
intentionally *not* reused here to avoid a #4153 hardcode).

No physical runs are ever started here. Bindings are minted only from a
live-verified :class:`AuthorizationContext`; profile/manifest flags alone can
never produce one. The adapter validates the 39 primary run keys, plans
resume actions (skip identical / retry / start), refuses ``RUNNING`` without a
completion marker, and refuses binding drift — all by composing existing
primitives rather than copying the ~1500-line runner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from tools.arvp_vacation.hh_hl_campaign_execution_authorization import (
    AuthorizationContext,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    CampaignBindings,
    SensitivityStateError,
    assert_namespace_startable,
    inspect_run_for_resume,
)

# hh_hl evidence namespace (profile-owned; never the #4153 root).
HH_HL_EVIDENCE_NAMESPACE = "artifacts/arvp_campaign/hh_hl_continuation/4374"
HH_HL_EVIDENCE_NAMESPACE_PARTS = (
    "artifacts",
    "arvp_campaign",
    "hh_hl_continuation",
    "4374",
)
HH_HL_EXPECTED_RUN_COUNT = 39

# Re-export for callers that only want the hh_hl surface.
__all__ = [
    "CampaignBindings",
    "HhHlLifecycleError",
    "HH_HL_EVIDENCE_NAMESPACE",
    "HH_HL_EXPECTED_RUN_COUNT",
    "hh_hl_evidence_root_for",
    "bindings_from_authorization",
    "validate_primary_run_keys",
    "assert_startable",
    "plan_resume_actions",
]


class HhHlLifecycleError(ValueError):
    """Fail-closed hh_hl lifecycle/binding error carrying a HOLD reason code."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


def hh_hl_evidence_root_for(
    *,
    base: Path,
    campaign_id: str,
    manifest_fingerprint: str,
    authorization_id: str,
) -> Path:
    """Deterministic hh_hl evidence root under the profile namespace.

    Mirrors the #4153 layout shape (campaign/manifest/authorization) but rooted
    at the hh_hl namespace, so #4374 evidence never lands in the #4153 tree.
    """
    if not campaign_id or not manifest_fingerprint or not authorization_id:
        raise HhHlLifecycleError("HH_HL_LIFECYCLE_EVIDENCE_ROOT_FIELDS_REQUIRED")
    root = Path(base)
    for part in HH_HL_EVIDENCE_NAMESPACE_PARTS:
        root = root / part
    return root / campaign_id / manifest_fingerprint / authorization_id


def bindings_from_authorization(
    authorization_context: AuthorizationContext,
    *,
    run_plan_fingerprint: str | None = None,
) -> CampaignBindings:
    """Mint :class:`CampaignBindings` from a verified Owner Execution-GO only.

    ``run_plan_fingerprint`` may be supplied to cross-check the run plan the
    caller intends to execute against the authorization; a mismatch fails
    closed. Without an override the authorization's own bound run-plan
    fingerprint is used.
    """
    if not isinstance(authorization_context, AuthorizationContext):
        raise HhHlLifecycleError("HH_HL_LIFECYCLE_AUTHORIZATION_REQUIRED")
    ctx = authorization_context
    if run_plan_fingerprint is not None and run_plan_fingerprint != (
        ctx.run_plan_fingerprint
    ):
        raise HhHlLifecycleError(
            "HH_HL_LIFECYCLE_RUN_PLAN_FINGERPRINT_MISMATCH",
            f"requested={run_plan_fingerprint} bound={ctx.run_plan_fingerprint}",
        )
    if not str(ctx.evidence_namespace or "").startswith(HH_HL_EVIDENCE_NAMESPACE):
        raise HhHlLifecycleError(
            "HH_HL_LIFECYCLE_EVIDENCE_NAMESPACE_MISMATCH", ctx.evidence_namespace
        )
    return CampaignBindings(
        campaign_id=ctx.campaign_id,
        manifest_fingerprint=ctx.manifest_fingerprint,
        run_plan_fingerprint=ctx.run_plan_fingerprint,
        authorization_fingerprint=ctx.authorization_fingerprint,
        execution_sha=ctx.execution_sha,
        main_sha=ctx.bound_main_sha,
    )


def validate_primary_run_keys(run_keys: Mapping | list | tuple) -> tuple[str, ...]:
    """Assert exactly ``HH_HL_EXPECTED_RUN_COUNT`` unique primary run keys."""
    keys = tuple(str(k) for k in run_keys)
    if len(keys) != HH_HL_EXPECTED_RUN_COUNT:
        raise HhHlLifecycleError(
            "HH_HL_LIFECYCLE_RUN_KEY_COUNT_MISMATCH",
            f"{len(keys)}!={HH_HL_EXPECTED_RUN_COUNT}",
        )
    if len(set(keys)) != len(keys):
        raise HhHlLifecycleError("HH_HL_LIFECYCLE_RUN_KEYS_NOT_UNIQUE")
    return keys


def assert_startable(
    root: Path,
    *,
    bindings: CampaignBindings,
    allow_resume: bool = True,
) -> str:
    """Return ``fresh`` or ``resume``; fail closed on foreign/stale evidence.

    Thin pass-through to the #4153 primitive so hh_hl inherits the exact
    namespace-collision and binding-mismatch guarantees.
    """
    return assert_namespace_startable(
        Path(root), bindings=bindings, allow_resume=allow_resume
    )


def plan_resume_actions(
    root: Path,
    *,
    bindings: CampaignBindings,
    run_keys: Mapping | list | tuple,
    max_attempts: int = 1,
    retry_failed: bool = True,
) -> dict[str, str]:
    """Compute per-run resume actions (skip | retry | start).

    Composes :func:`inspect_run_for_resume` for every validated run key, so a
    ``SUCCEEDED`` run with an intact marker/result skips, a ``RUNNING`` run
    without completion fails closed (``STATE_RUNNING_WITHOUT_COMPLETION``), and
    any binding drift fails closed (``STATE_BINDING_MISMATCH``). Never starts a
    run — planning only.
    """
    keys = validate_primary_run_keys(run_keys)
    actions: dict[str, str] = {}
    for run_key in keys:
        actions[run_key] = inspect_run_for_resume(
            Path(root),
            run_key=run_key,
            bindings=bindings,
            max_attempts=max_attempts,
            retry_failed=retry_failed,
        )
    return actions
