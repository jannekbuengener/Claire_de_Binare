"""
Market Regime Service
Deterministic ADX/ATR-based regime detection.
"""

import json
import logging
import logging.config
import sys
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Optional

import redis
from flask import Flask, jsonify, Response

from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_payload

try:
    from .config import config
    from .models import Candle, compute_adx, compute_atr
except ImportError:
    from config import config
    from models import Candle, compute_adx, compute_atr

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

logger = logging.getLogger("regime_service")
app = Flask(__name__)

stats = {
    "started_at": None,
    "candles_processed": 0,
    "regime_changes": 0,
    "last_regime": None,
    "status": "initializing",
}


def _utc_ts() -> float:
    """Return current UTC timestamp as float."""
    return utcnow().timestamp()


class RegimeService:
    def __init__(self):
        self.config = config
        self.config.validate()
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.candles: dict[str, deque[Candle]] = defaultdict(
            lambda: deque(
                maxlen=max(self.config.adx_period, self.config.atr_period) * 5
            )
        )
        self.current_regime: dict[str, str] = defaultdict(lambda: "UNKNOWN")
        self.candidate_regime: dict[str, str | None] = defaultdict(lambda: None)
        self.candidate_count: dict[str, int] = defaultdict(int)
        self.last_emitted_ts: dict[str, float] = defaultdict(float)

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

    def _emit_regime(
        self, candle: Candle, regime: str, adx: Optional[float], atr: Optional[float]
    ):
        payload = {
            "ts": str(candle.ts),
            "symbol": candle.symbol,
            "timeframe": candle.timeframe,
            "regime": regime,
            "adx": "" if adx is None else f"{adx:.6f}",
            "atr": "" if atr is None else f"{atr:.6f}",
            "source_version": self.config.source_version,
            "schema_version": self.config.schema_version,
        }
        sanitized = sanitize_payload(payload)
        self.redis_client.xadd(self.config.output_stream, sanitized, maxlen=10000)
        stats["regime_changes"] += 1
        stats["last_regime"] = sanitized
        key = f"{candle.symbol}:{candle.timeframe}:{candle.venue or ''}"
        self.last_emitted_ts[key] = time.time()
        logger.info(
            "Regime-Signal: %s %s %s",
            candle.symbol,
            candle.timeframe,
            regime,
        )

    def _derive_regime(self, candle: Candle) -> None:
        key = f"{candle.symbol}:{candle.timeframe}:{candle.venue or ''}"
        bucket = self.candles[key]
        bucket.append(candle)
        adx = compute_adx(list(bucket), self.config.adx_period)
        atr = compute_atr(list(bucket), self.config.atr_period)
        if adx is None or atr is None:
            return
        if atr >= self.config.atr_high_vol_threshold:
            raw_regime = "HIGH_VOL_CHAOTIC"
        elif adx >= self.config.adx_trend_threshold:
            raw_regime = "TREND"
        elif adx <= self.config.adx_range_threshold:
            raw_regime = "RANGE"
        else:
            raw_regime = self.current_regime[key]

        if raw_regime == self.current_regime[key]:
            self.candidate_regime[key] = None
            self.candidate_count[key] = 0
            # Heartbeat: re-emit unchanged regime so downstream staleness checks pass.
            # Without this, a stable regime produces no stream entries → _lookup_regime_id
            # sees a stale ts → returns None → market_state has no regime_id → RC_001 blocks.
            if (
                raw_regime != "UNKNOWN"
                and time.time() - self.last_emitted_ts[key]
                > self.config.heartbeat_interval_s
            ):
                self._emit_regime(candle, raw_regime, adx, atr)
            return

        if self.candidate_regime[key] != raw_regime:
            self.candidate_regime[key] = raw_regime
            self.candidate_count[key] = 1
        else:
            self.candidate_count[key] += 1

        if self.candidate_count[key] >= self.config.confirmation_bars:
            self.current_regime[key] = raw_regime
            self.candidate_regime[key] = None
            self.candidate_count[key] = 0
            self._emit_regime(candle, raw_regime, adx, atr)

    def _handle_missing_ohlcv(self, payload: dict):
        symbol = payload.get("symbol")
        timeframe = payload.get("timeframe") or payload.get("interval")
        if not symbol or not timeframe:
            return
        key = f"{symbol}:{timeframe}:{payload.get('venue') or ''}"
        if self.current_regime.get(key) != "UNKNOWN":
            self.current_regime[key] = "UNKNOWN"
            dummy = Candle(
                ts=int(payload.get("ts") or payload.get("timestamp") or 0),
                symbol=symbol,
                timeframe=str(timeframe),
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                volume=0.0,
                venue=payload.get("venue"),
            )
            self._emit_regime(dummy, "UNKNOWN", None, None)

    def run(self):
        if not self.redis_client:
            self.connect_redis()

        self.running = True
        stats["status"] = "running"
        stats["started_at"] = utcnow().isoformat()
        stats.setdefault("candles_processed", 0)
        stats.setdefault("regime_changes", 0)
        stats["consumer_errors"] = 0
        stats["last_error"] = ""
        stats["last_heartbeat_ts"] = _utc_ts()
        stats["last_processed_ts"] = 0.0

        last_id = "0-0"
        logger.info("Regime-Service gestartet")

        while self.running:
            try:
                stats["last_heartbeat_ts"] = _utc_ts()

                response = self.redis_client.xread(
                    {self.config.input_stream: last_id}, block=1000, count=10
                )

                if not response:
                    continue

                for _, entries in response:
                    for entry_id, payload in entries:
                        last_id = entry_id

                        candle = Candle.from_payload(payload)
                        if candle is None:
                            self._handle_missing_ohlcv(payload)
                            continue

                        stats["candles_processed"] += 1
                        stats["last_processed_ts"] = _utc_ts()
                        self._derive_regime(candle)

            except redis.exceptions.ConnectionError as e:
                stats["consumer_errors"] += 1
                stats["status"] = "reconnecting"
                stats["last_error"] = f"redis_connection_error: {e}"
                logger.exception("Redis connection lost – reconnecting")

                time.sleep(5)
                try:
                    self.connect_redis()
                    # hard proof the connection is alive
                    self.redis_client.ping()
                    stats["status"] = "running"
                    logger.info("Redis reconnected successfully")
                except Exception as reconnect_err:
                    stats["consumer_errors"] += 1
                    stats["last_error"] = f"redis_reconnect_failed: {reconnect_err}"
                    logger.exception("Redis reconnect failed – will retry")
                    time.sleep(5)

            except Exception as e:
                stats["consumer_errors"] += 1
                stats["last_error"] = f"consumer_loop_error: {e}"
                logger.exception(
                    "Consumer loop error (candles_processed=%d, last_id=%s)",
                    stats["candles_processed"],
                    last_id,
                )
                time.sleep(1)


@app.route("/health")
def health():
    now = _utc_ts()
    hb = float(stats.get("last_heartbeat_ts", 0.0))
    age = now - hb if hb else 1e9
    is_alive = age < 60 and stats.get("status") == "running"

    payload = {
        "status": "ok" if is_alive else "error",
        "service": "regime_service",
        "version": config.source_version,
        "heartbeat_age_seconds": age,
        "consumer_errors": stats.get("consumer_errors", 0),
        "last_error": stats.get("last_error", ""),
    }
    return jsonify(payload), (200 if is_alive else 503)


@app.route("/metrics")
def metrics():
    body = (
        "# HELP regime_candles_processed_total Anzahl verarbeiteter Candles\n"
        "# TYPE regime_candles_processed_total counter\n"
        f"regime_candles_processed_total {stats.get('candles_processed', 0)}\n\n"
        "# HELP regime_changes_total Anzahl Regime-Wechsel\n"
        "# TYPE regime_changes_total counter\n"
        f"regime_changes_total {stats.get('regime_changes', 0)}\n\n"
        "# HELP regime_consumer_errors_total Consumer loop errors\n"
        "# TYPE regime_consumer_errors_total counter\n"
        f"regime_consumer_errors_total {stats.get('consumer_errors', 0)}\n\n"
        "# HELP regime_last_heartbeat_timestamp_seconds Consumer loop last heartbeat\n"
        "# TYPE regime_last_heartbeat_timestamp_seconds gauge\n"
        f"regime_last_heartbeat_timestamp_seconds {stats.get('last_heartbeat_ts', 0.0)}\n\n"
        "# HELP regime_last_processed_timestamp_seconds Last candle processed timestamp\n"
        "# TYPE regime_last_processed_timestamp_seconds gauge\n"
        f"regime_last_processed_timestamp_seconds {stats.get('last_processed_ts', 0.0)}\n"
    )
    return Response(body, mimetype="text/plain")


if __name__ == "__main__":
    service = RegimeService()
    service.connect_redis()
    from threading import Thread

    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()
    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    service.run()
