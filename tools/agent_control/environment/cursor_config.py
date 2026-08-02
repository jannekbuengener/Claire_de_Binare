"""Validate Cursor .cursor/environment.json against official schema (#4255)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator

from tools.agent_control.environment.codes import (
    REASON_CONFIG_MISSING,
    REASON_CONFIG_SCHEMA_INVALID,
    REASON_PATH_ESCAPE,
)
from tools.agent_control.environment.digest import (
    config_digest,
    load_json,
    resolve_repo_relative,
)
from tools.agent_control.errors import DispatchError
from tools.agent_control.paths import REPO_ROOT

CURSOR_SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "cursor_environment.schema.json"
DEFAULT_CONFIG_REL = Path(".cursor") / "environment.json"


def load_cursor_schema() -> dict[str, Any]:
    with CURSOR_SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_cursor_environment_config(
    repo_root: Path,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Validate official Cursor environment config; return payload + digests/paths."""
    root = repo_root.resolve()
    path = (config_path or (root / DEFAULT_CONFIG_REL)).resolve()
    if not path.is_file():
        raise DispatchError(
            REASON_CONFIG_MISSING,
            f"missing provider environment config: {path}",
        )
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            f"invalid environment.json: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            "environment.json must be an object",
        )

    # Reject CDB-invented fields / secrets.
    forbidden_keys = {
        "allowed_paths",
        "live_dispatch_allowed",
        "secret_policy",
        "cdb_profile_id",
        "CURSOR_API_KEY",
        "api_key",
    }
    for key in payload:
        if key in forbidden_keys:
            raise DispatchError(
                REASON_CONFIG_SCHEMA_INVALID,
                f"CDB/secret field forbidden in Cursor environment.json: {key}",
            )

    schema = load_cursor_schema()
    validator = Draft201909Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        raise DispatchError(
            REASON_CONFIG_SCHEMA_INVALID,
            f"cursor environment schema: {first.message}",
        )

    base_dir = path.parent
    build = payload.get("build") or {}
    dockerfile = build.get("dockerfile")
    context = build.get("context", ".")
    resolved: dict[str, str] = {}
    if isinstance(dockerfile, str):
        df = resolve_repo_relative(root, base_dir, dockerfile, code=REASON_PATH_ESCAPE)
        resolved["dockerfile"] = str(df.relative_to(root)).replace("\\", "/")
        if not df.is_file():
            raise DispatchError(
                REASON_CONFIG_SCHEMA_INVALID,
                f"dockerfile not found: {dockerfile}",
            )
    if isinstance(context, str):
        ctx = resolve_repo_relative(root, base_dir, context, code=REASON_PATH_ESCAPE)
        if not ctx.is_dir():
            raise DispatchError(
                REASON_CONFIG_SCHEMA_INVALID,
                f"build context not found: {context}",
            )
        resolved["context"] = str(ctx.relative_to(root)).replace("\\", "/")

    # Opaque snapshot alone is never trusted as base identity.
    snapshot = payload.get("snapshot")
    agent_can_update = payload.get("agentCanUpdateSnapshot")
    return {
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "payload": payload,
        "digest": config_digest(payload),
        "resolved_paths": resolved,
        "snapshot_id": snapshot if isinstance(snapshot, str) else None,
        "agent_can_update_snapshot": agent_can_update,
        "base_identity_from_config": "unknown",
    }
