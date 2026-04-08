# tools/test_pack/tools/metrics/metrics_snapshot.py
# Status: experimental helper under tools/test_pack, not the canonical 431C source of truth.
# Purpose: capture a minimal Prometheus metrics snapshot for chaos drills.
# Stdlib only.

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

def _bootstrap_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
DEFAULT_QUERIES = {
    "up_cdb": 'up{job=~"cdb_.*"}',
    "signals_received_total": "signals_received_total",
    "orders_approved_total": "orders_approved_total",
    "orders_blocked_total": "orders_blocked_total",
    "circuit_breaker_active": "circuit_breaker_active",
    "risk_total_exposure_value": "risk_total_exposure_value",
    "risk_pending_orders_total": "risk_pending_orders_total",
}


def _query_prom(base_url: str, query: str) -> dict:
    params = urlencode({"query": query})
    url = f"{base_url}/api/v1/query?{params}"
    req = Request(url, headers={"User-Agent": "cdb-test-pack"})
    try:
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return {"status": "success", "data": payload}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main() -> int:
    _bootstrap_repo_root()
    from core.utils.clock import utcnow

    ap = argparse.ArgumentParser(description="Prometheus snapshot for chaos drills")
    ap.add_argument("--prom-url", default="http://127.0.0.1:19090")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "ts": utcnow().isoformat(),
        "prom_url": args.prom_url,
        "queries": {},
    }

    for name, query in DEFAULT_QUERIES.items():
        result = _query_prom(args.prom_url, query)
        report["queries"][name] = {
            "query": query,
            **result,
        }

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
