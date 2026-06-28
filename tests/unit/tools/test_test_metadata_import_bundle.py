from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from tools.test_metadata_import_bundle import (
    SCHEMA_VERSION,
    SOURCE_SCANNER,
    RECORD_TYPE,
    _derive_pilot_id,
    _to_relpath_posix,
    _build_record_id,
    _build_content_hash,
    _build_record,
    load_scanner_report,
    build_bundle,
    validate_records,
    write_bundle,
    run,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPORT_BLOCK = {
    "file": "tests/unit/validation/test_profitability_evidence_packet_assembler.py",
    "blocks": [
        {
            "fields": {
                "test_id": "cdb-test-pilot-001",
                "test_title": "Profitability Evidence Packet Assembler",
                "test_type": "mixed",
                "cdb_area": "validation",
                "rule_ref": "PROFITABILITY_EVIDENCE_PACKET_SCHEMA_CONFORMANCE",
                "decision_ref": "d-2026-04-08-evidence-packet-structure",
                "issue_ref": "#1492",
                "pr_ref": "#3408",
                "evidence_ref": "docs/contracts/profitability_evidence_packet.v1.schema.json",
                "code_area": "ProfitabilityEvidencePacketAssembler",
                "security_relevant": False,
                "live_relevant": False,
                "profitability_relevant": True,
                "surrealdb_export": True,
                "ci_artifact": "test-report",
            },
            "is_valid": True,
            "surrealdb_export": True,
        },
    ],
    "validation_errors": [],
}

NO_EXPORT_BLOCK = {
    "file": "tests/unit/validation/test_no_export.py",
    "blocks": [
        {
            "fields": {
                "test_id": "tc-no-export-001",
                "test_title": "No Export Block",
                "test_type": "bauteil",
                "cdb_area": "risk",
                "rule_ref": "NO_EXPORT",
                "decision_ref": "no export decision",
                "issue_ref": "#9999",
                "pr_ref": "#9999",
                "evidence_ref": "docs/test/noexport.md",
                "code_area": "services/risk/",
                "security_relevant": False,
                "live_relevant": False,
                "profitability_relevant": False,
                "surrealdb_export": False,
                "ci_artifact": "test-report",
            },
            "is_valid": True,
            "surrealdb_export": False,
        },
    ],
    "validation_errors": [],
}

INVALID_BLOCK = {
    "file": "tests/unit/validation/test_invalid.py",
    "blocks": [
        {
            "fields": {
                "test_id": "tc-invalid-001",
                "test_title": "Invalid Block",
                "test_type": "bauteil",
                "cdb_area": "risk",
            },
            "is_valid": False,
            "surrealdb_export": False,
            "missing_fields": [
                "rule_ref",
                "decision_ref",
                "issue_ref",
                "pr_ref",
                "evidence_ref",
                "code_area",
                "security_relevant",
                "live_relevant",
                "profitability_relevant",
                "surrealdb_export",
                "ci_artifact",
            ],
        },
    ],
    "validation_errors": [],
}

ABSOLUTE_PATH_RESULT = {
    "file": "C:/Users/test/some_file.py",
    "blocks": [
        {
            "fields": {
                "test_id": "tc-abs-001",
                "test_title": "Absolute Path",
                "test_type": "bauteil",
                "cdb_area": "risk",
                "rule_ref": "ABS_PATH",
                "decision_ref": "abs path decision",
                "issue_ref": "#9999",
                "pr_ref": "#9999",
                "evidence_ref": "docs/test/abs.md",
                "code_area": "services/risk/",
                "security_relevant": False,
                "live_relevant": False,
                "profitability_relevant": False,
                "surrealdb_export": True,
                "ci_artifact": "test-report",
            },
            "is_valid": True,
            "surrealdb_export": True,
        },
    ],
    "validation_errors": [],
}

VALID_SCANNER_REPORT = {
    "scanner_version": "1.0.0",
    "scanned_files": 1,
    "total_blocks": 1,
    "total_errors": 0,
    "surrealdb_export_ready": 1,
    "results": [EXPORT_BLOCK],
}


def _write_tmp_json(content: dict) -> Path:
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    os.write(fd, json.dumps(content, indent=2).encode("utf-8"))
    os.close(fd)
    return Path(path)


# ---------------------------------------------------------------------------
# _derive_pilot_id
# ---------------------------------------------------------------------------


class TestDerivePilotId:
    def test_pilot_pattern_matches(self):
        assert _derive_pilot_id("cdb-test-pilot-001") == "CDB-PILOT-001"

    def test_pilot_pattern_matches_large_number(self):
        assert _derive_pilot_id("cdb-test-pilot-042") == "CDB-PILOT-042"

    def test_non_pilot_id_returns_empty(self):
        assert _derive_pilot_id("tc-drawdown-001") == ""

    def test_empty_string_returns_empty(self):
        assert _derive_pilot_id("") == ""

    def test_case_insensitive(self):
        assert _derive_pilot_id("CDB-TEST-PILOT-007") == "CDB-PILOT-007"


# ---------------------------------------------------------------------------
# _to_relpath_posix
# ---------------------------------------------------------------------------


class TestToRelpathPosix:
    def test_relative_posix_accepted(self):
        assert _to_relpath_posix("tests/unit/risk/test_risk.py") == "tests/unit/risk/test_risk.py"

    def test_relative_with_backslashes_normalized(self):
        assert _to_relpath_posix("tests\\unit\\risk\\test_risk.py") == "tests/unit/risk/test_risk.py"

    def test_basename_accepted(self):
        assert _to_relpath_posix("test_risk.py") == "test_risk.py"

    def test_windows_drive_letter_rejected(self):
        with pytest.raises(ValueError, match="Absolute path rejected"):
            _to_relpath_posix("C:\\Users\\test\\file.py")

    def test_unix_absolute_rejected(self):
        with pytest.raises(ValueError, match="Absolute path rejected"):
            _to_relpath_posix("/home/user/file.py")

    def test_windows_forward_slash_drive_rejected(self):
        with pytest.raises(ValueError, match="Absolute path rejected"):
            _to_relpath_posix("C:/Users/test/file.py")

    def test_empty_string_returns_empty(self):
        assert _to_relpath_posix("") == ""

    def test_strip_whitespace(self):
        assert _to_relpath_posix("  tests/unit/test.py  ") == "tests/unit/test.py"


# ---------------------------------------------------------------------------
# _build_record_id
# ---------------------------------------------------------------------------


class TestBuildRecordId:
    def test_deterministic_same_input(self):
        id1 = _build_record_id("tests/unit/risk/test_risk.py", "tc-001")
        id2 = _build_record_id("tests/unit/risk/test_risk.py", "tc-001")
        assert id1 == id2

    def test_different_input_different_id(self):
        id1 = _build_record_id("tests/unit/risk/test_risk.py", "tc-001")
        id2 = _build_record_id("tests/unit/risk/test_risk.py", "tc-002")
        assert id1 != id2

    def test_prefix_is_test_case(self):
        rid = _build_record_id("tests/unit/test.py", "tc-001")
        assert rid.startswith("test_case:")

    def test_consistent_hash_length(self):
        rid = _build_record_id("some/file.py", "tc-001")
        suffix = rid.split(":")[1]
        assert len(suffix) == 24


# ---------------------------------------------------------------------------
# _build_content_hash
# ---------------------------------------------------------------------------


class TestBuildContentHash:
    def test_deterministic_same_record(self):
        record = {
            "record_id": "test_case:abc123",
            "source_file": "tests/unit/test.py",
            "test_id": "tc-001",
            "test_type": "bauteil",
            "ci_artifact": "test-report",
            "surrealdb_export": True,
        }
        h1 = _build_content_hash(record)
        h2 = _build_content_hash(record)
        assert h1 == h2

    def test_different_content_different_hash(self):
        r1 = {
            "record_id": "test_case:abc123",
            "source_file": "tests/unit/test.py",
            "test_id": "tc-001",
            "test_type": "bauteil",
            "surrealdb_export": True,
        }
        r2 = {
            "record_id": "test_case:def456",
            "source_file": "tests/unit/test.py",
            "test_id": "tc-002",
            "test_type": "schutz",
            "surrealdb_export": True,
        }
        assert _build_content_hash(r1) != _build_content_hash(r2)

    def test_record_id_excluded_from_hash(self):
        record = {
            "record_id": "test_case:abc123",
            "source_file": "tests/unit/test.py",
            "test_id": "tc-001",
            "surrealdb_export": True,
        }
        h1 = _build_content_hash(record)
        record["record_id"] = "test_case:xyz999"
        h2 = _build_content_hash(record)
        assert h1 == h2


# ---------------------------------------------------------------------------
# _build_record
# ---------------------------------------------------------------------------


class TestBuildRecord:
    def test_basic_record_structure(self):
        block = EXPORT_BLOCK["blocks"][0]
        record = _build_record("tests/unit/validation/test_profitability_evidence_packet_assembler.py", block)

        assert record["schema_version"] == SCHEMA_VERSION
        assert record["record_type"] == RECORD_TYPE
        assert record["source_file"] == "tests/unit/validation/test_profitability_evidence_packet_assembler.py"
        assert record["pilot_id"] == "CDB-PILOT-001"
        assert record["test_id"] == "cdb-test-pilot-001"
        assert record["test_type"] == "mixed"
        assert record["ci_artifact"] == "test-report"
        assert record["surrealdb_export"] is True
        assert record["source_scanner"] == SOURCE_SCANNER
        assert record["limitations"] == []

        assert record["record_id"].startswith("test_case:")
        assert len(record["content_hash"]) == 64

    def test_metadata_contains_all_fields(self):
        block = EXPORT_BLOCK["blocks"][0]
        record = _build_record("tests/unit/test.py", block)
        for key in block["fields"]:
            assert record["metadata"][key] == block["fields"][key]

    def test_deterministic_build(self):
        block = EXPORT_BLOCK["blocks"][0]
        r1 = _build_record("tests/unit/test.py", block)
        r2 = _build_record("tests/unit/test.py", block)
        assert r1 == r2

    def test_record_id_is_stable(self):
        block = EXPORT_BLOCK["blocks"][0]
        source_file = "tests/unit/validation/test_profitability_evidence_packet_assembler.py"
        r1 = _build_record(source_file, block)
        r2 = _build_record(source_file, block)
        assert r1["record_id"] == r2["record_id"]

    def test_non_pilot_block_has_empty_pilot_id(self):
        block = NO_EXPORT_BLOCK["blocks"][0]
        record = _build_record("tests/unit/test.py", block)
        assert record["pilot_id"] == ""


# ---------------------------------------------------------------------------
# load_scanner_report
# ---------------------------------------------------------------------------


class TestLoadScannerReport:
    def test_valid_report(self):
        raw = json.dumps(VALID_SCANNER_REPORT)
        report = load_scanner_report(raw)
        assert report["scanner_version"] == "1.0.0"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid scanner JSON"):
            load_scanner_report("not json")

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            load_scanner_report("[]")

    def test_missing_results_raises(self):
        with pytest.raises(ValueError, match="missing 'results'"):
            load_scanner_report('{"scanner_version": "1.0.0"}')


# ---------------------------------------------------------------------------
# build_bundle
# ---------------------------------------------------------------------------


class TestBuildBundle:
    def test_exportable_block_included(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 1,
            "total_blocks": 1,
            "total_errors": 0,
            "surrealdb_export_ready": 1,
            "results": [EXPORT_BLOCK],
        }
        records = build_bundle(report)
        assert len(records) == 1
        assert records[0]["test_id"] == "cdb-test-pilot-001"

    def test_no_export_excluded(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 2,
            "total_blocks": 2,
            "total_errors": 0,
            "surrealdb_export_ready": 1,
            "results": [EXPORT_BLOCK, NO_EXPORT_BLOCK],
        }
        records = build_bundle(report)
        assert len(records) == 1

    def test_invalid_block_excluded(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 2,
            "total_blocks": 2,
            "total_errors": 1,
            "surrealdb_export_ready": 0,
            "results": [EXPORT_BLOCK, INVALID_BLOCK],
        }
        records = build_bundle(report)
        assert len(records) == 1

    def test_all_excluded_returns_empty(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 1,
            "total_blocks": 1,
            "total_errors": 0,
            "surrealdb_export_ready": 0,
            "results": [NO_EXPORT_BLOCK],
        }
        records = build_bundle(report)
        assert len(records) == 0

    def test_absolute_path_result_skipped(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 2,
            "total_blocks": 2,
            "total_errors": 0,
            "surrealdb_export_ready": 1,
            "results": [ABSOLUTE_PATH_RESULT, EXPORT_BLOCK],
        }
        records = build_bundle(report)
        assert len(records) == 1
        assert records[0]["source_file"] == EXPORT_BLOCK["file"]

    def test_empty_report(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 0,
            "total_blocks": 0,
            "total_errors": 0,
            "surrealdb_export_ready": 0,
            "results": [],
        }
        records = build_bundle(report)
        assert len(records) == 0

    def test_deterministic_order(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 2,
            "total_blocks": 2,
            "total_errors": 0,
            "surrealdb_export_ready": 2,
            "results": [NO_EXPORT_BLOCK, EXPORT_BLOCK],
        }
        records = build_bundle(report)
        assert len(records) == 1

    def test_maintains_ci_artifact_as_string(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 1,
            "total_blocks": 1,
            "total_errors": 0,
            "surrealdb_export_ready": 1,
            "results": [EXPORT_BLOCK],
        }
        records = build_bundle(report)
        assert isinstance(records[0]["ci_artifact"], str)
        assert records[0]["ci_artifact"] == "test-report"


# ---------------------------------------------------------------------------
# validate_records
# ---------------------------------------------------------------------------


class TestValidateRecords:
    def test_no_errors_for_valid_records(self):
        records = build_bundle(VALID_SCANNER_REPORT)
        errors = validate_records(records)
        assert errors == []

    def test_duplicate_record_id_detected(self):
        records = [
            {"record_id": "test_case:dup", "source_file": "a.py"},
            {"record_id": "test_case:dup", "source_file": "b.py"},
        ]
        errors = validate_records(records)
        assert len(errors) == 1
        assert "duplicate" in errors[0]

    def test_empty_records_no_errors(self):
        errors = validate_records([])
        assert errors == []


# ---------------------------------------------------------------------------
# write_bundle
# ---------------------------------------------------------------------------


class TestWriteBundle:
    def test_bundle_has_required_keys(self):
        records = build_bundle(VALID_SCANNER_REPORT)
        bundle = json.loads(write_bundle(records))
        assert bundle["schema_version"] == SCHEMA_VERSION
        assert bundle["source_scanner"] == SOURCE_SCANNER
        assert bundle["record_count"] == 1
        assert len(bundle["records"]) == 1

    def test_empty_records(self):
        bundle = json.loads(write_bundle([]))
        assert bundle["record_count"] == 0
        assert bundle["records"] == []

    def test_valid_json_output(self):
        records = build_bundle(VALID_SCANNER_REPORT)
        raw = write_bundle(records)
        data = json.loads(raw)
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# run() integration
# ---------------------------------------------------------------------------


class TestRun:
    def test_stdin_no_data(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.read", lambda: "")
        code = run([])
        assert code == 2

    def test_valid_file_returns_zero(self):
        path = _write_tmp_json(VALID_SCANNER_REPORT)
        try:
            code = run([str(path)])
            assert code == 0
        finally:
            os.unlink(str(path))

    def test_output_file(self):
        path = _write_tmp_json(VALID_SCANNER_REPORT)
        out_path_obj = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_path = out_path_obj.name
        out_path_obj.close()
        try:
            code = run([str(path), "--output", out_path])
            assert code == 0
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["record_count"] == 1
        finally:
            os.unlink(str(path))
            os.unlink(out_path)

    def test_no_exportable_blocks_returns_one(self):
        report = {
            "scanner_version": "1.0.0",
            "scanned_files": 1,
            "total_blocks": 1,
            "total_errors": 0,
            "surrealdb_export_ready": 0,
            "results": [NO_EXPORT_BLOCK],
        }
        path = _write_tmp_json(report)
        try:
            code = run([str(path)])
            assert code == 1
        finally:
            os.unlink(str(path))

    def test_nonexistent_file_returns_two(self):
        code = run(["nonexistent_file_xyz.json"])
        assert code == 2

    def test_malformed_json_returns_two(self):
        fd, path = tempfile.mkstemp(suffix=".json", text=True)
        os.write(fd, b"not json at all")
        os.close(fd)
        try:
            code = run([str(path)])
            assert code == 2
        finally:
            os.unlink(path)

    def test_standard_input_pipe(self, monkeypatch):
        path = _write_tmp_json(VALID_SCANNER_REPORT)
        try:
            with open(str(path), encoding="utf-8") as f:
                content = f.read()
            monkeypatch.setattr("sys.stdin.read", lambda: content)
            code = run(["-"])
            assert code == 0
        finally:
            os.unlink(str(path))
