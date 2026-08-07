"""Unit tests for Y-only worktree path policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.worktrees import codes
from tools.worktrees.policy import (
    FsProbe,
    validate_main_checkout_path,
    validate_new_worktree_path,
)


def _probe(*, writable: bool = True, exists: bool = True) -> FsProbe:
    def _exists(path: Path) -> bool:
        return exists

    def _is_dir(path: Path) -> bool:
        return exists

    probe = FsProbe(exists=_exists, is_dir=_is_dir)
    if not writable:
        object.__setattr__(
            probe,
            "is_writable",
            lambda path: False,  # type: ignore[method-assign]
        )
        # FsProbe.is_writable is a method; replace via subclass pattern instead
    return probe


class _WritableProbe(FsProbe):
    def __init__(self, *, exists: bool = True, writable: bool = True) -> None:
        self._exists_flag = exists
        self._writable = writable
        super().__init__(
            exists=lambda p: self._exists_flag,
            is_dir=lambda p: self._exists_flag,
        )

    def is_writable(self, path: Path) -> bool:
        return self._exists_flag and self._writable


@pytest.mark.unit
def test_y_path_pass() -> None:
    result = validate_new_worktree_path(
        r"Y:\Worktrees\Claire_de_Binare\foo",
        root=Path(r"Y:\Worktrees"),
        platform="win32",
        fs=_WritableProbe(),
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
    )
    assert result.status == "PASS"
    assert codes.WORKTREE_PATH_ALLOWED in result.reason_codes


@pytest.mark.unit
def test_c_drive_fail() -> None:
    result = validate_new_worktree_path(
        r"C:\Users\tmp\cdb-wt-x",
        root=Path(r"Y:\Worktrees"),
        platform="win32",
        fs=_WritableProbe(),
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
    )
    assert result.status == "FAIL"
    assert codes.WORKTREE_ON_C_DRIVE in result.reason_codes


@pytest.mark.unit
def test_d_drive_fail_for_new_worktree() -> None:
    result = validate_new_worktree_path(
        r"D:\Dev\Workspaces\Repos\cdb-wt-x",
        root=Path(r"Y:\Worktrees"),
        platform="win32",
        fs=_WritableProbe(),
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
    )
    assert result.status == "FAIL"
    assert codes.WORKTREE_ON_D_DRIVE in result.reason_codes


@pytest.mark.unit
def test_y_missing_fail() -> None:
    result = validate_new_worktree_path(
        r"Y:\Worktrees\Claire_de_Binare\foo",
        root=Path(r"Y:\Worktrees"),
        platform="win32",
        fs=_WritableProbe(exists=False),
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
    )
    assert result.status == "FAIL"
    assert codes.WORKTREE_ROOT_UNAVAILABLE in result.reason_codes


@pytest.mark.unit
def test_y_not_writable_fail() -> None:
    result = validate_new_worktree_path(
        r"Y:\Worktrees\Claire_de_Binare\foo",
        root=Path(r"Y:\Worktrees"),
        platform="win32",
        fs=_WritableProbe(writable=False),
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
    )
    assert result.status == "FAIL"
    assert codes.WORKTREE_ROOT_NOT_WRITABLE in result.reason_codes


@pytest.mark.unit
def test_outside_root_fail() -> None:
    result = validate_new_worktree_path(
        r"Y:\Other\foo",
        root=Path(r"Y:\Worktrees"),
        platform="win32",
        fs=_WritableProbe(),
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
    )
    assert result.status == "FAIL"
    assert codes.WORKTREE_OUTSIDE_CANONICAL_ROOT in result.reason_codes


@pytest.mark.unit
def test_linux_policy_not_applicable() -> None:
    result = validate_new_worktree_path(
        "/tmp/wt/foo",
        platform="linux",
        fs=_WritableProbe(),
    )
    assert result.status == "SKIP"
    assert codes.WORKTREE_POLICY_NOT_APPLICABLE in result.reason_codes


@pytest.mark.unit
def test_main_checkout_on_d_allowed() -> None:
    result = validate_main_checkout_path(
        r"D:\Dev\Workspaces\Repos\Claire_de_Binare",
        platform="win32",
    )
    assert result.status == "PASS"
    assert codes.MAIN_CHECKOUT_ALLOWED in result.reason_codes
