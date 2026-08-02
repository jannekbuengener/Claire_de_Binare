"""Deterministic PR-Router → Agent Execution Contract handoff adapter.

The PR Router remains read-only. This adapter consumes a validated router
result dict plus an explicit policy template. It never derives permissions
from untrusted issue text.
"""

from __future__ import annotations

import copy
from datetime import timezone
from typing import Any, Mapping

from core.utils.clock import utcnow
from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.hashing import attach_digest
from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_execution_contract.validate import validate_contract

HOLD_DECISIONS = frozenset({"HOLD_PR_LOCK_CONFLICT", "HOLD_NO_SAFE_ROUTE"})

SAFE_DELIVERY_PERMISSIONS: dict[str, bool] = {
    "read_repo": True,
    "write_code": False,
    "write_docs": False,
    "commit": False,
    "push": False,
    "open_pr": False,
    "update_pr": False,
    "comment_issue": False,
    "close_issue": False,
    "publish_cdb_local_ci": False,
    "merge": False,
    "runtime_mutation": False,
    "database_mutation": False,
    "mcp_live_mutation": False,
}


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            f"{label} must be a mapping",
        )
    return dict(value)


def _iso_now(created_at: str | None) -> str:
    if created_at:
        return created_at
    value = utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_contract_from_router_result(
    router_result: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    agent: str,
    created_at: str | None = None,
    contract_id: str | None = None,
) -> dict[str, Any]:
    """Build a digest-bearing contract from router output + explicit policy.

    Determinism: identical router_result + policy + agent + created_at +
    contract_id produce byte-identical canonical JSON (and digest).
    """
    route_in = _require_mapping(router_result, "router_result")
    policy_in = _require_mapping(policy, "policy")

    decision = route_in.get("routing_decision")
    if not isinstance(decision, str) or not decision:
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            "router_result.routing_decision is required",
        )
    if decision in HOLD_DECISIONS:
        raise ContractValidationError(
            "CONTRACT_HANDOFF_ROUTE_HOLD",
            f"refusing contract generation for hold decision {decision}",
        )

    issue_number = route_in.get("issue_number")
    if not isinstance(issue_number, int) or isinstance(issue_number, bool):
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            "router_result.issue_number must be an integer",
        )

    permissions = dict(SAFE_DELIVERY_PERMISSIONS)
    policy_permissions = policy_in.get("permissions")
    if policy_permissions is not None:
        if not isinstance(policy_permissions, Mapping):
            raise ContractValidationError(
                "CONTRACT_HANDOFF_INPUT_INVALID",
                "policy.permissions must be a mapping",
            )
        for key, value in policy_permissions.items():
            if key not in permissions:
                raise ContractValidationError(
                    "CONTRACT_UNKNOWN_FIELD",
                    f"policy.permissions unknown key: {key}",
                )
            if not isinstance(value, bool):
                raise ContractValidationError(
                    "CONTRACT_PERMISSION_INVALID",
                    f"policy.permissions.{key} must be boolean",
                )
            # Policy may raise above defaults, but never grant merge/publish/
            # runtime/db/mcp live mutation via this delivery handoff.
            if (
                key
                in {
                    "merge",
                    "publish_cdb_local_ci",
                    "runtime_mutation",
                    "database_mutation",
                    "mcp_live_mutation",
                    "close_issue",
                }
                and value is True
            ):
                raise ContractValidationError(
                    "CONTRACT_PERMISSION_ESCALATION",
                    f"delivery handoff policy cannot grant {key}=true",
                )
            permissions[key] = value

    execution_scope = policy_in.get("execution_scope")
    if not isinstance(execution_scope, Mapping):
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            "policy.execution_scope is required",
        )
    budget = policy_in.get("budget")
    if not isinstance(budget, Mapping):
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            "policy.budget is required",
        )
    environment = policy_in.get("environment")
    if not isinstance(environment, Mapping):
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            "policy.environment is required",
        )
    validation_and_delivery = policy_in.get("validation_and_delivery")
    if not isinstance(validation_and_delivery, Mapping):
        raise ContractValidationError(
            "CONTRACT_HANDOFF_INPUT_INVALID",
            "policy.validation_and_delivery is required",
        )

    issue_meta = dict(policy_in.get("issue") or {})
    issue_meta["number"] = issue_number

    cid = contract_id or f"aec-issue-{issue_number}"
    created = _iso_now(created_at)

    contract: dict[str, Any] = {
        "schema_id": "cdb.agent_execution.v1",
        "schema_version": "1.0.0",
        "contract_id": cid,
        "created_at": created,
        "producer": {
            "component": "pr_router_handoff",
            "agent": agent,
            "policy_id": str(route_in.get("policy_id") or "cdb-pr-routing-v1"),
        },
        "issue": issue_meta,
        "route": {
            "routing_decision": decision,
            "target_pr": route_in.get("target_pr"),
            "target_branch": route_in.get("target_branch"),
            "batch_key": route_in.get("batch_key"),
            "lane": route_in.get("lane"),
            "validation_profile": route_in.get("validation_profile"),
            "merge_mode": route_in.get("merge_mode") or "batch",
            "lock_state": route_in.get("lock_state") or "UNLOCKED",
            "policy_id": route_in.get("policy_id") or "cdb-pr-routing-v1",
            "reason_codes": list(route_in.get("reason_codes") or []),
        },
        "permissions": permissions,
        "execution_scope": copy.deepcopy(dict(execution_scope)),
        "budget": copy.deepcopy(dict(budget)),
        "environment": copy.deepcopy(dict(environment)),
        "validation_and_delivery": copy.deepcopy(dict(validation_and_delivery)),
    }
    if route_in.get("observed_at"):
        contract["route"]["router_observed_at"] = route_in["observed_at"]

    sealed = attach_digest(contract)
    validate_contract(sealed)
    return sealed


def canonical_contract_bytes(contract: Mapping[str, Any]) -> bytes:
    """Byte-stable canonical form including digest (for golden vectors)."""
    return canonicalize(dict(contract)).encode("utf-8")
