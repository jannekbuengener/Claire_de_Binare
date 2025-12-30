"""
WebSocket Service - Feature Flag Integration

Modes (controlled by WS_SOURCE env):
- stub (default): Health endpoint only, no external connections
- mexc_pb: MEXC WebSocket V3 Protobuf client

Port: 8000
Dependencies: Redis (market_data publisher)
"""

import asyncio
import json
import logging
import os
import sys
import threading
from flask import Flask, jsonify
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import redis

from mexc_v3_client import MexcV3Client
from core.utils.redis_payload import sanitize_market_data

# Basic logging setup
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] ws_service: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Flask app for health/metrics endpoints
app = Flask(__name__)

# Global state
ws_client = None
ws_mode = None
redis_client = None

# Prometheus metrics
decoded_messages_total = Gauge("decoded_messages_total", "Total decoded WS messages")
decode_errors_total = Gauge("decode_errors_total", "Total WS decode errors")
ws_connected = Gauge("ws_connected", "WS connection status (0/1)")
last_message_ts_ms = Gauge("last_message_ts_ms", "Last message timestamp (ms)")
redis_publish_total = Counter("redis_publish_total", "Total Redis publishes")
redis_publish_errors_total = Counter("redis_publish_errors_total", "Redis publish errors")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint required by Docker HEALTHCHECK"""
    health_data = {
        "status": "healthy",
        "service": "websocket",
        "mode": ws_mode or "stub",
    }

    if ws_client:
        metrics = ws_client.get_metrics()
        health_data["ws_connected"] = metrics["ws_connected"]
        health_data["last_message_ts_ms"] = metrics["last_message_ts_ms"]

        # Calculate message age
        if metrics["last_message_ts_ms"] > 0:
            import time
            now_ms = int(time.time() * 1000)
            health_data["last_message_age_ms"] = now_ms - metrics["last_message_ts_ms"]
        else:
            health_data["last_message_age_ms"] = None

    # Redis status
    if redis_client:
        try:
            redis_client.ping()
            health_data["redis_connected"] = True
        except Exception:
            health_data["redis_connected"] = False
    else:
        health_data["redis_connected"] = False

    return jsonify(health_data), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics endpoint"""
    client = ws_client  # Local copy, reduces race risk
    if client is not None:
        m = client.get_metrics()
        decoded_messages_total.set(m.get("decoded_messages_total", 0))
        decode_errors_total.set(m.get("decode_errors_total", 0))
        ws_connected.set(m.get("ws_connected", 0))
        last_message_ts_ms.set(m.get("last_message_ts_ms", 0))
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


def start_flask_server():
    """Start Flask server in background thread"""
    logger.info("Starting Flask health endpoint on port 8000...")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True, use_reloader=False)


async def run_mexc_client():
    """Start MEXC WebSocket client"""
    global ws_client, redis_client

    symbol = os.getenv("MEXC_SYMBOL", "BTCUSDT")
    interval = os.getenv("MEXC_INTERVAL", "100ms")
    ping_interval = int(os.getenv("WS_PING_INTERVAL", "20"))
    reconnect_max = int(os.getenv("WS_RECONNECT_MAX", "10"))

    # Redis connection
    redis_host = os.getenv("REDIS_HOST", "cdb_redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD", "")

    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password else None,
            db=0,
            decode_responses=True,
        )
        redis_client.ping()
        logger.info(f"Redis connected: {redis_host}:{redis_port}")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        logger.error("Service will continue but market_data will NOT be published!")

    logger.info(f"Starting MEXC WS client: symbol={symbol}, interval={interval}")

    def on_trade(event):
        """Trade event callback: Publish to Redis market_data topic"""
        if redis_client:
            try:
                # Sanitize payload (Issue #349: None-filtering + contract v1.0 enforcement)
                sanitized = sanitize_market_data(event)
                message = json.dumps(sanitized)
                redis_client.publish("market_data", message)
                redis_publish_total.inc()
                logger.debug(f"[redis] published market_data: {event['symbol']} @ {event['price']}")
            except Exception as e:
                redis_publish_errors_total.inc()
                logger.error(f"[redis] publish error: {e}")
        else:
            logger.warning(f"[redis] not connected, dropping trade: {event}")

    ws_client = MexcV3Client(
        symbol=symbol,
        interval=interval,
        on_trade=on_trade,
        ping_interval=ping_interval,
        reconnect_max=reconnect_max,
    )

    await ws_client.run()


def main():
    """
    Main service entry point.

    Modes:
    - WS_SOURCE=stub (default): Health endpoint only
    - WS_SOURCE=mexc_pb: MEXC WebSocket V3 Protobuf client
    """
    global ws_mode
    ws_mode = os.getenv("WS_SOURCE", "stub").lower()

    logger.info("=" * 60)
    logger.info(f"WEBSOCKET SERVICE - MODE: {ws_mode}")
    logger.info("=" * 60)

    # Start Flask server in background thread
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()

    if ws_mode == "stub":
        logger.info("STUB mode: No external WS connections")
        logger.info("Health endpoint available at http://0.0.0.0:8000/health")
        logger.info("Press Ctrl+C to stop")

        # Keep alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Service stopped by user")

    elif ws_mode == "mexc_pb":
        logger.info("MEXC Protobuf mode: Starting WS client")

        # Run async client
        try:
            asyncio.run(run_mexc_client())
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            if ws_client:
                ws_client.stop()

    else:
        logger.error(f"Unknown WS_SOURCE mode: {ws_mode}")
        logger.error("Valid modes: stub, mexc_pb")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Service crashed: {e}", exc_info=True)
        sys.exit(1)
