"""Safety contract tests for the #4422 event-log archive planner."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.storage.log_archive import (
    LogArchiveError,
    build_log_archive_plan,
    verify_copied_file,
    verify_planned_source,
)


AS_OF = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
ENV = {"CDB_BULK_STORAGE_ROOT": "Y:\\CDB-Storage"}


@pytest.fixture
def archive_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    source = tmp_path / "events"
    destination = tmp_path / "bulk" / "logs" / "events"
    source.mkdir(parents=True)
    destination.mkdir(parents=True)
    monkeypatch.setattr(
        "tools.storage.log_archive.resolve_bulk_storage_path",
        lambda _subtree, environ=None: destination.parent,
    )
    return source, destination


def _write(source: Path, name: str, content: str = "{}\n") -> Path:
    path = source / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.unit
def test_cold_event_is_candidate_with_deterministic_fingerprint(
    archive_roots: tuple[Path, Path],
) -> None:
    source, _destination = archive_roots
    _write(source, "events_20260714.jsonl")

    first = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    second = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert first["entries"][0]["classification"] == "ARCHIVE_CANDIDATE"
    assert first["plan_fingerprint"] == second["plan_fingerprint"]


@pytest.mark.unit
@pytest.mark.parametrize("name", ["events_20260715.jsonl", "events_20260814.jsonl"])
def test_hot_and_todays_events_are_kept(
    archive_roots: tuple[Path, Path], name: str
) -> None:
    source, _destination = archive_roots
    _write(source, name)

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert plan["entries"][0]["classification"] == "KEEP_HOT"


@pytest.mark.unit
@pytest.mark.parametrize("name", ["unknown.jsonl", "_quarantine", "_archive_old", "paper_trading_2026.log"])
def test_unknown_and_paper_logs_are_excluded(
    archive_roots: tuple[Path, Path], name: str
) -> None:
    source, _destination = archive_roots
    _write(source, name)

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert plan["entries"][0]["classification"] == "EXCLUDE_UNKNOWN"


@pytest.mark.unit
@pytest.mark.parametrize("root", ["", "D:\\CDB-Storage", "Y:\\Worktrees\\Claire_de_Binare"])
def test_noncanonical_bulk_root_blocks(source_root: Path, root: str) -> None:
    source_root.mkdir()
    _write(source_root, "events_20260714.jsonl")

    with pytest.raises(LogArchiveError, match="BULK_STORAGE"):
        build_log_archive_plan(source_root, environ={"CDB_BULK_STORAGE_ROOT": root}, as_of_utc=AS_OF)


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    return tmp_path / "events"


@pytest.mark.unit
def test_reparse_source_is_blocked(
    archive_roots: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _destination = archive_roots
    _write(source, "events_20260714.jsonl")
    monkeypatch.setattr("tools.storage.log_archive._is_reparse_point", lambda _: True)

    with pytest.raises(LogArchiveError, match="REPARSE_POINT"):
        build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)


@pytest.mark.unit
def test_destination_collision_with_different_content_is_hold(
    archive_roots: tuple[Path, Path],
) -> None:
    source, destination = archive_roots
    _write(source, "events_20260714.jsonl", "source\n")
    _write(destination, "events_20260714.jsonl", "other\n")

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert plan["entries"][0]["classification"] == "HOLD"
    assert plan["entries"][0]["reason_code"] == "DESTINATION_COLLISION_HASH_MISMATCH"


@pytest.mark.unit
def test_identical_destination_is_resumable_and_source_integrity_is_verified(
    archive_roots: tuple[Path, Path],
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "same\n")
    _write(destination, file.name, "same\n")

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    entry = plan["entries"][0]

    assert entry["classification"] == "ARCHIVE_CANDIDATE"
    assert entry["destination_state"] == "RESUMABLE_IDENTICAL"
    verify_planned_source(file, entry)
    verify_copied_file(file, destination / file.name)


@pytest.mark.unit
def test_changed_source_or_copy_hash_mismatch_blocks_before_any_unlink(
    archive_roots: tuple[Path, Path],
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "before\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    entry = plan["entries"][0]
    file.write_text("after\n", encoding="utf-8")
    _write(destination, file.name, "mismatch\n")

    with pytest.raises(LogArchiveError, match="SOURCE_CHANGED_AFTER_PLANNING"):
        verify_planned_source(file, entry)
    with pytest.raises(LogArchiveError, match="COPY_HASH_MISMATCH"):
        verify_copied_file(file, destination / file.name)
    assert file.exists()
