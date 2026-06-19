from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.evidence_harvester.validation import (
    ALLOWED_SOURCE_MODES,
    DEFAULT_CADENCE_TOLERANCE_MINUTES,
    DEFAULT_EXPECTED_SNAPSHOT_COUNT,
    EXPECTED_ALERT_SCHEMA,
    EXPECTED_SNAPSHOT_SCHEMA,
    SAFETY_BANNER,
    ValidationError,
    ValidationReport,
    validate_24h_window,
    validate_24h_window_from_dir,
    report_to_markdown,
)

_NOW = datetime(2026, 6, 19, 16, 0, 0, tzinfo=UTC)
_WINDOW_START = datetime(2026, 6, 18, 16, 0, 0, tzinfo=UTC)
_WINDOW_END = _NOW
_SNAPSHOT_TS = "2026-06-19T14:00:00Z"


def _valid_snapshot_payload(overrides: dict | None = None) -> dict:
    payload = {
        "metadata": {
            "schema_version": EXPECTED_SNAPSHOT_SCHEMA,
            "generated_at_utc": _SNAPSHOT_TS,
            "collector_report_hash": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "collector_report_id": "harv-test123",
            "collector_report_schema_version": "evidence_harvester.collector_report.v1",
            "source_mode": "fixture",
            "evidence_class": "pipeline_test_evidence",
            "evidence_class_version": "1.0",
            "produced_by": "test",
            "collector_report_produced_at_utc": "2026-06-19T12:00:00Z",
        },
        "status": {
            "overall_status": "ok",
            "gap_counts": {"blocking": 0, "warning": 0, "info": 0},
            "has_zero_paper_chains": False,
            "raw_evidence": {
                "candle_input_count": 1,
                "regime_input_count": 1,
                "paper_chain_input_count": 1,
                "provenance_input_count": 1,
                "observed_input_count": 4,
            },
        },
        "coverage": {
            "candles": {
                "status": "ok",
                "total_streams": 1,
                "observed_count_total": 100,
                "expected_count_total": 100,
                "coverage_pct": 1.0,
                "stale_stream_count": 0,
                "status_counts": {"blocking": 0, "warning": 0, "info": 1},
                "items": [],
            },
            "regimes": {
                "status": "ok",
                "total_streams": 1,
                "observed_count_total": 100,
                "expected_count_total": 100,
                "coverage_pct": 1.0,
                "zero_coverage_stream_count": 0,
                "status_counts": {"blocking": 0, "warning": 0, "info": 1},
                "items": [],
            },
        },
        "provenance": {
            "status": "ok",
            "allowed_sources": ["mexc"],
            "unknown_source_count": 0,
            "contaminated_source_count": 0,
            "source_findings": [],
        },
        "paper_chains": {
            "status": "ok",
            "total_streams": 1,
            "signal_count_total": 10,
            "decision_count_total": 5,
            "order_count_total": 3,
            "fill_count_total": 3,
            "complete_chain_count_total": 3,
            "partial_chain_count_total": 0,
            "zero_complete_stream_count": 0,
            "zero_signal_stream_count": 0,
            "average_signal_density_per_hour": 0.5,
            "status_counts": {"blocking": 0, "warning": 0, "info": 1},
            "items": [],
        },
        "gap_findings": {
            "summary": {
                "total_count": 0,
                "blocking_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "by_type": {},
            },
            "items": [],
        },
        "safety": {
            "banner": SAFETY_BANNER,
            "lr_status": "NO-GO",
            "live_status": "NO-GO",
            "echtgeld_status": "NO-GO",
            "runtime_actions": "not_allowed",
            "db_execution": "not_allowed",
            "background_job_orchestration": "not_in_scope",
            "allowed_scope": "fixture/mock-based collector report snapshot generation only",
        },
        "next_action_hints": [],
    }
    if overrides:
        _deep_merge(payload, overrides)
    return payload


def _valid_alert_payload(overrides: dict | None = None) -> dict:
    payload = {
        "schema_version": EXPECTED_ALERT_SCHEMA,
        "evaluated_at_utc": "2026-06-19T15:00:00Z",
        "snapshot_generated_at_utc": _SNAPSHOT_TS,
        "collector_report_id": "harv-test123",
        "collector_report_hash": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "snapshot_age_minutes": 60,
        "summary": {
            "highest_severity": "info",
            "total_count": 0,
            "critical_count": 0,
            "warn_count": 0,
            "info_count": 0,
            "manual_escalation_recommended": False,
        },
        "findings": [],
        "manual_escalation_only": True,
    }
    if overrides:
        _deep_merge(payload, overrides)
    return payload


def _deep_merge(target: dict, source: dict) -> None:
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


class TestValidate24hWindow:
    def test_pass_with_valid_artifacts(self, tmp_path: Path) -> None:
        snap_path = _write_json(
            tmp_path / "snapshot_20260619.json", _valid_snapshot_payload()
        )
        alert_path = _write_json(
            tmp_path / "alert_20260619.json", _valid_alert_payload()
        )
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "PASS"
        assert report.summary.fail_count == 0

    def test_fail_on_missing_snapshot(self, tmp_path: Path) -> None:
        report = validate_24h_window(
            [],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
            expected_snapshot_count=1,
        )
        assert report.summary.verdict == "FAIL"
        assert any("Expected at least 1 snapshot" in f.message for f in report.findings)

    def test_fail_on_invalid_json(self, tmp_path: Path) -> None:
        snap_path = tmp_path / "snapshot_bad.json"
        snap_path.write_text("not json", encoding="utf-8")
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any("Failed to parse" in f.message for f in report.findings)

    def test_fail_on_wrong_schema_version(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload(
            {"metadata": {"schema_version": "wrong.version"}}
        )
        snap_path = _write_json(tmp_path / "snapshot_bad_schema.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any(
            "schema_version" in f.message
            for f in report.findings
            if f.severity == "fail"
        )

    def test_fail_on_wrong_alert_schema(self, tmp_path: Path) -> None:
        snap_path = _write_json(tmp_path / "snap.json", _valid_snapshot_payload())
        alert_payload = _valid_alert_payload({"schema_version": "wrong.alert.version"})
        alert_path = _write_json(tmp_path / "alert.json", alert_payload)
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any(
            "schema_version" in f.message
            for f in report.findings
            if f.severity == "fail"
        )

    def test_fail_on_missing_collector_hash(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"metadata": {"collector_report_hash": ""}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any(
            "collector_report_hash" in f.message
            for f in report.findings
            if f.severity == "fail"
        )

    def test_fail_on_lr_go_safety_flag(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"safety": {"lr_status": "GO"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any(
            "lr_status" in f.message for f in report.findings if f.severity == "fail"
        )

    def test_fail_on_live_go_safety_flag(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"safety": {"live_status": "GO"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_fail_on_echtgeld_go_safety_flag(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"safety": {"echtgeld_status": "GO"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_fail_on_forbidden_source_mode(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"metadata": {"source_mode": "live"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_warn_on_missing_alert_report(self, tmp_path: Path) -> None:
        snap_path = _write_json(tmp_path / "snap.json", _valid_snapshot_payload())
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "WARN"
        assert any("No alert report provided" in f.message for f in report.findings)

    def test_warn_on_forbidden_content(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload()
        payload["metadata"]["collector_report_id"] = "trade_executed_ref"
        snap_path = _write_json(tmp_path / "snap.json", payload)
        alert_path = _write_json(tmp_path / "alert.json", _valid_alert_payload())
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any(
            "trade_executed" in f.message
            for f in report.findings
            if f.severity == "fail"
        )

    def test_alert_manual_escalation_flag_fail(self, tmp_path: Path) -> None:
        snap_path = _write_json(tmp_path / "snap.json", _valid_snapshot_payload())
        alert_payload = _valid_alert_payload({"manual_escalation_only": False})
        alert_path = _write_json(tmp_path / "alert.json", alert_payload)
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_generated_at_utc_empty_fails(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"metadata": {"generated_at_utc": ""}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_invalid_generated_at_utc_fails(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload(
            {"metadata": {"generated_at_utc": "not-a-date"}}
        )
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_safety_banner_mismatch_fails(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"safety": {"banner": "Wrong banner text"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_timestamp_outside_window_warns(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload(
            {"metadata": {"generated_at_utc": "2026-06-17T12:00:00Z"}}
        )
        snap_path = _write_json(tmp_path / "snap.json", payload)
        alert_path = _write_json(tmp_path / "alert.json", _valid_alert_payload())
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "WARN"

    def test_cadence_gap_warns(self, tmp_path: Path) -> None:
        ts1 = "2026-06-19T10:00:00Z"
        ts2 = "2026-06-19T14:00:00Z"
        snap1 = _write_json(
            tmp_path / "snap_early.json",
            _valid_snapshot_payload({"metadata": {"generated_at_utc": ts1}}),
        )
        snap2 = _write_json(
            tmp_path / "snap_late.json",
            _valid_snapshot_payload({"metadata": {"generated_at_utc": ts2}}),
        )
        alert_path = _write_json(tmp_path / "alert.json", _valid_alert_payload())
        report = validate_24h_window(
            [snap1, snap2],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
            cadence_tolerance_minutes=60,
        )
        assert report.summary.verdict == "WARN"
        assert any("Gap" in f.message for f in report.findings if f.severity == "warn")

    def test_validation_error_on_bad_window(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="window_end_utc must be after"):
            validate_24h_window(
                [],
                [],
                window_start_utc=_WINDOW_END,
                window_end_utc=_WINDOW_START,
            )

    def test_validation_error_on_negative_count(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            validate_24h_window(
                [],
                [],
                window_start_utc=_WINDOW_START,
                window_end_utc=_WINDOW_END,
                expected_snapshot_count=0,
            )

    def test_report_to_markdown(self, tmp_path: Path) -> None:
        snap_path = _write_json(tmp_path / "snap.json", _valid_snapshot_payload())
        alert_path = _write_json(tmp_path / "alert.json", _valid_alert_payload())
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        md = report_to_markdown(report)
        assert "PASS" in md
        assert "24h Dry Validation Report" in md
        assert "No LR-Go" in md

    def test_fail_on_runtime_actions_allowed(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"safety": {"runtime_actions": "allowed"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_fail_on_db_execution_allowed(self, tmp_path: Path) -> None:
        payload = _valid_snapshot_payload({"safety": {"db_execution": "allowed"}})
        snap_path = _write_json(tmp_path / "snap.json", payload)
        report = validate_24h_window(
            [snap_path],
            [],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_forbidden_content_in_alert(self, tmp_path: Path) -> None:
        snap_path = _write_json(tmp_path / "snap.json", _valid_snapshot_payload())
        alert_payload = _valid_alert_payload()
        alert_payload["collector_report_id"] = "order_submitted_ref"
        alert_path = _write_json(tmp_path / "alert.json", alert_payload)
        report = validate_24h_window(
            [snap_path],
            [alert_path],
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"
        assert any(
            "order_submitted" in f.message
            for f in report.findings
            if f.severity == "fail"
        )


class TestValidate24hWindowFromDir:
    def test_pass_with_dir(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "snapshot_20260619.json", _valid_snapshot_payload())
        _write_json(tmp_path / "alert_20260619.json", _valid_alert_payload())
        report = validate_24h_window_from_dir(
            tmp_path,
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "PASS"

    def test_fail_empty_dir(self, tmp_path: Path) -> None:
        report = validate_24h_window_from_dir(
            tmp_path,
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "FAIL"

    def test_error_on_nonexistent_dir(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="does not exist"):
            validate_24h_window_from_dir(
                tmp_path / "nonexistent",
                window_start_utc=_WINDOW_START,
                window_end_utc=_WINDOW_END,
            )

    def test_alert_reports_with_alerts_prefix(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "snapshot_1.json", _valid_snapshot_payload())
        _write_json(tmp_path / "alerts_1.json", _valid_alert_payload())
        report = validate_24h_window_from_dir(
            tmp_path,
            window_start_utc=_WINDOW_START,
            window_end_utc=_WINDOW_END,
        )
        assert report.summary.verdict == "PASS"

    def test_schema_version_field(self) -> None:
        report = ValidationReport(
            schema_version="cdb.evidence_harvester.24h_validation.v1",
            validated_at_utc="2026-06-19T16:00:00Z",
            window_start_utc="2026-06-18T16:00:00Z",
            window_end_utc="2026-06-19T16:00:00Z",
            snapshot_count=0,
            alert_report_count=0,
            findings=(),
            summary=type(
                "Summary",
                (),
                {
                    "verdict": "PASS",
                    "total_checks": 0,
                    "fail_count": 0,
                    "warn_count": 0,
                    "pass_count": 0,
                },
            )(),
        )
        assert report.schema_version == "cdb.evidence_harvester.24h_validation.v1"


class TestCli:
    def test_validate_dir_help(self) -> None:
        from tools.evidence_harvester.validation import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--help"])

    def test_validate_dir_no_subcommand(self) -> None:
        from tools.evidence_harvester.validation import parse_args

        with pytest.raises(SystemExit):
            parse_args([])

    def test_validate_dir_missing_artifact_dir(self) -> None:
        from tools.evidence_harvester.validation import parse_args

        with pytest.raises(SystemExit):
            parse_args(["validate-dir"])
