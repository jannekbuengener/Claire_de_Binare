"""Safety contract tests for the #4422 event-log archive planner."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from shutil import rmtree

import pytest

from tools.storage.log_archive import (
    LogArchiveError,
    apply_log_archive_plan,
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
    path.parent.mkdir(parents=True, exist_ok=True)
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
def test_archive_and_quarantine_subtrees_are_excluded_from_plan_and_fingerprint(
    archive_roots: tuple[Path, Path],
) -> None:
    source, _destination = archive_roots
    ordinary = _write(source, "events_20260714.jsonl", "ordinary\n")
    archived = _write(
        source / "nested" / "_archive_20260424_153327",
        "events_20260714.jsonl",
        "archived\n",
    )
    quarantined = _write(
        source / "deep" / "tree" / "_quarantine",
        "events_20260714.jsonl",
        "quarantined\n",
    )
    top_level_quarantine = _write(
        source / "_quarantine",
        "events_20260714.jsonl",
        "also quarantined\n",
    )
    archive_with_nested_quarantine = _write(
        source / "_archive_old" / "deeper" / "_quarantine",
        "events_20260714.jsonl",
        "also excluded\n",
    )

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    rmtree(source / "nested")
    rmtree(source / "deep")
    rmtree(source / "_quarantine")
    rmtree(source / "_archive_old")
    baseline = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert [entry["relative_path"] for entry in plan["entries"]] == [ordinary.name]
    assert sum(entry["size_bytes"] for entry in plan["entries"]) == ordinary.stat().st_size
    assert plan["plan_fingerprint"] == baseline["plan_fingerprint"]
    assert all(
        path.relative_to(source).as_posix()
        not in {entry["relative_path"] for entry in plan["entries"]}
        for path in (
            archived,
            quarantined,
            top_level_quarantine,
            archive_with_nested_quarantine,
        )
    )


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


def test_apply_requires_the_exact_expected_fingerprint(
    archive_roots: tuple[Path, Path], tmp_path: Path
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "bound\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    result = apply_log_archive_plan(plan, "wrong", tmp_path / "evidence.json")

    assert result["result"] == "BLOCKED"
    assert not (destination / file.name).exists()
    assert file.exists()


def test_apply_copies_verifies_then_deletes_and_writes_evidence_atomically(
    archive_roots: tuple[Path, Path], tmp_path: Path
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "bound\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    evidence = tmp_path / "evidence.json"

    result = apply_log_archive_plan(plan, plan["plan_fingerprint"], evidence)

    assert result["result"] == "SUCCESS"
    assert not file.exists()
    assert (destination / file.name).read_text(encoding="utf-8") == "bound\n"
    assert json.loads(evidence.read_text(encoding="utf-8"))["deleted_source_count"] == 1
    assert result["entries"][0]["disposition"] == "COPIED_VERIFIED_DELETED"


def test_apply_resume_requires_source_to_remain_bound(
    archive_roots: tuple[Path, Path], tmp_path: Path
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "same\n")
    _write(destination, file.name, "same\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    result = apply_log_archive_plan(plan, plan["plan_fingerprint"], tmp_path / "evidence.json")

    assert result["entries"][0]["disposition"] == "RESUMED_VERIFIED_DELETED"
    assert not file.exists()


def test_apply_holds_on_source_drift_without_delete(
    archive_roots: tuple[Path, Path], tmp_path: Path
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "before\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    file.write_text("after\n", encoding="utf-8")

    result = apply_log_archive_plan(plan, plan["plan_fingerprint"], tmp_path / "evidence.json")

    assert result["result"] == "BLOCKED"
    assert file.exists()
    assert not (destination / file.name).exists()
    assert result["entries"][0]["disposition"] == "HELD_SOURCE_DRIFT"


@pytest.mark.unit
def test_apply_refuses_to_mutate_when_initial_evidence_journal_cannot_be_written(
    archive_roots: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "bound\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("evidence unavailable")

    monkeypatch.setattr("tools.storage.log_archive._write_evidence", fail_write)

    with pytest.raises(LogArchiveError, match="EVIDENCE_JOURNAL_INIT_FAILED"):
        apply_log_archive_plan(plan, plan["plan_fingerprint"], tmp_path / "evidence.json")

    assert file.exists()
