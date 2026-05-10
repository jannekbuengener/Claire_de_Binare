"""Canonical repo-native 431C chaos drill for Redis and Postgres restart recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path("reports/drills/lr041")
DEFAULT_SCENARIOS = ("redis_restart", "postgres_restart")

DRILL_ID = "LR-041"
RUNNER_VERSION = "1.0"

# Issue #787 pass criteria
REDIS_RECOVERY_PASS_SECONDS = 30.0
POSTGRES_RECOVERY_PASS_SECONDS = 60.0

REQUIRED_CONTAINERS = [
    "cdb_redis",
    "cdb_postgres",
    "cdb_risk",
    "cdb_execution",
    "cdb_db_writer",
]


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    target_container: str
    recovery_pass_seconds: float
    note: str


def _scenario_catalog() -> dict[str, ScenarioConfig]:
    return {
        "redis_restart": ScenarioConfig(
            name="redis_restart",
            target_container="cdb_redis",
            recovery_pass_seconds=REDIS_RECOVERY_PASS_SECONDS,
            note="docker restart cdb_redis — services must reconnect within 30s",
        ),
        "postgres_restart": ScenarioConfig(
            name="postgres_restart",
            target_container="cdb_postgres",
            recovery_pass_seconds=POSTGRES_RECOVERY_PASS_SECONDS,
            note="docker restart cdb_postgres — services must reconnect within 60s",
        ),
    }


# ---------------------------------------------------------------------------
# Helpers (self-contained, consistent with LR-042 runner pattern)
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def _run_cmd(
    cmd: list[str],
    *,
    timeout: int = 30,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )
    return result


def _docker_info_ok() -> bool:
    return _run_cmd(["docker", "info"], timeout=20).returncode == 0


def _docker_inspect(container: str, template: str) -> str:
    result = _run_cmd(
        ["docker", "inspect", "--format", template, container],
        timeout=20,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _container_running(container: str) -> bool:
    return _docker_inspect(container, "{{.State.Status}}") == "running"


def _container_healthy(container: str) -> bool:
    """Check Docker healthcheck status. Only reliable for containers with
    an explicit healthcheck in compose (cdb_redis, cdb_postgres, cdb_db_writer).
    Containers without healthcheck (cdb_risk, cdb_execution) return empty string."""
    health = _docker_inspect(container, "{{.State.Health.Status}}")
    return health == "healthy"


def _container_restart_count(container: str) -> int:
    raw = _docker_inspect(container, "{{.RestartCount}}")
    if not raw:
        return -1
    try:
        return int(raw)
    except ValueError:
        return -1


def _http_get_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_get_text(url: str, timeout: float = 3.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _parse_prometheus_text(body: str) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        key, value = parts
        if "{" in key:
            continue
        try:
            metrics[key] = float(value)
        except ValueError:
            continue
    return metrics


def _metric_or_zero(metrics: dict[str, float], key: str) -> float:
    try:
        return float(metrics.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _probe_http(url: str, timeout: float = 3.0) -> tuple[bool, Optional[float], str]:
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            _ = response.read(64)
        elapsed_ms = (time.monotonic() - started) * 1000.0
        return True, elapsed_ms, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def _normalize_runtime_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "").strip().lower()
    if mode == "staged":
        mode = "shadow"
    if mode == "mock":
        mode = "shadow"
    if mode in {"shadow", "paper", "replay", "live"}:
        return mode
    return "unresolved"


def _queue_length(stream_name: str = "stream.orders") -> int:
    result = _run_cmd(
        [
            "docker",
            "exec",
            "cdb_redis",
            "sh",
            "-lc",
            f'redis-cli -a "$(cat /run/secrets/redis_password)" XLEN {stream_name}',
        ],
        timeout=10,
    )
    if result.returncode != 0:
        return -1
    lines = [
        line.strip() for line in (result.stdout or "").splitlines() if line.strip()
    ]
    if not lines:
        return -1
    try:
        return int(lines[-1])
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Snapshot collection
# ---------------------------------------------------------------------------


def _collect_snapshot() -> dict[str, Any]:
    def _read_runtime_mode() -> tuple[str, str]:
        try:
            status_payload = _http_get_json("http://localhost:8003/status")
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return "unresolved", "unresolved"

        raw_mode = status_payload.get("runtime_mode")
        runtime_mode_source = "runtime_mode"
        if raw_mode in (None, ""):
            raw_mode = status_payload.get("mode")
            runtime_mode_source = "mode"
        return _normalize_runtime_mode(raw_mode), runtime_mode_source

    runtime_mode, runtime_mode_source = _read_runtime_mode()

    execution_metrics: dict[str, float] = {}
    risk_metrics: dict[str, float] = {}
    try:
        execution_metrics = _parse_prometheus_text(
            _http_get_text("http://localhost:8003/metrics")
        )
    except (urllib.error.URLError, TimeoutError):
        pass
    try:
        risk_metrics = _parse_prometheus_text(
            _http_get_text("http://localhost:8002/metrics")
        )
    except (urllib.error.URLError, TimeoutError):
        pass

    return {
        "captured_at_utc": _utc_now(),
        "runtime_mode": runtime_mode,
        "runtime_mode_source": runtime_mode_source,
        "metrics": {
            "execution_orders_filled_total": _metric_or_zero(
                execution_metrics, "execution_orders_filled_total"
            ),
            "execution_orders_rejected_total": _metric_or_zero(
                execution_metrics, "execution_orders_rejected_total"
            ),
            "execution_shadow_blocked_total": _metric_or_zero(
                execution_metrics, "execution_shadow_blocked_total"
            ),
            "signals_received_total": _metric_or_zero(
                risk_metrics, "signals_received_total"
            ),
            "orders_approved_total": _metric_or_zero(
                risk_metrics, "orders_approved_total"
            ),
            "orders_blocked_total": _metric_or_zero(
                risk_metrics, "orders_blocked_total"
            ),
        },
        "queue_length_stream_orders": _queue_length(),
        "service_state": {
            container: {
                "running": _container_running(container),
                "healthy": _container_healthy(container),
                "restart_count": _container_restart_count(container),
            }
            for container in REQUIRED_CONTAINERS
        },
    }


# ---------------------------------------------------------------------------
# Recovery classification
# ---------------------------------------------------------------------------


def _classify_recovery(seconds: float, threshold: float) -> str:
    if seconds < 0:
        return "FAIL"
    if seconds <= threshold:
        return "PASS"
    return "FAIL"


def _wait_for_container_healthy(
    container: str,
    *,
    timeout_seconds: int,
) -> float:
    """Poll until container is running and healthy. Returns elapsed seconds or -1."""
    start = time.monotonic()
    while time.monotonic() - start < timeout_seconds:
        if _container_running(container) and _container_healthy(container):
            return time.monotonic() - start
        time.sleep(1)
    return -1.0


def _wait_for_service_recovery(
    *,
    timeout_seconds: int,
) -> float:
    """Poll until both risk and execution health endpoints respond. Returns elapsed seconds or -1."""
    start = time.monotonic()
    while time.monotonic() - start < timeout_seconds:
        risk_ok, _, _ = _probe_http("http://localhost:8002/status", timeout=3.0)
        exec_ok, _, _ = _probe_http("http://localhost:8003/status", timeout=3.0)
        if risk_ok and exec_ok:
            return time.monotonic() - start
        time.sleep(1)
    return -1.0


# ---------------------------------------------------------------------------
# Scenario execution
# ---------------------------------------------------------------------------


def _run_scenario(
    config: ScenarioConfig,
    *,
    baseline: dict[str, Any],
    recovery_timeout: int,
    stability_seconds: int,
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    restarts_before = {
        svc: baseline["service_state"][svc]["restart_count"]
        for svc in REQUIRED_CONTAINERS
    }
    baseline_filled = baseline["metrics"]["execution_orders_filled_total"]

    # --- t1: inject fault (docker restart) ---
    timeline.append(
        {
            "step": "t1",
            "scenario": config.name,
            "event": "fault_injected",
            "timestamp_utc": _utc_now(),
            "method": "docker_restart",
            "target_container": config.target_container,
        }
    )
    restart_start = time.monotonic()
    restart_result = _run_cmd(
        ["docker", "restart", config.target_container],
        timeout=90,
    )
    restart_ok = restart_result.returncode == 0
    restart_cmd_seconds = time.monotonic() - restart_start

    timeline.append(
        {
            "step": "t2",
            "scenario": config.name,
            "event": "restart_command_completed",
            "timestamp_utc": _utc_now(),
            "restart_ok": restart_ok,
            "restart_cmd_seconds": round(restart_cmd_seconds, 3),
            "stderr": (restart_result.stderr or "").strip()[:200],
        }
    )

    if not restart_ok:
        timeline.append(
            {
                "step": "t3",
                "scenario": config.name,
                "event": "restart_failed",
                "timestamp_utc": _utc_now(),
            }
        )
        return {
            "name": config.name,
            "status": "FAIL",
            "reasons": ["restart_command_failed"],
            "target_container": config.target_container,
            "restart_ok": False,
            "container_recovery_seconds": -1,
            "service_recovery_seconds": -1,
            "recovery_class": "FAIL",
            "filled_delta": 0.0,
            "runtime_mode_after": "unknown",
            "restart_deltas": {},
        }

    # --- t3: wait for container health ---
    container_recovery = _wait_for_container_healthy(
        config.target_container,
        timeout_seconds=recovery_timeout,
    )
    container_recovery_class = _classify_recovery(
        container_recovery, config.recovery_pass_seconds
    )

    timeline.append(
        {
            "step": "t3",
            "scenario": config.name,
            "event": "container_healthy",
            "timestamp_utc": _utc_now(),
            "container_recovery_seconds": round(container_recovery, 3),
            "container_recovery_class": container_recovery_class,
        }
    )

    # --- t4: wait for downstream service recovery ---
    service_recovery = _wait_for_service_recovery(
        timeout_seconds=recovery_timeout,
    )
    service_recovery_class = _classify_recovery(
        service_recovery, config.recovery_pass_seconds
    )

    timeline.append(
        {
            "step": "t4",
            "scenario": config.name,
            "event": "services_recovered",
            "timestamp_utc": _utc_now(),
            "service_recovery_seconds": round(service_recovery, 3),
            "service_recovery_class": service_recovery_class,
        }
    )

    # --- t5: post-recovery stabilization and verification ---
    time.sleep(max(0, stability_seconds))
    after_snapshot = _collect_snapshot()

    filled_after = after_snapshot["metrics"]["execution_orders_filled_total"]
    filled_delta = filled_after - baseline_filled
    runtime_mode_after = after_snapshot["runtime_mode"]

    restart_deltas = {
        svc: after_snapshot["service_state"][svc]["restart_count"] - before
        for svc, before in restarts_before.items()
    }

    # Note: docker restart does NOT increment Docker's RestartCount.
    # Only policy-triggered restarts (restart: unless-stopped) do.
    # Therefore restart_ok=True from the command is sufficient proof.
    # Dependent services may restart via Docker restart policy — this is
    # expected behavior, not a failure.
    collateral_restarts = {
        svc: delta
        for svc, delta in restart_deltas.items()
        if svc != config.target_container and delta > 0
    }

    reasons: list[str] = []

    if container_recovery < 0:
        reasons.append("container_did_not_recover")
    elif container_recovery_class == "FAIL":
        reasons.append("container_recovery_too_slow")

    if service_recovery < 0:
        reasons.append("services_did_not_recover")
    elif service_recovery_class == "FAIL":
        reasons.append("service_recovery_too_slow")

    if runtime_mode_after != "shadow":
        reasons.append("runtime_mode_not_shadow_after_recovery")

    if filled_delta != 0.0:
        reasons.append("lr030_zero_execution_breach")

    status = "FAIL" if reasons else "PASS"

    timeline.append(
        {
            "step": "t5",
            "scenario": config.name,
            "event": "post_recovery_verification",
            "timestamp_utc": _utc_now(),
            "filled_delta": filled_delta,
            "runtime_mode_after": runtime_mode_after,
            "restart_deltas": restart_deltas,
            "collateral_restarts": collateral_restarts,
            "status": status,
            "reasons": reasons,
        }
    )

    return {
        "name": config.name,
        "status": status,
        "reasons": reasons,
        "target_container": config.target_container,
        "restart_ok": restart_ok,
        "container_recovery_seconds": round(container_recovery, 3),
        "service_recovery_seconds": round(service_recovery, 3),
        "recovery_class": service_recovery_class,
        "filled_delta": filled_delta,
        "runtime_mode_after": runtime_mode_after,
        "restart_deltas": restart_deltas,
    }


# ---------------------------------------------------------------------------
# Verdict rendering
# ---------------------------------------------------------------------------


def _render_verdict_markdown(summary: dict[str, Any]) -> str:
    overall = summary.get("summary", {}).get("overall", "UNKNOWN")
    lines = [
        f"# LR-041 Chaos Verdict - {summary.get('evaluated_at_utc', 'unknown')}",
        "",
        f"- drill_id: `{summary.get('drill_id', DRILL_ID)}`",
        f"- runner_version: `{summary.get('runner_version', RUNNER_VERSION)}`",
        f"- overall: `{overall}`",
        f"- injection_method: `docker_restart`",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Status | Container Recovery | Service Recovery | Filled Delta |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario in summary.get("scenarios", []):
        lines.append(
            f"| {scenario['name']} | {scenario['status']} "
            f"| {scenario['container_recovery_seconds']:.3f}s "
            f"| {scenario['service_recovery_seconds']:.3f}s "
            f"| {scenario['filled_delta']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Hard Invariants",
            "",
            f"- shadow_runtime_preserved: `{summary.get('checks', {}).get('shadow_runtime_preserved', False)}`",
            f"- zero_execution_preserved: `{summary.get('checks', {}).get('zero_execution_preserved', False)}`",
            "",
            "## Observations",
            "",
            f"- collateral_restarts: `{summary.get('observations', {}).get('collateral_restarts', {})}`",
            "",
            "## Pass Criteria (Issue #787)",
            "",
            f"- Redis Recovery <{REDIS_RECOVERY_PASS_SECONDS}s: "
            f"`{summary.get('checks', {}).get('redis_recovery_within_threshold', 'N/A')}`",
            f"- Postgres Recovery <{POSTGRES_RECOVERY_PASS_SECONDS}s: "
            f"`{summary.get('checks', {}).get('postgres_recovery_within_threshold', 'N/A')}`",
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main drill entrypoint
# ---------------------------------------------------------------------------


def run_lr041_drill(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    recovery_timeout: int = 90,
    stability_seconds: int = 10,
) -> dict[str, Any]:
    if not _docker_info_ok():
        raise RuntimeError("Docker daemon is not reachable (docker info failed)")

    for container in REQUIRED_CONTAINERS:
        if not _container_running(container):
            raise RuntimeError(f"Required container not running: {container}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timeline_path = output_path / "lr041_timeline.json"
    summary_path = output_path / "lr041_summary.json"
    verdict_path = output_path / "lr041_verdict.md"

    catalog = _scenario_catalog()
    unknown = [name for name in scenarios if name not in catalog]
    if unknown:
        raise ValueError(f"Unsupported scenarios: {unknown}")

    baseline = _collect_snapshot()
    if baseline["runtime_mode"] != "shadow":
        raise RuntimeError(
            f"LR-041 requires shadow runtime mode, got {baseline['runtime_mode']}"
        )
    if baseline["metrics"]["execution_orders_filled_total"] != 0.0:
        raise RuntimeError(
            "LR-030 invariant violated at baseline: execution_orders_filled_total must be 0"
        )

    timeline: list[dict[str, Any]] = [
        {
            "step": "t0",
            "event": "baseline_snapshot",
            "timestamp_utc": _utc_now(),
            "baseline": baseline,
        }
    ]

    scenario_results: list[dict[str, Any]] = []
    for scenario_name in scenarios:
        result = _run_scenario(
            catalog[scenario_name],
            baseline=baseline,
            recovery_timeout=recovery_timeout,
            stability_seconds=stability_seconds,
            timeline=timeline,
        )
        scenario_results.append(result)

    # Global checks (hard invariants only — collateral restarts are
    # expected with restart: unless-stopped and recorded as observation)
    checks: dict[str, Any] = {
        "shadow_runtime_preserved": all(
            row["runtime_mode_after"] == "shadow" for row in scenario_results
        ),
        "zero_execution_preserved": all(
            float(row["filled_delta"]) == 0.0 for row in scenario_results
        ),
    }

    # Observation: dependent services that restarted via Docker restart policy
    observations: dict[str, Any] = {
        "collateral_restarts": {
            row["name"]: {
                svc: delta
                for svc, delta in row["restart_deltas"].items()
                if svc != row["target_container"] and delta > 0
            }
            for row in scenario_results
        },
    }

    # Per-service recovery threshold checks
    for row in scenario_results:
        if row["name"] == "redis_restart":
            checks["redis_recovery_within_threshold"] = (
                0 <= row["service_recovery_seconds"] <= REDIS_RECOVERY_PASS_SECONDS
            )
        elif row["name"] == "postgres_restart":
            checks["postgres_recovery_within_threshold"] = (
                0 <= row["service_recovery_seconds"] <= POSTGRES_RECOVERY_PASS_SECONDS
            )

    scenario_statuses = [row["status"] for row in scenario_results]
    overall = "PASS"
    if "FAIL" in scenario_statuses:
        overall = "FAIL"
    if not all(checks.values()):
        overall = "FAIL"

    summary_payload: dict[str, Any] = {
        "drill_id": DRILL_ID,
        "runner_version": RUNNER_VERSION,
        "evaluated_at_utc": _utc_now(),
        "deterministic_runner": True,
        "injection_method": "docker_restart",
        "parameters": {
            "scenarios": list(scenarios),
            "recovery_timeout": recovery_timeout,
            "stability_seconds": stability_seconds,
        },
        "thresholds": {
            "redis_recovery_pass_seconds": REDIS_RECOVERY_PASS_SECONDS,
            "postgres_recovery_pass_seconds": POSTGRES_RECOVERY_PASS_SECONDS,
        },
        "baseline": baseline,
        "scenarios": scenario_results,
        "checks": checks,
        "observations": observations,
        "summary": {
            "overall": overall,
            "scenario_pass_count": sum(
                1 for row in scenario_results if row["status"] == "PASS"
            ),
            "scenario_fail_count": sum(
                1 for row in scenario_results if row["status"] == "FAIL"
            ),
        },
        "artifacts": {
            "timeline_path": str(timeline_path),
            "summary_path": str(summary_path),
            "verdict_path": str(verdict_path),
        },
    }

    timeline.append(
        {
            "step": "t6",
            "event": "evidence_written",
            "timestamp_utc": _utc_now(),
            "overall": overall,
            "artifacts": [str(timeline_path), str(summary_path), str(verdict_path)],
        }
    )

    summary_payload["hashes"] = {
        "timeline_sha256": _sha256_hex(_canonical_json(timeline)),
        "summary_sha256": _sha256_hex(_canonical_json(summary_payload)),
    }

    _write_json(timeline_path, timeline)
    _write_json(summary_path, summary_payload)
    _write_text(verdict_path, _render_verdict_markdown(summary_payload))
    return summary_payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic LR-041 Redis/Postgres restart chaos drill."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for lr041 artifacts",
    )
    parser.add_argument(
        "--scenarios",
        default="redis_restart,postgres_restart",
        help="Comma-separated scenarios: redis_restart, postgres_restart",
    )
    parser.add_argument(
        "--recovery-timeout",
        type=int,
        default=90,
        help="Maximum seconds to wait for recovery per scenario",
    )
    parser.add_argument(
        "--stability-seconds",
        type=int,
        default=10,
        help="Post-recovery stabilization wait in seconds",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    scenarios = tuple(
        value.strip().lower() for value in args.scenarios.split(",") if value.strip()
    )
    summary = run_lr041_drill(
        output_dir=args.output_dir,
        scenarios=scenarios,
        recovery_timeout=args.recovery_timeout,
        stability_seconds=args.stability_seconds,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    overall = str(summary.get("summary", {}).get("overall", "FAIL")).upper()
    return 0 if overall != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
