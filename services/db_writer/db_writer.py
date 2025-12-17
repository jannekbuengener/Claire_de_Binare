"""
DB Writer Service - Claire de Binare
Persistiert Events aus Redis in PostgreSQL

Funktionen:
- Signals → PostgreSQL (signals table)
- Orders → PostgreSQL (orders table)
- Trades → PostgreSQL (trades table)
- Portfolio Snapshots → PostgreSQL (portfolio_snapshots table)
"""

import os
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional

import redis
import psycopg2
from core.domain.secrets import get_secret

# Logging Setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_writer")

# Trade Status Definitions
# Only filled/partial trades are persisted to trades table
EXECUTION_STATUSES = {"filled", "partial", "partially_filled"}
NON_EXECUTION_STATUSES = {"rejected", "cancelled"}


class DatabaseWriter:
    """
    Database Writer Service

    Subscribes to Redis channels and persists events to PostgreSQL
    """

    def __init__(self):
        """Initialize DB Writer"""
        self.redis_host = os.getenv("REDIS_HOST", "cdb_redis")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = get_secret("redis_password", "REDIS_PASSWORD")
        logger.info(f"Redis password loaded: {'Yes' if self.redis_password else 'No'}")

        self.postgres_host = os.getenv("POSTGRES_HOST", "cdb_postgres")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "claire_de_binare")
        self.postgres_user = os.getenv("POSTGRES_USER", "claire_user")
        self.postgres_password = get_secret(
            "postgres_password", "POSTGRES_PASSWORD", ""
        )

        # Channels to subscribe to
        self.channels = ["signals", "orders", "order_results", "portfolio_snapshots"]

        # Connections
        self.redis_client = None
        self.db_conn = None
        self.pubsub = None

    @staticmethod
    def convert_timestamp(timestamp_value):
        """
        Convert timestamp to PostgreSQL-compatible format.

        Handles:
        - Unix timestamps (integers like 1763840671)
        - ISO strings (like "2025-11-22T12:00:00Z")
        - None (returns current UTC time)

        Args:
            timestamp_value: Unix timestamp (int), ISO string, or None

        Returns:
            datetime object compatible with PostgreSQL timestamp with time zone
        """
        if timestamp_value is None:
            return datetime.utcnow()

        # If integer (Unix timestamp), convert to datetime
        if isinstance(timestamp_value, int):
            return datetime.utcfromtimestamp(timestamp_value)

        # If string (ISO format), parse it
        if isinstance(timestamp_value, str):
            try:
                # Handle ISO format with 'Z' suffix
                if timestamp_value.endswith("Z"):
                    timestamp_value = timestamp_value[:-1] + "+00:00"
                return datetime.fromisoformat(timestamp_value)
            except ValueError:
                # Fallback to current time if parsing fails
                logger.warning(
                    f"Invalid timestamp format: {timestamp_value}, using current time"
                )
                return datetime.utcnow()

        # If already datetime, return as-is
        if isinstance(timestamp_value, datetime):
            return timestamp_value

        # Fallback
        logger.warning(
            f"Unknown timestamp type: {type(timestamp_value)}, using current time"
        )
        return datetime.utcnow()

    @staticmethod
    def normalize_side(value: str) -> str:
        """Normalize side strings to lowercase and handle missing values."""
        if value is None:
            return ""
        try:
            return str(value).lower()
        except Exception:  # pragma: no cover - defensive fallback
            return ""

    @staticmethod
    def normalize_exposure_pct(value) -> float:
        """Normalize exposure values sent either as decimal (0-1) or percentage (0-100)."""
        try:
            exposure = float(value)
        except (TypeError, ValueError):
            return 0.0

        if exposure > 1:
            logger.warning(
                "Portfolio snapshot total_exposure_pct looks like a percentage (%.4f); normalizing by /100",
                exposure,
            )
            return exposure / 100.0

        if exposure < 0:
            logger.warning(
                "Portfolio snapshot total_exposure_pct is negative (%.4f); clamping to 0",
                exposure,
            )
            return 0.0

        return exposure

    @staticmethod
    def get_order_price(data: Dict[str, Any]) -> Optional[Decimal]:
        """
        Get order limit price (NULL for pure market orders).

        Returns:
            Decimal: Limit price for limit/stop orders
            None: Market orders without limit price

        Raises:
            ValueError: If price format is invalid
        """
        raw = data.get("price") or data.get("limit_price")

        if raw is None:
            logger.info(
                "Market order without limit price: %s %s",
                data.get("symbol"),
                data.get("order_type"),
            )
            return None

        try:
            return Decimal(str(raw))
        except (InvalidOperation, TypeError) as e:
            logger.error("Invalid price format in order data: %s (error: %s)", raw, e)
            raise ValueError(f"Invalid price format: {raw}") from e

    @staticmethod
    def _get_positive_decimal(value: Any, field_name: str, data: Dict) -> Decimal:
        """
        Extract and validate a positive decimal value.

        Args:
            value: Raw value to convert
            field_name: Field name for error messages
            data: Full event data for error logging

        Returns:
            Decimal: Validated positive decimal value

        Raises:
            ValueError: If value is None, invalid format, or not positive
        """
        if value is None:
            raise ValueError(f"{field_name} is required but was None")

        try:
            dec = Decimal(str(value))
        except (InvalidOperation, TypeError) as e:
            logger.error(
                "Invalid %s format in trade: %s (data=%s, error=%s)",
                field_name,
                value,
                data.get("symbol"),
                e,
            )
            raise ValueError(f"Invalid {field_name} format: {value}") from e

        if dec <= 0:
            logger.error(
                "Non-positive %s in trade: %s (data=%s)",
                field_name,
                dec,
                data.get("symbol"),
            )
            raise ValueError(f"{field_name} must be > 0, got: {dec}")

        return dec

    def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True,
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def connect_postgres(self):
        """Connect to PostgreSQL"""
        try:
            self.db_conn = psycopg2.connect(
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
                user=self.postgres_user,
                password=self.postgres_password,
            )
            self.db_conn.autocommit = True
            logger.info(
                f"Connected to PostgreSQL at {self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def subscribe_to_channels(self):
        """Subscribe to Redis channels"""
        try:
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(*self.channels)
            logger.info(f"Subscribed to channels: {', '.join(self.channels)}")
        except Exception as e:
            logger.error(f"Failed to subscribe to channels: {e}")
            raise

    def process_signal_event(self, data: Dict):
        """
        Persist Signal event to PostgreSQL

        Args:
            data: Signal event data
        """
        try:
            cursor = self.db_conn.cursor()

            # Convert timestamp (handles Unix timestamps and ISO strings)
            timestamp = self.convert_timestamp(data.get("timestamp"))

            cursor.execute(
                """
                INSERT INTO signals (symbol, signal_type, price, confidence, timestamp, source, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    data.get("symbol"),
                    data.get("signal_type"),
                    data.get("price"),
                    data.get("confidence", 0.5),
                    timestamp,
                    data.get("source", "signal_engine"),
                    json.dumps(data.get("metadata", {})),
                ),
            )
            signal_id = cursor.fetchone()[0]
            logger.info(
                f"✅ Signal persisted: ID={signal_id}, {data.get('symbol')} {data.get('signal_type')}"
            )
        except Exception as e:
            logger.error(f"Failed to persist signal: {e}")

    def process_order_event(self, data: Dict):
        """
        Persist Order event to PostgreSQL.

        Note: orders.price can be NULL for pure market orders without limit price.

        Args:
            data: Order event data
        """
        try:
            # Get limit price (NULL for market orders without limit)
            order_price = self.get_order_price(data)

            # Convert timestamp (handles Unix timestamps and ISO strings)
            timestamp = self.convert_timestamp(data.get("timestamp"))

            cursor = self.db_conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders
                (symbol, side, order_type, price, size, approved, rejection_reason, status, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    data.get("symbol"),
                    self.normalize_side(data.get("side")),
                    data.get("order_type", "market"),
                    order_price,  # Can be None for market orders
                    data.get("quantity", data.get("size", 0)),
                    data.get("approved", False),
                    data.get("rejection_reason"),
                    data.get("status", "pending"),
                    json.dumps(data.get("metadata", {})),
                    timestamp,
                ),
            )
            order_id = cursor.fetchone()[0]
            logger.info(
                "✅ Order persisted: ID=%d, %s %s",
                order_id,
                data.get("symbol"),
                data.get("side"),
            )
        except ValueError as e:
            # Validation error (e.g., invalid price format)
            logger.error(
                "Validation error for order event %s: %s",
                data.get("symbol"),
                e,
            )
        except Exception as e:
            logger.error("Failed to persist order: %s", e)

    def process_trade_event(self, data: Dict):
        """
        Persist Trade event to PostgreSQL.

        IMPORTANT: Only persists actual executions (filled/partial).
        Rejected/cancelled orders are NOT trades and belong in orders table.

        Args:
            data: Trade/Order Result event data
        """
        # Validate status - only persist actual executions
        status_raw = data.get("status") or "filled"
        status = status_raw.lower()

        # Skip non-executions
        if status in NON_EXECUTION_STATUSES:
            logger.info(
                "⏭️  Skipping %s order_result: %s - not an actual trade",
                status,
                data.get("symbol"),
            )
            return

        # Warn on unknown status
        if status not in EXECUTION_STATUSES:
            logger.warning(
                "Unknown trade status '%s' for %s - treating as non-execution",
                status_raw,
                data.get("symbol"),
            )
            return

        try:
            # Validate execution price (must be > 0 for actual trades)
            execution_price_raw = data.get("price") or data.get("execution_price")
            execution_price = self._get_positive_decimal(
                execution_price_raw, "execution_price", data
            )

            # Validate execution quantity (must be > 0)
            execution_qty_raw = data.get("quantity") or data.get("size")
            execution_qty = self._get_positive_decimal(
                execution_qty_raw, "execution_quantity", data
            )

            # Convert timestamp
            timestamp = self.convert_timestamp(data.get("timestamp"))

            # Calculate slippage in basis points (if target_price available)
            slippage_bps = None
            target_price = data.get("target_price")
            if target_price:
                try:
                    target_dec = Decimal(str(target_price))
                    slippage = abs(execution_price - target_dec) / target_dec
                    slippage_bps = float(slippage * 10000)  # Convert to bps
                except (InvalidOperation, ZeroDivisionError, TypeError):
                    logger.warning(
                        "Could not calculate slippage for %s (target_price=%s)",
                        data.get("symbol"),
                        target_price,
                    )

            cursor = self.db_conn.cursor()
            cursor.execute(
                """
                INSERT INTO trades
                (symbol, side, price, size, status, execution_price, slippage_bps, fees, timestamp, exchange, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    data.get("symbol"),
                    self.normalize_side(data.get("side")),
                    execution_price,
                    execution_qty,
                    status,
                    execution_price,
                    slippage_bps,
                    data.get("fees", 0.0),
                    timestamp,
                    data.get("exchange", "MEXC"),
                    json.dumps(data.get("metadata", {})),
                ),
            )
            trade_id = cursor.fetchone()[0]
            logger.info(
                "✅ Trade persisted: ID=%d, %s %s @ %s",
                trade_id,
                data.get("symbol"),
                data.get("side"),
                execution_price,
            )
        except ValueError as e:
            # Validation error - log but don't crash the service
            logger.error(
                "Validation error for trade event %s: %s",
                data.get("symbol"),
                e,
            )
        except Exception as e:
            logger.error("Failed to persist trade: %s", e)

    def process_portfolio_snapshot(self, data: Dict):
        """
        Persist Portfolio Snapshot to PostgreSQL

        Args:
            data: Portfolio snapshot data
        """
        try:
            cursor = self.db_conn.cursor()

            # Convert timestamp (handles Unix timestamps and ISO strings)
            timestamp = self.convert_timestamp(data.get("timestamp"))

            cursor.execute(
                """
                INSERT INTO portfolio_snapshots
                (timestamp, total_equity, available_balance, margin_used, daily_pnl,
                 total_unrealized_pnl, total_realized_pnl, total_exposure_pct, max_drawdown_pct,
                 open_positions, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    timestamp,
                    data.get("equity", data.get("total_equity", 0)),
                    data.get("cash", data.get("available_balance", 0)),
                    data.get("margin_used", 0),
                    data.get("daily_pnl", 0),
                    data.get("total_unrealized_pnl", 0),
                    data.get("total_realized_pnl", 0),
                    self.normalize_exposure_pct(data.get("total_exposure_pct", 0.0)),
                    data.get("max_drawdown_pct", 0),
                    data.get("num_positions", data.get("open_positions", 0)),
                    json.dumps(data.get("metadata", {})),
                ),
            )
            snapshot_id = cursor.fetchone()[0]
            logger.info(
                f"✅ Portfolio snapshot persisted: ID={snapshot_id}, Equity={data.get('equity')}"
            )
        except Exception as e:
            logger.error(f"Failed to persist portfolio snapshot: {e}")

    def handle_message(self, message: Dict):
        """
        Route message to appropriate handler

        Args:
            message: Redis Pub/Sub message
        """
        if message["type"] != "message":
            return

        channel = message["channel"]

        try:
            data = json.loads(message["data"])
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in message from {channel}")
            return

        # Route to handler
        if channel == "signals":
            self.process_signal_event(data)
        elif channel == "orders":
            self.process_order_event(data)
        elif channel == "order_results":
            self.process_trade_event(data)
        elif channel == "portfolio_snapshots":
            self.process_portfolio_snapshot(data)
        else:
            logger.warning(f"Unknown channel: {channel}")

    def run(self):
        """Main event loop"""
        logger.info("Starting DB Writer Service...")

        # Connect to Redis and PostgreSQL
        self.connect_redis()
        self.connect_postgres()
        self.subscribe_to_channels()

        logger.info("DB Writer Service started ✅")
        logger.info("Listening for events...")

        # Event loop
        try:
            for message in self.pubsub.listen():
                self.handle_message(message)
        except KeyboardInterrupt:
            logger.info("Shutting down DB Writer Service...")
        except Exception as e:
            logger.error(f"Error in event loop: {e}")
            raise
        finally:
            if self.pubsub:
                self.pubsub.close()
            if self.db_conn:
                self.db_conn.close()
            logger.info("DB Writer Service stopped")


if __name__ == "__main__":
    writer = DatabaseWriter()
    writer.run()
