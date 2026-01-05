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
        """Stub for Redis stream reading (placeholder)."""
        # TODO: use redis_client.xrange/xread once integration ready
        return []
