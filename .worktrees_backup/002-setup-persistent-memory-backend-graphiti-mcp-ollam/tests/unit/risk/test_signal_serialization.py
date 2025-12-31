"""Unit tests for Signal.from_dict() deserialization."""

import pytest
from services.risk.models import Signal


@pytest.mark.unit
def test_signal_from_dict_minimal():
    """Test Signal.from_dict() with minimal required fields."""
    data = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "strength": 0.75,
        "timestamp": 1700000000.0,
    }
    signal = Signal.from_dict(data)

    assert signal.symbol == "BTCUSDT"
    assert signal.direction == "BUY"
    assert signal.strength == 0.75
    assert signal.timestamp == 1700000000.0
    assert signal.signal_id is None  # Optional field defaults to None
    assert signal.strategy_id is None


@pytest.mark.unit
def test_signal_from_dict_full():
    """Test Signal.from_dict() with all fields populated."""
    data = {
        "signal_id": "sig_001",
        "strategy_id": "strat_001",
        "bot_id": "bot_001",
        "symbol": "BTCUSDT",
        "direction": "SELL",
        "strength": 0.95,
        "timestamp": 1700000000.0,
        "side": "SELL",
        "confidence": 0.88,
        "reason": "Strong bearish signal",
        "price": 42000.50,
        "pct_change": -2.5,
    }
    signal = Signal.from_dict(data)

    assert signal.signal_id == "sig_001"
    assert signal.strategy_id == "strat_001"
    assert signal.bot_id == "bot_001"
    assert signal.symbol == "BTCUSDT"
    assert signal.direction == "SELL"
    assert signal.strength == 0.95
    assert signal.timestamp == 1700000000.0
    assert signal.side == "SELL"
    assert signal.confidence == 0.88
    assert signal.reason == "Strong bearish signal"
    assert signal.price == 42000.50
    assert signal.pct_change == -2.5


@pytest.mark.unit
def test_signal_roundtrip():
    """Test Signal.to_dict() -> from_dict() roundtrip preserves data."""
    original = Signal(
        signal_id="sig_roundtrip",
        strategy_id="strat_test",
        bot_id="bot_test",
        symbol="ETHUSDT",
        direction="BUY",
        strength=0.65,
        timestamp=1700000000.0,
        side="BUY",
        confidence=0.72,
        reason="Test signal",
        price=2100.25,
        pct_change=1.3,
    )

    # Serialize and deserialize
    data = original.to_dict()
    restored = Signal.from_dict(data)

    # Verify all fields match
    assert restored.signal_id == original.signal_id
    assert restored.strategy_id == original.strategy_id
    assert restored.bot_id == original.bot_id
    assert restored.symbol == original.symbol
    assert restored.direction == original.direction
    assert restored.strength == original.strength
    assert restored.timestamp == original.timestamp
    assert restored.side == original.side
    assert restored.confidence == original.confidence
    assert restored.reason == original.reason
    assert restored.price == original.price
    assert restored.pct_change == original.pct_change


@pytest.mark.unit
def test_signal_from_dict_type_coercion():
    """Test Signal.from_dict() handles type coercion correctly."""
    data = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "strength": "0.80",  # String should be coerced to float
        "timestamp": 1700000000,  # Int should be coerced to float
        "confidence": "0.75",  # String should be coerced to float
        "price": "42500.0",  # String should be coerced to float
        "pct_change": "1.5",  # String should be coerced to float
    }
    signal = Signal.from_dict(data)

    assert isinstance(signal.strength, float)
    assert signal.strength == 0.80
    assert isinstance(signal.timestamp, float)
    assert signal.timestamp == 1700000000.0
    assert isinstance(signal.confidence, float)
    assert signal.confidence == 0.75
    assert isinstance(signal.price, float)
    assert signal.price == 42500.0
    assert isinstance(signal.pct_change, float)
    assert signal.pct_change == 1.5


@pytest.mark.unit
def test_signal_from_dict_none_handling():
    """Test Signal.from_dict() handles None values correctly for optional fields."""
    data = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "strength": 0.70,
        "timestamp": 1700000000.0,
        "confidence": None,  # Explicitly None
        "price": None,  # Explicitly None
        "pct_change": None,  # Explicitly None
    }
    signal = Signal.from_dict(data)

    assert signal.confidence is None
    assert signal.price is None
    assert signal.pct_change is None
