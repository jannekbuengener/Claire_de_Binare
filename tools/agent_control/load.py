"""Load declarative agent registry documents from file or config root."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from tools.agent_control.errors import RegistryError

PROFILE_DIRS = (
    "execution_contracts",
    "providers",
    "environments",
    "skills",
    "mcp",
)


def _read_structured(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_load(text)
        if suffix == ".json":
            return json.loads(text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise RegistryError(
            "REGISTRY_PARSE_ERROR",
            f"failed to parse {path}: {exc}",
        ) from exc
    raise RegistryError(
        "REGISTRY_UNSUPPORTED_FORMAT",
        f"unsupported registry file format: {path}",
    )


def _strip_profile_extension(name: str) -> str:
    for ext in (".yaml", ".yml", ".json"):
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


def _load_profile_catalog(profiles_root: Path) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {key: {} for key in PROFILE_DIRS}
    for kind in PROFILE_DIRS:
        directory = profiles_root / kind
        if not directory.is_dir():
            raise RegistryError(
                "REGISTRY_PROFILE_ROOT_INVALID",
                f"missing profiles directory: {directory}",
            )
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            if path.name.startswith("."):
                continue
            profile_id = _strip_profile_extension(path.name)
            payload = _read_structured(path)
            if not isinstance(payload, dict):
                raise RegistryError(
                    "REGISTRY_PROFILE_INVALID",
                    f"profile {kind}/{profile_id} must be an object",
                )
            # Allow optional wrapper with profile_id for readability.
            if "profile_id" in payload:
                declared = payload.pop("profile_id")
                if declared != profile_id:
                    raise RegistryError(
                        "REGISTRY_PROFILE_ID_MISMATCH",
                        f"{kind}/{path.name}: profile_id {declared!r} != {profile_id!r}",
                    )
            catalog[kind][profile_id] = payload
        if not catalog[kind]:
            raise RegistryError(
                "REGISTRY_PROFILE_EMPTY",
                f"no profiles found under {directory}",
            )
    return catalog


def load_registry_document(config: Path) -> dict[str, Any]:
    """Load a registry document from a file or config/agent-control root."""
    config = config.resolve()
    if config.is_file():
        payload = _read_structured(config)
        if not isinstance(payload, dict):
            raise RegistryError(
                "REGISTRY_TYPE_INVALID",
                "registry root must be an object",
            )
        return payload

    if not config.is_dir():
        raise RegistryError(
            "REGISTRY_CONFIG_MISSING",
            f"config path does not exist: {config}",
        )

    agents_path = config / "agents" / "registry.v1.yaml"
    if not agents_path.is_file():
        alt = config / "agents" / "registry.v1.yml"
        if alt.is_file():
            agents_path = alt
        else:
            raise RegistryError(
                "REGISTRY_AGENTS_MISSING",
                f"missing agents registry file under {config / 'agents'}",
            )

    agents_doc = _read_structured(agents_path)
    if not isinstance(agents_doc, dict):
        raise RegistryError(
            "REGISTRY_TYPE_INVALID",
            "agents registry root must be an object",
        )

    profiles = _load_profile_catalog(config / "profiles")
    document: dict[str, Any] = {
        "schema_id": agents_doc.get("schema_id", "cdb.agent_registry.v1"),
        "schema_version": agents_doc.get("schema_version", "1.0.0"),
        "profiles": profiles,
        "agents": agents_doc.get("agents"),
    }
    # Preserve unknown top-level keys from agents file so schema can reject them.
    for key, value in agents_doc.items():
        if key in {"schema_id", "schema_version", "agents", "profiles"}:
            continue
        document[key] = value
    return document


def load_observed_state(path: Path) -> dict[str, Any]:
    """Load observed state document (JSON/YAML)."""
    payload = _read_structured(path.resolve())
    if not isinstance(payload, dict):
        raise RegistryError(
            "REGISTRY_STATE_TYPE_INVALID",
            "observed state root must be an object",
        )
    return payload


def dump_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
