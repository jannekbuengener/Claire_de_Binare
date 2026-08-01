"""Deterministic normalization of validated registry documents."""

from __future__ import annotations

import hashlib
from typing import Any

from tools.agent_execution_contract.attenuation import PERMISSION_KEYS
from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_control.validate import validate_registry


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted(set(values))


def normalize_agent(agent: dict[str, Any], profiles: dict[str, Any]) -> dict[str, Any]:
    ceiling = dict(
        profiles["execution_contracts"][agent["execution_contract_profile"]][
            "permissions"
        ]
    )
    overrides = agent.get("permission_overrides") or {}
    effective = {key: bool(ceiling[key]) for key in PERMISSION_KEYS}
    for key, value in overrides.items():
        effective[key] = effective[key] and bool(value)

    labels = agent.get("labels_or_routing_selectors") or {}
    normalized_labels = {str(key): labels[key] for key in sorted(labels)}
    return {
        "agent_id": agent["agent_id"],
        "version": agent["version"],
        "enabled": bool(agent["enabled"]),
        "description": agent["description"],
        "execution_contract_profile": agent["execution_contract_profile"],
        "provider_profile": agent["provider_profile"],
        "environment_profile": agent["environment_profile"],
        "skills": _sorted_unique(list(agent.get("skills") or [])),
        "mcp_profiles": _sorted_unique(list(agent.get("mcp_profiles") or [])),
        "subagents": _sorted_unique(list(agent.get("subagents") or [])),
        "labels_or_routing_selectors": normalized_labels,
        "depends_on": _sorted_unique(list(agent.get("depends_on") or [])),
        "effective_permissions": {key: effective[key] for key in PERMISSION_KEYS},
    }


def normalize_registry(document: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministically ordered registry snapshot."""
    validated = validate_registry(document)
    profiles = validated["profiles"]
    agents = [
        normalize_agent(agent, profiles)
        for agent in sorted(validated["agents"], key=lambda item: item["agent_id"])
    ]
    normalized_profiles: dict[str, Any] = {}
    for kind in (
        "execution_contracts",
        "providers",
        "environments",
        "skills",
        "mcp",
    ):
        bucket = profiles[kind]
        normalized_profiles[kind] = {
            profile_id: bucket[profile_id] for profile_id in sorted(bucket)
        }
    return {
        "schema_id": "cdb.agent_registry.v1",
        "schema_version": "1.0.0",
        "profiles": normalized_profiles,
        "agents": agents,
    }


def registry_fingerprint(document: dict[str, Any]) -> str:
    normalized = normalize_registry(document)
    # Reuse RFC8785 JCS from execution-contract tooling for byte-stable digests.
    canonical = canonicalize(normalized)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def agent_desired_fingerprint(agent: dict[str, Any]) -> str:
    canonical = canonicalize(agent)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
