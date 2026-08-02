"""Environment gate invoked from tools.agent_control.preflight (#4255)."""

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
) -> EnvironmentPreflightResult:
    """Shared environment preflight for dry-run and execute paths.

    If ``attestation`` dict is provided (tests), write it to a temp-less path by
    using doctor with attestation_path only when a path is given. For in-memory
    attestations, callers should pass ``attestation_path`` to a fixture file.
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
        # Dry-run may proceed when offline-ready even if execute_ready is false.
        if result.verdict in {
            VERDICT_READY_OFFLINE_ONLY,
            VERDICT_READY_FOR_RECORDED_TEST,
        }:
            return result
        return result

    # Execute path: only READY_FOR_RECORDED_TEST with allow_recorded may proceed.
    if result.verdict == VERDICT_READY_FOR_RECORDED_TEST and allow_recorded:
        if result.execute_ready:
            return result
        result.verdict = VERDICT_BLOCKED
        result.execute_ready = False
        result.reason_codes = list(result.reason_codes) + [
            "ENVIRONMENT_EXECUTE_NOT_READY"
        ]
        return result

    if result.verdict in {VERDICT_UNKNOWN, VERDICT_UNAVAILABLE}:
        result.execute_ready = False
        return result

    # Any other verdict blocks execute (including READY_OFFLINE_ONLY).
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
