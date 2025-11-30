"""
Database Layer for Execution Service
Claire de Binare Trading Bot
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
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
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Insert into orders table (schema uses: size, order_type, filled_size, avg_fill_price)
                    cur.execute(
                        """
                        INSERT INTO orders (
                            symbol, side, order_type,
                            size, price, filled_size, avg_fill_price,
                            status, approved, submitted_at, filled_at
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, NOW(), %s
                        )
                    """,
                        (
                            result.symbol,
                            result.side.lower(),  # Schema uses lowercase
                            "market",  # Schema uses lowercase
                            result.quantity,
                            result.price,
                            result.filled_quantity,
                            result.price,  # avg_fill_price = price for now
                            result.status.lower(),  # Schema uses lowercase
                            True,  # approved (already passed risk checks)
                            (
                                "NOW()"
                                if result.status == OrderStatus.FILLED.value
                                else None
                            ),
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
        if result.status != OrderStatus.FILLED.value:
            logger.warning(f"Skipping trade save - order not filled: {result.order_id}")
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Insert into trades table (schema uses: size, price, execution_price, timestamp)
                    cur.execute(
                        """
                        INSERT INTO trades (
                            symbol, side, price, size,
                            execution_price, status, timestamp,
                            exchange, exchange_trade_id
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, NOW(),
                            %s, %s
                        )
                    """,
                        (
                            result.symbol,
                            result.side.lower(),  # Schema uses lowercase
                            result.price,
                            result.filled_quantity,
                            result.price,  # execution_price same as price for mock
                            "filled",  # Schema uses lowercase
                            "MEXC",  # exchange
                            result.order_id,  # exchange_trade_id stores our mock order_id
                        ),
                    )

                    logger.info(f"Saved trade to database: {result.order_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            return False

    def get_order_by_id(self, order_id: str) -> Optional[dict]:
        """Retrieve order by database id"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM orders
                        WHERE id = %s
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
                        ORDER BY created_at DESC
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
