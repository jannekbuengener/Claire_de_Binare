from __future__ import annotations

import json
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.evidence_harvester.write_audit import (
    WRITE_AUDIT_REPORT_SCHEMA,
    WriteAuditError,
    WriteAuditReport,
    main,
    report_to_markdown,
    run_write_audit,
)

_FIXED_TS = datetime(2026, 6, 19, 16, 0, 0, tzinfo=UTC)


def _ts(offset_minutes: int = 0) -> str:
    target = _FIXED_TS - timedelta(minutes=offset_minutes)
    return target.isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _collector_payload(stamp: str = "20260619", source_mode: str = "fixture") -> dict:
    return {
        "schema_version": "evidence_harvester.collector_report.v1",
        "report_id": f"report_{stamp}",
        "evidence_class": "pipeline_test_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "pytest",
        "produced_at_utc": _ts(15),
        "source_mode": source_mode,
        "raw_evidence": {
            "candle_input_count": 10,
            "regime_input_count": 5,
            "paper_chain_input_count": 3,
            "provenance_input_count": 2,
            "observed_input_count": 20,
        },
        "candle_coverages": [],
        "regime_coverages": [],
        "paper_chain_coverages": [],
        "provenance": {
            "allowed_sources": ["mexc"],
            "source_findings": [],
            "unknown_source_count": 0,
            "contaminated_source_count": 0,
        },
        "gap_findings": [],
        "summary": {
            "overall_status": "ok",
            "blocking_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "has_zero_paper_chains": False,
        },
    }


def _collector_hash(payload: dict) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _snapshot_payload(
    stamp: str = "20260619",
    age_minutes: int = 10,
    schema_version: str = "cdb.evidence_harvester.snapshot.v1",
    collector_hash: str = "sha256:abc123",
    collector_id: str = "report_20260619",
    source_mode: str = "fixture",
) -> dict:
    return {
        "metadata": {
            "schema_version": schema_version,
            "generated_at_utc": _ts(age_minutes),
            "collector_report_hash": collector_hash,
            "collector_report_id": collector_id,
            "collector_report_schema_version": "evidence_harvester.collector_report.v1",
            "source_mode": source_mode,
            "evidence_class": "pipeline_test_evidence",
            "evidence_class_version": "1.0",
            "produced_by": "pytest",
            "collector_report_produced_at_utc": _ts(age_minutes + 1),
        },
        "safety": {
            "banner": "Paper/research evidence only; no LR-Go, no Live-Go, no Echtgeld-Go.",
            "lr_status": "NO-GO",
            "live_status": "NO-GO",
            "echtgeld_status": "NO-GO",
            "runtime_actions": "not_allowed",
            "db_execution": "not_allowed",
            "background_job_orchestration": "not_in_scope",
            "allowed_scope": "fixture-based snapshot generation only",
        },
        "status": {
            "overall_status": "ok",
            "gap_counts": {"blocking": 0, "warning": 0, "info": 0},
            "has_zero_paper_chains": False,
            "raw_evidence": {
                "candle_input_count": 10,
                "regime_input_count": 5,
                "paper_chain_input_count": 3,
                "provenance_input_count": 2,
                "observed_input_count": 20,
            },
        },
        "coverage": {
            "candles": {
                "status": "ok",
                "total_streams": 1,
                "observed_count_total": 18,
                "expected_count_total": 20,
                "coverage_pct": 0.9,
                "stale_stream_count": 0,
                "status_counts": {"blocking": 0, "warning": 0, "info": 1},
                "items": [],
            },
            "regimes": {
                "status": "ok",
                "total_streams": 1,
                "observed_count_total": 10,
                "expected_count_total": 20,
                "coverage_pct": 0.5,
                "stale_stream_count": 0,
                "status_counts": {"blocking": 0, "warning": 0, "info": 1},
                "items": [],
            },
        },
        "provenance": {
            "allowed_sources": ["mexc"],
            "source_findings": [],
            "unknown_source_count": 0,
            "contaminated_source_count": 0,
        },
        "paper_chains": {
            "total_streams": 1,
            "items": [],
            "status_counts": {"blocking": 0, "warning": 0, "info": 1},
        },
        "gap_findings": {"items": [], "by_severity": {}},
        "next_action_hints": [],
    }


def _alert_payload(
    age_minutes: int = 8,
    manual_escalation_only: bool = True,
    schema_version: str = "cdb.evidence_harvester.alert_report.v1",
) -> dict:
    return {
        "schema_version": schema_version,
        "snapshot_generated_at_utc": _ts(age_minutes),
        "snapshot_schema_version": "cdb.evidence_harvester.snapshot.v1",
        "collector_report_hash": "sha256:abc123",
        "collector_report_schema_version": "evidence_harvester.collector_report.v1",
        "snapshot_source_mode": "fixture",
        "evaluated_at_utc": _ts(age_minutes),
        "overall_status": "ok",
        "items": [],
        "report_type": "evidence_harvester_alert",
        "has_warning": False,
        "has_blocking": False,
        "manual_escalation_only": manual_escalation_only,
    }


def _heartbeat_payload(age_minutes: int = 1) -> dict:
    return {
        "schema_version": "cdb.evidence_harvester.runner_heartbeat.v1",
        "runner_mode": "loop-fixture",
        "iteration": 5,
        "started_at_utc": _ts(age_minutes + 10),
        "current_run_at_utc": _ts(age_minutes),
        "last_success_at_utc": _ts(age_minutes),
        "last_failure_at_utc": "",
        "last_error": "",
        "last_collector_report": "",
        "last_snapshot_json": "",
        "last_snapshot_markdown": "",
        "last_alert_json": "",
        "last_alert_markdown": "",
    }


def _state_payload(verdict: str = "PASS", age_minutes: int = 1) -> dict:
    return {
        "schema_version": "cdb.evidence_harvester.runner_state.v1",
        "total_runs": 5,
        "successful_runs": 5,
        "failed_runs": 0,
        "last_cycle_verdict": verdict,
        "last_cycle_ended_at_utc": _ts(age_minutes),
    }


def _watchdog_payload(verdict: str = "PASS") -> dict:
    return {
        "schema_version": "cdb.evidence_harvester.watchdog_report.v1",
        "evaluated_at_utc": _ts(1),
        "artifact_dir": "",
        "mode": "status",
        "heartbeat_fresh": True,
        "runner_state_ok": True,
        "required_artifacts_present": True,
        "verdict": {
            "verdict": verdict,
            "total_checks": 5,
            "pass_count": 5,
            "warn_count": 0,
            "fail_count": 0,
        },
        "findings": [],
    }


def _setup_complete_artifacts(
    tmp_path: Path,
    stamp: str = "20260619",
) -> Path:
    cr = _collector_payload(stamp)
    cr_hash = _collector_hash(cr)
    _write_json(tmp_path / f"collector_report_{stamp}.json", cr)
    _write_json(
        tmp_path / f"snapshot_{stamp}.json",
        _snapshot_payload(
            stamp, collector_hash=cr_hash, collector_id=f"report_{stamp}"
        ),
    )
    _write_json(tmp_path / f"snapshot_{stamp}.md", {})
    _write_json(tmp_path / f"alert_{stamp}.json", _alert_payload())
    _write_json(tmp_path / f"alert_{stamp}.md", {})
    _write_json(tmp_path / "runner_heartbeat.json", _heartbeat_payload())
    _write_json(tmp_path / "runner_state.json", _state_payload())
    _write_json(tmp_path / "watchdog_report.json", _watchdog_payload())
    _write_json(tmp_path / "watchdog_report.md", {})
    return tmp_path


# --- A001: Required artifacts ---


def test_rwa_a001_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    a001 = [f for f in report.findings if f.check_id == "A001"]
    assert any(f.severity == "pass" for f in a001)
    assert not any(f.severity == "fail" for f in a001)


def test_rwa_a001_fail_missing_snapshot_json(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "snapshot_20260619.json").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a001 = [f for f in report.findings if f.check_id == "A001"]
    assert any("snapshot_*.json" in f.message for f in a001)


def test_rwa_a001_fail_missing_heartbeat(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "runner_heartbeat.json").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a001 = [f for f in report.findings if f.check_id == "A001"]
    assert any("runner_heartbeat.json" in f.message for f in a001)


def test_rwa_a001_fail_missing_state(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "runner_state.json").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a001 = [f for f in report.findings if f.check_id == "A001"]
    assert any("runner_state.json" in f.message for f in a001)


def test_rwa_a001_fail_missing_watchdog_report(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "watchdog_report.json").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a001 = [f for f in report.findings if f.check_id == "A001"]
    assert any("watchdog_report.json" in f.message for f in a001)


def test_rwa_a001_warn_missing_watchdog_md(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "watchdog_report.md").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "WARN"
    a001 = [f for f in report.findings if f.check_id == "A001"]
    assert any("watchdog_report.md" in f.message for f in a001)


# --- A002: JSON integrity ---


def test_rwa_a002_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.all_json_parse is True
    a002 = [f for f in report.findings if f.check_id == "A002"]
    assert any(f.severity == "pass" for f in a002)


def test_rwa_a002_fail_malformed_json(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "snapshot_20260619.json").write_text("{bad json", encoding="utf-8")
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.all_json_parse is False
    a002 = [f for f in report.findings if f.check_id == "A002"]
    assert any(f.severity == "fail" for f in a002)


# --- A003: Schema versions ---


def test_rwa_a003_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.schema_versions_match is True
    a003 = [f for f in report.findings if f.check_id == "A003"]
    assert any(f.severity == "pass" for f in a003)


def test_rwa_a003_fail_bad_snapshot_schema(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    _write_json(
        d / "snapshot_20260619.json",
        _snapshot_payload(schema_version="wrong.v2"),
    )
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.schema_versions_match is False
    a003 = [f for f in report.findings if f.check_id == "A003"]
    assert any("wrong.v2" in f.message for f in a003)


def test_rwa_a003_fail_bad_heartbeat_schema(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    hb = _heartbeat_payload()
    hb["schema_version"] = "wrong.v2"
    _write_json(d / "runner_heartbeat.json", hb)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a003 = [f for f in report.findings if f.check_id == "A003"]
    assert any("wrong.v2" in f.message for f in a003)


def test_rwa_a003_fail_bad_alert_schema(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    _write_json(
        d / "alert_20260619.json",
        _alert_payload(schema_version="wrong.v2"),
    )
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a003 = [f for f in report.findings if f.check_id == "A003"]
    assert any("wrong.v2" in f.message for f in a003)


def test_rwa_a003_fail_bad_watchdog_schema(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    wd = _watchdog_payload()
    wd["schema_version"] = "wrong.v2"
    _write_json(d / "watchdog_report.json", wd)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a003 = [f for f in report.findings if f.check_id == "A003"]
    assert any("wrong.v2" in f.message for f in a003)


# --- A004: Hash linkage ---


def test_rwa_a004_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.hash_linkage_valid is True
    a004 = [f for f in report.findings if f.check_id == "A004"]
    assert any(f.severity == "pass" for f in a004)


def test_rwa_a004_fail_hash_mismatch(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    _write_json(
        d / "snapshot_20260619.json",
        _snapshot_payload(
            collector_hash="sha256:doesnotmatch",
            collector_id="nonexistent_report",
        ),
    )
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.hash_linkage_valid is False
    a004 = [f for f in report.findings if f.check_id == "A004"]
    assert any(f.severity == "fail" for f in a004)


def test_rwa_a004_fail_no_collector_report(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "collector_report_20260619.json").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.hash_linkage_valid is False


# --- A005: Safety flags ---


def test_rwa_a005_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.safety_flags_correct is True
    a005 = [f for f in report.findings if f.check_id == "A005"]
    assert any(f.severity == "pass" for f in a005)


def test_rwa_a005_fail_lr_status_wrong(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    snap = _snapshot_payload(
        collector_hash=_collector_hash(_collector_payload()),
        collector_id="report_20260619",
    )
    snap["safety"]["lr_status"] = "GO"
    _write_json(d / "snapshot_20260619.json", snap)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.safety_flags_correct is False
    a005 = [f for f in report.findings if f.check_id == "A005"]
    assert any(f.severity == "fail" for f in a005)


def test_rwa_a005_fail_manual_escalation_false(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    _write_json(
        d / "alert_20260619.json",
        _alert_payload(manual_escalation_only=False),
    )
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a005 = [f for f in report.findings if f.check_id == "A005"]
    assert any("manual_escalation_only" in f.message for f in a005)


# --- A006: Timestamps ---


def test_rwa_a006_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.timestamps_coherent is True
    a006 = [f for f in report.findings if f.check_id == "A006"]
    assert any(f.severity == "pass" for f in a006)


def test_rwa_a006_fail_stale_heartbeat(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    hb = _heartbeat_payload(age_minutes=9999)
    _write_json(d / "runner_heartbeat.json", hb)
    report = run_write_audit(d, stale_threshold=7200, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.timestamps_coherent is False
    a006 = [f for f in report.findings if f.check_id == "A006"]
    assert any(f.severity == "fail" for f in a006)


def test_rwa_a006_warn_stale_heartbeat(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    hb = _heartbeat_payload(age_minutes=100)
    _write_json(d / "runner_heartbeat.json", hb)
    report = run_write_audit(d, stale_threshold=99999, warn_stale=60, now=_FIXED_TS)
    assert report.verdict.verdict == "WARN"
    a006 = [f for f in report.findings if f.check_id == "A006"]
    assert any(f.severity == "warn" for f in a006)


def test_rwa_a006_fail_stale_snapshot(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    snap = _snapshot_payload(
        age_minutes=9999,
        collector_hash=_collector_hash(_collector_payload()),
        collector_id="report_20260619",
    )
    _write_json(d / "snapshot_20260619.json", snap)
    report = run_write_audit(d, stale_threshold=7200, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a006 = [f for f in report.findings if f.check_id == "A006"]
    assert any(f.severity == "fail" for f in a006)


def test_rwa_a006_ignore_historical_snapshot_staleness(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    old_snap = _snapshot_payload(
        stamp="20260618T000000Z",
        age_minutes=9999,
        collector_hash=_collector_hash(_collector_payload("20260618T000000Z")),
        collector_id="report_20260618T000000Z",
    )
    _write_json(
        d / "collector_report_20260618T000000Z.json",
        _collector_payload("20260618T000000Z"),
    )
    _write_json(d / "snapshot_20260618T000000Z.json", old_snap)
    (d / "snapshot_20260618T000000Z.md").write_text("# Historical", encoding="utf-8")

    report = run_write_audit(d, stale_threshold=7200, now=_FIXED_TS)

    assert report.verdict.verdict == "PASS"
    a006 = [f for f in report.findings if f.check_id == "A006"]
    assert all(
        "latest snapshot" in f.message.lower() or f.severity == "pass" for f in a006
    )


# --- A007: Source modes ---


def test_rwa_a007_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.source_modes_valid is True
    a007 = [f for f in report.findings if f.check_id == "A007"]
    assert any(f.severity == "pass" for f in a007)


def test_rwa_a007_pass_future_readonly(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    _write_json(
        d / "collector_report_20260619.json",
        _collector_payload(source_mode="future_readonly"),
    )
    cr = _collector_payload(source_mode="future_readonly")
    _write_json(
        d / "snapshot_20260619.json",
        _snapshot_payload(
            collector_hash=_collector_hash(cr),
            collector_id="report_20260619",
            source_mode="future_readonly",
        ),
    )
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"


def test_rwa_a007_fail_bad_source_mode(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    _write_json(
        d / "collector_report_20260619.json",
        _collector_payload(source_mode="production"),
    )
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.source_modes_valid is False
    a007 = [f for f in report.findings if f.check_id == "A007"]
    assert any("production" in f.message for f in a007)


# --- A008: Artifact sizes ---


def test_rwa_a008_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    assert report.sizes_sane is True
    a008 = [f for f in report.findings if f.check_id == "A008"]
    assert any(f.severity == "pass" for f in a008)


def test_rwa_a008_fail_zero_byte(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "snapshot_20260619.json").write_text("", encoding="utf-8")
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.sizes_sane is False
    a008 = [f for f in report.findings if f.check_id == "A008"]
    assert any("zero bytes" in f.message for f in a008)


# --- A009: Markdown companions ---


def test_rwa_a009_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    a009 = [f for f in report.findings if f.check_id == "A009"]
    assert any(f.severity == "pass" for f in a009)


def test_rwa_a009_warn_missing_snapshot_md(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    (d / "snapshot_20260619.md").unlink()
    report = run_write_audit(d, now=_FIXED_TS)
    a009 = [f for f in report.findings if f.check_id == "A009"]
    assert any(f.severity == "warn" for f in a009)


# --- A010: Metadata fields ---


def test_rwa_a010_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "PASS"
    a010 = [f for f in report.findings if f.check_id == "A010"]
    assert any(f.severity == "pass" for f in a010)


def test_rwa_a010_fail_empty_schema_version(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    hb = _heartbeat_payload()
    hb["schema_version"] = ""
    _write_json(d / "runner_heartbeat.json", hb)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a010 = [f for f in report.findings if f.check_id == "A010"]
    assert any("schema_version" in f.message for f in a010)


def test_rwa_a010_fail_missing_verdict(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    wd = _watchdog_payload()
    wd.pop("verdict")
    _write_json(d / "watchdog_report.json", wd)
    report = run_write_audit(d, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    a010 = [f for f in report.findings if f.check_id == "A010"]
    assert any("verdict" in f.message for f in a010)


# --- Determinism ---


def test_rwa_deterministic(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path, stamp="20260619")
    report_a = run_write_audit(d, now=_FIXED_TS)
    report_b = run_write_audit(d, now=_FIXED_TS)
    assert report_a.to_dict() == report_b.to_dict()


# --- Edge cases ---


def test_rwa_empty_directory(tmp_path: Path) -> None:
    report = run_write_audit(tmp_path, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.required_artifacts_present is False


def test_rwa_no_json_artifacts(tmp_path: Path) -> None:
    _write_json(tmp_path / "some_other_file.txt", {"key": "val"})
    report = run_write_audit(tmp_path, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"


def test_rwa_non_dict_json(tmp_path: Path) -> None:
    (tmp_path / "snapshot_20260619.json").write_text(
        json.dumps(["list", "not", "dict"]), encoding="utf-8"
    )
    report = run_write_audit(tmp_path, now=_FIXED_TS)
    assert report.verdict.verdict == "FAIL"
    assert report.all_json_parse is False


# --- CLI ---


def test_rwa_cli_default(tmp_path: Path) -> None:
    exit_code = main(["--artifact-dir", str(tmp_path)])
    assert exit_code == 1


def test_rwa_cli_pass(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    exit_code = main(
        [
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )
    assert exit_code == 0


def test_rwa_cli_json_output(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    json_out = tmp_path / "report.json"
    exit_code = main(
        [
            "--artifact-dir",
            str(d),
            "--json-output",
            str(json_out),
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )
    assert exit_code == 0
    assert json_out.exists()
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == WRITE_AUDIT_REPORT_SCHEMA


def test_rwa_cli_md_output(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    md_out = tmp_path / "report.md"
    exit_code = main(
        [
            "--artifact-dir",
            str(d),
            "--markdown-output",
            str(md_out),
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )
    assert exit_code == 0
    assert md_out.exists()
    text = md_out.read_text(encoding="utf-8")
    assert "Write-Audit Report" in text


# --- Markdown report ---


def test_rwa_markdown_output(tmp_path: Path) -> None:
    d = _setup_complete_artifacts(tmp_path)
    report = run_write_audit(d, now=_FIXED_TS)
    md = report_to_markdown(report)
    assert "Write-Audit Report" in md
    assert "PASS" in md
    assert "No LR-Go" in md
    assert "No runtime" in md


# --- WriteAuditError ---


def test_rwa_error_base() -> None:
    err = WriteAuditError("test error")
    assert isinstance(err, ValueError)
    assert "test error" in str(err)
