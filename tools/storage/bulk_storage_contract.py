"""Fail-closed opt-in contract for the Windows CDB bulk-storage root (#4419)."""

from __future__ import annotations

import os
import stat
from pathlib import Path, PureWindowsPath
from typing import Mapping

BULK_STORAGE_ROOT_ENV = "CDB_BULK_STORAGE_ROOT"
CANONICAL_BULK_STORAGE_ROOT = PureWindowsPath("Y:/CDB-Storage")
WORKTREE_ROOT = PureWindowsPath("Y:/Worktrees")
BULK_STORAGE_SUBTREES = frozenset(
    {"market-history", "replay-arvp", "logs", "evidence", "archive"}
)


class BulkStorageContractError(ValueError):
    """Raised when an explicitly selected bulk-storage path is not canonical."""


def _windows_path(value: str) -> PureWindowsPath:
    candidate = PureWindowsPath(value.strip())
    if (
        not value.strip()
        or not candidate.is_absolute()
        or candidate.drive.upper() != "Y:"
    ):
        raise BulkStorageContractError("BULK_STORAGE_ROOT_INVALID")
    return candidate


def _normalise(path: PureWindowsPath) -> str:
    return str(path).replace("/", "\\").rstrip("\\").casefold()


def _is_reparse_point(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def _reject_reparse_ancestors(path: Path) -> None:
    current = path
    while True:
        if _is_reparse_point(current):
            raise BulkStorageContractError("BULK_STORAGE_REPARSE_POINT")
        parent = current.parent
        if parent == current:
            return
        current = parent


def validate_bulk_storage_root(value: str) -> Path:
    """Validate the only accepted root without creating it or redirecting it.

    The root may not exist yet: #4419 defines a policy, while later issues own
    provisioning and data migration. Existing ancestor junctions/symlinks are
    nevertheless rejected so that they cannot silently stand in for the contract.
    """
    candidate = _windows_path(value)
    if _normalise(candidate) != _normalise(CANONICAL_BULK_STORAGE_ROOT):
        if _normalise(candidate).startswith(_normalise(WORKTREE_ROOT) + "\\") or (
            _normalise(candidate) == _normalise(WORKTREE_ROOT)
        ):
            raise BulkStorageContractError("BULK_STORAGE_WORKTREE_ROOT_FORBIDDEN")
        raise BulkStorageContractError("BULK_STORAGE_ROOT_NON_CANONICAL")

    resolved = Path(str(candidate))
    _reject_reparse_ancestors(resolved)
    return resolved


def resolve_bulk_storage_path(
    subtree: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve an explicitly opted-in subtree or fail closed.

    Existing consumers do not call this helper and retain their current D:/repo
    paths. A consumer that adopts the new contract must configure its root; no
    fallback, directory creation, copy, move, or deletion is performed here.
    """
    if subtree not in BULK_STORAGE_SUBTREES:
        raise BulkStorageContractError("BULK_STORAGE_SUBTREE_INVALID")
    env = os.environ if environ is None else environ
    raw_root = env.get(BULK_STORAGE_ROOT_ENV, "")
    if not raw_root.strip():
        raise BulkStorageContractError("BULK_STORAGE_ROOT_REQUIRED")
    return validate_bulk_storage_root(raw_root) / subtree
