'"""Integrationstest: Execution-Service-Pipeline und Metrics Publishing."""'

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from core.utils.seed import Seed, SeedManager
from services.execution import mock_executor as execution_mock_executor, service
from services.execution.mock_executor import MockExecutor
from services.execution.models import OrderStatus
from services.risk.models import Order as RiskOrder


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

    def save_order(self, result: object) -> None:
        self.saved_orders.append(result.order_id)

    def persist_correlation_event(self, **kwargs) -> bool:
        """No-op stub for Phase 8C (not validated by this test)."""
        return True


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
            # Phase 8C: Correlation IDs for fail-closed semantics
            "signal_id": "test-sig-PIPE-001",
            "decision_id": "test-dec-PIPE-001",
            "order_id": "test-ord-PIPE-001",
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
        stats_after = service.get_stats_copy()
        assert stats_after["orders_received"] == stats_before["orders_received"] + 1
        assert stats_after["orders_filled"] == stats_before["orders_filled"] + 1
    finally:
        service.stats.clear()
        service.stats.update(stats_before)
        Seed.set(None)


@pytest.mark.integration
def test_shadow_order_blocks_via_risk_contract_and_exports_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stats_before = service.stats.copy()
    service.stats.clear()
    service.stats.update(
        {
            "orders_received": 0,
            "orders_filled": 0,
            "orders_rejected": 0,
            "shadow_blocked": 0,
            "invalid_payloads": 0,
            "start_time": stats_before["start_time"],
            "last_result": None,
        }
    )
    redis_stub = DummyRedisClient()
    db_stub = DummyDatabase()
    executor = MagicMock()
    executor.execute_order.side_effect = AssertionError(
        "shadow order must not reach executor"
    )

    try:
        monkeypatch.setattr(service, "executor", executor)
        monkeypatch.setattr(service, "redis_client", redis_stub)
        monkeypatch.setattr(service, "db", db_stub)
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
        monkeypatch.setattr(
            "core.safety.kill_switch.get_kill_switch_details",
            lambda create_if_missing=False: (False, None, None, None),
        )

        risk_order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            stop_loss_pct=0.02,
            signal_id="test-sig-shadow-001",
            reason="integration-shadow-proof",
            timestamp=1700000000,
            strategy_id="shadow-proof",
            bot_id="bot-shadow",
            client_id="shadow-client-1",
            order_id="test-ord-shadow-001",
            decision_id="test-dec-shadow-001",
            trace_id="test-trace-shadow-001",
            decision_contract_v1={
                "input": {
                    "run_mode": "shadow",
                    "order": {"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001},
                },
                "output": {},
            },
        )
        payload = risk_order.to_dict()

        assert payload["run_mode"] == "shadow"
        assert payload["decision_contract_v1"]["input"]["run_mode"] == "shadow"

        result = service.process_order(payload)

        assert result is not None
        assert result.status == OrderStatus.REJECTED.value
        assert "shadow mode" in (result.error_message or "").lower()
        executor.execute_order.assert_not_called()
        assert db_stub.saved_orders == ["test-ord-shadow-001"]
        assert len(redis_stub.published) == 1

        channel, text = redis_stub.published[0]
        assert "order_results" in channel
        published = json.loads(text)
        assert published["order_id"] == "test-ord-shadow-001"
        assert published["status"] == OrderStatus.REJECTED.value
        assert "shadow mode" in published["error_message"].lower()
        assert float(published["filled_quantity"]) == 0.0

        stats_after = service.get_stats_copy()
        assert stats_after["orders_received"] == 1
        assert stats_after["orders_filled"] == 0
        assert stats_after["orders_rejected"] == 1
        assert stats_after["shadow_blocked"] == 1

        metrics_handler = getattr(service, "metrics", None)
        if service.app is not None and metrics_handler is not None:
            with service.app.test_request_context("/metrics"):
                metrics_response = metrics_handler()
            metrics_text = metrics_response.get_data(as_text=True)
            assert "execution_orders_filled_total 0" in metrics_text
            assert "execution_shadow_blocked_total 1" in metrics_text
    finally:
        service.stats.clear()
        service.stats.update(stats_before)
