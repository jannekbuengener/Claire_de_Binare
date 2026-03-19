from __future__ import annotations

import pytest

from services.execution.models import Order, OrderStatus
from services.execution.simulator_executor import SimulatorExecutor


@pytest.mark.unit
def test_simulator_executor_returns_market_like_fill() -> None:
    executor = SimulatorExecutor(order_book_depth=1_000_000.0, volatility=0.02)
    order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1, client_id="client-1")

    result = executor.execute_order(order)

    assert result.status == OrderStatus.FILLED.value
    assert result.order_id.startswith("SIM_")
    assert result.fill_id == result.order_id
    assert result.filled_quantity == pytest.approx(order.quantity)
    assert result.price is not None
    assert result.price > 50000.0


@pytest.mark.unit
def test_simulator_executor_rejects_when_modeled_depth_is_too_thin() -> None:
    executor = SimulatorExecutor(order_book_depth=10_000.0, volatility=0.02)
    order = Order(symbol="BTCUSDT", side="BUY", quantity=10.0, client_id="client-2")

    result = executor.execute_order(order)

    assert result.status == OrderStatus.REJECTED.value
    assert result.order_id.startswith("SIM_")
    assert result.fill_id is None
    assert result.filled_quantity == 0.0
    assert result.price is None
    assert result.error_message is not None
    assert "modeled depth" in result.error_message
