"""Unit tests for core.domain.models module."""
import pytest
from core.domain.models import Signal, Position, Order


def test_signal_creation():
    """Test Signal model creation."""
    signal = Signal(
        signal_id="sig_001",
        symbol="BTCUSD",
        direction="LONG",
        strength=0.8,
        timestamp=1000.0
    )
    assert signal.signal_id == "sig_001"
    assert signal.symbol == "BTCUSD"
    assert signal.direction == "LONG"
    assert signal.strength == 0.8


def test_position_creation():
    """Test Position model creation."""
    position = Position(
        position_id="pos_001",
        symbol="BTCUSD",
        size=1.0,
        entry_price=50000.0,
        current_price=51000.0
    )
    assert position.position_id == "pos_001"
    assert position.symbol == "BTCUSD"
    assert position.size == 1.0


def test_order_creation():
    """Test Order model creation."""
    order = Order(
        order_id="ord_001",
        symbol="BTCUSD",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )
    assert order.order_id == "ord_001"
    assert order.symbol == "BTCUSD"
    assert order.side == "BUY"
