# tools/test_pack/tools/assertions/evaluate_assertions.py
# Purpose: evaluate basic assertions from a Prometheus snapshot.
# Stdlib only.

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.utils.clock import utcnow


def _extract_values(result_payload: dict) -> list[float]:
    data = result_payload.get("data", {}) if isinstance(result_payload, dict) else {}
    items = data.get("data", {}).get("result", []) if isinstance(data, dict) else []
    values = []
    for item in items:
        value = item.get("value")
        if isinstance(value, list) and len(value) == 2:
            try:
                values.append(float(value[1]))
            except ValueError:
                continue
    return values


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate chaos drill assertions")
    ap.add_argument("--snapshot", required=True, help="Path to metrics_snapshot.json")
    ap.add_argument("--out", required=True, help="Path to assertions_result.json")
    args = ap.parse_args()

    snapshot_path = Path(args.snapshot)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    assertions: list[dict[str, Any]] = []

    if not snapshot_path.exists():
        assertions.append({
            "id": "snapshot_exists",
            "name": "metrics snapshot exists",
            "pass": False,
            "observed": "missing",
            "threshold": "file present",
            "evidence_links": [str(snapshot_path)],
        })
        result = {
            "ts": utcnow().isoformat(),
            "overall_pass": False,
            "assertions": assertions,
        }
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 2

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    queries = snapshot.get("queries", {})

    # Assertion 1: up{job=~"cdb_.*"} all == 1
    up = queries.get("up_cdb", {})
    up_vals = _extract_values(up)
    up_pass = bool(up_vals) and all(v >= 1 for v in up_vals)
    assertions.append({
        "id": "up_cdb",
        "name": "all CDB targets UP",
        "pass": up_pass,
        "observed": up_vals,
        "threshold": ">= 1 for all",
        "evidence_links": [str(snapshot_path)],
    })

    # Assertion 2: circuit_breaker_active metric present
    cb = queries.get("circuit_breaker_active", {})
    cb_vals = _extract_values(cb)
    cb_pass = bool(cb_vals)
    assertions.append({
        "id": "circuit_breaker_metric",
        "name": "circuit_breaker_active present",
        "pass": cb_pass,
        "observed": cb_vals,
        "threshold": "metric exists",
        "evidence_links": [str(snapshot_path)],
    })

    # Assertion 3: orders metrics present (approved or blocked)
    approved = _extract_values(queries.get("orders_approved_total", {}))
    blocked = _extract_values(queries.get("orders_blocked_total", {}))
    ob_pass = bool(approved) or bool(blocked)
    assertions.append({
        "id": "orders_metrics_present",
        "name": "orders_approved_total or orders_blocked_total present",
        "pass": ob_pass,
        "observed": {"approved": approved, "blocked": blocked},
        "threshold": "at least one metric present",
        "evidence_links": [str(snapshot_path)],
    })

    overall_pass = all(a["pass"] for a in assertions)

    result = {
        "ts": utcnow().isoformat(),
        "overall_pass": overall_pass,
        "assertions": assertions,
    }

    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if overall_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
