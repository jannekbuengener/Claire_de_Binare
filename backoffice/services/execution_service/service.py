"""
Execution Service - Main Entry Point
Claire de Binare Trading Bot
"""

import json
import signal
import sys
import logging
import logging.config
import time
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, Response
import redis
from threading import Thread

try:
    from . import config
    from .models import Order, ExecutionResult
    from .mock_executor import MockExecutor
    from .database import Database
except ImportError:
    import config
    from models import Order, ExecutionResult
    from mock_executor import MockExecutor
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
    # Fallback zu basicConfig
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
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
stats = {
    "orders_received": 0,
    "orders_filled": 0,
    "orders_rejected": 0,
    "start_time": datetime.now(timezone.utc).isoformat(),
    "last_result": None,
}


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

        # Initialize executor
        if config.MOCK_TRADING:
            executor = MockExecutor()
            logger.info("Using MockExecutor (Paper Trading Mode)")
        else:
            # TODO: Real MEXC executor
            logger.warning("Real trading not implemented yet, using MockExecutor")
            executor = MockExecutor()

        # Initialize database
        db = _init_with_retry(
            "PostgreSQL", Database, retries=3, delay=config.RETRY_DELAY_SECONDS * 2
        )
        logger.info("Database initialized")

        return True

    except Exception as e:
        logger.exception("Failed to initialize services: %s", e)
        return False


def process_order(order_data: dict):
    """Process incoming order"""
    global stats

    try:
        if order_data.get("type") not in (None, "order"):
            logger.warning(
                "Ignoriere Event mit unerwartetem Typ: %s", order_data.get("type")
            )
            return None

        order = Order.from_event(order_data)

        stats["orders_received"] += 1

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

        # Update stats
        schema_status = ExecutionResult._schema_status(result.status)
        if schema_status == "FILLED":
            stats["orders_filled"] += 1
            logger.info("Order filled: %s at %s", result.order_id, result.price)
        else:
            stats["orders_rejected"] += 1
            logger.warning(
                "Order rejected: %s - %s", result.order_id, result.error_message
            )

        # Publish result
        event_payload = result.to_dict()
        stats["last_result"] = event_payload
        if not redis_client:
            raise RuntimeError("Redis client not initialised")

        redis_client.publish(
            config.TOPIC_ORDER_RESULTS, json.dumps(event_payload, ensure_ascii=False)
        )
        logger.info(f"Published result to {config.TOPIC_ORDER_RESULTS}")

        # Save to PostgreSQL
        if db:
            db.save_order(result)
            if schema_status == "FILLED":
                db.save_trade(result)

        return result
    except (KeyError, ValueError) as err:
        logger.error("Fehlerhafte Orderdaten: %s", err)
        stats["orders_rejected"] += 1
        return None
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        stats["orders_rejected"] += 1
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
    uptime_seconds = max(
        0.0,
        (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(stats["start_time"])
        ).total_seconds(),
    )

    body = (
        "# HELP execution_orders_received_total Anzahl eingegangener Orders\n"
        "# TYPE execution_orders_received_total counter\n"
        f"execution_orders_received_total {stats['orders_received']}\n"
        "# HELP execution_orders_filled_total Anzahl erfolgreich ausgefuehrter Orders\n"
        "# TYPE execution_orders_filled_total counter\n"
        f"execution_orders_filled_total {stats['orders_filled']}\n"
        "# HELP execution_orders_rejected_total Anzahl abgelehnter Orders\n"
        "# TYPE execution_orders_rejected_total counter\n"
        f"execution_orders_rejected_total {stats['orders_rejected']}\n"
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
