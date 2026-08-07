"""Unit tests for hh_hl execution window-bank resolution (#4395).

No physical campaign execute. No Owner-GO. No dataset content mutation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.arvp_vacation.hh_hl_execution_window_bank import (
    HOLD_WINDOW_BANK_LINK_CONFLICT,
    HOLD_WINDOW_BANK_UNAVAILABLE,
    HhHlExecutionWindowBankError,
    assert_execution_window_bank_available,
    ensure_worktree_market_data_link,
    local_market_data_root,
    local_window_bank_root,
    main as window_bank_main,
    parent_checkout_root,
    resolve_execution_window_bank,
)
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)


def _fake_complete_bank(root: Path) -> Path:
    bank = (
        root
        / "artifacts"
        / "market_data"
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
    )
    for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS:
        (bank / wid).mkdir(parents=True, exist_ok=True)
    return bank


def test_resolve_prefers_local_complete_bank(tmp_path: Path) -> None:
    bank = _fake_complete_bank(tmp_path)
    resolved = resolve_execution_window_bank(tmp_path)
    assert resolved is not None
    assert resolved.window_bank_root == bank.resolve()
    assert resolved.source_kind in {"local", "link"}
    assert resolved.window_count == 39


def test_resolve_falls_back_to_parent_worktree_layout(tmp_path: Path) -> None:
    parent = tmp_path / "Claire_de_Binare"
    parent.mkdir()
    bank = _fake_complete_bank(parent)
    wt = parent / ".worktrees" / "exact-sha-exec"
    wt.mkdir(parents=True)
    # Worktree has no local market_data.
    assert not local_market_data_root(wt).exists()
    assert parent_checkout_root(wt) == parent.resolve()
    resolved = resolve_execution_window_bank(wt)
    assert resolved is not None
    assert resolved.window_bank_root == bank.resolve()
    assert resolved.source_kind == "parent"


def test_assert_fail_closed_when_incomplete(tmp_path: Path) -> None:
    bank = local_window_bank_root(tmp_path)
    # Only one window — incomplete.
    (bank / LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]).mkdir(parents=True)
    with pytest.raises(HhHlExecutionWindowBankError) as exc:
        assert_execution_window_bank_available(tmp_path)
    assert exc.value.reason_code == HOLD_WINDOW_BANK_UNAVAILABLE


def test_ensure_link_creates_junction_or_symlink(tmp_path: Path) -> None:
    parent = tmp_path / "Claire_de_Binare"
    parent.mkdir()
    _fake_complete_bank(parent)
    wt = parent / ".worktrees" / "exact-sha-exec"
    wt.mkdir(parents=True)
    result = ensure_worktree_market_data_link(wt)
    assert result["ok"] is True
    assert result["action"] == "linked"
    assert local_market_data_root(wt).exists()
    assert resolve_execution_window_bank(wt) is not None
    # Idempotent.
    again = ensure_worktree_market_data_link(wt)
    assert again["action"] == "already_linked"


def test_ensure_link_refuses_conflict(tmp_path: Path) -> None:
    parent = tmp_path / "Claire_de_Binare"
    parent.mkdir()
    _fake_complete_bank(parent)
    wt = parent / ".worktrees" / "exact-sha-exec"
    wt.mkdir(parents=True)
    # Real non-linked directory that is incomplete.
    local_market_data_root(wt).mkdir(parents=True)
    (local_market_data_root(wt) / "noise.txt").write_text("x", encoding="utf-8")
    with pytest.raises(HhHlExecutionWindowBankError) as exc:
        ensure_worktree_market_data_link(wt)
    assert exc.value.reason_code == HOLD_WINDOW_BANK_LINK_CONFLICT


def test_cli_assert_and_resolve(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_complete_bank(tmp_path)
    assert window_bank_main(["--repo-root", str(tmp_path), "assert"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["resolution"]["window_count"] == 39

    empty = tmp_path / "empty-wt"
    empty.mkdir()
    assert window_bank_main(["--repo-root", str(empty), "resolve"]) == 1
    out2 = json.loads(capsys.readouterr().out)
    assert out2["ok"] is False
    assert out2["reason_code"] == HOLD_WINDOW_BANK_UNAVAILABLE


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bank_host = tmp_path / "external_bank_host"
    bank = _fake_complete_bank(bank_host)
    orphan = tmp_path / "orphan-wt"
    orphan.mkdir()
    monkeypatch.setenv("CDB_WINDOW_BANK_ROOT", str(bank))
    resolved = resolve_execution_window_bank(orphan)
    assert resolved is not None
    assert resolved.source_kind == "env"
    assert resolved.window_bank_root == bank.resolve()
    monkeypatch.delenv("CDB_WINDOW_BANK_ROOT", raising=False)
