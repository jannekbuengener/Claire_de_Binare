"""Unit tests for deterministic Context Importer plans (#2071)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.context_importer import (
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    EXIT_WRITE_DENIED,
    EXPECTED_JSONL_FILES,
    INDEXER_SCHEMA_VERSION,
    main,
)

HASH = "b" * 64
RUN_ID = "run-2071"


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


@pytest.mark.unit
def test_plan_generates_deterministic_create_actions(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(["plan", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "planned"
    assert payload["implemented"] is True
    assert payload["surrealdb_connection"] == "disabled"
    assert payload["has_blocking_validation_findings"] is False
    assert payload["action_counts"] == {"create": 14}
    assert payload["import_order"] == [
        "repo_artifact",
        "doc_page",
        "doc_section",
        "doc_chunk",
        "code_symbol",
        "import_reference",
        "test_case",
        "config_reference",
        "doc_code_link",
        "dependency_edge",
        "evidence_ref",
        "claim",
        "decision_event",
        "agent_memory",
    ]
    assert [action["record_id"] for action in payload["actions"]] == [
        "repo_artifact:artifact-doc",
        "doc_page:page-example",
        "doc_section:section-example",
        "doc_chunk:chunk-example",
        "code_symbol:symbol-example",
        "import_reference:import-json",
        "test_case:test-example",
        "config_reference:config-safe",
        "doc_code_link:link-example",
        "dependency_edge:edge-example",
        "evidence_ref:ev-001",
        "claim:claim-001",
        "decision_event:decision-001",
        "agent_memory:memory-001",
    ]
    section_action = payload["actions"][2]
    assert section_action["depends_on"] == ["doc_page:page-example"]
    chunk_action = payload["actions"][3]
    assert chunk_action["depends_on"] == [
        "doc_page:page-example",
        "doc_section:section-example",
    ]
    assert all(len(action["payload_hash"]) == 64 for action in payload["actions"])


@pytest.mark.unit
def test_plan_output_is_stable_for_same_input(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    assert main(["plan", "--input-dir", str(tmp_path)]) == EXIT_OK
    first = capsys.readouterr().out
    assert main(["plan", "--input-dir", str(tmp_path)]) == EXIT_OK
    second = capsys.readouterr().out

    assert first == second


@pytest.mark.unit
def test_plan_blocks_actions_when_validation_blocks(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    records = _valid_records()["doc_pages"]
    records[0]["source_path"] = "../secrets.md"
    _write_jsonl(tmp_path, "doc_pages", records)

    exit_code = main(["plan", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "blocked"
    assert payload["has_blocking_validation_findings"] is True
    assert payload["actions"] == []
    assert payload["action_counts"] == {}
    assert any(
        warning["code"] == "forbidden_source_path" and warning["severity"] == "blocking"
        for warning in payload["warnings"]
    )


@pytest.mark.unit
def test_plan_marks_duplicate_input_record_as_skip(tmp_path: Path, capsys) -> None:
    records = _valid_records()
    records["repo_artifacts"] = records["repo_artifacts"] * 2
    for artifact, items in records.items():
        _write_jsonl(tmp_path, artifact, items)

    exit_code = main(["plan", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    repo_actions = [
        action for action in payload["actions"] if action["table"] == "repo_artifact"
    ]
    assert [action["action"] for action in repo_actions] == ["create", "skip"]
    assert payload["action_counts"] == {"create": 14, "skip": 1}


@pytest.mark.unit
def test_plan_markdown_report_output_is_written_under_whitelist(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _write_valid_artifacts(input_dir)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "plan",
            "--input-dir",
            str(input_dir),
            "--format",
            "markdown",
            "--report-output",
            "artifacts/plan.md",
        ]
    )

    assert exit_code == EXIT_OK
    stdout = capsys.readouterr().out
    assert stdout.startswith("# context_importer: plan")
    report = tmp_path / "artifacts" / "plan.md"
    assert report.exists()
    assert report.read_text(encoding="utf-8").startswith("# context_importer: plan")


@pytest.mark.unit
def test_plan_report_output_outside_whitelist_is_rejected(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(
        ["plan", "--input-dir", str(tmp_path), "--report-output", "etc/plan.json"]
    )

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_plan_includes_wave14_artifacts(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    assert main(["plan", "--input-dir", str(tmp_path)]) == EXIT_OK
    payload = _read_json(capsys)
    tables = {action["table"] for action in payload["actions"]}
    assert "evidence_ref" in tables
    assert "claim" in tables
    assert "decision_event" in tables
    assert "agent_memory" in tables


@pytest.mark.unit
def test_import_order_ends_with_wave14_in_dependency_order(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    assert main(["plan", "--input-dir", str(tmp_path)]) == EXIT_OK
    payload = _read_json(capsys)
    assert payload["import_order"][-4:] == [
        "evidence_ref",
        "claim",
        "decision_event",
        "agent_memory",
    ]
