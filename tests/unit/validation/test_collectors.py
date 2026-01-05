"\"\"\"Unit tests for validation collectors.\"\"\""

from __future__ import annotations

import pytest

from services.validation.collectors import (
    ExecutionCollector,
    ExecutionCollectorConfig,
)


@pytest.mark.unit
def test_execution_collector_returns_deterministic_payloads() -> None:
    config = ExecutionCollectorConfig(db_url="postgres://example", redis_url="redis://0")
    collector = ExecutionCollector(config=config)

    orders = list(collector.collect_orders())
    results = list(collector.collect_results())

    assert orders == [
        {"order_id": "order-1", "symbol": "BTCUSDT", "filled_quantity": 0.1}
    ]
    assert results == [
        {"result_id": "result-1", "status": "FILLED", "symbol": "BTCUSDT"}
    ]
