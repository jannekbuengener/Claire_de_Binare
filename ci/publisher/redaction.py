"""Redact secrets and token-like values from publisher output."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(
    r"(?i)\b("
    r"gh[pousr]_[A-Za-z0-9_]{8,}"
    r"|github_pat_[A-Za-z0-9_]{8,}"
    r"|gho_[A-Za-z0-9_]{8,}"
    r"|ghu_[A-Za-z0-9_]{8,}"
    r"|ghs_[A-Za-z0-9_]{8,}"
    r"|ghr_[A-Za-z0-9_]{8,}"
    r"|Bearer\s+\S+"
    r")\b"
)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"
)
_AUTH_HEADER_RE = re.compile(
    r"(?i)(authorization\s*[:=]\s*)(['\"]?)(Bearer\s+\S+|[^'\"\s,;]+)(['\"]?)"
)
_QUERY_TOKEN_RE = re.compile(r"(?i)([?&](?:access_token|token|auth)=)([^&\s]+)")


def redact_text(value: str) -> str:
    """Redact token-like substrings and Authorization headers from text."""
    if not value:
        return value
    redacted = _AUTH_HEADER_RE.sub(r"\1\2[REDACTED]\4", value)
    redacted = _QUERY_TOKEN_RE.sub(r"\1[REDACTED]", redacted)
    redacted = _PRIVATE_KEY_RE.sub("[REDACTED_PRIVATE_KEY]", redacted)
    redacted = _TOKEN_RE.sub("[REDACTED]", redacted)
    redacted = _JWT_RE.sub("[REDACTED_JWT]", redacted)
    return redacted


def redact_mapping(payload: Any) -> Any:
    """Deep-copy-ish redaction for dict/list structures used in diagnostics."""
    if isinstance(payload, dict):
        out: dict[Any, Any] = {}
        for key, value in payload.items():
            key_str = str(key).lower()
            if key_str in {
                "authorization",
                "token",
                "access_token",
                "password",
                "secret",
                "private_key",
                "privatekey",
                "jwt",
                "app_jwt",
            }:
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_mapping(value)
        return out
    if isinstance(payload, list):
        return [redact_mapping(item) for item in payload]
    if isinstance(payload, str):
        return redact_text(payload)
    return payload
