"""Load versioned approval prompt; compute content_sha256 at load time."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.agent_control.approval.codes import REASON_MISSING_PROMPT, ApprovalError
from tools.agent_control.approval.policy import _repo_relative, content_sha256_bytes

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_VERSION_LINE = re.compile(r"(?m)^version:\s*[\"']?([^\"'\n]+)[\"']?\s*$")


def load_prompt(path: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Load prompt markdown and return metadata with load-time content hash.

    The source file must not embed its own content_sha256 (no circular contract).
    Version is read from YAML frontmatter ``version:`` when present.
    """
    if not path.is_file():
        raise ApprovalError(REASON_MISSING_PROMPT, f"prompt file missing: {path}")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ApprovalError(
            REASON_MISSING_PROMPT, f"prompt unreadable: {path}: {exc}"
        ) from exc

    frontmatter = _FRONTMATTER.match(text)
    if frontmatter and re.search(r"(?m)^content_sha256\s*:", frontmatter.group(1)):
        raise ApprovalError(
            REASON_MISSING_PROMPT,
            "prompt must not embed content_sha256 (computed at load time)",
        )

    version = _extract_version(text)
    if not version:
        raise ApprovalError(REASON_MISSING_PROMPT, "prompt.version missing")
    return {
        "version": version,
        "source_path": _repo_relative(path, repo_root),
        "content_sha256": content_sha256_bytes(raw),
        "body": text,
    }


def _extract_version(text: str) -> str | None:
    match = _FRONTMATTER.match(text)
    if not match:
        return None
    version_match = _VERSION_LINE.search(match.group(1))
    if not version_match:
        return None
    return version_match.group(1).strip()
