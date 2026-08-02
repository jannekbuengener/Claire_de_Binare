"""Fail-closed path normalization for execution_scope allow/deny lists."""

from __future__ import annotations

import posixpath
import re

from tools.agent_execution_contract.errors import ContractValidationError

_SAFE_PATH_RE = re.compile(
    r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))"
    r"(?:[A-Za-z0-9._@+-]+(?:/[A-Za-z0-9._@+-]+)*)(?:/\*)?$"
)


def normalize_repo_relative_path(raw: str) -> str:
    """Normalize and validate a repo-relative path pattern.

    Rejects absolute paths, traversal (`..`), empty segments, backslashes,
    null bytes, and other alias/escape attempts.
    """
    if not isinstance(raw, str) or not raw:
        raise ContractValidationError(
            "CONTRACT_PATH_INVALID",
            "path must be a non-empty string",
        )
    if "\x00" in raw or "\\" in raw:
        raise ContractValidationError(
            "CONTRACT_PATH_TRAVERSAL",
            "null byte or backslash in path is rejected",
        )
    if raw.startswith("/") or raw.startswith("~"):
        raise ContractValidationError(
            "CONTRACT_PATH_TRAVERSAL",
            "absolute or home-relative paths are rejected",
        )
    if "//" in raw or "/./" in raw or raw.startswith("./") or raw.endswith("/."):
        raise ContractValidationError(
            "CONTRACT_PATH_TRAVERSAL",
            f"non-canonical path alias rejected: {raw!r}",
        )
    if any(part == ".." for part in raw.split("/")):
        raise ContractValidationError(
            "CONTRACT_PATH_TRAVERSAL",
            f"path traversal rejected: {raw!r}",
        )
    if not _SAFE_PATH_RE.match(raw):
        raise ContractValidationError(
            "CONTRACT_PATH_INVALID",
            f"path does not match repo-relative allowlist pattern: {raw!r}",
        )

    if raw.endswith("/*"):
        base = raw[:-2]
        normalized = posixpath.normpath(base)
        if normalized != base or normalized in {".", ".."}:
            raise ContractValidationError(
                "CONTRACT_PATH_TRAVERSAL",
                f"path traversal rejected: {raw!r}",
            )
        return f"{normalized}/*"

    if raw.endswith("*") and "/" not in raw:
        return raw

    normalized = posixpath.normpath(raw)
    if normalized != raw or normalized in {".", ".."}:
        raise ContractValidationError(
            "CONTRACT_PATH_TRAVERSAL",
            f"non-canonical path alias rejected: {raw!r}",
        )
    return raw


def normalize_path_list(paths: list[str]) -> list[str]:
    return [normalize_repo_relative_path(p) for p in paths]
