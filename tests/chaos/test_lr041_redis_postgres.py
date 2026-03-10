"""Gate test for LR-041 Redis/Postgres restart chaos drill."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _assert_required_timeline_steps(timeline_path: Path) -> None:
    timeline_payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    timeline_steps = {str(event.get("step")) for event in timeline_payload}
    for required_step in ("t0", "t1", "t2", "t3", "t4", "t5", "t6"):
        assert (
            required_step in timeline_steps
        ), f"Timeline is missing required step {required_step}: {timeline_steps}"


@pytest.mark.chaos
@pytest.mark.local_only
def test_lr041_redis_postgres_drill_gate(tmp_path):
    if os.getenv("RUN_CHAOS_TESTS") != "1":
        pytest.skip("Set RUN_CHAOS_TESTS=1 to execute chaos tests.")

    repo_root = Path(__file__).resolve().parents[2]
    runner_path = (
        repo_root / "scripts" / "drills" / "lr041_redis_postgres_failure_runner.py"
    )
    assert runner_path.exists(), f"Missing LR-041 runner: {runner_path}"

    output_dir = tmp_path / "lr041_smoke"
    command = [
        sys.executable,
        str(runner_path),
        "--output-dir",
        str(output_dir),
        "--scenarios",
        "redis_restart",
        "--recovery-timeout",
        "60",
        "--stability-seconds",
        "5",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=300,
    )

    summary_path = output_dir / "lr041_summary.json"
    timeline_path = output_dir / "lr041_timeline.json"
    verdict_path = output_dir / "lr041_verdict.md"
    assert summary_path.exists(), f"Missing summary artifact: {summary_path}"
    assert timeline_path.exists(), f"Missing timeline artifact: {timeline_path}"
    assert verdict_path.exists(), f"Missing verdict artifact: {verdict_path}"

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    overall = summary_payload.get("summary", {}).get("overall", "FAIL").strip().upper()

    assert result.returncode == 0, (
        f"LR-041 smoke drill failed: rc={result.returncode}\n"
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}"
    )
    assert overall == "PASS", f"LR-041 smoke drill must PASS, got overall={overall}"

    assert summary_payload.get("drill_id") == "LR-041"
    scenarios = summary_payload.get("scenarios", [])
    assert scenarios, "Expected at least one scenario result in summary artifact"
    for scenario in scenarios:
        assert float(scenario.get("filled_delta", 1.0)) == 0.0, (
            "LR-030 zero execution must hold during LR-041 chaos, "
            f"scenario={scenario.get('name')} filled_delta={scenario.get('filled_delta')}"
        )
        assert (
            scenario.get("service_recovery_seconds", -1) >= 0
        ), f"Service did not recover: scenario={scenario.get('name')}"

    _assert_required_timeline_steps(timeline_path)
