"""Regression guards for Linux-safe bulk-storage path joining (#4504)."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from tools.storage.bulk_storage_contract import (
    BULK_STORAGE_ROOT_ENV,
    resolve_bulk_storage_path,
)


@pytest.mark.unit
def test_resolve_bulk_storage_path_uses_windows_separators_on_posix_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tools.storage.bulk_storage_contract._reject_reparse_ancestors", lambda _: None
    )
    result = resolve_bulk_storage_path(
        "replay-arvp", environ={BULK_STORAGE_ROOT_ENV: "Y:\\CDB-Storage"}
    )
    expected = str(PureWindowsPath("Y:/CDB-Storage") / "replay-arvp")
    assert str(result) == expected
    assert "/" not in str(result)
