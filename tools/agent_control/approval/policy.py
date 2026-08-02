"""Load versioned approval policy; compute content_sha256 at load time."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from tools.agent_control.approval.codes import (
    DIGEST_PREFIX,
    REASON_MISSING_POLICY,
    ApprovalError,
)


def content_sha256_bytes(raw: bytes) -> str:
    """Hash file bytes after LF-normalization (CRLF/CR → LF).

    Keeps policy/prompt digests stable across Windows working trees and
    Git LF blobs so baselines match committed artifacts.
    """
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return f"{DIGEST_PREFIX}{hashlib.sha256(normalized).hexdigest()}"


def load_policy(path: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Load policy YAML and return metadata with load-time content hash.

    The source file must not embed its own content_sha256 (no circular contract).
    """
    if not path.is_file():
        raise ApprovalError(REASON_MISSING_POLICY, f"policy file missing: {path}")
    raw = path.read_bytes()
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ApprovalError(
            REASON_MISSING_POLICY, f"policy unreadable: {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ApprovalError(REASON_MISSING_POLICY, f"policy must be a mapping: {path}")
    if "content_sha256" in data:
        raise ApprovalError(
            REASON_MISSING_POLICY,
            "policy must not embed content_sha256 (computed at load time)",
        )
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ApprovalError(REASON_MISSING_POLICY, "policy.version missing")
    return {
        "version": version.strip(),
        "source_path": _repo_relative(path, repo_root),
        "content_sha256": content_sha256_bytes(raw),
        "document": data,
    }


def _repo_relative(path: Path, repo_root: Path | None) -> str:
    resolved = path.resolve()
    if repo_root is not None:
        try:
            return resolved.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()
