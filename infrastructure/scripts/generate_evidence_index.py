#!/usr/bin/env python3
"""Generate a machine-readable evidence_index.json from a shadow-soak evidence directory.

Mandatory sources (missing → exit 1):
  - run_summary.json
  - endpoints/execution_metrics.txt
  - endpoints/risk_metrics.txt

Optional enrichment sources (missing → null fields, no failure):
  - endpoints/execution_status.json
  - endpoints/risk_status.json
  - endpoints/prometheus_targets.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FETCH_FAILURE_MARKER = "EVIDENCE-FETCH-FAILED"

REQUIRED_SOURCES = [
    "run_summary.json",
    "endpoints/execution_metrics.txt",
    "endpoints/risk_metrics.txt",
]

OPTIONAL_SOURCES = [
    "endpoints/execution_status.json",
    "endpoints/risk_status.json",
    "endpoints/prometheus_targets.json",
]


def parse_prometheus_metric(text: str, metric_name: str) -> float | None:
    """Extract a single metric value from Prometheus text exposition format."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] == metric_name:
            try:
                return float(parts[1])
            except ValueError:
                return None
    return None


def detect_fetch_failure(text: str) -> str | None:
    """Return the failure line if a fetch-failure marker is present."""
    for line in text.splitlines():
        if FETCH_FAILURE_MARKER in line:
            return line.strip()
    return None


def scan_fetch_failures(evidence_dir: Path) -> list[str]:
    """Scan all endpoint files for fetch-failure markers."""
    failures = []
    endpoints_dir = evidence_dir / "endpoints"
    if not endpoints_dir.is_dir():
        return failures
    for fpath in sorted(endpoints_dir.iterdir()):
        if not fpath.is_file():
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        failure = detect_fetch_failure(content)
        if failure:
            failures.append(f"{fpath.name}: {failure}")
    return failures


def load_json_optional(path: Path) -> dict | None:
    """Load a JSON file, returning None if missing, unreadable, or fetch-failed."""
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if FETCH_FAILURE_MARKER in content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def load_text_required(path: Path, source_name: str) -> str:
    """Load a text file, raising SystemExit if missing or fetch-failed."""
    if not path.is_file():
        print(f"ERROR: required source missing: {source_name}", file=sys.stderr)
        sys.exit(1)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {source_name}: {exc}", file=sys.stderr)
        sys.exit(1)
    if FETCH_FAILURE_MARKER in content:
        print(
            f"ERROR: required source has fetch failure: {source_name}", file=sys.stderr
        )
        sys.exit(1)
    return content


def build_source_integrity(evidence_dir: Path) -> dict:
    """Document which sources are present, missing, or failed."""
    integrity: dict[str, str] = {}
    for src in REQUIRED_SOURCES + OPTIONAL_SOURCES:
        fpath = evidence_dir / src
        if not fpath.is_file():
            integrity[src] = "missing"
        else:
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                integrity[src] = "unreadable"
                continue
            if FETCH_FAILURE_MARKER in content:
                integrity[src] = "fetch_failed"
            else:
                integrity[src] = "ok"
    return integrity


def generate_index(evidence_dir: Path) -> dict:
    """Generate the evidence index from the given directory."""
    # --- Required: run_summary.json ---
    run_summary_path = evidence_dir / "run_summary.json"
    if not run_summary_path.is_file():
        print("ERROR: required source missing: run_summary.json", file=sys.stderr)
        sys.exit(1)
    run_summary = load_json_optional(run_summary_path)
    if run_summary is None:
        print("ERROR: run_summary.json is unreadable or fetch-failed", file=sys.stderr)
        sys.exit(1)

    # --- Required: execution_metrics.txt ---
    exec_metrics_text = load_text_required(
        evidence_dir / "endpoints" / "execution_metrics.txt",
        "endpoints/execution_metrics.txt",
    )

    # --- Required: risk_metrics.txt ---
    risk_metrics_text = load_text_required(
        evidence_dir / "endpoints" / "risk_metrics.txt",
        "endpoints/risk_metrics.txt",
    )

    # --- Parse metrics ---
    orders_filled = parse_prometheus_metric(
        exec_metrics_text, "execution_orders_filled_total"
    )
    orders_received = parse_prometheus_metric(
        exec_metrics_text, "execution_orders_received_total"
    )
    orders_rejected = parse_prometheus_metric(
        exec_metrics_text, "execution_orders_rejected_total"
    )
    shadow_blocked_total = parse_prometheus_metric(
        exec_metrics_text, "execution_shadow_blocked_total"
    )

    signals_received = parse_prometheus_metric(
        risk_metrics_text, "signals_received_total"
    )
    orders_blocked = parse_prometheus_metric(risk_metrics_text, "orders_blocked_total")
    orders_approved = parse_prometheus_metric(
        risk_metrics_text, "orders_approved_total"
    )
    total_exposure = parse_prometheus_metric(
        risk_metrics_text, "risk_total_exposure_value"
    )

    # --- Derived safety assertions (from metrics only) ---
    has_live_data = signals_received is not None and signals_received > 0
    zero_execution = orders_filled is not None and orders_filled == 0
    zero_exposure = total_exposure is not None and total_exposure == 0.0
    risk_blocked_all = (
        orders_approved is not None
        and orders_blocked is not None
        and orders_approved == 0
        and orders_blocked > 0
    )

    # --- Optional enrichment: execution_status.json ---
    exec_status = load_json_optional(
        evidence_dir / "endpoints" / "execution_status.json"
    )
    trading_mode = None
    if exec_status is not None:
        trading_mode = exec_status.get("mode")

    # --- Optional enrichment: risk_status.json ---
    risk_status = load_json_optional(evidence_dir / "endpoints" / "risk_status.json")
    kill_switch_active = None
    if risk_status is not None:
        risk_state = risk_status.get("risk_state")
        if isinstance(risk_state, dict):
            kill_switch_active = risk_state.get("circuit_breaker")

    # --- Optional enrichment: prometheus_targets.json ---
    prom_targets = load_json_optional(
        evidence_dir / "endpoints" / "prometheus_targets.json"
    )
    prometheus_targets_up = None
    if prom_targets is not None:
        try:
            active = prom_targets.get("data", {}).get("activeTargets", [])
            prometheus_targets_up = sum(1 for t in active if t.get("health") == "up")
        except (AttributeError, TypeError):
            pass

    # --- Fetch failures ---
    fetch_failures = scan_fetch_failures(evidence_dir)

    # --- Source integrity ---
    source_integrity = build_source_integrity(evidence_dir)

    # --- Coerce metric floats to int where appropriate ---
    def to_int_or_none(v: float | None) -> int | None:
        return int(v) if v is not None else None

    return {
        "schema_version": "1.0",
        # run metadata (from run_summary.json)
        "run_id": run_summary.get("run_id"),
        "run_url": run_summary.get("run_url"),
        "commit": run_summary.get("commit"),
        "ref": run_summary.get("ref"),
        "mode": run_summary.get("mode"),
        "soak_minutes": run_summary.get("soak_minutes"),
        "gate_status": run_summary.get("gate_status"),
        "ended_at": run_summary.get("ended_at"),
        # metrics (from Prometheus text)
        "signals_received": to_int_or_none(signals_received),
        "orders_blocked": to_int_or_none(orders_blocked),
        "orders_approved": to_int_or_none(orders_approved),
        "orders_filled": to_int_or_none(orders_filled),
        "orders_received": to_int_or_none(orders_received),
        "orders_rejected": to_int_or_none(orders_rejected),
        "shadow_blocked_total": to_int_or_none(shadow_blocked_total),
        "total_exposure": total_exposure,
        # derived safety assertions
        "has_live_data": has_live_data,
        "zero_execution": zero_execution,
        "zero_exposure": zero_exposure,
        "risk_blocked_all": risk_blocked_all,
        # optional enrichment
        "trading_mode": trading_mode,
        "kill_switch_active": kill_switch_active,
        "prometheus_targets_up": prometheus_targets_up,
        # diagnostics
        "fetch_failures": fetch_failures,
        "source_integrity": source_integrity,
        "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <evidence-directory>", file=sys.stderr)
        sys.exit(2)

    evidence_dir = Path(sys.argv[1])
    if not evidence_dir.is_dir():
        print(f"ERROR: not a directory: {evidence_dir}", file=sys.stderr)
        sys.exit(1)

    index = generate_index(evidence_dir)

    output_path = evidence_dir / "evidence_index.json"
    output_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Evidence index written to {output_path}")


if __name__ == "__main__":
    main()
