#!/usr/bin/env python3
"""Evaluate shadow-soak evidence with hard LR-030/LR-031 gate criteria.

Canonical runtime-mode is taken only from ``endpoints/execution_status.json``
field ``mode``. Shadow probe semantics and soak-profile labels are separate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_json_required(path: Path, source_name: str) -> dict:
    if not path.is_file():
        print(f"ERROR: required source missing: {source_name}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load {source_name}: {exc}", file=sys.stderr)
        sys.exit(1)


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_shadow_soak_evidence(evidence_dir: Path) -> dict:
    evidence_index_path = evidence_dir / "evidence_index.json"
    shadow_probe_path = evidence_dir / "shadow_block_probe.json"

    evidence_index = _load_json_required(evidence_index_path, "evidence_index.json")
    shadow_probe = _load_json_required(shadow_probe_path, "shadow_block_probe.json")

    exec_status = _load_json_required(
        evidence_dir / "endpoints" / "execution_status.json",
        "endpoints/execution_status.json",
    )
    risk_status = _load_json_required(
        evidence_dir / "endpoints" / "risk_status.json",
        "endpoints/risk_status.json",
    )

    shadow_blocked_total = _to_int(evidence_index.get("shadow_blocked_total"))
    orders_filled = _to_int(evidence_index.get("orders_filled"))

    order_result = shadow_probe.get("order_result") or {}
    order_result_found = bool(shadow_probe.get("order_result_found"))
    order_result_status = order_result.get("status")
    filled_quantity = _to_float(order_result.get("filled_quantity"))

    has_live_data = evidence_index.get("has_live_data")
    orders_approved = _to_int(evidence_index.get("orders_approved"))
    risk_blocked_all = evidence_index.get("risk_blocked_all")
    # Canonical runtime-mode source: execution_status.mode
    execution_runtime_mode = exec_status.get("mode")
    kill_switch_active = risk_status.get("risk_state", {}).get("circuit_breaker")

    checks = {
        "shadow_blocked_total_gte_1": shadow_blocked_total is not None
        and shadow_blocked_total >= 1,
        "execution_orders_filled_total_eq_0": orders_filled == 0,
        "auditable_reject_present": order_result_found
        and order_result_status == "REJECTED",
        "reject_filled_quantity_eq_0": filled_quantity == 0.0,
        "shadow_probe_artifact_present": shadow_probe_path.is_file(),
        "has_live_data_true": has_live_data is True,
        "orders_approved_eq_0": orders_approved is not None and orders_approved == 0,
        "risk_blocked_all_true": risk_blocked_all is True,
        "runtime_mode_verified": execution_runtime_mode == "mock",
        "kill_switch_precheck_inactive": kill_switch_active is False,
    }

    failures = [name for name, passed in checks.items() if not passed]
    verdict = "PASS" if not failures else "FAIL"

    return {
        "schema_version": "1.1",
        "verdict": verdict,
        "checks": checks,
        "failures": failures,
        "metrics": {
            "shadow_blocked_total": shadow_blocked_total,
            "orders_filled": orders_filled,
            "orders_approved": orders_approved,
            "has_live_data": has_live_data,
            "risk_blocked_all": risk_blocked_all,
        },
        "runtime": {
            "trading_mode": execution_runtime_mode,
            "kill_switch_active": kill_switch_active,
        },
        "probe": {
            "probe_order_id": shadow_probe.get("probe_order_id"),
            "publish_subscribers": shadow_probe.get("publish_subscribers"),
            "order_result_found": order_result_found,
            "order_result_source": shadow_probe.get("order_result_source"),
            "stream_order_result_found": shadow_probe.get("stream_order_result_found"),
            "order_result_status": order_result_status,
            "filled_quantity": filled_quantity,
            "error": shadow_probe.get("error"),
        },
        "artifacts": {
            "evidence_index": evidence_index_path.name,
            "shadow_block_probe": shadow_probe_path.name,
            "execution_status": "endpoints/execution_status.json",
            "risk_status": "endpoints/risk_status.json",
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate shadow-soak evidence with hard LR-030/LR-031 gate criteria."
    )
    parser.add_argument(
        "evidence_directory",
        help="Path to the evidence directory containing the required shadow-soak artifacts.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    evidence_dir = Path(args.evidence_directory)
    if not evidence_dir.is_dir():
        print(f"ERROR: not a directory: {evidence_dir}", file=sys.stderr)
        sys.exit(1)

    result = evaluate_shadow_soak_evidence(evidence_dir)
    output_path = evidence_dir / "soak_gate_eval.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Shadow soak gate evaluation written to {output_path}")
    sys.exit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
