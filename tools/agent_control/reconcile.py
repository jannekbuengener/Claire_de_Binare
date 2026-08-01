"""Deterministic registry reconcile planner (dry-run by default)."""

from __future__ import annotations

import hashlib
from typing import Any

from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_control.backend import (
    FileStateBackend,
    MockBackend,
    RegistryBackend,
    normalize_observed_state,
)
from tools.agent_control.errors import RegistryError
from tools.agent_control.normalize import (
    agent_desired_fingerprint,
    normalize_registry,
)
from tools.agent_control.validate import validate_registry


def _plan_digest(operations: list[dict[str, Any]], *, blocked: bool, reason: str | None) -> str:
    payload = {
        "blocked": blocked,
        "operations": operations,
        "reason": reason,
        "schema_id": "cdb.agent_registry.plan.v1",
    }
    digest = hashlib.sha256(canonicalize(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_plan(
    document: dict[str, Any],
    observed_state: dict[str, Any],
    *,
    mode: str = "dry-run",
) -> dict[str, Any]:
    """Build a deterministic reconcile plan.

    On invalid registry, returns a fully blocked plan (no partial ops).
    """
    if mode not in {"dry-run", "plan", "apply"}:
        raise RegistryError(
            "REGISTRY_MODE_INVALID",
            f"unsupported reconcile mode: {mode!r}",
        )

    try:
        validate_registry(document)
        desired_doc = normalize_registry(document)
        observed = normalize_observed_state(observed_state)
    except RegistryError as exc:
        operations = [
            {
                "op": "block",
                "agent_id": "*",
                "reason": f"{exc.code}: {exc.message}",
            }
        ]
        return {
            "schema_id": "cdb.agent_registry.plan.v1",
            "mode": mode,
            "blocked": True,
            "reason": f"{exc.code}: {exc.message}",
            "operations": operations,
            "plan_digest": _plan_digest(
                operations, blocked=True, reason=f"{exc.code}: {exc.message}"
            ),
            "mutation_intended": False,
        }

    operations: list[dict[str, Any]] = []
    desired_by_id = {agent["agent_id"]: agent for agent in desired_doc["agents"]}

    for agent_id in sorted(set(desired_by_id) | set(observed)):
        desired = desired_by_id.get(agent_id)
        current = observed.get(agent_id)

        if desired is None:
            # Observed but not in registry desired set → leave untouched (noop).
            # Deletion is out of scope for #4252; disable only when desired says so.
            operations.append(
                {
                    "op": "noop",
                    "agent_id": agent_id,
                    "reason": "observed_not_in_desired_registry",
                    "desired": None,
                    "observed": current,
                }
            )
            continue

        fingerprint = agent_desired_fingerprint(desired)
        desired_view = {
            "agent_id": desired["agent_id"],
            "version": desired["version"],
            "enabled": desired["enabled"],
            "provider_profile": desired["provider_profile"],
            "environment_profile": desired["environment_profile"],
            "execution_contract_profile": desired["execution_contract_profile"],
            "skills": desired["skills"],
            "mcp_profiles": desired["mcp_profiles"],
            "subagents": desired["subagents"],
            "labels_or_routing_selectors": desired["labels_or_routing_selectors"],
            "depends_on": desired["depends_on"],
            "effective_permissions": desired["effective_permissions"],
            "fingerprint": fingerprint,
        }

        if not desired["enabled"]:
            if current is None:
                operations.append(
                    {
                        "op": "noop",
                        "agent_id": agent_id,
                        "reason": "disabled_not_present",
                        "desired": desired_view,
                        "observed": None,
                    }
                )
            elif current.get("enabled") is False and current.get("fingerprint") in {
                None,
                fingerprint,
            }:
                operations.append(
                    {
                        "op": "noop",
                        "agent_id": agent_id,
                        "reason": "already_disabled",
                        "desired": desired_view,
                        "observed": current,
                    }
                )
            else:
                operations.append(
                    {
                        "op": "disable",
                        "agent_id": agent_id,
                        "reason": "desired_disabled",
                        "desired": desired_view,
                        "observed": current,
                    }
                )
            continue

        # Desired enabled
        if current is None:
            operations.append(
                {
                    "op": "create",
                    "agent_id": agent_id,
                    "reason": "missing_in_observed",
                    "desired": desired_view,
                    "observed": None,
                }
            )
            continue

        if current.get("enabled") is False:
            operations.append(
                {
                    "op": "update",
                    "agent_id": agent_id,
                    "reason": "reenable_and_sync",
                    "desired": desired_view,
                    "observed": current,
                }
            )
            continue

        if current.get("fingerprint") == fingerprint and current.get("version") == desired[
            "version"
        ]:
            operations.append(
                {
                    "op": "noop",
                    "agent_id": agent_id,
                    "reason": "already_aligned",
                    "desired": desired_view,
                    "observed": current,
                }
            )
        else:
            operations.append(
                {
                    "op": "update",
                    "agent_id": agent_id,
                    "reason": "drift_detected",
                    "desired": desired_view,
                    "observed": current,
                }
            )

    # Stable order already by sorted agent_id traversal.
    mutating = [op for op in operations if op["op"] in {"create", "update", "disable"}]
    return {
        "schema_id": "cdb.agent_registry.plan.v1",
        "mode": mode,
        "blocked": False,
        "reason": None,
        "operations": operations,
        "plan_digest": _plan_digest(operations, blocked=False, reason=None),
        "mutation_intended": bool(mutating) and mode == "apply",
        "desired_agent_count": len(desired_doc["agents"]),
        "observed_agent_count": len(observed),
        "mutating_op_count": len(mutating),
    }


def reconcile(
    document: dict[str, Any],
    backend: RegistryBackend,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Plan against backend.observe(); apply only when dry_run is False on MockBackend."""
    observed = backend.observe()
    mode = "dry-run" if dry_run else "apply"
    plan = build_plan(document, observed, mode=mode)
    result: dict[str, Any] = {
        "plan": plan,
        "backend": getattr(backend, "name", "unknown"),
        "dry_run": dry_run,
        "applied": False,
        "apply_result": None,
    }
    if dry_run:
        return result
    if plan.get("blocked"):
        raise RegistryError(
            "REGISTRY_APPLY_BLOCKED",
            plan.get("reason") or "blocked plan",
        )
    if not isinstance(backend, MockBackend):
        raise RegistryError(
            "REGISTRY_LIVE_MUTATION_FORBIDDEN",
            "live/provider apply is forbidden in #4252; use MockBackend or dry-run",
        )
    apply_result = backend.apply(plan)
    result["applied"] = True
    result["apply_result"] = apply_result
    return result


def backend_from_state(
    observed_state: dict[str, Any], *, backend_name: str = "file"
) -> RegistryBackend:
    if backend_name == "mock":
        return MockBackend(observed_state)
    if backend_name == "file":
        return FileStateBackend(observed_state)
    raise RegistryError(
        "REGISTRY_BACKEND_UNKNOWN",
        f"unknown backend: {backend_name!r}",
    )
