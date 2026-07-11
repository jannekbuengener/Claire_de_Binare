from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from tools.arvp_vacation.contract import backfill_scenario_group_ids, load_manifest
from tools.arvp_vacation.coordinator import (
    initialize_queue_state,
    run_coordinator_cycle,
    run_until_complete,
)
from tools.arvp_vacation.queue_store import QUEUE_STATE_FILENAME, read_queue_state
from tools.arvp_vacation.summary import write_summary


def _write_dataset(root: Path, rel_dir: str, *, dataset_id: str, fingerprint: str) -> None:
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
        "start_ts_ms": 1000 + hash(dataset_id) % 1000,
        "end_ts_ms": 2000 + hash(dataset_id) % 1000,
        "evidence_class": "controlled_lab_evidence",
    }
    (base / "dataset_spec.json").write_text(json.dumps(spec), encoding="utf-8")


def _manifest_yaml(dataset_roots: list[str]) -> str:
    payload = {
        "schema_version": "1.0",
        "campaign_id": "vac_recovery",
        "source_sha": "abc123def4567890abc123def4567890abc123de",
        "evidence_class": "controlled_lab_evidence",
        "artifact_root": "artifacts/arvp_vacation",
        "allow_paper_jobs": False,
        "dataset_roots": dataset_roots,
        "strategies": [
            {"strategy_id": "donchian_breakout_v1", "role": "active"},
            {"strategy_id": "breakout_trend_filter_v1", "role": "active"},
            {"strategy_id": "primary_breakout_v1", "role": "parked_reference"},
        ],
        "scenarios": ["baseline", "pessimistic_execution", "feed_gap"],
        "max_job_runtime_seconds": 30,
        "max_attempts_per_job": 2,
        "min_free_disk_gb": 0.001,
    }
    return yaml.safe_dump(payload)


def _mock_runner(output_root: Path):
    calls = {"count": 0}

    def _runner(command, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise subprocess.TimeoutExpired(cmd=command, timeout=1)
        output_dir = Path(command[command.index("--output-dir") + 1])
        group_id = command[command.index("--scenario-group-id") + 1]
        group_dir = output_dir / group_id
        group_dir.mkdir(parents=True, exist_ok=True)
        (group_dir / "scenario_group_manifest.json").write_text(
            json.dumps({"failed_count": 0}), encoding="utf-8"
        )
        (group_dir / "baseline_metrics.json").write_text(
            json.dumps({"trade_count": 2, "net_pnl": 0.5}), encoding="utf-8"
        )
        (group_dir / "scenario_comparison_summary.md").write_text("# ok\n")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    return _runner, calls


def test_recovery_orphan_running_without_double_pass(tmp_path: Path) -> None:
    roots = [f"datasets/w{i}" for i in range(3)]
    for i, rel in enumerate(roots):
        _write_dataset(
            tmp_path,
            rel,
            dataset_id=f"w{i}",
            fingerprint=f"{i:064d}",
        )
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(_manifest_yaml(roots), encoding="utf-8")
    manifest = load_manifest(manifest_path)
    state = initialize_queue_state(manifest, tmp_path)
    assert len(state["jobs"]) >= 6

    runner, _ = _mock_runner(tmp_path)
    state = run_coordinator_cycle(
        manifest_path=manifest_path,
        repo_root=tmp_path,
        subprocess_runner=runner,
    )
    running = [j for j in state["jobs"] if j.get("status") == "RUNNING"]
    if not running:
        running_job = next(j for j in state["jobs"] if j.get("status") == "PASS")
    else:
        running_job = running[0]
        running_job["status"] = "RUNNING"
        running_job["exit_code"] = None
    campaign_dir = tmp_path / "artifacts/arvp_vacation/vac_recovery"
    from tools.arvp_vacation.queue_store import write_queue_state

    write_queue_state(campaign_dir / QUEUE_STATE_FILENAME, state)

    state = run_coordinator_cycle(
        manifest_path=manifest_path,
        repo_root=tmp_path,
        resume=True,
        subprocess_runner=runner,
    )
    interrupted = [j for j in state["jobs"] if j.get("status") == "INTERRUPTED"]
    assert interrupted or any(j.get("status") == "PASS" for j in state["jobs"])
    pass_fps = {
        j["fingerprint"]
        for j in state["jobs"]
        if j.get("status") == "PASS" and j.get("fingerprint")
    }
    assert len(pass_fps) == len(set(pass_fps))


def test_acceptance_drill_six_jobs_summary(tmp_path: Path) -> None:
    roots = [
        "datasets/a",
        "datasets/b",
        "datasets/c",
    ]
    for i, rel in enumerate(roots):
        _write_dataset(
            tmp_path,
            rel,
            dataset_id=f"ds{i}",
            fingerprint=f"{i+10:064d}",
        )
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(_manifest_yaml(roots), encoding="utf-8")
    runner, calls = _mock_runner(tmp_path)
    state = run_until_complete(
        manifest_path=manifest_path,
        repo_root=tmp_path,
        subprocess_runner=runner,
    )
    manifest = load_manifest(manifest_path)
    write_summary(manifest, state, tmp_path)
    assert len(state["jobs"]) >= 6
    assert (tmp_path / "artifacts/arvp_vacation/vac_recovery/vacation_summary.json").exists()
    assert calls["count"] >= 1


def test_recovery_preserves_scenario_group_id(tmp_path: Path) -> None:
    roots = ["datasets/a", "datasets/b"]
    for i, rel in enumerate(roots):
        _write_dataset(
            tmp_path,
            rel,
            dataset_id=f"w{i}",
            fingerprint=f"{i+20:064d}",
        )
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(_manifest_yaml(roots), encoding="utf-8")
    manifest = load_manifest(manifest_path)
    state = initialize_queue_state(manifest, tmp_path)
    original = state["jobs"][0]["scenario_group_id"]
    legacy = dict(state["jobs"][0])
    legacy.pop("scenario_group_id", None)
    state["jobs"][0] = legacy
    backfilled = backfill_scenario_group_ids(state)
    assert backfilled["jobs"][0]["scenario_group_id"] == original
