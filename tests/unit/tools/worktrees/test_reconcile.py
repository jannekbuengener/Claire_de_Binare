"""Unit tests for legacy worktree classification."""

from __future__ import annotations

import pytest

from tools.worktrees import codes
from tools.worktrees.reconcile import (
    LegacyWorktreeFacts,
    classify_legacy_worktree,
    inventory_from_porcelain,
)


@pytest.mark.unit
def test_main_checkout_not_removal_target() -> None:
    result = classify_legacy_worktree(
        LegacyWorktreeFacts(
            path=r"D:\Dev\Workspaces\Repos\Claire_de_Binare",
            is_main_checkout=True,
            dirty=False,
            unpushed=False,
        )
    )
    assert codes.MAIN_CHECKOUT_ALLOWED in result.reason_codes


@pytest.mark.unit
def test_obsolete_remove() -> None:
    result = classify_legacy_worktree(
        LegacyWorktreeFacts(
            path=r"D:\Dev\Workspaces\Repos\cdb-wt-old",
            dirty=False,
            unpushed=False,
            merged_into_base=True,
            on_windows_legacy_drive=True,
        )
    )
    assert result.classification == codes.OBSOLETE_REMOVE


@pytest.mark.unit
def test_needed_quick_finish() -> None:
    result = classify_legacy_worktree(
        LegacyWorktreeFacts(
            path=r"D:\Dev\Workspaces\Repos\cdb-wt-x",
            dirty=False,
            unpushed=False,
            merged_into_base=False,
            active_issue="1234",
        )
    )
    assert result.classification == codes.NEEDED_QUICK_FINISH


@pytest.mark.unit
def test_needed_followup_issue() -> None:
    result = classify_legacy_worktree(
        LegacyWorktreeFacts(
            path=r"D:\Dev\Workspaces\Repos\cdb-wt-x",
            dirty=False,
            unpushed=True,
            active_issue="1234",
        )
    )
    assert result.classification == codes.NEEDED_FOLLOWUP_ISSUE


@pytest.mark.unit
def test_unclear_hold_dirty() -> None:
    result = classify_legacy_worktree(
        LegacyWorktreeFacts(
            path=r"D:\Dev\Workspaces\Repos\cdb-wt-x",
            dirty=True,
            unpushed=False,
        )
    )
    assert result.classification == codes.UNCLEAR_HOLD


@pytest.mark.unit
def test_inventory_from_porcelain() -> None:
    text = """\
worktree D:/Dev/Workspaces/Repos/Claire_de_Binare
HEAD abcdef
branch refs/heads/main

worktree D:/Dev/Workspaces/Repos/cdb-wt-x
HEAD 123456
detached
prunable

"""
    facts = inventory_from_porcelain(text)
    assert len(facts) == 2
    assert facts[0].branch == "main"
    assert facts[1].prunable is True
