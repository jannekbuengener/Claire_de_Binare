"""
Dry/Wet Adaptive Intensity Service

Runs a lightweight loop that:
- pulls the latest trades from Postgres,
- computes a Dry/Wet score (0..100) and derived risk parameters,
- publishes them to Redis key `adaptive_intensity:current_params`,
- exposes Prometheus metrics and simple health/status endpoints.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import redis
from flask import Flask, jsonify
from prometheus_client import Gauge, Histogram, REGISTRY, generate_latest

from .dry_wet import compute_and_publish

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
DRY_WET_SCORE = Gauge("dry_wet_score", "Dry/Wet score (0=DRY, 100=WET)")
DRY_WET_WINRATE = Gauge("dry_wet_winrate", "Winrate of lookback window")
DRY_WET_PROFIT_FACTOR = Gauge("dry_wet_profit_factor", "Profit factor of lookback window")
DRY_WET_MAX_DRAWDOWN = Gauge("dry_wet_max_drawdown", "Max drawdown (fraction) of lookback window")
DRY_WET_WINDOW_TRADES = Gauge("dry_wet_window_trades_total", "Trades in lookback window")
UPDATE_DURATION = Histogram(
    "dry_wet_update_duration_seconds", "Time spent computing Dry/Wet parameters"
)


redis_client: Optional[redis.Redis] = None
current_params: Optional[dict] = None


def init_redis():
    """Initialize Redis connection."""
    global redis_client
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        db=0,
        decode_responses=True,
    )
    redis_client.ping()
    logger.info("Redis connected")


def update_metrics(params: dict):
    """Update Prometheus metrics from params."""
    DRY_WET_SCORE.set(params.get("dry_wet_score", 0))
    DRY_WET_WINRATE.set(params.get("winrate", 0))
    DRY_WET_PROFIT_FACTOR.set(params.get("profit_factor", 0))
    DRY_WET_MAX_DRAWDOWN.set(params.get("max_drawdown", 0))
    DRY_WET_WINDOW_TRADES.set(params.get("window_trades", 0))


def update_loop():
    """Background loop to compute and publish parameters."""
    global current_params
    interval = int(os.getenv("ADAPTIVE_UPDATE_INTERVAL_SEC", "30"))
    logger.info("Starting Dry/Wet update loop (interval=%ss)", interval)

    while True:
        try:
            with UPDATE_DURATION.time():
                params = compute_and_publish(redis_client)
                current_params = params
                update_metrics(params)
                logger.info(
                    "Dry/Wet updated: score=%.1f winrate=%.1f%% pf=%.2f dd=%.2f trades=%d",
                    params.get("dry_wet_score", 0),
                    params.get("winrate", 0) * 100,
                    params.get("profit_factor", 0),
                    params.get("max_drawdown", 0),
                    params.get("window_trades", 0),
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error in Dry/Wet update loop: %s", exc, exc_info=True)
        time.sleep(interval)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "dry_wet"}), 200


@app.route("/status", methods=["GET"])
def status():
    if not current_params:
        return jsonify({"status": "initializing"}), 503
    return jsonify({"status": "active", **current_params}), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(REGISTRY), 200, {"Content-Type": "text/plain"}


def run_service():
    init_redis()
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    port = int(os.getenv("ADAPTIVE_PORT", "8004"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":  # pragma: no cover
    run_service()
