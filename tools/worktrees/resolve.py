"""Resolve the canonical local Windows worktree root and target paths."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Mapping, Sequence

from tools.worktrees import codes

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class ResolveResult:
    """Outcome of resolving CDB_WORKTREE_ROOT."""

    status: str
    root: Path | None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    platform: str = ""
    source: str = ""  # env | default | none


def is_windows_drive_policy_applicable(platform: str | None = None) -> bool:
    """Return True only when Windows drive-letter policy must apply."""
    plat = (platform or sys.platform).lower()
    return plat.startswith("win")


def resolve_worktree_root(
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> ResolveResult:
    """Resolve the canonical worktree root.

    On non-Windows platforms the Windows Y: default is not applied; callers
    may still set CDB_WORKTREE_ROOT explicitly for path construction tests.
    """
    plat = platform or sys.platform
    environ = env if env is not None else os.environ
    raw = (environ.get(codes.ENV_WORKTREE_ROOT) or "").strip()

    if raw:
        root = Path(raw)
        return ResolveResult(
            status="PASS",
            root=root,
            reason_codes=(),
            platform=plat,
            source="env",
        )

    if is_windows_drive_policy_applicable(plat):
        return ResolveResult(
            status="PASS",
            root=Path(codes.DEFAULT_WINDOWS_ROOT),
            reason_codes=(),
            platform=plat,
            source="default",
        )

    return ResolveResult(
        status="SKIP",
        root=None,
        reason_codes=(codes.WORKTREE_POLICY_NOT_APPLICABLE,),
        platform=plat,
        source="none",
    )


def _validate_name_segment(value: str, *, label: str) -> str | None:
    text = (value or "").strip()
    if not text or text in {".", ".."} or "/" in text or "\\" in text:
        return f"{label} invalid"
    if not _NAME_RE.match(text):
        return f"{label} invalid"
    return None


def build_worktree_path(
    root: Path,
    repository: str,
    worktree_name: str,
) -> Path:
    """Build ``<root>/<repository>/<worktree-name>`` fail-closed."""
    repo_err = _validate_name_segment(repository, label="repository")
    name_err = _validate_name_segment(worktree_name, label="worktree_name")
    if repo_err or name_err:
        raise ValueError(codes.WORKTREE_NAME_INVALID)
    return Path(root) / repository.strip() / worktree_name.strip()


def windows_drive_letter(path: Path | str) -> str | None:
    """Return drive letter uppercased (e.g. ``Y``) or None."""
    text = str(path)
    # PureWindowsPath handles both / and \ for drive letters.
    drive = PureWindowsPath(text).drive
    if len(drive) >= 2 and drive[1] == ":":
        return drive[0].upper()
    return None


def normalize_for_compare(path: Path | str) -> str:
    """Normalize path for containment checks (case-insensitive on Windows)."""
    return os.path.normcase(os.path.normpath(str(path)))


def is_path_under_root(path: Path | str, root: Path | str) -> bool:
    """True if path is equal to root or a descendant.

    Drive-letter paths always use ``PureWindowsPath`` semantics so Linux CI
    hosts evaluate ``Y:\\...`` containment correctly (POSIX ``os.sep`` must
    not decide Windows worktree policy).
    """
    if windows_drive_letter(path) is not None or windows_drive_letter(root) is not None:
        win_path = PureWindowsPath(str(path))
        win_root = PureWindowsPath(str(root))
        try:
            win_path.relative_to(win_root)
            return True
        except ValueError:
            return False

    norm_path = normalize_for_compare(path)
    norm_root = normalize_for_compare(root)
    if norm_path == norm_root:
        return True
    prefix = norm_root + os.sep
    return norm_path.startswith(prefix)


def reason_summary(codes_seq: Sequence[str]) -> str:
    return ",".join(codes_seq)
