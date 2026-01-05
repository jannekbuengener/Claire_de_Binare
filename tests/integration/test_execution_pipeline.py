"\"\"\"Integrationstest: Execution-Service-Pipeline und Metrics Publishing.\"\"\""

from __future__ import annotations

import json

import pytest

from core.utils.seed import Seed, SeedManager
from services.execution import mock_executor as execution_mock_executor, service
from services.execution.mock_executor import MockExecutor
from services.execution.models import OrderStatus


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
        self.saved_orders: list[str] = []
        self.saved_trades: list[str] = []

    def save_order(self, result: object) -> None:
        self.saved_orders.append(result.order_id)

    def save_trade(self, result: object) -> None:
        self.saved_trades.append(result.order_id)


@pytest.mark.integration
def test_process_order_publishes_real_result(monkeypatch: pytest.MonkeyPatch) -> None:
    stats_before = service.stats.copy()
    redis_stub = DummyRedisClient()
    db_stub = DummyDatabase()
    Seed.set(4242)
    seed_manager = SeedManager(Seed.get())
    executor = MockExecutor(
        success_rate=1.0,
        min_latency_ms=0,
        max_latency_ms=0,
        base_slippage_pct=0.0,
        seed_manager=seed_manager,
    )
    try:
        monkeypatch.setattr(service, "executor", executor)
        monkeypatch.setattr(service, "redis_client", redis_stub)
        monkeypatch.setattr(service, "db", db_stub)
        monkeypatch.setattr(execution_mock_executor.time, "sleep", lambda _: None)

        payload = {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "quantity": 0.2,
            "type": "order",
            "strategy_id": "e2e-strat",
            "bot_id": "bot-101",
            "client_id": "client-1",
        }

        result = service.process_order(payload)
        assert result is not None
        assert result.status == OrderStatus.FILLED.value
        assert redis_stub.published
        channel, text = redis_stub.published[0]
        assert "order_results" in channel
        data = json.loads(text)
        assert data["symbol"] == payload["symbol"]
        assert db_stub.saved_orders
        assert db_stub.saved_trades
        stats_after = service.get_stats_copy()
        assert stats_after["orders_received"] == stats_before["orders_received"] + 1
        assert stats_after["orders_filled"] == stats_before["orders_filled"] + 1
    finally:
        service.stats.clear()
        service.stats.update(stats_before)
        Seed.set(None)
