from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from tools.test_metadata_scanner import (
    REQUIRED_FIELDS,
    _find_metadata_blocks,
    _process_fields,
    _coerce_bool,
    scan_file,
    build_report,
    collect_paths,
    run,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PILOT_METADATA_FILE = (
    PROJECT_ROOT
    / "tests"
    / "unit"
    / "validation"
    / "test_profitability_evidence_packet_assembler.py"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_BLOCK = """\
# ===========================================================================
# Test-First Metadata (Pilot: CDB-PILOT-001)
# ===========================================================================
#
# Metadata fields (TEST_FIRST_PROCESSING_CONTRACT.md §7):
#   test_id:              cdb-test-pilot-001
#   test_title:           Profitability Evidence Packet Assembler
#   test_type:            mixed
#   cdb_area:             validation
#   rule_ref:             PROFITABILITY_EVIDENCE_PACKET_SCHEMA_CONFORMANCE
#   decision_ref:         d-2026-04-08-evidence-packet-structure
#   issue_ref:            #1492
#   pr_ref:               #3408
#   evidence_ref:         docs/contracts/profitability_evidence_packet.v1.schema.json
#   code_area:            ProfitabilityEvidencePacketAssembler
#   security_relevant:    false
#   live_relevant:        false
#   profitability_relevant: true
#   surrealdb_export:     false
#   ci_artifact:          test-report
# ===========================================================================
"""

VALID_BLOCK_SURRDB = """\
#   test_id:              tc-export-001
#   test_title:           Export-Ready Block
#   test_type:            bauteil
#   cdb_area:             risk
#   rule_ref:             EXPORT_TEST
#   decision_ref:         export test decision
#   issue_ref:            #9999
#   pr_ref:               #9999
#   evidence_ref:         docs/test/export.md
#   code_area:            services/risk/
#   security_relevant:    false
#   live_relevant:        false
#   profitability_relevant: false
#   surrealdb_export:     true
#   ci_artifact:          test-report
"""

PARTIAL_BLOCK = """\
#   test_id:              tc-partial-001
#   test_title:           Partial Block
#   test_type:            bauteil
#   cdb_area:             risk
#   rule_ref:             PARTIAL_TEST
#   decision_ref:         partial test decision
#   issue_ref:            #8888
#   pr_ref:               #8888
#   evidence_ref:         docs/test/partial.md
#   code_area:            services/risk/
#   security_relevant:    true
#   live_relevant:        false
   # missing: profitability_relevant, surrealdb_export, ci_artifact
"""

NO_METADATA_FILE = """\
from __future__ import annotations
import pytest

def test_something():
    assert True
"""


def _write_tmp_file(content: str, suffix: str = ".py") -> Path:
    fd, path = tempfile.mkstemp(suffix=suffix, text=True)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return Path(path)


# ---------------------------------------------------------------------------
# _find_metadata_blocks
# ---------------------------------------------------------------------------


class TestFindMetadataBlocks:
    def test_valid_block_found(self):
        blocks = _find_metadata_blocks(VALID_BLOCK)
        assert len(blocks) == 1
        fields = blocks[0]
        assert fields["test_id"] == "cdb-test-pilot-001"
        assert fields["surrealdb_export"] == "false"

    def test_surrealdb_true_detected(self):
        blocks = _find_metadata_blocks(VALID_BLOCK_SURRDB)
        assert len(blocks) == 1
        assert blocks[0]["surrealdb_export"] == "true"

    def test_partial_block(self):
        """A block missing some fields is still found but flagged later."""
        blocks = _find_metadata_blocks(PARTIAL_BLOCK)
        assert len(blocks) == 1
        assert "profitability_relevant" not in blocks[0]

    def test_no_metadata(self):
        blocks = _find_metadata_blocks(NO_METADATA_FILE)
        assert len(blocks) == 0

    def test_empty_content(self):
        blocks = _find_metadata_blocks("")
        assert len(blocks) == 0

    def test_multiple_blocks_separated(self):
        content = VALID_BLOCK + "\n\nsome_code()\n\n" + VALID_BLOCK_SURRDB
        blocks = _find_metadata_blocks(content)
        assert len(blocks) == 2


# ---------------------------------------------------------------------------
# _process_fields
# ---------------------------------------------------------------------------


class TestProcessFields:
    def test_valid_block(self):
        raw = {
            "test_id": "tc-001",
            "test_title": "Test",
            "test_type": "bauteil",
            "cdb_area": "risk",
            "rule_ref": "RULE-001",
            "decision_ref": "decision",
            "issue_ref": "#1",
            "pr_ref": "#1",
            "evidence_ref": "docs/test.md",
            "code_area": "risk/",
            "security_relevant": "true",
            "live_relevant": "false",
            "profitability_relevant": "false",
            "surrealdb_export": "true",
            "ci_artifact": "test-report",
        }
        processed, missing = _process_fields(raw)
        assert len(missing) == 0
        assert processed["test_id"] == "tc-001"
        assert processed["security_relevant"] is True
        assert processed["surrealdb_export"] is True
        assert processed["ci_artifact"] == "test-report"

    def test_missing_fields(self):
        raw = {
            "test_id": "tc-001",
            "test_title": "Test",
        }
        _, missing = _process_fields(raw)
        assert len(missing) > 0
        assert "test_type" in missing
        assert "cdb_area" in missing

    def test_all_fields_missing(self):
        _, missing = _process_fields({})
        assert len(missing) == len(REQUIRED_FIELDS)


# ---------------------------------------------------------------------------
# _coerce_bool
# ---------------------------------------------------------------------------


class TestCoerceBool:
    def test_true(self):
        assert _coerce_bool("true") is True
        assert _coerce_bool("  true  ") is True
        assert _coerce_bool("True") is True

    def test_false(self):
        assert _coerce_bool("false") is False
        assert _coerce_bool("False") is False
        assert _coerce_bool("") is False
        assert _coerce_bool("yes") is False
        assert _coerce_bool("1") is False


# ---------------------------------------------------------------------------
# scan_file
# ---------------------------------------------------------------------------


class TestScanFile:
    def test_valid_block(self):
        path = _write_tmp_file(VALID_BLOCK)
        result = scan_file(path)
        assert result["file"] == path.name
        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["is_valid"] is True
        assert result["validation_errors"] == []

    def test_surrealdb_export_true(self):
        path = _write_tmp_file(VALID_BLOCK_SURRDB)
        result = scan_file(path)
        assert result["blocks"][0]["surrealdb_export"] is True

    def test_actual_pilot001_is_export_ready(self):
        result = scan_file(PILOT_METADATA_FILE, repo_root=PROJECT_ROOT)
        assert result["file"] == (
            "tests/unit/validation/" "test_profitability_evidence_packet_assembler.py"
        )
        assert len(result["blocks"]) == 1
        assert result["validation_errors"] == []

        block = result["blocks"][0]
        fields = block["fields"]
        assert block["is_valid"] is True
        assert block["surrealdb_export"] is True
        assert fields["test_id"] == "cdb-test-pilot-001"
        assert fields["surrealdb_export"] is True
        assert fields["ci_artifact"] == "test-report"
        assert set(fields) == set(REQUIRED_FIELDS)

    def test_partial_block_flags_errors(self):
        path = _write_tmp_file(PARTIAL_BLOCK)
        result = scan_file(path)
        assert len(result["validation_errors"]) == 1
        assert (
            "profitability_relevant" in result["validation_errors"][0]["missing_fields"]
        )
        assert "surrealdb_export" in result["validation_errors"][0]["missing_fields"]
        assert "ci_artifact" in result["validation_errors"][0]["missing_fields"]

    def test_no_metadata(self):
        path = _write_tmp_file(NO_METADATA_FILE)
        result = scan_file(path)
        assert len(result["blocks"]) == 0
        assert result["validation_errors"] == []

    def test_nonexistent_file(self):
        path = Path("nonexistent_file_xyz.py")
        result = scan_file(path)
        assert "error" in result
        assert result["blocks"] == []

    def test_repo_root_relative(self):
        path = _write_tmp_file(VALID_BLOCK)
        repo_root = path.parent
        result = scan_file(path, repo_root=repo_root)
        # Relative path must not contain the repo_root as a prefix
        rel = result["file"]
        assert not rel.startswith(
            str(repo_root)
        ), f"{rel} should be relative to {repo_root}"


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


class TestBuildReport:
    def test_empty_results(self):
        report = build_report([])
        assert report["scanned_files"] == 0
        assert report["total_blocks"] == 0
        assert report["total_errors"] == 0

    def test_valid_results(self):
        path = _write_tmp_file(VALID_BLOCK)
        results = [scan_file(path)]
        report = build_report(results)
        assert report["scanned_files"] == 1
        assert report["total_blocks"] == 1
        assert report["total_errors"] == 0

    def test_surrealdb_ready_count(self):
        path1 = _write_tmp_file(VALID_BLOCK_SURRDB)
        path2 = _write_tmp_file(VALID_BLOCK)
        results = [scan_file(path1), scan_file(path2)]
        report = build_report(results)
        assert report["surrealdb_export_ready"] == 1

    def test_deterministic_order(self):
        path_a = _write_tmp_file(VALID_BLOCK)
        path_b = _write_tmp_file(VALID_BLOCK_SURRDB)
        res1 = build_report([scan_file(path_a), scan_file(path_b)])
        res2 = build_report([scan_file(path_b), scan_file(path_a)])
        # Results are in input order; build_report doesn't sort
        assert res1["results"][0]["file"] != res2["results"][0]["file"]

    def test_no_absolute_paths_in_output(self):
        path = _write_tmp_file(VALID_BLOCK)
        result = scan_file(path)
        # No drive letter or root slash in the 'file' field
        file_path = result["file"]
        assert ":" not in file_path  # no Windows drive letter
        assert "\\" not in file_path or "\\\\" not in file_path

    def test_actual_pilot001_report_is_stable_and_machine_readable(self):
        report1 = build_report([scan_file(PILOT_METADATA_FILE, repo_root=PROJECT_ROOT)])
        report2 = build_report([scan_file(PILOT_METADATA_FILE, repo_root=PROJECT_ROOT)])

        assert report1 == report2
        assert set(report1) == {
            "scanner_version",
            "scanned_files",
            "total_blocks",
            "total_errors",
            "surrealdb_export_ready",
            "results",
        }
        assert report1["scanned_files"] == 1
        assert report1["total_blocks"] == 1
        assert report1["total_errors"] == 0
        assert report1["surrealdb_export_ready"] == 1
        assert ":" not in report1["results"][0]["file"]


# ---------------------------------------------------------------------------
# collect_paths
# ---------------------------------------------------------------------------


class TestCollectPaths:
    def test_single_file(self):
        path = _write_tmp_file(VALID_BLOCK)
        files = collect_paths([str(path)])
        assert len(files) >= 1

    def test_non_py_file_skipped(self):
        path = _write_tmp_file("hello world", suffix=".txt")
        files = collect_paths([str(path)])
        assert len(files) == 0

    def test_directory_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            f1 = d / "test_a.py"
            f2 = d / "sub" / "test_b.py"
            f2.parent.mkdir()
            f1.write_text("", encoding="utf-8")
            f2.write_text("", encoding="utf-8")
            files = collect_paths([str(d)])
            assert len(files) == 2

    def test_nonexistent_path_warns(self, capsys):
        files = collect_paths(["nonexistent_dir_xyz"])
        captured = capsys.readouterr()
        assert "Warning" in captured.err


# ---------------------------------------------------------------------------
# run() integration
# ---------------------------------------------------------------------------


class TestRun:
    def test_stdout_no_blocks(self):
        path = _write_tmp_file(NO_METADATA_FILE)
        code = run([str(path)])
        assert code == 0

    def test_valid_returns_zero(self):
        path = _write_tmp_file(VALID_BLOCK)
        code = run([str(path)])
        assert code == 0

    def test_partial_returns_one(self):
        path = _write_tmp_file(PARTIAL_BLOCK)
        code = run([str(path)])
        assert code == 1

    def test_output_file(self):
        path = _write_tmp_file(VALID_BLOCK)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            out_path = f.name
        try:
            code = run([str(path), "--output", out_path])
            assert code == 0
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
            assert data["total_blocks"] == 1
        finally:
            os.unlink(out_path)

    def test_no_files_returns_two(self):
        code = run(["nonexistent_dir_xyz"])
        assert code == 2
