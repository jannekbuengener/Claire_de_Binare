"""
Database Layer for Execution Service
Claire de Binare Trading Bot
"""

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import datetime
import time
from contextlib import contextmanager

try:
    from . import config
    from .models import ExecutionResult, OrderStatus
except ImportError:
    import config
    from models import ExecutionResult, OrderStatus

logger = logging.getLogger(config.SERVICE_NAME)


class Database:
    """PostgreSQL database handler"""

    def __init__(self):
        self.connection_string = config.DATABASE_URL
        self._test_connection()

    def _test_connection(self):
        """Test database connection on init"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def save_order(self, result: ExecutionResult) -> bool:
        """
        Save order to orders table
        Returns True on success, False on failure
        """
        status = ExecutionResult._schema_status(result.status)
        status_db = (
            "filled"
            if status == "FILLED"
            else "rejected"
            if status in {"REJECTED", "ERROR"}
            else "pending"
        )
        price_value = float(result.price) if result.price and result.price > 0 else 1.0
        rejection_reason = (
            result.error_message if status_db == "rejected" else None
        )
        metadata = {
            "order_id": result.order_id,
            "client_id": result.client_id,
            "strategy_id": result.strategy_id,
            "bot_id": result.bot_id,
            "raw_status": status,
        }

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Insert into orders table
                    cur.execute(
                        """
                        INSERT INTO orders (
                            symbol, side, order_type, price, size,
                            approved, rejection_reason, status,
                            filled_size, avg_fill_price, submitted_at, filled_at,
                            metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s
                        )
                    """,
                        (
                            result.symbol,
                            result.side.lower(),
                            "market",
                            price_value,
                            float(result.quantity),
                            True,
                            rejection_reason,
                            status_db,
                            float(result.filled_quantity),
                            price_value,
                            datetime.utcnow(),
                            (
                                datetime.utcnow()
                                if status_db == "filled"
                                else None
                            ),
                            json.dumps(metadata),
                        ),
                    )

                    logger.info(f"Saved order to database: {result.order_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to save order: {e}")
            return False

    def save_trade(self, result: ExecutionResult) -> bool:
        """
        Save filled order as trade to trades table
        Only called for FILLED orders
        Returns True on success, False on failure
        """
        if ExecutionResult._schema_status(result.status) != "FILLED":
            logger.warning(f"Skipping trade save - order not filled: {result.order_id}")
            return False

        price_value = float(result.price) if result.price and result.price > 0 else 1.0

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Insert into trades table
                    cur.execute(
                        """
                        INSERT INTO trades (
                            order_id, symbol, side,
                            price, size,
                            status, execution_price,
                            exchange, exchange_trade_id, metadata
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s, %s
                        )
                    """,
                        (
                            None,
                            result.symbol,
                            result.side.lower(),
                            price_value,
                            float(result.filled_quantity),
                            "filled",
                            price_value,
                            result.exchange if hasattr(result, "exchange") else None,
                            result.order_id,
                            json.dumps(
                                {
                                    "order_id": result.order_id,
                                    "client_id": result.client_id,
                                    "strategy_id": result.strategy_id,
                                    "bot_id": result.bot_id,
                                }
                            ),
                        ),
                    )

                    logger.info(f"Saved trade to database: {result.order_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            return False

    def get_order_by_id(self, order_id: str) -> Optional[dict]:
        """Retrieve order by order_id"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM orders 
                        WHERE order_id = %s
                    """,
                        (order_id,),
                    )

                    result = cur.fetchone()
                    return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to retrieve order: {e}")
            return None

    def get_recent_orders(self, limit: int = 10) -> list:
        """Get recent orders"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM orders 
                        ORDER BY submitted_at DESC 
                        LIMIT %s
                    """,
                        (limit,),
                    )

                    results = cur.fetchall()
                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to retrieve orders: {e}")
            return []

    def get_stats(self) -> dict:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Count orders by status
                    cur.execute(
                        """
                        SELECT 
                            COUNT(*) FILTER (WHERE status = 'FILLED') as filled,
                            COUNT(*) FILTER (WHERE status = 'REJECTED') as rejected,
                            COUNT(*) FILTER (WHERE status = 'PENDING') as pending,
                            COUNT(*) as total
                        FROM orders
                    """
                    )

                    row = cur.fetchone()
                    return {
                        "filled": row[0],
                        "rejected": row[1],
                        "pending": row[2],
                        "total": row[3],
                    }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"filled": 0, "rejected": 0, "pending": 0, "total": 0}
