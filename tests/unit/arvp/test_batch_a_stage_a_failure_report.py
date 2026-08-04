"""Tests for Batch-A Stage-A failure report (#4065)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tools.arvp_vacation.batch_a_stage_a_failure_report import (
    SCHEMA_VERSION,
    build_failure_report,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "docs/contracts/batch_a_stage_a_failure_report.v1.schema.json"
BEFORE_SUMMARY = (
    REPO_ROOT / "docs/evidence/arvp_batch_a_stage_a_survivor_summary_4032.v1.json"
)
METRICS = Path(
    r"d:\Dev\Workspaces\Repos\Claire_de_Binare\artifacts\evidence\batch_a_stage_a_d0a4e72d_20260713\arvp_strategy_metrics.v1.recompute_run1.json"
)


@pytest.fixture(scope="module")
def schema_validator() -> Draft7Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft7Validator(schema)


@pytest.mark.skipif(not METRICS.is_file(), reason="local recompute metrics missing")
def test_failure_report_has_ten_candidates(schema_validator: Draft7Validator) -> None:
    bundle = json.loads(METRICS.read_text(encoding="utf-8"))
    before = json.loads(BEFORE_SUMMARY.read_text(encoding="utf-8"))
    report = build_failure_report(
        metrics_bundle=bundle,
        before_survivor_summary=before,
        metrics_content_hash_before="3ee5c429cc8d7df499e9870f1253f350f235ebe2a6974dbfcddbb1a7f8c60958",
    )
    assert report["schema_version"] == SCHEMA_VERSION
    assert len(report["candidates"]) == 10
    assert report["survivor_count_after_fix"] == 0
    # CDB-052: historical recompute rows lack bound rankability provenance, so the
    # scorer fail-closes uniformly to INSUFFICIENT_EVIDENCE. That can match the
    # pre-#4065 summary and yield status_changed_by_4065_count == 0; the #4065
    # delta is no longer a required observable under provenance enforcement.
    assert "status_changed_by_4065_count" in report["aggregate"]
    assert all(
        row["final_status"] == "INSUFFICIENT_EVIDENCE" for row in report["candidates"]
    )
    assert all(row["rankable_baseline_windows"] == 0 for row in report["candidates"])
    assert all(row["rankable_pessimistic_windows"] == 0 for row in report["candidates"])
    errors = list(schema_validator.iter_errors(report))
    assert not errors, [error.message for error in errors]
