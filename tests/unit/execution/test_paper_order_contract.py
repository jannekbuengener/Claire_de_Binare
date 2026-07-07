"""Paper order creation contract tests (#3835)."""

from __future__ import annotations

import pytest

from services.execution.models import ExecutionResult, OrderStatus
from services.execution.paper_trading import OrderType, PaperTradingEngine
from services.execution import service

from tests.unit.execution._execution_boundary_contract_helpers import (
    ExecutionHarness,
    execution_harness,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def persist_correlation_event(self, **kwargs) -> bool:
        self.calls.append(dict(kwargs))
        return True


class _FakeExecutor:
    def __init__(self, *, exchange_order_id: str) -> None:
        self.exchange_order_id = exchange_order_id

    def execute_order(self, order):
        return ExecutionResult(
            order_id=self.exchange_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=order.quantity,
            status=OrderStatus.FILLED.value,
            price=50000.0,
            client_id=order.client_id,
            fill_id=self.exchange_order_id,
            strategy_id=order.strategy_id,
            bot_id=order.bot_id,
        )


def test_paper_trading_engine_creates_pending_order_with_id() -> None:
    engine = PaperTradingEngine(initial_balance=10000.0)
    engine.start_paper_trading()
    engine.update_market_price("BTCUSDT", 50000.0)
    order_id = engine.place_order("BTCUSDT", "buy", 0.01, OrderType.MARKET)
    assert order_id.startswith("paper_")
    assert order_id in engine.orders


def test_process_order_persists_paper_prefixed_canonical_order_id(
    execution_harness: ExecutionHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.safety.kill_switch as kill_switch

    monkeypatch.setattr(
        kill_switch,
        "get_kill_switch_details",
        lambda create_if_missing=False: (False, "inactive", None, None),
    )
    fake_db = _FakeDb()
    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(
        service,
        "executor",
        _FakeExecutor(exchange_order_id="MOCK_123"),
    )
    monkeypatch.setattr(service, "_publish_result", lambda _result: None)

    result = service.process_order(
        {
            "type": "order",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "strategy_id": "primary_breakout_v1",
            "signal_id": "sig-unit-1",
            "decision_id": "dec-unit-1",
            "order_id": "paper_1700000000000",
        }
    )
    assert result is not None
    assert fake_db.calls
    assert fake_db.calls[0]["order_id"] == "paper_1700000000000"
