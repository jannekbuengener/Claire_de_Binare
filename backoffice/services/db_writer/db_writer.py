"""
DB Writer Service - Claire de Binaire
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
from typing import Dict

import redis
import psycopg2

# Logging Setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_writer")


# ===== TIMESTAMP CONVERSION UTILITY =====


def convert_timestamp(timestamp_value):
    """
    Konvertiert verschiedene Timestamp-Formate zu PostgreSQL-kompatiblem datetime.

    Unterstützt:
    - Unix timestamps (int): 1732302000
    - ISO strings: "2024-11-22T19:00:00Z"
    - datetime objects: datetime(2024, 11, 22, 19, 0, 0)
    - None: current UTC time

    Args:
        timestamp_value: Unix timestamp (int), ISO string, datetime, or None

    Returns:
        datetime: PostgreSQL-kompatibles datetime-Objekt

    Raises:
        ValueError: Wenn das Format nicht konvertiert werden kann
    """
    # None → current UTC
    if timestamp_value is None:
        return datetime.utcnow()

    # Bereits datetime → zurückgeben
    if isinstance(timestamp_value, datetime):
        return timestamp_value

    # Unix timestamp (int oder float)
    if isinstance(timestamp_value, (int, float)):
        try:
            return datetime.utcfromtimestamp(timestamp_value)
        except (ValueError, OSError) as e:
            logger.error(f"Ungültiger Unix timestamp: {timestamp_value} ({e})")
            return datetime.utcnow()

    # ISO string
    if isinstance(timestamp_value, str):
        try:
            # Entferne 'Z' suffix falls vorhanden
            iso_str = timestamp_value.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_str)
        except ValueError:
            logger.error(f"Ungültiger ISO timestamp: {timestamp_value}")
            return datetime.utcnow()

    # Unbekanntes Format → Fallback
    logger.warning(
        f"Unbekanntes Timestamp-Format: {type(timestamp_value)} - {timestamp_value}"
    )
    return datetime.utcnow()


class DatabaseWriter:
    """
    Database Writer Service

    Subscribes to Redis channels and persists events to PostgreSQL
    """

    def __init__(self):
        """Initialize DB Writer"""
        self.redis_host = os.getenv("REDIS_HOST", "cdb_redis")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)

        self.postgres_host = os.getenv("POSTGRES_HOST", "cdb_postgres")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "claire_de_binaire")
        self.postgres_user = os.getenv("POSTGRES_USER", "claire_user")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "")

        # Channels to subscribe to
        self.channels = ["signals", "orders", "order_results", "portfolio_snapshots"]

        # Connections
        self.redis_client = None
        self.db_conn = None
        self.pubsub = None

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

            # Convert timestamp (Unix int → datetime)
            timestamp = convert_timestamp(data.get("timestamp"))

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
                    timestamp,  # ✅ FIX: Converted timestamp
                    data.get("source", "signal_engine"),
                    json.dumps(data.get("metadata", {})),
                ),
            )
            signal_id = cursor.fetchone()[0]
            logger.info(
                f"✅ Signal persisted: ID={signal_id}, {data.get('symbol')} {data.get('signal_type')} @ {timestamp}"
            )
        except Exception as e:
            logger.error(f"Failed to persist signal: {e}")

    def process_order_event(self, data: Dict):
        """
        Persist Order event to PostgreSQL

        Args:
            data: Order event data
        """
        try:
            cursor = self.db_conn.cursor()

            # Convert timestamp (Unix int → datetime)
            timestamp = convert_timestamp(data.get("timestamp"))

            cursor.execute(
                """
                INSERT INTO orders
                (symbol, side, order_type, price, size, approved, rejection_reason, status, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    data.get("symbol"),
                    data.get("side"),
                    data.get("order_type", "market"),
                    data.get("price"),
                    data.get("quantity", data.get("size", 0)),
                    data.get("approved", False),
                    data.get("rejection_reason"),
                    data.get("status", "pending"),
                    json.dumps(data.get("metadata", {})),
                    timestamp,  # ✅ FIX: Converted timestamp
                ),
            )
            order_id = cursor.fetchone()[0]
            logger.info(
                f"✅ Order persisted: ID={order_id}, {data.get('symbol')} {data.get('side')} @ {timestamp}"
            )
        except Exception as e:
            logger.error(f"Failed to persist order: {e}")

    def process_trade_event(self, data: Dict):
        """
        Persist Trade event to PostgreSQL

        Args:
            data: Trade/Order Result event data
        """
        try:
            cursor = self.db_conn.cursor()

            # Convert timestamp (Unix int → datetime)
            timestamp = convert_timestamp(data.get("timestamp"))

            # Calculate slippage in basis points
            slippage_bps = None
            if data.get("target_price") and data.get("price"):
                slippage = abs(data.get("price") - data.get("target_price")) / data.get(
                    "target_price"
                )
                slippage_bps = slippage * 10000  # Convert to bps

            cursor.execute(
                """
                INSERT INTO trades
                (symbol, side, price, size, status, execution_price, slippage_bps, fees, timestamp, exchange, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    data.get("symbol"),
                    data.get("side"),
                    data.get("price"),
                    data.get("quantity", data.get("size", 0)),
                    data.get("status", "filled"),
                    data.get("price"),  # execution_price
                    slippage_bps,
                    data.get("fees", 0.0),
                    timestamp,  # ✅ FIX: Converted timestamp
                    data.get("exchange", "MEXC"),
                    json.dumps(data.get("metadata", {})),
                ),
            )
            trade_id = cursor.fetchone()[0]
            logger.info(
                f"✅ Trade persisted: ID={trade_id}, {data.get('symbol')} {data.get('side')} @ {data.get('price')} @ {timestamp}"
            )
        except Exception as e:
            logger.error(f"Failed to persist trade: {e}")

    def process_portfolio_snapshot(self, data: Dict):
        """
        Persist Portfolio Snapshot to PostgreSQL

        Args:
            data: Portfolio snapshot data
        """
        try:
            cursor = self.db_conn.cursor()

            # Convert timestamp (Unix int → datetime)
            timestamp = convert_timestamp(data.get("timestamp"))

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
                    timestamp,  # ✅ FIX: Converted timestamp
                    data.get("equity", data.get("total_equity", 0)),
                    data.get("cash", data.get("available_balance", 0)),
                    data.get("margin_used", 0),
                    data.get("daily_pnl", 0),
                    data.get("total_unrealized_pnl", 0),
                    data.get("total_realized_pnl", 0),
                    data.get("total_exposure_pct", 0) / 100.0,  # Convert to decimal
                    data.get("max_drawdown_pct", 0),
                    data.get("num_positions", data.get("open_positions", 0)),
                    json.dumps(data.get("metadata", {})),
                ),
            )
            snapshot_id = cursor.fetchone()[0]
            logger.info(
                f"✅ Portfolio snapshot persisted: ID={snapshot_id}, Equity={data.get('equity')} @ {timestamp}"
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
