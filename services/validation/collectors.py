"""Collectors that read Execution DB + Redis streams for the 72h validation window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


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
        rows = self.db_client.fetch_execution_orders(window_start, window_end)
        normalized: list[dict] = []
        for row in rows:
            normalized.append(
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "side": row["side"].upper(),
                    "qty": float(row["quantity"]),
                    "price": float(row["price"]),
                    "ts": row["timestamp"],
                    "status": row["status"],
                }
            )
        return normalized

    def collect_redis_events(
        self, stream: str, start_id: str, end_id: str, limit: int
    ) -> list[dict]:
        """Stub for Redis stream reading (placeholder)."""
        # TODO: use redis_client.xrange/xread once integration ready
        return []
