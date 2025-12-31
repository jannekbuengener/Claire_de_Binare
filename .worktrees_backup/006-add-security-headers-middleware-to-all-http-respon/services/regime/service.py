"""
Market Regime Service
Deterministic ADX/ATR-based regime detection.
"""

import json
import logging
import logging.config
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Optional

import redis
from flask import Flask, jsonify, Response

from core.security_headers import init_security_headers
from core.utils.clock import utcnow
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
init_security_headers(app)

stats = {
    "started_at": None,
    "candles_processed": 0,
    "regime_changes": 0,
    "last_regime": None,
    "status": "initializing",
}


class RegimeService:
    def __init__(self):
        self.config = config
        self.config.validate()
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.candles: dict[str, deque[Candle]] = defaultdict(
            lambda: deque(maxlen=max(self.config.adx_period, self.config.atr_period) * 5)
        )
        self.current_regime: dict[str, str] = defaultdict(lambda: "UNKNOWN")
        self.candidate_regime: dict[str, str | None] = defaultdict(lambda: None)
        self.candidate_count: dict[str, int] = defaultdict(int)

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

    def _emit_regime(self, candle: Candle, regime: str, adx: Optional[float], atr: Optional[float]):
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
        self.redis_client.xadd(self.config.output_stream, payload, maxlen=10000)
        stats["regime_changes"] += 1
        stats["last_regime"] = payload
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
        last_id = "0-0"
        logger.info("Regime-Service gestartet")

        while self.running:
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
                    self._derive_regime(candle)


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok" if stats["status"] == "running" else "error",
            "service": "regime_service",
            "version": config.source_version,
        }
    )


@app.route("/metrics")
def metrics():
    body = (
        "# HELP regime_candles_processed_total Anzahl verarbeiteter Candles\n"
        "# TYPE regime_candles_processed_total counter\n"
        f"regime_candles_processed_total {stats['candles_processed']}\n\n"
        "# HELP regime_changes_total Anzahl Regime-Wechsel\n"
        "# TYPE regime_changes_total counter\n"
        f"regime_changes_total {stats['regime_changes']}\n"
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
