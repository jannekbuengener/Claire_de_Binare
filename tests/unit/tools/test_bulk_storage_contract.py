from __future__ import annotations

from pathlib import Path

import pytest

from tools.storage.bulk_storage_contract import (
    BULK_STORAGE_ROOT_ENV,
    BulkStorageContractError,
    resolve_bulk_storage_path,
    validate_bulk_storage_root,
)


@pytest.mark.unit
def test_valid_canonical_y_bulk_root_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tools.storage.bulk_storage_contract._reject_reparse_ancestors", lambda _: None
    )
    assert validate_bulk_storage_root("Y:\\CDB-Storage") == Path("Y:\\CDB-Storage")


@pytest.mark.unit
def test_worktree_root_is_rejected() -> None:
    with pytest.raises(BulkStorageContractError, match="WORKTREE_ROOT_FORBIDDEN"):
        validate_bulk_storage_root("Y:\\Worktrees\\Claire_de_Binare\\bulk")


@pytest.mark.unit
def test_disallowed_drive_or_root_is_rejected() -> None:
    with pytest.raises(BulkStorageContractError, match="ROOT_INVALID"):
        validate_bulk_storage_root("D:\\CDB-Storage")


@pytest.mark.unit
def test_explicit_consumer_requires_configured_root() -> None:
    with pytest.raises(BulkStorageContractError, match="ROOT_REQUIRED"):
        resolve_bulk_storage_path("market-history", environ={})


@pytest.mark.unit
def test_explicit_consumer_resolves_only_canonical_subtree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "tools.storage.bulk_storage_contract._reject_reparse_ancestors", lambda _: None
    )
    result = resolve_bulk_storage_path(
        "replay-arvp", environ={BULK_STORAGE_ROOT_ENV: "Y:\\CDB-Storage"}
    )
    assert result == Path("Y:\\CDB-Storage\\replay-arvp")


@pytest.mark.unit
def test_reparse_ancestor_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tools.storage.bulk_storage_contract._is_reparse_point", lambda _: True
    )
    with pytest.raises(BulkStorageContractError, match="REPARSE_POINT"):
        validate_bulk_storage_root("Y:\\CDB-Storage")
