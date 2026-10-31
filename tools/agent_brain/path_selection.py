"""Controlled selection between legacy Claire brain path and Agent Brain consumer.

Default is ``legacy`` (fail-safe; no live/trading cutover). Rollback is an
explicit path switch, not a silent fallback and not a git revert.
"""

from __future__ import annotations

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "agent-brain" / "consumer_cutover.v1.json"
ENV_PATH_OVERRIDE = "CDB_AGENT_BRAIN_CONSUMER_PATH"


class ConsumerPath(StrEnum):
    LEGACY = "legacy"
    AGENT_BRAIN = "agent_brain"


def load_cutover_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        return {
            "schema_version": "consumer_cutover/v1",
            "consumer_path": ConsumerPath.LEGACY.value,
            "allow_live_or_echtgeld": False,
            "notes": "missing config; default legacy",
        }
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConsumerError(
            ConsumerErrorCode.INVALID_INPUT,
            "consumer cutover config must be a JSON object",
            details={"path": str(config_path)},
        )
    return payload


def resolve_consumer_path(
    *,
    config: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    explicit: str | ConsumerPath | None = None,
) -> ConsumerPath:
    """Resolve the active consumer path.

    Precedence: explicit argument > env override > config file > legacy default.
    """
    if explicit is not None:
        return _coerce_path(explicit)

    environ = env if env is not None else os.environ
    if ENV_PATH_OVERRIDE in environ and str(environ[ENV_PATH_OVERRIDE]).strip():
        return _coerce_path(environ[ENV_PATH_OVERRIDE])

    cfg = dict(config) if config is not None else load_cutover_config()
    return _coerce_path(cfg.get("consumer_path", ConsumerPath.LEGACY.value))


def select_consumer_path(
    *,
    desired: str | ConsumerPath,
    config: Mapping[str, Any] | None = None,
) -> ConsumerPath:
    """Explicit, testable switch used for cutover and rollback probes."""
    path = _coerce_path(desired)
    cfg = dict(config) if config is not None else load_cutover_config()
    if path is ConsumerPath.AGENT_BRAIN and cfg.get("allow_live_or_echtgeld") is True:
        # Hard safety: this cutover must never authorize live/echtgeld.
        raise ConsumerError(
            ConsumerErrorCode.POLICY_BLOCKED,
            "agent-brain consumer path must not enable live/echtgeld cutover",
            details={"allow_live_or_echtgeld": True},
        )
    return path


def _coerce_path(value: str | ConsumerPath) -> ConsumerPath:
    text = (
        value.value if isinstance(value, ConsumerPath) else str(value).strip().lower()
    )
    try:
        return ConsumerPath(text)
    except ValueError as exc:
        raise ConsumerError(
            ConsumerErrorCode.UNSUPPORTED_PATH,
            f"unknown consumer path: {text!r}",
            details={"allowed": [item.value for item in ConsumerPath]},
        ) from exc


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "ENV_PATH_OVERRIDE",
    "ConsumerPath",
    "load_cutover_config",
    "resolve_consumer_path",
    "select_consumer_path",
]
