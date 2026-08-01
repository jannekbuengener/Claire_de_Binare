"""Risk producer tests for the explicit reduce-only order contract."""

from __future__ import annotations

import pytest

from services.risk.models import Order

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_risk_order_serializes_explicit_reduce_only() -> None:
    order = Order(
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.5,
        stop_loss_pct=0.02,
        signal_id="signal-4184",
        reason="proactive_unwind:over_limit",
        timestamp=1700000000,
        strategy_id="paper",
        order_id="order-4184",
        decision_id="decision-4184",
        reduce_only=True,
    )

    assert order.to_dict()["reduce_only"] is True


def test_risk_order_defaults_to_non_reduce_only() -> None:
    order = Order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.5,
        stop_loss_pct=0.02,
        signal_id="signal-entry-4184",
        reason="entry",
        timestamp=1700000000,
        strategy_id="paper",
    )

    assert order.to_dict()["reduce_only"] is False
