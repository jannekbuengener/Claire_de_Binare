"""Versioned replay-only sensitivity experiment manifest (#4153).

Defines schema load, fail-closed validation, fingerprinting, and schema
dispatch for v1 (non-executable) and v1.1 (executable, ratification-bound).
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
MANIFEST_SCHEMA_V11_PATH = (
    CONTRACTS_DIR / "cdb_sensitivity_experiment_manifest.v1.1.schema.json"
)
MANIFEST_SCHEMA_VERSION = "cdb.sensitivity_experiment_manifest.v1"
MANIFEST_SCHEMA_VERSION_V11 = "cdb.sensitivity_experiment_manifest.v1.1"
CANONICAL_EXECUTABLE_MANIFEST_REL = Path(
    "config/arvp/sensitivity_campaign_4153_v1.json"
)

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


def resolve_manifest_schema_path(manifest: Mapping[str, Any]) -> Path:
    version = manifest.get("schema_version")
    if version == MANIFEST_SCHEMA_VERSION_V11:
        return MANIFEST_SCHEMA_V11_PATH
    if version == MANIFEST_SCHEMA_VERSION:
        return MANIFEST_SCHEMA_PATH
    raise SensitivityManifestError(f"UNSUPPORTED_MANIFEST_SCHEMA_VERSION: {version!r}")


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
    if schema is None:
        resolved = load_manifest_schema(resolve_manifest_schema_path(manifest))
    else:
        resolved = dict(schema)
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


def assert_executable_consistency(manifest: Mapping[str, Any]) -> None:
    """Enforce executable ↔ ban pairing and safety bans."""
    executable = manifest.get("executable")
    bans = manifest.get("explicit_bans") or {}
    if manifest.get("lr_status") != "NO-GO":
        raise SensitivityManifestError("lr_status must be NO-GO")

    version = manifest.get("schema_version")
    if version == MANIFEST_SCHEMA_VERSION:
        if executable is not False:
            raise SensitivityManifestError("v1 manifests must set executable=false")
        if bans.get("campaign_execution") is not True:
            raise SensitivityManifestError(
                "v1 manifests require explicit_bans.campaign_execution=true"
            )
        for safety_field in ("promotion", "paper", "live", "echtgeld"):
            if bans.get(safety_field) is not True:
                raise SensitivityManifestError(
                    f"explicit_bans.{safety_field} must be true"
                )
        return

    if version == MANIFEST_SCHEMA_VERSION_V11:
        if executable is not True:
            raise SensitivityManifestError("v1.1 manifests must set executable=true")
        if manifest.get("execution_mode") != "replay_only":
            raise SensitivityManifestError("execution_mode must be replay_only")
        required_true = (
            "promotion",
            "paper",
            "live",
            "echtgeld",
            "orders",
            "exchange_execution",
            "testnet_orders",
            "balance_usage",
            "position_mutation",
            "risk_limit_mutation",
            "kill_switch_mutation",
            "stop_loss_mutation",
            "stage_b",
            "oos",
            "stress",
            "holdout",
            "campaign_execution_auto_start",
        )
        for safety_field in required_true:
            if bans.get(safety_field) is not True:
                raise SensitivityManifestError(
                    f"explicit_bans.{safety_field} must be true"
                )
        # Legacy alias if present must remain banned (no auto campaign).
        if "campaign_execution" in bans and bans.get("campaign_execution") is not True:
            raise SensitivityManifestError(
                "explicit_bans.campaign_execution alias must stay true "
                "(auto-start banned; separate Owner Campaign-GO required)"
            )
        return

    raise SensitivityManifestError(f"unsupported schema_version: {version!r}")


def validate_manifest(
    manifest: Mapping[str, Any],
    *,
    schema: Mapping[str, Any] | None = None,
) -> None:
    """Full validation: schema + secret-safe + executable consistency."""
    validate_manifest_schema(manifest, schema=schema)
    assert_manifest_secret_safe(manifest)
    assert_executable_consistency(manifest)
    if manifest.get("schema_version") == MANIFEST_SCHEMA_VERSION_V11:
        from tools.arvp_vacation.sensitivity_campaign_grid import (
            SensitivityGridError,
            assert_manifest_matches_ratified_grid,
        )

        try:
            assert_manifest_matches_ratified_grid(manifest)
        except SensitivityGridError as exc:
            raise SensitivityManifestError(str(exc)) from exc


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
