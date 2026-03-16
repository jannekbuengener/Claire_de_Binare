"""Unit tests for infrastructure/scripts/shadow_metrics_compare.py.

Tests prove fail-closed behaviour:
- UNCALIBRATED (all null) → exit 1
- PASS (calibrated thresholds satisfied) → exit 0
- FAIL (threshold violated) → exit 1
- actual=None with calibrated threshold → FAIL
- unknown spec key → FAIL
- missing evidence_index.json → exit 1
- missing thresholds file → exit 1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "infrastructure" / "scripts"))

from shadow_metrics_compare import (
    _evaluate_check,
    _write_artefacts,
    compare_shadow_metrics,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_evidence(tmp_path: Path, metrics: dict) -> Path:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "evidence_index.json").write_text(
        json.dumps({"schema_version": "1.0", **metrics}), encoding="utf-8"
    )
    return evidence_dir


def _write_thresholds(tmp_path: Path, thresholds: dict, calibration_status: str = "CALIBRATED") -> Path:
    path = tmp_path / "thresholds.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "calibration_status": calibration_status,
                "thresholds": thresholds,
            }
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# _evaluate_check unit tests
# ---------------------------------------------------------------------------


def test_evaluate_check_skip_all_null():
    result = _evaluate_check("signals_received", {"min": None}, 42)
    assert result["result"] == "SKIP"


def test_evaluate_check_pass_min():
    result = _evaluate_check("signals_received", {"min": 1}, 5)
    assert result["result"] == "PASS"


def test_evaluate_check_fail_min():
    result = _evaluate_check("signals_received", {"min": 10}, 5)
    assert result["result"] == "FAIL"


def test_evaluate_check_pass_max():
    result = _evaluate_check("orders_approved", {"max": 0}, 0)
    assert result["result"] == "PASS"


def test_evaluate_check_fail_max():
    result = _evaluate_check("orders_approved", {"max": 0}, 1)
    assert result["result"] == "FAIL"


def test_evaluate_check_pass_exact_bool():
    result = _evaluate_check("has_live_data", {"exact": True}, True)
    assert result["result"] == "PASS"


def test_evaluate_check_fail_exact_bool():
    result = _evaluate_check("has_live_data", {"exact": True}, False)
    assert result["result"] == "FAIL"


def test_evaluate_check_fail_actual_none_with_calibrated_threshold():
    """actual=None with a calibrated threshold must FAIL (fail-closed)."""
    result = _evaluate_check("signals_received", {"min": 1}, None)
    assert result["result"] == "FAIL"
    assert "unavailable" in result.get("reason", "")


def test_evaluate_check_fail_unknown_spec_key_nonnull():
    """Typo in spec key with non-null value must FAIL, not silently SKIP."""
    result = _evaluate_check("signals_received", {"minn": 5}, 10)
    assert result["result"] == "FAIL"
    assert "invalid threshold spec keys" in result.get("reason", "")


def test_evaluate_check_skip_unknown_spec_key_null():
    """Unknown spec key with null value is harmless — treated as all-null SKIP."""
    result = _evaluate_check("signals_received", {"minn": None}, 10)
    assert result["result"] == "SKIP"


# ---------------------------------------------------------------------------
# compare_shadow_metrics integration tests
# ---------------------------------------------------------------------------


def test_all_null_thresholds_is_uncalibrated(tmp_path):
    """All-null thresholds → UNCALIBRATED verdict."""
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 5})
    thresholds_path = _write_thresholds(
        tmp_path,
        {"signals_received": {"min": None}},
        calibration_status="UNCALIBRATED",
    )
    report, md = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "UNCALIBRATED"
    assert report["failures"] == []
    assert "signals_received" in report["skipped_uncalibrated"]
    assert "UNCALIBRATED" in md


def test_calibrated_pass(tmp_path):
    """Single calibrated threshold satisfied → PASS."""
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 5, "orders_filled": 0})
    thresholds_path = _write_thresholds(
        tmp_path,
        {
            "signals_received": {"min": 1},
            "orders_filled": {"exact": None},  # null → skip
        },
    )
    report, _ = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "PASS"
    assert report["failures"] == []


def test_calibrated_fail(tmp_path):
    """Calibrated threshold violated → FAIL."""
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 0})
    thresholds_path = _write_thresholds(
        tmp_path,
        {"signals_received": {"min": 1}},
    )
    report, _ = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "FAIL"
    assert "signals_received" in report["failures"]


def test_mixed_null_and_satisfied(tmp_path):
    """Mix of null + calibrated satisfied → PASS (only non-null compared)."""
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 5, "orders_filled": 0})
    thresholds_path = _write_thresholds(
        tmp_path,
        {
            "signals_received": {"min": 1},     # calibrated, passes
            "orders_filled": {"exact": None},    # null → skip
        },
    )
    report, _ = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "PASS"
    assert "orders_filled" in report["skipped_uncalibrated"]


def test_mixed_null_and_violated(tmp_path):
    """Mix of null + calibrated violated → FAIL."""
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 0, "orders_filled": 0})
    thresholds_path = _write_thresholds(
        tmp_path,
        {
            "signals_received": {"min": 10},    # calibrated, fails
            "orders_filled": {"exact": None},   # null → skip
        },
    )
    report, _ = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "FAIL"
    assert "signals_received" in report["failures"]


def test_actual_none_with_calibrated_threshold_is_fail(tmp_path):
    """Metric missing from evidence_index with calibrated threshold → FAIL (fail-closed)."""
    evidence_dir = _write_evidence(tmp_path, {})  # no signals_received key
    thresholds_path = _write_thresholds(tmp_path, {"signals_received": {"min": 1}})
    report, _ = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "FAIL"
    assert "signals_received" in report["failures"]


def test_unknown_spec_key_nonnull_is_fail(tmp_path):
    """Typo in threshold spec key → FAIL, never silently skip."""
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 10})
    thresholds_path = _write_thresholds(tmp_path, {"signals_received": {"minn": 5}})
    report, _ = compare_shadow_metrics(evidence_dir, thresholds_path)
    assert report["verdict"] == "FAIL"
    assert "signals_received" in report["failures"]


# ---------------------------------------------------------------------------
# Artefact output tests
# ---------------------------------------------------------------------------


def test_artefacts_written_on_pass(tmp_path):
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 5})
    thresholds_path = _write_thresholds(tmp_path, {"signals_received": {"min": 1}})
    report, md = compare_shadow_metrics(evidence_dir, thresholds_path)
    _write_artefacts(evidence_dir, report, md)
    assert (evidence_dir / "shadow_metrics_comparison.json").is_file()
    assert (evidence_dir / "shadow_metrics_comparison.md").is_file()
    written = json.loads((evidence_dir / "shadow_metrics_comparison.json").read_text())
    assert written["verdict"] == "PASS"


def test_artefacts_written_on_uncalibrated(tmp_path):
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 5})
    thresholds_path = _write_thresholds(
        tmp_path, {"signals_received": {"min": None}}, calibration_status="UNCALIBRATED"
    )
    report, md = compare_shadow_metrics(evidence_dir, thresholds_path)
    _write_artefacts(evidence_dir, report, md)
    written = json.loads((evidence_dir / "shadow_metrics_comparison.json").read_text())
    assert written["verdict"] == "UNCALIBRATED"


# ---------------------------------------------------------------------------
# Missing-file error propagation (compare_shadow_metrics raises, main exits 1)
# ---------------------------------------------------------------------------


def test_missing_evidence_index_raises(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    # No evidence_index.json
    thresholds_path = _write_thresholds(tmp_path, {"signals_received": {"min": 1}})
    with pytest.raises(FileNotFoundError):
        compare_shadow_metrics(evidence_dir, thresholds_path)


def test_missing_thresholds_file_raises(tmp_path):
    evidence_dir = _write_evidence(tmp_path, {"signals_received": 5})
    thresholds_path = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        compare_shadow_metrics(evidence_dir, thresholds_path)
