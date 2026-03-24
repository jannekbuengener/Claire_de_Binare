#!/usr/bin/env python3
"""Evaluate 72h soak test artifacts against LR-040 pass criteria (Issue #786).

Input: artifact directory produced by soak_monitor.sh
Output: lr040_soak_gate_eval.json with verdict PASS / FAIL / INCONCLUSIVE

Pass criteria (from Issue #786):
  - 72h without restart/crash
  - Memory usage stable (<10% growth)
  - CPU usage <70% avg
  - No critical errors in logs (no FAILED marker, no restart alerts)

INCONCLUSIVE verdict (Issue #1270):
  - soak_test_INCONCLUSIVE.txt present: environment interruption was detected
    (Docker-daemon or host restart) — run is invalid but not a SUT defect.
    Run must be restarted. exit 1 (fail-closed, same as FAIL).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REQUIRED_DURATION_HOURS = 72
MAX_MEMORY_GROWTH_PERCENT = 10.0
MAX_CPU_AVG_PERCENT = 70.0


def _parse_hourly_timestamps(hourly_log: Path) -> list[datetime]:
    """Extract UTC timestamps from hourly_checks.log lines."""
    timestamps: list[datetime] = []
    if not hourly_log.is_file():
        return timestamps
    for line in hourly_log.read_text(encoding="utf-8").splitlines():
        # Format: "2026-03-08 14:00:00 UTC - Hour 14: No restarts"
        match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC", line.strip())
        if match:
            timestamps.append(
                datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            )
    return timestamps


def _detect_restart_cause(restart_alerts: Path) -> str | None:
    """Read restart cause class from restart_alerts.log annotations.

    Returns None when no restarts occurred (file absent or empty).
    Falls back to 'sut_restart' when no cause annotation is present
    (legacy artifacts written before Issue #1270 — fail-closed).
    """
    if not restart_alerts.is_file():
        return None
    content = restart_alerts.read_text(encoding="utf-8")
    if not content.strip():
        return None
    if "ENVIRONMENT_INTERRUPTION" in content:
        return "environment_interruption"
    return "sut_restart"


def _parse_resource_snapshots(artifact_dir: Path) -> list[dict]:
    """Parse resource snapshot files produced by soak_monitor.sh.

    Expected format (docker stats --no-stream table output):
      NAME           CPU %   MEM USAGE / LIMIT   MEM %   NET I/O   BLOCK I/O
      cdb_redis      0.15%   24.5MiB / 256MiB    9.57%   ...       ...
    """
    snapshots = sorted(artifact_dir.glob("resources_snapshot_*.txt"))
    results: list[dict] = []
    for snap_path in snapshots:
        lines = snap_path.read_text(encoding="utf-8").splitlines()
        entries: list[dict] = []
        for line in lines:
            # Skip header / timestamp / separator lines
            match = re.match(
                r"(\S+)\s+([\d.]+)%\s+\S+\s*/\s*\S+\s+([\d.]+)%", line.strip()
            )
            if match and not line.strip().startswith("NAME"):
                entries.append(
                    {
                        "name": match.group(1),
                        "cpu_pct": float(match.group(2)),
                        "mem_pct": float(match.group(3)),
                    }
                )
        if entries:
            results.append({"file": snap_path.name, "services": entries})
    return results


def evaluate_lr040_soak(artifact_dir: Path) -> dict:
    """Evaluate soak artifacts against LR-040 criteria. Fail-closed."""
    hourly_log = artifact_dir / "hourly_checks.log"
    failed_marker = artifact_dir / "soak_test_FAILED.txt"
    restart_alerts = artifact_dir / "restart_alerts.log"

    # --- Duration check ---
    timestamps = _parse_hourly_timestamps(hourly_log)
    if len(timestamps) >= 2:
        duration = timestamps[-1] - timestamps[0]
        duration_hours = duration.total_seconds() / 3600
    else:
        duration = timedelta(0)
        duration_hours = 0.0

    # --- Restart / failure / inconclusive checks ---
    has_failed_marker = failed_marker.is_file()
    inconclusive_marker = artifact_dir / "soak_test_INCONCLUSIVE.txt"
    has_inconclusive_marker = inconclusive_marker.is_file()
    has_restart_alerts = (
        restart_alerts.is_file()
        and len(restart_alerts.read_text(encoding="utf-8").strip()) > 0
    )
    restart_cause = _detect_restart_cause(restart_alerts)

    # --- Resource analysis ---
    snapshots = _parse_resource_snapshots(artifact_dir)

    # Memory growth: compare first and last snapshot per service
    mem_growth_ok = True
    max_mem_growth: float | None = None
    cpu_avg_ok = True
    overall_cpu_avg: float | None = None

    if len(snapshots) >= 2:
        first_snap = {s["name"]: s["mem_pct"] for s in snapshots[0]["services"]}
        last_snap = {s["name"]: s["mem_pct"] for s in snapshots[-1]["services"]}

        growths: list[float] = []
        for name, first_mem in first_snap.items():
            if name in last_snap and first_mem > 0:
                growth = last_snap[name] - first_mem
                growths.append(growth)

        if growths:
            max_mem_growth = max(growths)
            mem_growth_ok = max_mem_growth < MAX_MEMORY_GROWTH_PERCENT

        # CPU average across all snapshots
        all_cpu: list[float] = []
        for snap in snapshots:
            for svc in snap["services"]:
                all_cpu.append(svc["cpu_pct"])
        if all_cpu:
            overall_cpu_avg = sum(all_cpu) / len(all_cpu)
            cpu_avg_ok = overall_cpu_avg < MAX_CPU_AVG_PERCENT
    else:
        # No snapshots = fail closed
        mem_growth_ok = False
        cpu_avg_ok = False

    # --- Build checks ---
    # NOTE: no_inconclusive_marker is intentionally NOT in this dict.
    # INCONCLUSIVE is a distinct verdict class, not a generic failed check.
    # not_both_markers captures the error case where soak_monitor.sh left
    # both markers behind (scripting bug) — that is a real failure signal.
    checks = {
        "hourly_log_present": hourly_log.is_file(),
        "duration_gte_72h": duration_hours >= REQUIRED_DURATION_HOURS,
        "no_failed_marker": not has_failed_marker,
        "not_both_markers": not (has_failed_marker and has_inconclusive_marker),
        "no_restart_alerts": not has_restart_alerts,
        "memory_growth_below_10pct": mem_growth_ok,
        "cpu_avg_below_70pct": cpu_avg_ok,
        "resource_snapshots_present": len(snapshots) >= 2,
    }

    failures = [name for name, passed in checks.items() if not passed]

    # Verdict logic (Issue #1270):
    # - Both markers simultaneously = scripting error → FAIL (fail-closed).
    #   Expose via restart_cause="conflicting_markers" for forensic review.
    # - INCONCLUSIVE: environment interruption was detected; run is invalid
    #   but not a SUT defect. Independent of the failures list.
    # - FAIL / PASS: normal path via checks dict.
    # Exit codes: 0 = PASS only; 1 = FAIL or INCONCLUSIVE (fail-closed).
    if has_failed_marker and has_inconclusive_marker:
        verdict = "FAIL"
        restart_cause = "conflicting_markers"
    elif has_inconclusive_marker:
        verdict = "INCONCLUSIVE"
    elif failures:
        verdict = "FAIL"
    else:
        verdict = "PASS"

    return {
        "schema_version": "1.1",
        "control": "LR-040",
        "issue": "#786",
        "verdict": verdict,
        "checks": checks,
        "failures": failures,
        "metrics": {
            "duration_hours": round(duration_hours, 2),
            "hourly_entries": len(timestamps),
            "max_memory_growth_pct": (
                round(max_mem_growth, 2) if max_mem_growth is not None else None
            ),
            "overall_cpu_avg_pct": (
                round(overall_cpu_avg, 2) if overall_cpu_avg is not None else None
            ),
            "resource_snapshot_count": len(snapshots),
        },
        "artifacts": {
            "hourly_log": hourly_log.name if hourly_log.is_file() else None,
            "failed_marker": failed_marker.name if has_failed_marker else None,
            "inconclusive_marker": inconclusive_marker.name if has_inconclusive_marker else None,
            "restart_cause": restart_cause,
            "restart_alerts": restart_alerts.name if has_restart_alerts else None,
            "resource_snapshots": [s["file"] for s in snapshots],
        },
    }


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <soak-artifact-directory>", file=sys.stderr)
        sys.exit(2)

    artifact_dir = Path(sys.argv[1])
    if not artifact_dir.is_dir():
        print(f"ERROR: not a directory: {artifact_dir}", file=sys.stderr)
        sys.exit(1)

    result = evaluate_lr040_soak(artifact_dir)
    output_path = artifact_dir / "lr040_soak_gate_eval.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"LR-040 soak gate evaluation written to {output_path}")
    sys.exit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
