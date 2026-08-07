"""Unit tests for worktree root resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.worktrees import codes
from tools.worktrees.resolve import (
    build_worktree_path,
    is_path_under_root,
    resolve_worktree_root,
)


@pytest.mark.unit
def test_resolve_root_windows_default() -> None:
    result = resolve_worktree_root(env={}, platform="win32")
    assert result.status == "PASS"
    assert result.root == Path(codes.DEFAULT_WINDOWS_ROOT)
    assert result.source == "default"


@pytest.mark.unit
def test_resolve_root_env_override() -> None:
    result = resolve_worktree_root(
        env={codes.ENV_WORKTREE_ROOT: r"Y:\CustomRoot"},
        platform="win32",
    )
    assert result.status == "PASS"
    assert result.root == Path(r"Y:\CustomRoot")
    assert result.source == "env"


@pytest.mark.unit
def test_resolve_root_linux_without_env_skips_y_default() -> None:
    result = resolve_worktree_root(env={}, platform="linux")
    assert result.status == "SKIP"
    assert result.root is None
    assert codes.WORKTREE_POLICY_NOT_APPLICABLE in result.reason_codes


@pytest.mark.unit
def test_build_worktree_path_ok() -> None:
    path = build_worktree_path(Path(r"Y:\Worktrees"), "Claire_de_Binare", "foo")
    assert path == Path(r"Y:\Worktrees") / "Claire_de_Binare" / "foo"


@pytest.mark.unit
def test_build_worktree_path_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        build_worktree_path(Path(r"Y:\Worktrees"), "Claire_de_Binare", "../escape")


@pytest.mark.unit
def test_is_path_under_root_windows_drive_semantics() -> None:
    """Containment must not depend on host os.sep (Linux CI regression guard)."""
    assert is_path_under_root(
        r"Y:\Worktrees\Claire_de_Binare\foo",
        r"Y:\Worktrees",
    )
    assert is_path_under_root(r"Y:\Worktrees", r"Y:\Worktrees")
    assert not is_path_under_root(r"Y:\Other\foo", r"Y:\Worktrees")
    assert not is_path_under_root(r"D:\Worktrees\foo", r"Y:\Worktrees")
