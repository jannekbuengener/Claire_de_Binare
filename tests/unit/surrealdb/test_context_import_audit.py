"""Unit tests for context import audit reports (#2075/#2076)."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

import pytest

from core.utils.clock import FixedClock
from tools.surrealdb.context_importer import (
    ALLOWED_CONTEXT_IMPORT_TABLES,
    AUDIT_SCHEMA_VERSION,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    FORBIDDEN_CONTEXT_IMPORT_TABLES,
    build_audit_report,
    build_import_plan,
    load_config,
    load_existing_records,
    main,
    reconcile_import_plan,
)


FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "surrealdb"
    / "context_importer"
)
EXPECTED_JSONL = (
    "repo_artifacts.jsonl",
    "doc_pages.jsonl",
    "doc_sections.jsonl",
    "doc_chunks.jsonl",
    "code_symbols.jsonl",
    "import_references.jsonl",
    "test_cases.jsonl",
    "config_references.jsonl",
    "doc_code_links.jsonl",
    "dependency_edges.jsonl",
    "evidence_refs.jsonl",
    "claims.jsonl",
    "decision_events.jsonl",
    "agent_memories.jsonl",
)
FIXED_AT = "2026-05-02T10:11:12Z"
FIXED_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _copy_valid_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "input"
    shutil.copytree(FIXTURE_ROOT / "valid_minimal", target)
    return target


def _read_json(capsys) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out.strip())


def _write_local_dev_config(path: Path) -> Path:
    forbidden = sorted(FORBIDDEN_CONTEXT_IMPORT_TABLES)
    allowed = sorted(ALLOWED_CONTEXT_IMPORT_TABLES)
    body = (
        "schema_version: context-import-local/v0\n"
        "surreal_url: ws://127.0.0.1:8000/rpc\n"
        "namespace: cdb_ctx\n"
        "database: context\n"
        "auth_mode: none\n"
        "timeout: 5\n"
        "allow_apply_default: false\n"
        "allowed_tables:\n"
        + "".join(f"  - {table}\n" for table in allowed)
        + "forbidden_tables:\n"
        + "".join(f"  - {table}\n" for table in forbidden)
    )
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.unit
def test_audit_schema_version_constant_is_pinned() -> None:
    assert AUDIT_SCHEMA_VERSION == "context-import-audit/v0"


@pytest.mark.unit
def test_build_dry_run_audit_report_is_deterministic(tmp_path: Path) -> None:
    input_dir = _copy_valid_fixture(tmp_path)
    plan = build_import_plan(input_dir, "fixture-run-1")
    reconcile = reconcile_import_plan(plan, load_existing_records(None))
    clock = FixedClock(datetime(2026, 5, 2, 10, 11, 12, tzinfo=timezone.utc))

    first = build_audit_report(
        mode="dry-run",
        input_dir=input_dir,
        run_id="fixture-run-1",
        git_commit=FIXED_COMMIT,
        namespace="cdb_ctx",
        database="context",
        clock=clock,
        duration_ms=123,
        reconcile_report=reconcile,
    ).to_payload()
    second = build_audit_report(
        mode="dry-run",
        input_dir=input_dir,
        run_id="fixture-run-1",
        git_commit=FIXED_COMMIT,
        namespace="cdb_ctx",
        database="context",
        clock=clock,
        duration_ms=123,
        reconcile_report=reconcile,
    ).to_payload()

    assert first == second
    assert first["schema_version"] == AUDIT_SCHEMA_VERSION
    assert first["mode"] == "dry-run"
    assert first["generated_at"] == FIXED_AT
    assert first["duration_ms"] == 123
    assert first["git_commit"] == FIXED_COMMIT
    assert first["planned_counts"] == {
        "creates": 10,
        "skips": 0,
        "tombstones": 0,
        "updates": 0,
    }
    assert first["actual_counts"] == {
        "creates": 0,
        "skips": 0,
        "tombstones": 0,
        "updates": 0,
    }
    assert first["payload_policy"] == "metadata-only; no record payloads serialized"


@pytest.mark.unit
def test_dry_run_cli_writes_json_and_markdown_audit(tmp_path: Path, monkeypatch) -> None:
    input_dir = _copy_valid_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "dry-run",
            "--input-dir",
            str(input_dir),
            "--run-id",
            "fixture-run-1",
            "--namespace",
            "cdb_ctx",
            "--database",
            "context",
            "--audit-output",
            "artifacts/audit/context-import.json",
            "--git-commit",
            FIXED_COMMIT,
            "--audit-generated-at",
            FIXED_AT,
            "--audit-duration-ms",
            "77",
        ]
    )

    assert exit_code == EXIT_OK
    audit_json = tmp_path / "artifacts" / "audit" / "context-import.json"
    audit_md = tmp_path / "artifacts" / "audit" / "context-import.md"
    payload = json.loads(audit_json.read_text(encoding="utf-8"))
    markdown = audit_md.read_text(encoding="utf-8")
    assert payload["command"] == "audit"
    assert payload["mode"] == "dry-run"
    assert payload["namespace"] == "cdb_ctx"
    assert payload["database"] == "context"
    assert "## Planned Counts" in markdown
    assert "`creates`: `10`" in markdown


@pytest.mark.unit
def test_apply_cli_writes_audit_with_actual_counts(tmp_path: Path, monkeypatch) -> None:
    input_dir = _copy_valid_fixture(tmp_path)
    config = _write_local_dev_config(tmp_path / "config.yaml")
    existing = tmp_path / "existing.json"
    existing.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "payload": {"legacy_field": "preserve-me", "title": "Old page"},
                        "record_id": "doc_chunk:stale",
                        "schema_version": "context-importer/v0",
                        "table": "doc_chunk",
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config),
            "--input-dir",
            str(input_dir),
            "--existing-records",
            str(existing),
            "--run-id",
            "fixture-run-1",
            "--audit-output",
            "artifacts/audit/apply.json",
            "--git-commit",
            FIXED_COMMIT,
            "--audit-generated-at",
            FIXED_AT,
            "--audit-duration-ms",
            "88",
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(
        (tmp_path / "artifacts" / "audit" / "apply.json").read_text(encoding="utf-8")
    )
    assert payload["mode"] == "apply"
    assert payload["actual_counts"] == {
        "creates": 10,
        "skips": 0,
        "tombstones": 1,
        "updates": 0,
    }
    assert payload["planned_counts"] == {
        "creates": 10,
        "skips": 0,
        "tombstones": 1,
        "updates": 0,
    }


@pytest.mark.unit
def test_audit_report_includes_blocking_findings_without_secret_leak(
    tmp_path: Path, capsys
) -> None:
    input_dir = _copy_valid_fixture(tmp_path)
    config_ref = input_dir / "config_references.jsonl"
    record = json.loads(config_ref.read_text(encoding="utf-8"))
    record["api_key"] = "api_key=SHOULD_NOT_LEAK_123456"
    config_ref.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    exit_code = main(
        [
            "audit",
            "--audit-mode",
            "dry-run",
            "--input-dir",
            str(input_dir),
            "--run-id",
            "fixture-run-1",
            "--git-commit",
            FIXED_COMMIT,
            "--audit-generated-at",
            FIXED_AT,
        ]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    raw = capsys.readouterr().out
    assert "SHOULD_NOT_LEAK" not in raw
    payload = json.loads(raw)
    assert payload["status"] == "blocked"
    assert payload["blocking_findings"]
    assert any(
        finding["code"] == "secret_like_value_in_jsonl"
        for finding in payload["blocking_findings"]
    )


@pytest.mark.unit
def test_audit_output_path_must_remain_whitelisted(tmp_path: Path, capsys) -> None:
    input_dir = _copy_valid_fixture(tmp_path)

    exit_code = main(
        [
            "dry-run",
            "--input-dir",
            str(input_dir),
            "--audit-output",
            "reports/audit.json",
        ]
    )

    assert exit_code == 5
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_valid_minimal_fixture_contains_all_expected_jsonl_files() -> None:
    fixture_dir = FIXTURE_ROOT / "valid_minimal"
    assert sorted(path.name for path in fixture_dir.glob("*.jsonl")) == sorted(
        EXPECTED_JSONL
    )


@pytest.mark.unit
def test_fixture_paths_cover_plan_reconcile_tombstone_without_docker(
    tmp_path: Path,
) -> None:
    input_dir = _copy_valid_fixture(tmp_path)
    plan = build_import_plan(input_dir, "fixture-run-1")
    reconcile = reconcile_import_plan(
        plan, load_existing_records(FIXTURE_ROOT / "existing_mixed.json")
    )
    config = load_config(_write_local_dev_config(tmp_path / "config.yaml"))

    assert plan.status == "planned"
    assert reconcile.action_counts()["tombstone_candidates"] == 1
    assert config.namespace == "cdb_ctx"


@pytest.mark.unit
def test_apply_audit_clock_does_not_affect_tombstone_at(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: ``--audit-generated-at`` must only drive the audit report's
    ``generated_at`` and must never propagate into apply payload timestamps
    such as ``tombstoned_at``. Wiring the audit clock into
    ``execute_context_apply`` would let an operator backdate or forward-date
    applied tombstone data, turning an audit-only determinism flag into a
    data-mutation control. PR #2249 review feedback.
    """

    input_dir = _copy_valid_fixture(tmp_path)
    config = _write_local_dev_config(tmp_path / "config.yaml")
    existing = tmp_path / "existing.json"
    existing.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "payload": {"legacy_field": "preserve-me", "title": "Old page"},
                        "record_id": "doc_chunk:stale",
                        "schema_version": "context-importer/v0",
                        "table": "doc_chunk",
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    # Backdated audit clock: if the bug regresses, applied tombstones would
    # be timestamped to 1990 instead of "now".
    backdated_audit_at = "1990-01-01T00:00:00Z"

    exit_code = main(
        [
            "apply",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(config),
            "--input-dir",
            str(input_dir),
            "--existing-records",
            str(existing),
            "--run-id",
            "fixture-run-1",
            "--report-output",
            "artifacts/apply/report.json",
            "--audit-output",
            "artifacts/audit/apply.json",
            "--git-commit",
            FIXED_COMMIT,
            "--audit-generated-at",
            backdated_audit_at,
            "--audit-duration-ms",
            "12",
        ]
    )

    assert exit_code == EXIT_OK

    # 1) Audit report uses the injected audit clock for ``generated_at``.
    audit_payload = json.loads(
        (tmp_path / "artifacts" / "audit" / "apply.json").read_text(encoding="utf-8")
    )
    assert audit_payload["generated_at"] == backdated_audit_at
    assert audit_payload["mode"] == "apply"

    # 2) The apply report must NOT carry that backdated timestamp on any
    #    tombstone payload. ``tombstoned_at`` must be a real, non-injected
    #    ISO8601 UTC value (runtime SystemClock).
    apply_payload = json.loads(
        (tmp_path / "artifacts" / "apply" / "report.json").read_text(encoding="utf-8")
    )
    tombstones = [
        result
        for result in apply_payload["results"]
        if result["op"] == "tombstone"
    ]
    assert tombstones, "expected at least one applied tombstone result"
    for result in tombstones:
        assert result["status"] == "applied"
        ts = result["tombstoned_at"]
        assert ts is not None
        assert ts != backdated_audit_at, (
            "audit clock must not propagate into applied tombstone payload"
        )
        # Must still be a parseable ISO8601 UTC timestamp (microseconds optional).
        assert ts.endswith("Z"), ts
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None


@pytest.mark.unit
def test_audit_output_with_md_suffix_keeps_json_artifact_distinct(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: when ``--audit-output`` already ends in ``.md`` the JSON
    artifact must not be silently overwritten by the markdown render. The
    markdown sibling path must always be distinct from the JSON path so that
    downstream consumers expecting machine-readable audit output keep
    receiving valid JSON. PR #2249 review feedback.
    """

    input_dir = _copy_valid_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "dry-run",
            "--input-dir",
            str(input_dir),
            "--run-id",
            "fixture-run-1",
            "--namespace",
            "cdb_ctx",
            "--database",
            "context",
            "--audit-output",
            "artifacts/audit/context-import.md",
            "--git-commit",
            FIXED_COMMIT,
            "--audit-generated-at",
            FIXED_AT,
            "--audit-duration-ms",
            "5",
        ]
    )

    assert exit_code == EXIT_OK
    json_path = tmp_path / "artifacts" / "audit" / "context-import.md"
    md_path = tmp_path / "artifacts" / "audit" / "context-import.md.md"
    assert json_path.exists(), "JSON audit artifact missing"
    assert md_path.exists(), "Markdown audit artifact missing or collapsed onto JSON path"
    # JSON artifact must be machine-readable JSON, not Markdown.
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry-run"
    assert payload["generated_at"] == FIXED_AT
    # Markdown artifact must be human-readable Markdown, not JSON.
    md_text = md_path.read_text(encoding="utf-8")
    assert md_text.startswith("# context_importer audit:")
    with pytest.raises(json.JSONDecodeError):
        json.loads(md_text)
