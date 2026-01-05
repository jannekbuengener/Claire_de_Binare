"\"\"\"Unit tests for validation collectors.\"\"\""

from __future__ import annotations

import pytest

from services.validation.collectors import (
    ExecutionCollector,
    ExecutionCollectorConfig,
)


class DummyDBClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def fetch_execution_orders(self, start: str, end: str) -> list[dict]:
        self.calls.append((start, end))
        return [
            {
                "id": "order-1",
                "symbol": "btcusdt",
                "side": "buy",
                "quantity": "0.3",
                "price": "42000",
                "timestamp": "2026-01-05T00:00:00Z",
                "status": "FILLED",
            }
        ]


class DummyRedisClient:
    def __init__(self) -> None:
        self.calls = []

    def xrange(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return []


@pytest.mark.unit
def test_execution_collector_normalizes_db_output() -> None:
    db = DummyDBClient()
    redis = DummyRedisClient()
    config = ExecutionCollectorConfig(db_client=db, redis_client=redis)
    collector = ExecutionCollector(config=config)

    orders = collector.collect_execution_orders("2026-01-01", "2026-01-05")

    assert db.calls == [("2026-01-01", "2026-01-05")]
    assert orders == [
        {
            "id": "order-1",
            "symbol": "btcusdt",
            "side": "BUY",
            "qty": 0.3,
            "price": 42000.0,
            "ts": "2026-01-05T00:00:00Z",
            "status": "FILLED",
        }
    ]
