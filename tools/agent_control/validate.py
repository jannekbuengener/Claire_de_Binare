"""Schema + semantic validation for cdb.agent_registry.v1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.agent_control.errors import RegistryError
from tools.agent_control.load import load_registry_document
from tools.agent_control.paths import SCHEMA_PATH
from tools.agent_execution_contract.attenuation import PERMISSION_KEYS

_SECRET_VALUE_HINT = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|bearer)\b\s*[:=]\s*\S+"
)


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _schema_validate(document: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda err: list(err.path))
    if not errors:
        return
    first = errors[0]
    path = ".".join(str(part) for part in first.path) or "<root>"
    msg = first.message
    code = "REGISTRY_SCHEMA_INVALID"
    if "Additional properties are not allowed" in msg:
        code = "REGISTRY_UNKNOWN_FIELD"
    raise RegistryError(code, f"{path}: {msg}")


def _reject_plaintext_secrets(node: Any, *, path: str = "$") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            key_l = str(key).lower()
            if key_l in {"api_key", "secret", "token", "password", "bearer"}:
                if isinstance(value, str) and value and not value.startswith(
                    ("env:", "secret:")
                ):
                    raise RegistryError(
                        "REGISTRY_PLAINTEXT_SECRET",
                        f"plaintext secret-like field rejected at {path}.{key}",
                    )
            _reject_plaintext_secrets(value, path=f"{path}.{key}")
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            _reject_plaintext_secrets(value, path=f"{path}[{idx}]")
    elif isinstance(node, str):
        if _SECRET_VALUE_HINT.search(node):
            raise RegistryError(
                "REGISTRY_PLAINTEXT_SECRET",
                f"plaintext secret-like value rejected at {path}",
            )


def _detect_cycles(agents: list[dict[str, Any]]) -> None:
    graph: dict[str, list[str]] = {}
    for agent in agents:
        agent_id = agent["agent_id"]
        deps = list(agent.get("depends_on") or [])
        if agent_id in deps:
            raise RegistryError(
                "REGISTRY_SELF_DEPENDENCY",
                f"agent {agent_id!r} depends on itself",
            )
        graph[agent_id] = deps

    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = " -> ".join(stack + [node])
            raise RegistryError(
                "REGISTRY_CYCLIC_DEPENDENCY",
                f"cyclic dependency detected: {cycle}",
            )
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                raise RegistryError(
                    "REGISTRY_UNKNOWN_DEPENDENCY",
                    f"agent {node!r} depends_on unknown agent {dep!r}",
                )
            dfs(dep, stack + [node])
        visiting.remove(node)
        visited.add(node)

    for agent_id in sorted(graph):
        dfs(agent_id, [])


def _effective_permissions(
    ceiling: dict[str, bool], overrides: dict[str, Any] | None
) -> dict[str, bool]:
    effective = dict(ceiling)
    if not overrides:
        return effective
    for key, value in overrides.items():
        if key not in PERMISSION_KEYS:
            raise RegistryError(
                "REGISTRY_UNKNOWN_FIELD",
                f"permission_overrides unknown field: {key}",
            )
        if not isinstance(value, bool):
            raise RegistryError(
                "REGISTRY_PERMISSION_INVALID",
                f"permission_overrides.{key} must be boolean",
            )
        if value and not ceiling.get(key, False):
            raise RegistryError(
                "REGISTRY_PERMISSION_ESCALATION",
                f"registry attempted to expand contract permission {key!r}",
            )
        effective[key] = ceiling[key] and value
    return effective


def _semantic_validate(document: dict[str, Any]) -> None:
    if document.get("schema_id") != "cdb.agent_registry.v1":
        raise RegistryError(
            "REGISTRY_SCHEMA_VERSION",
            "schema_id must be cdb.agent_registry.v1",
        )
    if document.get("schema_version") != "1.0.0":
        raise RegistryError(
            "REGISTRY_SCHEMA_VERSION",
            "schema_version must be 1.0.0",
        )

    profiles = document["profiles"]
    agents = document["agents"]
    if not isinstance(agents, list) or not agents:
        raise RegistryError("REGISTRY_AGENTS_EMPTY", "agents must be a non-empty array")

    seen_ids: set[str] = set()
    for idx, agent in enumerate(agents):
        if not isinstance(agent, dict):
            raise RegistryError(
                "REGISTRY_AGENT_TYPE_INVALID",
                f"agents[{idx}] must be an object",
            )
        agent_id = agent.get("agent_id")
        if not isinstance(agent_id, str):
            raise RegistryError(
                "REGISTRY_AGENT_ID_INVALID",
                f"agents[{idx}].agent_id must be a string",
            )
        if agent_id in seen_ids:
            raise RegistryError(
                "REGISTRY_DUPLICATE_AGENT_ID",
                f"duplicate agent_id: {agent_id}",
            )
        seen_ids.add(agent_id)

        ec_ref = agent["execution_contract_profile"]
        if ec_ref not in profiles["execution_contracts"]:
            raise RegistryError(
                "REGISTRY_UNKNOWN_EXECUTION_CONTRACT_PROFILE",
                f"agent {agent_id!r}: unknown execution_contract_profile {ec_ref!r}",
            )
        provider_ref = agent["provider_profile"]
        if provider_ref not in profiles["providers"]:
            raise RegistryError(
                "REGISTRY_UNKNOWN_PROVIDER_PROFILE",
                f"agent {agent_id!r}: unknown provider_profile {provider_ref!r}",
            )
        env_ref = agent["environment_profile"]
        if env_ref not in profiles["environments"]:
            raise RegistryError(
                "REGISTRY_UNKNOWN_ENVIRONMENT_PROFILE",
                f"agent {agent_id!r}: unknown environment_profile {env_ref!r}",
            )
        for skill_ref in agent.get("skills") or []:
            if skill_ref not in profiles["skills"]:
                raise RegistryError(
                    "REGISTRY_UNKNOWN_SKILL_PROFILE",
                    f"agent {agent_id!r}: unknown skill profile {skill_ref!r}",
                )
        for mcp_ref in agent.get("mcp_profiles") or []:
            if mcp_ref not in profiles["mcp"]:
                raise RegistryError(
                    "REGISTRY_UNKNOWN_MCP_PROFILE",
                    f"agent {agent_id!r}: unknown mcp profile {mcp_ref!r}",
                )

        ceiling = profiles["execution_contracts"][ec_ref]["permissions"]
        if not isinstance(ceiling, dict):
            raise RegistryError(
                "REGISTRY_PERMISSION_INVALID",
                f"execution_contract_profile {ec_ref!r} permissions must be object",
            )
        for key in PERMISSION_KEYS:
            if key not in ceiling:
                raise RegistryError(
                    "REGISTRY_PERMISSION_MISSING",
                    f"execution_contract_profile {ec_ref!r} missing permission {key!r}",
                )
            if not isinstance(ceiling[key], bool):
                raise RegistryError(
                    "REGISTRY_PERMISSION_INVALID",
                    f"execution_contract_profile {ec_ref!r}.{key} must be boolean",
                )
        # Delivery-safe ceilings: merge / publish / mutations must remain false
        # unless a future governance profile explicitly widens (not this slice).
        for forbidden in (
            "merge",
            "publish_cdb_local_ci",
            "runtime_mutation",
            "database_mutation",
            "mcp_live_mutation",
        ):
            if ceiling.get(forbidden) is True:
                raise RegistryError(
                    "REGISTRY_PERMISSION_ESCALATION",
                    f"execution_contract_profile {ec_ref!r} sets {forbidden}=true "
                    "(registry cannot expand contract authority)",
                )

        _effective_permissions(ceiling, agent.get("permission_overrides"))

        mcp_refs = agent.get("mcp_profiles") or []
        for mcp_ref in mcp_refs:
            mcp_profile = profiles["mcp"][mcp_ref]
            if mcp_profile.get("mutation_allowed") is True:
                raise RegistryError(
                    "REGISTRY_PERMISSION_ESCALATION",
                    f"mcp profile {mcp_ref!r} sets mutation_allowed=true",
                )

    _detect_cycles(agents)
    _reject_plaintext_secrets(document)


def validate_registry(document: dict[str, Any]) -> dict[str, Any]:
    """Validate registry document; returns the same object on success."""
    if not isinstance(document, dict):
        raise RegistryError("REGISTRY_TYPE_INVALID", "registry root must be an object")
    schema = load_schema()
    _schema_validate(document, schema)
    _semantic_validate(document)
    return document


def validate_registry_path(config: Path) -> dict[str, Any]:
    document = load_registry_document(config)
    return validate_registry(document)
