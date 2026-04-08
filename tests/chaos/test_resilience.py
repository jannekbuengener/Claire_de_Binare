"""Canonical repo-native 431C gate test coverage for LR-042 resilience drills."""

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
def test_resilience_suite_gate_lr042(tmp_path):
    if os.getenv("RUN_CHAOS_TESTS") != "1":
        pytest.skip("Set RUN_CHAOS_TESTS=1 to execute resilience tests.")

    repo_root = Path(__file__).resolve().parents[2]
    runner_path = (
        repo_root / "scripts" / "drills" / "lr042_network_latency_packet_loss_runner.py"
    )
    assert runner_path.exists(), f"Missing LR-042 runner: {runner_path}"

    output_dir = tmp_path / "lr042_smoke"
    command = [
        sys.executable,
        str(runner_path),
        "--output-dir",
        str(output_dir),
        "--scenarios",
        "latency_only",
        "--fault-duration-seconds",
        "4",
        "--recovery-timeout",
        "45",
        "--stability-seconds",
        "5",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=360,
    )

    summary_path = output_dir / "lr042_summary.json"
    timeline_path = output_dir / "lr042_timeline.json"
    verdict_path = output_dir / "lr042_verdict.md"
    assert summary_path.exists(), f"Missing summary artifact: {summary_path}"
    assert timeline_path.exists(), f"Missing timeline artifact: {timeline_path}"
    assert verdict_path.exists(), f"Missing verdict artifact: {verdict_path}"

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    overall = summary_payload.get("summary", {}).get("overall", "FAIL").strip().upper()

    if result.returncode == 3 or overall == "UNSUPPORTED":
        reason = summary_payload.get("unsupported_reason", "netem unsupported")
        pytest.skip(f"LR-042 unsupported in current environment: {reason}")

    assert result.returncode == 0, (
        f"LR-042 smoke drill failed: rc={result.returncode}\n"
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}"
    )
    assert overall in {"PASS", "WARN"}, (
        "LR-042 smoke drill must end in PASS/WARN for gated chaos test, "
        f"got overall={overall}"
    )

    assert summary_payload.get("drill_id") == "LR-042"
    scenarios = summary_payload.get("scenarios", [])
    assert scenarios, "Expected at least one scenario result in summary artifact"
    for scenario in scenarios:
        assert float(scenario.get("filled_delta", 1.0)) == 0.0, (
            "LR-030 zero execution must hold in LR-042 chaos smoke, "
            f"scenario={scenario.get('name')} filled_delta={scenario.get('filled_delta')}"
        )

    _assert_required_timeline_steps(timeline_path)
