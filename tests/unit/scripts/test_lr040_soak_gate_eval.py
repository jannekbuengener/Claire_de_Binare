"""Tests for lr040_soak_gate_eval.py — 72h soak stability gate (Issue #786)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from lr040_soak_gate_eval import evaluate_lr040_soak


def _build_hourly_log(hours: int = 73) -> str:
    """Generate hourly_checks.log spanning ``hours`` hours."""
    lines = []
    for h in range(hours):
        day_offset = h // 24
        hour_of_day = h % 24
        lines.append(
            f"2026-03-08 {hour_of_day:02d}:00:00 UTC - "
            f"Hour {hour_of_day}: No restarts"
        )
    # Fix: generate distinct days so timestamps actually span 72+ hours
    result = []
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 3, 8, 0, 0, 0, tzinfo=timezone.utc)
    for h in range(hours):
        ts = base + timedelta(hours=h)
        result.append(
            f"{ts.strftime('%Y-%m-%d %H:%M:%S')} UTC - " f"Hour {ts.hour}: No restarts"
        )
    return "\n".join(result) + "\n"


def _build_resource_snapshot(cpu_pct: float = 15.0, mem_pct: float = 25.0) -> str:
    """Generate a resource snapshot file matching docker stats format."""
    return (
        "Timestamp: 2026-03-08 00:00:00 UTC\n"
        "=========================================\n"
        f"NAME           CPU %     MEM USAGE / LIMIT     MEM %     NET I/O     BLOCK I/O\n"
        f"cdb_redis      {cpu_pct}%    24.5MiB / 256MiB      {mem_pct}%     1kB / 0B    0B / 0B\n"
        f"cdb_postgres   {cpu_pct + 5}%   120MiB / 512MiB      {mem_pct + 2}%   2kB / 1kB   4kB / 8kB\n"
    )


def _write_passing_artifacts(tmp_path: Path, **overrides) -> Path:
    """Create a soak artifact directory that passes all LR-040 checks."""
    artifact_dir = tmp_path / "soak_artifacts"
    artifact_dir.mkdir()

    hours = overrides.get("hours", 73)
    (artifact_dir / "hourly_checks.log").write_text(
        _build_hourly_log(hours), encoding="utf-8"
    )

    # Two resource snapshots (first and last) with stable memory
    first_mem = overrides.get("first_mem_pct", 25.0)
    last_mem = overrides.get("last_mem_pct", 28.0)
    first_cpu = overrides.get("first_cpu_pct", 15.0)
    last_cpu = overrides.get("last_cpu_pct", 20.0)

    (artifact_dir / "resources_snapshot_00h.txt").write_text(
        _build_resource_snapshot(cpu_pct=first_cpu, mem_pct=first_mem),
        encoding="utf-8",
    )
    (artifact_dir / "resources_snapshot_72h.txt").write_text(
        _build_resource_snapshot(cpu_pct=last_cpu, mem_pct=last_mem),
        encoding="utf-8",
    )

    return artifact_dir


class TestLR040SoakGatePass:
    def test_full_pass(self, tmp_path: Path) -> None:
        result = evaluate_lr040_soak(_write_passing_artifacts(tmp_path))
        assert result["verdict"] == "PASS"
        assert result["failures"] == []
        assert result["control"] == "LR-040"
        assert result["schema_version"] == "1.1"

    def test_metrics_populated(self, tmp_path: Path) -> None:
        result = evaluate_lr040_soak(_write_passing_artifacts(tmp_path))
        assert result["metrics"]["duration_hours"] >= 72.0
        assert result["metrics"]["resource_snapshot_count"] == 2
        assert result["metrics"]["max_memory_growth_pct"] is not None
        assert result["metrics"]["overall_cpu_avg_pct"] is not None


class TestLR040SoakGateFailClosed:
    def test_fails_on_short_duration(self, tmp_path: Path) -> None:
        result = evaluate_lr040_soak(_write_passing_artifacts(tmp_path, hours=50))
        assert result["verdict"] == "FAIL"
        assert "duration_gte_72h" in result["failures"]

    def test_fails_on_missing_hourly_log(self, tmp_path: Path) -> None:
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "hourly_checks.log").unlink()
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "hourly_log_present" in result["failures"]
        assert "duration_gte_72h" in result["failures"]

    def test_fails_on_failed_marker(self, tmp_path: Path) -> None:
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_FAILED.txt").write_text(
            "2026-03-09 12:00:00 UTC - ABORT: Service restart detected",
            encoding="utf-8",
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "no_failed_marker" in result["failures"]

    def test_fails_on_restart_alerts(self, tmp_path: Path) -> None:
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "restart_alerts.log").write_text(
            "2026-03-09 - RESTART DETECTED: cdb_redis (Up 5 seconds)",
            encoding="utf-8",
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "no_restart_alerts" in result["failures"]

    def test_fails_on_high_memory_growth(self, tmp_path: Path) -> None:
        result = evaluate_lr040_soak(
            _write_passing_artifacts(tmp_path, first_mem_pct=20.0, last_mem_pct=35.0)
        )
        assert result["verdict"] == "FAIL"
        assert "memory_growth_below_10pct" in result["failures"]

    def test_fails_on_high_cpu(self, tmp_path: Path) -> None:
        result = evaluate_lr040_soak(
            _write_passing_artifacts(tmp_path, first_cpu_pct=72.0, last_cpu_pct=75.0)
        )
        assert result["verdict"] == "FAIL"
        assert "cpu_avg_below_70pct" in result["failures"]

    def test_fails_on_missing_snapshots(self, tmp_path: Path) -> None:
        artifact_dir = _write_passing_artifacts(tmp_path)
        for f in artifact_dir.glob("resources_snapshot_*.txt"):
            f.unlink()
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "resource_snapshots_present" in result["failures"]

    def test_empty_restart_alerts_file_passes(self, tmp_path: Path) -> None:
        """Empty restart_alerts.log = no restarts = OK."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "restart_alerts.log").write_text("", encoding="utf-8")
        result = evaluate_lr040_soak(artifact_dir)
        assert "no_restart_alerts" not in result["failures"]


class TestLR040SoakGateInconclusive:
    """Tests for environment_interruption classification (Issue #1270)."""

    def test_inconclusive_on_env_interruption_marker(self, tmp_path: Path) -> None:
        """soak_test_INCONCLUSIVE.txt present → verdict INCONCLUSIVE."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_INCONCLUSIVE.txt").write_text(
            "2026-03-24 17:22:51 UTC - INCONCLUSIVE: Environment interruption detected"
            " (cause=environment_interruption, containers=22/22, uptime_spread_s=1,"
            " monitor_container_fresh=0)",
            encoding="utf-8",
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "INCONCLUSIVE"
        # INCONCLUSIVE is a distinct verdict class, not a generic failed check.
        assert "no_inconclusive_marker" not in result["failures"]

    def test_inconclusive_is_not_pass(self, tmp_path: Path) -> None:
        """INCONCLUSIVE must not be mistaken for PASS (fail-closed)."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_INCONCLUSIVE.txt").write_text(
            "inconclusive", encoding="utf-8"
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] != "PASS"

    def test_inconclusive_with_restart_alerts_still_inconclusive(
        self, tmp_path: Path
    ) -> None:
        """INCONCLUSIVE marker + restart_alerts.log → INCONCLUSIVE (env wins)."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_INCONCLUSIVE.txt").write_text(
            "inconclusive", encoding="utf-8"
        )
        (artifact_dir / "restart_alerts.log").write_text(
            "2026-03-24 17:22:51 UTC - ENVIRONMENT_INTERRUPTION: 22/22 containers,"
            " spread=1s, monitor_fresh=0",
            encoding="utf-8",
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "INCONCLUSIVE"

    def test_sut_restart_marker_without_inconclusive_is_fail(
        self, tmp_path: Path
    ) -> None:
        """soak_test_FAILED.txt without INCONCLUSIVE → FAIL (isolated SUT restart)."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_FAILED.txt").write_text(
            "2026-03-24 10:00:00 UTC - ABORT: Service restart detected"
            " (cause=sut_restart, containers=1/22)",
            encoding="utf-8",
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "no_failed_marker" in result["failures"]
        assert "no_inconclusive_marker" not in result["failures"]

    def test_both_markers_is_fail_closed(self, tmp_path: Path) -> None:
        """Both markers present simultaneously = scripting error → FAIL (fail-closed)."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_FAILED.txt").write_text("failed", encoding="utf-8")
        (artifact_dir / "soak_test_INCONCLUSIVE.txt").write_text(
            "inconclusive", encoding="utf-8"
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "not_both_markers" in result["failures"]
        assert result["artifacts"]["restart_cause"] == "conflicting_markers"

    def test_restart_cause_and_inconclusive_marker_in_artifacts(
        self, tmp_path: Path
    ) -> None:
        """restart_cause and inconclusive_marker are present in the artifacts payload."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "soak_test_INCONCLUSIVE.txt").write_text(
            "inconclusive", encoding="utf-8"
        )
        (artifact_dir / "restart_alerts.log").write_text(
            "2026-03-24 17:22:51 UTC - ENVIRONMENT_INTERRUPTION: 22/22",
            encoding="utf-8",
        )
        result = evaluate_lr040_soak(artifact_dir)
        assert result["artifacts"]["restart_cause"] == "environment_interruption"
        assert (
            result["artifacts"]["inconclusive_marker"] == "soak_test_INCONCLUSIVE.txt"
        )


class TestLR040SoakGateRunIntent:
    """Tests for run intent separation (Issue #1278)."""

    def test_validation_intent_returns_not_applicable(self, tmp_path: Path) -> None:
        """run_intent.txt = validation -> NOT_APPLICABLE, no LR-040 checks run."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "run_intent.txt").write_text("validation\n", encoding="utf-8")
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "NOT_APPLICABLE"
        assert result["run_intent"] == "validation"
        assert result["checks"] == {}
        assert result["failures"] == []
        assert result["control"] == "LR-040"

    def test_missing_run_intent_is_legacy_lr040(self, tmp_path: Path) -> None:
        """No run_intent.txt (pre-#1278 artifacts) -> normal LR-040 evaluation."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        assert not (artifact_dir / "run_intent.txt").exists()
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "PASS"
        assert result["run_intent"] == "lr040"

    def test_lr040_intent_runs_normal_evaluation(self, tmp_path: Path) -> None:
        """run_intent.txt = lr040 -> normal LR-040 evaluation proceeds."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "run_intent.txt").write_text("lr040\n", encoding="utf-8")
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "PASS"
        assert result["run_intent"] == "lr040"
        assert "hourly_log_present" in result["checks"]

    def test_validation_intent_exit_code_nonzero(self, tmp_path: Path) -> None:
        """NOT_APPLICABLE verdict must not be mistaken for PASS (fail-closed)."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "run_intent.txt").write_text("validation\n", encoding="utf-8")
        result = evaluate_lr040_soak(artifact_dir)
        # main() uses: sys.exit(0 if result["verdict"] == "PASS" else 1)
        assert result["verdict"] != "PASS"

    def test_validation_intent_even_with_72h_data(self, tmp_path: Path) -> None:
        """Validation run with full 72h data must still be NOT_APPLICABLE."""
        artifact_dir = _write_passing_artifacts(tmp_path, hours=73)
        (artifact_dir / "run_intent.txt").write_text("validation\n", encoding="utf-8")
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "NOT_APPLICABLE"

    def test_lr030_intent_returns_not_applicable(self, tmp_path: Path) -> None:
        """run_intent.txt = lr030 -> NOT_APPLICABLE for LR-040 gate eval."""
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "NOT_APPLICABLE"
        assert result["run_intent"] == "lr030"
        assert result["checks"] == {}
        assert result["failures"] == []


class TestLR040SoakGateEdgeCases:
    def test_exactly_72h_passes(self, tmp_path: Path) -> None:
        result = evaluate_lr040_soak(_write_passing_artifacts(tmp_path, hours=73))
        # 73 entries = 72h span (entry 0 to entry 72)
        assert result["verdict"] == "PASS"

    def test_single_snapshot_fails_closed(self, tmp_path: Path) -> None:
        artifact_dir = _write_passing_artifacts(tmp_path)
        (artifact_dir / "resources_snapshot_72h.txt").unlink()
        result = evaluate_lr040_soak(artifact_dir)
        assert result["verdict"] == "FAIL"
        assert "resource_snapshots_present" in result["failures"]
