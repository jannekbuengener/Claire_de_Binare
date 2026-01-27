"""
Mock Exchange (stdlib only)

Purpose:
- Accept orders/cancels like a trading API would
- Deterministic responses for testing (no real market access)
- Provides a minimal /health endpoint for harness scripts

This is intentionally small: it's a "shim" you can wire to cdb_execution
when you want realistic order-lifecycle tests without the real exchange.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Any, Optional

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.utils.uuid_gen import generate_uuid
STATE: Dict[str, Any] = {
    "started_ts": time.time(),
    "orders": {},  # order_id -> dict
    "fills": [],   # list of fills
}

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str
    qty: float
    price: Optional[float]
    status: str  # NEW | FILLED | CANCELED | REJECTED
    ts: float

def _json(handler: BaseHTTPRequestHandler, code: int, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        # keep quiet; evidence scripts can capture stdout if needed
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            return _json(self, 200, {"ok": True, "uptime_s": round(time.time() - STATE["started_ts"], 3)})
        if self.path == "/state":
            return _json(self, 200, {"orders": len(STATE["orders"]), "fills": len(STATE["fills"])})
        return _json(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return _json(self, 400, {"ok": False, "error": "invalid_json"})

        if self.path == "/order":
            # expected: {symbol, side, qty, price?}
            try:
                symbol = str(body["symbol"])
                side = str(body["side"]).upper()
                qty = float(body["qty"])
                price = body.get("price", None)
                price = float(price) if price is not None else None
                if side not in {"BUY", "SELL"} or qty <= 0:
                    raise ValueError("bad_order")
            except Exception:
                return _json(self, 400, {"ok": False, "error": "bad_order_payload"})

            oid = generate_uuid()
            order = Order(order_id=oid, symbol=symbol, side=side, qty=qty, price=price, status="NEW", ts=time.time())
            STATE["orders"][oid] = asdict(order)

            # deterministic auto-fill: if price is provided, fill immediately; else keep NEW
            if price is not None:
                STATE["orders"][oid]["status"] = "FILLED"
                STATE["fills"].append({"order_id": oid, "qty": qty, "price": price, "ts": time.time()})

            return _json(self, 200, {"ok": True, "order": STATE["orders"][oid]})

        if self.path == "/cancel":
            try:
                oid = str(body["order_id"])
            except Exception:
                return _json(self, 400, {"ok": False, "error": "bad_cancel_payload"})

            order = STATE["orders"].get(oid)
            if not order:
                return _json(self, 404, {"ok": False, "error": "unknown_order"})
            if order["status"] in {"FILLED", "CANCELED"}:
                return _json(self, 200, {"ok": True, "order": order})

            order["status"] = "CANCELED"
            return _json(self, 200, {"ok": True, "order": order})

        return _json(self, 404, {"ok": False, "error": "not_found"})

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Mock Exchange (HTTP)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=18080)
    args = ap.parse_args()

    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"MockExchange listening on http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
