"""Extra regression coverage for #4422 archive delete/evidence safety."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import tools.storage.log_archive as log_archive

AS_OF = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
ENV = {"CDB_BULK_STORAGE_ROOT": "Y:\\CDB-Storage"}


def _setup_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    source = tmp_path / "events"
    destination = tmp_path / "bulk" / "logs" / "events"
    source.mkdir(parents=True)
    destination.mkdir(parents=True)
    source_file = source / "events_20260714.jsonl"
    source_file.write_text("original\n", encoding="utf-8")
    monkeypatch.setattr(
        log_archive,
        "resolve_bulk_storage_path",
        lambda _subtree, environ=None: destination.parent,
    )
    return source, destination, source_file


@pytest.mark.unit
def test_evidence_reparse_parent_blocks_before_journal_or_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, destination, source_file = _setup_roots(tmp_path, monkeypatch)
    plan = log_archive.build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    evidence_parent = tmp_path / "journal"
    evidence = evidence_parent / "result.json"

    monkeypatch.setattr(
        log_archive,
        "_is_reparse_point",
        lambda path: path == evidence_parent,
    )

    result = log_archive.apply_log_archive_plan(
        plan, plan["plan_fingerprint"], evidence
    )

    assert result["result"] == "BLOCKED"
    assert result["failure_reason"] == "LOG_ARCHIVE_REPARSE_POINT"
    assert source_file.read_text(encoding="utf-8") == "original\n"
    assert not (destination / source_file.name).exists()
    assert not evidence.exists()


@pytest.mark.unit
def test_source_change_after_delete_pending_journal_blocks_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, destination, source_file = _setup_roots(tmp_path, monkeypatch)
    plan = log_archive.build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    evidence = tmp_path / "evidence" / "result.json"
    real_write_evidence = log_archive._write_evidence

    def mutate_after_delete_pending(path: Path, payload: dict[str, object]) -> None:
        real_write_evidence(path, payload)
        if payload.get("apply_status") == "DELETE_PENDING":
            source_file.write_text("changed-after-journal\n", encoding="utf-8")

    monkeypatch.setattr(log_archive, "_write_evidence", mutate_after_delete_pending)

    result = log_archive.apply_log_archive_plan(
        plan, plan["plan_fingerprint"], evidence
    )

    assert result["result"] == "BLOCKED"
    assert result["failure_reason"] == "SOURCE_CHANGED_AFTER_PLANNING"
    assert result["deleted_source_count"] == 0
    assert source_file.exists()
    assert source_file.read_text(encoding="utf-8") == "changed-after-journal\n"
    assert (destination / source_file.name).exists()
