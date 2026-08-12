"""Contract tests for the #4421 versioned replay/ARVP bulk-root resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.storage.replay_arvp_storage import (
    CONFLICTING_CANON_ROOTS,
    JUNCTION_CUTOVER_ROOTS,
    POSTGRES_HOLD_ROOTS,
    ReplayArvpStorageError,
    apply_replay_arvp_junction_cutover,
    resolve_replay_arvp_consumer_path,
    resolve_replay_arvp_payload_path,
)


def test_cutover_inventory_covers_49_safe_paths_and_excludes_hold() -> None:
    assert len(JUNCTION_CUTOVER_ROOTS) == 49
    assert len(POSTGRES_HOLD_ROOTS) == 2
    assert not set(JUNCTION_CUTOVER_ROOTS) & POSTGRES_HOLD_ROOTS
    assert not set(JUNCTION_CUTOVER_ROOTS) & CONFLICTING_CANON_ROOTS


@pytest.mark.unit
def test_conflicting_canon_path_resolves_under_explicit_bulk_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage.resolve_bulk_storage_path",
        lambda _subtree, environ=None: tmp_path / "replay-arvp",
    )

    assert resolve_replay_arvp_payload_path(
        "artifacts/replay_reports/run-1/report.json",
        environ={"CDB_BULK_STORAGE_ROOT": "Y:\\CDB-Storage"},
    ) == (tmp_path / "replay-arvp" / "replay_reports" / "run-1" / "report.json")


@pytest.mark.unit
def test_missing_explicit_bulk_root_fails_closed() -> None:
    with pytest.raises(ReplayArvpStorageError, match="BULK_STORAGE_ROOT_REQUIRED"):
        resolve_replay_arvp_payload_path("artifacts/replay_reports/run-1/report.json")


@pytest.mark.unit
def test_consumer_keeps_repo_canon_without_bulk_opt_in(tmp_path: Path) -> None:
    assert resolve_replay_arvp_consumer_path(
        tmp_path,
        "artifacts/replay_reports/run-1/report.json",
        environ={},
    ) == (tmp_path / "artifacts" / "replay_reports" / "run-1" / "report.json")


@pytest.mark.unit
def test_worktree_bulk_root_is_rejected() -> None:
    with pytest.raises(
        ReplayArvpStorageError, match="BULK_STORAGE_WORKTREE_ROOT_FORBIDDEN"
    ):
        resolve_replay_arvp_payload_path(
            "artifacts/replay_reports/run-1/report.json",
            environ={"CDB_BULK_STORAGE_ROOT": "Y:\\Worktrees\\Claire_de_Binare"},
        )


@pytest.mark.unit
def test_e_drive_root_is_rejected() -> None:
    with pytest.raises(ReplayArvpStorageError, match="BULK_STORAGE_ROOT_INVALID"):
        resolve_replay_arvp_payload_path(
            "artifacts/replay_reports/run-1/report.json",
            environ={"CDB_BULK_STORAGE_ROOT": "E:\\CDB_artifacts"},
        )


@pytest.mark.unit
def test_path_traversal_and_non_conflicting_roots_are_rejected() -> None:
    with pytest.raises(
        ReplayArvpStorageError, match="REPLAY_ARVP_PAYLOAD_PATH_INVALID"
    ):
        resolve_replay_arvp_payload_path(
            "artifacts/replay_reports/../market_data/payload.json",
            environ={"CDB_BULK_STORAGE_ROOT": "Y:\\CDB-Storage"},
        )
    with pytest.raises(
        ReplayArvpStorageError, match="REPLAY_ARVP_CANON_ROOT_UNMANAGED"
    ):
        resolve_replay_arvp_payload_path(
            "artifacts/market_data/payload.json",
            environ={"CDB_BULK_STORAGE_ROOT": "Y:\\CDB-Storage"},
        )


@pytest.mark.unit
def test_existing_junction_must_target_the_expected_y_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_root = tmp_path / "artifacts"
    destination = artifact_root / "safe"
    destination.mkdir(parents=True)
    target = tmp_path / "replay-arvp" / "safe"
    target.mkdir(parents=True)
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage.JUNCTION_CUTOVER_ROOTS", ("safe",)
    )
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage.resolve_bulk_storage_path",
        lambda _subtree, environ=None: tmp_path / "replay-arvp",
    )
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage._is_junction", lambda _: True
    )
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage._junction_targets_expected", lambda *_: False
    )

    with pytest.raises(
        ReplayArvpStorageError, match="REPLAY_ARVP_JUNCTION_TARGET_MISMATCH"
    ):
        apply_replay_arvp_junction_cutover(tmp_path, environ={})


@pytest.mark.unit
def test_junction_cutover_preflights_all_paths_before_creating_any(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target_root = tmp_path / "replay-arvp"
    (target_root / "first").mkdir(parents=True)
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage.JUNCTION_CUTOVER_ROOTS", ("first", "missing")
    )
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage.resolve_bulk_storage_path",
        lambda _subtree, environ=None: target_root,
    )
    run_calls: list[object] = []
    monkeypatch.setattr(
        "tools.storage.replay_arvp_storage.subprocess.run",
        lambda *args, **kwargs: run_calls.append((args, kwargs)),
    )

    with pytest.raises(
        ReplayArvpStorageError, match="REPLAY_ARVP_JUNCTION_TARGET_MISSING"
    ):
        apply_replay_arvp_junction_cutover(tmp_path, environ={})
    assert not run_calls
