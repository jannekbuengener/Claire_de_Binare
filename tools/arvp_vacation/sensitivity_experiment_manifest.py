"""Versioned replay-only sensitivity experiment manifest (#4153).

Defines schema load, fail-closed validation, and deterministic fingerprinting.
Does not execute campaigns or authorize paper/live/echtgeld.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash
from core.replay.dataset_identity import collect_forbidden_evidence_keys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"
MANIFEST_SCHEMA_PATH = (
    CONTRACTS_DIR / "cdb_sensitivity_experiment_manifest.v1.schema.json"
)
MANIFEST_SCHEMA_VERSION = "cdb.sensitivity_experiment_manifest.v1"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore


class SensitivityManifestError(ValueError):
    """Fail-closed sensitivity experiment manifest violation."""


def load_manifest_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or MANIFEST_SCHEMA_PATH
    if not schema_path.exists():
        raise SensitivityManifestError(f"Manifest schema missing: {schema_path}")
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SensitivityManifestError("Manifest schema root must be object")
    return payload


def _body_for_fingerprint(manifest: Mapping[str, Any]) -> dict[str, Any]:
    body = deepcopy(dict(manifest))
    body.pop("manifest_fingerprint", None)
    return body


def fingerprint_manifest(manifest: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over the manifest body (excluding fingerprint)."""
    return canonical_hash(_body_for_fingerprint(manifest))


def validate_manifest_schema(
    manifest: Mapping[str, Any],
    *,
    schema: Mapping[str, Any] | None = None,
) -> None:
    """Validate against JSON Schema; fail closed on missing jsonschema or errors."""
    if jsonschema is None:
        raise SensitivityManifestError(
            "jsonschema is required to validate sensitivity experiment manifests"
        )
    resolved = schema or load_manifest_schema()
    try:
        jsonschema.validate(instance=dict(manifest), schema=dict(resolved))
    except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
        raise SensitivityManifestError(
            f"INVALID_EXPERIMENT_MANIFEST: {exc.message}"
        ) from exc


def assert_manifest_secret_safe(manifest: Mapping[str, Any]) -> None:
    bad = collect_forbidden_evidence_keys(manifest)
    if bad:
        raise SensitivityManifestError(
            "manifest must not include secret/path/DSN fields: " + ", ".join(bad)
        )


def load_manifest(path: Path | str) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        raise SensitivityManifestError(f"Manifest missing: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SensitivityManifestError("Manifest root must be object")
    return payload


def attach_fingerprint(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with embedded ``manifest_fingerprint``."""
    out = deepcopy(dict(manifest))
    out["manifest_fingerprint"] = fingerprint_manifest(out)
    return out
