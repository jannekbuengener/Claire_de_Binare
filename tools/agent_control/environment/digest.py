"""Digest + path helpers for environment profiles (#4255)."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.agent_control.environment.codes import REASON_PATH_ESCAPE
from tools.agent_control.errors import DispatchError
from tools.agent_execution_contract.jcs import canonicalize


def profile_digest(profile: dict[str, Any]) -> str:
    """Deterministic sha256 digest over JCS of the profile snapshot."""
    material = canonicalize(deepcopy(profile)).encode("utf-8")
    return "sha256:" + hashlib.sha256(material).hexdigest()


def config_digest(config: dict[str, Any]) -> str:
    material = canonicalize(deepcopy(config)).encode("utf-8")
    return "sha256:" + hashlib.sha256(material).hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_repo_relative(
    repo_root: Path,
    base_dir: Path,
    relative: str,
    *,
    code: str = REASON_PATH_ESCAPE,
) -> Path:
    """Resolve a relative path and require it stays inside repo_root."""
    candidate = (base_dir / relative).resolve()
    root = repo_root.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DispatchError(
            code,
            f"path escapes repository: {relative!r} -> {candidate}",
        ) from exc
    return candidate


def redact_mapping(node: Any) -> Any:
    """Drop secret-like values for deterministic JSON output."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            key_l = str(key).lower()
            if key_l in {
                "api_key",
                "authorization",
                "cookie",
                "password",
                "secret",
                "token",
                "x-api-key",
            }:
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_mapping(value)
        return out
    if isinstance(node, list):
        return [redact_mapping(item) for item in node]
    if isinstance(node, str):
        lower = node.lower()
        if "presigned" in lower or "x-amz-signature" in lower:
            return "[REDACTED_URL]"
    return node
