"""Provider attenuation: rights/scope/budget may only shrink."""

from __future__ import annotations

import copy
from typing import Any

from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.hashing import attach_digest
from tools.agent_execution_contract.paths import normalize_repo_relative_path

PERMISSION_KEYS = (
    "read_repo",
    "write_code",
    "write_docs",
    "commit",
    "push",
    "open_pr",
    "update_pr",
    "comment_issue",
    "close_issue",
    "publish_cdb_local_ci",
    "merge",
    "runtime_mutation",
    "database_mutation",
    "mcp_live_mutation",
)


def _as_bool_map(permissions: Any, *, label: str) -> dict[str, bool]:
    if not isinstance(permissions, dict):
        raise ContractValidationError(
            "CONTRACT_PERMISSION_INVALID",
            f"{label} permissions must be an object",
        )
    out: dict[str, bool] = {}
    for key in PERMISSION_KEYS:
        if key not in permissions:
            raise ContractValidationError(
                "CONTRACT_PERMISSION_MISSING",
                f"{label} missing permission field {key!r}; absent must not be true",
            )
        value = permissions[key]
        if not isinstance(value, bool):
            raise ContractValidationError(
                "CONTRACT_PERMISSION_INVALID",
                f"{label}.{key} must be boolean",
            )
        out[key] = value
    unknown = sorted(set(permissions) - set(PERMISSION_KEYS))
    if unknown:
        raise ContractValidationError(
            "CONTRACT_UNKNOWN_FIELD",
            f"{label} unknown permission fields: {', '.join(unknown)}",
        )
    return out


def attenuate_permissions(
    base: dict[str, bool], override: dict[str, bool]
) -> dict[str, bool]:
    """Apply provider permission overrides; only true→false is allowed."""
    result = dict(base)
    for key, new_value in override.items():
        if key not in PERMISSION_KEYS:
            raise ContractValidationError(
                "CONTRACT_UNKNOWN_FIELD",
                f"provider permission override unknown field: {key}",
            )
        old_value = base[key]
        if new_value and not old_value:
            raise ContractValidationError(
                "CONTRACT_PERMISSION_ESCALATION",
                f"provider attempted false→true escalation on {key}",
            )
        if old_value and not new_value:
            result[key] = False
        else:
            result[key] = old_value and new_value
    return result


def _subset_paths(base: list[str], override: list[str], *, field: str) -> list[str]:
    base_norm = {normalize_repo_relative_path(p) for p in base}
    ov_norm = [normalize_repo_relative_path(p) for p in override]
    for path in ov_norm:
        if path not in base_norm:
            # Allow further restriction via more-specific child only when base
            # contains a matching directory wildcard prefix.
            if not any(
                (b.endswith("/*") and (path == b[:-2] or path.startswith(b[:-1])))
                for b in base_norm
            ):
                raise ContractValidationError(
                    "CONTRACT_SCOPE_EXPANSION",
                    f"provider expanded {field} beyond base allowlist: {path}",
                )
    return sorted(set(ov_norm))


def _superset_paths(base: list[str], override: list[str], *, field: str) -> list[str]:
    base_norm = {normalize_repo_relative_path(p) for p in base}
    ov_norm = {normalize_repo_relative_path(p) for p in override}
    if not base_norm.issubset(ov_norm):
        missing = sorted(base_norm - ov_norm)
        raise ContractValidationError(
            "CONTRACT_SCOPE_EXPANSION",
            f"provider removed {field} entries (forbidden may only grow): {missing}",
        )
    return sorted(ov_norm)


def _attenuate_budget(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key in ("wall_time_seconds", "max_iterations", "max_tool_calls"):
        if key not in override:
            continue
        new_val = override[key]
        old_val = base[key]
        if not isinstance(new_val, int) or isinstance(new_val, bool) or new_val < 0:
            raise ContractValidationError(
                "CONTRACT_BUDGET_INVALID",
                f"provider budget.{key} must be a non-negative integer",
            )
        if new_val > old_val:
            raise ContractValidationError(
                "CONTRACT_SCOPE_EXPANSION",
                f"provider expanded budget.{key} from {old_val} to {new_val}",
            )
        result[key] = new_val

    if "network_policy" in override:
        base_net = base["network_policy"]
        ov_net = override["network_policy"]
        if not isinstance(ov_net, dict):
            raise ContractValidationError(
                "CONTRACT_BUDGET_INVALID",
                "provider network_policy must be an object",
            )
        mode = ov_net.get("mode", base_net.get("mode"))
        if mode not in {"deny_all", "allowlist"}:
            raise ContractValidationError(
                "CONTRACT_BUDGET_INVALID",
                "network_policy.mode must be deny_all or allowlist",
            )
        if base_net.get("mode") == "deny_all" and mode == "allowlist":
            raise ContractValidationError(
                "CONTRACT_SCOPE_EXPANSION",
                "provider expanded network_policy from deny_all to allowlist",
            )
        base_domains = set(base_net.get("allowed_domains") or [])
        ov_domains = set(ov_net.get("allowed_domains") or [])
        if mode == "allowlist" and not ov_domains.issubset(base_domains):
            raise ContractValidationError(
                "CONTRACT_SCOPE_EXPANSION",
                "provider expanded network_policy.allowed_domains",
            )
        base_classes = set(base_net.get("allowed_classes") or [])
        ov_classes = set(ov_net.get("allowed_classes") or [])
        if not ov_classes.issubset(base_classes):
            raise ContractValidationError(
                "CONTRACT_SCOPE_EXPANSION",
                "provider expanded network_policy.allowed_classes",
            )
        result["network_policy"] = {
            "mode": mode,
            "allowed_domains": sorted(ov_domains),
            "allowed_classes": sorted(ov_classes),
        }
    return result


def attenuate_contract(
    base_contract: dict[str, Any],
    provider_override: dict[str, Any],
) -> dict[str, Any]:
    """Return a provider-reduced contract. Escalation is fail-closed."""
    if not isinstance(provider_override, dict):
        raise ContractValidationError(
            "CONTRACT_TYPE_INVALID",
            "provider_override must be an object",
        )
    forbidden_core = {
        "schema_id",
        "schema_version",
        "contract_id",
        "created_at",
        "producer",
        "issue",
        "route",
        "validation_and_delivery",
        "integrity",
    }
    overlap = sorted(set(provider_override) & forbidden_core)
    if overlap:
        raise ContractValidationError(
            "CONTRACT_CORE_OVERRIDE",
            "provider extensions must not override core fields: " + ", ".join(overlap),
        )

    result = copy.deepcopy(base_contract)

    if "permissions" in provider_override:
        base_perms = _as_bool_map(base_contract["permissions"], label="base")
        ov_perms = _as_bool_map(provider_override["permissions"], label="provider")
        result["permissions"] = attenuate_permissions(base_perms, ov_perms)

    if "execution_scope" in provider_override:
        base_scope = base_contract["execution_scope"]
        ov_scope = provider_override["execution_scope"]
        if not isinstance(ov_scope, dict):
            raise ContractValidationError(
                "CONTRACT_SCOPE_INVALID",
                "provider execution_scope must be an object",
            )
        scope = copy.deepcopy(base_scope)
        if "allowed_paths" in ov_scope:
            scope["allowed_paths"] = _subset_paths(
                list(base_scope.get("allowed_paths") or []),
                list(ov_scope["allowed_paths"] or []),
                field="allowed_paths",
            )
        if "forbidden_paths" in ov_scope:
            scope["forbidden_paths"] = _superset_paths(
                list(base_scope.get("forbidden_paths") or []),
                list(ov_scope["forbidden_paths"] or []),
                field="forbidden_paths",
            )
        if "allowed_commands_or_command_classes" in ov_scope:
            base_cmds = set(base_scope.get("allowed_commands_or_command_classes") or [])
            ov_cmds = set(ov_scope.get("allowed_commands_or_command_classes") or [])
            if not ov_cmds.issubset(base_cmds):
                raise ContractValidationError(
                    "CONTRACT_SCOPE_EXPANSION",
                    "provider expanded allowed_commands_or_command_classes",
                )
            scope["allowed_commands_or_command_classes"] = sorted(ov_cmds)
        if "stop_conditions" in ov_scope:
            base_stops = list(base_scope.get("stop_conditions") or [])
            ov_stops = list(ov_scope.get("stop_conditions") or [])
            if any(item not in ov_stops for item in base_stops):
                raise ContractValidationError(
                    "CONTRACT_SCOPE_EXPANSION",
                    "provider must not remove stop_conditions",
                )
            # Provider may only add additional stop conditions.
            scope["stop_conditions"] = ov_stops
        for key in ("issue_scope", "delivery_target"):
            if key in ov_scope and ov_scope[key] != base_scope.get(key):
                raise ContractValidationError(
                    "CONTRACT_CORE_OVERRIDE",
                    f"provider must not override execution_scope.{key}",
                )
        result["execution_scope"] = scope

    if "budget" in provider_override:
        result["budget"] = _attenuate_budget(
            base_contract["budget"], provider_override["budget"]
        )

    if "environment" in provider_override:
        env_ov = provider_override["environment"]
        if not isinstance(env_ov, dict):
            raise ContractValidationError(
                "CONTRACT_TYPE_INVALID",
                "provider environment override must be an object",
            )
        env = copy.deepcopy(base_contract["environment"])
        # Provider may only narrow lists / replace provider_profile.extensions.
        for list_key in ("mcp_profiles", "skills", "subagents", "secret_references"):
            if list_key in env_ov:
                if list_key == "secret_references":
                    raise ContractValidationError(
                        "CONTRACT_CORE_OVERRIDE",
                        "provider must not rewrite secret_references",
                    )
                base_set = set(env.get(list_key) or [])
                ov_set = set(env_ov.get(list_key) or [])
                if not ov_set.issubset(base_set):
                    raise ContractValidationError(
                        "CONTRACT_SCOPE_EXPANSION",
                        f"provider expanded environment.{list_key}",
                    )
                env[list_key] = sorted(ov_set)
        if "provider_profile" in env_ov:
            base_pp = env.get("provider_profile") or {}
            ov_pp = env_ov["provider_profile"]
            if not isinstance(ov_pp, dict):
                raise ContractValidationError(
                    "CONTRACT_TYPE_INVALID",
                    "provider_profile override must be an object",
                )
            if ov_pp.get("provider_id") not in (None, base_pp.get("provider_id")):
                raise ContractValidationError(
                    "CONTRACT_CORE_OVERRIDE",
                    "provider_id cannot be changed by attenuation",
                )
            merged_pp = copy.deepcopy(base_pp)
            if "profile_name" in ov_pp:
                merged_pp["profile_name"] = ov_pp["profile_name"]
            if "extensions" in ov_pp:
                merged_pp["extensions"] = ov_pp["extensions"]
            env["provider_profile"] = merged_pp
        if "environment_profile" in env_ov:
            raise ContractValidationError(
                "CONTRACT_CORE_OVERRIDE",
                "environment_profile cannot be changed by provider attenuation",
            )
        result["environment"] = env

    # Recompute digest for attenuated contract; keep identity fields.
    result.pop("integrity", None)
    return attach_digest(result)
