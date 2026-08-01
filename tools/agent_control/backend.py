"""Observed-state backends for the registry reconciler.

Live provider mutation is intentionally unsupported in #4252.
"""

from __future__ import annotations

import copy
from typing import Any, Protocol

from tools.agent_control.errors import RegistryError


class RegistryBackend(Protocol):
    name: str

    def observe(self) -> dict[str, Any]:
        """Return observed agent state document."""

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Apply a plan. Mock-only in this slice."""


def normalize_observed_state(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize observed state into agent_id -> record map."""
    if not isinstance(state, dict):
        raise RegistryError(
            "REGISTRY_STATE_TYPE_INVALID",
            "observed state root must be an object",
        )
    schema_id = state.get("schema_id")
    if schema_id not in {
        "cdb.agent_registry.observed.v1",
        "cdb.agent_registry.observed",
        None,
    }:
        # Accept missing schema_id for fixture simplicity, but reject foreign ids.
        if schema_id is not None:
            raise RegistryError(
                "REGISTRY_STATE_SCHEMA_INVALID",
                f"unsupported observed state schema_id: {schema_id!r}",
            )

    agents_raw = state.get("agents")
    if agents_raw is None:
        raise RegistryError(
            "REGISTRY_STATE_AGENTS_MISSING",
            "observed state missing agents",
        )

    records: dict[str, dict[str, Any]] = {}
    if isinstance(agents_raw, dict):
        iterable = agents_raw.values()
    elif isinstance(agents_raw, list):
        iterable = agents_raw
    else:
        raise RegistryError(
            "REGISTRY_STATE_AGENTS_INVALID",
            "observed state agents must be object or array",
        )

    for item in iterable:
        if not isinstance(item, dict):
            raise RegistryError(
                "REGISTRY_STATE_AGENT_INVALID",
                "observed agent record must be an object",
            )
        agent_id = item.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            raise RegistryError(
                "REGISTRY_STATE_AGENT_ID_INVALID",
                "observed agent_id must be a non-empty string",
            )
        if agent_id in records:
            raise RegistryError(
                "REGISTRY_STATE_DUPLICATE_AGENT_ID",
                f"duplicate observed agent_id: {agent_id}",
            )
        if "fingerprint" not in item and "enabled" not in item:
            raise RegistryError(
                "REGISTRY_STATE_INCOMPLETE",
                f"observed agent {agent_id!r} missing fingerprint/enabled",
            )
        records[agent_id] = {
            "agent_id": agent_id,
            "version": item.get("version"),
            "enabled": bool(item.get("enabled", True)),
            "fingerprint": item.get("fingerprint"),
            "provider_ref": item.get("provider_ref"),
        }
    return {key: records[key] for key in sorted(records)}


class FileStateBackend:
    """Read-only backend backed by a static observed-state document."""

    name = "file"

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = copy.deepcopy(state)
        # Validate early for fail-closed planning.
        normalize_observed_state(self._state)

    def observe(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        raise RegistryError(
            "REGISTRY_APPLY_BLOCKED",
            "FileStateBackend is read-only; use MockBackend for simulated apply",
        )


class MockBackend:
    """In-memory mock backend for tests. Never talks to a live provider."""

    name = "mock"

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self._state = copy.deepcopy(state) if state is not None else {
            "schema_id": "cdb.agent_registry.observed.v1",
            "agents": {},
        }
        normalize_observed_state(self._state)
        self.mutations: list[dict[str, Any]] = []

    def observe(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def apply(self, plan: dict[str, Any]) -> dict[str, Any]:
        if plan.get("blocked"):
            raise RegistryError(
                "REGISTRY_APPLY_BLOCKED",
                "refusing to apply a blocked plan",
            )
        if plan.get("mode") != "apply":
            raise RegistryError(
                "REGISTRY_APPLY_MODE_INVALID",
                "MockBackend.apply requires plan.mode=apply",
            )
        agents = normalize_observed_state(self._state)
        for op in plan.get("operations") or []:
            op_name = op["op"]
            agent_id = op["agent_id"]
            if op_name in {"noop", "block"}:
                continue
            if op_name == "create":
                desired = op["desired"]
                agents[agent_id] = {
                    "agent_id": agent_id,
                    "version": desired["version"],
                    "enabled": True,
                    "fingerprint": desired["fingerprint"],
                    "provider_ref": desired["provider_profile"],
                }
            elif op_name == "update":
                desired = op["desired"]
                agents[agent_id] = {
                    "agent_id": agent_id,
                    "version": desired["version"],
                    "enabled": True,
                    "fingerprint": desired["fingerprint"],
                    "provider_ref": desired["provider_profile"],
                }
            elif op_name == "disable":
                if agent_id in agents:
                    agents[agent_id]["enabled"] = False
            else:
                raise RegistryError(
                    "REGISTRY_UNKNOWN_OP",
                    f"unknown plan op: {op_name}",
                )
            self.mutations.append(copy.deepcopy(op))
        self._state = {
            "schema_id": "cdb.agent_registry.observed.v1",
            "agents": {key: agents[key] for key in sorted(agents)},
        }
        return {
            "applied": True,
            "backend": self.name,
            "mutation_count": len(self.mutations),
            "state": copy.deepcopy(self._state),
        }
