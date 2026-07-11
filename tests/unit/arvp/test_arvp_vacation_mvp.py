from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from tools.arvp_vacation.contract import (
    JOB_SKIPPED_DUPLICATE,
    VacationContractError,
    build_job_fingerprint,
    discover_datasets,
    load_manifest,
    parse_dataset_spec,
)
from tools.arvp_vacation.coordinator import (
    CAMPAIGN_FATAL_STOP,
    CAMPAIGN_RUNNING,
    initialize_queue_state,
    preflight_manifest,
    run_coordinator_cycle,
)
from tools.arvp_vacation.job_runner import JobRunResult, build_replay_command, run_replay_job
from tools.arvp_vacation.queue_store import (
    QUEUE_STATE_FILENAME,
    atomic_write_json,
    read_queue_state,
    recover_orphan_running_jobs,
    write_queue_state,
)
from tools.arvp_vacation.summary import build_summary_payload, write_summary


def _write_dataset(
    root: Path,
    rel_dir: str,
    *,
    dataset_id: str,
    fingerprint: str,
    start_ts_ms: int = 1000,
    end_ts_ms: int = 2000,
) -> None:
    base = root / rel_dir
    base.mkdir(parents=True, exist_ok=True)
    candles = base / "candles.jsonl"
    candles.write_text('{"ts_ms":1,"open":1,"high":1,"low":1,"close":1,"volume":1}\n')
    spec = {
        "dataset_id": dataset_id,
        "source": "file",
        "file_path": f"{rel_dir}/candles.jsonl".replace("\\", "/"),
        "symbol": "BTCUSDT",
        "fingerprint": fingerprint,
        "start_ts_ms": start_ts_ms,
        "end_ts_ms": end_ts_ms,
        "evidence_class": "controlled_lab_evidence",
    }
    (base / "dataset_spec.json").write_text(json.dumps(spec), encoding="utf-8")


def _manifest_yaml(
    *,
    campaign_id: str = "vac_test",
    allow_paper: bool = False,
    dataset_roots: list[str] | None = None,
) -> str:
    payload = {
        "schema_version": "1.0",
        "campaign_id": campaign_id,
        "source_sha": "abc123def456",
        "evidence_class": "controlled_lab_evidence",
        "artifact_root": "artifacts/arvp_vacation",
        "allow_paper_jobs": allow_paper,
        "dataset_roots": dataset_roots or ["datasets/a", "datasets/b"],
        "strategies": [
            {"strategy_id": "donchian_breakout_v1", "role": "active"},
            {"strategy_id": "breakout_trend_filter_v1", "role": "active"},
        ],
        "scenarios": ["baseline", "pessimistic_execution", "feed_gap"],
        "max_job_runtime_seconds": 30,
        "max_attempts_per_job": 2,
        "min_free_disk_gb": 0.001,
    }
    return yaml.safe_dump(payload)


@pytest.fixture
def vacation_repo(tmp_path: Path) -> Path:
    _write_dataset(
        tmp_path,
        "datasets/a",
        dataset_id="ds_a",
        fingerprint="a" * 64,
    )
    _write_dataset(
        tmp_path,
        "datasets/b",
        dataset_id="ds_b",
        fingerprint="b" * 64,
        start_ts_ms=3000,
        end_ts_ms=4000,
    )
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(_manifest_yaml(), encoding="utf-8")
    return tmp_path


def test_manifest_validation_rejects_paper_jobs(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(_manifest_yaml(allow_paper=True), encoding="utf-8")
    manifest = load_manifest(path)
    with pytest.raises(VacationContractError, match="allow_paper_jobs"):
        manifest.validate_preflight()


def test_fingerprint_stable() -> None:
    fp1 = build_job_fingerprint(
        source_sha="abc",
        strategy_id="donchian_breakout_v1",
        dataset_fingerprint="d" * 64,
        scenarios=["feed_gap", "baseline"],
        speedup_profile="instant",
    )
    fp2 = build_job_fingerprint(
        source_sha="abc",
        strategy_id="donchian_breakout_v1",
        dataset_fingerprint="d" * 64,
        scenarios=["baseline", "feed_gap"],
        speedup_profile="instant",
    )
    assert fp1 == fp2


def test_dataset_dedup_by_time_window(tmp_path: Path) -> None:
    _write_dataset(
        tmp_path,
        "datasets/dup1",
        dataset_id="dup1",
        fingerprint="c" * 64,
    )
    _write_dataset(
        tmp_path,
        "datasets/dup2",
        dataset_id="dup2",
        fingerprint="d" * 64,
    )
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        _manifest_yaml(dataset_roots=["datasets/dup1", "datasets/dup2"]),
        encoding="utf-8",
    )
    manifest = load_manifest(manifest_path)
    datasets = discover_datasets(manifest, tmp_path)
    assert len(datasets) == 1


def test_atomic_queue_write_and_read(tmp_path: Path) -> None:
    path = tmp_path / "queue_state.json"
    payload = {"campaign_id": "x", "jobs": []}
    write_queue_state(path, payload)
    loaded = read_queue_state(path)
    assert loaded["campaign_id"] == "x"
    assert loaded["schema_version"] == "1.0"


def test_orphan_running_recovery() -> None:
    state = {
        "jobs": [
            {"job_id": "j1", "status": "RUNNING"},
            {"job_id": "j2", "status": "PASS"},
        ]
    }
    updated, interrupted = recover_orphan_running_jobs(state, now_fn=lambda: "2026-07-11T00:00:00Z")
    assert interrupted == ["j1"]
    assert updated["jobs"][0]["status"] == "INTERRUPTED"


def test_initialize_queue_has_six_jobs(vacation_repo: Path) -> None:
    manifest = load_manifest(vacation_repo / "manifest.yaml")
    state = initialize_queue_state(manifest, vacation_repo)
    assert len(state["jobs"]) == 4


def test_duplicate_fingerprint_marked_skipped(vacation_repo: Path) -> None:
    manifest = load_manifest(vacation_repo / "manifest.yaml")
    manifest = load_manifest(vacation_repo / "manifest.yaml")
    state = initialize_queue_state(manifest, vacation_repo)
    fps = [j["fingerprint"] for j in state["jobs"]]
    assert len(fps) == len(set(fps))


def _mock_subprocess_factory(group_dir: Path):
    def _runner(command, **kwargs):
        group_dir.mkdir(parents=True, exist_ok=True)
        (group_dir / "scenario_group_manifest.json").write_text(
            json.dumps({"failed_count": 0}), encoding="utf-8"
        )
        (group_dir / "baseline_metrics.json").write_text(
            json.dumps({"trade_count": 5, "net_pnl": 1.0}), encoding="utf-8"
        )
        (group_dir / "scenario_comparison_summary.md").write_text("# ok\n")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    return _runner


def test_coordinator_runs_job_and_persists(vacation_repo: Path) -> None:
    manifest = load_manifest(vacation_repo / "manifest.yaml")

    def runner(command, **kwargs):
        output_dir = Path(command[command.index("--output-dir") + 1])
        job_id = command[command.index("--scenario-group-id") + 1]
        return _mock_subprocess_factory(output_dir / job_id)(command, **kwargs)

    state = run_coordinator_cycle(
        manifest_path=vacation_repo / "manifest.yaml",
        repo_root=vacation_repo,
        subprocess_runner=runner,
    )
    assert state["campaign_status"] in {CAMPAIGN_RUNNING, "completed"}
    state_path = vacation_repo / "artifacts/arvp_vacation/vac_test" / QUEUE_STATE_FILENAME
    assert state_path.exists()
    finished = [j for j in state["jobs"] if j.get("exit_code") is not None]
    assert len(finished) == 1
    assert finished[0]["status"] == "PASS"


def test_disk_fatal_stop(vacation_repo: Path) -> None:
    state = run_coordinator_cycle(
        manifest_path=vacation_repo / "manifest.yaml",
        repo_root=vacation_repo,
        disk_probe=lambda _p: 0.0,
    )
    assert state["campaign_status"] == CAMPAIGN_FATAL_STOP


def test_insufficient_data_dataset(vacation_repo: Path) -> None:
    bad = vacation_repo / "datasets/bad/dataset_spec.json"
    bad.parent.mkdir(parents=True)
    bad.write_text(json.dumps({"dataset_id": "bad"}), encoding="utf-8")
    manifest_path = vacation_repo / "manifest_bad.yaml"
    manifest_path.write_text(
        _manifest_yaml(dataset_roots=["datasets/bad"]),
        encoding="utf-8",
    )
    datasets = discover_datasets(load_manifest(manifest_path), vacation_repo)
    assert datasets == []


def test_duplicate_skip_on_completed_fingerprint(vacation_repo: Path) -> None:
    campaign_dir = vacation_repo / "artifacts/arvp_vacation/vac_test"
    campaign_dir.mkdir(parents=True)
    manifest = load_manifest(vacation_repo / "manifest.yaml")
    state = initialize_queue_state(manifest, vacation_repo)
    fp = state["jobs"][0]["fingerprint"]
    for job in state["jobs"]:
        job["status"] = "PASS"
        job["exit_code"] = 0
        job["artifacts_complete"] = True
    state["completed_fingerprints"] = [fp]
    dup = dict(state["jobs"][0])
    dup["job_id"] = dup["job_id"] + "-dup"
    dup["status"] = "PENDING"
    dup["exit_code"] = None
    dup["artifacts_complete"] = False
    state["jobs"] = [dup]
    write_queue_state(campaign_dir / QUEUE_STATE_FILENAME, state)

    def runner(command, **kwargs):
        output_dir = Path(command[command.index("--output-dir") + 1])
        job_id = command[command.index("--scenario-group-id") + 1]
        return _mock_subprocess_factory(output_dir / job_id)(command, **kwargs)

    state = run_coordinator_cycle(
        manifest_path=vacation_repo / "manifest.yaml",
        repo_root=vacation_repo,
        resume=True,
        subprocess_runner=runner,
    )
    skipped = [j for j in state["jobs"] if j["status"] == JOB_SKIPPED_DUPLICATE]
    assert skipped


def test_summary_generation(vacation_repo: Path) -> None:
    manifest = load_manifest(vacation_repo / "manifest.yaml")
    state = initialize_queue_state(manifest, vacation_repo)
    state["jobs"][0]["status"] = "PASS"
    state["jobs"][0]["artifacts_complete"] = True
    state["jobs"][0]["scenario_metrics"] = {
        "baseline": {"trade_count": 3, "net_pnl": 1.0},
        "_group_manifest": {"failed_count": 0},
    }
    summary = build_summary_payload(manifest, state)
    assert summary["ranking_ready"] is False
    json_path, md_path = write_summary(manifest, state, vacation_repo)
    assert json_path.exists()
    assert md_path.exists()


def test_build_replay_command_uses_strategy_replay_runner(vacation_repo: Path) -> None:
    manifest = load_manifest(vacation_repo / "manifest.yaml")
    job = initialize_queue_state(manifest, vacation_repo)["jobs"][0]
    cmd = build_replay_command(
        repo_root=vacation_repo,
        manifest=manifest,
        job=job,
        replay_output_dir=vacation_repo / "out",
    )
    assert "services.validation.strategy_replay_runner" in cmd


def test_preflight_manifest(vacation_repo: Path) -> None:
    info = preflight_manifest(vacation_repo / "manifest.yaml", vacation_repo)
    assert info["dataset_count"] == 2
    assert info["job_count_estimate"] == 4
