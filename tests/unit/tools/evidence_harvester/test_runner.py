from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from tools.evidence_harvester.runner import (
    HEARTBEAT_SCHEMA,
    STATE_SCHEMA,
    RunnerError,
    main,
)


def _fixture_payload() -> dict:
    return {
        "evidence_class": "pipeline_test_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "pytest",
        "produced_at_utc": "2026-06-19T12:00:00Z",
        "source_mode": "fixture",
        "allowed_provenance_sources": ["mexc", "paper_runner"],
        "stale_after_minutes": 60,
        "candle_coverages": [
            {
                "symbol": "BTCUSDT",
                "venue": "mexc",
                "timeframe": "1m",
                "first_ts_utc": "2026-06-19T10:00:00Z",
                "last_ts_utc": "2026-06-19T10:19:00Z",
                "observed_count": 18,
                "expected_count": 20,
            }
        ],
        "regime_coverages": [
            {
                "symbol": "BTCUSDT",
                "venue": "regime_service",
                "timeframe": "1m",
                "first_ts_utc": "2026-06-19T10:00:00Z",
                "last_ts_utc": "2026-06-19T10:19:00Z",
                "observed_count": 0,
                "expected_count": 20,
                "regime_distribution": {},
            }
        ],
        "paper_chain_coverages": [
            {
                "symbol": "BTCUSDT",
                "venue": "paper_runner",
                "timeframe": "1m",
                "observation_window_hours": 2.0,
                "signal_count": 0,
                "decision_count": 0,
                "order_count": 0,
                "fill_count": 0,
                "complete_chain_count": 0,
                "partial_chain_count": 0,
            }
        ],
        "provenance_observations": [
            {"source": "mexc", "observed_count": 18, "contaminated": False},
            {"source": "replay_runner", "observed_count": 2, "contaminated": True},
        ],
    }


def _write_fixture(tmp_path: Path) -> Path:
    fixture_path = tmp_path / "collector_input.json"
    fixture_path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")
    return fixture_path


@pytest.mark.unit
def test_default_command_is_plan(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "plan"
    assert payload["default_mode"] == "dry-run"
    assert "run-once-fixture" in payload["available_commands"]
    assert "loop-fixture" in payload["available_commands"]


@pytest.mark.unit
def test_plan_command_accepts_optional_fixture(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = _write_fixture(tmp_path)
    exit_code = main(["plan", "--fixture", str(fixture_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fixture"] == str(fixture_path)


@pytest.mark.unit
def test_plan_rejects_nonexistent_fixture(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(RunnerError, match="fixture path does not exist"):
        main(["plan", "--fixture", str(missing)])


@pytest.mark.unit
def test_status_reports_no_artifacts_on_empty_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty_output"
    exit_code = main(["status", "--output-dir", str(empty)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "status"
    assert payload["artifact_dir_exists"] is False
    assert payload["artifact_count"] == 0
    assert payload["heartbeat"] is None
    assert payload["state"] is None


@pytest.mark.unit
def test_run_once_fixture_writes_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = _write_fixture(tmp_path)
    output_dir = tmp_path / "artifacts"

    exit_code = main(
        [
            "run-once-fixture",
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(output_dir),
            "--generated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "run-once-fixture"

    hb = payload["heartbeat"]
    assert hb["schema_version"] == HEARTBEAT_SCHEMA
    assert hb["runner_mode"] == "run-once-fixture"
    assert hb["iteration"] == 0
    assert hb["last_collector_report"] != ""
    assert hb["last_snapshot_json"] != ""
    assert hb["last_snapshot_markdown"] != ""
    assert hb["last_alert_json"] != ""
    assert hb["last_alert_markdown"] != ""

    st = payload["state"]
    assert st["schema_version"] == STATE_SCHEMA
    assert st["total_runs"] == 1
    assert st["successful_runs"] == 1
    assert st["failed_runs"] == 0
    assert st["last_cycle_verdict"] == "PASS"


@pytest.mark.unit
def test_run_once_fixture_creates_heartbeat_and_state_on_disk(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = _write_fixture(tmp_path)
    output_dir = tmp_path / "artifacts"

    main(
        [
            "run-once-fixture",
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(output_dir),
            "--generated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )
    capsys.readouterr()

    assert (output_dir / "runner_heartbeat.json").exists()
    assert (output_dir / "runner_state.json").exists()
    json_files = list(output_dir.glob("collector_report_*.json"))
    assert len(json_files) >= 1
    snapshot_jsons = list(output_dir.glob("snapshot_*.json"))
    assert len(snapshot_jsons) >= 1
    alert_jsons = list(output_dir.glob("alert_*.json"))
    assert len(alert_jsons) >= 1


@pytest.mark.unit
def test_run_once_fixture_rejects_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(RunnerError, match="fixture path does not exist"):
        main(["run-once-fixture", "--fixture", str(missing)])


@pytest.mark.unit
def test_run_once_fixture_rejects_invalid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = tmp_path / "bad.json"
    fixture_path.write_text("not json", encoding="utf-8")
    output_dir = tmp_path / "out"

    with pytest.raises(RunnerError, match="Failed to read"):
        main(
            [
                "run-once-fixture",
                "--fixture",
                str(fixture_path),
                "--output-dir",
                str(output_dir),
            ]
        )


@pytest.mark.unit
def test_loop_fixture_runs_bounded_iterations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = _write_fixture(tmp_path)
    output_dir = tmp_path / "loop_artifacts"

    exit_code = main(
        [
            "loop-fixture",
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(output_dir),
            "--iterations",
            "3",
            "--interval-seconds",
            "1",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "loop-fixture"
    assert payload["iterations_completed"] == 3
    assert payload["state"]["total_runs"] == 3
    assert payload["state"]["successful_runs"] == 3
    assert payload["state"]["failed_runs"] == 0


@pytest.mark.unit
def test_loop_fixture_requires_minimum_iterations(tmp_path: Path) -> None:
    fixture_path = _write_fixture(tmp_path)

    with pytest.raises(RunnerError, match="--iterations must be >= 1"):
        main(
            [
                "loop-fixture",
                "--fixture",
                str(fixture_path),
                "--iterations",
                "0",
                "--interval-seconds",
                "1",
            ]
        )


@pytest.mark.unit
def test_loop_fixture_requires_minimum_interval(tmp_path: Path) -> None:
    fixture_path = _write_fixture(tmp_path)

    with pytest.raises(RunnerError, match="--interval-seconds must be >= 1"):
        main(
            [
                "loop-fixture",
                "--fixture",
                str(fixture_path),
                "--iterations",
                "1",
                "--interval-seconds",
                "0",
            ]
        )


@pytest.mark.unit
def test_status_reads_heartbeat_and_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = _write_fixture(tmp_path)
    output_dir = tmp_path / "artifacts"

    main(
        [
            "run-once-fixture",
            "--fixture",
            str(fixture_path),
            "--output-dir",
            str(output_dir),
            "--generated-at-utc",
            "2026-06-19T16:00:00Z",
        ]
    )
    capsys.readouterr()

    exit_code = main(["status", "--output-dir", str(output_dir)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact_dir_exists"] is True
    assert payload["artifact_count"] >= 7
    assert payload["heartbeat"]["schema_version"] == HEARTBEAT_SCHEMA
    assert payload["state"]["schema_version"] == STATE_SCHEMA
    assert payload["state"]["total_runs"] == 1
    assert payload["state"]["last_cycle_verdict"] == "PASS"
