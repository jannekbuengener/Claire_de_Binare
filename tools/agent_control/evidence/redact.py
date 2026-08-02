"""Fail-closed redaction for agent run evidence (#4256).

Input trust is untrusted. Structural removal or abort — masking with *** alone
never yields PASS.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.codes import REASON_SECRET_DETECTED

_AUTH_KEY = re.compile(
    r"(?i)^(authorization|cookie|x-api-key|api[-_]?key|token|secret|password|"
    r"session|private[_-]?key|access[_-]?token|refresh[_-]?token)$"
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+\S+")
_CRSR = re.compile(r"\bcrsr_[A-Za-z0-9_\-]{8,}\b")
_PRESIGNED = re.compile(r"(?i)[?&](X-Amz-Signature|Signature|token)=|presigned")
_PEM = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
_PROMPT_KEY = re.compile(r"(?i)^(prompt_text|prompt_body|system_prompt|raw_prompt)$")
_SECRET_PATH = re.compile(r"(?i)(/run/secrets/|documents[\\/]\.secrets|\.secrets[\\/])")


def _string_has_secret(text: str) -> bool:
    if _BEARER.search(text) or _CRSR.search(text) or _PRESIGNED.search(text):
        return True
    if _PEM.search(text):
        return True
    if _SECRET_PATH.search(text):
        return True
    return False


def detect_secrets(value: Any, *, path: str = "$") -> list[str]:
    """Return paths where secret-like content appears."""
    hits: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_s = str(key)
            child = f"{path}.{key_s}"
            if _AUTH_KEY.match(key_s) or _PROMPT_KEY.match(key_s):
                hits.append(child)
                continue
            hits.extend(detect_secrets(item, path=child))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            hits.extend(detect_secrets(item, path=f"{path}[{idx}]"))
    elif isinstance(value, str):
        if _string_has_secret(value):
            hits.append(path)
    return hits


def strip_secrets(value: Any) -> Any:
    """Structurally remove secret-bearing keys; never leave *** placeholders."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_s = str(key)
            if _AUTH_KEY.match(key_s) or _PROMPT_KEY.match(key_s):
                continue
            cleaned = strip_secrets(item)
            if isinstance(item, str) and _string_has_secret(item):
                continue
            out[key_s] = cleaned
        return out
    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            if isinstance(item, str) and _string_has_secret(item):
                continue
            cleaned_list.append(strip_secrets(item))
        return cleaned_list
    if isinstance(value, str) and _string_has_secret(value):
        return None
    return value


def assert_no_secrets(payload: Any) -> None:
    hits = detect_secrets(payload)
    if hits:
        raise EvidenceError(
            REASON_SECRET_DETECTED,
            f"secret-like content at {hits[0]}",
        )


def sanitize_result_refs(result_refs: dict[str, Any] | None) -> dict[str, Any]:
    refs = strip_secrets(deepcopy(result_refs or {}))
    if not isinstance(refs, dict):
        return {}
    assert_no_secrets(refs)
    return refs


def validate_repo_relative_path(
    path: str,
    *,
    allowed_roots: tuple[str, ...] = ("artifacts/",),
) -> str:
    text = path.replace("\\", "/").strip()
    if not text or text.startswith("/") or text.startswith("~"):
        raise EvidenceError(
            "EVIDENCE_PATH_INVALID",
            f"absolute or empty path rejected: {path!r}",
        )
    if text.startswith("..") or "/../" in f"/{text}/" or text.endswith("/.."):
        raise EvidenceError(
            "EVIDENCE_PATH_INVALID",
            f"path traversal rejected: {path!r}",
        )
    if "://" in text:
        parsed = urlparse(text)
        if parsed.scheme:
            raise EvidenceError(
                "EVIDENCE_PATH_INVALID",
                f"URL path rejected: {path!r}",
            )
    if allowed_roots and not any(text.startswith(root) for root in allowed_roots):
        raise EvidenceError(
            "EVIDENCE_PATH_INVALID",
            f"path outside allowed roots: {path!r}",
        )
    return text
