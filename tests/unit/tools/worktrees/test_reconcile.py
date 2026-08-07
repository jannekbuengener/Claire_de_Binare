"""Unit tests for legacy worktree classification."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.worktrees import codes
from tools.worktrees.reconcile import (
    LegacyWorktreeFacts,
    classify_legacy_worktree,
    discover_legacy_fs_paths,
    enrich_worktree_facts,
    infer_active_issue,
    inventory_from_porcelain,
    reconcile_inventory,
)


@pytest.mark.unit
def test_main_branch_worktree_never_obsolete() -> None:
    result = classify_legacy_worktree(
        LegacyWorktreeFacts(
            path=r"D:\Dev\Workspaces\Repos\cdb-wt-4164-publisher",
            branch="main",
            dirty=False,
            unpushed=False,
            merged_into_base=True,
            on_windows_legacy_drive=True,
        )
    )
    assert result.classification == codes.UNCLEAR_HOLD
    assert codes.MAIN_CHECKOUT_ALLOWED in result.reason_codes


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


@pytest.mark.unit
def test_infer_active_issue() -> None:
    assert infer_active_issue("dedicated/ci-tooling-issue-4393") == "4393"
    assert infer_active_issue("fix/4182-stop-loss") == "4182"
    assert infer_active_issue(None, r"D:\x\.worktrees\4374-exec-go-prep") == "4374"


@pytest.mark.unit
def test_enrich_marks_dirty_and_merged(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(args: list[str] | tuple[str, ...], cwd: str | None):
        cmd = tuple(args)
        calls.append(cmd)
        # status dirty
        if "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, " M file.py\n", "")
        if "rev-list" in cmd and "@{upstream}..HEAD" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "0\n", "")
        if "merge-base" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 1, "", "err")

    # Create path so exists() is true
    wt = tmp_path / "cdb-wt-demo"
    wt.mkdir()
    facts = LegacyWorktreeFacts(
        path=str(wt),
        branch="issue-1234-demo",
        head="abc",
        on_windows_legacy_drive=True,
    )
    enriched = enrich_worktree_facts(
        facts,
        main_checkout=str(tmp_path / "main"),
        git_runner=fake_git,
    )
    assert enriched.dirty is True
    assert enriched.unpushed is False
    assert enriched.merged_into_base is True
    assert enriched.active_issue == "1234"
    assert classify_legacy_worktree(enriched).classification == codes.UNCLEAR_HOLD


@pytest.mark.unit
def test_enrich_obsolete_when_clean_merged(tmp_path: Path) -> None:
    def fake_git(args: list[str] | tuple[str, ...], cwd: str | None):
        cmd = tuple(args)
        if "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if "rev-list" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "0\n", "")
        if "merge-base" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 1, "", "")

    wt = tmp_path / "cdb-wt-old"
    wt.mkdir()
    facts = LegacyWorktreeFacts(path=str(wt), branch="gone-branch", head="abc")
    enriched = enrich_worktree_facts(
        facts,
        main_checkout=str(tmp_path / "main"),
        git_runner=fake_git,
    )
    # Force legacy drive flag for classification path used in hosts
    from dataclasses import replace

    enriched = replace(enriched, on_windows_legacy_drive=True)
    assert enriched.dirty is False
    assert enriched.unpushed is False
    assert enriched.merged_into_base is True
    assert classify_legacy_worktree(enriched).classification == codes.OBSOLETE_REMOVE


@pytest.mark.unit
def test_reconcile_inventory_without_enrich_is_hold() -> None:
    text = """\
worktree D:/Dev/Workspaces/Repos/cdb-wt-x
HEAD 123456
branch refs/heads/feat-x

"""
    facts, results = reconcile_inventory(porcelain_text=text, enrich=False)
    assert len(facts) == 1
    assert results[0].classification == codes.UNCLEAR_HOLD


@pytest.mark.unit
def test_discover_legacy_fs_paths(tmp_path: Path) -> None:
    root = tmp_path / "Repos"
    root.mkdir()
    main = root / "Claire_de_Binare"
    main.mkdir()
    (main / ".git").mkdir()
    legacy = root / "cdb-wt-1234"
    legacy.mkdir()
    (legacy / ".git").write_text("gitdir: somewhere", encoding="utf-8")
    nested = main / ".worktrees" / "4384-run-key"
    nested.mkdir(parents=True)
    (nested / ".git").write_text("gitdir: somewhere", encoding="utf-8")
    noise = root / "not-a-wt"
    noise.mkdir()

    found = discover_legacy_fs_paths(
        [str(root)],
        main_checkout=str(main),
    )
    norms = {str(Path(p)).lower() for p in found}
    assert str(legacy).lower() in norms
    assert str(nested).lower() in norms
    assert str(main).lower() not in norms
    assert str(noise).lower() not in norms
