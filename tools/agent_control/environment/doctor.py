"""Environment profile validation and offline doctor (#4255)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.agent_control.environment.attestation import load_attestation
from tools.agent_control.environment.attenuation import (
    attenuate_constraints,
    detect_network_expansion,
)
from tools.agent_control.environment.codes import (
    CLOUD_AGENT_REQUIRED_FIELDS,
    GOVERNED_PROFILE_IDS,
    PROVIDER_CONFIG_REF_DEFAULT,
    REASON_ARTIFACT_PATH_INVALID,
    REASON_BASE_IDENTITY_UNVERIFIED,
    REASON_CHECKPOINT_DRIFT,
    REASON_CONFIG_MISSING,
    REASON_COST_LIMIT_UNVERIFIED,
    REASON_EGRESS_UNENFORCED,
    REASON_FALLBACK_FORBIDDEN,
    REASON_FALLBACK_UNPROVEN,
    REASON_LIVE_DISPATCH,
    REASON_PROFILE_DIGEST_MISMATCH,
    REASON_PROFILE_INCOMPLETE,
    REASON_PROFILE_UNKNOWN,
    REASON_PROVIDER_NOT_ALLOWED,
    REASON_REQUIRED_TOOL_MISSING,
    REASON_RESOURCE_LIMIT_UNVERIFIED,
    REASON_RUNTIME_BLOCKED,
    REASON_SECRET_SCOPE_VIOLATION,
    REASON_SETUP_FAILED,
    REASON_SETUP_UNPROVEN,
    REASON_SOURCE_COMMIT_MISMATCH,
    REASON_TIMEOUT_CANCEL_UNCONFIRMED,
    REASON_TOOL_VERSION_MISMATCH,
    REASON_WORKSPACE_SCOPE_INVALID,
    VERDICT_BLOCKED,
    VERDICT_READY_FOR_RECORDED_TEST,
    VERDICT_READY_OFFLINE_ONLY,
    VERDICT_UNKNOWN,
)
from tools.agent_control.environment.cursor_config import (
    validate_cursor_environment_config,
)
from tools.agent_control.environment.digest import profile_digest, redact_mapping
from tools.agent_control.errors import DispatchError, RegistryError
from tools.agent_control.load import load_registry_document
from tools.agent_control.normalize import normalize_registry
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT, REPO_ROOT
from tools.agent_control.validate import validate_registry


@dataclass
class EnvironmentPreflightResult:
    profile_id: str
    profile_version: str | None
    profile_digest: str | None
    provider_id: str | None
    provider_config_ref: str | None
    provider_config_digest: str | None
    source_commit: str | None
    setup_status: str
    base_identity_status: str
    fallback_status: str
    toolchain_status: str
    workspace_status: str
    egress_status: str
    secret_status: str
    resource_status: str
    timeout_status: str
    cost_status: str
    artifact_status: str
    execute_ready: bool
    offline_ready: bool
    verdict: str
    reason_codes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    profile_snapshot: dict[str, Any] | None = None
    effective_constraints: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return redact_mapping(
            {
                "profile_id": self.profile_id,
                "profile_version": self.profile_version,
                "profile_digest": self.profile_digest,
                "provider_id": self.provider_id,
                "provider_config_ref": self.provider_config_ref,
                "provider_config_digest": self.provider_config_digest,
                "source_commit": self.source_commit,
                "setup_status": self.setup_status,
                "base_identity_status": self.base_identity_status,
                "fallback_status": self.fallback_status,
                "toolchain_status": self.toolchain_status,
                "workspace_status": self.workspace_status,
                "egress_status": self.egress_status,
                "secret_status": self.secret_status,
                "resource_status": self.resource_status,
                "timeout_status": self.timeout_status,
                "cost_status": self.cost_status,
                "artifact_status": self.artifact_status,
                "execute_ready": self.execute_ready,
                "offline_ready": self.offline_ready,
                "verdict": self.verdict,
                "reason_codes": list(self.reason_codes),
                "limitations": list(self.limitations),
                "effective_constraints": self.effective_constraints,
            }
        )


def _ensure_cloud_fields(profile_id: str, profile: dict[str, Any]) -> list[str]:
    if profile.get("runtime_class") != "cloud_agent":
        return []
    missing = [f for f in CLOUD_AGENT_REQUIRED_FIELDS if f not in profile]
    if missing:
        raise RegistryError(
            REASON_PROFILE_INCOMPLETE,
            f"cloud_agent profile {profile_id!r} missing fields: {missing}",
        )
    if profile.get("live_dispatch_allowed") is not False:
        raise RegistryError(
            REASON_LIVE_DISPATCH,
            f"profile {profile_id!r} must set live_dispatch_allowed=false",
        )
    cost = profile.get("cost_limit") or {}
    if cost.get("max_live_cost_usd") not in (0, 0.0):
        raise RegistryError(
            REASON_COST_LIMIT_UNVERIFIED,
            f"profile {profile_id!r} max_live_cost_usd must be 0 in #4255",
        )
    return []


def validate_profile(
    profile_id: str,
    *,
    config: Path = DEFAULT_CONFIG_ROOT,
) -> dict[str, Any]:
    document = load_registry_document(config)
    validate_registry(document)
    normalized = normalize_registry(document)
    profiles = normalized["profiles"]["environments"]
    if profile_id not in profiles:
        raise RegistryError(
            REASON_PROFILE_UNKNOWN,
            f"unknown environment profile: {profile_id}",
        )
    profile = deepcopy(profiles[profile_id])
    _ensure_cloud_fields(profile_id, profile)
    digest = profile_digest(profile)
    return {
        "profile_id": profile_id,
        "valid": True,
        "profile_digest": digest,
        "runtime_class": profile.get("runtime_class"),
        "live_dispatch_allowed": profile.get("live_dispatch_allowed", False),
    }


def validate_all_profiles(*, config: Path = DEFAULT_CONFIG_ROOT) -> dict[str, Any]:
    document = load_registry_document(config)
    validate_registry(document)
    normalized = normalize_registry(document)
    envs = normalized["profiles"]["environments"]
    results = []
    for profile_id in sorted(envs):
        profile = deepcopy(envs[profile_id])
        _ensure_cloud_fields(profile_id, profile)
        results.append(
            {
                "profile_id": profile_id,
                "profile_digest": profile_digest(profile),
                "runtime_class": profile.get("runtime_class"),
            }
        )
    missing_governed = [p for p in GOVERNED_PROFILE_IDS if p not in envs]
    if missing_governed:
        raise RegistryError(
            REASON_PROFILE_UNKNOWN,
            f"missing governed profiles: {missing_governed}",
        )
    # Provider config schema check (shared).
    cursor = validate_cursor_environment_config(REPO_ROOT)
    return {
        "valid": True,
        "profiles": results,
        "governed_profile_ids": list(GOVERNED_PROFILE_IDS),
        "provider_config_ref": PROVIDER_CONFIG_REF_DEFAULT,
        "provider_config_digest": cursor["digest"],
    }


def _status_pass() -> str:
    return "ok"


def doctor_profile(
    profile_id: str,
    *,
    config: Path = DEFAULT_CONFIG_ROOT,
    repo_root: Path | None = None,
    attestation_path: Path | None = None,
    contract: dict[str, Any] | None = None,
    provider_id: str | None = None,
    source_commit: str | None = None,
    offline: bool = True,
) -> EnvironmentPreflightResult:
    """Offline/fixture environment doctor. Never contacts Cursor providers."""
    del offline  # offline is the only supported mode in #4255
    root = (repo_root or REPO_ROOT).resolve()
    document = load_registry_document(config)
    validate_registry(document)
    normalized = normalize_registry(document)
    envs = normalized["profiles"]["environments"]
    if profile_id not in envs:
        return EnvironmentPreflightResult(
            profile_id=profile_id,
            profile_version=None,
            profile_digest=None,
            provider_id=provider_id,
            provider_config_ref=None,
            provider_config_digest=None,
            source_commit=source_commit,
            setup_status="unknown",
            base_identity_status="unknown",
            fallback_status="unknown",
            toolchain_status="unknown",
            workspace_status="unknown",
            egress_status="unknown",
            secret_status="unknown",
            resource_status="unknown",
            timeout_status="unknown",
            cost_status="unknown",
            artifact_status="unknown",
            execute_ready=False,
            offline_ready=False,
            verdict=VERDICT_BLOCKED,
            reason_codes=[REASON_PROFILE_UNKNOWN],
            limitations=["profile not found in registry"],
        )

    profile = deepcopy(envs[profile_id])
    try:
        _ensure_cloud_fields(profile_id, profile)
    except RegistryError as exc:
        return EnvironmentPreflightResult(
            profile_id=profile_id,
            profile_version=profile.get("profile_version"),
            profile_digest=None,
            provider_id=provider_id,
            provider_config_ref=profile.get("provider_config_ref"),
            provider_config_digest=None,
            source_commit=source_commit,
            setup_status="unknown",
            base_identity_status="unknown",
            fallback_status="unknown",
            toolchain_status="unknown",
            workspace_status="unknown",
            egress_status="unknown",
            secret_status="unknown",
            resource_status="unknown",
            timeout_status="unknown",
            cost_status="unknown",
            artifact_status="unknown",
            execute_ready=False,
            offline_ready=False,
            verdict=VERDICT_BLOCKED,
            reason_codes=[exc.code],
            limitations=[exc.message],
            profile_snapshot=profile,
        )

    reasons: list[str] = []
    limitations: list[str] = []
    setup_status = "not_run"
    base_identity_status = "unknown"
    fallback_status = "unknown"
    toolchain_status = "unknown"
    workspace_status = "unknown"
    egress_status = "unknown"
    secret_status = "unknown"
    resource_status = "unknown"
    timeout_status = "unknown"
    cost_status = "unknown"
    artifact_status = "unknown"

    digest = profile_digest(profile)
    provider_config_ref = (
        profile.get("provider_config_ref") or PROVIDER_CONFIG_REF_DEFAULT
    )
    provider_config_digest = None

    try:
        cursor = validate_cursor_environment_config(root)
        provider_config_digest = cursor["digest"]
        if cursor.get("agent_can_update_snapshot") is True:
            reasons.append(REASON_FALLBACK_FORBIDDEN)
            limitations.append(
                "agentCanUpdateSnapshot=true is forbidden; automatic snapshot "
                "mutation must stay disabled"
            )
        elif cursor.get("agent_can_update_snapshot") is not False:
            limitations.append(
                "agentCanUpdateSnapshot not explicitly false; treat auto-update "
                "as unproven for live readiness"
            )
        # Snapshot ID alone never proves base identity.
        if cursor.get("snapshot_id"):
            limitations.append("opaque snapshot id is not a trusted CDB base identity")
            base_identity_status = "unverified"
    except DispatchError as exc:
        reasons.append(exc.code)
        limitations.append(exc.message)
        if exc.code == REASON_CONFIG_MISSING:
            provider_config_digest = None

    # Minimal profiles (mock/local_repo): offline schema-ready without attestation.
    if profile.get("runtime_class") != "cloud_agent":
        return EnvironmentPreflightResult(
            profile_id=profile_id,
            profile_version=profile.get("profile_version"),
            profile_digest=digest,
            provider_id=provider_id or "mock",
            provider_config_ref=provider_config_ref,
            provider_config_digest=provider_config_digest,
            source_commit=source_commit,
            setup_status="not_applicable",
            base_identity_status="not_applicable",
            fallback_status="not_applicable",
            toolchain_status="not_applicable",
            workspace_status="ok",
            egress_status="not_applicable",
            secret_status="ok",
            resource_status="not_applicable",
            timeout_status="not_applicable",
            cost_status="ok",
            artifact_status="ok",
            execute_ready=False,
            offline_ready=True,
            verdict=VERDICT_READY_OFFLINE_ONLY,
            reason_codes=[],
            limitations=["mock/local_repo profile: offline only"],
            profile_snapshot=profile,
        )

    if profile.get("workspace_policy", {}).get("mode") == "blocked":
        reasons.append(REASON_RUNTIME_BLOCKED)
        workspace_status = "blocked"
        limitations.append("workspace_policy.mode=blocked; not executable in #4255")

    effective = None
    if contract is not None:
        try:
            if detect_network_expansion(contract, profile):
                reasons.append(REASON_EGRESS_UNENFORCED)
                limitations.append("contract network allowlist expands profile")
                egress_status = "blocked"
            effective = attenuate_constraints(contract, profile)
            workspace_status = (
                "ok" if workspace_status != "blocked" else workspace_status
            )
        except DispatchError as exc:
            reasons.append(exc.code)
            limitations.append(exc.message)
            if exc.code == REASON_SECRET_SCOPE_VIOLATION:
                secret_status = "blocked"
            elif exc.code == REASON_WORKSPACE_SCOPE_INVALID:
                workspace_status = "blocked"
            else:
                workspace_status = "blocked"

    # Artifact policy static checks.
    art = profile.get("artifact_policy") or {}
    if art.get("auto_execute") is True:
        reasons.append(REASON_ARTIFACT_PATH_INVALID)
        artifact_status = "blocked"
    else:
        artifact_status = "ok"
    for root_path in art.get("allowed_roots") or []:
        if Path(root_path).is_absolute() or ".." in Path(root_path).parts:
            reasons.append(REASON_ARTIFACT_PATH_INVALID)
            artifact_status = "blocked"

    ck = profile.get("checkpoint_policy") or {}
    if any(
        ck.get(k) is True
        for k in (
            "may_mutate_profile",
            "may_mutate_digest",
            "may_mutate_source_commit",
            "may_mutate_permissions",
            "provider_snapshot_is_cdb_checkpoint",
        )
    ):
        reasons.append(REASON_CHECKPOINT_DRIFT)
        limitations.append("checkpoint_policy must not allow binding mutation")

    # Cost/resource ceilings present but enforcement unknown without attestation.
    cost_status = "unknown"
    resource_status = "unknown"
    egress_status = egress_status if egress_status != "unknown" else "unknown"
    timeout_status = "unknown"
    toolchain_status = "unknown"
    secret_status = secret_status if secret_status != "unknown" else "ok"

    attestation = None
    if attestation_path is not None:
        attestation = load_attestation(attestation_path)
        if attestation.get("profile_id") != profile_id:
            reasons.append(REASON_PROFILE_DIGEST_MISMATCH)
        if attestation.get("profile_digest") != digest:
            reasons.append(REASON_PROFILE_DIGEST_MISMATCH)
            limitations.append("attestation profile_digest mismatch")
        if (
            provider_config_digest
            and attestation.get("provider_config_digest") != provider_config_digest
        ):
            reasons.append(REASON_PROFILE_DIGEST_MISMATCH)
            limitations.append("provider config digest mismatch")
        if source_commit and attestation.get("source_commit") != source_commit:
            reasons.append(REASON_SOURCE_COMMIT_MISMATCH)
        if provider_id and attestation.get("provider_id") != provider_id:
            reasons.append(REASON_PROVIDER_NOT_ALLOWED)

        setup_status = str(attestation.get("setup_status") or "unknown").lower()
        if setup_status in {"failed", "error"}:
            reasons.append(REASON_SETUP_FAILED)
        elif setup_status in {"unknown", "not_run", "not-run"}:
            reasons.append(REASON_SETUP_UNPROVEN)
            setup_status = "unknown" if setup_status == "unknown" else "not_run"

        base_identity_status = str(
            attestation.get("base_identity_status") or "unknown"
        ).lower()
        if base_identity_status in {"unknown", "unverified", ""}:
            reasons.append(REASON_BASE_IDENTITY_UNVERIFIED)
            base_identity_status = "unverified"

        fallback_raw = attestation.get("fallback_detected")
        if fallback_raw is True:
            reasons.append(REASON_FALLBACK_FORBIDDEN)
            fallback_status = "true"
        elif fallback_raw is False:
            fallback_status = "false"
        else:
            reasons.append(REASON_FALLBACK_UNPROVEN)
            fallback_status = "unknown"

        observed = attestation.get("observed_tool_versions") or {}
        required = profile.get("required_toolchain") or []
        for tool in required:
            name = tool.get("name")
            rule = tool.get("version_rule")
            if name not in observed:
                if rule and str(rule).startswith("optional:"):
                    continue
                reasons.append(REASON_REQUIRED_TOOL_MISSING)
                toolchain_status = "missing"
            else:
                observed_ver = str(observed[name])
                if rule == "==3.12" and not observed_ver.startswith("3.12"):
                    reasons.append(REASON_TOOL_VERSION_MISMATCH)
                    toolchain_status = "mismatch"
        if toolchain_status == "unknown" and required:
            toolchain_status = "ok"

        enforcement = attestation.get("enforcement") or {}
        for key, reason, attr in (
            ("egress", REASON_EGRESS_UNENFORCED, "egress"),
            ("secrets", REASON_SECRET_SCOPE_VIOLATION, "secret"),
            ("resources", REASON_RESOURCE_LIMIT_UNVERIFIED, "resource"),
            ("cost", REASON_COST_LIMIT_UNVERIFIED, "cost"),
        ):
            status = str(enforcement.get(key) or "unknown").lower()
            if status in {"unknown", "unenforced", "false", "0"}:
                reasons.append(reason)
                if attr == "egress":
                    egress_status = "unenforced"
                elif attr == "secret":
                    secret_status = "unenforced"
                elif attr == "resource":
                    resource_status = "unverified"
                else:
                    cost_status = "unverified"
            else:
                if attr == "egress":
                    egress_status = "enforced"
                elif attr == "secret":
                    secret_status = "ok"
                elif attr == "resource":
                    resource_status = "verified"
                else:
                    cost_status = "verified"

        # Cancel confirmation / timeout — cloud profiles require confirmed cancel.
        if enforcement.get("timeout_cancel_confirmed") is True:
            timeout_status = "ok"
        else:
            timeout_status = "unverified"
            if profile.get("runtime_class") == "cloud_agent":
                reasons.append(REASON_TIMEOUT_CANCEL_UNCONFIRMED)

        ck_att = attestation.get("checkpoint") or {}
        if ck_att.get("profile_digest") and ck_att.get("profile_digest") != digest:
            reasons.append(REASON_CHECKPOINT_DRIFT)
        if (
            source_commit
            and ck_att.get("source_commit")
            and ck_att.get("source_commit") != source_commit
        ):
            reasons.append(REASON_CHECKPOINT_DRIFT)

        art_att = attestation.get("artifacts") or []
        for item in art_att:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "")
            if (
                path.startswith("/")
                or ".." in Path(path).parts
                or path.startswith("\\")
            ):
                reasons.append(REASON_ARTIFACT_PATH_INVALID)
                artifact_status = "blocked"
            if item.get("presigned_url"):
                reasons.append(REASON_ARTIFACT_PATH_INVALID)
                artifact_status = "blocked"
    else:
        # Offline without attestation: setup/base/fallback unknown → not execute-ready.
        reasons.extend(
            [
                REASON_SETUP_UNPROVEN,
                REASON_BASE_IDENTITY_UNVERIFIED,
                REASON_FALLBACK_UNPROVEN,
                REASON_EGRESS_UNENFORCED,
                REASON_RESOURCE_LIMIT_UNVERIFIED,
                REASON_COST_LIMIT_UNVERIFIED,
            ]
        )
        limitations.append(
            "offline doctor without attestation cannot prove live readiness"
        )
        setup_status = "not_run"
        base_identity_status = "unverified"
        fallback_status = "unknown"

    if provider_id and profile.get("runtime_class") == "cloud_agent":
        allowed = set(profile.get("allowed_provider_ids") or [])
        if provider_id not in allowed:
            reasons.append(REASON_PROVIDER_NOT_ALLOWED)

    # Deduplicate reason codes while preserving order.
    seen: set[str] = set()
    uniq_reasons: list[str] = []
    for code in reasons:
        if code not in seen:
            seen.add(code)
            uniq_reasons.append(code)

    # Verdict selection.
    live_blocking = {
        REASON_SETUP_FAILED,
        REASON_SETUP_UNPROVEN,
        REASON_FALLBACK_FORBIDDEN,
        REASON_FALLBACK_UNPROVEN,
        REASON_BASE_IDENTITY_UNVERIFIED,
        REASON_PROFILE_DIGEST_MISMATCH,
        REASON_SOURCE_COMMIT_MISMATCH,
        REASON_EGRESS_UNENFORCED,
        REASON_RESOURCE_LIMIT_UNVERIFIED,
        REASON_COST_LIMIT_UNVERIFIED,
        REASON_REQUIRED_TOOL_MISSING,
        REASON_TOOL_VERSION_MISMATCH,
        REASON_SECRET_SCOPE_VIOLATION,
        REASON_ARTIFACT_PATH_INVALID,
        REASON_CHECKPOINT_DRIFT,
        REASON_RUNTIME_BLOCKED,
        REASON_PROVIDER_NOT_ALLOWED,
        REASON_CONFIG_MISSING,
        REASON_WORKSPACE_SCOPE_INVALID,
        REASON_TIMEOUT_CANCEL_UNCONFIRMED,
    }
    hard_block = [c for c in uniq_reasons if c in live_blocking]

    execute_ready = False
    offline_ready = provider_config_digest is not None and not any(
        c
        in {
            REASON_CONFIG_MISSING,
            REASON_PROFILE_UNKNOWN,
            REASON_PROFILE_INCOMPLETE,
            REASON_LIVE_DISPATCH,
        }
        for c in uniq_reasons
    )

    if profile.get("live_dispatch_allowed") is True:
        hard_block.append(REASON_LIVE_DISPATCH)
        uniq_reasons.append(REASON_LIVE_DISPATCH)

    if attestation is not None and not hard_block:
        # Recorded/fake path only — still never live.
        verdict = VERDICT_READY_FOR_RECORDED_TEST
        execute_ready = True
        offline_ready = True
        setup_status = setup_status if setup_status != "not_run" else "succeeded"
    elif offline_ready and (
        attestation is None
        or all(
            c
            in {
                REASON_SETUP_UNPROVEN,
                REASON_BASE_IDENTITY_UNVERIFIED,
                REASON_FALLBACK_UNPROVEN,
                REASON_EGRESS_UNENFORCED,
                REASON_RESOURCE_LIMIT_UNVERIFIED,
                REASON_COST_LIMIT_UNVERIFIED,
            }
            for c in uniq_reasons
        )
    ):
        verdict = VERDICT_READY_OFFLINE_ONLY
        execute_ready = False
    elif not uniq_reasons:
        verdict = VERDICT_READY_OFFLINE_ONLY
        execute_ready = False
    elif any(c == REASON_SETUP_FAILED for c in uniq_reasons):
        verdict = VERDICT_BLOCKED
    elif any(
        c in {REASON_FALLBACK_FORBIDDEN, REASON_PROFILE_DIGEST_MISMATCH}
        for c in uniq_reasons
    ):
        verdict = VERDICT_BLOCKED
    else:
        # Unknown enforcement / unproven setup → BLOCKED for execute, may still
        # surface as UNKNOWN when attestation fields themselves are unknown.
        if attestation is not None and (
            fallback_status == "unknown" or setup_status in {"unknown", "not_run"}
        ):
            verdict = VERDICT_UNKNOWN if setup_status == "unknown" else VERDICT_BLOCKED
        else:
            verdict = VERDICT_BLOCKED if hard_block else VERDICT_READY_OFFLINE_ONLY

    if verdict == VERDICT_READY_FOR_RECORDED_TEST:
        # Strip informational unproven reasons that were cleared by attestation.
        uniq_reasons = []
        limitations = [
            "READY_FOR_RECORDED_TEST only; live Cursor dispatch remains forbidden",
            "environment success is not PASS / not merge authority",
        ]
    elif verdict == VERDICT_READY_OFFLINE_ONLY:
        execute_ready = False
        limitations.append("execute_ready=false; offline schema/doctor only")

    return EnvironmentPreflightResult(
        profile_id=profile_id,
        profile_version=str(profile.get("profile_version") or ""),
        profile_digest=digest,
        provider_id=provider_id,
        provider_config_ref=provider_config_ref,
        provider_config_digest=provider_config_digest,
        source_commit=source_commit,
        setup_status=setup_status,
        base_identity_status=base_identity_status,
        fallback_status=fallback_status,
        toolchain_status=toolchain_status,
        workspace_status=workspace_status,
        egress_status=egress_status,
        secret_status=secret_status,
        resource_status=resource_status,
        timeout_status=timeout_status,
        cost_status=cost_status,
        artifact_status=artifact_status,
        execute_ready=execute_ready,
        offline_ready=offline_ready
        and verdict in {VERDICT_READY_OFFLINE_ONLY, VERDICT_READY_FOR_RECORDED_TEST},
        verdict=verdict,
        reason_codes=uniq_reasons,
        limitations=limitations,
        profile_snapshot=profile,
        effective_constraints=effective,
    )
