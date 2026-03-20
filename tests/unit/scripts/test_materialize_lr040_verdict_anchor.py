"""Tests for committed LR-040 verdict-anchor materialization."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from lr040_soak_gate_eval import evaluate_lr040_soak
from materialize_lr040_verdict_anchor import (
    ContractError,
    materialize_lr040_verdict_anchor,
)


def _build_hourly_log(hours: int = 73) -> str:
    base = datetime(2026, 3, 21, 0, 0, 0, tzinfo=timezone.utc)
    lines = []
    for hour in range(hours):
        ts = base + timedelta(hours=hour)
        lines.append(
            f"{ts.strftime('%Y-%m-%d %H:%M:%S')} UTC - Hour {ts.hour:02d}: No restarts"
        )
    return "\n".join(lines) + "\n"


def _build_resource_snapshot(cpu_pct: float, mem_pct: float) -> str:
    return (
        "Timestamp: 2026-03-21 00:00:00 UTC\n"
        "=========================================\n"
        "NAME           CPU %     MEM USAGE / LIMIT     MEM %     NET I/O     BLOCK I/O\n"
        f"cdb_redis      {cpu_pct}%    24.5MiB / 256MiB      {mem_pct}%     1kB / 0B    0B / 0B\n"
        f"cdb_postgres   {cpu_pct + 5}%   120MiB / 512MiB      {mem_pct + 2}%   2kB / 1kB   4kB / 8kB\n"
    )


def _write_raw_lr040_artifacts(tmp_path: Path, *, failed: bool = False) -> tuple[Path, dict]:
    artifact_dir = tmp_path / "artifacts" / "soak_test_20260321_120000"
    artifact_dir.mkdir(parents=True)

    (artifact_dir / "hourly_checks.log").write_text(
        _build_hourly_log(), encoding="utf-8"
    )
    (artifact_dir / "resources_snapshot_00h.txt").write_text(
        _build_resource_snapshot(cpu_pct=15.0, mem_pct=25.0),
        encoding="utf-8",
    )
    (artifact_dir / "resources_snapshot_72h.txt").write_text(
        _build_resource_snapshot(cpu_pct=18.0, mem_pct=27.0),
        encoding="utf-8",
    )
    (artifact_dir / "restart_alerts.log").write_text("", encoding="utf-8")

    if failed:
        (artifact_dir / "soak_test_FAILED.txt").write_text(
            "2026-03-22 12:00:00 UTC - ABORT: Service restart detected",
            encoding="utf-8",
        )

    raw_result = evaluate_lr040_soak(artifact_dir)
    (artifact_dir / "lr040_soak_gate_eval.json").write_text(
        json.dumps(raw_result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return artifact_dir, raw_result


def test_materializes_committed_anchor_from_raw_pass(tmp_path: Path) -> None:
    artifact_dir, raw_result = _write_raw_lr040_artifacts(tmp_path)
    report_root = tmp_path / "reports" / "p5_canary" / "2026-03-21"

    target_path, payload = materialize_lr040_verdict_anchor(
        artifact_dir,
        report_root,
        repo_root=tmp_path,
        materialized_at_utc="2026-03-24T12:34:56Z",
    )

    assert target_path == report_root / "lr040" / "lr040_soak_gate_eval.json"
    assert payload["contract_role"] == "committed_verdict_anchor"
    assert payload["verdict"] == "PASS"
    assert payload["committed_reference_path"] == (
        "reports/p5_canary/2026-03-21/lr040/lr040_soak_gate_eval.json"
    )
    assert payload["source_raw_evidence"]["artifact_root"] == (
        "artifacts/soak_test_20260321_120000"
    )
    assert payload["source_raw_evidence"]["verdict_source"]["path"] == (
        "artifacts/soak_test_20260321_120000/lr040_soak_gate_eval.json"
    )
    assert payload["source_raw_evidence"]["hourly_log"]["path"] == (
        "artifacts/soak_test_20260321_120000/hourly_checks.log"
    )
    assert len(payload["source_raw_evidence"]["resource_snapshots"]) == 2
    assert payload["verdict_summary"]["metrics"] == raw_result["metrics"]
    assert payload["materialization"]["materialized_at_utc"] == "2026-03-24T12:34:56Z"
    assert payload["pass_required_before_start"] is True

    written = json.loads(target_path.read_text(encoding="utf-8"))
    assert written["verdict"] == "PASS"


def test_materializes_fail_without_claiming_go(tmp_path: Path) -> None:
    artifact_dir, _ = _write_raw_lr040_artifacts(tmp_path, failed=True)
    report_root = tmp_path / "reports" / "p5_canary" / "2026-03-21"

    _, payload = materialize_lr040_verdict_anchor(
        artifact_dir,
        report_root,
        repo_root=tmp_path,
        materialized_at_utc="2026-03-24T12:34:56Z",
    )

    assert payload["verdict"] == "FAIL"
    assert payload["source_raw_evidence"]["failed_marker"] is not None
    assert "NO-GO" in payload["governance_effect"]
    assert any("does not authorize" in note for note in payload["notes"])


def test_rejects_sources_outside_artifacts_soak_test_namespace(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "packages" / "shadow-soak-pass"
    artifact_dir.mkdir(parents=True)
    report_root = tmp_path / "reports" / "p5_canary" / "2026-03-21"

    with pytest.raises(ContractError, match="artifacts/soak_test_\\*"):
        materialize_lr040_verdict_anchor(
            artifact_dir,
            report_root,
            repo_root=tmp_path,
        )


def test_rejects_missing_raw_eval_file(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts" / "soak_test_20260321_120000"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "hourly_checks.log").write_text(_build_hourly_log(), encoding="utf-8")
    (artifact_dir / "resources_snapshot_00h.txt").write_text(
        _build_resource_snapshot(cpu_pct=15.0, mem_pct=25.0),
        encoding="utf-8",
    )
    (artifact_dir / "resources_snapshot_72h.txt").write_text(
        _build_resource_snapshot(cpu_pct=18.0, mem_pct=27.0),
        encoding="utf-8",
    )

    report_root = tmp_path / "reports" / "p5_canary" / "2026-03-21"

    with pytest.raises(ContractError, match="raw lr040_soak_gate_eval.json"):
        materialize_lr040_verdict_anchor(
            artifact_dir,
            report_root,
            repo_root=tmp_path,
        )
