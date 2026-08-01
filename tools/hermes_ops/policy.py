"""Capability and deny policy for Hermes profiles (#4289)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORBIDDEN_GITHUB_ACTIONS = frozenset(
    {
        "publish_cdb_local_ci",
        "admin_merge",
        "edit_branch_protection",
        "read_or_write_repo_secrets",
        "force_push",
        "delete_default_branch",
        "expand_app_permissions",
    }
)

PROFILE_POLICY: dict[str, dict[str, Any]] = {
    "jannek-assistant": {
        "windows_access": False,
        "github_write": False,
        "live_authority": False,
        "risk_authority": False,
        "merge_authority": False,
        "cdb_local_ci_publish": False,
        "allowed_repositories": [],
        "token_permissions": {},
    },
    "cdb-engineer": {
        "windows_access": "dedicated_workspace_only",
        "github_write": True,
        "live_authority": False,
        "risk_authority": False,
        "merge_authority": False,
        "cdb_local_ci_publish": False,
        "allowed_repositories": ["jannekbuengener/Claire_de_Binare"],  # pragma: allowlist secret
        # Minimal contents write for branches/PRs; never checks:write (CI publish).
        "token_permissions": {
            "contents": "write",
            "pull_requests": "write",
            "issues": "write",
            "metadata": "read",
        },
    },
    "validation-chief": {
        "windows_access": False,
        "github_write": False,
        "live_authority": False,
        "risk_authority": False,
        "merge_authority": False,
        "cdb_local_ci_publish": False,
        "enabled_by_default": False,
        "allowed_repositories": [],
        "token_permissions": {},
    },
}


@dataclass(frozen=True)
class PolicyVerdict:
    ok: bool
    profile: str
    reason: str
    details: dict[str, Any]


def get_profile_policy(profile: str) -> dict[str, Any]:
    if profile not in PROFILE_POLICY:
        raise KeyError(f"unknown hermes profile: {profile}")
    return dict(PROFILE_POLICY[profile])


def assert_action_allowed(profile: str, action: str) -> PolicyVerdict:
    policy = get_profile_policy(profile)
    if action in FORBIDDEN_GITHUB_ACTIONS:
        return PolicyVerdict(
            ok=False,
            profile=profile,
            reason="forbidden_github_action",
            details={"action": action},
        )
    if action.startswith("github_write") and not policy.get("github_write"):
        return PolicyVerdict(
            ok=False,
            profile=profile,
            reason="github_write_disabled_for_profile",
            details={"action": action},
        )
    if action == "windows_shell" and not policy.get("windows_access"):
        return PolicyVerdict(
            ok=False,
            profile=profile,
            reason="windows_access_disabled_for_profile",
            details={"action": action},
        )
    if action in {"live_trade", "risk_override", "strategy_promote", "capital_go"}:
        return PolicyVerdict(
            ok=False,
            profile=profile,
            reason="cdb_live_boundary",
            details={"action": action},
        )
    if action == "publish_cdb_local_ci":
        return PolicyVerdict(
            ok=False,
            profile=profile,
            reason="cdb_local_ci_publish_forbidden",
            details={"action": action},
        )
    return PolicyVerdict(
        ok=True, profile=profile, reason="allowed", details={"action": action}
    )


def omnipotent_combination_forbidden(capabilities: set[str]) -> bool:
    """True if a capability set illegally combines personal + admin powers."""
    personal = "personal_memory" in capabilities
    windows_admin = "windows_admin" in capabilities
    github_admin = "github_admin" in capabilities
    live = "cdb_live" in capabilities
    return personal and (windows_admin or github_admin or live)


def validate_distribution_cdb_block(cdb: dict[str, Any], profile: str) -> list[str]:
    errors: list[str] = []
    expected = get_profile_policy(profile)
    if cdb.get("live_authority") is not False:
        errors.append("live_authority must be false")
    if cdb.get("risk_authority") is not False:
        errors.append("risk_authority must be false")
    if cdb.get("merge_authority") is not False:
        errors.append("merge_authority must be false")
    if cdb.get("cdb_local_ci_publish") is not False:
        errors.append("cdb_local_ci_publish must be false")
    if profile == "jannek-assistant":
        if cdb.get("windows_access") not in (False, "false", None):
            errors.append("jannek-assistant must not allow windows_access")
        if cdb.get("github_write") not in (False, "false", None):
            errors.append("jannek-assistant must not allow github_write")
    if profile == "cdb-engineer":
        allowed = list(cdb.get("allowed_repositories") or [])
        if expected["allowed_repositories"] != allowed:
            errors.append(
                "cdb-engineer allowed_repositories drift from policy "
                f"(got {allowed})"
            )
    if profile == "validation-chief" and cdb.get("enabled_by_default") is True:
        errors.append("validation-chief must stay disabled by default until #4270")
    return errors
