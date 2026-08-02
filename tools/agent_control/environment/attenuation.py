"""Contract ∩ environment profile constraint attenuation (#4255)."""

from __future__ import annotations

from typing import Any

from tools.agent_control.environment.codes import (
    REASON_ATTENUATION_EMPTY,
    REASON_SECRET_SCOPE_VIOLATION,
)
from tools.agent_control.errors import DispatchError


def _intersect_lists(left: list[str], right: list[str]) -> list[str]:
    right_set = set(right)
    return [item for item in left if item in right_set]


def attenuate_constraints(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Return effective constraints = Contract ∩ Profile (fail-closed)."""
    scope = contract.get("execution_scope") or {}
    budget = contract.get("budget") or {}
    env = contract.get("environment") or {}

    contract_paths = list(scope.get("allowed_paths") or [])
    profile_paths = list(profile.get("allowed_paths") or [])
    # When profile is mock/local_repo with empty paths, do not invent rights:
    # intersection with empty profile paths for cloud profiles is required.
    if profile.get("runtime_class") == "cloud_agent":
        effective_paths = _intersect_lists(contract_paths, profile_paths)
        if not effective_paths and (contract_paths or profile_paths):
            raise DispatchError(
                REASON_ATTENUATION_EMPTY,
                "effective allowed_paths intersection is empty",
            )
    else:
        effective_paths = contract_paths

    contract_cmds = list(scope.get("allowed_commands_or_command_classes") or [])
    profile_cmds = list(profile.get("allowed_command_classes") or [])
    if profile.get("runtime_class") == "cloud_agent":
        effective_cmds = _intersect_lists(contract_cmds, profile_cmds)
        if not effective_cmds and (contract_cmds or profile_cmds):
            # runtime-risk-restricted intentionally has empty command classes
            if profile_cmds or contract_cmds:
                if profile.get("workspace_policy", {}).get("mode") == "blocked":
                    effective_cmds = []
                elif not effective_cmds:
                    raise DispatchError(
                        REASON_ATTENUATION_EMPTY,
                        "effective command_classes intersection is empty",
                    )
    else:
        effective_cmds = contract_cmds

    contract_net = budget.get("network_policy") or {}
    profile_net = profile.get("network_policy") or {}
    if profile_net.get("mode") == "deny_all":
        effective_net = {
            "mode": "deny_all",
            "allowed_classes": [],
            "allowed_domains": [],
        }
    elif profile.get("runtime_class") == "cloud_agent":
        c_classes = list(contract_net.get("allowed_classes") or [])
        p_classes = list(profile_net.get("allowed_classes") or [])
        c_domains = list(contract_net.get("allowed_domains") or [])
        p_domains = list(profile_net.get("allowed_domains") or [])
        # Profile must not expand contract; take intersection.
        if contract_net.get("mode") == "deny_all":
            effective_net = {
                "mode": "deny_all",
                "allowed_classes": [],
                "allowed_domains": [],
            }
        else:
            # Detect expansion attempt: profile domain not in contract when both allowlist
            if p_domains and c_domains:
                if any(d not in set(c_domains) for d in p_domains):
                    # Profile claiming extra domains is ignored via intersection;
                    # if contract tries to expand beyond profile, also intersect.
                    pass
            effective_net = {
                "mode": "allowlist",
                "allowed_classes": (
                    _intersect_lists(c_classes, p_classes) if p_classes else []
                ),
                "allowed_domains": (
                    _intersect_lists(c_domains, p_domains) if p_domains else []
                ),
            }
            # Contract expansion beyond profile: any contract-only class is dropped.
            if c_classes and p_classes:
                expanded = [c for c in c_classes if c not in set(p_classes)]
                if expanded and not _intersect_lists(c_classes, p_classes):
                    raise DispatchError(
                        REASON_ATTENUATION_EMPTY,
                        "network allowlist intersection is empty",
                    )
    else:
        effective_net = dict(contract_net)

    # Budgets: minimum of positive ints where both present.
    wall_c = budget.get("wall_time_seconds")
    wall_p = (profile.get("execution_limits") or {}).get("run_timeout_seconds")
    wall = None
    if isinstance(wall_c, int) and isinstance(wall_p, int):
        wall = min(wall_c, wall_p)
    elif isinstance(wall_c, int):
        wall = wall_c
    elif isinstance(wall_p, int):
        wall = wall_p

    # Secret classes: contract must be subset of profile allowlist for cloud_agent.
    contract_secrets = [
        item.get("class")
        for item in (env.get("secret_references") or [])
        if isinstance(item, dict) and item.get("class")
    ]
    profile_secret_allow = list(
        (profile.get("secret_policy") or {}).get("allowed_classes") or []
    )
    if profile.get("runtime_class") == "cloud_agent":
        for cls in contract_secrets:
            if cls not in profile_secret_allow:
                raise DispatchError(
                    REASON_SECRET_SCOPE_VIOLATION,
                    f"contract secret class {cls!r} not in profile allowlist",
                )

    cost_p = (profile.get("cost_limit") or {}).get("max_live_cost_usd")
    cost_c = budget.get("max_live_cost_usd")
    max_cost = 0
    if cost_p is not None and cost_c is not None:
        try:
            max_cost = min(float(cost_p), float(cost_c))
        except (TypeError, ValueError):
            max_cost = 0
    elif cost_p is not None:
        max_cost = float(cost_p)
    else:
        max_cost = 0.0

    return {
        "allowed_paths": effective_paths,
        "allowed_command_classes": effective_cmds,
        "network_policy": effective_net,
        "wall_time_seconds": wall,
        "max_live_cost_usd": max_cost,
        "secret_classes": list(contract_secrets),
        "forbidden_paths": list(profile.get("forbidden_paths") or [])
        + list(scope.get("forbidden_paths") or []),
    }


def detect_network_expansion(contract: dict[str, Any], profile: dict[str, Any]) -> bool:
    """True when contract egress allowlist expands beyond profile."""
    contract_net = (contract.get("budget") or {}).get("network_policy") or {}
    profile_net = profile.get("network_policy") or {}
    if profile_net.get("mode") == "deny_all" and (
        contract_net.get("allowed_domains") or contract_net.get("allowed_classes")
    ):
        if contract_net.get("mode") != "deny_all":
            return True
    p_domains = set(profile_net.get("allowed_domains") or [])
    c_domains = set(contract_net.get("allowed_domains") or [])
    if p_domains and c_domains - p_domains:
        return True
    p_classes = set(profile_net.get("allowed_classes") or [])
    c_classes = set(contract_net.get("allowed_classes") or [])
    if p_classes and c_classes - p_classes:
        return True
    return False
