"""
Execution Service - Main Entry Point
Claire de Binare Trading Bot
"""

import os
import json
import copy
import signal
import sys
import logging
import logging.config
import math
import time
from datetime import datetime
from pathlib import Path
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
import redis
from threading import Thread, Lock

from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_payload
from core.utils.uuid_gen import generate_uuid_hex
from core.utils.trace_toggle import trace_contract_v1_enabled
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
    "shadow_blocked": 0,  # LR-030: distinct evidence trail for shadow-mode blocks
    "invalid_payloads": 0,
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


def _mark_invalid_payload(reason: str, *, exc: Exception | None = None) -> None:
    """Track malformed input payloads without side effects."""
    increment_stat("invalid_payloads")
    if exc is not None:
        logger.warning("Invalid order payload skipped: %s (%s)", reason, exc)
        return
    logger.warning("Invalid order payload skipped: %s", reason)


def _validate_optional_json_object_field(payload: dict, field_name: str) -> None:
    """Validate optional JSON-string/object fields used by order contract."""
    if field_name not in payload:
        return

    raw_value = payload.get(field_name)
    if raw_value is None:
        return

    if isinstance(raw_value, dict):
        return

    if isinstance(raw_value, str):
        parsed = json.loads(raw_value)
        if not isinstance(parsed, dict):
            raise ValueError(f"Field '{field_name}' must encode a JSON object")
        return

    raise ValueError(f"Field '{field_name}' must be dict or JSON object string")


def _parse_optional_int(value) -> int | None:
    """Parse optional integer-like values without inventing replacements."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_metadata(value):
    if isinstance(value, dict):
        compacted = {}
        for key, item in value.items():
            if item is None:
                continue
            nested = _compact_metadata(item)
            if nested in (None, {}, []):
                continue
            compacted[key] = nested
        return compacted
    return value


def _compute_slippage_bps(expected_price, execution_price) -> float | None:
    try:
        expected = float(expected_price)
        actual = float(execution_price)
    except (TypeError, ValueError):
        return None
    if expected <= 0 or not math.isfinite(expected) or not math.isfinite(actual):
        return None
    return abs(actual - expected) / expected * 10000.0


def _build_result_metadata(order: Order, result: ExecutionResult) -> dict:
    metadata = copy.deepcopy(order.metadata) if isinstance(order.metadata, dict) else {}
    timing = metadata.get("timing") if isinstance(metadata.get("timing"), dict) else {}
    freshness = (
        metadata.get("freshness") if isinstance(metadata.get("freshness"), dict) else {}
    )
    timestamps_ms = (
        freshness.get("timestamps_ms")
        if isinstance(freshness.get("timestamps_ms"), dict)
        else {}
    )
    market_context = metadata.get("market_context", {})
    expected_price = getattr(order, "price", None)
    signal_ts_ms = _parse_optional_int(timing.get("signal_ts_ms"))
    if signal_ts_ms is None:
        signal_ts_ms = _parse_optional_int(timestamps_ms.get("signal_ts_ms"))

    fill_context = {
        "signal_ts_ms": signal_ts_ms,
        "decision_ts_ms": _parse_optional_int(timestamps_ms.get("now_ms")),
        "market_state_ts_ms": _parse_optional_int(
            timestamps_ms.get("market_state_ts_ms")
        ),
    }
    if signal_ts_ms is None:
        logger.warning(
            "Order %s missing canonical signal_ts_ms in metadata; fill_context will stay explicit null",
            order.order_id or order.client_id or "UNKNOWN_ORDER",
        )

    metadata.update(
        _compact_metadata(
            {
                "signal_id": order.signal_id,
                "strategy_id": order.strategy_id,
                "decision_id": order.decision_id,
                "trace_id": order.trace_id,
                "order_id": order.order_id,
                "exchange_order_id": result.order_id,
                "exchange_trade_id": result.fill_id,
                "regime_id": market_context.get("regime_id"),
                "expected_price": expected_price,
                "execution_price": result.price,
                "slippage_bps": _compute_slippage_bps(expected_price, result.price),
            }
        )
    )
    metadata["fill_context"] = fill_context
    return metadata


def _parse_order_payload(order_data: object) -> Order | None:
    """Return validated Order or None for invalid payload input."""
    if not isinstance(order_data, dict):
        _mark_invalid_payload(f"payload_type={type(order_data).__name__}")
        return None

    try:
        sanitized_payload = sanitize_payload(order_data)
    except (TypeError, ValueError) as exc:
        _mark_invalid_payload("sanitize_failed", exc=exc)
        return None

    event_type = sanitized_payload.get("type")
    if event_type not in (None, "order"):
        _mark_invalid_payload(f"unexpected_type={event_type}")
        return None

    try:
        _validate_optional_json_object_field(sanitized_payload, "policy_snapshot")
        _validate_optional_json_object_field(sanitized_payload, "metadata")
        order = Order.from_event(sanitized_payload)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        _mark_invalid_payload("order_parse_failed", exc=exc)
        return None

    if not math.isfinite(order.quantity):
        _mark_invalid_payload("quantity_not_finite")
        return None
    if order.quantity <= 0:
        _mark_invalid_payload("quantity_non_positive")
        return None

    return order


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
            dry_run = config.DRY_RUN if hasattr(config, "DRY_RUN") else True
            testnet = config.MEXC_TESTNET if hasattr(config, "MEXC_TESTNET") else False
            if not dry_run and (not config.MEXC_API_KEY or not config.MEXC_API_SECRET):
                raise RuntimeError(
                    "Missing MEXC API credentials for live trading. Set MEXC_API_KEY/MEXC_API_SECRET or enable DRY_RUN."
                )
            executor = LiveExecutor(
                api_key=config.MEXC_API_KEY or None,
                api_secret=config.MEXC_API_SECRET or None,
                testnet=testnet,
                dry_run=dry_run,
            )

            if dry_run:
                logger.warning(
                    "🔶 Live Executor in DRY RUN mode - orders logged but not executed"
                )
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
    stream_payload = {
        key: value for key, value in event_payload.items() if value is not None
    }
    if "filled_quantity" in stream_payload and "filled_size" not in stream_payload:
        stream_payload["filled_size"] = stream_payload["filled_quantity"]
    if "price" in stream_payload and "avg_fill_price" not in stream_payload:
        stream_payload["avg_fill_price"] = stream_payload["price"]

    streams: list[str] = []
    if config.STREAM_ORDER_RESULTS:
        streams.append(config.STREAM_ORDER_RESULTS)
    if "stream.order_results" not in streams:
        streams.append("stream.order_results")

    for stream in streams:
        redis_client.xadd(stream, stream_payload, maxlen=10000)
        logger.info("Published result to stream %s", stream)
    logger.info(f"Published result to {config.TOPIC_ORDER_RESULTS}")

    if db:
        db.save_order(result)
        if ExecutionResult._schema_status(result.status) == "FILLED":
            db.save_trade(result)


def process_order(order_data: object):
    """Process incoming order."""
    order = _parse_order_payload(order_data)
    if order is None:
        return None

    try:
        increment_stat("orders_received")  # Thread-safe

        # Safety gate: reject orders without Risk Service approval (refs #467)
        # Only enforced when Trace Contract v1 is active (toggle ON).
        if trace_contract_v1_enabled() and not order.decision_id:
            result = ExecutionResult(
                order_id=order.order_id or "MISSING_ORDER_ID",
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=order.client_id,
                error_message="Order rejected: missing decision_id (not approved by Risk Service)",
                timestamp=utcnow().isoformat(),
                strategy_id=order.strategy_id,
                bot_id=order.bot_id,
            )
            result.metadata = _build_result_metadata(order, result)
            logger.warning(
                "REJECTED (no decision_id): %s %s qty=%.4f",
                order.symbol,
                order.side,
                order.quantity,
            )
            increment_stat("orders_rejected")
            _publish_result(result)
            return result

        # LR-030: Shadow-mode execution gate (always active, not toggle-gated).
        # Orders with run_mode="shadow" MUST NOT reach any executor.
        # run_mode=None passes (backward compat for legacy orders).
        if order.run_mode == "shadow":
            result = ExecutionResult(
                order_id=order.order_id or "SHADOW_BLOCKED",
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=order.client_id,
                error_message="Order blocked: shadow mode (zero execution)",
                timestamp=utcnow().isoformat(),
                strategy_id=order.strategy_id,
                bot_id=order.bot_id,
            )
            result.metadata = _build_result_metadata(order, result)
            logger.warning(
                "SHADOW-BLOCKED: %s %s qty=%.4f (run_mode=shadow, zero execution)",
                order.symbol,
                order.side,
                order.quantity,
            )
            increment_stat("orders_rejected")
            increment_stat("shadow_blocked")
            _publish_result(result)
            return result

        # LR-030: Kill-switch gate in Execution Service (defense-in-depth).
        # Consistent with process_order() fail-closed convention: the outer
        # try/except already returns None on unexpected errors.
        try:
            from core.safety.kill_switch import get_kill_switch_details

            ks_active, ks_reason, _ks_msg, _ks_at = get_kill_switch_details(
                create_if_missing=False
            )
        except Exception:
            ks_active, ks_reason = True, "evaluation_error"  # fail-closed

        if ks_active:
            result = ExecutionResult(
                order_id=order.order_id or "KILL_SWITCH_BLOCKED",
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=order.client_id,
                error_message=f"Order blocked: kill-switch active ({ks_reason})",
                timestamp=utcnow().isoformat(),
                strategy_id=order.strategy_id,
                bot_id=order.bot_id,
            )
            result.metadata = _build_result_metadata(order, result)
            logger.warning(
                "KILL-SWITCH-BLOCKED in execution: %s %s reason=%s",
                order.symbol,
                order.side,
                ks_reason,
            )
            increment_stat("orders_rejected")
            _publish_result(result)
            return result

        if (
            bot_shutdown_active
            or (order.strategy_id and order.strategy_id in blocked_strategy_ids)
            or (order.bot_id and order.bot_id in blocked_bot_ids)
        ):
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
            result.metadata = _build_result_metadata(order, result)
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
        result.metadata = _build_result_metadata(order, result)

        # Phase 8C/8E: Persist ORDER and FILL events to correlation_ledger
        # order_id ist jetzt final (von executor zurückgegeben)
        # Correlation write failures must NOT prevent order_results publish.
        if db:
            try:
                timestamp_ms = int(time.time() * 1000)
                schema_status = ExecutionResult._schema_status(result.status)

                # ORDER event (always persisted)
                order_payload = {
                    "signal_id": order.signal_id,
                    "decision_id": order.decision_id,
                    "order_id": result.order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "strategy_id": order.strategy_id,
                    "trace_id": order.trace_id,
                }
                # Phase 9: Trace Contract v1 - Policy governance (conditional)
                if getattr(order, "policy_id", None) is not None:
                    order_payload["policy_id"] = order.policy_id
                if getattr(order, "policy_hash", None) is not None:
                    order_payload["policy_hash"] = order.policy_hash
                if getattr(order, "input_hash", None) is not None:
                    order_payload["input_hash"] = order.input_hash
                if getattr(order, "output_hash", None) is not None:
                    order_payload["output_hash"] = order.output_hash
                if not db.persist_correlation_event(
                    signal_id=order.signal_id,
                    event_type="ORDER",
                    symbol=order.symbol,
                    timestamp_ms=timestamp_ms,
                    decision_id=order.decision_id,
                    order_id=result.order_id,
                    payload=order_payload,
                ):
                    logger.warning(
                        "⚠️ correlation_ledger ORDER write failed (evidence debt)"
                    )

                # Phase 8E: FILL event (only for fully filled orders, same timestamp_ms)
                if schema_status == "FILLED" and result.fill_id:
                    fill_payload = {
                        "signal_id": order.signal_id,
                        "decision_id": order.decision_id,
                        "order_id": result.order_id,
                        "fill_id": result.fill_id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "filled_quantity": result.filled_quantity,
                        "price": result.price,
                        "strategy_id": order.strategy_id,
                        "trace_id": order.trace_id,
                    }
                    # Phase 9: Trace Contract v1 - Policy governance (conditional)
                    if getattr(order, "policy_id", None) is not None:
                        fill_payload["policy_id"] = order.policy_id
                    if getattr(order, "policy_hash", None) is not None:
                        fill_payload["policy_hash"] = order.policy_hash
                    if getattr(order, "input_hash", None) is not None:
                        fill_payload["input_hash"] = order.input_hash
                    if getattr(order, "output_hash", None) is not None:
                        fill_payload["output_hash"] = order.output_hash
                    if not db.persist_correlation_event(
                        signal_id=order.signal_id,
                        event_type="FILL",
                        symbol=order.symbol,
                        timestamp_ms=timestamp_ms,
                        decision_id=order.decision_id,
                        order_id=result.order_id,
                        fill_id=result.fill_id,
                        payload=fill_payload,
                    ):
                        logger.warning(
                            "⚠️ correlation_ledger FILL write failed (evidence debt)"
                        )
            except ValueError as corr_err:
                logger.warning(
                    "correlation_ledger write skipped for order %s: %s",
                    result.order_id,
                    corr_err,
                )

        # LR-021 Slice 2: FILL envelope emission (toggle-gated, default OFF)
        try:
            _cdb_val = os.getenv("CDB_ENVELOPE_EMISSION")
            _lr021_emit = (
                (_cdb_val == "1")
                if _cdb_val is not None
                else os.getenv("LR021_ENVELOPE_EMIT_ENABLED", "0") == "1"
            )
        except Exception:
            _lr021_emit = False
        if (
            _lr021_emit
            and ExecutionResult._schema_status(result.status) == "FILLED"
            and getattr(result, "fill_id", None)
        ):
            try:
                from core.replay.emitter import emit_fill_envelope

                emit_fill_envelope(
                    event_id=str(result.fill_id),
                    ts_ms=timestamp_ms,
                    order_id=str(result.order_id),
                    fill_id=str(result.fill_id),
                    symbol=str(result.symbol),
                    side=str(result.side),
                    filled_quantity=float(result.filled_quantity),
                    price=float(result.price) if result.price is not None else None,
                    signal_id=getattr(order, "signal_id", None),
                    trace_id=getattr(order, "trace_id", None),
                    status=ExecutionResult._schema_status(result.status),
                    policy_id=getattr(order, "policy_id", None),
                    policy_hash=getattr(order, "policy_hash", None),
                    input_hash=getattr(order, "input_hash", None),
                    output_hash=getattr(order, "output_hash", None),
                    policy_snapshot=getattr(order, "policy_snapshot", None),
                )
            except Exception:
                pass  # Guardrail: never break execution path

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
    except Exception as exc:
        logger.error("Error processing order: %s", exc)
        increment_stat("orders_rejected")  # Thread-safe
        return None


def message_loop():
    """Listen for orders from Redis"""
    global running

    logger.info("Starting message loop...")

    while running:
        try:
            message = pubsub.get_message(timeout=1.0)

            if message and message.get("type") == "message":
                try:
                    raw_data = message.get("data")
                    if raw_data is None:
                        _mark_invalid_payload("missing_message_data")
                        continue
                    order_data = json.loads(raw_data)
                    process_order(order_data)
                except json.JSONDecodeError as exc:
                    _mark_invalid_payload("json_decode_failed", exc=exc)
                except Exception as exc:
                    logger.error("Error handling message: %s", exc)

        except Exception as exc:
            logger.error("Error in message loop: %s", exc)
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


# ===== FLASK ENDPOINTS =====

if _FLASK_AVAILABLE:
    from flask import Flask, jsonify, Response

    app = Flask(__name__)

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
            "# HELP execution_invalid_payloads_total Anzahl invalid/malformed Payloads\n"
            "# TYPE execution_invalid_payloads_total counter\n"
            f"execution_invalid_payloads_total {current_stats['invalid_payloads']}\n"
            "# HELP execution_shadow_blocked_total Orders blocked by shadow mode gate (LR-030)\n"
            "# TYPE execution_shadow_blocked_total counter\n"
            f"execution_shadow_blocked_total {current_stats['shadow_blocked']}\n"
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

else:
    app = None


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False


def _require_live_confirmation() -> None:
    """
    Sicherheitsprüfung für Live-Trading.
    Erfordert explizite Bestätigung, wenn echtes Geld (Mainnet + Live Executor) im Spiel ist.
    """
    # Sicherer Modus, wenn:
    # 1. MOCK_TRADING aktiv ist (MockExecutor wird verwendet)
    # 2. DRY_RUN aktiv ist (LiveExecutor loggt nur, führt nicht aus)
    # 3. MEXC_TESTNET aktiv ist (Testnet, kein echtes Geld)
    if config.MOCK_TRADING or config.DRY_RUN or config.MEXC_TESTNET:
        return

    # Nur wenn alle oben genannten Sicherheitsnetze deaktiviert sind,
    # ist es eine ECHTE Live-Umgebung auf dem Mainnet.
    confirmation = os.getenv("CONFIRM_LIVE_TRADING", "").lower().strip()
    if confirmation != "true":
        logger.critical("🚨 LIVE TRADING SAFETY GATE TRIGGERED 🚨")
        logger.critical("Sie versuchen, auf dem MAINNET ohne MOCK/DRY-RUN zu traden!")
        logger.critical("Setzen Sie CONFIRM_LIVE_TRADING=true, um fortzufahren.")
        logger.critical(
            "Aktuelle Konfiguration: DRY_RUN=%s, MOCK_TRADING=%s, TESTNET=%s",
            config.DRY_RUN,
            config.MOCK_TRADING,
            config.MEXC_TESTNET,
        )
        sys.exit(1)


def main():
    """Main entry point"""
    global running

    logger.info(f"Starting {config.SERVICE_NAME} v{config.SERVICE_VERSION}")
    logger.info(f"Port: {config.SERVICE_PORT}")
    logger.info(f"Mode: {'MOCK' if config.MOCK_TRADING else 'LIVE'}")
    logger.info(
        "Trading config: TRADING_MODE=%s DRY_RUN=%s MOCK_TRADING=%s",
        os.getenv("TRADING_MODE", "(unset)"),
        config.DRY_RUN,
        config.MOCK_TRADING,
    )

    _require_live_confirmation()

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
    if not _FLASK_AVAILABLE or app is None:
        raise RuntimeError(
            "Flask ist nicht installiert. HTTP-Endpoints (health/status/metrics) "
            "benötigen Flask als optionale Abhängigkeit: pip install flask"
        )
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
