"""Environment gate invoked from tools.agent_control.preflight (#4255/#4461)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.agent_control.environment.codes import (
    VERDICT_BLOCKED,
    VERDICT_READY_FOR_RECORDED_TEST,
    VERDICT_READY_OFFLINE_ONLY,
    VERDICT_UNAVAILABLE,
    VERDICT_UNKNOWN,
)
from tools.agent_control.environment.doctor import (
    EnvironmentPreflightResult,
    doctor_profile,
)
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT, REPO_ROOT


def run_environment_preflight(
    *,
    profile_id: str,
    provider_id: str | None,
    contract: dict[str, Any] | None,
    source_commit: str | None = None,
    attestation_path: Path | None = None,
    attestation: dict[str, Any] | None = None,
    config: Path = DEFAULT_CONFIG_ROOT,
    repo_root: Path | None = None,
    execute: bool = False,
    allow_recorded: bool = False,
    allow_live: bool = False,
) -> EnvironmentPreflightResult:
    """Shared environment preflight for dry-run and execute paths.

    Recorded/fake provider transports may execute against local_repo/mock
    profiles without pretending the external provider environment is live-ready.
    Cloud-agent profiles still require their recorded attestation path.
    """
    del attestation  # path-based only to keep doctor deterministic
    result = doctor_profile(
        profile_id,
        config=config,
        repo_root=repo_root or REPO_ROOT,
        attestation_path=attestation_path,
        contract=contract,
        provider_id=provider_id,
        source_commit=source_commit,
        offline=True,
    )

    if not execute:
        if result.verdict in {
            VERDICT_READY_OFFLINE_ONLY,
            VERDICT_READY_FOR_RECORDED_TEST,
        }:
            return result
        return result

    # Recorded/fake transport on an offline-only local/mock environment is not
    # a live-provider readiness claim. It is safe to exercise provider contracts
    # and state normalization without network or runtime provisioning.
    runtime_class = (result.profile_snapshot or {}).get("runtime_class")
    if (
        allow_recorded
        and result.verdict == VERDICT_READY_OFFLINE_ONLY
        and runtime_class in {"local_repo", "mock"}
    ):
        result.execute_ready = True
        result.limitations = list(result.limitations) + [
            "recorded/fake provider transport only; no live environment claim"
        ]
        return result

    # Cloud-provider recorded/fake path still needs READY_FOR_RECORDED_TEST.
    if result.verdict == VERDICT_READY_FOR_RECORDED_TEST and allow_recorded:
        if result.execute_ready:
            return result
        result.verdict = VERDICT_BLOCKED
        result.execute_ready = False
        result.reason_codes = list(result.reason_codes) + [
            "ENVIRONMENT_EXECUTE_NOT_READY"
        ]
        return result

    # Human-GO live cursor/provider: mock/offline-class pilot envs may execute
    # under explicit live flags only. This remains separate from recorded mode.
    if allow_live and result.verdict == VERDICT_READY_OFFLINE_ONLY:
        result.execute_ready = True
        result.limitations = list(result.limitations) + [
            "human_go_live_provider_offline_env"
        ]
        return result

    if result.verdict in {VERDICT_UNKNOWN, VERDICT_UNAVAILABLE}:
        result.execute_ready = False
        return result

    result.execute_ready = False
    if result.verdict == VERDICT_READY_OFFLINE_ONLY:
        result.verdict = VERDICT_BLOCKED
        result.reason_codes = list(result.reason_codes) + [
            "ENVIRONMENT_EXECUTE_REQUIRES_RECORDED_ATTESTATION"
        ]
        result.limitations = list(result.limitations) + [
            "dry-run READY_OFFLINE_ONLY cannot execute"
        ]
    return result
