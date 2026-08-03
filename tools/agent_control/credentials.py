"""Credential presence checks without reading secret values into logs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CredentialPresence:
    """Bool-only presence result; never carries secret material."""

    name: str
    present: bool
    source: str  # env | file | missing


def cursor_api_key_present(
    *,
    env: dict[str, str] | None = None,
    secrets_dir: Path | None = None,
) -> CredentialPresence:
    """Return whether CURSOR_API_KEY exists as env or secrets file.

    Does not return or log the secret value. File presence checks only the
    basename ``CURSOR_API_KEY`` (or ``CURSOR_API_KEY.txt``) under secrets_dir.
    """
    environ = env if env is not None else os.environ
    if "CURSOR_API_KEY" in environ and str(environ.get("CURSOR_API_KEY", "")).strip():
        return CredentialPresence(name="CURSOR_API_KEY", present=True, source="env")
    if secrets_dir is not None:
        for candidate in (
            secrets_dir / "CURSOR_API_KEY",
            secrets_dir / "CURSOR_API_KEY.txt",
        ):
            if candidate.is_file() and candidate.stat().st_size > 0:
                return CredentialPresence(
                    name="CURSOR_API_KEY", present=True, source="file"
                )
    return CredentialPresence(name="CURSOR_API_KEY", present=False, source="missing")
