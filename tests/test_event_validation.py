"""Tests for event validation against JSON schemas."""

import pytest
from services.event_validation import (
    EventValidator,
    ValidationError,
    validate_event,
    is_valid_event,
)


@pytest.fixture
def validator():
    """Create an EventValidator instance for testing."""
    return EventValidator()


@pytest.mark.unit
class TestMarketDataValidation:
    """Tests for market_data event validation."""

    def test_valid_market_data_event(self, validator):
        """Test validation of a valid market_data event."""
        event = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            "timestamp": 1730443200000,
            "open": 35210.0,
            "high": 35280.5,
            "low": 35190.0,
            "close": 35250.5,
            "volume": 184.12,
            "interval": "1m"
        }

        # Should not raise
        validator.validate_market_data(event)
        assert validator.is_valid(event, "market_data")

    def test_missing_required_field(self, validator):
        """Test validation fails when required field is missing."""
        event = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            # Missing timestamp
            "close": 35250.5,
            "volume": 184.12,
            "interval": "1m"
        }

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_market_data(event)

        assert "timestamp" in str(exc_info.value).lower()

    def test_invalid_symbol_format(self, validator):
        """Test validation fails for invalid symbol format."""
        event = {
            "type": "market_data",
            "symbol": "btc_usdt",  # Lowercase not allowed
            "timestamp": 1730443200000,
            "close": 35250.5,
            "volume": 184.12,
            "interval": "1m"
        }

        with pytest.raises(ValidationError):
            validator.validate_market_data(event)

    def test_negative_price(self, validator):
        """Test validation fails for negative price."""
        event = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            "timestamp": 1730443200000,
            "close": -100.0,  # Negative not allowed
            "volume": 184.12,
            "interval": "1m"
        }

        with pytest.raises(ValidationError):
            validator.validate_market_data(event)

    def test_invalid_interval(self, validator):
        """Test validation fails for invalid interval."""
        event = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            "timestamp": 1730443200000,
            "close": 35250.5,
            "volume": 184.12,
            "interval": "2h"  # Not in enum
        }

        with pytest.raises(ValidationError):
            validator.validate_market_data(event)


@pytest.mark.unit
class TestSignalValidation:
    """Tests for signal event validation."""

    def test_valid_signal_event(self, validator):
        """Test validation of a valid signal event."""
        event = {
            "type": "signal",
            "symbol": "BTC_USDT",
            "direction": "BUY",
            "strength": 0.82,
            "reason": "MOMENTUM_BREAKOUT",
            "timestamp": 1730443260000,
            "strategy_id": "momentum_v1"
        }

        validator.validate_signal(event)
        assert validator.is_valid(event)

    def test_signal_with_side_instead_of_direction(self, validator):
        """Test signal with 'side' field instead of 'direction'."""
        event = {
            "type": "signal",
            "symbol": "BTC_USDT",
            "side": "SELL",  # Alternative to 'direction'
            "confidence": 0.75,
            "timestamp": 1730443260000
        }

        validator.validate_signal(event)
        assert validator.is_valid(event)

    def test_strength_out_of_range(self, validator):
        """Test validation fails when strength is out of 0-1 range."""
        event = {
            "type": "signal",
            "symbol": "BTC_USDT",
            "direction": "BUY",
            "strength": 1.5,  # > 1.0
            "timestamp": 1730443260000
        }

        with pytest.raises(ValidationError):
            validator.validate_signal(event)


@pytest.mark.unit
class TestRiskDecisionValidation:
    """Tests for risk_decision event validation."""

    def test_valid_risk_decision(self, validator):
        """Test validation of a valid risk_decision event."""
        event = {
            "type": "risk_decision",
            "symbol": "BTC_USDT",
            "requested_direction": "BUY",
            "approved": True,
            "approved_size": 0.05,
            "reason_code": "OK",
            "timestamp": 1730443270000
        }

        validator.validate_risk_decision(event)

    def test_risk_decision_with_checks(self, validator):
        """Test risk_decision with detailed risk_checks."""
        event = {
            "type": "risk_decision",
            "symbol": "BTC_USDT",
            "requested_direction": "BUY",
            "approved": False,
            "reason_code": "DAILY_DRAWDOWN_EXCEEDED",
            "timestamp": 1730443270000,
            "risk_checks": {
                "daily_drawdown": False,
                "exposure_limit": True,
                "position_size": True
            }
        }

        validator.validate_risk_decision(event)


@pytest.mark.unit
class TestOrderValidation:
    """Tests for order event validation."""

    def test_valid_market_order(self, validator):
        """Test validation of a valid market order."""
        event = {
            "type": "order",
            "order_id": "ORD_1730443270_BTC_USDT",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 0.05,
            "order_type": "MARKET",
            "timestamp": 1730443270000
        }

        validator.validate_order(event)

    def test_limit_order_with_price(self, validator):
        """Test that LIMIT orders can include a price field."""
        event = {
            "type": "order",
            "order_id": "ORD_1730443270_BTC_USDT",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 0.05,
            "order_type": "LIMIT",
            "price": 35000.0,  # Price for LIMIT order
            "timestamp": 1730443270000
        }

        # Should validate successfully (business logic validates price requirement)
        validator.validate_order(event)

    def test_negative_quantity(self, validator):
        """Test validation fails for negative quantity."""
        event = {
            "type": "order",
            "order_id": "ORD_1730443270_BTC_USDT",
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": -0.05,  # Negative not allowed
            "timestamp": 1730443270000
        }

        with pytest.raises(ValidationError):
            validator.validate_order(event)


@pytest.mark.unit
class TestOrderResultValidation:
    """Tests for order_result event validation."""

    def test_valid_filled_order(self, validator):
        """Test validation of a filled order result."""
        event = {
            "type": "order_result",
            "order_id": "ORD_1730443270_BTC_USDT",
            "status": "FILLED",
            "symbol": "BTC_USDT",
            "filled_quantity": 0.05,
            "price": 35260.1,
            "timestamp": 1730443280000
        }

        validator.validate_order_result(event)

    def test_rejected_order(self, validator):
        """Test validation of a rejected order result."""
        event = {
            "type": "order_result",
            "order_id": "ORD_1730443270_BTC_USDT",
            "status": "REJECTED",
            "symbol": "BTC_USDT",
            "timestamp": 1730443280000,
            "error_code": "INSUFFICIENT_BALANCE",
            "error_message": "Not enough USDT balance"
        }

        validator.validate_order_result(event)


@pytest.mark.unit
class TestAlertValidation:
    """Tests for alert event validation."""

    def test_valid_critical_alert(self, validator):
        """Test validation of a critical alert."""
        event = {
            "type": "alert",
            "level": "CRITICAL",
            "code": "DRAWDOWN_LIMIT_HIT",
            "message": "Maximaler Drawdown erreicht. Trading gestoppt.",
            "timestamp": 1730443300000,
            "service": "risk_manager",
            "action_required": True
        }

        validator.validate_alert(event)

    def test_warning_alert(self, validator):
        """Test validation of a warning alert."""
        event = {
            "type": "alert",
            "level": "WARNING",
            "code": "HIGH_SLIPPAGE",
            "message": "High slippage detected: 1.8%",
            "timestamp": 1730443300000,
            "symbol": "BTC_USDT"
        }

        validator.validate_alert(event)

    def test_invalid_alert_level(self, validator):
        """Test validation fails for invalid alert level."""
        event = {
            "type": "alert",
            "level": "MEDIUM",  # Not in enum
            "code": "RISK_LIMIT",
            "message": "Some message",
            "timestamp": 1730443300000
        }

        with pytest.raises(ValidationError):
            validator.validate_alert(event)


@pytest.mark.unit
class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_validate_event_function(self):
        """Test the global validate_event function."""
        event = {
            "type": "market_data",
            "symbol": "BTC_USDT",
            "timestamp": 1730443200000,
            "close": 35250.5,
            "volume": 184.12,
            "interval": "1m"
        }

        # Should not raise
        validate_event(event)

    def test_is_valid_event_function(self):
        """Test the global is_valid_event function."""
        valid_event = {
            "type": "signal",
            "symbol": "BTC_USDT",
            "direction": "BUY",
            "timestamp": 1730443260000
        }

        invalid_event = {
            "type": "signal",
            "symbol": "btc_usdt",  # Invalid format
            "timestamp": 1730443260000
        }

        assert is_valid_event(valid_event) is True
        assert is_valid_event(invalid_event) is False


@pytest.mark.unit
class TestEventValidatorConfiguration:
    """Tests for EventValidator configuration."""

    def test_strict_mode_enabled(self):
        """Test that unknown event types raise errors in strict mode."""
        validator = EventValidator(strict_mode=True)
        event = {"type": "unknown_event", "data": "test"}

        with pytest.raises(ValidationError):
            validator.validate_event(event)

    def test_strict_mode_disabled(self):
        """Test that unknown event types are logged in non-strict mode."""
        validator = EventValidator(strict_mode=False)
        event = {"type": "unknown_event", "data": "test"}

        # Should not raise (only log warning)
        validator.validate_event(event)
