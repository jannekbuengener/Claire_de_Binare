from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.evidence_harvester.ops_validation import (
    BOOT_READINESS_SCHEMA,
    DEFAULT_REQUIRED_WINDOW_HOURS,
    OPS_VALIDATION_SCHEMA_VERSION,
    OpsValidationError,
    RuntimeHandoff,
    report_to_markdown,
    validate_72h_window_from_dir,
)
from tools.evidence_harvester.snapshot import SAFETY_BANNER, SNAPSHOT_SCHEMA_VERSION
from tools.evidence_harvester.validation import EXPECTED_ALERT_SCHEMA
from tools.evidence_harvester.write_audit import (
    COLLECTOR_REPORT_SCHEMA,
    WRITE_AUDIT_REPORT_SCHEMA,
)
from tools.evidence_harvester.watchdog import WATCHDOG_REPORT_SCHEMA

HEARTBEAT_SCHEMA = "cdb.evidence_harvester.runner_heartbeat.v1"
STATE_SCHEMA = "cdb.evidence_harvester.runner_state.v1"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str = "ok\n") -> None:
    path.write_text(text, encoding="utf-8")


def _deep_merge(target: dict, source: dict) -> None:
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def _snapshot_payload(ts: str, overrides: dict | None = None) -> dict:
    payload = {
        "metadata": {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "generated_at_utc": ts,
            "collector_report_hash": (
                "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
            ),
            "collector_report_id": "harv-test123",
            "collector_report_schema_version": COLLECTOR_REPORT_SCHEMA,
            "source_mode": "fixture",
            "evidence_class": "pipeline_test_evidence",
            "evidence_class_version": "1.0",
            "produced_by": "test",
            "collector_report_produced_at_utc": ts,
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


def _alert_payload(ts: str, overrides: dict | None = None) -> dict:
    payload = {
        "schema_version": EXPECTED_ALERT_SCHEMA,
        "evaluated_at_utc": ts,
        "snapshot_generated_at_utc": ts,
        "collector_report_id": "harv-test123",
        "collector_report_hash": (
            "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        ),
        "snapshot_age_minutes": 1,
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


def _collector_payload(ts: str) -> dict:
    return {
        "schema_version": COLLECTOR_REPORT_SCHEMA,
        "collector_report_id": "harv-test123",
        "generated_at_utc": ts,
        "source_mode": "fixture",
    }


def _watchdog_payload(ts: str, verdict: str = "PASS") -> dict:
    return {
        "schema_version": WATCHDOG_REPORT_SCHEMA,
        "evaluated_at_utc": ts,
        "artifact_dir": "test",
        "mode": "status",
        "heartbeat_fresh": verdict != "FAIL",
        "runner_state_ok": verdict != "FAIL",
        "required_artifacts_present": True,
        "verdict": {
            "verdict": verdict,
            "total_checks": 10,
            "pass_count": 10 if verdict == "PASS" else 8,
            "warn_count": 0 if verdict == "PASS" else 2,
            "fail_count": 1 if verdict == "FAIL" else 0,
        },
        "findings": [],
    }


def _write_audit_payload(ts: str, verdict: str = "PASS") -> dict:
    return {
        "schema_version": WRITE_AUDIT_REPORT_SCHEMA,
        "evaluated_at_utc": ts,
        "artifact_dir": "test",
        "required_artifacts_present": True,
        "all_json_parse": True,
        "schema_versions_match": True,
        "hash_linkage_valid": True,
        "safety_flags_correct": True,
        "timestamps_coherent": True,
        "source_modes_valid": True,
        "sizes_sane": True,
        "verdict": {
            "verdict": verdict,
            "total_checks": 10,
            "pass_count": 10 if verdict == "PASS" else 8,
            "warn_count": 0 if verdict == "PASS" else 2,
            "fail_count": 1 if verdict == "FAIL" else 0,
        },
        "findings": [],
    }


def _boot_payload(ts: str, verdict: str = "PASS") -> dict:
    return {
        "schema_version": BOOT_READINESS_SCHEMA,
        "evaluated_at_utc": ts,
        "mode": "status",
        "repo_root_valid": True,
        "harvester_modules_importable": True,
        "artifact_dirs_available": True,
        "scheduler_script_present": True,
        "command_plan_available": True,
        "docker_available": False,
        "safety_boundaries_ok": True,
        "verdict": {
            "verdict": verdict,
            "total_checks": 8,
            "pass_count": 8 if verdict == "PASS" else 7,
            "warn_count": 0 if verdict == "PASS" else 1,
            "fail_count": 1 if verdict == "FAIL" else 0,
        },
        "findings": [],
    }


def _heartbeat_payload(started_at: str, current_ts: str, iteration: int) -> dict:
    return {
        "schema_version": HEARTBEAT_SCHEMA,
        "runner_mode": "loop-fixture",
        "iteration": iteration,
        "started_at_utc": started_at,
        "current_run_at_utc": current_ts,
        "last_success_at_utc": current_ts,
        "last_failure_at_utc": "",
        "last_error": "",
        "last_collector_report": "collector_report_test.json",
        "last_snapshot_json": "snapshot_test.json",
        "last_snapshot_markdown": "snapshot_test.md",
        "last_alert_json": "alert_test.json",
        "last_alert_markdown": "alert_test.md",
    }


def _state_payload(current_ts: str, runs: int, verdict: str = "PASS") -> dict:
    return {
        "schema_version": STATE_SCHEMA,
        "total_runs": runs,
        "successful_runs": runs if verdict == "PASS" else max(0, runs - 1),
        "failed_runs": 0 if verdict == "PASS" else 1,
        "last_cycle_verdict": verdict,
        "last_cycle_ended_at_utc": current_ts,
    }


def _stamp(ts: datetime) -> str:
    return ts.strftime("%Y%m%dT%H%M%SZ")


def _ts(ts: datetime) -> str:
    return ts.isoformat().replace("+00:00", "Z")


def _write_valid_run(
    artifact_dir: Path,
    *,
    start: datetime,
    hours: int,
    cadence_seconds: int,
    boot_verdict: str = "PASS",
    watchdog_verdict: str = "PASS",
    write_audit_verdict: str = "PASS",
    snapshot_overrides: dict | None = None,
) -> None:
    times: list[datetime] = []
    current = start
    end = start + timedelta(hours=hours)
    while current <= end:
        times.append(current)
        current += timedelta(seconds=cadence_seconds)
    for ts in times:
        stamp = _stamp(ts)
        iso = _ts(ts)
        _write_json(
            artifact_dir / f"collector_report_{stamp}.json", _collector_payload(iso)
        )
        _write_json(
            artifact_dir / f"snapshot_{stamp}.json",
            _snapshot_payload(iso, snapshot_overrides),
        )
        _write_text(artifact_dir / f"snapshot_{stamp}.md")
        _write_json(artifact_dir / f"alert_{stamp}.json", _alert_payload(iso))
        _write_text(artifact_dir / f"alert_{stamp}.md")
        _write_json(
            artifact_dir / f"watchdog_report_{stamp}.json",
            _watchdog_payload(iso, watchdog_verdict),
        )
        _write_text(artifact_dir / f"watchdog_report_{stamp}.md")
        _write_json(
            artifact_dir / f"write_audit_report_{stamp}.json",
            _write_audit_payload(iso, write_audit_verdict),
        )
        _write_text(artifact_dir / f"write_audit_report_{stamp}.md")

    final_ts = _ts(times[-1])
    _write_json(
        artifact_dir / "runner_heartbeat.json",
        _heartbeat_payload(_ts(times[0]), final_ts, len(times)),
    )
    _write_json(
        artifact_dir / "runner_state.json",
        _state_payload(final_ts, len(times), "PASS"),
    )
    _write_json(
        artifact_dir / "boot_readiness_report.json",
        _boot_payload(final_ts, boot_verdict),
    )
    _write_text(artifact_dir / "boot_readiness_report.md")


class TestValidate72hWindowFromDir:
    @pytest.mark.unit
    def test_pass_with_valid_artifacts(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(tmp_path, start=start, hours=2, cadence_seconds=3600)
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "PASS"
        assert report.required_window_hours == 2
        assert report.observed_counts["watchdog_json"] == 3

    @pytest.mark.unit
    def test_fail_on_short_window(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(tmp_path, start=start, hours=1, cadence_seconds=3600)
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "FAIL"
        assert any("shorter than required 2h" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_fail_on_missing_heartbeat(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(tmp_path, start=start, hours=2, cadence_seconds=3600)
        (tmp_path / "runner_heartbeat.json").unlink()
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "FAIL"
        assert any("runner_heartbeat.json" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_fail_on_watchdog_fail(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(
            tmp_path,
            start=start,
            hours=2,
            cadence_seconds=3600,
            watchdog_verdict="FAIL",
        )
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "FAIL"
        assert any("Watchdog report is FAIL" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_fail_on_write_audit_fail(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(
            tmp_path,
            start=start,
            hours=2,
            cadence_seconds=3600,
            write_audit_verdict="FAIL",
        )
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "FAIL"
        assert any("Write-audit report is FAIL" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_warn_on_boot_warn(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(
            tmp_path,
            start=start,
            hours=2,
            cadence_seconds=3600,
            boot_verdict="WARN",
        )
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "WARN"
        assert any(
            "Boot readiness report is WARN" in f.message for f in report.findings
        )

    @pytest.mark.unit
    def test_fail_on_forbidden_content(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(
            tmp_path,
            start=start,
            hours=2,
            cadence_seconds=3600,
            snapshot_overrides={
                "metadata": {"collector_report_id": "trade_executed_ref"}
            },
        )
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "FAIL"
        assert any("trade_executed" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_warn_on_minor_cadence_drift(self, tmp_path: Path) -> None:
        t0 = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        times = [t0, t0 + timedelta(minutes=70), t0 + timedelta(hours=2)]
        for ts in times:
            stamp = _stamp(ts)
            iso = _ts(ts)
            _write_json(
                tmp_path / f"collector_report_{stamp}.json", _collector_payload(iso)
            )
            _write_json(tmp_path / f"snapshot_{stamp}.json", _snapshot_payload(iso))
            _write_text(tmp_path / f"snapshot_{stamp}.md")
            _write_json(tmp_path / f"alert_{stamp}.json", _alert_payload(iso))
            _write_text(tmp_path / f"alert_{stamp}.md")
            _write_json(
                tmp_path / f"watchdog_report_{stamp}.json", _watchdog_payload(iso)
            )
            _write_text(tmp_path / f"watchdog_report_{stamp}.md")
            _write_json(
                tmp_path / f"write_audit_report_{stamp}.json", _write_audit_payload(iso)
            )
            _write_text(tmp_path / f"write_audit_report_{stamp}.md")
        final_ts = _ts(times[-1])
        _write_json(
            tmp_path / "runner_heartbeat.json",
            _heartbeat_payload(_ts(times[0]), final_ts, len(times)),
        )
        _write_json(
            tmp_path / "runner_state.json", _state_payload(final_ts, len(times))
        )
        _write_json(tmp_path / "boot_readiness_report.json", _boot_payload(final_ts))
        _write_text(tmp_path / "boot_readiness_report.md")
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "WARN"
        assert any("warn threshold" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_fail_on_large_cadence_gap(self, tmp_path: Path) -> None:
        t0 = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        times = [t0, t0 + timedelta(hours=2, minutes=10), t0 + timedelta(hours=4)]
        for ts in times:
            stamp = _stamp(ts)
            iso = _ts(ts)
            _write_json(
                tmp_path / f"collector_report_{stamp}.json", _collector_payload(iso)
            )
            _write_json(tmp_path / f"snapshot_{stamp}.json", _snapshot_payload(iso))
            _write_text(tmp_path / f"snapshot_{stamp}.md")
            _write_json(tmp_path / f"alert_{stamp}.json", _alert_payload(iso))
            _write_text(tmp_path / f"alert_{stamp}.md")
            _write_json(
                tmp_path / f"watchdog_report_{stamp}.json", _watchdog_payload(iso)
            )
            _write_text(tmp_path / f"watchdog_report_{stamp}.md")
            _write_json(
                tmp_path / f"write_audit_report_{stamp}.json", _write_audit_payload(iso)
            )
            _write_text(tmp_path / f"write_audit_report_{stamp}.md")
        final_ts = _ts(times[-1])
        _write_json(
            tmp_path / "runner_heartbeat.json",
            _heartbeat_payload(_ts(times[0]), final_ts, len(times)),
        )
        _write_json(
            tmp_path / "runner_state.json", _state_payload(final_ts, len(times))
        )
        _write_json(tmp_path / "boot_readiness_report.json", _boot_payload(final_ts))
        _write_text(tmp_path / "boot_readiness_report.md")
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=4,
            runner_cadence_seconds=3600,
        )
        assert report.summary.verdict == "FAIL"
        assert any("fail threshold" in f.message for f in report.findings)

    @pytest.mark.unit
    def test_fail_on_nonexistent_dir(self, tmp_path: Path) -> None:
        with pytest.raises(OpsValidationError, match="does not exist"):
            validate_72h_window_from_dir(tmp_path / "missing")


class TestMarkdownAndCli:
    @pytest.mark.unit
    def test_report_to_markdown_includes_runtime_handoff(self, tmp_path: Path) -> None:
        start = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)
        _write_valid_run(tmp_path, start=start, hours=2, cadence_seconds=3600)
        report = validate_72h_window_from_dir(
            tmp_path,
            required_window_hours=2,
            runner_cadence_seconds=3600,
        )
        markdown = report_to_markdown(report)
        assert "72h Ops Validation Report" in markdown
        assert "Runtime Handoff" in markdown
        assert "boot_readiness_report.json" in markdown
        assert "No LR-Go" in markdown

    @pytest.mark.unit
    def test_schema_version_constant(self) -> None:
        assert (
            OPS_VALIDATION_SCHEMA_VERSION == "cdb.evidence_harvester.ops_validation.v1"
        )
        assert DEFAULT_REQUIRED_WINDOW_HOURS == 72
        assert isinstance(RuntimeHandoff, type)

    @pytest.mark.unit
    def test_parse_args_help(self) -> None:
        from tools.evidence_harvester.ops_validation import parse_args

        with pytest.raises(SystemExit):
            parse_args(["--help"])

    @pytest.mark.unit
    def test_parse_args_missing_artifact_dir(self) -> None:
        from tools.evidence_harvester.ops_validation import parse_args

        with pytest.raises(SystemExit):
            parse_args(["validate-dir"])
