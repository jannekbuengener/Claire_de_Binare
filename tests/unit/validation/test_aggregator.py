"\"\"\"Unit tests for the validation aggregator.\"\"\""

from __future__ import annotations

import pytest

from services.validation.aggregator import aggregate_orders


@pytest.mark.unit
def test_aggregate_orders_happy_path() -> None:
    orders = [
        {"status": "FILLED", "symbol": "BTCUSDT", "qty": 0.5, "price": 42000},
        {"status": "REJECTED", "symbol": "ETHUSDT", "qty": 0.2, "price": 2500},
        {"status": "FILLED", "symbol": "BTCUSDT", "qty": 0.1, "price": 42500},
    ]
    summary = aggregate_orders(orders)

    assert summary["orders_total"] == 3
    assert summary["filled_total"] == 2
    assert summary["not_filled_total"] == 1
    assert summary["symbols"] == 2
    assert summary["qty_sum"] == pytest.approx(0.8)
    assert summary["avg_price"] == pytest.approx((42000 + 2500 + 42500) / 3)


@pytest.mark.unit
def test_aggregate_orders_empty() -> None:
    summary = aggregate_orders([])
    assert summary == {
        "orders_total": 0,
        "filled_total": 0,
        "not_filled_total": 0,
        "symbols": 0,
        "qty_sum": 0,
        "avg_price": 0.0,
    }
