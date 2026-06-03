"""Deterministic redaction helpers for SurrealDB operator tooling (#2918-#2920)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

REDACT_PLACEHOLDER = "[REDACTED]"

SENSITIVE_KEY_RE = re.compile(
    r"(?i)(^|_)(token|secret|password|passwd|credential|api[_-]?key|auth_token|"
    r"bearer|dsn|private[_-]?key)(_|$)"
)

REDACT_TEXT_PATTERNS = (
    re.compile(r"(?i)(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)SURREAL_(?:PASS|USER)\s*=\s*\S+"),
    re.compile(r"(?i)Authorization:\s*Basic\s+[A-Za-z0-9+/=]+"),
    re.compile(r"https?://[^\s\"']+"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
)


def redact_sensitive_text(value: str) -> str:
    """Return text safe for logs/stdout with sensitive substrings masked."""
    redacted = value
    for pattern in REDACT_TEXT_PATTERNS:
        redacted = pattern.sub(REDACT_PLACEHOLDER, redacted)
    return redacted


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return bool(SENSITIVE_KEY_RE.search(normalized))


def redact_sensitive_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        if value is None:
            return None
        if isinstance(value, str) and not value:
            return ""
        return REDACT_PLACEHOLDER
    if isinstance(value, dict):
        return redact_sensitive_mapping(value)
    if isinstance(value, list):
        return [redact_sensitive_value(key, item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


def redact_sensitive_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): redact_sensitive_value(str(key), item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


def redact_sensitive_json(payload: Any) -> str:
    """Serialize payload to JSON with sensitive keys/values redacted."""
    return json.dumps(
        redact_sensitive_mapping(payload),
        ensure_ascii=True,
        sort_keys=True,
    )


def write_restricted_secret_file(path: Path, secret: str) -> None:
    """Persist an operator credential sidecar with restrictive file permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = f"{secret}\n".encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    if os.name != "nt":
        os.chmod(path, 0o600)
