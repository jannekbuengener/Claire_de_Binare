"""
Execution Service - Main Entry Point
Claire de Binare Trading Bot
"""

import os
import json
import signal
import sys
import logging
import logging.config
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, Response
import redis
from threading import Thread, Lock

from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_payload
from core.utils.uuid_gen import generate_uuid_hex
from core.auth import validate_all_auth
try:
    from . import config
    from .models import Order, ExecutionResult, OrderStatus
    from .mock_executor import MockExecutor
    from .live_executor import LiveExecutor
    from .database import Database
except ImportError:
    import config
    from models import Order, ExecutionResult, OrderStatus
    from mock_executor import MockExecutor
    from live_executor import LiveExecutor
    from database import Database

# Logging setup mit zentraler Konfiguration
# Im Container ist logging_config.json nicht verfügbar, daher Fallback
logging_config_path = Path("/app/logging_config.json")  # Falls gemountet
if not logging_config_path.exists():
    # Versuche relative Pfade für lokale Entwicklung
    logging_config_path = (
        Path(__file__).resolve().parent.parent.parent / "logging_config.json"
    )

if logging_config_path.exists():
    with open(logging_config_path) as cfg_file:
        logging_conf = json.load(cfg_file)
        logging.config.dictConfig(logging_conf)
else:
    # Fallback zu basicConfig (Issue #347 - Dev vs Prod logging policy)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(config.SERVICE_NAME)

# Flask app
app = Flask(__name__)

# Global state
executor = None
redis_client = None
pubsub = None
db = None
running = True

# Thread-safe stats with lock (Fix for Issue #306)
_stats_lock = Lock()
stats = {
    "orders_received": 0,
    "orders_filled": 0,
    "orders_rejected": 0,
    "start_time": utcnow().isoformat(),
    "last_result": None,
}

# Thread-safe sets with lock (Fix for Issue #306)
_orders_lock = Lock()
bot_shutdown_active = False
blocked_strategy_ids = set()
blocked_bot_ids = set()
open_orders = set()


def increment_stat(key: str, value: int = 1) -> None:
    """Thread-safe stats increment"""
    with _stats_lock:
        stats[key] += value


def set_stat(key: str, value) -> None:
    """Thread-safe stats set"""
    with _stats_lock:
        stats[key] = value


def get_stats_copy() -> dict:
    """Thread-safe stats read"""
    with _stats_lock:
        return stats.copy()


def _init_with_retry(
    name: str, factory, retries: int = 3, delay: float = config.RETRY_DELAY_SECONDS
) -> object:
    """Initialisiert eine Komponente mit Retry-Logik"""
    for attempt in range(1, retries + 1):
        try:
            return factory()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "%s Initialisierung fehlgeschlagen (%s/%s): %s",
                name,
                attempt,
                retries,
                exc,
            )
            if attempt == retries:
                raise
            time.sleep(delay)


def init_services():
    """Initialize Redis, Executor and Database"""
    global redis_client, pubsub, executor, db

    try:

        def _create_redis_client():
            client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD or None,
                db=config.REDIS_DB,
                decode_responses=True,
            )
            client.ping()
            return client

        # Redis connection
        redis_client = _init_with_retry("Redis", _create_redis_client, retries=5)
        logger.info(f"Connected to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}")

        # Subscribe to orders topic
        pubsub = redis_client.pubsub()
        pubsub.subscribe(config.TOPIC_ORDERS)
        logger.info(f"Subscribed to topic: {config.TOPIC_ORDERS}")

        # Initialize executor - LIVE DATA CONVERSION
        if config.MOCK_TRADING:
            executor = MockExecutor()
            logger.info("🟢 Using MockExecutor (Paper Trading Mode)")
        else:
            # Real MEXC executor with enhanced capabilities
            try:
                from .mexc_executor import MexcExecutor
                executor = MexcExecutor()
                logger.info("Using MexcExecutor (LIVE TRADING MODE - REAL DATA)")
            except ImportError:
                # Fallback to LiveExecutor
                dry_run = config.DRY_RUN if hasattr(config, "DRY_RUN") else True
                testnet = config.MEXC_TESTNET if hasattr(config, "MEXC_TESTNET") else False
                executor = LiveExecutor(testnet=testnet, dry_run=dry_run)
                
                if dry_run:
                    logger.warning("🔶 Live Executor in DRY RUN mode - orders logged but not executed")
                else:
                    mode = "TESTNET" if testnet else "LIVE"
                    logger.warning(f"🔴 Live Executor in {mode} mode - REAL MONEY!")

        # Initialize database
        db = _init_with_retry(
            "PostgreSQL", Database, retries=3, delay=config.RETRY_DELAY_SECONDS * 2
        )
        logger.info("Database initialized")

        return True

    except Exception as e:
        logger.exception("Failed to initialize services: %s", e)
        return False


def _publish_result(result: ExecutionResult) -> None:
    """Publish order result to Redis (pubsub + stream) and persist to DB."""
    event_payload = sanitize_payload(result.to_dict())
    set_stat("last_result", event_payload)  # Thread-safe
    if not redis_client:
        raise RuntimeError("Redis client not initialised")

    redis_client.publish(
        config.TOPIC_ORDER_RESULTS, json.dumps(event_payload, ensure_ascii=False)
    )
    if config.STREAM_ORDER_RESULTS:
        redis_client.xadd(config.STREAM_ORDER_RESULTS, event_payload, maxlen=10000)
    logger.info(f"Published result to {config.TOPIC_ORDER_RESULTS}")

    if db:
        db.save_order(result)
        if ExecutionResult._schema_status(result.status) == "FILLED":
            db.save_trade(result)


def process_order(order_data: dict):
    """Process incoming order"""
    try:
        if order_data.get("type") not in (None, "order"):
            logger.warning(
                "Ignoriere Event mit unerwartetem Typ: %s", order_data.get("type")
            )
            return None

        order = Order.from_event(order_data)

        increment_stat("orders_received")  # Thread-safe

        if bot_shutdown_active or (
            order.strategy_id and order.strategy_id in blocked_strategy_ids
        ) or (order.bot_id and order.bot_id in blocked_bot_ids):
            shutdown_id = generate_uuid_hex(
                name=f"shutdown:{order.symbol}:{order.side}:{order.quantity}:{utcnow().isoformat()}"
            )
            result = ExecutionResult(
                order_id=f"SHUTDOWN_{shutdown_id}",
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=order.client_id,
                error_message="Order blocked by bot shutdown",
                timestamp=utcnow().isoformat(),
                strategy_id=order.strategy_id,
                bot_id=order.bot_id,
            )
            increment_stat("orders_rejected")  # Thread-safe
            _publish_result(result)
            return result

        logger.info(
            "Processing order: %s %s qty=%.4f",
            order.symbol,
            order.side,
            order.quantity,
        )

        if executor is None:
            raise RuntimeError("Executor not initialised")

        # Execute order
        result = executor.execute_order(order)
        if result is None:
            raise RuntimeError("Executor returned no result")

        result.strategy_id = order.strategy_id
        result.bot_id = order.bot_id

        # Update stats (Thread-safe)
        schema_status = ExecutionResult._schema_status(result.status)
        if schema_status == "FILLED":
            increment_stat("orders_filled")
            logger.info("Order filled: %s at %s", result.order_id, result.price)
        else:
            increment_stat("orders_rejected")
            logger.warning(
                "Order rejected: %s - %s", result.order_id, result.error_message
            )

        _publish_result(result)

        return result
    except (KeyError, ValueError) as err:
        logger.error("Fehlerhafte Orderdaten: %s", err)
        increment_stat("orders_rejected")  # Thread-safe
        return None
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        increment_stat("orders_rejected")  # Thread-safe
        return None


def message_loop():
    """Listen for orders from Redis"""
    global running

    logger.info("Starting message loop...")

    while running:
        try:
            message = pubsub.get_message(timeout=1.0)

            if message and message["type"] == "message":
                try:
                    order_data = json.loads(message["data"])
                    process_order(order_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except Exception as e:
            logger.error(f"Error in message loop: {e}")
            time.sleep(1)

    logger.info("Message loop stopped")


def _handle_bot_shutdown(payload: dict) -> None:
    """Handle bot shutdown events with safety priority."""
    global bot_shutdown_active

    strategy_id = payload.get("strategy_id")
    bot_id = payload.get("bot_id")
    if strategy_id:
        blocked_strategy_ids.add(strategy_id)
    if bot_id:
        blocked_bot_ids.add(bot_id)

    bot_shutdown_active = True
    logger.warning(
        "Bot shutdown active (strategy_id=%s, bot_id=%s, reason=%s)",
        strategy_id,
        bot_id,
        payload.get("reason"),
    )

    if executor:
        for order_id in list(open_orders):
            try:
                executor.cancel_order(order_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Cancel failed for %s: %s", order_id, exc)
        open_orders.clear()


def listen_bot_shutdown():
    """Listen for bot shutdown events from Redis stream."""
    if not redis_client or not config.STREAM_BOT_SHUTDOWN:
        return

    last_id = "0-0"
    while running:
        try:
            response = redis_client.xread(
                {config.STREAM_BOT_SHUTDOWN: last_id}, block=1000, count=10
            )
            if not response:
                continue
            for _, entries in response:
                for entry_id, payload in entries:
                    last_id = entry_id
                    _handle_bot_shutdown(payload)
        except Exception as exc:  # noqa: BLE001
            logger.error("Bot shutdown stream error: %s", exc)
            time.sleep(1)


# Health Check Endpoint
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "service": config.SERVICE_NAME,
                "status": "ok",
                "version": config.SERVICE_VERSION,
            }
        ),
        200,
    )


@app.route("/status", methods=["GET"])
def status():
    """Status endpoint with statistics"""
    try:
        redis_connected = redis_client.ping() if redis_client else False
    except Exception:
        redis_connected = False

    return (
        jsonify(
            {
                "service": config.SERVICE_NAME,
                "version": config.SERVICE_VERSION,
                "mode": "mock" if config.MOCK_TRADING else "live",
                "stats": stats,
                "redis": {"connected": redis_connected},
                "database": db.get_stats() if db else {"error": "not initialized"},
            }
        ),
        200,
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    """Metrics endpoint for Prometheus"""
    # Thread-safe stats read (Fix for Issue #306)
    current_stats = get_stats_copy()

    uptime_seconds = max(
        0.0,
        (
            utcnow() - datetime.fromisoformat(current_stats["start_time"])
        ).total_seconds(),
    )

    body = (
        "# HELP execution_orders_received_total Anzahl eingegangener Orders\n"
        "# TYPE execution_orders_received_total counter\n"
        f"execution_orders_received_total {current_stats['orders_received']}\n"
        "# HELP execution_orders_filled_total Anzahl erfolgreich ausgefuehrter Orders\n"
        "# TYPE execution_orders_filled_total counter\n"
        f"execution_orders_filled_total {current_stats['orders_filled']}\n"
        "# HELP execution_orders_rejected_total Anzahl abgelehnter Orders\n"
        "# TYPE execution_orders_rejected_total counter\n"
        f"execution_orders_rejected_total {current_stats['orders_rejected']}\n"
        "# HELP execution_uptime_seconds Service Laufzeit in Sekunden\n"
        "# TYPE execution_uptime_seconds gauge\n"
        f"execution_uptime_seconds {uptime_seconds}\n"
    )

    return Response(body, mimetype="text/plain")


@app.route("/orders", methods=["GET"])
def orders():
    """Get recent orders from database"""
    if not db:
        return jsonify({"error": "Database not initialized"}), 503

    try:
        recent_orders = db.get_recent_orders(limit=20)
        return jsonify({"count": len(recent_orders), "orders": recent_orders}), 200
    except Exception as e:
        logger.error(f"Error retrieving orders: {e}")
        return jsonify({"error": str(e)}), 500


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False


def main():
    """Main entry point"""
    global running

    logger.info(f"Starting {config.SERVICE_NAME} v{config.SERVICE_VERSION}")
    logger.info(f"Port: {config.SERVICE_PORT}")
    logger.info(f"Mode: {'MOCK' if config.MOCK_TRADING else 'LIVE'}")

    # Validate auth credentials before startup
    validate_all_auth(
        config.REDIS_HOST,
        config.REDIS_PORT,
        config.REDIS_PASSWORD,
        config.POSTGRES_HOST,
        config.POSTGRES_PORT,
        config.POSTGRES_USER,
        config.POSTGRES_PASSWORD,
        config.POSTGRES_DB,
    )

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize services
    if not init_services():
        logger.error("Failed to initialize services, exiting")
        sys.exit(1)

    # Start message loop in background
    message_thread = Thread(target=message_loop, daemon=True)
    message_thread.start()
    logger.info("Message loop started")
    shutdown_thread = Thread(target=listen_bot_shutdown, daemon=True)
    shutdown_thread.start()
    logger.info("Bot-shutdown listener started")

    # Start Flask app
    try:
        app.run(
            host="0.0.0.0", port=config.SERVICE_PORT, debug=False, use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        running = False
        if pubsub:
            pubsub.close()
        if redis_client:
            redis_client.close()
        logger.info("Service stopped")


if __name__ == "__main__":
    main()
