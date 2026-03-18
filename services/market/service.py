"""Market Data Service — sidecar consumer of the ``market_data`` PubSub channel.

Subscribes to the ``market_data`` channel published by ``cdb_ws``.
Validates each message via ``sanitize_market_data``, updates an in-memory
price cache, and writes ``market_price:{symbol}`` into Redis (TTL 30 s).

Endpoints:
  GET /health                 — Docker HEALTHCHECK (503 when degraded)
  GET /status                 — operational stats + cached symbols
  GET /market/price/<symbol>  — last-known price entry for a symbol

Market State V1 (Issue #1201 Delta 1 — cutover complete):
  This service writes ``market_state:{symbol}`` (live key) into Redis.
  Cutover from the shadow key completed 2026-03-18; Evidence Gate PASS on record.
  MARKET_STATE_KEY_PREFIX=market_state is set in compose.blue.yml.

V3 WebSocket path (Issue #1206 — live-write active as of 2026-03-18):
  MARKET_V3_CLIENT_ENABLED=true activates a direct MEXC V3 WebSocket client
  alongside the existing ``cdb_ws`` PubSub path.

  Two modes, controlled by MARKET_V3_LIVE_WRITE:
    false (shadow mode):
      V3 writes to ``market_price_v3:{symbol}`` only.
      Verified via ``shadow_compare`` gate (v3_compare.py --mode shadow_compare).
      Shadow key exists; live key written by cdb_ws path only.

    true  (live-write mode — current BLUE state):
      V3 writes to ``market_price:{symbol}`` via _process_event().
      cdb_ws PubSub path continues in parallel (last-write-wins, both sources).
      Shadow key ``market_price_v3:{symbol}`` is intentionally absent.
      Verified via ``live_write_smoke`` gate (v3_compare.py --mode live_write_smoke).
      Evidence: reports/v3_smoke_BTCUSDT_live_write_2026-03-18.json (PASS 2026-03-18)

  Rollback: MARKET_V3_LIVE_WRITE=false + redeploy cdb_market → shadow-only immediately.
  Full disable: MARKET_V3_CLIENT_ENABLED=false + redeploy → zero V3 side-effects.
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
MARKET_REGIME_STALENESS_SECONDS = int(
    os.getenv("MARKET_REGIME_STALENESS_SECONDS", "300")
)

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

# V3 client metrics — always registered; stay at 0 when V3 path is disabled.
V3_DECODED_TOTAL = Gauge(
    "market_v3_decoded_total",
    "Total Protobuf messages decoded by the MEXC V3 WebSocket client",
)
V3_DECODE_ERRORS_TOTAL = Gauge(
    "market_v3_decode_errors_total",
    "Total Protobuf decode errors in the MEXC V3 WebSocket client",
)
V3_WS_CONNECTED = Gauge(
    "market_v3_ws_connected",
    "1 if the MEXC V3 WebSocket client is currently connected, 0 otherwise",
)
V3_LAST_MESSAGE_TS_MS = Gauge(
    "market_v3_last_message_ts_ms",
    "Epoch milliseconds of the last message received by the MEXC V3 WebSocket client",
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

# Set by _start_v3_client_if_enabled(); None when V3 path is disabled (default).
_v3_client = None


def _sync_v3_metrics() -> None:
    """Sync V3 client runtime counters into Prometheus gauges.

    Called from the /metrics handler on every scrape.
    No-op when _v3_client is None (V3 path disabled or not yet started).
    Fail-safe: any error is logged and swallowed — never breaks /metrics.
    """
    if _v3_client is None:
        return
    try:
        m = _v3_client.get_metrics()
        V3_DECODED_TOTAL.set(m.get("decoded_messages_total", 0))
        V3_DECODE_ERRORS_TOTAL.set(m.get("decode_errors_total", 0))
        V3_WS_CONNECTED.set(m.get("ws_connected", 0))
        V3_LAST_MESSAGE_TS_MS.set(m.get("last_message_ts_ms", 0))
    except Exception as exc:
        logger.warning("[v3] metrics sync error: %s", exc)


def _build_redis_client() -> redis.Redis:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD") or None
    return redis.Redis(host=host, port=port, password=password, decode_responses=True)


def _process_event(data: dict) -> None:
    """Validate, cache, and persist one already-decoded market event.

    Dict-based ingress point shared by all data paths:
    - Redis PubSub path: called from _process_message after JSON parsing
    - Future direct path: can be called directly from mexc_v3_client on_trade callback

    Caller is responsible for passing a dict; non-dict input will propagate
    TypeError from sanitize_market_data (existing behaviour, not changed here).
    """
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


def _process_message(raw: str) -> None:
    """Parse a JSON PubSub message and forward to _process_event.

    Thin wrapper: handles JSON decode errors only.
    All business logic lives in _process_event.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        _stats["messages_invalid"] += 1
        MESSAGES_INVALID.inc()
        return
    _process_event(data)


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
                "market_state skip: %s has only %d candles (need 6)",
                symbol,
                len(candles),
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

        return_1m = (close_now - close_1m_ago) / close_1m_ago
        return_5m = (close_now - close_5m_ago) / close_5m_ago
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
            "market_state updated: %s return_1m=%.6f return_5m=%.6f",
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
    return (
        jsonify({"status": "degraded", "service": "market_data", "detail": issues}),
        503,
    )


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
    _sync_v3_metrics()
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/market/price/<symbol>", methods=["GET"])
def market_price(symbol: str):
    key = symbol.upper()
    with _cache_lock:
        entry = _cache.get(key)
    if entry is None:
        return jsonify({"error": f"no data for symbol {key!r}"}), 404
    return jsonify(entry)


# ─── Optional V3 client bootstrap ────────────────────────────────────────────
#
# MARKET_V3_CLIENT_ENABLED (default false) — activates the V3 WebSocket client.
#   false: zero side effects, no dep imports.
#   true:  V3 client starts in daemon thread; bootstrap failure → RuntimeError (fail-closed).
#
# MARKET_V3_LIVE_WRITE (default false) — controls which Redis key the V3 callback writes.
#   false (shadow mode): writes market_price_v3:{symbol} only; live key unaffected.
#   true  (live mode):   writes market_price:{symbol} via _process_event(); cdb_ws PubSub
#                        path continues in parallel (last-write-wins).
#
# Rollback: set MARKET_V3_LIVE_WRITE=false + redeploy → reverts to shadow-only immediately.

MARKET_V3_CLIENT_ENABLED: bool = (
    os.getenv("MARKET_V3_CLIENT_ENABLED", "false").lower() == "true"
)
MARKET_V3_LIVE_WRITE: bool = (
    os.getenv("MARKET_V3_LIVE_WRITE", "false").lower() == "true"
)
MARKET_V3_SYMBOL: str = os.getenv("MARKET_V3_SYMBOL", "BTCUSDT")
MARKET_V3_PRICE_KEY_PREFIX: str = "market_price_v3"


def _parse_v3_symbols(raw: str) -> list[str]:
    """Parse a comma-separated symbol string for V3 client bootstrap.

    Strips whitespace, uppercases, and filters empty entries.
    Returns a non-empty list of symbol strings.
    Raises ValueError when no valid symbols remain after filtering.

    In the current single-symbol-per-instance model (Option A), each
    cdb_market container sets exactly one MARKET_V3_SYMBOL in compose.blue.yml.
    This function validates that value and prepares the interface for a future
    bootstrap loop should multi-symbol support be added.

    Examples:
        _parse_v3_symbols("BTCUSDT")            → ["BTCUSDT"]
        _parse_v3_symbols("BTCUSDT,ETHUSDT")    → ["BTCUSDT", "ETHUSDT"]
        _parse_v3_symbols("  btcusdt , eth  ")  → ["BTCUSDT", "ETH"]
        _parse_v3_symbols("")                   → ValueError
        _parse_v3_symbols(",,,")                → ValueError
    """
    symbols = [s.strip().upper() for s in raw.split(",")]
    symbols = [s for s in symbols if s]
    if not symbols:
        raise ValueError(f"No valid symbols in {raw!r}")
    return symbols


def _v3_shadow_event(data: dict) -> None:
    """Process one V3 client trade event in shadow/compare mode.

    Validates via sanitize_market_data(), then writes to market_price_v3:{symbol}.
    Does NOT write to market_price:{symbol} or market_state:{symbol}.
    _process_event() (the live path) is never called from here.
    Fail-safe: validation errors and Redis errors are logged and swallowed.
    """
    try:
        sanitized = sanitize_market_data(data)
    except ValueError as exc:
        logger.debug("[v3] shadow rejected: %s", exc)
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
    if _redis_client is not None:
        try:
            _redis_client.setex(
                f"{MARKET_V3_PRICE_KEY_PREFIX}:{key}",
                MARKET_PRICE_TTL_SECONDS,
                json.dumps(entry),
            )
            logger.debug("[v3] shadow write: %s:%s", MARKET_V3_PRICE_KEY_PREFIX, key)
        except redis.RedisError as exc:
            logger.warning("[v3] shadow write failed for %s: %s", key, exc)


def _v3_live_event(data: dict) -> None:
    """Process one V3 client trade event in live-write mode.

    Delegates directly to _process_event(), which:
      - validates via sanitize_market_data()
      - updates the in-memory price cache
      - writes market_price:{symbol} with TTL
      - updates market_state:{symbol}

    cdb_ws PubSub path continues to write in parallel; last-write-wins semantics apply.
    Only active when MARKET_V3_LIVE_WRITE=true.
    Fail-safe: validation and Redis errors are handled by _process_event().
    """
    _process_event(data)


def _start_v3_client_if_enabled() -> None:
    """Bootstrap MexcV3Client in a daemon thread, if MARKET_V3_CLIENT_ENABLED=true.

    Raises RuntimeError (fail-closed) if the flag is set but bootstrap fails,
    e.g. because websockets / protobuf dependencies are not installed.
    Sets module-level _v3_client so _sync_v3_metrics() can poll it on scrape.

    Callback selection (MARKET_V3_LIVE_WRITE):
      false (default) → _v3_shadow_event  — writes market_price_v3:{symbol} only
      true            → _v3_live_event    — writes market_price:{symbol} via _process_event
    """
    global _v3_client

    if not MARKET_V3_CLIENT_ENABLED:
        return

    if MARKET_V3_LIVE_WRITE:
        callback = _v3_live_event
        logger.warning(
            "[v3] MARKET_V3_LIVE_WRITE=true — V3 writes to live key market_price:%s",
            MARKET_V3_SYMBOL,
        )
    else:
        callback = _v3_shadow_event
        logger.info(
            "[v3] shadow mode — V3 writes to market_price_v3:%s only",
            MARKET_V3_SYMBOL,
        )

    logger.info("[v3] MARKET_V3_CLIENT_ENABLED=true — bootstrapping V3 client")
    try:
        from services.market.mexc_v3_client import MexcV3Client  # lazy import
    except ImportError as exc:
        raise RuntimeError(
            f"[v3] MARKET_V3_CLIENT_ENABLED=true but import failed "
            f"(websockets/protobuf missing?): {exc}"
        ) from exc

    # Single-symbol bootstrap (Option A: one cdb_market instance per symbol).
    # For multi-symbol support iterate _parse_v3_symbols(MARKET_V3_SYMBOL) here
    # and start one MexcV3Client + daemon thread per entry.
    client = MexcV3Client(symbol=MARKET_V3_SYMBOL, on_trade=callback)
    _v3_client = client

    def _run() -> None:
        import asyncio

        asyncio.run(client.run())

    thread = threading.Thread(target=_run, daemon=True, name="v3-client")
    thread.start()
    logger.info("[v3] client thread started for symbol=%s", MARKET_V3_SYMBOL)


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
        logger.warning(
            "Redis unavailable at startup: %s — running in degraded mode", exc
        )
        _redis_client = None

    flask_thread = threading.Thread(target=_run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask API started on port %d", _FLASK_PORT)

    _start_v3_client_if_enabled()  # no-op when MARKET_V3_CLIENT_ENABLED=false

    if _redis_client is None:
        logger.warning(
            "No Redis connection — cannot subscribe; service in degraded mode"
        )
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
