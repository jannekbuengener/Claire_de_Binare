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
from flask import Flask, jsonify, Response

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
app = Flask(__name__)

stats = {
    "started_at": None,
    "trades_processed": 0,
    "candles_emitted": 0,
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


if __name__ == "__main__":
    service = CandleService()
    service.connect_redis()

    # Start Flask in background thread
    from threading import Thread

    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()
    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Run main loop
    service.run()
