from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.evidence_harvester.coordinator import CoordinatorSummary
from tools.evidence_harvester.supervisor import (
    COORDINATOR_PID_FILENAME,
    SUPERVISION_STATE_FILENAME,
    SUPERVISION_STATE_SCHEMA,
    SupervisorError,
    build_subprocess_resume_launcher,
    main,
    parse_args,
    probe_process_alive,
    read_coordinator_pid_record,
    read_supervision_state,
    resolve_coordinator_process_alive,
    write_coordinator_pid_record,
    write_supervision_state,
)


def _write_runner_state(artifact_dir: Path, *, run_id: str = "run-a") -> None:
    payload = {
        "schema_version": "cdb.evidence_harvester.runner_state.v1",
        "run_id": run_id,
        "total_cycles_completed": 1,
        "coordinator_status": "sleeping",
        "next_cycle_due_at_utc": "2026-06-30T11:00:00Z",
    }
    (artifact_dir / "runner_state.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


@pytest.mark.unit
def test_probe_process_alive_uses_injected_probe() -> None:
    assert probe_process_alive(42, probe_fn=lambda pid: pid == 42) is True
    assert probe_process_alive(42, probe_fn=lambda pid: pid == 99) is False


@pytest.mark.unit
def test_probe_process_alive_rejects_non_positive_pid() -> None:
    assert probe_process_alive(0) is False
    assert probe_process_alive(-1) is False


@pytest.mark.unit
def test_write_and_read_coordinator_pid_record(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    record = write_coordinator_pid_record(
        artifact_dir, pid=12345, run_id="run-a", recorded_at_utc="2026-07-05T10:00:00Z"
    )
    assert record.pid == 12345
    assert read_coordinator_pid_record(artifact_dir) == record
    assert (artifact_dir / COORDINATOR_PID_FILENAME).exists()


@pytest.mark.unit
def test_write_coordinator_pid_record_rejects_invalid_pid(tmp_path: Path) -> None:
    with pytest.raises(SupervisorError):
        write_coordinator_pid_record(tmp_path, pid=0, run_id="run-a")


@pytest.mark.unit
def test_resolve_process_alive_missing_pid_record(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    alive, reason = resolve_coordinator_process_alive(artifact_dir)
    assert alive is False
    assert reason == "missing_coordinator_pid_record"


@pytest.mark.unit
def test_resolve_process_alive_stale_run_id(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_runner_state(artifact_dir, run_id="run-a")
    write_coordinator_pid_record(artifact_dir, pid=100, run_id="run-b")
    alive, reason = resolve_coordinator_process_alive(
        artifact_dir, probe_fn=lambda pid: True
    )
    assert alive is False
    assert reason == "stale_coordinator_pid_run_id_mismatch"


@pytest.mark.unit
def test_resolve_process_alive_dead_pid(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_runner_state(artifact_dir)
    write_coordinator_pid_record(artifact_dir, pid=100, run_id="run-a")
    alive, reason = resolve_coordinator_process_alive(
        artifact_dir, probe_fn=lambda pid: False
    )
    assert alive is False
    assert reason == "coordinator_pid_not_alive"


@pytest.mark.unit
def test_resolve_process_alive_live_pid(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_runner_state(artifact_dir)
    write_coordinator_pid_record(artifact_dir, pid=100, run_id="run-a")
    alive, reason = resolve_coordinator_process_alive(
        artifact_dir, probe_fn=lambda pid: True
    )
    assert alive is True
    assert reason == "coordinator_pid_alive"


@pytest.mark.unit
def test_supervision_state_contract(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    record = write_supervision_state(
        artifact_dir,
        run_id="run-a",
        coordinator_pid=100,
        poll_count=2,
        relaunch_count=1,
        last_decision={"action": "WAIT", "reason": "coordinator process alive"},
        last_error="",
        updated_at_utc="2026-07-05T10:00:00Z",
    )
    assert record.schema_version == SUPERVISION_STATE_SCHEMA
    loaded = read_supervision_state(artifact_dir)
    assert loaded == record
    assert (artifact_dir / SUPERVISION_STATE_FILENAME).exists()


@pytest.mark.unit
def test_build_subprocess_resume_launcher_uses_injected_popen(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_runner_state(artifact_dir)
    mock_proc = MagicMock()
    mock_proc.pid = 4242
    popen_calls: list[list[str]] = []

    def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
        popen_calls.append(cmd)
        return mock_proc

    launcher = build_subprocess_resume_launcher(
        repo_root=tmp_path,
        fixture_path=tmp_path / "fixture.json",
        artifact_dir=artifact_dir,
        iterations=10,
        cadence_seconds=900,
        max_restart_count=3,
        restart_backoff_seconds=30,
        popen_fn=fake_popen,
    )
    summary = launcher()
    assert summary.status == "LAUNCHED"
    assert popen_calls
    assert "resume-fixture-window" in popen_calls[0]
    pid_record = read_coordinator_pid_record(artifact_dir)
    assert pid_record is not None
    assert pid_record.pid == 4242


@pytest.mark.unit
def test_supervise_external_without_explicit_prints_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    exit_code = main(
        [
            "supervise-external",
            "--artifact-dir",
            str(tmp_path / "run"),
            "--fixture",
            str(fixture),
            "--iterations",
            "10",
        ]
    )
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert payload["explicit"] is False


@pytest.mark.unit
def test_plan_external_default_is_safe_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")
    exit_code = main(
        [
            "--pretty",
            "plan-external",
            "--artifact-dir",
            str(tmp_path / "run"),
            "--fixture",
            str(fixture),
            "--iterations",
            "10",
        ]
    )
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert payload["mode"] == "supervise-external"


@pytest.mark.unit
def test_parse_args_supervise_external_requires_explicit_by_default() -> None:
    args = parse_args(
        [
            "supervise-external",
            "--artifact-dir",
            "runs/x",
            "--fixture",
            "f.json",
            "--iterations",
            "288",
        ]
    )
    assert args.command == "supervise-external"
    assert args.explicit is False


@pytest.mark.unit
def test_record_coordinator_pid_requires_runner_state(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    with pytest.raises(SupervisorError):
        main(
            [
                "record-coordinator-pid",
                "--artifact-dir",
                str(artifact_dir),
                "--pid",
                "1234",
            ]
        )


@pytest.mark.unit
def test_record_coordinator_pid_writes_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact_dir = tmp_path / "run"
    artifact_dir.mkdir()
    _write_runner_state(artifact_dir)
    exit_code = main(
        [
            "record-coordinator-pid",
            "--artifact-dir",
            str(artifact_dir),
            "--pid",
            "1234",
        ]
    )
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert exit_code == 0
    assert payload["record"]["pid"] == 1234
    assert read_coordinator_pid_record(artifact_dir) is not None
