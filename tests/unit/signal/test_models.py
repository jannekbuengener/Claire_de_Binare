"""
Unit-Tests für Signal Model.

Issue: #260 - Signal.from_dict() missing
"""

import pytest
from services.signal.models import Signal


@pytest.mark.unit
class TestSignalFromDict:
    """Tests für Signal.from_dict() Methode."""

    def test_from_dict_full_payload(self):
        """Test: from_dict mit vollständigem Payload."""
        payload = {
            "signal_id": "sig-123",
            "strategy_id": "strat-001",
            "bot_id": "bot-001",
            "symbol": "BTC/USDT",
            "direction": "BUY",
            "strength": 0.85,
            "timestamp": 1735000000,
            "side": "BUY",
            "confidence": 0.9,
            "reason": "momentum breakout",
            "price": 42000.0,
            "pct_change": 2.5,
        }

        signal = Signal.from_dict(payload)

        assert signal.signal_id == "sig-123"
        assert signal.strategy_id == "strat-001"
        assert signal.bot_id == "bot-001"
        assert signal.symbol == "BTC/USDT"
        assert signal.direction == "BUY"
        assert signal.strength == 0.85
        assert signal.timestamp == 1735000000
        assert signal.side == "BUY"
        assert signal.confidence == 0.9
        assert signal.reason == "momentum breakout"
        assert signal.price == 42000.0
        assert signal.pct_change == 2.5

    def test_from_dict_minimal_payload(self):
        """Test: from_dict mit minimalem Payload."""
        payload = {
            "symbol": "ETH/USDT",
            "direction": "SELL",
        }

        signal = Signal.from_dict(payload)

        assert signal.symbol == "ETH/USDT"
        assert signal.direction == "SELL"
        assert signal.signal_id is None
        assert signal.strength == 0.0
        assert signal.timestamp == 0.0

    def test_from_dict_empty_payload(self):
        """Test: from_dict mit leerem Payload verwendet Defaults."""
        payload = {}

        signal = Signal.from_dict(payload)

        assert signal.symbol == ""
        assert signal.direction == ""
        assert signal.strength == 0.0
        assert signal.signal_id is None

    def test_from_dict_to_dict_roundtrip(self):
        """Test: from_dict → to_dict Roundtrip erhält Daten."""
        original = {
            "signal_id": "roundtrip-test",
            "symbol": "SOL/USDT",
            "direction": "BUY",
            "strength": 0.75,
            "timestamp": 1735000000,
            "side": "BUY",
            "confidence": 0.8,
        }

        signal = Signal.from_dict(original)
        result = signal.to_dict()

        assert result["signal_id"] == original["signal_id"]
        assert result["symbol"] == original["symbol"]
        assert result["direction"] == original["direction"]
        assert result["strength"] == original["strength"]
        assert result["timestamp"] == original["timestamp"]
        assert result["side"] == original["side"]
        assert result["confidence"] == original["confidence"]

    def test_from_dict_strength_conversion(self):
        """Test: from_dict konvertiert strength zu float."""
        payload = {
            "symbol": "BTC/USDT",
            "strength": "0.95",  # String statt float
        }

        signal = Signal.from_dict(payload)

        assert signal.strength == 0.95
        assert isinstance(signal.strength, float)
