"""Regression coverage for #4465 path-safety hardening residuals (#4526)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import tools.storage.log_archive as log_archive
from tools.storage.log_archive import (
    LogArchiveError,
    apply_log_archive_plan,
    build_log_archive_plan,
    main,
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
        log_archive,
        "resolve_bulk_storage_path",
        lambda _subtree, environ=None: destination.parent,
    )
    return source, destination


def _write(source: Path, name: str, content: str = "{}\n") -> Path:
    path = source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.unit
@pytest.mark.parametrize(
    ("component", "expected"),
    [
        ("_quarantine", True),
        ("_Quarantine", True),
        ("_QUARANTINE", True),
        ("_archive_20260424", True),
        ("_ARCHIVE_old", True),
        ("archive_not_prefixed", False),
        ("quarantine", False),
        ("nested", False),
    ],
)
def test_excluded_components_honour_windows_normcase(
    component: str, expected: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(log_archive.os.path, "normcase", lambda value: value.lower())

    assert log_archive._is_excluded_component(component) is expected


@pytest.mark.unit
def test_case_variant_quarantine_and_archive_subtrees_are_excluded_under_normcase(
    archive_roots: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _destination = archive_roots
    monkeypatch.setattr(log_archive.os.path, "normcase", lambda value: value.lower())
    ordinary = _write(source, "events_20260714.jsonl", "ordinary\n")
    _write(source / "_Quarantine", "events_20260714.jsonl", "quarantined\n")
    _write(source / "_ARCHIVE_20260424", "events_20260714.jsonl", "archived\n")

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert [entry["relative_path"] for entry in plan["entries"]] == [ordinary.name]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("relative_path", "reason"),
    [
        ("C:events_20260714.jsonl", "APPLY_RELATIVE_PATH_INVALID"),
        ("nested/C:escape/events_20260714.jsonl", "APPLY_RELATIVE_PATH_INVALID"),
        ("../events_20260714.jsonl", "APPLY_RELATIVE_PATH_INVALID"),
        ("/abs/events_20260714.jsonl", "APPLY_RELATIVE_PATH_INVALID"),
        ("", "APPLY_RELATIVE_PATH_INVALID"),
        ("foo/../events_20260714.jsonl", "APPLY_RELATIVE_PATH_INVALID"),
        ("_quarantine/events_20260714.jsonl", "APPLY_EXCLUDED_SUBTREE"),
        ("_archive_old/events_20260714.jsonl", "APPLY_EXCLUDED_SUBTREE"),
        ("not_an_event.jsonl", "APPLY_CANDIDATE_NAME_INVALID"),
        ("events_20260714.txt", "APPLY_CANDIDATE_NAME_INVALID"),
    ],
)
def test_safe_relative_path_rejects_escape_and_name_payloads(
    relative_path: str, reason: str
) -> None:
    with pytest.raises(LogArchiveError, match=reason):
        log_archive._safe_relative_path(relative_path)


@pytest.mark.unit
def test_apply_rejects_drive_relative_relative_path_before_any_mutation(
    archive_roots: tuple[Path, Path], tmp_path: Path
) -> None:
    source, destination = archive_roots
    file = _write(source, "events_20260714.jsonl", "bound\n")
    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)
    plan["entries"][0]["relative_path"] = "C:events_20260714.jsonl"
    plan["plan_fingerprint"] = log_archive._plan_fingerprint(plan)

    result = apply_log_archive_plan(
        plan, plan["plan_fingerprint"], tmp_path / "evidence.json"
    )

    assert result["result"] == "BLOCKED"
    assert result["failure_reason"] == "APPLY_RELATIVE_PATH_INVALID"
    assert file.exists()
    assert file.read_text(encoding="utf-8") == "bound\n"
    assert not (destination / file.name).exists()


@pytest.mark.unit
def test_missing_destination_root_holds_plan_and_blocks_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "events"
    destination = tmp_path / "bulk" / "logs" / "events"
    source.mkdir(parents=True)
    # Destination intentionally absent — plan must HOLD before any apply.
    monkeypatch.setattr(
        log_archive,
        "resolve_bulk_storage_path",
        lambda _subtree, environ=None: destination.parent,
    )
    file = _write(source, "events_20260714.jsonl", "cold\n")

    plan = build_log_archive_plan(source, environ=ENV, as_of_utc=AS_OF)

    assert plan["destination_root_exists"] is False
    assert plan["hold_reasons"] == ["DESTINATION_ROOT_REQUIRED"]

    result = apply_log_archive_plan(
        plan, plan["plan_fingerprint"], tmp_path / "evidence.json"
    )

    # Apply-time root validation fail-closes before the plan-hold branch;
    # either gate must leave source untouched and create no destination tree.
    assert result["result"] == "BLOCKED"
    assert result["failure_reason"] == "APPLY_ROOT_REQUIRED"
    assert file.exists()
    assert not destination.exists()


@pytest.mark.unit
def test_cli_rejects_non_canonical_source_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "events"
    source.mkdir()
    _write(source, "events_20260714.jsonl")

    exit_code = main(
        [
            "plan",
            "--source-root",
            str(source),
            "--as-of-utc",
            "2026-08-14T12:00:00+00:00",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload == {
        "status": "BLOCKED",
        "reason_code": "SOURCE_ROOT_NON_CANONICAL",
    }
