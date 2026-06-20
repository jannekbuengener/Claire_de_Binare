from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.evidence_harvester.watchdog import (
    COORDINATOR_LIVENESS_CLASSIFICATIONS,
    WATCHDOG_REPORT_SCHEMA,
    WatchdogError,
    WatchdogReport,
    main,
    render_escalation_draft,
    report_to_markdown,
    run_check_artifacts,
    run_status,
)


def _ts(offset_minutes: int = 0) -> str:
    now = datetime.now(UTC)
    target = now - timedelta(minutes=offset_minutes)
    return target.isoformat().replace("+00:00", "Z")


def _now_iso() -> str:
    return _ts(0)


def _write_heartbeat(
    artifact_dir: Path,
    *,
    age_minutes: int = 1,
    mode: str = "loop-fixture",
    iteration: int = 5,
    last_error: str = "",
) -> Path:
    payload = {
        "schema_version": "cdb.evidence_harvester.runner_heartbeat.v1",
        "runner_mode": mode,
        "iteration": iteration,
        "started_at_utc": _ts(age_minutes + 10),
        "current_run_at_utc": _ts(age_minutes),
        "last_success_at_utc": _ts(age_minutes),
        "last_failure_at_utc": "",
        "last_error": last_error,
        "last_collector_report": str(artifact_dir / "collector_report_20260619.json"),
        "last_snapshot_json": str(artifact_dir / "snapshot_20260619.json"),
        "last_snapshot_markdown": str(artifact_dir / "snapshot_20260619.md"),
        "last_alert_json": str(artifact_dir / "alert_20260619.json"),
        "last_alert_markdown": str(artifact_dir / "alert_20260619.md"),
    }
    path = artifact_dir / "runner_heartbeat.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_state(
    artifact_dir: Path,
    *,
    total_runs: int = 5,
    successful_runs: int = 5,
    failed_runs: int = 0,
    last_verdict: str = "PASS",
    age_minutes: int = 1,
    coordinator_status: str = "",
    next_cycle_due_at_utc: str = "",
) -> Path:
    payload = {
        "schema_version": "cdb.evidence_harvester.runner_state.v1",
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "last_cycle_verdict": last_verdict,
        "last_cycle_ended_at_utc": _ts(age_minutes),
        "run_id": "test-run",
        "total_cycles_started": total_runs,
        "total_cycles_completed": successful_runs,
        "total_successful_cycles": successful_runs,
        "total_failed_cycles": failed_runs,
        "last_cycle_started_at_utc": _ts(age_minutes + 1),
        "next_cycle_due_at_utc": next_cycle_due_at_utc,
        "last_successful_artifact_stamp": "20260619T000000Z",
        "coordinator_status": coordinator_status,
    }
    path = artifact_dir / "runner_state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_collector_report(artifact_dir: Path, stamp: str = "20260619") -> Path:
    payload = {
        "schema_version": "evidence_harvester.collector_report.v1",
        "report_id": f"report_{stamp}",
        "evidence_class": "pipeline_test_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "pytest",
        "produced_at_utc": _ts(15),
        "source_mode": "fixture",
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
    path = artifact_dir / f"collector_report_{stamp}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_snapshot(
    artifact_dir: Path,
    stamp: str = "20260619",
    *,
    age_minutes: int = 10,
    schema_version: str = "cdb.evidence_harvester.snapshot.v1",
    lr_status: str = "NO-GO",
    live_status: str = "NO-GO",
    echtgeld_status: str = "NO-GO",
) -> Path:
    payload = {
        "metadata": {
            "schema_version": schema_version,
            "generated_at_utc": _ts(age_minutes),
            "collector_report_hash": "sha256:abc123",
            "collector_report_id": f"report_{stamp}",
            "collector_report_schema_version": "evidence_harvester.collector_report.v1",
            "source_mode": "fixture",
            "evidence_class": "pipeline_test_evidence",
            "evidence_class_version": "1.0",
            "produced_by": "pytest",
            "collector_report_produced_at_utc": _ts(age_minutes + 1),
        },
        "safety": {
            "banner": "Paper/research evidence only; no LR-Go, no Live-Go, no Echtgeld-Go.",
            "lr_status": lr_status,
            "live_status": live_status,
            "echtgeld_status": echtgeld_status,
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
            "total_streams": 0,
            "signal_count_total": 0,
            "decision_count_total": 0,
            "order_count_total": 0,
            "fill_count_total": 0,
            "complete_chain_count_total": 0,
            "partial_chain_count_total": 0,
            "zero_complete_stream_count": 0,
            "zero_signal_stream_count": 0,
            "average_signal_density_per_hour": 0.0,
            "status_counts": {"blocking": 0, "warning": 0, "info": 0},
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
        "next_action_hints": ["No immediate gap-driven action."],
    }
    path = artifact_dir / f"snapshot_{stamp}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_coordinator_events(
    artifact_dir: Path,
    *,
    event_types: list[str] | None = None,
) -> Path:
    run_id = "test-watchdog"
    events = []
    for etype in event_types or []:
        event = {
            "schema_version": "cdb.evidence_harvester.coordinator_event.v1",
            "event_at_utc": _ts(1),
            "run_id": run_id,
            "event_type": etype,
        }
        if etype == "fatal_stop":
            event["coordinator_status"] = "fatal_stop"
            event["stop_reason"] = "fatal_watchdog_failure"
        events.append(event)
    path = artifact_dir / "coordinator_events.jsonl"
    path.write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
        encoding="utf-8",
    )
    return path


def _write_alert(
    artifact_dir: Path,
    stamp: str = "20260619",
    *,
    schema_version: str = "cdb.evidence_harvester.alert_report.v1",
    manual_escalation_only: bool = True,
) -> Path:
    payload = {
        "schema_version": schema_version,
        "evaluated_at_utc": _ts(5),
        "snapshot_generated_at_utc": _ts(10),
        "collector_report_id": f"report_{stamp}",
        "collector_report_hash": "sha256:abc123",
        "snapshot_age_minutes": 10,
        "summary": {
            "highest_severity": "info",
            "total_count": 0,
            "critical_count": 0,
            "warn_count": 0,
            "info_count": 0,
            "manual_escalation_recommended": False,
        },
        "findings": [],
        "manual_escalation_only": manual_escalation_only,
    }
    path = artifact_dir / f"alert_{stamp}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_artifact_dir(
    tmp_path: Path,
    *,
    heartbeat_age_minutes: int = 1,
    snapshot_age_minutes: int = 10,
    state_failed_runs: int = 0,
    state_verdict: str = "PASS",
    state_age_minutes: int = 1,
    include_heartbeat: bool = True,
    include_state: bool = True,
    include_snapshot: bool = True,
    include_alert: bool = True,
    include_snapshot_md: bool = True,
    include_alert_md: bool = True,
) -> Path:
    d = tmp_path / "runner_artifacts"
    d.mkdir(parents=True, exist_ok=True)

    if include_heartbeat:
        _write_heartbeat(d, age_minutes=heartbeat_age_minutes)
    if include_state:
        _write_state(
            d,
            failed_runs=state_failed_runs,
            last_verdict=state_verdict,
            age_minutes=state_age_minutes,
        )
    if include_snapshot:
        _write_snapshot(d, age_minutes=snapshot_age_minutes)
    if include_alert:
        _write_alert(d)
    _write_collector_report(d)
    if include_snapshot_md:
        (d / "snapshot_20260619.md").write_text("# Snapshot", encoding="utf-8")
    if include_alert_md:
        (d / "alert_20260619.md").write_text("# Alert", encoding="utf-8")

    return d


# ============================================================
# coordinator_liveness — all 8 classifications
# ============================================================


@pytest.mark.unit
def test_liveness_running_healthy(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, heartbeat_age_minutes=1)
    _write_state(d, coordinator_status="running")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "RUNNING_HEALTHY"
    assert cl.severity == "pass"


@pytest.mark.unit
def test_liveness_sleeping_until_next_cycle(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    due_at = (
        (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    )
    _write_state(
        d,
        coordinator_status="sleeping",
        next_cycle_due_at_utc=due_at,
    )
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "SLEEPING_UNTIL_NEXT_CYCLE"
    assert cl.severity == "pass"


@pytest.mark.unit
def test_liveness_sleeping_warn_within_tolerance(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    due_at = (
        (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    )
    _write_state(
        d,
        coordinator_status="sleeping",
        next_cycle_due_at_utc=due_at,
    )
    now = datetime.now(UTC)
    report = run_status(d, cadence_seconds=900, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "SLEEPING_UNTIL_NEXT_CYCLE"
    assert cl.severity == "warn"


@pytest.mark.unit
def test_liveness_stale_heartbeat(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, heartbeat_age_minutes=200)
    _write_state(d, coordinator_status="running")
    now = datetime.now(UTC)
    report = run_status(d, max_age_seconds=60, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "STALE_HEARTBEAT"
    assert cl.severity == "fail"


@pytest.mark.unit
def test_liveness_stale_next_cycle(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    due_at = (datetime.now(UTC) - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    _write_state(
        d,
        coordinator_status="sleeping",
        next_cycle_due_at_utc=due_at,
    )
    now = datetime.now(UTC)
    report = run_status(d, cadence_seconds=900, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "STALE_NEXT_CYCLE"
    assert cl.severity == "fail"


@pytest.mark.unit
def test_liveness_stale_next_cycle_missing_due(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="sleeping", next_cycle_due_at_utc="")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "STALE_NEXT_CYCLE"
    assert cl.severity == "fail"


@pytest.mark.unit
def test_liveness_coordinator_stopped_completed(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="completed")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "COORDINATOR_STOPPED"
    assert cl.severity == "warn"


@pytest.mark.unit
def test_liveness_coordinator_stopped_failed(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="failed")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "COORDINATOR_STOPPED"
    assert cl.severity == "fail"


@pytest.mark.unit
def test_liveness_coordinator_unknown(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "COORDINATOR_UNKNOWN"
    assert cl.severity == "warn"


@pytest.mark.unit
def test_liveness_recovery_in_progress(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="recovering")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "RECOVERY_IN_PROGRESS"
    assert cl.severity == "warn"


@pytest.mark.unit
def test_liveness_fatal_stop_from_state(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="fatal_stop")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "FATAL_STOP"
    assert cl.severity == "fail"


@pytest.mark.unit
def test_liveness_fatal_stop_from_lifecycle_event(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="running")
    _write_coordinator_events(d, event_types=["fatal_stop"])
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.classification == "FATAL_STOP"
    assert cl.severity == "fail"


@pytest.mark.unit
def test_liveness_missing_telemetry_does_not_silently_pass(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_state(d, coordinator_status="")
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    cl = report.coordinator_liveness
    assert cl.severity != "pass"
    assert cl.classification in COORDINATOR_LIVENESS_CLASSIFICATIONS


@pytest.mark.unit
def test_liveness_existing_watchdog_freshness_remains_compatible(
    tmp_path: Path,
) -> None:
    d = _write_artifact_dir(tmp_path, heartbeat_age_minutes=1)
    now = datetime.now(UTC)
    report = run_status(d, now=now)
    assert report.verdict.verdict == "PASS"


# ============================================================
# run_status — PASS
# ============================================================


@pytest.mark.unit
def test_status_pass_with_fresh_artifacts(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.schema_version == WATCHDOG_REPORT_SCHEMA
    assert report.mode == "status"
    assert report.verdict.verdict == "PASS"
    assert report.heartbeat_fresh is True
    assert report.runner_state_ok is True
    assert report.required_artifacts_present is True
    assert report.verdict.fail_count == 0


@pytest.mark.unit
def test_watchdog_main_uses_sys_argv_when_none(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_dir = _write_artifact_dir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["watchdog", "check-artifacts", "--artifact-dir", str(artifact_dir)],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "check-artifacts"


@pytest.mark.unit
def test_status_pass_default_dir_resolves(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "PASS"


# ============================================================
# run_status — WARN
# ============================================================


@pytest.mark.unit
def test_status_warn_on_approaching_stale_heartbeat(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, heartbeat_age_minutes=100)
    now = datetime.now(UTC)

    report = run_status(d, max_age_seconds=7200, warn_age_seconds=1800, now=now)

    assert report.verdict.verdict == "WARN"
    assert report.heartbeat_fresh is True


@pytest.mark.unit
def test_status_warn_on_failed_runs(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, state_failed_runs=2)
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "WARN"
    assert report.runner_state_ok is True


@pytest.mark.unit
def test_status_pass_when_coordinator_sleep_schedule_is_healthy(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    due_at = (
        (datetime.now(UTC) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    )
    _write_state(
        d,
        age_minutes=1,
        coordinator_status="sleeping",
        next_cycle_due_at_utc=due_at,
    )
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "PASS"
    assert any(f.check_id == "W017" and f.severity == "pass" for f in report.findings)


# ============================================================
# run_status — FAIL
# ============================================================


@pytest.mark.unit
def test_status_fail_on_stale_heartbeat(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, heartbeat_age_minutes=200)
    now = datetime.now(UTC)

    report = run_status(d, max_age_seconds=60, now=now)

    assert report.verdict.verdict == "FAIL"
    assert report.heartbeat_fresh is False


@pytest.mark.unit
def test_status_fail_on_missing_heartbeat(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, include_heartbeat=False)
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_status_fail_on_missing_state(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, include_state=False)
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_status_fail_on_runner_failure_verdict(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, state_verdict="FAIL")
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"
    assert report.runner_state_ok is False


@pytest.mark.unit
def test_status_fail_on_missing_required_artifact(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, include_snapshot=False)
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"
    assert report.required_artifacts_present is False


@pytest.mark.unit
def test_status_fail_on_stale_snapshot(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, snapshot_age_minutes=200)
    now = datetime.now(UTC)

    report = run_status(d, max_age_seconds=60, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_status_ignores_historical_snapshot_freshness(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, snapshot_age_minutes=1)
    _write_snapshot(d, stamp="20260618T000000Z", age_minutes=200)
    (d / "snapshot_20260618T000000Z.md").write_text("# Historical", encoding="utf-8")
    now = datetime.now(UTC)

    report = run_status(d, max_age_seconds=120, now=now)

    assert report.verdict.verdict == "PASS"
    freshness = [f for f in report.findings if f.check_id == "W011"]
    assert len(freshness) == 1
    assert freshness[0].severity == "pass"
    assert "Latest snapshot" in freshness[0].message


@pytest.mark.unit
def test_status_fail_on_stale_runner_state(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, state_age_minutes=200)
    now = datetime.now(UTC)

    report = run_status(d, max_age_seconds=60, now=now)

    assert report.verdict.verdict == "FAIL"
    assert report.runner_state_ok is False
    assert any(f.check_id == "W016" and f.severity == "fail" for f in report.findings)


@pytest.mark.unit
def test_status_fail_on_empty_dir(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


# ============================================================
# run_status — malformed JSON
# ============================================================


@pytest.mark.unit
def test_status_fail_on_malformed_heartbeat_json(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    (d / "runner_heartbeat.json").write_text("not json", encoding="utf-8")
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_status_fail_on_malformed_state_json(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    (d / "runner_state.json").write_text("not json", encoding="utf-8")
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_status_fail_on_malformed_snapshot_json(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    (d / "snapshot_20260619.json").write_text("not json", encoding="utf-8")
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_status_fail_on_malformed_alert_json(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    (d / "alert_20260619.json").write_text("not json", encoding="utf-8")
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


# ============================================================
# run_status — safety flags
# ============================================================


@pytest.mark.unit
def test_status_fail_on_wrong_safety_flag(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    _write_snapshot(d, lr_status="GO")
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


# ============================================================
# run_check_artifacts
# ============================================================


@pytest.mark.unit
def test_check_artifacts_pass(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    now = datetime.now(UTC)

    report = run_check_artifacts(d, now=now)

    assert report.schema_version == WATCHDOG_REPORT_SCHEMA
    assert report.mode == "check-artifacts"
    assert report.verdict.verdict == "PASS"
    assert report.required_artifacts_present is True


@pytest.mark.unit
def test_check_artifacts_fail_on_missing_snapshot(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, include_snapshot=False)
    now = datetime.now(UTC)

    report = run_check_artifacts(d, now=now)

    assert report.verdict.verdict == "FAIL"
    assert report.required_artifacts_present is False


@pytest.mark.unit
def test_check_artifacts_fail_on_malformed_snapshot(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    (d / "snapshot_20260619.json").write_text("bad json", encoding="utf-8")
    now = datetime.now(UTC)

    report = run_check_artifacts(d, now=now)

    assert report.verdict.verdict == "FAIL"


# ============================================================
# run_status — cadence
# ============================================================


@pytest.mark.unit
def test_status_warn_on_cadence_exceeded(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, snapshot_age_minutes=90)
    now = datetime.now(UTC)

    report = run_status(d, cadence_seconds=3600, now=now)

    assert report.verdict.verdict == "WARN"


@pytest.mark.unit
def test_status_fail_on_double_cadence_exceeded(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path, snapshot_age_minutes=5000)
    now = datetime.now(UTC)

    report = run_status(d, cadence_seconds=3600, now=now)

    assert report.verdict.verdict == "FAIL"


# ============================================================
# report_to_markdown
# ============================================================


@pytest.mark.unit
def test_report_to_markdown_contains_verdict(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    now = datetime.now(UTC)
    report = run_status(d, now=now)

    md = report_to_markdown(report)

    assert "PASS" in md or "WARN" in md or "FAIL" in md
    assert "Watchdog Report" in md
    assert "No LR-Go" in md


# ============================================================
# render_escalation_draft
# ============================================================


@pytest.mark.unit
def test_escalation_draft_contains_verdict_and_safety(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    now = datetime.now(UTC)
    report = run_status(d, now=now)

    draft = render_escalation_draft(report)

    assert "Manual Escalation Draft" in draft
    assert "No LR-Go" in draft
    assert report.verdict.verdict in draft


@pytest.mark.unit
def test_escalation_draft_accepts_parent_issue(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    now = datetime.now(UTC)
    report = run_status(d, now=now)

    draft = render_escalation_draft(report, parent_issue="3345")

    assert "#3345" in draft


# ============================================================
# CLI — main()
# ============================================================


@pytest.mark.unit
def test_cli_status_returns_zero_on_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = _write_artifact_dir(tmp_path)
    evaluated_at = _now_iso()

    exit_code = main(
        [
            "status",
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            evaluated_at,
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "status"
    assert payload["verdict"]["verdict"] == "PASS"


@pytest.mark.unit
def test_cli_status_returns_one_on_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    evaluated_at = _now_iso()

    exit_code = main(
        [
            "status",
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            evaluated_at,
        ]
    )
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"]["verdict"] == "FAIL"


@pytest.mark.unit
def test_cli_check_artifacts_returns_zero_on_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = _write_artifact_dir(tmp_path)
    evaluated_at = _now_iso()

    exit_code = main(
        [
            "check-artifacts",
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            evaluated_at,
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "check-artifacts"
    assert payload["verdict"]["verdict"] == "PASS"


@pytest.mark.unit
def test_cli_render_escalation_draft_from_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = _write_artifact_dir(tmp_path)
    evaluated_at = _now_iso()
    json_out = tmp_path / "watchdog_report.json"

    main(
        [
            "status",
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            evaluated_at,
            "--json-output",
            str(json_out),
        ]
    )
    capsys.readouterr()

    exit_code = main(
        [
            "render-escalation-draft",
            "--report-json",
            str(json_out),
            "--parent-issue",
            "3345",
        ]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Manual Escalation Draft" in output


@pytest.mark.unit
def test_cli_default_command_is_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "status"


# ============================================================
# File outputs
# ============================================================


@pytest.mark.unit
def test_cli_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    evaluated_at = _now_iso()
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"

    exit_code = main(
        [
            "status",
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            evaluated_at,
            "--json-output",
            str(json_out),
            "--markdown-output",
            str(md_out),
        ]
    )
    assert exit_code == 0
    assert json_out.exists()
    assert md_out.exists()

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["verdict"]["verdict"] == "PASS"

    md = md_out.read_text(encoding="utf-8")
    assert "Watchdog Report" in md


@pytest.mark.unit
def test_cli_writes_escalation_draft_output(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    evaluated_at = _now_iso()
    draft_out = tmp_path / "escalation.md"

    exit_code = main(
        [
            "status",
            "--artifact-dir",
            str(d),
            "--evaluated-at-utc",
            evaluated_at,
            "--escalation-draft-output",
            str(draft_out),
        ]
    )
    assert exit_code == 0
    assert draft_out.exists()
    draft = draft_out.read_text(encoding="utf-8")
    assert "Manual Escalation Draft" in draft


# ============================================================
# Determinism
# ============================================================


@pytest.mark.unit
def test_status_is_deterministic_with_fixed_timestamp(tmp_path: Path) -> None:
    d1 = _write_artifact_dir(tmp_path / "run1")
    d2 = _write_artifact_dir(tmp_path / "run2")
    fixed_ts = "2026-06-19T16:00:00Z"

    report1 = run_status(
        d1, now=datetime.fromisoformat(fixed_ts.replace("Z", "+00:00"))
    )
    report2 = run_status(
        d2, now=datetime.fromisoformat(fixed_ts.replace("Z", "+00:00"))
    )

    assert report1.verdict.verdict == report2.verdict.verdict
    assert report1.verdict.fail_count == report2.verdict.fail_count
    assert report1.verdict.warn_count == report2.verdict.warn_count
    assert report1.verdict.pass_count == report2.verdict.pass_count


# ============================================================
# Error handling
# ============================================================


@pytest.mark.unit
def test_watchdog_error_on_missing_dir(tmp_path: Path) -> None:
    d = tmp_path / "nonexistent"
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL"


@pytest.mark.unit
def test_payload_without_safety_flags_still_handled(tmp_path: Path) -> None:
    d = _write_artifact_dir(tmp_path)
    (d / "snapshot_20260619.json").write_text(
        json.dumps(
            {
                "metadata": {
                    "schema_version": "cdb.evidence_harvester.snapshot.v1",
                    "generated_at_utc": _ts(10),
                }
            }
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)

    report = run_status(d, now=now)

    assert report.verdict.verdict == "FAIL" or report.verdict.verdict == "WARN"


@pytest.mark.unit
def test_cli_rejects_nonexistent_report_json(tmp_path: Path) -> None:
    missing = tmp_path / "no_such_report.json"
    exit_code = main(
        [
            "render-escalation-draft",
            "--report-json",
            str(missing),
        ]
    )
    assert exit_code == 1
