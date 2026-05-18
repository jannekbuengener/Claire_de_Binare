"""Unit tests for dry-run Context Importer reconcile (#2072)."""

from __future__ import annotations

from dataclasses import replace
import json
import socket
from pathlib import Path

import pytest

from tools.surrealdb.context_importer import (
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    EXIT_WRITE_DENIED,
    EXPECTED_JSONL_FILES,
    INDEXER_SCHEMA_VERSION,
    ReadOnlyExistingRecords,
    build_import_plan,
    main,
    reconcile_import_plan,
)

HASH = "c" * 64
RUN_ID = "run-2072"


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def _base_record(**updates) -> dict:
    record = {"schema_version": INDEXER_SCHEMA_VERSION, "run_id": RUN_ID}
    record.update(updates)
    return record


def _write_jsonl(input_dir: Path, artifact: str, records: list[dict]) -> None:
    path = input_dir / EXPECTED_JSONL_FILES[artifact]
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _valid_records() -> dict[str, list[dict]]:
    return {
        "repo_artifacts": [
            _base_record(
                artifact_id="artifact-doc",
                source_path="docs/example.md",
                file_type="markdown",
                raw_sha256=HASH,
                normalized_sha256=HASH,
                source_hash=HASH,
                integrity_algo="sha256",
                size_bytes=12,
                sensitivity="internal_context",
            )
        ],
        "doc_pages": [
            _base_record(
                page_id="page-example",
                source_path="docs/example.md",
                source_hash=HASH,
                title="Example",
                doc_format="markdown",
            )
        ],
        "doc_sections": [
            _base_record(
                section_id="section-example",
                page_id="page-example",
                source_path="docs/example.md",
                source_hash=HASH,
                heading="Example",
                heading_path=["Example"],
                section_level=1,
                section_index=0,
            )
        ],
        "doc_chunks": [
            _base_record(
                chunk_id="chunk-example",
                page_id="page-example",
                section_id="section-example",
                source_path="docs/example.md",
                source_hash=HASH,
                heading_path=["Example"],
                chunk_index=0,
                content="safe context",
                content_hash=HASH,
            )
        ],
        "code_symbols": [
            _base_record(
                symbol_id="symbol-example",
                source_path="tools/example.py",
                source_hash=HASH,
                symbol_type="function",
                name="example",
                qualified_name="example",
            )
        ],
        "import_references": [
            _base_record(
                import_id="import-json",
                source_path="tools/example.py",
                source_hash=HASH,
                module="json",
            )
        ],
        "test_cases": [
            _base_record(
                test_id="test-example",
                source_path="tests/test_example.py",
                source_hash=HASH,
                symbol_id="symbol-example",
                name="test_example",
            )
        ],
        "config_references": [
            _base_record(
                config_ref_id="config-safe",
                source_path="infrastructure/config/example.yaml",
                source_hash=HASH,
                config_key="safe_key",
                config_value="safe-value",
                sensitive=False,
            )
        ],
        "doc_code_links": [
            _base_record(
                link_id="link-example",
                source_path="docs/example.md",
                source_hash=HASH,
                target_symbol="example",
                source_chunk_id="chunk-example",
            )
        ],
        "dependency_edges": [
            _base_record(
                edge_id="edge-example",
                from_id="symbol-example",
                to_id="import-json",
                edge_type="imports",
            )
        ],
        "evidence_refs": [
            _base_record(
                evidence_id="ev-001",
                created_at="2026-05-18T00:00:00Z",
            )
        ],
        "claims": [
            _base_record(
                claim_id="claim-001",
                created_at="2026-05-18T00:00:00Z",
            )
        ],
        "decision_events": [
            _base_record(
                decision_id="decision-001",
                created_at="2026-05-18T00:00:00Z",
            )
        ],
        "agent_memories": [
            _base_record(
                memory_id="memory-001",
                created_at="2026-05-18T00:00:00Z",
            )
        ],
    }


def _write_valid_artifacts(input_dir: Path) -> None:
    for artifact, records in _valid_records().items():
        _write_jsonl(input_dir, artifact, records)


def _write_existing(path: Path, records: list[dict]) -> None:
    path.write_text(json.dumps({"records": records}, sort_keys=True), encoding="utf-8")


def _payload_hash_by_record_id(payload: dict) -> dict[str, str]:
    return {action["record_id"]: action["payload_hash"] for action in payload["actions"]}


@pytest.mark.unit
def test_dry_run_empty_existing_state_creates_candidates(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(["dry-run", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "reconciled"
    assert payload["surrealdb_writes"] == "disabled"
    assert payload["counts"]["creates"] == 14
    assert payload["counts"]["skips"] == 0
    assert all(action["action"] == "create" for action in payload["actions"])


@pytest.mark.unit
def test_dry_run_identical_records_skip(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    assert main(["plan", "--input-dir", str(tmp_path)]) == EXIT_OK
    plan_payload = _read_json(capsys)
    hashes = _payload_hash_by_record_id(plan_payload)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "doc_page",
                "record_id": "doc_page:page-example",
                "payload_hash": hashes["doc_page:page-example"],
                "schema_version": "context-importer/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    skip = next(action for action in payload["actions"] if action["action"] == "skip")
    assert skip["record_id"] == "doc_page:page-example"
    assert skip["reason"] == "record_same"
    assert payload["counts"]["skips"] == 1


@pytest.mark.unit
def test_dry_run_changed_record_is_update_candidate(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "doc_page",
                "record_id": "doc_page:page-example",
                "payload_hash": "d" * 64,
                "schema_version": "context-importer/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    update = next(
        action for action in payload["actions"] if action["action"] == "update_candidate"
    )
    assert update["record_id"] == "doc_page:page-example"
    assert update["reason"] == "record_changed"
    assert payload["counts"]["update_candidates"] == 1


@pytest.mark.unit
def test_dry_run_existing_record_missing_from_plan_is_tombstone_candidate(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "doc_page",
                "record_id": "doc_page:stale",
                "payload_hash": "e" * 64,
                "schema_version": "context-importer/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    tombstone = next(
        action
        for action in payload["actions"]
        if action["action"] == "tombstone_candidate"
    )
    assert tombstone["record_id"] == "doc_page:stale"
    assert tombstone["reason"] == "record_removed_from_snapshot"
    assert payload["counts"]["tombstone_candidates"] == 1


@pytest.mark.unit
def test_dry_run_forbidden_table_blocks(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "orders",
                "record_id": "orders:1",
                "payload_hash": "f" * 64,
                "schema_version": "context-importer/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "blocked"
    assert payload["counts"]["blocking"] == 1
    assert any(finding["code"] == "forbidden_table" for finding in payload["findings"])


@pytest.mark.unit
def test_dry_run_schema_mismatch_blocks(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "doc_page",
                "record_id": "doc_page:page-example",
                "payload_hash": "a" * 64,
                "schema_version": "other/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert any(finding["code"] == "schema_mismatch" for finding in payload["findings"])
    assert payload["counts"]["blocking"] == 1


@pytest.mark.unit
def test_dry_run_rejects_duplicate_existing_record_ids(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "doc_page",
                "record_id": "doc_page:page-example",
                "payload_hash": "a" * 64,
                "schema_version": "context-importer/v0",
            },
            {
                "table": "doc_page",
                "record_id": "doc_page:page-example",
                "payload_hash": "b" * 64,
                "schema_version": "context-importer/v0",
            },
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "error"
    assert payload["error"] == "EXISTING_RECORDS_VALIDATION_ERROR"
    assert "duplicate existing record_id" in payload["message"]
    assert "aaaaaaaa" not in payload["message"]
    assert "bbbbbbbb" not in payload["message"]


@pytest.mark.unit
def test_dry_run_accepts_existing_record_id_with_matching_table(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "doc_page",
                "record_id": "doc_page:page-example",
                "payload_hash": "a" * 64,
                "schema_version": "context-importer/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "reconciled"
    assert any(action["action"] == "update_candidate" for action in payload["actions"])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("record_id", "expected_message"),
    [
        ("code_symbol:page-example", "matching table"),
        ("page-example", "matching table"),
        ("doc_page:", "matching table"),
        (123, "existing record_id must be a string"),
        (None, "existing record_id must be a string"),
    ],
)
def test_dry_run_rejects_existing_record_id_without_matching_table(
    tmp_path: Path, capsys, record_id, expected_message: str
) -> None:
    _write_valid_artifacts(tmp_path)
    existing = tmp_path / "existing.json"
    secret_payload = "secret-token-value-1234567890"
    raw_existing = {
        "table": "doc_page",
        "payload_hash": "a" * 64,
        "payload": {"secret": secret_payload},
        "schema_version": "context-importer/v0",
    }
    if record_id is not None:
        raw_existing["record_id"] = record_id
    _write_existing(existing, [raw_existing])

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "error"
    assert payload["error"] == "EXISTING_RECORDS_VALIDATION_ERROR"
    assert expected_message in payload["message"]
    assert secret_payload not in json.dumps(payload)
    assert "aaaaaaaa" not in json.dumps(payload)


@pytest.mark.unit
def test_dry_run_warning_count_excludes_blocking_plan_warnings(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    records = _valid_records()["doc_pages"]
    records[0]["source_path"] = "../secrets.md"
    _write_jsonl(tmp_path, "doc_pages", records)

    exit_code = main(["dry-run", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "blocked"
    assert payload["counts"]["blocking"] > 0
    assert payload["counts"]["warnings"] == 0
    assert any(finding["severity"] == "blocking" for finding in payload["findings"])


@pytest.mark.unit
def test_dry_run_preserves_import_plan_skip_actions(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    plan = build_import_plan(tmp_path)
    skipped_action = replace(
        plan.actions[0],
        action="skip",
        reason="duplicate record_id in validated input; first occurrence wins",
    )
    report = reconcile_import_plan(
        replace(plan, actions=(skipped_action,)),
        ReadOnlyExistingRecords(records=(), source="empty"),
    )
    payload = report.to_payload()

    assert payload["status"] == "reconciled"
    assert payload["actions"] == [
        {
            "action": "skip",
            "table": "repo_artifact",
            "record_id": "repo_artifact:artifact-doc",
            "source_ref": "docs/example.md",
            "reason": "duplicate record_id in validated input; first occurrence wins",
            "payload_hash": skipped_action.payload_hash,
            "existing_payload_hash": None,
        }
    ]
    assert payload["actions"][0]["reason"] == (
        "duplicate record_id in validated input; first occurrence wins"
    )
    assert payload["counts"]["creates"] == 0
    assert payload["counts"]["skips"] == 1
    assert payload["counts"]["update_candidates"] == 0


@pytest.mark.unit
def test_dry_run_duplicate_plan_skip_does_not_emit_second_candidate(
    tmp_path: Path, capsys
) -> None:
    records = _valid_records()
    records["doc_pages"] = records["doc_pages"] * 2
    for artifact, items in records.items():
        _write_jsonl(tmp_path, artifact, items)

    exit_code = main(["dry-run", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    page_actions = [
        action for action in payload["actions"] if action["record_id"] == "doc_page:page-example"
    ]
    assert len(page_actions) == 1
    assert page_actions[0]["action"] == "create"
    assert payload["counts"]["creates"] == 14
    assert payload["counts"]["skips"] == 0
    assert payload["counts"]["update_candidates"] == 0


@pytest.mark.unit
def test_dry_run_plan_skip_still_blocks_on_schema_mismatch(
    tmp_path: Path, capsys
) -> None:
    records = _valid_records()
    records["repo_artifacts"] = records["repo_artifacts"] * 2
    for artifact, items in records.items():
        _write_jsonl(tmp_path, artifact, items)
    existing = tmp_path / "existing.json"
    _write_existing(
        existing,
        [
            {
                "table": "repo_artifact",
                "record_id": "repo_artifact:artifact-doc",
                "payload_hash": "a" * 64,
                "schema_version": "other/v0",
            }
        ],
    )

    exit_code = main(
        ["dry-run", "--input-dir", str(tmp_path), "--existing-records", str(existing)]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert any(finding["code"] == "schema_mismatch" for finding in payload["findings"])


@pytest.mark.unit
def test_dry_run_preserves_plan_warning_severity_and_counts(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    doc_chunks = tmp_path / EXPECTED_JSONL_FILES["doc_chunks"]
    doc_chunks.write_text(doc_chunks.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    records = _valid_records()["doc_pages"]
    records[0]["source_path"] = "../secrets.md"
    _write_jsonl(tmp_path, "doc_pages", records)

    exit_code = main(["dry-run", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    finding_severities = {finding["code"]: finding["severity"] for finding in payload["findings"]}
    assert finding_severities["forbidden_source_path"] == "blocking"
    assert finding_severities["jsonl_blank_line"] == "warning"
    assert payload["counts"]["blocking"] >= 1
    assert payload["counts"]["warnings"] == 1
    assert "secret-token-value" not in json.dumps(payload)


@pytest.mark.unit
def test_dry_run_blocked_plan_does_not_load_existing_records(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    records = _valid_records()["doc_pages"]
    records[0]["source_path"] = "../secrets.md"
    _write_jsonl(tmp_path, "doc_pages", records)
    missing_existing = tmp_path / "missing-existing.json"

    exit_code = main(
        [
            "dry-run",
            "--input-dir",
            str(tmp_path),
            "--existing-records",
            str(missing_existing),
        ]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "blocked"
    assert payload["existing_records_source"] == "empty"
    assert any(
        finding["code"] == "forbidden_source_path"
        for finding in payload["findings"]
    )
    assert "existing records fixture not found" not in json.dumps(payload)


@pytest.mark.unit
def test_dry_run_makes_no_writes_and_opens_no_socket(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _boom(*args, **kwargs):  # pragma: no cover - safety net
        raise AssertionError("dry-run reconcile must not open network sockets")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket.socket, "connect_ex", _boom)

    exit_code = main(
        [
            "dry-run",
            "--input-dir",
            str(tmp_path),
            "--surreal-url",
            "ws://example.invalid:8000/rpc",
        ]
    )

    assert exit_code == EXIT_OK
    assert not (tmp_path / "artifacts").exists()
    payload = _read_json(capsys)
    assert payload["surrealdb_writes"] == "disabled"


@pytest.mark.unit
def test_dry_run_report_is_deterministic_and_reviewable(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    monkeypatch.chdir(tmp_path)

    args = [
        "dry-run",
        "--input-dir",
        str(tmp_path),
        "--format",
        "markdown",
        "--report-output",
        "artifacts/reconcile.md",
    ]
    assert main(args) == EXIT_OK
    first = (tmp_path / "artifacts" / "reconcile.md").read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(args) == EXIT_OK
    second = (tmp_path / "artifacts" / "reconcile.md").read_text(encoding="utf-8")

    assert first == second
    assert first.startswith("# context_importer: dry-run reconcile")
    assert "## Counts" in first
    assert "## Actions" in first


@pytest.mark.unit
def test_dry_run_does_not_echo_secret_values(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    secret_value = "secret-token-value-1234567890"
    records = _valid_records()["config_references"]
    records[0]["access_token"] = secret_value
    _write_jsonl(tmp_path, "config_references", records)

    exit_code = main(["dry-run", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    out = capsys.readouterr().out
    assert secret_value not in out
    payload = json.loads(out)
    assert payload["status"] == "blocked"


@pytest.mark.unit
def test_apply_remains_hard_blocked_for_dry_run(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(["dry-run", "--input-dir", str(tmp_path), "--apply"])

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
