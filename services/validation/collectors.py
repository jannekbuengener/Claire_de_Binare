"""Collectors that read Execution DB + Redis streams for the 72h validation window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class ExecutionCollectorConfig:
    db_url: str
    redis_url: str


class ExecutionCollector:
    """Read-only collector wrapping Execution DB and Redis connections."""

    def __init__(self, config: ExecutionCollectorConfig) -> None:
        self.config = config

    def collect_orders(self) -> Iterable[dict]:
        """Yields order events from the Execution DB (read-only)."""
        # TODO: replace with real query, no writes performed here.
        query_result = [
            {"order_id": "order-1", "symbol": "BTCUSDT", "filled_quantity": 0.1}
        ]
        yield from query_result

    def collect_results(self) -> Iterable[dict]:
        """Yields result events aggregated from Redis streams."""
        stream_result = [
            {"result_id": "result-1", "status": "FILLED", "symbol": "BTCUSDT"}
        ]
        yield from stream_result
