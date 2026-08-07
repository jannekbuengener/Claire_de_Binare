"""Unit tests for governed worktree create planning."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.worktrees import codes
from tools.worktrees.create import create_worktree, plan_worktree_create
from tools.worktrees.policy import FsProbe


class _Probe(FsProbe):
    def __init__(self) -> None:
        super().__init__(exists=lambda p: True, is_dir=lambda p: True)

    def is_writable(self, path: Path) -> bool:
        return True


@pytest.mark.unit
def test_plan_create_pass_dry_run() -> None:
    plan = plan_worktree_create(
        repository="Claire_de_Binare",
        worktree_name="issue-9999",
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
        platform="win32",
        fs=_Probe(),
        path_exists=lambda p: False,
    )
    assert plan.status == "PASS"
    assert plan.path.endswith(str(Path("Claire_de_Binare") / "issue-9999"))
    result = create_worktree(plan, dry_run=True)
    assert result.status == "PASS"
    assert codes.WORKTREE_CREATE_PLANNED in result.reason_codes


@pytest.mark.unit
def test_plan_create_collision() -> None:
    plan = plan_worktree_create(
        repository="Claire_de_Binare",
        worktree_name="exists",
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
        platform="win32",
        fs=_Probe(),
        path_exists=lambda p: True,
    )
    assert plan.status == "FAIL"
    assert codes.WORKTREE_PATH_COLLISION in plan.reason_codes


@pytest.mark.unit
def test_create_does_not_call_git_on_policy_fail() -> None:
    calls: list[list[str]] = []

    def runner(args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(args))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    plan = plan_worktree_create(
        repository="Claire_de_Binare",
        worktree_name="bad",
        env={codes.ENV_WORKTREE_ROOT: r"Y:\Worktrees"},
        platform="win32",
        fs=_Probe(),
        path_exists=lambda p: False,
    )
    # Force fail by mutating into a rejected plan
    from tools.worktrees.create import CreatePlan

    failed = CreatePlan(
        status="FAIL",
        path=r"D:\bad",
        repository="Claire_de_Binare",
        worktree_name="bad",
        ref="origin/main",
        branch=None,
        reason_codes=(codes.WORKTREE_ON_D_DRIVE,),
        root=r"Y:\Worktrees",
    )
    result = create_worktree(failed, dry_run=False, git_runner=runner)
    assert result.status == "FAIL"
    assert calls == []
