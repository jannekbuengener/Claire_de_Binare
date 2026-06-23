from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from tools.test_metadata_surrealdb_import_plan import (
    PLAN_SCHEMA_VERSION,
    BUNDLE_SCHEMA_VERSION,
    PLAN_TYPE,
    TARGET_TABLE,
    _check_absolute_path,
    _build_operation,
    load_bundle,
    validate_bundle_record,
    build_plan,
    write_plan,
    run,
)

VALID_RECORD = {
    "schema_version": "test-metadata-import-bundle/v1",
    "record_type": "test_case",
    "record_id": "test_case:f7cbdae5b69b6355575cf520",
    "source_file": "tests/unit/validation/test_profitability_evidence_packet_assembler.py",
    "pilot_id": "CDB-PILOT-001",
    "test_id": "cdb-test-pilot-001",
    "test_type": "mixed",
    "ci_artifact": "test-report",
    "surrealdb_export": True,
    "content_hash": "9cb810756e8cb05f5ebe62352517cc23c98797294a6a8a26c374efc03676b574",
    "source_scanner": "test_metadata_scanner/v1.0.0",
    "limitations": [],
    "metadata": {
        "test_title": "Profitability Evidence Packet Assembler",
        "test_type": "mixed",
        "cdb_area": "validation",
    },
}

VALID_BUNDLE = {
    "schema_version": "test-metadata-import-bundle/v1",
    "source_scanner": "test_metadata_scanner/v1.0.0",
    "record_count": 1,
    "records": [VALID_RECORD],
}

VALID_RECORD_NO_PILOT = {
    "schema_version": "test-metadata-import-bundle/v1",
    "record_type": "test_case",
    "record_id": "test_case:abc123def4567890abcdef12",
    "source_file": "tests/unit/risk/test_drawdown.py",
    "pilot_id": "",
    "test_id": "tc-drawdown-001",
    "test_type": "schutz",
    "ci_artifact": "test-report",
    "surrealdb_export": True,
    "content_hash": "a" * 64,
    "source_scanner": "test_metadata_scanner/v1.0.0",
    "limitations": [],
    "metadata": {
        "test_title": "Drawdown Limit Test",
    },
}

VALID_RECORD_WITH_LIMITATION = {
    "schema_version": "test-metadata-import-bundle/v1",
    "record_type": "test_case",
    "record_id": "test_case:def4567890abcdef12345678",
    "source_file": "tests/unit/risk/test_variance.py",
    "pilot_id": "CDB-PILOT-002",
    "test_id": "cdb-test-pilot-002",
    "test_type": "bauteil",
    "ci_artifact": "test-report",
    "surrealdb_export": True,
    "content_hash": "b" * 64,
    "source_scanner": "test_metadata_scanner/v1.0.0",
    "limitations": ["some-known-limitation"],
    "metadata": {
        "test_title": "Variance Test",
    },
}


def _write_tmp_json(content: dict) -> Path:
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    os.write(fd, json.dumps(content, indent=2).encode("utf-8"))
    os.close(fd)
    return Path(path)


# ---------------------------------------------------------------------------
# _check_absolute_path
# ---------------------------------------------------------------------------


class TestCheckAbsolutePath:
    def test_relative_path_false(self):
        assert _check_absolute_path("tests/unit/test.py") is False

    def test_windows_drive_letter_true(self):
        assert _check_absolute_path("C:\\Users\\test\\file.py") is True

    def test_windows_forward_slash_drive_true(self):
        assert _check_absolute_path("C:/Users/test/file.py") is True

    def test_unix_absolute_true(self):
        assert _check_absolute_path("/home/user/file.py") is True

    def test_backslash_normalized(self):
        assert _check_absolute_path("C:\\Projects\\test.py") is True

    def test_empty_string_false(self):
        assert _check_absolute_path("") is False

    def test_basename_false(self):
        assert _check_absolute_path("test_risk.py") is False


# ---------------------------------------------------------------------------
# load_bundle
# ---------------------------------------------------------------------------


class TestLoadBundle:
    def test_valid_bundle(self):
        raw = json.dumps(VALID_BUNDLE)
        bundle = load_bundle(raw)
        assert bundle["schema_version"] == "test-metadata-import-bundle/v1"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid bundle JSON"):
            load_bundle("not json")

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            load_bundle("[]")

    def test_missing_records_raises(self):
        with pytest.raises(ValueError, match="missing 'records'"):
            load_bundle('{"schema_version": "v1"}')


# ---------------------------------------------------------------------------
# validate_bundle_record
# ---------------------------------------------------------------------------


class TestValidateBundleRecord:
    def test_valid_record_no_errors(self):
        errors = validate_bundle_record(VALID_RECORD)
        assert errors == []

    def test_missing_record_id(self):
        record = dict(VALID_RECORD)
        del record["record_id"]
        errors = validate_bundle_record(record)
        assert any("record_id" in e for e in errors)

    def test_missing_content_hash(self):
        record = dict(VALID_RECORD)
        del record["content_hash"]
        errors = validate_bundle_record(record)
        assert any("content_hash" in e for e in errors)

    def test_missing_test_id(self):
        record = dict(VALID_RECORD)
        del record["test_id"]
        errors = validate_bundle_record(record)
        assert any("test_id" in e for e in errors)

    def test_missing_ci_artifact(self):
        record = dict(VALID_RECORD)
        del record["ci_artifact"]
        errors = validate_bundle_record(record)
        assert any("ci_artifact" in e for e in errors)

    def test_missing_surrealdb_export(self):
        record = dict(VALID_RECORD)
        del record["surrealdb_export"]
        errors = validate_bundle_record(record)
        assert any("surrealdb_export" in e for e in errors)

    def test_ci_artifact_bool_rejected(self):
        record = dict(VALID_RECORD)
        record["ci_artifact"] = True
        errors = validate_bundle_record(record)
        assert any("must be a string" in e for e in errors)

    def test_absolute_source_file_detected(self):
        record = dict(VALID_RECORD)
        record["source_file"] = "C:/Users/test/file.py"
        errors = validate_bundle_record(record)
        assert any("Absolute path" in e for e in errors)

    def test_multiple_errors_returned(self):
        record = {}
        errors = validate_bundle_record(record)
        assert len(errors) >= 5


# ---------------------------------------------------------------------------
# _build_operation
# ---------------------------------------------------------------------------


class TestBuildOperation:
    def test_operation_structure(self):
        op = _build_operation(VALID_RECORD)
        assert op["operation"] == PLAN_TYPE
        assert op["target_table"] == TARGET_TABLE
        assert op["target_id"] == "test_case:f7cbdae5b69b6355575cf520"
        assert (
            op["content_hash"]
            == "9cb810756e8cb05f5ebe62352517cc23c98797294a6a8a26c374efc03676b574"
        )
        assert op["source_bundle_record_id"] == "test_case:f7cbdae5b69b6355575cf520"

    def test_record_subset_excludes_control_fields(self):
        op = _build_operation(VALID_RECORD)
        record = op["record"]
        assert "schema_version" not in record
        assert "record_type" not in record
        assert "record_id" not in record
        assert "content_hash" not in record
        assert "source_scanner" not in record
        assert "limitations" not in record

    def test_record_subset_includes_payload_fields(self):
        op = _build_operation(VALID_RECORD)
        record = op["record"]
        assert (
            record["source_file"]
            == "tests/unit/validation/test_profitability_evidence_packet_assembler.py"
        )
        assert record["pilot_id"] == "CDB-PILOT-001"
        assert record["test_id"] == "cdb-test-pilot-001"
        assert record["test_type"] == "mixed"
        assert record["ci_artifact"] == "test-report"
        assert record["surrealdb_export"] is True

    def test_metadata_merged_into_record(self):
        op = _build_operation(VALID_RECORD)
        record = op["record"]
        assert record["test_title"] == "Profitability Evidence Packet Assembler"
        assert record["cdb_area"] == "validation"

    def test_limitations_passed_through(self):
        op = _build_operation(VALID_RECORD_WITH_LIMITATION)
        assert op["limitations"] == ["some-known-limitation"]

    def test_no_metadata_fallback(self):
        record = dict(VALID_RECORD)
        record["metadata"] = {}
        op = _build_operation(record)
        assert op["record"] is not None


# ---------------------------------------------------------------------------
# build_plan
# ---------------------------------------------------------------------------


class TestBuildPlan:
    def test_happy_path(self):
        operations, warnings, limitations, fingerprint = build_plan(VALID_BUNDLE)
        assert len(operations) == 1
        assert warnings == []
        assert limitations == []
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64

    def test_empty_bundle(self):
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 0,
            "records": [],
        }
        operations, warnings, limitations, fingerprint = build_plan(bundle)
        assert len(operations) == 0
        assert warnings == []
        assert isinstance(fingerprint, str)

    def test_no_pilot_generates_warning(self):
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 1,
            "records": [VALID_RECORD_NO_PILOT],
        }
        operations, warnings, limitations, _ = build_plan(bundle)
        assert len(operations) == 1
        assert any("empty_pilot_id" in w for w in warnings)
        assert "pilot_id: not derivable" in operations[0]["limitations"][0]

    def test_ci_artifact_bool_record_excluded(self):
        record = dict(VALID_RECORD)
        record["ci_artifact"] = True
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 1,
            "records": [record],
        }
        operations, warnings, _, _ = build_plan(bundle)
        assert len(operations) == 0
        assert any("must be a string" in w for w in warnings)

    def test_absolute_path_record_excluded(self):
        record = dict(VALID_RECORD)
        record["source_file"] = "D:/Projects/test.py"
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 1,
            "records": [record],
        }
        operations, warnings, _, _ = build_plan(bundle)
        assert len(operations) == 0
        assert any("Absolute path" in w for w in warnings)

    def test_missing_field_record_excluded(self):
        record = dict(VALID_RECORD)
        del record["test_id"]
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 1,
            "records": [record],
        }
        operations, warnings, _, _ = build_plan(bundle)
        assert len(operations) == 0
        assert any("test_id" in w for w in warnings)

    def test_deterministic_sort_order(self):
        record_b = dict(VALID_RECORD)
        record_b["source_file"] = "tests/unit/beta/test_b.py"
        record_b["test_id"] = "tc-beta-001"
        record_b["record_id"] = "test_case:bbbbbbbbbbbbbbbbbbbbbbbb"
        record_b["content_hash"] = "c" * 64

        record_a = dict(VALID_RECORD)
        record_a["source_file"] = "tests/unit/alpha/test_a.py"
        record_a["test_id"] = "tc-alpha-001"
        record_a["record_id"] = "test_case:aaaaaaaaaaaaaaaaaaaaaaaa"
        record_a["content_hash"] = "d" * 64

        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 2,
            "records": [record_b, record_a],
        }
        operations, _, _, _ = build_plan(bundle)
        assert len(operations) == 2
        assert operations[0]["target_id"] == "test_case:aaaaaaaaaaaaaaaaaaaaaaaa"
        assert operations[1]["target_id"] == "test_case:bbbbbbbbbbbbbbbbbbbbbbbb"

    def test_deterministic_fingerprint(self):
        ops1, _, _, fp1 = build_plan(VALID_BUNDLE)
        ops2, _, _, fp2 = build_plan(VALID_BUNDLE)
        assert fp1 == fp2
        assert len(fp1) == 64

    def test_mixed_valid_and_invalid_records(self):
        bad_record = dict(VALID_RECORD)
        bad_record["ci_artifact"] = 123
        bad_record["record_id"] = "test_case:badbadbadbadbadbadbadbad"

        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 2,
            "records": [VALID_RECORD, bad_record],
        }
        operations, warnings, _, _ = build_plan(bundle)
        assert len(operations) == 1
        assert any("ci_artifact" in w for w in warnings)


# ---------------------------------------------------------------------------
# write_plan
# ---------------------------------------------------------------------------


class TestWritePlan:
    def test_plan_has_required_keys(self):
        operations, warnings, limitations, fingerprint = build_plan(VALID_BUNDLE)
        plan = json.loads(write_plan(operations, warnings, limitations, fingerprint))
        assert plan["schema_version"] == PLAN_SCHEMA_VERSION
        assert plan["source_bundle_schema"] == BUNDLE_SCHEMA_VERSION
        assert plan["plan_type"] == PLAN_TYPE
        assert plan["operation_count"] == 1
        assert plan["dry_run"] is True
        assert plan["surrealdb_write"] is False
        assert isinstance(plan["bundle_fingerprint"], str)
        assert isinstance(plan["warnings"], list)
        assert isinstance(plan["limitations"], list)
        assert len(plan["operations"]) == 1

    def test_empty_operations(self):
        raw = write_plan([], [], [], "f" * 64)
        plan = json.loads(raw)
        assert plan["operation_count"] == 0
        assert plan["operations"] == []

    def test_valid_json_output(self):
        operations, warnings, limitations, fingerprint = build_plan(VALID_BUNDLE)
        raw = write_plan(operations, warnings, limitations, fingerprint)
        data = json.loads(raw)
        assert isinstance(data, dict)

    def test_warnings_formatted(self):
        raw = write_plan([], ["[tc-001] some warning"], [], "f" * 64)
        plan = json.loads(raw)
        assert "[tc-001] some warning" in plan["warnings"]


# ---------------------------------------------------------------------------
# run() integration
# ---------------------------------------------------------------------------


class TestRun:
    def test_stdin_no_data(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.read", lambda: "")
        code = run([])
        assert code == 2

    def test_valid_file_returns_zero(self):
        path = _write_tmp_json(VALID_BUNDLE)
        try:
            code = run([str(path)])
            assert code == 0
        finally:
            os.unlink(str(path))

    def test_output_file(self):
        path = _write_tmp_json(VALID_BUNDLE)
        out_path_obj = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_path = out_path_obj.name
        out_path_obj.close()
        try:
            code = run([str(path), "--output", out_path])
            assert code == 0
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["operation_count"] == 1
        finally:
            os.unlink(str(path))
            os.unlink(out_path)

    def test_empty_bundle_returns_one(self):
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 0,
            "records": [],
        }
        path = _write_tmp_json(bundle)
        try:
            code = run([str(path)])
            assert code == 1
        finally:
            os.unlink(str(path))

    def test_all_records_invalid_returns_one(self):
        record = dict(VALID_RECORD)
        record["ci_artifact"] = 1234
        bundle = {
            "schema_version": "test-metadata-import-bundle/v1",
            "source_scanner": "test_metadata_scanner/v1.0.0",
            "record_count": 1,
            "records": [record],
        }
        path = _write_tmp_json(bundle)
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
        path = _write_tmp_json(VALID_BUNDLE)
        try:
            with open(str(path), encoding="utf-8") as f:
                content = f.read()
            monkeypatch.setattr("sys.stdin.read", lambda: content)
            code = run(["-"])
            assert code == 0
        finally:
            os.unlink(str(path))
