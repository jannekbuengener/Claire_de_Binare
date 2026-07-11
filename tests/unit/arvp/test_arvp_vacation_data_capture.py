from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from tools.arvp_vacation.data_capture import (
    CAMPAIGN_STATE_FILENAME,
    DataCaptureError,
    build_preflight_report,
    start_campaign,
    stop_campaign,
    verify_go_phrase,
)
from tools.arvp_vacation.data_capture_contract import (
    DATA_CAPTURE_GO_PHRASE,
    DataCaptureContractError,
    classify_running_services,
    load_data_capture_manifest,
    resolve_planned_end_utc,
    resolve_runtime_window,
    validate_end_matches_start,
)


@pytest.fixture()
def manifest_path(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    manifest = {
        "schema_version": "1.0",
        "campaign_id": "arvp_vacation_data_capture_test",
        "source_sha": "RUNTIME_RESOLVE",
        "symbol": "BTCUSDT",
        "venue": "MEXC",
        "timeframe": "1m",
        "start_utc": "2026-07-11T12:00:00Z",
        "planned_end_utc": "2026-07-25T12:00:00Z",
        "max_duration_days": 14,
        "database_target": "public.candles_1m",
        "heartbeat_interval_seconds": 300,
        "stale_threshold_seconds": 180,
        "min_free_disk_gb": 1,
        "max_restart_budget": 3,
        "evidence_dir": "artifacts/arvp_vacation/data_capture",
        "allow_signal": False,
        "allow_execution": False,
        "allow_paper": False,
        "allow_live_trading": False,
    }
    path = repo / "manifest.yaml"
    path.write_text(yaml.dump(manifest), encoding="utf-8")
    return path


@pytest.mark.unit
def test_load_manifest_validates_14_day_window(manifest_path: Path) -> None:
    manifest = load_data_capture_manifest(manifest_path)
    validate_end_matches_start(
        manifest.start_utc, manifest.planned_end_utc, manifest.max_duration_days
    )


@pytest.mark.unit
def test_planned_end_exactly_14_days() -> None:
    start = "2026-07-11T12:00:00Z"
    end = resolve_planned_end_utc(start, 14)
    assert end == "2026-07-25T12:00:00Z"


@pytest.mark.unit
def test_reject_paper_flags(manifest_path: Path) -> None:
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    raw["allow_paper"] = True
    manifest_path.write_text(yaml.dump(raw), encoding="utf-8")
    with pytest.raises(DataCaptureContractError, match="allow_paper"):
        load_data_capture_manifest(manifest_path)


@pytest.mark.unit
def test_classify_forbidden_services() -> None:
    result = classify_running_services(
        ["cdb_postgres", "cdb_signal", "cdb_candles"],
        allowed=["cdb_postgres", "cdb_candles", "cdb_redis", "cdb_ws", "cdb_db_writer"],
        forbidden=["cdb_signal", "cdb_risk"],
    )
    assert result["running_forbidden"] == ["cdb_signal"]
    assert "cdb_postgres" in result["running_allowed"]


@pytest.mark.unit
def test_go_phrase_gate() -> None:
    verify_go_phrase(DATA_CAPTURE_GO_PHRASE)
    with pytest.raises(DataCaptureError, match="DATA-CAPTURE-GO"):
        verify_go_phrase("wrong phrase")


@pytest.mark.unit
def test_preflight_passes_with_mocks(manifest_path: Path, tmp_path: Path) -> None:
    repo = manifest_path.parent

    def fake_git(_: Path) -> str:
        return "clean"

    def fake_disk(_: Path) -> float:
        return 10.0

    def fake_coverage(_: Path, __: str, ___: int | None) -> dict:
        return {"available": True, "candle_count": 100}

    def fake_docker(args, cwd: Path):
        import subprocess

        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def fake_containers() -> list[str]:
        return ["cdb_postgres"]

    manifest = load_data_capture_manifest(manifest_path)
    report = build_preflight_report(
        manifest,
        repo_root=repo,
        docker_runner=fake_docker,
        container_lister=fake_containers,
        git_status_probe=fake_git,
        disk_probe=fake_disk,
        coverage_probe=fake_coverage,
        skip_docker=False,
    )
    assert report["passed"] is True
    assert report["verdict"] == "PREFLIGHT_PASS"


@pytest.mark.unit
def test_preflight_fails_on_forbidden_running(manifest_path: Path) -> None:
    repo = manifest_path.parent
    manifest = load_data_capture_manifest(manifest_path)

    def fake_containers() -> list[str]:
        return ["cdb_signal"]

    def fake_docker(args, cwd: Path):
        import subprocess

        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    report = build_preflight_report(
        manifest,
        repo_root=repo,
        docker_runner=fake_docker,
        container_lister=fake_containers,
        git_status_probe=lambda _: "clean",
        disk_probe=lambda _: 10.0,
        coverage_probe=lambda *_: {"available": True},
    )
    assert report["passed"] is False
    assert "no_forbidden_services_running" in report["failed_checks"]


@pytest.mark.unit
def test_start_stop_with_skip_docker(manifest_path: Path) -> None:
    repo = manifest_path.parent
    manifest = load_data_capture_manifest(manifest_path)
    started = start_campaign(
        manifest,
        repo_root=repo,
        go_phrase=DATA_CAPTURE_GO_PHRASE,
        skip_docker=True,
        git_status_probe=lambda _: "clean",
        disk_probe=lambda _: 10.0,
        coverage_probe=lambda *_: {"available": True, "candle_count": 0},
    )
    assert started["status"] == "running"
    state_path = (
        repo
        / "artifacts/arvp_vacation/data_capture"
        / manifest.campaign_id
        / CAMPAIGN_STATE_FILENAME
    )
    assert state_path.exists()
    stopped = stop_campaign(manifest, repo_root=repo, skip_docker=True)
    assert stopped["status"] == "stopped"


@pytest.mark.unit
def test_runtime_window_resolution(manifest_path: Path) -> None:
    manifest = load_data_capture_manifest(manifest_path)
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    raw["start_utc"] = "RUNTIME_RESOLVE"
    raw["planned_end_utc"] = "RUNTIME_RESOLVE"
    manifest_path.write_text(yaml.dump(raw), encoding="utf-8")
    manifest = load_data_capture_manifest(manifest_path)
    fixed = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    start, end = resolve_runtime_window(manifest, now=fixed)
    assert start == "2026-07-11T12:00:00Z"
    assert end == "2026-07-25T12:00:00Z"
