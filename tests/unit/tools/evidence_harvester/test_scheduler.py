from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.evidence_harvester.scheduler import SchedulerValidationError, main


def _fixture_payload() -> dict[str, object]:
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
def test_scheduler_defaults_to_safe_plan(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "plan"
    assert payload["default_mode"] == "dry-run"
    assert payload["scheduled_action"] == "run-once-fixture"


@pytest.mark.unit
def test_scheduler_main_uses_sys_argv_when_none(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_path = _write_fixture(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scheduler", "plan", "--fixture", str(fixture_path)],
    )

    exit_code = main()

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "plan"
    assert payload["fixture"] == str(fixture_path)


@pytest.mark.unit
def test_run_once_fixture_writes_snapshot_artifacts(
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
    assert Path(payload["artifacts"]["collector_report"]).exists()
    assert Path(payload["artifacts"]["snapshot_json"]).exists()
    assert Path(payload["artifacts"]["snapshot_markdown"]).exists()
    assert payload["latest_snapshot"]["generated_at_utc"] == "2026-06-19T16:00:00Z"
    assert payload["latest_snapshot"]["overall_status"] == "blocked"


@pytest.mark.unit
def test_status_reads_latest_snapshot_from_local_artifacts(
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
    assert payload["artifacts_present"] is True
    assert payload["latest_snapshot"]["collector_report_id"].startswith("harv-")
    assert payload["latest_snapshot"]["overall_status"] == "blocked"


@pytest.mark.unit
def test_install_requires_explicit_flag(tmp_path: Path) -> None:
    fixture_path = _write_fixture(tmp_path)

    with pytest.raises(SchedulerValidationError, match="install requires --explicit"):
        main(["install", "--fixture", str(fixture_path)])


@pytest.mark.unit
def test_install_path_is_patchable_and_does_not_run_real_task_install_in_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_path = _write_fixture(tmp_path)
    calls: list[list[str]] = []

    def _fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert check is True
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("tools.evidence_harvester.scheduler.subprocess.run", _fake_run)

    exit_code = main(
        [
            "install",
            "--fixture",
            str(fixture_path),
            "--explicit",
            "--start-time",
            "04:30",
        ]
    )

    assert exit_code == 0
    assert calls
    assert calls[0][0] == "schtasks.exe"
    assert "/Create" in calls[0]
    tr_index = calls[0].index("/TR") + 1
    tr_command = calls[0][tr_index]
    assert tr_command.endswith("run_task.cmd")
    assert len(tr_command) <= 261
    payload = json.loads(capsys.readouterr().out)
    assert payload["installed"] is True
    assert payload["start_time"] == "04:30"
    assert Path(payload["run_task_cmd"]).exists()
