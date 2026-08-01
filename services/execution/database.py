"""
Database Layer for Execution Service
Claire de Binare Trading Bot
"""

from __future__ import annotations

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation
import time
from contextlib import contextmanager

from core.utils.uuid_gen import compute_correlation_id, compute_event_pk
from core.utils.trace_toggle import allow_evidence_debt

try:
    from . import config
    from .models import ExecutionResult, OrderStatus
    from .reduce_only import (
        REDUCE_ONLY_ADAPTER_BOUND,
        REDUCE_ONLY_DUPLICATE_RESULT,
        REDUCE_ONLY_PARTIAL_FILL,
        REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
        REDUCE_ONLY_POSITION_UNKNOWN,
        REDUCE_ONLY_BINDABLE_REASONS,
        apply_reduce_only_result,
        prepare_reduce_only,
    )
except ImportError:
    import config
    from models import ExecutionResult, OrderStatus
    from reduce_only import (
        REDUCE_ONLY_ADAPTER_BOUND,
        REDUCE_ONLY_DUPLICATE_RESULT,
        REDUCE_ONLY_PARTIAL_FILL,
        REDUCE_ONLY_POSITION_INCREASE_BLOCKED,
        REDUCE_ONLY_POSITION_UNKNOWN,
        REDUCE_ONLY_BINDABLE_REASONS,
        apply_reduce_only_result,
        prepare_reduce_only,
    )

logger = logging.getLogger(config.SERVICE_NAME)

# Phase 8C: Fail-closed with safety valve
# Modul-Level-Konstante entfernt; allow_evidence_debt() aus core.utils.trace_toggle

# Valid event types for correlation_ledger
# BLOCK ist ein Entscheidungsergebnis (event_type="DECISION"), kein eigener Event-Typ.
# Details zu BLOCK-Entscheidungen in der blocked_decisions-Tabelle.
VALID_EVENT_TYPES = {"SIGNAL", "DECISION", "ORDER", "FILL"}


class Database:
    """PostgreSQL database handler"""

    def __init__(
        self,
        connection_string: str | None = None,
        *,
        test_on_init: bool = True,
    ):
        self.connection_string = connection_string or config.DATABASE_URL
        self._orders_has_order_id_column = None
        if test_on_init:
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

    @staticmethod
    def _signed_position(row) -> Decimal | None:
        """Convert the positions table side+size representation to signed qty."""

        if row is None:
            return Decimal("0")
        if isinstance(row, dict):
            side, size = row.get("side"), row.get("size")
        else:
            side, size = row
        quantity = Decimal(str(size))
        if not quantity.is_finite() or quantity < 0:
            return None
        normalized_side = str(side).lower()
        if normalized_side == "long":
            return quantity
        if normalized_side == "short":
            return -quantity
        if normalized_side == "none" and quantity == 0:
            return Decimal("0")
        return None

    @staticmethod
    def _reduce_only_row(row, *, duplicate: bool) -> dict:
        payload = dict(row)
        payload["allowed"] = payload.get("status") == "PREPARED" and not duplicate
        payload["duplicate"] = duplicate
        if duplicate:
            payload["reason_code"] = REDUCE_ONLY_DUPLICATE_RESULT
        return payload

    def _bind_prepared_for_adapter(self, cur, *, order_id: str) -> dict | None:
        """Atomically mark a bindable PREPARED claim as adapter-bound.

        Returns the bound row payload when this caller won the CAS; otherwise None.
        """
        cur.execute(
            """
            UPDATE reduce_only_executions
            SET reason_code = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s
              AND status = 'PREPARED'
              AND reason_code IN %s
            RETURNING order_id, symbol, side, position_before,
                      requested_quantity, submitted_quantity,
                      filled_quantity, fill_price, realized_pnl_delta,
                      position_after, status, reason_code
            """,
            (
                REDUCE_ONLY_ADAPTER_BOUND,
                order_id,
                tuple(REDUCE_ONLY_BINDABLE_REASONS),
            ),
        )
        bound = cur.fetchone()
        if bound is None:
            return None
        payload = self._reduce_only_row(bound, duplicate=False)
        payload["allowed"] = True
        payload["adapter_bound"] = True
        return payload

    def prepare_reduce_only(
        self,
        *,
        order_id: str,
        symbol: str,
        side: str,
        requested_quantity: Decimal,
        persist_blocked: bool = True,
        bind_for_adapter: bool = True,
    ) -> dict:
        """Persistently validate/reserve a reduce-only order before submission.

        ``bind_for_adapter=True`` (execution default) atomically transitions a
        bindable ``PREPARED`` claim to ``REDUCE_ONLY_ADAPTER_BOUND`` so exactly
        one adapter submission can proceed. ``bind_for_adapter=False`` is used
        by risk PAPER_AUTO_UNWIND to claim before Redis dispatch without binding.

        When ``persist_blocked=False``, unsuccessful preparations do not insert
        a ``BLOCKED`` ledger row (keeps deterministic unwind ``order_id``s
        retryable after a persistence race).
        """

        if not order_id:
            raise ValueError("reduce-only order_id is required")

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT order_id, symbol, side, position_before,
                           requested_quantity, submitted_quantity,
                           filled_quantity, fill_price, realized_pnl_delta,
                           position_after, status, reason_code
                    FROM reduce_only_executions
                    WHERE order_id = %s
                    FOR UPDATE
                    """,
                    (order_id,),
                )
                existing = cur.fetchone()
                if existing is not None:
                    existing_reason = str(existing.get("reason_code") or "")
                    if (
                        existing.get("status") == "PREPARED"
                        and existing_reason in REDUCE_ONLY_BINDABLE_REASONS
                    ):
                        if bind_for_adapter:
                            bound = self._bind_prepared_for_adapter(
                                cur, order_id=order_id
                            )
                            if bound is not None:
                                # Preserve clamp/ready reason for caller metadata.
                                bound["reason_code"] = existing_reason
                                return bound
                            return self._reduce_only_row(existing, duplicate=True)
                        # Risk re-entry: claim held, not yet adapter-bound.
                        payload = dict(existing)
                        payload["allowed"] = True
                        payload["duplicate"] = True
                        payload["resume_dispatch"] = True
                        return payload
                    return self._reduce_only_row(existing, duplicate=True)

                cur.execute(
                    """
                    SELECT id, side, size, entry_price, realized_pnl
                    FROM positions
                    WHERE symbol = %s AND closed_at IS NULL
                    FOR UPDATE
                    """,
                    (symbol,),
                )
                position_rows = cur.fetchall()
                position = (
                    self._signed_position(position_rows[0])
                    if len(position_rows) == 1
                    else (Decimal("0") if not position_rows else None)
                )
                if position not in (None, Decimal("0")):
                    try:
                        entry_price = Decimal(str(position_rows[0].get("entry_price")))
                        realized_pnl = Decimal(
                            str(position_rows[0].get("realized_pnl") or Decimal("0"))
                        )
                    except (InvalidOperation, TypeError, ValueError):
                        position = None
                    else:
                        if (
                            not entry_price.is_finite()
                            or entry_price <= 0
                            or not realized_pnl.is_finite()
                        ):
                            position = None

                cur.execute(
                    """
                    SELECT COALESCE(SUM(submitted_quantity), 0)
                    FROM reduce_only_executions
                    WHERE symbol = %s AND status = 'PREPARED'
                    """,
                    (symbol,),
                )
                reserved = Decimal(str(cur.fetchone()["coalesce"]))
                preparation = prepare_reduce_only(
                    position_before=position,
                    side=side,
                    requested_quantity=requested_quantity,
                    reserved_quantity=reserved,
                )
                if not preparation.allowed and not persist_blocked:
                    return {
                        "allowed": False,
                        "duplicate": False,
                        "order_id": order_id,
                        "symbol": symbol,
                        "side": str(side).upper(),
                        "position_before": preparation.position_before,
                        "requested_quantity": preparation.requested_quantity,
                        "submitted_quantity": preparation.submitted_quantity,
                        "position_after": preparation.position_before,
                        "status": "BLOCKED",
                        "reason_code": preparation.reason_code,
                        "persisted": False,
                    }

                status = "PREPARED" if preparation.allowed else "BLOCKED"
                cur.execute(
                    """
                    INSERT INTO reduce_only_executions (
                        order_id, symbol, side, position_before,
                        requested_quantity, submitted_quantity,
                        position_after, status, reason_code
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING order_id, symbol, side, position_before,
                              requested_quantity, submitted_quantity,
                              filled_quantity, position_after, status, reason_code
                    """,
                    (
                        order_id,
                        symbol,
                        str(side).upper(),
                        preparation.position_before,
                        preparation.requested_quantity,
                        preparation.submitted_quantity,
                        preparation.position_before,
                        status,
                        preparation.reason_code,
                    ),
                )
                inserted = cur.fetchone()
                payload = self._reduce_only_row(inserted, duplicate=False)
                payload["persisted"] = True
                if (
                    bind_for_adapter
                    and preparation.allowed
                    and preparation.reason_code in REDUCE_ONLY_BINDABLE_REASONS
                ):
                    bound = self._bind_prepared_for_adapter(cur, order_id=order_id)
                    if bound is None:
                        # Lost CAS after insert — fail closed.
                        return self._reduce_only_row(inserted, duplicate=True)
                    bound["reason_code"] = preparation.reason_code
                    bound["persisted"] = True
                    return bound
                return payload

    def finalize_reduce_only(
        self,
        *,
        order_id: str,
        status: str,
        filled_quantity: Decimal,
        fill_price: Decimal | None,
    ) -> dict:
        """Apply a reduce-only adapter result once in the positions transaction."""

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT order_id, symbol, side, position_before,
                           requested_quantity, submitted_quantity,
                           filled_quantity, fill_price, realized_pnl_delta,
                           position_after, status, reason_code
                    FROM reduce_only_executions
                    WHERE order_id = %s
                    FOR UPDATE
                    """,
                    (order_id,),
                )
                contract_row = cur.fetchone()
                if contract_row is None:
                    raise ValueError(REDUCE_ONLY_POSITION_UNKNOWN)
                if contract_row["status"] != "PREPARED":
                    return self._reduce_only_row(contract_row, duplicate=True)

                cur.execute(
                    """
                    SELECT id, side, size, entry_price, current_price, realized_pnl
                    FROM positions
                    WHERE symbol = %s AND closed_at IS NULL
                    FOR UPDATE
                    """,
                    (contract_row["symbol"],),
                )
                position_rows = cur.fetchall()
                if len(position_rows) != 1:
                    raise ValueError(REDUCE_ONLY_POSITION_UNKNOWN)
                position_row = position_rows[0]
                current_position = self._signed_position(position_row)
                if current_position is None:
                    raise ValueError(REDUCE_ONLY_POSITION_UNKNOWN)

                prepared_position = Decimal(str(contract_row["position_before"]))
                preparation = prepare_reduce_only(
                    position_before=prepared_position,
                    side=contract_row["side"],
                    requested_quantity=Decimal(str(contract_row["submitted_quantity"])),
                )
                outcome = apply_reduce_only_result(
                    preparation,
                    status=status,
                    filled_quantity=filled_quantity,
                )

                normalized_status = str(status).upper()
                if current_position != prepared_position:
                    applied = False
                    applied_quantity = Decimal("0")
                    position_after = current_position
                    reason_code = REDUCE_ONLY_POSITION_INCREASE_BLOCKED
                    persisted_status = "BLOCKED"
                else:
                    applied = outcome.applied
                    applied_quantity = outcome.filled_quantity
                    position_after = outcome.position_after
                    reason_code = outcome.reason_code
                    persisted_status = (
                        "REJECTED"
                        if normalized_status
                        in {"REJECTED", "FAILED", "CANCELLED", "ERROR"}
                        else (
                            "BLOCKED"
                            if reason_code == REDUCE_ONLY_POSITION_INCREASE_BLOCKED
                            else (
                                "PARTIALLY_FILLED"
                                if reason_code == REDUCE_ONLY_PARTIAL_FILL
                                else "FILLED"
                            )
                        )
                    )

                realized_pnl_delta = Decimal("0")
                realized_pnl_after = Decimal(
                    str(position_row.get("realized_pnl") or Decimal("0"))
                )
                if applied:
                    try:
                        execution_price = Decimal(str(fill_price))
                        entry_price = Decimal(str(position_row["entry_price"]))
                    except (InvalidOperation, TypeError, ValueError) as exc:
                        raise ValueError(REDUCE_ONLY_POSITION_UNKNOWN) from exc
                    if (
                        not execution_price.is_finite()
                        or execution_price <= 0
                        or not entry_price.is_finite()
                    ):
                        raise ValueError(REDUCE_ONLY_POSITION_UNKNOWN)
                    realized_pnl_delta = (
                        (execution_price - entry_price) * applied_quantity
                        if current_position > 0
                        else (entry_price - execution_price) * applied_quantity
                    )
                    realized_pnl_after += realized_pnl_delta
                    if position_after == 0:
                        cur.execute(
                            """
                            UPDATE positions
                            SET size = 0, closed_at = CURRENT_TIMESTAMP,
                                current_price = %s, realized_pnl = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s AND closed_at IS NULL
                            """,
                            (
                                execution_price,
                                realized_pnl_after,
                                position_row["id"],
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE positions SET size = %s, current_price = %s,
                                realized_pnl = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s AND closed_at IS NULL
                            """,
                            (
                                abs(position_after),
                                execution_price,
                                realized_pnl_after,
                                position_row["id"],
                            ),
                        )

                cur.execute(
                    """
                    UPDATE reduce_only_executions
                    SET filled_quantity = %s,
                        fill_price = %s,
                        realized_pnl_delta = %s,
                        position_after = %s,
                        status = %s,
                        reason_code = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = %s
                    RETURNING order_id, symbol, side, position_before,
                              requested_quantity, submitted_quantity,
                              filled_quantity, fill_price, realized_pnl_delta,
                              position_after, status, reason_code
                    """,
                    (
                        applied_quantity,
                        execution_price if applied else None,
                        realized_pnl_delta if applied else None,
                        position_after,
                        persisted_status,
                        reason_code,
                        order_id,
                    ),
                )
                payload = self._reduce_only_row(cur.fetchone(), duplicate=False)
                payload.update(
                    {
                        "applied": applied,
                        "adapter_reported_filled_quantity": filled_quantity,
                        "position_before_apply": current_position,
                        "remaining_position_quantity": abs(position_after),
                        "position_increase_observed": abs(position_after)
                        > abs(prepared_position),
                        "side_flip_observed": prepared_position * position_after < 0,
                        "realized_pnl_delta": realized_pnl_delta,
                        "realized_pnl_after": realized_pnl_after,
                    }
                )
                return payload

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
                    raw_metadata = (
                        dict(result.metadata)
                        if isinstance(result.metadata, dict)
                        else {}
                    )
                    canonical_order_id = raw_metadata.get("order_id")
                    metadata_payload = dict(raw_metadata)
                    metadata_payload.setdefault("source", "execution_service")
                    if result.order_id:
                        metadata_payload.setdefault(
                            "exchange_order_id", result.order_id
                        )
                    metadata_json = json.dumps(metadata_payload)

                    has_order_id = self._orders_has_order_id(cur)
                    if not has_order_id:
                        logger.warning(
                            "Skipping order lifecycle update for %s: orders.order_id column missing",
                            result.order_id,
                        )
                        return False

                    if not canonical_order_id:
                        logger.warning(
                            "Skipping order lifecycle update for %s: missing canonical order_id",
                            result.order_id,
                        )
                        return False

                    if has_order_id:
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
                                canonical_order_id,
                            ),
                        )
                        if cur.fetchone():
                            logger.info(
                                "Updated order lifecycle in database: %s",
                                canonical_order_id,
                            )
                            return True

                    logger.warning(
                        "Skipping order lifecycle update for canonical order %s: no existing order row found (exchange_order_id=%s)",
                        canonical_order_id,
                        result.order_id,
                    )
                    return False

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
