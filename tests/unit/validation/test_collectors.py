"\"\"\"Unit tests for the validation collector SQL logic.\"\"\""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from services.validation.collectors import ExecutionCollector, ExecutionCollectorConfig


class DummyCursor:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, tuple[Any, Any]]] = []

    def execute(self, query: str, params: tuple[Any, Any]) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[dict]:
        return self.rows

    def __enter__(self) -> "DummyCursor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None


class DummyConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.cursor_instance = DummyCursor(rows)
        self.closed = False

    def cursor(self, cursor_factory=None):
        return self.cursor_instance

    def close(self):
        self.closed = True


@pytest.mark.unit
def test_collect_execution_orders_normalizes_sql_results() -> None:
    now = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
    rows = [
        {
            "id": 42,
            "symbol": "BTCUSDT",
            "side": "buy",
            "size": 0.5,
            "effective_price": 42000.0,
            "price": 42000.0,
            "submitted_at": now,
            "status": "filled",
        }
    ]
    conn = DummyConnection(rows)
    config = ExecutionCollectorConfig(db_client=conn, redis_client=None)
    collector = ExecutionCollector(config=config)

    orders = collector.collect_execution_orders("2026-01-01", "2026-01-02")

    assert conn.cursor_instance.executed
    query, params = conn.cursor_instance.executed[0]
    assert "submitted_at >= %s" in query
    assert params == ("2026-01-01", "2026-01-02")

    assert orders == [
        {
            "id": 42,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "qty": 0.5,
            "price": 42000.0,
            "ts": now.isoformat(),
            "status": "FILLED",
        }
    ]
