"\"\"\"Unit-Tests für Execution-Service-Statistik und Publishing.\"\"\""

from __future__ import annotations

import json

import pytest

from services.execution import config, service
from services.execution.models import ExecutionResult, OrderStatus


class DummyRedisClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []
        self.streams: list[tuple[str, dict, int]] = []

    def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))

    def xadd(self, stream: str, payload: dict, maxlen: int) -> None:
        self.streams.append((stream, payload, maxlen))


class DummyDatabase:
    def __init__(self) -> None:
        self.saved_orders: list[ExecutionResult] = []
        self.saved_trades: list[ExecutionResult] = []

    def save_order(self, result: ExecutionResult) -> None:
        self.saved_orders.append(result)

    def save_trade(self, result: ExecutionResult) -> None:
        self.saved_trades.append(result)


def test_stats_increment_isolates_copy() -> None:
    original = service.stats.copy()
    try:
        service.set_stat("orders_received", 0)
        service.increment_stat("orders_received", 3)
        snapshot = service.get_stats_copy()
        assert snapshot["orders_received"] == 3
        snapshot["orders_received"] = 99
        assert service.get_stats_copy()["orders_received"] == 3
    finally:
        service.stats.clear()
        service.stats.update(original)


def test_publish_result_updates_stats_and_history(monkeypatch: pytest.MonkeyPatch) -> None:
    original = service.stats.copy()
    dummy_redis = DummyRedisClient()
    dummy_db = DummyDatabase()
    try:
        monkeypatch.setattr(service, "redis_client", dummy_redis)
        monkeypatch.setattr(service, "db", dummy_db)
        result = ExecutionResult(
            order_id="order-42",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.5,
            filled_quantity=0.5,
            status=OrderStatus.FILLED.value,
            price=42000.0,
        )
        service._publish_result(result)

        assert dummy_redis.published, "Redis-Publish fehlt"
        channel, payload_text = dummy_redis.published[0]
        assert channel == config.TOPIC_ORDER_RESULTS
        payload = json.loads(payload_text)
        assert payload["order_id"] == result.order_id
        assert dummy_redis.streams[0][0] == config.STREAM_ORDER_RESULTS
        assert dummy_db.saved_orders
        assert dummy_db.saved_trades
        stats_snapshot = service.get_stats_copy()
        assert stats_snapshot["last_result"]["order_id"] == result.order_id
    finally:
        service.stats.clear()
        service.stats.update(original)
