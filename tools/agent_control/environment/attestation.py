"""Offline/recorded environment attestation fixtures (#4255)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.agent_control.errors import DispatchError

REQUIRED_ATTESTATION_KEYS = (
    "profile_id",
    "profile_version",
    "profile_digest",
    "source_commit",
    "provider_id",
    "provider_config_ref",
    "provider_config_digest",
    "setup_status",
    "base_identity_status",
    "fallback_detected",
    "observed_tool_versions",
    "enforcement",
)


def load_attestation(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchError(
            "ENVIRONMENT_ATTESTATION_INVALID",
            f"failed to load attestation fixture: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise DispatchError(
            "ENVIRONMENT_ATTESTATION_INVALID",
            "attestation must be an object",
        )
    for key in REQUIRED_ATTESTATION_KEYS:
        if key not in payload:
            raise DispatchError(
                "ENVIRONMENT_ATTESTATION_INVALID",
                f"attestation missing required field: {key}",
            )
    # Never accept secret-bearing fixtures.
    blob = json.dumps(payload)
    for needle in ("CURSOR_API_KEY", "Bearer ", "x-api-key", "presigned"):
        if needle.lower() in blob.lower():
            raise DispatchError(
                "ENVIRONMENT_SECRET_SCOPE_VIOLATION",
                f"attestation contains forbidden secret-like material ({needle})",
            )
    return payload
