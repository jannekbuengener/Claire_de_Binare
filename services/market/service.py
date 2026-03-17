"""Market Data Service — sidecar consumer of the ``market_data`` PubSub channel.

Subscribes to the ``market_data`` channel published by ``cdb_ws``.
Validates each message via ``sanitize_market_data``, updates an in-memory
price cache, and writes ``market_price:{symbol}`` into Redis (TTL 30 s).

Endpoints:
  GET /health                 — Docker HEALTHCHECK (503 when degraded)
  GET /status                 — operational stats + cached symbols
  GET /market/price/<symbol>  — last-known price entry for a symbol

NOTE (PR1): This service intentionally does not write to ``market_state:{symbol}``.
Existing consumers (cdb_risk, cdb_signal) depend on computed fields in that key
that are written by cdb_candles. The architecture of that key is deferred to PR2.
"""

import json
import logging
import os
import sys
import threading
import time

import redis
from flask import Flask, jsonify

from core.utils.redis_payload import sanitize_market_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] market_service: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MARKET_PRICE_TTL_SECONDS = 30
SUBSCRIBE_CHANNEL = "market_data"

app = Flask(__name__)

# In-memory cache: symbol (uppercase str) -> last sanitized entry (dict)
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()

_stats: dict[str, int] = {
    "messages_received": 0,
    "messages_invalid": 0,
}

_redis_client: redis.Redis | None = None
_redis_connected: bool = False
_subscription_active: bool = False


def _build_redis_client() -> redis.Redis:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD") or None
    return redis.Redis(host=host, port=port, password=password, decode_responses=True)


def _process_message(raw: str) -> None:
    """Parse, validate, cache, and persist one PubSub message."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        _stats["messages_invalid"] += 1
        return

    try:
        sanitized = sanitize_market_data(data)
    except ValueError as exc:
        _stats["messages_invalid"] += 1
        logger.debug("sanitize_market_data rejected: %s", exc)
        return

    key = str(sanitized["symbol"]).upper()
    entry = {
        "symbol": key,
        "price": sanitized["price"],
        "ts_ms": sanitized["ts_ms"],
        "source": sanitized["source"],
        "trade_qty": sanitized["trade_qty"],
        "side": sanitized["side"],
        "cached_at_ms": int(time.time() * 1000),
    }
    with _cache_lock:
        _cache[key] = entry

    _stats["messages_received"] += 1

    if _redis_client is not None:
        try:
            _redis_client.setex(
                f"market_price:{key}",
                MARKET_PRICE_TTL_SECONDS,
                json.dumps(entry),
            )
        except redis.RedisError as exc:
            logger.warning("Redis write failed for %s: %s", key, exc)


# ─── Flask endpoints ──────────────────────────────────────────────────────────


@app.route("/health", methods=["GET"])
def health():
    if _redis_connected and _subscription_active:
        return jsonify({"status": "healthy", "service": "market_data"}), 200
    issues = []
    if not _redis_connected:
        issues.append("redis unavailable")
    if not _subscription_active:
        issues.append("no active subscription")
    return jsonify({"status": "degraded", "service": "market_data", "detail": issues}), 503


@app.route("/status", methods=["GET"])
def status():
    with _cache_lock:
        symbols = list(_cache.keys())
    return jsonify(
        {
            "service": "market_data",
            "redis_connected": _redis_connected,
            "subscription_active": _subscription_active,
            "stats": dict(_stats),
            "cached_symbols": symbols,
        }
    )


@app.route("/market/price/<symbol>", methods=["GET"])
def market_price(symbol: str):
    key = symbol.upper()
    with _cache_lock:
        entry = _cache.get(key)
    if entry is None:
        return jsonify({"error": f"no data for symbol {key!r}"}), 404
    return jsonify(entry)


# ─── Main ─────────────────────────────────────────────────────────────────────


def _run_flask() -> None:
    app.run(host="0.0.0.0", port=8004, debug=False)


def main() -> None:
    global _redis_client, _redis_connected, _subscription_active

    try:
        _redis_client = _build_redis_client()
        _redis_client.ping()
        _redis_connected = True
        logger.info("Redis connected at %s", os.getenv("REDIS_HOST", "localhost"))
    except redis.RedisError as exc:
        logger.warning("Redis unavailable at startup: %s — running in degraded mode", exc)
        _redis_client = None

    flask_thread = threading.Thread(target=_run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask API started on port 8004")

    if _redis_client is None:
        logger.warning("No Redis connection — cannot subscribe; service in degraded mode")
        while True:
            time.sleep(60)

    try:
        pubsub = _redis_client.pubsub()
        pubsub.subscribe(SUBSCRIBE_CHANNEL)
        _subscription_active = True
        logger.info("Subscribed to channel: %s", SUBSCRIBE_CHANNEL)
        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            _process_message(message["data"])
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except redis.RedisError as exc:
        logger.error("PubSub error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
