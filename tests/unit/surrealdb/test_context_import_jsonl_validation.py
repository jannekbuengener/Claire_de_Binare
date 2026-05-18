"""Unit tests for Context Importer JSONL validation (#2070)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.context_importer import (
    EXIT_INPUT_NOT_FOUND,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    EXIT_WRITE_DENIED,
    EXPECTED_JSONL_FILES,
    INDEXER_SCHEMA_VERSION,
    main,
)


HASH = "a" * 64
RUN_ID = "run-2070"


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def _write_jsonl(input_dir: Path, artifact: str, records: list[dict]) -> None:
    path = input_dir / EXPECTED_JSONL_FILES[artifact]
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _base_record(**updates) -> dict:
    record = {"schema_version": INDEXER_SCHEMA_VERSION, "run_id": RUN_ID}
    record.update(updates)
    return record


def _write_valid_artifacts(input_dir: Path) -> None:
    records = {
        "repo_artifacts": [
            _base_record(
                artifact_id="artifact:1",
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
                page_id="page:1",
                source_path="docs/example.md",
                source_hash=HASH,
                title="Example",
                doc_format="markdown",
            )
        ],
        "doc_sections": [
            _base_record(
                section_id="section:1",
                page_id="page:1",
                source_path="docs/example.md",
                source_hash=HASH,
                heading="Example",
                heading_path=["Example"],
                section_level=1,
                section_index=0,
                span_start_line=1,
                span_end_line=3,
            )
        ],
        "doc_chunks": [
            _base_record(
                chunk_id="chunk:1",
                page_id="page:1",
                section_id="section:1",
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
                symbol_id="symbol:1",
                source_path="tools/example.py",
                source_hash=HASH,
                symbol_type="function",
                name="example",
                qualified_name="example",
            )
        ],
        "import_references": [
            _base_record(
                import_id="import:1",
                source_path="tools/example.py",
                source_hash=HASH,
                module="json",
            )
        ],
        "test_cases": [
            _base_record(
                test_id="test:1",
                source_path="tests/test_example.py",
                source_hash=HASH,
                symbol_id="symbol:1",
                name="test_example",
            )
        ],
        "config_references": [
            _base_record(
                config_ref_id="config:1",
                source_path="infrastructure/config/example.yaml",
                source_hash=HASH,
                config_key="safe_key",
                config_value="safe-value",
                sensitive=False,
            )
        ],
        "doc_code_links": [
            _base_record(
                link_id="link:1",
                source_path="docs/example.md",
                source_hash=HASH,
                target_symbol="example",
                source_chunk_id="chunk:1",
            )
        ],
        "dependency_edges": [
            _base_record(
                edge_id="edge:1",
                from_id="symbol:1",
                to_id="import:1",
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
    for artifact, items in records.items():
        _write_jsonl(input_dir, artifact, items)


def _read_jsonl_report(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.unit
def test_validate_jsonl_passes_valid_artifacts(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "passed"
    assert payload["implemented"] is True
    assert payload["surrealdb_connection"] == "disabled"
    assert payload["validation"]["blocking_count"] == 0
    assert payload["artifact_counts"]["repo_artifacts"] == 1


@pytest.mark.unit
def test_validate_jsonl_allows_doc_chunk_tokens_estimate(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "doc_chunks",
        [
            _base_record(
                chunk_id="chunk:1",
                page_id="page:1",
                section_id="section:1",
                source_path="docs/example.md",
                source_hash=HASH,
                heading_path=["Example"],
                chunk_index=0,
                content="safe context",
                content_hash=HASH,
                tokens_estimate=42,
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "passed"
    assert not any(
        finding["code"] == "secret_like_value_in_jsonl"
        for finding in payload["findings"]
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "source_path",
    (
        "/etc/passwd",
        "../secrets.md",
        "docs/../secrets.md",
        r"C:\repo\file.md",
        "C:/repo/file.md",
        r"\\server\share\file.md",
        "//server/share/file.md",
        r"..\secrets.md",
        r"docs\..\secrets.md",
        r"C:..\secrets.md",
    ),
)
def test_validate_jsonl_blocks_forbidden_source_paths(
    tmp_path: Path, capsys, source_path: str
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "doc_pages",
        [
            _base_record(
                page_id="page:1",
                source_path=source_path,
                source_hash=HASH,
                title="Example",
                doc_format="markdown",
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert any(
        finding["code"] == "forbidden_source_path"
        and finding["source_path"] == source_path
        for finding in payload["findings"]
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "source_path",
    (123, ["docs/foo.md"], {"path": "docs/foo.md"}),
)
def test_validate_jsonl_blocks_invalid_source_path_types(
    tmp_path: Path, capsys, source_path
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "doc_pages",
        [
            _base_record(
                page_id="page:1",
                source_path=source_path,
                source_hash=HASH,
                title="Example",
                doc_format="markdown",
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    out = capsys.readouterr().out
    assert "docs/foo.md" not in out
    payload = json.loads(out)
    assert any(
        finding["code"] == "source_path_invalid_type"
        and "source_path" not in finding
        for finding in payload["findings"]
    )


@pytest.mark.unit
@pytest.mark.parametrize("source_path", ("", "   "))
def test_validate_jsonl_blocks_blank_required_source_paths(
    tmp_path: Path, capsys, source_path: str
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "doc_pages",
        [
            _base_record(
                page_id="page:1",
                source_path=source_path,
                source_hash=HASH,
                title="Example",
                doc_format="markdown",
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    expected_code = "required_field_missing" if source_path == "" else "source_path_blank"
    assert any(
        finding["code"] == expected_code and finding["artifact"] == "doc_pages"
        for finding in payload["findings"]
    )


@pytest.mark.unit
@pytest.mark.parametrize("source_path", ("docs/foo.md", r"docs\foo.md"))
def test_validate_jsonl_allows_safe_relative_source_paths(
    tmp_path: Path, capsys, source_path: str
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "doc_pages",
        [
            _base_record(
                page_id="page:1",
                source_path=source_path,
                source_hash=HASH,
                title="Example",
                doc_format="markdown",
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert not any(
        finding["code"] == "forbidden_source_path"
        for finding in payload["findings"]
    )


@pytest.mark.unit
def test_validate_jsonl_blocks_missing_required_file(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)
    (tmp_path / EXPECTED_JSONL_FILES["doc_chunks"]).unlink()

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert payload["status"] == "blocked"
    assert any(
        finding["code"] == "jsonl_file_missing"
        and finding["artifact"] == "doc_chunks"
        for finding in payload["findings"]
    )


@pytest.mark.unit
def test_validate_jsonl_blocks_bad_schema_and_missing_ref(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "doc_pages",
        [
            _base_record(
                schema_version="wrong/v0",
                page_id="page:1",
                source_path="docs/example.md",
                source_hash="b" * 64,
                title="Example",
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    codes = {finding["code"] for finding in payload["findings"]}
    assert "schema_version_mismatch" in codes
    assert "source_hash_ref_missing" in codes


@pytest.mark.unit
@pytest.mark.parametrize(
    ("secret_key", "secret_value"),
    (
        ("access_token", "access-token-value-1234567890"),
        ("api_key", "api-key-value-1234567890"),
    ),
)
def test_validate_jsonl_blocks_secret_like_keys_without_leaking_values(
    tmp_path: Path, capsys, secret_key: str, secret_value: str
) -> None:
    _write_valid_artifacts(tmp_path)
    config_record = _base_record(
        config_ref_id="config:1",
        source_path="infrastructure/config/example.yaml",
        source_hash=HASH,
        config_key="safe_key",
        config_value="safe-value",
        sensitive=False,
    )
    config_record[secret_key] = secret_value
    _write_jsonl(tmp_path, "config_references", [config_record])

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path)])

    assert exit_code == EXIT_VALIDATION_ERROR
    out = capsys.readouterr().out
    assert secret_value not in out
    payload = json.loads(out)
    assert any(
        finding["code"] == "secret_like_value_in_jsonl"
        for finding in payload["findings"]
    )


@pytest.mark.unit
def test_validate_jsonl_writes_report_only_when_requested(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "validate-jsonl",
            "--input-dir",
            str(tmp_path),
            "--report-output",
            "artifacts/report.md",
            "--format",
            "markdown",
        ]
    )

    assert exit_code == EXIT_OK
    assert capsys.readouterr().out.startswith("# context_importer: validate-jsonl")
    report = tmp_path / "artifacts" / "report.md"
    assert report.exists()
    assert report.read_text(encoding="utf-8").startswith(
        "# context_importer: validate-jsonl"
    )


@pytest.mark.unit
def test_validate_jsonl_jsonl_report_pass_contains_summary(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "validate-jsonl",
            "--input-dir",
            str(tmp_path),
            "--run-id",
            RUN_ID,
            "--report-output",
            "artifacts/report.jsonl",
            "--format",
            "jsonl",
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"
    records = _read_jsonl_report(tmp_path / "artifacts" / "report.jsonl")
    assert len(records) == 1
    summary = records[0]
    assert summary["record_type"] == "summary"
    assert summary["status"] == "passed"
    assert summary["run_id"] == RUN_ID
    assert summary["artifact_count"] == len(EXPECTED_JSONL_FILES)
    assert summary["checked_records"] == len(EXPECTED_JSONL_FILES)
    assert summary["has_blocking"] is False


@pytest.mark.unit
def test_validate_jsonl_jsonl_report_blocks_with_summary_first(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    (tmp_path / EXPECTED_JSONL_FILES["doc_chunks"]).unlink()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "validate-jsonl",
            "--input-dir",
            str(tmp_path),
            "--report-output",
            "artifacts/report.jsonl",
            "--format",
            "jsonl",
        ]
    )

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    records = _read_jsonl_report(tmp_path / "artifacts" / "report.jsonl")
    assert records[0]["record_type"] == "summary"
    assert records[0]["status"] == "blocked"
    assert records[0]["finding_count"] >= 1
    assert records[0]["has_blocking"] is True
    assert all(record["record_type"] == "finding" for record in records[1:])
    assert any(
        record["code"] == "jsonl_file_missing"
        and record["artifact"] == "doc_chunks"
        for record in records[1:]
    )


@pytest.mark.unit
def test_validate_jsonl_json_report_shape_remains_unchanged(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "validate-jsonl",
            "--input-dir",
            str(tmp_path),
            "--report-output",
            "artifacts/report.json",
            "--format",
            "json",
        ]
    )

    assert exit_code == EXIT_OK
    stdout_payload = json.loads(capsys.readouterr().out)
    report = json.loads((tmp_path / "artifacts" / "report.json").read_text(encoding="utf-8"))
    assert stdout_payload["report_output"].replace("\\", "/") == "artifacts/report.json"
    assert "record_type" not in report
    assert report["command"] == "validate-jsonl"
    assert report["findings"] == []
    assert report["status"] == "passed"
    assert report["validation"]["blocking_count"] == 0


@pytest.mark.unit
def test_validate_jsonl_rejects_report_output_outside_whitelist(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(
        ["validate-jsonl", "--input-dir", str(tmp_path), "--report-output", "out/report.json"]
    )

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("link_path", "report_output"),
    (
        (Path("artifacts"), "artifacts/report.json"),
        (Path("artifacts/linked"), "artifacts/linked/report.json"),
    ),
)
def test_validate_jsonl_rejects_report_output_symlink_escape(
    tmp_path: Path, monkeypatch, capsys, link_path: Path, report_output: str
) -> None:
    _write_valid_artifacts(tmp_path)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    artifacts_link = tmp_path / link_path
    artifacts_link.parent.mkdir(parents=True, exist_ok=True)
    try:
        artifacts_link.symlink_to(outside_dir, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable on this platform: {exc}")
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "validate-jsonl",
            "--input-dir",
            str(tmp_path),
            "--report-output",
            report_output,
        ]
    )

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"
    assert not (outside_dir / "report.json").exists()


@pytest.mark.unit
def test_validate_jsonl_requires_input_dir(capsys) -> None:
    exit_code = main(["validate-jsonl"])

    assert exit_code == EXIT_INPUT_NOT_FOUND
    payload = _read_json(capsys)
    assert payload["error"] == "INPUT_NOT_FOUND"


@pytest.mark.unit
def test_apply_short_circuits_before_jsonl_validation(capsys) -> None:
    exit_code = main(["validate-jsonl", "--apply", "--input-dir", "missing"])

    assert exit_code == EXIT_WRITE_DENIED
    payload = _read_json(capsys)
    assert payload["error"] == "WRITE_DENIED"


@pytest.mark.unit
def test_wave14_artifacts_pass_validation(tmp_path: Path, capsys) -> None:
    _write_valid_artifacts(tmp_path)

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert payload["status"] == "passed"
    assert payload["validation"]["blocking_count"] == 0
    assert payload["artifact_counts"]["evidence_refs"] == 1
    assert payload["artifact_counts"]["claims"] == 1
    assert payload["artifact_counts"]["decision_events"] == 1
    assert payload["artifact_counts"]["agent_memories"] == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    "artifact,pk_field",
    [
        ("evidence_refs", "evidence_id"),
        ("claims", "claim_id"),
        ("decision_events", "decision_id"),
        ("agent_memories", "memory_id"),
    ],
)
def test_wave14_missing_pk_is_blocking(
    tmp_path: Path, capsys, artifact: str, pk_field: str
) -> None:
    _write_valid_artifacts(tmp_path)
    bad_record = _base_record(created_at="2026-05-18T00:00:00Z")
    _write_jsonl(tmp_path, artifact, [bad_record])

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_VALIDATION_ERROR
    payload = _read_json(capsys)
    assert any(
        finding["code"] == "required_field_missing"
        and finding["artifact"] == artifact
        for finding in payload["findings"]
    )


# ---------------------------------------------------------------------------
# Wave-14 cross-reference validation tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wave14_empty_evidence_refs_array_produces_no_findings(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "claims",
        [_base_record(claim_id="claim-001", created_at="2026-05-18T00:00:00Z", evidence_refs=[])],
    )
    _write_jsonl(
        tmp_path,
        "decision_events",
        [
            _base_record(
                decision_id="decision-001",
                created_at="2026-05-18T00:00:00Z",
                evidence_refs=[],
                claim_refs=[],
            )
        ],
    )
    _write_jsonl(
        tmp_path,
        "agent_memories",
        [_base_record(memory_id="memory-001", created_at="2026-05-18T00:00:00Z", evidence_refs=[])],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    cross_ref_codes = {
        "claim_evidence_ref_not_in_batch",
        "decision_evidence_ref_not_in_batch",
        "decision_claim_ref_not_in_batch",
        "memory_evidence_ref_not_in_batch",
    }
    assert not any(f["code"] in cross_ref_codes for f in payload["findings"])
    assert payload["validation"]["blocking_count"] == 0


@pytest.mark.unit
def test_wave14_valid_within_batch_claim_evidence_ref_passes(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "evidence_refs",
        [_base_record(evidence_id="ev-001", created_at="2026-05-18T00:00:00Z")],
    )
    _write_jsonl(
        tmp_path,
        "claims",
        [
            _base_record(
                claim_id="claim-001",
                created_at="2026-05-18T00:00:00Z",
                evidence_refs=["ev-001"],
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    assert not any(f["code"] == "claim_evidence_ref_not_in_batch" for f in payload["findings"])


@pytest.mark.unit
def test_wave14_missing_claim_evidence_ref_is_warning(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "claims",
        [
            _base_record(
                claim_id="claim-001",
                created_at="2026-05-18T00:00:00Z",
                evidence_refs=["ev-missing"],
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    matching = [f for f in payload["findings"] if f["code"] == "claim_evidence_ref_not_in_batch"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "warning"
    assert payload["validation"]["blocking_count"] == 0


@pytest.mark.unit
def test_wave14_missing_decision_claim_ref_is_warning(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "decision_events",
        [
            _base_record(
                decision_id="decision-001",
                created_at="2026-05-18T00:00:00Z",
                claim_refs=["claim-missing"],
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    matching = [f for f in payload["findings"] if f["code"] == "decision_claim_ref_not_in_batch"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "warning"
    assert payload["validation"]["blocking_count"] == 0


@pytest.mark.unit
def test_wave14_missing_memory_evidence_ref_is_warning(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "agent_memories",
        [
            _base_record(
                memory_id="memory-001",
                created_at="2026-05-18T00:00:00Z",
                evidence_refs=["ev-missing"],
            )
        ],
    )

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    matching = [f for f in payload["findings"] if f["code"] == "memory_evidence_ref_not_in_batch"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "warning"
    assert payload["validation"]["blocking_count"] == 0


@pytest.mark.unit
def test_wave14_indexer_generated_evidence_refs_pass_cross_ref_check(
    tmp_path: Path, capsys
) -> None:
    _write_valid_artifacts(tmp_path)
    _write_jsonl(
        tmp_path,
        "evidence_refs",
        [
            _base_record(
                evidence_id="evidence_ref:abc123",
                created_at="2026-05-18T00:00:00Z",
                evidence_type="test_file",
                source_path="tests/unit/surrealdb/test_context_indexer.py",
                source_hash=HASH,
                confidence=0.8,
            )
        ],
    )
    # claims/decision_events/agent_memories remain empty (no refs to validate)

    exit_code = main(["validate-jsonl", "--input-dir", str(tmp_path), "--run-id", RUN_ID])

    assert exit_code == EXIT_OK
    payload = _read_json(capsys)
    cross_ref_codes = {
        "claim_evidence_ref_not_in_batch",
        "decision_evidence_ref_not_in_batch",
        "decision_claim_ref_not_in_batch",
        "memory_evidence_ref_not_in_batch",
    }
    assert not any(f["code"] in cross_ref_codes for f in payload["findings"])
    assert payload["validation"]["blocking_count"] == 0
