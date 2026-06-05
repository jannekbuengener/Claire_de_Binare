"""
Candle Aggregator Service
Aggregates raw trades (PubSub) into 1-minute OHLCV candles (Stream).
"""

import json
import logging
import logging.config
import sys
import time
from pathlib import Path
from threading import Thread
from typing import Optional

import redis
import importlib.util

try:
    _FLASK_AVAILABLE = importlib.util.find_spec("flask") is not None
except ModuleNotFoundError as e:
    if e.name == "flask" or (e.name and e.name.startswith("flask.")):
        _FLASK_AVAILABLE = False
    else:
        raise
except ValueError:
    _FLASK_AVAILABLE = False

from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_payload

try:
    from .config import config
    from .models import CandleAggregator
except ImportError:
    from config import config
    from models import CandleAggregator

logging_config_path = Path(__file__).parent.parent.parent / "logging_config.json"
if logging_config_path.exists():
    with open(logging_config_path) as f:
        logging_conf = json.load(f)
        logging.config.dictConfig(logging_conf)
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("candle_service")

stats = {
    "started_at": None,
    "trades_processed": 0,
    "candles_emitted": 0,
    "market_state_updates": 0,
    "market_state_skipped": 0,
    "status": "initializing",
}


class CandleService:
    def __init__(self):
        self.config = config
        self.config.validate()
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.running = False
        self.aggregator = CandleAggregator(
            interval_seconds=self.config.interval_seconds
        )

    def connect_redis(self):
        self.redis_client = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            password=self.config.redis_password,
            db=self.config.redis_db,
            decode_responses=True,
        )
        self.redis_client.ping()
        logger.info(
            "Redis verbunden: %s:%s", self.config.redis_host, self.config.redis_port
        )

    def _emit_candle(self, candle: dict):
        """Emit completed candle to stream"""
        sanitized = sanitize_payload(candle)
        sanitized["schema_version"] = self.config.schema_version
        sanitized["source_version"] = self.config.source_version

        self.redis_client.xadd(self.config.output_stream, sanitized, maxlen=100000)
        stats["candles_emitted"] += 1
        logger.info(
            "Candle emittiert: %s @ %s (O:%s H:%s L:%s C:%s V:%s)",
            candle.get("symbol"),
            candle.get("ts"),
            candle.get("open"),
            candle.get("high"),
            candle.get("low"),
            candle.get("close"),
            candle.get("volume"),
        )

        # Market State V1: Compute and persist returns after each candle.
        # Skipped when CANDLE_WRITE_MARKET_STATE=false (kill-switch for cutover).
        symbol = candle.get("symbol")
        if symbol and self.config.write_market_state:
            candle_ts_s = None
            if candle.get("ts") is not None:
                try:
                    candle_ts_s = int(candle.get("ts"))
                except (TypeError, ValueError):
                    candle_ts_s = None
            self._update_market_state(symbol, candle_ts_s)

    def _lookup_regime_id(
        self, symbol: str, as_of_ts_s: int | None = None
    ) -> int | None:
        """
        Lookup regime_id from stream.regime_signals (deterministic mapping).

        Mapping (from Regime Service output):
        - TREND → 0
        - RANGE → 1
        - HIGH_VOL_* (startswith) → 2
        - CRISIS → 3
        - UNKNOWN, missing, stale → None (fail-closed)

        Selection rule:
        - Prefer the newest valid regime entry at or before ``as_of_ts_s`` when
          provided (the candle timestamp that is being enriched).
        - Future, out-of-range, and stale entries are skipped so they cannot mask
          a valid current-window regime.

        Fail-closed:
        - No regime signal found → None → RC_001 blocks
        - Regime signal stale (> regime_staleness_seconds) → None → RC_001 blocks
        - Regime ts invalid or in future → None → RC_001 blocks
        - Regime string not in mapping → None → RC_001 blocks
        """
        try:
            # Read latest regime signal for this symbol
            raw_entries = self.redis_client.xrevrange(
                self.config.regime_stream, "+", "-", count=50
            )

            lookup_ts_s = int(time.time()) if as_of_ts_s is None else int(as_of_ts_s)

            # Find latest valid entry for this symbol at or before the lookup anchor.
            regime_entry = None
            for entry_id, payload in raw_entries:
                if payload.get("symbol") != symbol:
                    continue

                # Parse and validate ts (must be seconds, not ms)
                ts_raw = payload.get("ts")
                if ts_raw is None:
                    logger.debug("regime_id skip: %s ts missing", symbol)
                    continue
                try:
                    regime_ts = int(ts_raw)
                except (ValueError, TypeError):
                    logger.debug("regime_id skip: %s ts not parseable", symbol)
                    continue

                # Plausibility: must be seconds (not ms), not too old, not in future
                if regime_ts < 1_000_000_000 or regime_ts > 4_000_000_000:
                    logger.debug(
                        "regime_id skip: %s ts out of range %d", symbol, regime_ts
                    )
                    continue

                age = lookup_ts_s - regime_ts
                if age < 0:
                    logger.debug("regime_id skip: %s ts in future", symbol)
                    continue

                if age > self.config.regime_staleness_seconds:
                    logger.debug(
                        "regime_id skip: %s signal stale (%ds old, max %ds)",
                        symbol,
                        age,
                        self.config.regime_staleness_seconds,
                    )
                    continue

                regime_entry = payload
                break

            if regime_entry is None:
                logger.debug("regime_id skip: %s no signal found", symbol)
                return None

            # Deterministic mapping: regime string → regime_id
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
                logger.debug(
                    "regime_id skip: %s unknown regime '%s'", symbol, regime_str
                )
                return None

        except Exception as e:
            logger.warning("regime_id error for %s: %s", symbol, e)
            return None

    def _update_market_state(self, symbol: str, candle_ts_s: int | None = None) -> None:
        """
        Compute market_state V1 returns from candle history and persist to Redis.

        Source: stream.candles_1m (last 6 candles via XREVRANGE)
        Output: market_state:{symbol} Redis key with TTL

        Fail-closed:
        - If history < 6 candles → no update (Risk blocks with RC_002)
        - If any close == 0 → no update
        - No defaults, no fallbacks

        Index semantics (XREVRANGE returns newest first):
        - candles[0] = latest (now)
        - candles[1] = 1 minute ago
        - candles[5] = 5 minutes ago
        """
        try:
            # Read last 6 candles for this symbol from stream
            # XREVRANGE returns newest first: [0]=now, [1]=1m ago, ..., [5]=5m ago
            raw_entries = self.redis_client.xrevrange(
                self.config.output_stream, "+", "-", count=100
            )

            # Filter for this symbol only
            candles = []
            for entry_id, payload in raw_entries:
                if payload.get("symbol") == symbol:
                    candles.append(payload)
                    if len(candles) >= 6:
                        break

            # Fail-closed: Need at least 6 candles for 5-minute return
            if len(candles) < 6:
                stats["market_state_skipped"] += 1
                logger.debug(
                    "market_state skip: %s has only %d candles (need 6)",
                    symbol,
                    len(candles),
                )
                return

            # Extract close prices
            try:
                close_now = float(candles[0].get("close", 0))
                close_1m_ago = float(candles[1].get("close", 0))
                close_5m_ago = float(candles[5].get("close", 0))
            except (TypeError, ValueError):
                stats["market_state_skipped"] += 1
                logger.warning("market_state skip: %s invalid close values", symbol)
                return

            # Fail-closed: Division by zero guard
            if close_1m_ago == 0 or close_5m_ago == 0:
                stats["market_state_skipped"] += 1
                logger.warning("market_state skip: %s close=0 in history", symbol)
                return

            # Canonical runtime contract: percentage points (10.0 == 10%)
            return_1m = ((close_now - close_1m_ago) / close_1m_ago) * 100.0
            return_5m = ((close_now - close_5m_ago) / close_5m_ago) * 100.0
            price_change_5m = abs(return_5m)

            # Lookup regime_id from stream.regime_signals (fail-closed)
            # Anchor to the candle timestamp so a later future/stale regime entry
            # cannot override the regime that was valid for this candle.
            regime_id = self._lookup_regime_id(symbol, candle_ts_s)

            # Build market_state payload
            ts_ms = int(time.time() * 1000)
            # Get last_tick_ts_ms from aggregator (updated on each trade)
            last_tick_ts_ms = self.aggregator.last_tick_ts_ms.get(symbol)
            # When the last tick source is a stimulus fixture, the aggregator's
            # ts_ms is a historical fixture timestamp.  Use wall-clock to preserve
            # freshness so cdb_risk RC_004 (data_silence) does not block the
            # shadow-validation path (#3021).  Without this, cdb_candles overwrites
            # the wall-clock value that cdb_market already wrote (#3019).
            if self.aggregator.last_tick_source.get(symbol) == "stimulus_fixture":
                last_tick_ts_ms = ts_ms
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
            # Only set regime_id if valid (fail-closed: missing key → RC_001 blocks)
            if regime_id is not None:
                market_state["regime_id"] = regime_id

            # Persist to Redis with TTL
            key = f"{self.config.market_state_key_prefix}:{symbol}"
            self.redis_client.setex(
                key,
                self.config.market_state_ttl_seconds,
                json.dumps(market_state),
            )

            stats["market_state_updates"] += 1
            logger.debug(
                "market_state updated: %s return_1m=%.6f%% return_5m=%.6f%%",
                symbol,
                return_1m,
                return_5m,
            )

        except Exception as e:
            stats["market_state_skipped"] += 1
            logger.error("market_state error for %s: %s", symbol, e)

    def _process_trade(self, trade: dict):
        """Process incoming trade and emit completed candles"""
        completed = self.aggregator.process_trade(trade)
        for candle in completed:
            self._emit_candle(candle)

    def _sweep_expired_windows(self):
        """Periodic task: Force-close expired windows"""
        while self.running:
            time.sleep(self.config.interval_seconds)
            current_ts = int(time.time())
            completed = self.aggregator.get_completed_windows(current_ts)
            for candle in completed:
                self._emit_candle(candle)

    def run(self):
        if not self.redis_client:
            self.connect_redis()

        # Subscribe to market_data PubSub channel
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(self.config.input_channel)
        logger.info(f"Subscribed zu PubSub channel: {self.config.input_channel}")

        # Start sweep thread
        sweep_thread = Thread(target=self._sweep_expired_windows, daemon=True)
        sweep_thread.start()

        self.running = True
        stats["status"] = "running"
        stats["started_at"] = utcnow().isoformat()
        logger.info("Candle-Service gestartet")

        # Main loop: Listen to PubSub
        for message in self.pubsub.listen():
            if not self.running:
                break

            if message["type"] != "message":
                continue

            try:
                data = message.get("data")
                if not data:
                    continue

                # Parse JSON
                trade = json.loads(data)
                stats["trades_processed"] += 1
                self._process_trade(trade)

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in PubSub message")
            except Exception as e:
                logger.error(f"Error processing trade: {e}")


# ===== FLASK ENDPOINTS =====

if _FLASK_AVAILABLE:
    from flask import Flask, jsonify, Response

    app = Flask(__name__)

    @app.route("/health")
    def health():
        return jsonify(
            {
                "status": "ok" if stats["status"] == "running" else "error",
                "service": "candle_service",
                "version": config.source_version,
            }
        )

    @app.route("/metrics")
    def metrics():
        body = (
            "# HELP candle_trades_processed_total Anzahl verarbeiteter Trades\n"
            "# TYPE candle_trades_processed_total counter\n"
            f"candle_trades_processed_total {stats['trades_processed']}\n\n"
            "# HELP candle_candles_emitted_total Anzahl emittierter Candles\n"
            "# TYPE candle_candles_emitted_total counter\n"
            f"candle_candles_emitted_total {stats['candles_emitted']}\n"
        )
        return Response(body, mimetype="text/plain")

else:
    app = None


if __name__ == "__main__":
    service = CandleService()
    service.connect_redis()

    # Start Flask in background thread
    if not _FLASK_AVAILABLE or app is None:
        raise RuntimeError(
            "Flask ist nicht installiert. HTTP-Endpoints (health/metrics) "
            "benötigen Flask als optionale Abhängigkeit: pip install flask"
        )
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()
    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Run main loop
    service.run()
