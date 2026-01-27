# tools/test_pack/tools/ingestion/ingest_scenario.py
# Purpose: publish chaos scenario JSONL into CDB market_data channel (Redis).
# Stdlib + redis client (matches repo dependency).

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import redis

# Ensure repo root is on sys.path for shared utils
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.utils.redis_payload import sanitize_market_data


def _iso_to_ms(ts: str) -> int:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return int(dt.timestamp() * 1000)


def _load_redis_password() -> str | None:
    env_pw = os.getenv("REDIS_PASSWORD")
    if env_pw:
        return env_pw

    secrets_path = os.getenv("SECRETS_PATH", os.path.expanduser("~/.secrets/.cdb"))
    pw_file = Path(secrets_path) / "REDIS_PASSWORD"
    if pw_file.exists():
        return pw_file.read_text().strip()

    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest chaos scenario JSONL into Redis market_data")
    ap.add_argument("--scenario", required=True, help="Path to scenario JSONL")
    ap.add_argument("--out", required=True, help="Output report JSON path")
    ap.add_argument("--redis-host", default=os.getenv("REDIS_HOST", "localhost"))
    ap.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", "6379")))
    ap.add_argument("--redis-db", type=int, default=int(os.getenv("REDIS_DB", "0")))
    ap.add_argument("--redis-password", default=None)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--trade-qty", default="1")
    ap.add_argument("--source", default="test_pack")
    ap.add_argument("--tick-delay-ms", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="Parse only, no Redis publish")
    ap.add_argument("--channel", default="market_data")
    ap.add_argument("--run-id", default=None, help="Optional run id for traceability")
    args = ap.parse_args()

    scenario_path = Path(args.scenario)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stats: Dict[str, Any] = {
        "scenario": str(scenario_path),
        "channel": args.channel,
        "symbol": args.symbol,
        "trade_qty": args.trade_qty,
        "source": args.source,
        "run_id": args.run_id,
        "ticks_total": 0,
        "ticks_published": 0,
        "errors": 0,
        "dry_run": bool(args.dry_run),
    }

    if not scenario_path.exists():
        stats["error"] = f"Scenario not found: {scenario_path}"
        out_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
        return 1

    redis_password = args.redis_password or _load_redis_password()

    client = None
    if not args.dry_run:
        try:
            client = redis.Redis(
                host=args.redis_host,
                port=args.redis_port,
                password=redis_password,
                db=args.redis_db,
                decode_responses=True,
            )
            client.ping()
            stats["redis_connected"] = True
        except Exception as e:
            stats["redis_connected"] = False
            stats["error"] = f"Redis connection failed: {e}"
            out_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
            return 1

    try:
        with scenario_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                stats["ticks_total"] += 1
                try:
                    tick = json.loads(line)
                    ts = tick.get("ts") or tick.get("timestamp")
                    if not ts:
                        raise ValueError("missing ts")

                    payload = {
                        "schema_version": "v1.0",
                        "type": "market_data",
                        "source": args.source,
                        "symbol": args.symbol,
                        "ts_ms": _iso_to_ms(ts),
                        "price": str(tick.get("price", "0")),
                        "trade_qty": str(args.trade_qty),
                        "side": "BUY" if (tick.get("step", 0) % 2 == 0) else "SELL",
                    }

                    if args.run_id:
                        payload["bot_id"] = args.run_id

                    sanitized = sanitize_market_data(payload)

                    if not args.dry_run and client is not None:
                        client.publish(args.channel, json.dumps(sanitized))
                        stats["ticks_published"] += 1

                except Exception:
                    stats["errors"] += 1

                if args.tick_delay_ms > 0:
                    import time

                    time.sleep(args.tick_delay_ms / 1000.0)

    finally:
        if client is not None:
            client.close()

    out_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return 0 if stats["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())