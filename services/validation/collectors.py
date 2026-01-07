"""Collectors that read Execution DB + Redis streams for the 72h validation window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from psycopg2.extras import RealDictCursor


@dataclass
class ExecutionCollectorConfig:
    db_client: Any
    redis_client: Any


class ExecutionCollector:
    """Read-only collector wrapping Execution DB and Redis connections."""

    def __init__(self, config: ExecutionCollectorConfig) -> None:
        self.db_client = config.db_client
        self.redis_client = config.redis_client

    def collect_execution_orders(self, window_start: str, window_end: str) -> list[dict]:
        """Return normalized order rows from Execution DB."""
        with self.db_client.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, symbol, side, size, COALESCE(avg_fill_price, price) AS effective_price,
                       price, submitted_at, status
                FROM orders
                WHERE submitted_at >= %s AND submitted_at <= %s
                ORDER BY submitted_at ASC
                """,
                (window_start, window_end),
            )
            rows = cur.fetchall()

        normalized: list[dict] = []
        for row in rows:
            price = row["effective_price"]
            normalized.append(
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "side": row["side"].upper(),
                    "qty": float(row["size"]),
                    "price": float(price) if price is not None else 0.0,
                    "ts": row["submitted_at"].isoformat(),
                    "status": row["status"].upper(),
                }
            )
        return normalized

    def collect_redis_events(
        self, stream: str, start_id: str, end_id: str, limit: int
    ) -> list[dict]:
        """
        Read events from Redis stream using XRANGE.

        Args:
            stream: Redis stream name (e.g., 'signals', 'market_events')
            start_id: Starting stream ID (e.g., '0', '1640000000000-0')
            end_id: Ending stream ID (e.g., '+', '1640100000000-0')
            limit: Maximum number of entries to return

        Returns:
            List of normalized event dictionaries with 'id' and event fields
        """
        if not self.redis_client:
            return []

        try:
            # Use XRANGE to read stream entries within the specified range
            # XRANGE returns: [(stream_id, {field: value, ...}), ...]
            entries = self.redis_client.xrange(
                name=stream,
                min=start_id,
                max=end_id,
                count=limit
            )

            # Normalize to list of dicts with stream_id included
            normalized: list[dict] = []
            for stream_id, fields in entries:
                event = {"id": stream_id}
                event.update(fields)
                normalized.append(event)

            return normalized

        except Exception as e:
            # Log error but don't crash - return empty list
            # The logging setup from service.py should be available
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to read Redis stream '{stream}': {e}")
            return []
