"""Market Data Service — sidecar consumer of the ``market_data`` PubSub channel.

Subscribes to the ``market_data`` channel published by ``cdb_ws``.
Validates each message via ``sanitize_market_data``, updates an in-memory
price cache, and writes ``market_price:{symbol}`` into Redis (TTL 30 s).

Endpoints:
  GET /health                 — Docker HEALTHCHECK (503 when degraded)
  GET /status                 — operational stats + cached symbols
  GET /market/price/<symbol>  — last-known price entry for a symbol

Market State V1 (Issue #1201 Delta 1 — shadow mode):
  This service computes and writes ``market_state_shadow:{symbol}`` (shadow key)
  in parallel with ``cdb_candles`` writing to the live ``market_state:{symbol}``.
  The shadow key is used for Evidence Gate comparison only — no consumer reads it.

  Shadow mode is the default (MARKET_STATE_KEY_PREFIX=market_state_shadow).
  Cutover to the live key requires a passing Evidence Gate run and an explicit
  MARKET_STATE_KEY_PREFIX=market_state env-var change in compose.blue.yml.
"""

import json
import logging
import os
import sys
import threading
import time

import redis
from flask import Flask, jsonify
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

from core.utils.redis_payload import sanitize_market_data

# ─── Market State V1 config ───────────────────────────────────────────────────
# Mirrors cdb_candles config defaults exactly (no drift).

MARKET_CANDLES_STREAM = os.getenv("MARKET_CANDLES_STREAM", "stream.candles_1m")
MARKET_REGIME_STREAM = os.getenv("MARKET_REGIME_STREAM", "stream.regime_signals")
MARKET_STATE_KEY_PREFIX = os.getenv("MARKET_STATE_KEY_PREFIX", "market_state_shadow")
MARKET_STATE_TTL_SECONDS = int(os.getenv("MARKET_STATE_TTL_SECONDS", "120"))
MARKET_REGIME_STALENESS_SECONDS = int(os.getenv("MARKET_REGIME_STALENESS_SECONDS", "300"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] market_service: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MARKET_PRICE_TTL_SECONDS = 30
SUBSCRIBE_CHANNEL = "market_data"

# ─── Prometheus metrics ───────────────────────────────────────────────────────

MESSAGES_RECEIVED = Counter(
    "market_messages_received_total",
    "Total number of valid market_data messages processed",
)
MESSAGES_INVALID = Counter(
    "market_messages_invalid_total",
    "Total number of invalid or rejected market_data messages",
)
CACHE_SIZE = Gauge(
    "market_cache_size",
    "Number of symbols currently held in the in-memory price cache",
)

app = Flask(__name__)

# In-memory cache: symbol (uppercase str) -> last sanitized entry (dict)
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()

_stats: dict[str, int] = {
    "messages_received": 0,
    "messages_invalid": 0,
    "market_state_updates": 0,
    "market_state_skipped": 0,
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
        MESSAGES_INVALID.inc()
        return

    try:
        sanitized = sanitize_market_data(data)
    except ValueError as exc:
        _stats["messages_invalid"] += 1
        MESSAGES_INVALID.inc()
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
        CACHE_SIZE.set(len(_cache))

    _stats["messages_received"] += 1
    MESSAGES_RECEIVED.inc()

    if _redis_client is not None:
        try:
            _redis_client.setex(
                f"market_price:{key}",
                MARKET_PRICE_TTL_SECONDS,
                json.dumps(entry),
            )
        except redis.RedisError as exc:
            logger.warning("Redis write failed for %s: %s", key, exc)
        _update_market_state(key, entry["ts_ms"], _redis_client)


# ─── Market State V1 ─────────────────────────────────────────────────────────
#
# Identical contract to cdb_candles._lookup_regime_id / _update_market_state.
# No creative reinterpretation — any behavior change here is a bug.


def _lookup_regime_id(symbol: str, redis_client: redis.Redis) -> "int | None":
    """Lookup regime_id from stream.regime_signals (deterministic mapping).

    Mapping (identical to cdb_candles):
    - TREND → 0, RANGE → 1, HIGH_VOL_* → 2, CRISIS → 3
    - missing / stale / invalid → None (fail-closed: RC_001 blocks)
    """
    try:
        raw_entries = redis_client.xrevrange(MARKET_REGIME_STREAM, "+", "-", count=50)

        regime_entry = None
        for _entry_id, payload in raw_entries:
            if payload.get("symbol") == symbol:
                regime_entry = payload
                break

        if regime_entry is None:
            return None

        ts_raw = regime_entry.get("ts")
        if ts_raw is None:
            return None
        try:
            regime_ts = int(ts_raw)
        except (ValueError, TypeError):
            return None

        if regime_ts < 1_000_000_000 or regime_ts > 4_000_000_000:
            return None

        now_s = int(time.time())
        age = now_s - regime_ts
        if age < 0:
            return None
        if age > MARKET_REGIME_STALENESS_SECONDS:
            return None

        regime_str = (regime_entry.get("regime") or "").upper()
        if regime_str == "TREND":
            return 0
        elif regime_str == "RANGE":
            return 1
        elif regime_str.startswith("HIGH_VOL"):
            return 2
        elif regime_str == "CRISIS":
            return 3
        else:
            return None

    except Exception as exc:
        logger.warning("regime_id error for %s: %s", symbol, exc)
        return None


def _update_market_state(
    symbol: str, last_tick_ts_ms: "int | None", redis_client: redis.Redis
) -> None:
    """Compute market_state V1 from candle history and persist to Redis.

    Identical contract to cdb_candles._update_market_state (no drift):
    - Source: stream.candles_1m (last 6 candles via XREVRANGE, newest first)
    - Output: market_state:{symbol} with TTL 120s
    - Fail-closed: < 6 candles → no write; close=0 → no write

    Index semantics (XREVRANGE newest first):
      candles[0] = latest (now), candles[1] = 1m ago, candles[5] = 5m ago
    """
    try:
        raw_entries = redis_client.xrevrange(MARKET_CANDLES_STREAM, "+", "-", count=100)

        candles = []
        for _entry_id, payload in raw_entries:
            if payload.get("symbol") == symbol:
                candles.append(payload)
                if len(candles) >= 6:
                    break

        if len(candles) < 6:
            _stats["market_state_skipped"] += 1
            logger.debug(
                "market_state skip: %s has only %d candles (need 6)", symbol, len(candles)
            )
            return

        try:
            close_now = float(candles[0].get("close", 0))
            close_1m_ago = float(candles[1].get("close", 0))
            close_5m_ago = float(candles[5].get("close", 0))
        except (TypeError, ValueError):
            _stats["market_state_skipped"] += 1
            logger.warning("market_state skip: %s invalid close values", symbol)
            return

        if close_1m_ago == 0 or close_5m_ago == 0:
            _stats["market_state_skipped"] += 1
            logger.warning("market_state skip: %s close=0 in history", symbol)
            return

        # Canonical runtime contract: percentage points (10.0 == 10%)
        return_1m = ((close_now - close_1m_ago) / close_1m_ago) * 100.0
        return_5m = ((close_now - close_5m_ago) / close_5m_ago) * 100.0
        price_change_5m = abs(return_5m)

        regime_id = _lookup_regime_id(symbol, redis_client)

        ts_ms = int(time.time() * 1000)
        market_state = {
            "symbol": symbol,
            "return_1m": return_1m,
            "return_5m": return_5m,
            "price_change_5m": price_change_5m,
            "ts_ms": ts_ms,
            "close_now": close_now,
            "close_1m_ago": close_1m_ago,
            "close_5m_ago": close_5m_ago,
            "last_tick_ts_ms": last_tick_ts_ms,
        }
        if regime_id is not None:
            market_state["regime_id"] = regime_id

        key = f"{MARKET_STATE_KEY_PREFIX}:{symbol}"
        redis_client.setex(key, MARKET_STATE_TTL_SECONDS, json.dumps(market_state))

        _stats["market_state_updates"] += 1
        logger.debug(
            "market_state updated: %s return_1m=%.6f%% return_5m=%.6f%%",
            symbol,
            return_1m,
            return_5m,
        )

    except Exception as exc:
        _stats["market_state_skipped"] += 1
        logger.error("market_state error for %s: %s", symbol, exc)


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


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/market/price/<symbol>", methods=["GET"])
def market_price(symbol: str):
    key = symbol.upper()
    with _cache_lock:
        entry = _cache.get(key)
    if entry is None:
        return jsonify({"error": f"no data for symbol {key!r}"}), 404
    return jsonify(entry)


# ─── Main ─────────────────────────────────────────────────────────────────────


_FLASK_PORT: int = int(os.getenv("MARKET_PORT", "8009"))


def _run_flask() -> None:
    app.run(host="0.0.0.0", port=_FLASK_PORT, debug=False)


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
    logger.info("Flask API started on port %d", _FLASK_PORT)

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
