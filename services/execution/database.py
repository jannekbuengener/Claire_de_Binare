"""
Database Layer for Execution Service
Claire de Binare Trading Bot
"""

import json
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import datetime
import time
from contextlib import contextmanager

from core.utils.uuid_gen import compute_correlation_id, compute_event_pk
from core.utils.trace_toggle import allow_evidence_debt

try:
    from . import config
    from .models import ExecutionResult, OrderStatus
except ImportError:
    import config
    from models import ExecutionResult, OrderStatus

logger = logging.getLogger(config.SERVICE_NAME)

# Phase 8C: Fail-closed with safety valve
# Modul-Level-Konstante entfernt; allow_evidence_debt() aus core.utils.trace_toggle

# Valid event types for correlation_ledger
# BLOCK ist ein Entscheidungsergebnis (event_type="DECISION"), kein eigener Event-Typ.
# Details zu BLOCK-Entscheidungen in der blocked_decisions-Tabelle.
VALID_EVENT_TYPES = {"SIGNAL", "DECISION", "ORDER", "FILL"}


class Database:
    """PostgreSQL database handler"""

    def __init__(self):
        self.connection_string = config.DATABASE_URL
        self._orders_has_order_id_column = None
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

    def _orders_has_order_id(self, cur) -> bool:
        """Check if orders table has order_id column (cached)."""
        if self._orders_has_order_id_column is not None:
            return self._orders_has_order_id_column
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'orders' AND column_name = 'order_id'
        """)
        self._orders_has_order_id_column = cur.fetchone() is not None
        return self._orders_has_order_id_column

    def persist_correlation_event(
        self,
        signal_id: str,
        event_type: str,
        symbol: str,
        timestamp_ms: int,
        decision_id: str,
        order_id: Optional[str] = None,
        fill_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> bool:
        """
        Persist correlation event to correlation_ledger (Phase 8C).

        Fail-closed semantics:
        - signal_id + decision_id required
        - ORDER requires order_id
        - FILL requires order_id + fill_id
        - DB errors = warn-only (evidence debt)
        - statement_timeout = 250ms
        - ON CONFLICT (event_pk) DO NOTHING (idempotent)
        """
        # Canonicalize event_type
        event_type = event_type.strip().upper()
        if event_type not in VALID_EVENT_TYPES:
            if allow_evidence_debt():
                logger.warning(
                    f"⚠️ correlation_ledger skipped: unknown event_type={event_type} "
                    f"(ALLOW_EVIDENCE_DEBT=1)"
                )
                return False
            raise ValueError(
                f"Invalid event_type: {event_type}. Must be one of {VALID_EVENT_TYPES}"
            )

        # Fail-closed: validate required IDs
        if not signal_id or not decision_id:
            if allow_evidence_debt():
                logger.warning(
                    f"⚠️ correlation_ledger {event_type} skipped: "
                    f"signal_id={signal_id}, decision_id={decision_id} (ALLOW_EVIDENCE_DEBT=1)"
                )
                return False
            raise ValueError(
                f"signal_id and decision_id required for correlation_ledger {event_type} "
                f"(signal_id={signal_id}, decision_id={decision_id})"
            )

        if event_type == "ORDER" and not order_id:
            if allow_evidence_debt():
                logger.warning(
                    f"⚠️ correlation_ledger ORDER skipped: order_id missing (ALLOW_EVIDENCE_DEBT=1)"
                )
                return False
            raise ValueError("order_id required for correlation_ledger ORDER")

        if event_type == "FILL" and (not order_id or not fill_id):
            if allow_evidence_debt():
                logger.warning(
                    f"⚠️ correlation_ledger FILL skipped: "
                    f"order_id={order_id}, fill_id={fill_id} (ALLOW_EVIDENCE_DEBT=1)"
                )
                return False
            raise ValueError(
                f"order_id and fill_id required for correlation_ledger FILL "
                f"(order_id={order_id}, fill_id={fill_id})"
            )

        try:
            correlation_id = compute_correlation_id(signal_id)
            event_pk = compute_event_pk(signal_id, event_type, order_id, fill_id)

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL statement_timeout = '250ms'")
                    cur.execute(
                        """
                        INSERT INTO correlation_ledger
                            (event_pk, correlation_id, signal_id, decision_id, order_id, fill_id,
                             event_type, symbol, timestamp_ms, payload)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_pk) DO NOTHING
                        """,
                        (
                            event_pk,
                            correlation_id,
                            signal_id,
                            decision_id,
                            order_id,
                            fill_id,
                            event_type,
                            symbol,
                            timestamp_ms,
                            json.dumps(payload) if payload else None,
                        ),
                    )
            logger.debug(f"📊 correlation_ledger {event_type}: {signal_id[:20]}...")
            return True
        except Exception as e:
            logger.warning(f"⚠️ correlation_ledger {event_type} write failed: {e}")
            return False

    def save_order(self, result: ExecutionResult) -> bool:
        """
        Save order to orders table
        Returns True on success, False on failure
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    metadata_payload = (
                        dict(result.metadata)
                        if isinstance(result.metadata, dict)
                        else {}
                    )
                    metadata_payload.setdefault("source", "execution_service")
                    if result.order_id:
                        metadata_payload.setdefault("order_id", result.order_id)
                        metadata_payload.setdefault(
                            "exchange_order_id", result.order_id
                        )
                    metadata_json = json.dumps(metadata_payload)

                    has_order_id = self._orders_has_order_id(cur)
                    if has_order_id and result.order_id:
                        cur.execute(
                            """
                            UPDATE orders
                            SET filled_size = %s,
                                avg_fill_price = %s,
                                status = %s,
                                submitted_at = COALESCE(submitted_at, to_timestamp(%s)),
                                filled_at = CASE
                                    WHEN %s = %s THEN COALESCE(filled_at, to_timestamp(%s))
                                    ELSE filled_at
                                END,
                                metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                            WHERE order_id = %s
                            RETURNING id
                        """,
                            (
                                result.filled_quantity,
                                result.price,
                                result.status.lower(),
                                int(time.time()),
                                result.status.lower(),
                                OrderStatus.FILLED.value.lower(),
                                int(time.time()),
                                metadata_json,
                                result.order_id,
                            ),
                        )
                        if cur.fetchone():
                            logger.info(
                                "Updated order lifecycle in database: %s",
                                result.order_id,
                            )
                            return True

                    # Insert fallback for execution-local outcomes without a prior canonical order row.
                    if has_order_id:
                        cur.execute(
                            """
                            INSERT INTO orders (
                                order_id, symbol, side, order_type,
                                size, price, filled_size, avg_fill_price,
                                status, submitted_at, filled_at,
                                approved, metadata
                            ) VALUES (
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, to_timestamp(%s), to_timestamp(%s),
                                %s, %s
                            )
                            RETURNING id
                        """,
                            (
                                result.order_id,
                                result.symbol,
                                result.side.lower(),
                                "market",
                                result.quantity,
                                result.price,
                                result.filled_quantity,
                                result.price,
                                result.status.lower(),
                                int(time.time()),
                                (
                                    int(time.time())
                                    if result.status == OrderStatus.FILLED.value
                                    else None
                                ),
                                True,  # approved
                                metadata_json,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO orders (
                                symbol, side, order_type,
                                size, price, filled_size, avg_fill_price,
                                status, submitted_at, filled_at,
                                approved, metadata
                            ) VALUES (
                                %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, to_timestamp(%s), to_timestamp(%s),
                                %s, %s
                            )
                            RETURNING id
                        """,
                            (
                                result.symbol,
                                result.side.lower(),
                                "market",
                                result.quantity,
                                result.price,
                                result.filled_quantity,
                                result.price,
                                result.status.lower(),
                                int(time.time()),
                                (
                                    int(time.time())
                                    if result.status == OrderStatus.FILLED.value
                                    else None
                                ),
                                True,  # approved
                                metadata_json,
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
                    # Convert timestamp string to Unix timestamp
                    timestamp = int(
                        datetime.fromisoformat(result.timestamp).timestamp()
                    )
                    metadata_payload = (
                        dict(result.metadata)
                        if isinstance(result.metadata, dict)
                        else {}
                    )
                    if result.order_id:
                        metadata_payload.setdefault("order_id", result.order_id)
                        metadata_payload.setdefault(
                            "exchange_order_id", result.order_id
                        )
                    metadata_payload.setdefault("source", "execution_service")

                    # Insert into trades table
                    cur.execute(
                        """
                        INSERT INTO trades (
                            symbol, side,
                            price, size, execution_price,
                            status, timestamp,
                            metadata
                        ) VALUES (
                            %s, %s,
                            %s, %s, %s,
                            %s, to_timestamp(%s),
                            %s
                        )
                        RETURNING id
                    """,
                        (
                            result.symbol,
                            result.side.lower(),  # lowercase for schema constraint
                            result.price,  # price
                            result.filled_quantity,  # maps to size
                            result.price,  # execution_price = price for mock
                            "filled",  # Trade status (lowercase to match schema check constraint)
                            timestamp,  # Unix timestamp
                            json.dumps(metadata_payload),
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
                    if self._orders_has_order_id(cur):
                        cur.execute(
                            """
                            SELECT * FROM orders
                            WHERE order_id = %s
                        """,
                            (order_id,),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT * FROM orders
                            WHERE metadata->>'order_id' = %s
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
                    cur.execute("""
                        SELECT 
                            COUNT(*) FILTER (WHERE status = 'FILLED') as filled,
                            COUNT(*) FILTER (WHERE status = 'REJECTED') as rejected,
                            COUNT(*) FILTER (WHERE status = 'PENDING') as pending,
                            COUNT(*) as total
                        FROM orders
                    """)

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
