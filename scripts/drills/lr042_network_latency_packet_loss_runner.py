"""Deterministic LR-042 chaos drill for network latency and packet loss."""

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
DEFAULT_OUTPUT_DIR = Path("reports/drills/lr042")
DEFAULT_SCENARIOS = ("latency_only", "packet_loss_only")

DRILL_ID = "LR-042"
RUNNER_VERSION = "1.0"
RECOVERY_PASS_SECONDS = 30.0
RECOVERY_FAIL_SECONDS = 60.0
QUEUE_WARN_DELTA = 250
QUEUE_FAIL_DELTA = 1000

DEFAULT_TARGET_CONTAINER = "cdb_risk"
DEFAULT_TARGET_INTERFACE = "eth0"
DEFAULT_COMPARISON_WINDOW = "10m"

REQUIRED_CONTAINERS = [
    "cdb_redis",
    "cdb_postgres",
    "cdb_risk",
    "cdb_execution",
    "cdb_db_writer",
]

HARD_COMPARISON_FAIL_IDS = {"runtime_mode_shadow", "zero_real_execution"}


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    delay_ms: int
    loss_pct: float
    note: str


def _scenario_catalog() -> dict[str, ScenarioConfig]:
    return {
        "latency_only": ScenarioConfig(
            name="latency_only",
            delay_ms=250,
            loss_pct=0.0,
            note="netem delay 250ms",
        ),
        "packet_loss_only": ScenarioConfig(
            name="packet_loss_only",
            delay_ms=0,
            loss_pct=10.0,
            note="netem loss 10%",
        ),
        "optional_combined": ScenarioConfig(
            name="optional_combined",
            delay_ms=200,
            loss_pct=5.0,
            note="netem delay 200ms + loss 5%",
        ),
    }


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


def _container_restart_count(container: str) -> int:
    raw = _docker_inspect(container, "{{.RestartCount}}")
    if not raw:
        return -1
    try:
        return int(raw)
    except ValueError:
        return -1


def _exec_in_container(
    container: str,
    command: str,
    *,
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    return _run_cmd(
        ["docker", "exec", "-u", "0", container, "sh", "-lc", command],
        timeout=timeout,
    )


def _tc_show(container: str, interface: str) -> str:
    result = _exec_in_container(container, f"tc qdisc show dev {interface}", timeout=15)
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _netem_active(container: str, interface: str) -> bool:
    return "netem" in _tc_show(container, interface).lower()


def _clear_netem(container: str, interface: str) -> subprocess.CompletedProcess[str]:
    return _exec_in_container(
        container, f"tc qdisc del dev {interface} root", timeout=15
    )


def _apply_netem(
    container: str,
    interface: str,
    *,
    delay_ms: int,
    loss_pct: float,
) -> subprocess.CompletedProcess[str]:
    parts: list[str] = []
    if delay_ms > 0:
        parts.extend(["delay", f"{delay_ms}ms"])
    if loss_pct > 0:
        parts.extend(["loss", f"{loss_pct}%"])
    if not parts:
        raise ValueError("netem configuration requires delay_ms>0 or loss_pct>0")
    return _exec_in_container(
        container, f"tc qdisc replace dev {interface} root netem {' '.join(parts)}"
    )


def _check_netem_support(container: str, interface: str) -> tuple[bool, str]:
    if (
        _exec_in_container(
            container, "command -v tc >/dev/null 2>&1", timeout=10
        ).returncode
        != 0
    ):
        return False, "tc binary not found in target container"

    show_result = _exec_in_container(
        container, f"tc qdisc show dev {interface}", timeout=10
    )
    if show_result.returncode != 0:
        return False, (
            f"tc qdisc show failed for {interface}: "
            f"{(show_result.stderr or '').strip()}"
        )

    trial_apply = _apply_netem(container, interface, delay_ms=1, loss_pct=0.0)
    if trial_apply.returncode != 0:
        return False, (
            "netem apply test failed: "
            f"{(trial_apply.stderr or trial_apply.stdout or '').strip()}"
        )
    _clear_netem(container, interface)
    return True, "supported"


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


def _normalize_runtime_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "").strip().lower()
    if mode == "staged":
        mode = "shadow"
    if mode == "mock":
        mode = "shadow"
    if mode in {"shadow", "paper", "replay", "live"}:
        return mode
    return "unresolved"


def _collect_snapshot() -> dict[str, Any]:
    runtime_mode = "unresolved"
    runtime_mode_source = "unresolved"
    try:
        status_payload = _http_get_json("http://localhost:8003/status")
        raw_mode = status_payload.get("runtime_mode")
        runtime_mode_source = "runtime_mode"
        if raw_mode in (None, ""):
            raw_mode = status_payload.get("mode")
            runtime_mode_source = "mode"
        runtime_mode = _normalize_runtime_mode(raw_mode)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        runtime_mode = "unresolved"
        runtime_mode_source = "unresolved"

    execution_metrics: dict[str, float] = {}
    risk_metrics: dict[str, float] = {}
    try:
        execution_metrics = _parse_prometheus_text(
            _http_get_text("http://localhost:8003/metrics")
        )
    except (urllib.error.URLError, TimeoutError):
        execution_metrics = {}
    try:
        risk_metrics = _parse_prometheus_text(
            _http_get_text("http://localhost:8002/metrics")
        )
    except (urllib.error.URLError, TimeoutError):
        risk_metrics = {}

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
            "execution_orders_shadow_blocked_total": _metric_or_zero(
                execution_metrics, "execution_orders_shadow_blocked_total"
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
            "order_results_received_total": _metric_or_zero(
                risk_metrics, "order_results_received_total"
            ),
            "orders_rejected_execution_total": _metric_or_zero(
                risk_metrics, "orders_rejected_execution_total"
            ),
        },
        "queue_length_stream_orders": _queue_length(),
        "service_state": {
            "cdb_risk": {
                "running": _container_running("cdb_risk"),
                "restart_count": _container_restart_count("cdb_risk"),
            },
            "cdb_execution": {
                "running": _container_running("cdb_execution"),
                "restart_count": _container_restart_count("cdb_execution"),
            },
            "cdb_db_writer": {
                "running": _container_running("cdb_db_writer"),
                "restart_count": _container_restart_count("cdb_db_writer"),
            },
            "cdb_redis": {
                "running": _container_running("cdb_redis"),
                "restart_count": _container_restart_count("cdb_redis"),
            },
            "cdb_postgres": {
                "running": _container_running("cdb_postgres"),
                "restart_count": _container_restart_count("cdb_postgres"),
            },
        },
    }


def _probe_http(url: str, timeout: float = 3.0) -> tuple[bool, Optional[float], str]:
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            _ = response.read(64)
        elapsed_ms = (time.monotonic() - started) * 1000.0
        return True, elapsed_ms, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def _probe_window(
    *,
    risk_url: str,
    exec_url: str,
    attempts: int = 4,
    interval_seconds: float = 0.8,
) -> dict[str, Any]:
    risk_success = 0
    exec_success = 0
    risk_latencies: list[float] = []
    exec_latencies: list[float] = []
    risk_errors: list[str] = []
    exec_errors: list[str] = []

    for _ in range(max(1, attempts)):
        ok_risk, latency_risk, error_risk = _probe_http(risk_url, timeout=3.0)
        ok_exec, latency_exec, error_exec = _probe_http(exec_url, timeout=3.0)

        if ok_risk and latency_risk is not None:
            risk_success += 1
            risk_latencies.append(latency_risk)
        elif error_risk:
            risk_errors.append(error_risk)

        if ok_exec and latency_exec is not None:
            exec_success += 1
            exec_latencies.append(latency_exec)
        elif error_exec:
            exec_errors.append(error_exec)

        time.sleep(max(0.0, interval_seconds))

    return {
        "attempts": attempts,
        "risk_success_count": risk_success,
        "risk_success_rate": risk_success / max(1, attempts),
        "risk_avg_latency_ms": (
            sum(risk_latencies) / len(risk_latencies) if risk_latencies else None
        ),
        "risk_errors": risk_errors[:3],
        "execution_success_count": exec_success,
        "execution_success_rate": exec_success / max(1, attempts),
        "execution_avg_latency_ms": (
            sum(exec_latencies) / len(exec_latencies) if exec_latencies else None
        ),
        "execution_errors": exec_errors[:3],
    }


def _classify_recovery(seconds: float) -> str:
    if seconds < 0:
        return "FAIL"
    if seconds <= RECOVERY_PASS_SECONDS:
        return "PASS"
    if seconds <= RECOVERY_FAIL_SECONDS:
        return "WARN"
    return "FAIL"


def _wait_for_recovery(
    *,
    timeout_seconds: int,
    target_container: str,
    target_interface: str,
) -> float:
    start = time.monotonic()
    while time.monotonic() - start < timeout_seconds:
        netem_is_cleared = not _netem_active(target_container, target_interface)
        risk_ok, _, _ = _probe_http("http://localhost:8002/status", timeout=3.0)
        exec_ok, _, _ = _probe_http("http://localhost:8003/status", timeout=3.0)
        if netem_is_cleared and risk_ok and exec_ok:
            return time.monotonic() - start
        time.sleep(1)
    return -1.0


def _run_shadow_comparison(
    *,
    output_dir: Path,
    scenario_name: str,
    window: str,
    runtime_mode: str,
) -> dict[str, Any]:
    comparison_json = output_dir / f"lr042_{scenario_name}_shadow_comparison.json"
    comparison_md = output_dir / f"lr042_{scenario_name}_shadow_comparison.md"
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cmd = [
        sys.executable,
        str(REPO_ROOT / "infrastructure/scripts/generate_shadow_digest.py"),
        "--date",
        date_tag,
        "--comparison-only",
        "--window",
        window,
        "--runtime-mode",
        runtime_mode,
        "--comparison-json",
        str(comparison_json),
        "--comparison-md",
        str(comparison_md),
    ]
    result = _run_cmd(cmd, timeout=90)
    payload: dict[str, Any] | None = None
    if result.returncode == 0 and comparison_json.exists():
        try:
            payload = json.loads(comparison_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None

    if not payload:
        return {
            "status": "WARN",
            "reason": "comparison_unavailable",
            "summary": {"overall": "UNKNOWN", "warn_count": 0, "fail_count": 0},
            "failing_checks": [],
            "artifacts": {
                "comparison_json_path": str(comparison_json),
                "comparison_md_path": str(comparison_md),
            },
            "command_rc": result.returncode,
        }

    summary = payload.get("summary", {}) or {}
    overall = str(summary.get("overall", "UNKNOWN")).upper()
    failing_checks = [
        str(check.get("id"))
        for check in payload.get("checks", [])
        if str(check.get("status", "")).upper() == "FAIL"
    ]

    if overall == "FAIL":
        if any(check_id in HARD_COMPARISON_FAIL_IDS for check_id in failing_checks):
            status = "FAIL"
            reason = "hard_shadow_invariant_failed"
        else:
            status = "WARN"
            reason = "comparison_fail_during_chaos_window_treated_as_warn"
    elif overall == "WARN":
        status = "WARN"
        reason = "comparison_warn"
    else:
        status = "PASS"
        reason = "comparison_pass"

    return {
        "status": status,
        "reason": reason,
        "summary": summary,
        "failing_checks": failing_checks,
        "artifacts": {
            "comparison_json_path": str(comparison_json),
            "comparison_md_path": str(comparison_md),
        },
        "command_rc": result.returncode,
    }


def _run_scenario(
    config: ScenarioConfig,
    *,
    baseline: dict[str, Any],
    target_container: str,
    target_interface: str,
    fault_duration_seconds: int,
    recovery_timeout: int,
    stability_seconds: int,
    comparison_window: str,
    output_dir: Path,
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    restarts_before = {
        "cdb_risk": baseline["service_state"]["cdb_risk"]["restart_count"],
        "cdb_execution": baseline["service_state"]["cdb_execution"]["restart_count"],
        "cdb_db_writer": baseline["service_state"]["cdb_db_writer"]["restart_count"],
    }
    baseline_filled = baseline["metrics"]["execution_orders_filled_total"]
    baseline_queue = baseline["queue_length_stream_orders"]
    baseline_decisions = (
        baseline["metrics"]["orders_approved_total"]
        + baseline["metrics"]["orders_blocked_total"]
    )
    baseline_signals = baseline["metrics"]["signals_received_total"]
    baseline_probe = _probe_window(
        risk_url="http://localhost:8002/status",
        exec_url="http://localhost:8003/status",
        attempts=2,
        interval_seconds=0.5,
    )

    _clear_netem(target_container, target_interface)
    apply_result = _apply_netem(
        target_container,
        target_interface,
        delay_ms=config.delay_ms,
        loss_pct=config.loss_pct,
    )
    netem_applied = apply_result.returncode == 0 and _netem_active(
        target_container, target_interface
    )
    qdisc_after_apply = _tc_show(target_container, target_interface)

    timeline.append(
        {
            "step": "t1",
            "scenario": config.name,
            "event": "fault_injected",
            "timestamp_utc": _utc_now(),
            "config": {
                "delay_ms": config.delay_ms,
                "loss_pct": config.loss_pct,
                "target_container": target_container,
                "target_interface": target_interface,
            },
            "netem_applied": netem_applied,
            "qdisc_after_apply": qdisc_after_apply,
        }
    )

    time.sleep(max(0, fault_duration_seconds))
    during_snapshot = _collect_snapshot()
    during_probe = _probe_window(
        risk_url="http://localhost:8002/status",
        exec_url="http://localhost:8003/status",
    )

    latency_delta = None
    if (
        during_probe["risk_avg_latency_ms"] is not None
        and baseline_probe["risk_avg_latency_ms"] is not None
    ):
        latency_delta = (
            during_probe["risk_avg_latency_ms"] - baseline_probe["risk_avg_latency_ms"]
        )

    degradation_observed = False
    if config.delay_ms > 0 and latency_delta is not None:
        degradation_observed = latency_delta >= max(30.0, config.delay_ms * 0.2)
    if config.loss_pct > 0 and during_probe["risk_success_rate"] < 1.0:
        degradation_observed = True
    if during_probe["execution_success_rate"] < 1.0:
        degradation_observed = True

    runtime_mode_during = during_snapshot["runtime_mode"]
    filled_during = during_snapshot["metrics"]["execution_orders_filled_total"]
    restart_deltas_during = {
        service: during_snapshot["service_state"][service]["restart_count"] - before
        for service, before in restarts_before.items()
    }

    fail_safe_checks = {
        "netem_applied": netem_applied,
        "runtime_mode_shadow": runtime_mode_during == "shadow",
        "zero_execution_preserved_during_fault": (
            filled_during == baseline_filled and filled_during == 0.0
        ),
        "no_restart_spike": all(delta <= 1 for delta in restart_deltas_during.values()),
    }
    fail_safe_pass = all(fail_safe_checks.values())

    timeline.append(
        {
            "step": "t2",
            "scenario": config.name,
            "event": "degraded_behavior_observed",
            "timestamp_utc": _utc_now(),
            "degradation_observed": degradation_observed,
            "latency_delta_ms": latency_delta,
            "during_probe": during_probe,
            "fail_safe_checks": fail_safe_checks,
            "fail_safe_pass": fail_safe_pass,
        }
    )

    timeline.append(
        {
            "step": "t3",
            "scenario": config.name,
            "event": "recovery_initiated",
            "timestamp_utc": _utc_now(),
        }
    )

    _clear_netem(target_container, target_interface)
    recovery_seconds = _wait_for_recovery(
        timeout_seconds=recovery_timeout,
        target_container=target_container,
        target_interface=target_interface,
    )
    recovery_class = _classify_recovery(recovery_seconds)

    timeline.append(
        {
            "step": "t4",
            "scenario": config.name,
            "event": "recovery_verified",
            "timestamp_utc": _utc_now(),
            "recovery_seconds": recovery_seconds,
            "recovery_class": recovery_class,
            "qdisc_after_recovery": _tc_show(target_container, target_interface),
        }
    )

    time.sleep(max(0, stability_seconds))
    after_snapshot = _collect_snapshot()
    after_probe = _probe_window(
        risk_url="http://localhost:8002/status",
        exec_url="http://localhost:8003/status",
    )

    queue_after = after_snapshot["queue_length_stream_orders"]
    queue_delta = (
        queue_after - baseline_queue if baseline_queue >= 0 and queue_after >= 0 else -1
    )
    queue_class = "PASS"
    if queue_delta > QUEUE_FAIL_DELTA:
        queue_class = "FAIL"
    elif queue_delta > QUEUE_WARN_DELTA:
        queue_class = "WARN"

    decisions_after = (
        after_snapshot["metrics"]["orders_approved_total"]
        + after_snapshot["metrics"]["orders_blocked_total"]
    )
    decisions_delta = decisions_after - baseline_decisions
    signals_after = after_snapshot["metrics"]["signals_received_total"]
    signals_delta = signals_after - baseline_signals
    stall_detected = signals_delta > 0 and decisions_delta <= 0

    filled_after = after_snapshot["metrics"]["execution_orders_filled_total"]
    filled_delta = filled_after - baseline_filled
    runtime_mode_after = after_snapshot["runtime_mode"]

    restart_deltas_after = {
        service: after_snapshot["service_state"][service]["restart_count"] - before
        for service, before in restarts_before.items()
    }

    comparison = _run_shadow_comparison(
        output_dir=output_dir,
        scenario_name=config.name,
        window=comparison_window,
        runtime_mode=runtime_mode_after,
    )

    status = "PASS"
    reasons: list[str] = []
    if not fail_safe_pass:
        status = "FAIL"
        reasons.append("fail_safe_checks_failed")
    if recovery_class == "FAIL":
        status = "FAIL"
        reasons.append("recovery_timeout_exceeded")
    elif recovery_class == "WARN" and status != "FAIL":
        status = "WARN"
        reasons.append("slow_recovery_warn")
    if runtime_mode_after != "shadow":
        status = "FAIL"
        reasons.append("runtime_mode_not_shadow_after_recovery")
    if filled_delta != 0.0:
        status = "FAIL"
        reasons.append("lr030_zero_execution_breach")
    if stall_detected:
        status = "FAIL"
        reasons.append("pipeline_stall_after_recovery")
    if queue_class == "FAIL":
        status = "FAIL"
        reasons.append("queue_backlog_fail")
    elif queue_class == "WARN" and status != "FAIL":
        status = "WARN"
        reasons.append("queue_backlog_warn")
    if comparison["status"] == "FAIL":
        status = "FAIL"
        reasons.append("lr031_hard_comparison_fail")
    elif comparison["status"] == "WARN" and status != "FAIL":
        status = "WARN"
        reasons.append("lr031_comparison_warn")
    if not degradation_observed and status == "PASS":
        status = "WARN"
        reasons.append("degradation_not_observed_warn")

    timeline.append(
        {
            "step": "t5",
            "scenario": config.name,
            "event": "post_recovery_stabilization",
            "timestamp_utc": _utc_now(),
            "queue_delta": queue_delta,
            "queue_class": queue_class,
            "signals_delta": signals_delta,
            "decisions_delta": decisions_delta,
            "stall_detected": stall_detected,
            "filled_delta": filled_delta,
            "runtime_mode_after": runtime_mode_after,
            "restart_deltas": restart_deltas_after,
            "comparison": comparison,
            "status": status,
            "reasons": reasons,
        }
    )

    return {
        "name": config.name,
        "status": status,
        "reasons": reasons,
        "config": {
            "delay_ms": config.delay_ms,
            "loss_pct": config.loss_pct,
        },
        "degradation_observed": degradation_observed,
        "latency_delta_ms": latency_delta,
        "recovery_seconds": recovery_seconds,
        "recovery_class": recovery_class,
        "fail_safe_checks": fail_safe_checks,
        "runtime_mode_after": runtime_mode_after,
        "filled_delta": filled_delta,
        "queue_delta": queue_delta,
        "queue_class": queue_class,
        "signals_delta": signals_delta,
        "decisions_delta": decisions_delta,
        "stall_detected": stall_detected,
        "restart_deltas": restart_deltas_after,
        "probe": {
            "baseline": baseline_probe,
            "during": during_probe,
            "after": after_probe,
        },
        "comparison": comparison,
    }


def _render_verdict_markdown(summary: dict[str, Any]) -> str:
    overall = summary.get("summary", {}).get("overall", "UNKNOWN")
    lines = [
        f"# LR-042 Chaos Verdict - {summary.get('evaluated_at_utc', 'unknown')}",
        "",
        f"- drill_id: `{summary.get('drill_id', DRILL_ID)}`",
        f"- runner_version: `{summary.get('runner_version', RUNNER_VERSION)}`",
        f"- overall: `{overall}`",
        f"- injection_method: `{summary.get('injection_method', 'tc_netem')}`",
        f"- target: `{summary.get('target_container', '')}:{summary.get('target_interface', '')}`",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Status | Recovery | Recovery Class | Filled Delta | Queue Delta |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in summary.get("scenarios", []):
        lines.append(
            f"| {scenario['name']} | {scenario['status']} | {scenario['recovery_seconds']:.3f} | "
            f"{scenario['recovery_class']} | {scenario['filled_delta']:.3f} | {scenario['queue_delta']} |"
        )

    lines.extend(
        [
            "",
            "## Global Checks",
            "",
            f"- shadow_runtime_required: `{summary.get('checks', {}).get('shadow_runtime_required', False)}`",
            f"- zero_execution_preserved: `{summary.get('checks', {}).get('zero_execution_preserved', False)}`",
            f"- no_uncontrolled_restarts: `{summary.get('checks', {}).get('no_uncontrolled_restarts', False)}`",
            f"- queue_stall_check: `{summary.get('checks', {}).get('queue_stall_check', False)}`",
            "",
            "## Artifacts",
            "",
            f"- timeline: `{summary.get('artifacts', {}).get('timeline_path', '')}`",
            f"- summary: `{summary.get('artifacts', {}).get('summary_path', '')}`",
            f"- verdict: `{summary.get('artifacts', {}).get('verdict_path', '')}`",
            "",
        ]
    )
    return "\n".join(lines)


def _build_unsupported_result(
    *,
    output_path: Path,
    baseline: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    timeline_path = output_path / "lr042_timeline.json"
    summary_path = output_path / "lr042_summary.json"
    verdict_path = output_path / "lr042_verdict.md"

    timeline = [
        {
            "step": "t0",
            "event": "baseline_snapshot",
            "timestamp_utc": _utc_now(),
            "baseline": baseline,
        },
        {
            "step": "t6",
            "event": "evidence_written",
            "timestamp_utc": _utc_now(),
            "unsupported_reason": reason,
        },
    ]

    summary = {
        "drill_id": DRILL_ID,
        "runner_version": RUNNER_VERSION,
        "evaluated_at_utc": _utc_now(),
        "deterministic_runner": True,
        "injection_method": "tc_netem",
        "target_container": DEFAULT_TARGET_CONTAINER,
        "target_interface": DEFAULT_TARGET_INTERFACE,
        "baseline": baseline,
        "scenarios": [],
        "checks": {
            "shadow_runtime_required": baseline.get("runtime_mode") == "shadow",
            "zero_execution_preserved": baseline.get("metrics", {}).get(
                "execution_orders_filled_total", 1.0
            )
            == 0.0,
            "no_uncontrolled_restarts": True,
            "queue_stall_check": True,
        },
        "summary": {
            "overall": "UNSUPPORTED",
            "scenario_pass_count": 0,
            "scenario_warn_count": 0,
            "scenario_fail_count": 0,
        },
        "unsupported_reason": reason,
        "artifacts": {
            "timeline_path": str(timeline_path),
            "summary_path": str(summary_path),
            "verdict_path": str(verdict_path),
        },
    }

    summary["hashes"] = {
        "timeline_sha256": _sha256_hex(_canonical_json(timeline)),
        "summary_sha256": _sha256_hex(_canonical_json(summary)),
    }

    _write_json(timeline_path, timeline)
    _write_json(summary_path, summary)
    _write_text(
        verdict_path,
        (
            f"# LR-042 Chaos Verdict - {summary['evaluated_at_utc']}\n\n"
            f"- overall: `UNSUPPORTED`\n"
            f"- reason: `{reason}`\n"
        ),
    )
    return summary


def run_lr042_drill(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    fault_duration_seconds: int = 8,
    recovery_timeout: int = 60,
    stability_seconds: int = 10,
    target_container: str = DEFAULT_TARGET_CONTAINER,
    target_interface: str = DEFAULT_TARGET_INTERFACE,
    comparison_window: str = DEFAULT_COMPARISON_WINDOW,
) -> dict[str, Any]:
    if not _docker_info_ok():
        raise RuntimeError("Docker daemon is not reachable (docker info failed)")

    for container in REQUIRED_CONTAINERS:
        if not _container_running(container):
            raise RuntimeError(f"Required container not running: {container}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timeline_path = output_path / "lr042_timeline.json"
    summary_path = output_path / "lr042_summary.json"
    verdict_path = output_path / "lr042_verdict.md"

    catalog = _scenario_catalog()
    unknown = [name for name in scenarios if name not in catalog]
    if unknown:
        raise ValueError(f"Unsupported scenarios: {unknown}")

    baseline = _collect_snapshot()
    if baseline["runtime_mode"] != "shadow":
        raise RuntimeError(
            f"LR-042 requires shadow runtime mode, got {baseline['runtime_mode']}"
        )
    if baseline["metrics"]["execution_orders_filled_total"] != 0.0:
        raise RuntimeError(
            "LR-030 invariant violated at baseline: execution_orders_filled_total must be 0"
        )

    netem_supported, support_reason = _check_netem_support(
        target_container, target_interface
    )
    if not netem_supported:
        return _build_unsupported_result(
            output_path=output_path,
            baseline=baseline,
            reason=support_reason,
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
    try:
        for scenario_name in scenarios:
            result = _run_scenario(
                catalog[scenario_name],
                baseline=baseline,
                target_container=target_container,
                target_interface=target_interface,
                fault_duration_seconds=fault_duration_seconds,
                recovery_timeout=recovery_timeout,
                stability_seconds=stability_seconds,
                comparison_window=comparison_window,
                output_dir=output_path,
                timeline=timeline,
            )
            scenario_results.append(result)
    finally:
        _clear_netem(target_container, target_interface)

    scenario_statuses = [row["status"] for row in scenario_results]
    overall = "PASS"
    if "FAIL" in scenario_statuses:
        overall = "FAIL"
    elif "WARN" in scenario_statuses:
        overall = "WARN"

    checks = {
        "shadow_runtime_required": all(
            row["runtime_mode_after"] == "shadow" for row in scenario_results
        ),
        "zero_execution_preserved": all(
            float(row["filled_delta"]) == 0.0 for row in scenario_results
        ),
        "no_uncontrolled_restarts": all(
            max(row["restart_deltas"].values()) <= 1 for row in scenario_results
        ),
        "queue_stall_check": all(not row["stall_detected"] for row in scenario_results),
    }
    if not all(checks.values()):
        overall = "FAIL"

    summary_payload: dict[str, Any] = {
        "drill_id": DRILL_ID,
        "runner_version": RUNNER_VERSION,
        "evaluated_at_utc": _utc_now(),
        "deterministic_runner": True,
        "injection_method": "tc_netem",
        "target_container": target_container,
        "target_interface": target_interface,
        "parameters": {
            "scenarios": list(scenarios),
            "fault_duration_seconds": fault_duration_seconds,
            "recovery_timeout": recovery_timeout,
            "stability_seconds": stability_seconds,
            "comparison_window": comparison_window,
        },
        "thresholds": {
            "recovery_pass_seconds": RECOVERY_PASS_SECONDS,
            "recovery_fail_seconds": RECOVERY_FAIL_SECONDS,
            "queue_warn_delta": QUEUE_WARN_DELTA,
            "queue_fail_delta": QUEUE_FAIL_DELTA,
        },
        "baseline": baseline,
        "scenarios": scenario_results,
        "checks": checks,
        "summary": {
            "overall": overall,
            "scenario_pass_count": sum(
                1 for row in scenario_results if row["status"] == "PASS"
            ),
            "scenario_warn_count": sum(
                1 for row in scenario_results if row["status"] == "WARN"
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
        description="Run deterministic LR-042 network latency/packet-loss chaos drill."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for lr042 artifacts",
    )
    parser.add_argument(
        "--scenarios",
        default="latency_only,packet_loss_only",
        help="Comma-separated scenarios: latency_only, packet_loss_only, optional_combined",
    )
    parser.add_argument(
        "--fault-duration-seconds",
        type=int,
        default=8,
        help="Seconds to keep netem fault active per scenario",
    )
    parser.add_argument(
        "--recovery-timeout",
        type=int,
        default=60,
        help="Maximum seconds to wait for recovery verification",
    )
    parser.add_argument(
        "--stability-seconds",
        type=int,
        default=10,
        help="Post-recovery stabilization wait in seconds",
    )
    parser.add_argument(
        "--target-container",
        default=DEFAULT_TARGET_CONTAINER,
        help="Container where netem is injected (default: cdb_risk)",
    )
    parser.add_argument(
        "--target-interface",
        default=DEFAULT_TARGET_INTERFACE,
        help="Network interface for tc/netem (default: eth0)",
    )
    parser.add_argument(
        "--comparison-window",
        default=DEFAULT_COMPARISON_WINDOW,
        help="LR-031 comparison window passed to shadow digest generator",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    scenarios = tuple(
        value.strip().lower() for value in args.scenarios.split(",") if value.strip()
    )
    summary = run_lr042_drill(
        output_dir=args.output_dir,
        scenarios=scenarios,
        fault_duration_seconds=args.fault_duration_seconds,
        recovery_timeout=args.recovery_timeout,
        stability_seconds=args.stability_seconds,
        target_container=args.target_container,
        target_interface=args.target_interface,
        comparison_window=args.comparison_window,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    overall = str(summary.get("summary", {}).get("overall", "FAIL")).upper()
    if overall == "UNSUPPORTED":
        return 3
    return 0 if overall != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
