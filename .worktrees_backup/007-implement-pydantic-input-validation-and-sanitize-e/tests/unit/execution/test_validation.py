"""
Unit Tests for Execution Service Validation Module.

Tests for OrderRequest Pydantic validation to address pen test finding M-01:
Order payloads from Redis pub/sub lack comprehensive validation.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md
"""

import pytest
from pydantic import ValidationError

from services.execution.validation import (
    OrderRequest,
    OrderValidationError,
    validate_order_payload,
    SYMBOL_PATTERN,
)
from services.execution.models import Order


# ============================================
# VALID ORDER TESTS
# ============================================


class TestValidOrderPayloads:
    """Test that valid order payloads are accepted."""

    @pytest.mark.unit
    def test_valid_order_payload_passes(self):
        """Test: Valid order payload is accepted and creates Order."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.5,
        }

        order = validate_order_payload(payload)

        assert isinstance(order, Order)
        assert order.symbol == "BTCUSDT"
        assert order.side == "BUY"
        assert order.quantity == 1.5

    @pytest.mark.unit
    def test_valid_order_with_all_fields(self):
        """Test: Valid order with all optional fields is accepted."""
        payload = {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "quantity": 0.5,
            "stop_loss_pct": 5.0,
            "strategy_id": "momentum_v1",
            "bot_id": "bot_001",
            "client_id": "client_abc",
            "timestamp": 1704067200,
            "type": "order",
        }

        order = validate_order_payload(payload)

        assert order.symbol == "ETHUSDT"
        assert order.side == "SELL"
        assert order.quantity == 0.5
        assert order.stop_loss_pct == 5.0
        assert order.strategy_id == "momentum_v1"
        assert order.bot_id == "bot_001"
        assert order.client_id == "client_abc"
        assert order.timestamp == 1704067200
        assert order.type == "order"

    @pytest.mark.unit
    def test_valid_order_lowercase_symbol_normalized(self):
        """Test: Lowercase symbol is normalized to uppercase."""
        payload = {
            "symbol": "btcusdt",
            "side": "BUY",
            "quantity": 1.0,
        }

        order = validate_order_payload(payload)

        assert order.symbol == "BTCUSDT"

    @pytest.mark.unit
    def test_valid_order_lowercase_side_normalized(self):
        """Test: Lowercase side is normalized to uppercase."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 1.0,
        }

        order = validate_order_payload(payload)

        assert order.side == "BUY"

    @pytest.mark.unit
    def test_valid_order_long_alias_converted_to_buy(self):
        """Test: LONG alias is converted to BUY."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 1.0,
        }

        order = validate_order_payload(payload)

        assert order.side == "BUY"

    @pytest.mark.unit
    def test_valid_order_short_alias_converted_to_sell(self):
        """Test: SHORT alias is converted to SELL."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "SHORT",
            "quantity": 1.0,
        }

        order = validate_order_payload(payload)

        assert order.side == "SELL"

    @pytest.mark.unit
    def test_valid_order_quantity_as_string(self):
        """Test: Quantity can be provided as numeric string."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "2.5",
        }

        order = validate_order_payload(payload)

        assert order.quantity == 2.5

    @pytest.mark.unit
    def test_valid_order_quantity_as_int(self):
        """Test: Quantity can be provided as integer."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 10,
        }

        order = validate_order_payload(payload)

        assert order.quantity == 10.0

    @pytest.mark.unit
    def test_valid_stop_loss_pct_boundary_zero(self):
        """Test: stop_loss_pct = 0 is valid (no stop loss)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": 0,
        }

        order = validate_order_payload(payload)

        assert order.stop_loss_pct == 0

    @pytest.mark.unit
    def test_valid_stop_loss_pct_boundary_hundred(self):
        """Test: stop_loss_pct = 100 is valid (maximum)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": 100,
        }

        order = validate_order_payload(payload)

        assert order.stop_loss_pct == 100

    @pytest.mark.unit
    def test_valid_order_with_none_stop_loss(self):
        """Test: None stop_loss_pct is valid (optional field)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": None,
        }

        order = validate_order_payload(payload)

        assert order.stop_loss_pct is None


# ============================================
# QUANTITY VALIDATION TESTS
# ============================================


class TestQuantityValidation:
    """Test quantity validation - must be positive (> 0)."""

    @pytest.mark.unit
    def test_negative_quantity_rejected(self):
        """Test: Negative quantity is rejected (pen test M-01)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": -1.5,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert "quantity" in str(exc_info.value).lower() or any(
            "quantity" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_zero_quantity_rejected(self):
        """Test: Zero quantity is rejected (pen test M-01)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        # Verify the error relates to quantity
        assert any(
            "quantity" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_very_small_positive_quantity_accepted(self):
        """Test: Very small positive quantity is accepted."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.00001,
        }

        order = validate_order_payload(payload)

        assert order.quantity == 0.00001

    @pytest.mark.unit
    def test_quantity_non_numeric_rejected(self):
        """Test: Non-numeric quantity is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "invalid",
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_quantity_none_rejected(self):
        """Test: None quantity is rejected as missing required field."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": None,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        # Should mention missing/required field
        error_str = str(exc_info.value.details)
        assert "quantity" in error_str.lower()


# ============================================
# SYMBOL VALIDATION TESTS
# ============================================


class TestSymbolValidation:
    """Test symbol format validation - must be alphanumeric uppercase."""

    @pytest.mark.unit
    def test_valid_symbol_formats(self):
        """Test: Various valid symbol formats are accepted."""
        valid_symbols = ["BTCUSDT", "ETHBTC", "SOLUSDT", "BTC123", "ABC"]

        for symbol in valid_symbols:
            payload = {
                "symbol": symbol,
                "side": "BUY",
                "quantity": 1.0,
            }
            order = validate_order_payload(payload)
            assert order.symbol == symbol.upper()

    @pytest.mark.unit
    def test_invalid_symbol_with_special_chars_rejected(self):
        """Test: Symbol with special characters is rejected (pen test M-01)."""
        payload = {
            "symbol": "BTC-USDT",
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert any(
            "symbol" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_invalid_symbol_with_spaces_rejected(self):
        """Test: Symbol with spaces is rejected."""
        payload = {
            "symbol": "BTC USDT",
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_invalid_symbol_with_underscore_rejected(self):
        """Test: Symbol with underscore is rejected."""
        payload = {
            "symbol": "BTC_USDT",
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_invalid_symbol_empty_string_rejected(self):
        """Test: Empty symbol string is rejected."""
        payload = {
            "symbol": "",
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_symbol_pattern_matches_alphanumeric(self):
        """Test: SYMBOL_PATTERN regex correctly validates symbols."""
        # Valid patterns
        assert SYMBOL_PATTERN.match("BTCUSDT")
        assert SYMBOL_PATTERN.match("ETH123")
        assert SYMBOL_PATTERN.match("A1B2C3")

        # Invalid patterns
        assert not SYMBOL_PATTERN.match("BTC-USDT")
        assert not SYMBOL_PATTERN.match("BTC USDT")
        assert not SYMBOL_PATTERN.match("btcusdt")  # lowercase
        assert not SYMBOL_PATTERN.match("")


# ============================================
# SIDE VALIDATION TESTS
# ============================================


class TestSideValidation:
    """Test side validation - must be BUY or SELL."""

    @pytest.mark.unit
    def test_valid_side_buy(self):
        """Test: BUY side is valid."""
        payload = {"symbol": "BTCUSDT", "side": "BUY", "quantity": 1.0}

        order = validate_order_payload(payload)

        assert order.side == "BUY"

    @pytest.mark.unit
    def test_valid_side_sell(self):
        """Test: SELL side is valid."""
        payload = {"symbol": "BTCUSDT", "side": "SELL", "quantity": 1.0}

        order = validate_order_payload(payload)

        assert order.side == "SELL"

    @pytest.mark.unit
    def test_invalid_side_rejected(self):
        """Test: Invalid side is rejected (pen test M-01)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "HOLD",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert any(
            "side" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_invalid_side_random_string_rejected(self):
        """Test: Random string side is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "RANDOM",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_invalid_side_numeric_rejected(self):
        """Test: Numeric side is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": 123,
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_invalid_side_empty_string_rejected(self):
        """Test: Empty string side is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)


# ============================================
# STOP LOSS PCT VALIDATION TESTS
# ============================================


class TestStopLossPctValidation:
    """Test stop_loss_pct validation - must be 0-100 if provided."""

    @pytest.mark.unit
    def test_stop_loss_pct_negative_rejected(self):
        """Test: Negative stop_loss_pct is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": -5.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert any(
            "stop_loss" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_stop_loss_pct_over_100_rejected(self):
        """Test: stop_loss_pct over 100 is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": 150.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_stop_loss_pct_non_numeric_rejected(self):
        """Test: Non-numeric stop_loss_pct is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": "invalid",
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(payload)

    @pytest.mark.unit
    def test_stop_loss_pct_valid_middle_range(self):
        """Test: stop_loss_pct in middle of range is valid."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "stop_loss_pct": 50.5,
        }

        order = validate_order_payload(payload)

        assert order.stop_loss_pct == 50.5


# ============================================
# MISSING REQUIRED FIELDS TESTS
# ============================================


class TestMissingRequiredFields:
    """Test that missing required fields are properly rejected."""

    @pytest.mark.unit
    def test_missing_symbol_rejected(self):
        """Test: Missing symbol is rejected."""
        payload = {
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert any(
            "symbol" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_missing_side_rejected(self):
        """Test: Missing side is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert any(
            "side" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_missing_quantity_rejected(self):
        """Test: Missing quantity is rejected."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert any(
            "quantity" in d.lower() for d in exc_info.value.details
        )

    @pytest.mark.unit
    def test_empty_payload_rejected(self):
        """Test: Empty payload is rejected with all required fields listed."""
        payload = {}

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        # Should list all missing required fields
        details_str = str(exc_info.value.details).lower()
        assert "symbol" in details_str or "required" in details_str

    @pytest.mark.unit
    def test_non_dict_payload_rejected(self):
        """Test: Non-dictionary payload is rejected."""
        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload("not a dict")

        assert "dictionary" in exc_info.value.message.lower()

    @pytest.mark.unit
    def test_none_payload_rejected(self):
        """Test: None payload is rejected."""
        with pytest.raises(OrderValidationError):
            validate_order_payload(None)

    @pytest.mark.unit
    def test_list_payload_rejected(self):
        """Test: List payload is rejected."""
        with pytest.raises(OrderValidationError):
            validate_order_payload([{"symbol": "BTCUSDT", "side": "BUY", "quantity": 1}])


# ============================================
# ORDERREQUEST PYDANTIC MODEL TESTS
# ============================================


class TestOrderRequestModel:
    """Direct tests for OrderRequest Pydantic model."""

    @pytest.mark.unit
    def test_order_request_valid_creation(self):
        """Test: OrderRequest can be created with valid data."""
        request = OrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.5,
        )

        assert request.symbol == "BTCUSDT"
        assert request.side == "BUY"
        assert request.quantity == 1.5

    @pytest.mark.unit
    def test_order_request_model_validate(self):
        """Test: OrderRequest.model_validate works correctly."""
        data = {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "quantity": 2.0,
        }

        request = OrderRequest.model_validate(data)

        assert request.symbol == "ETHUSDT"
        assert request.side == "SELL"
        assert request.quantity == 2.0

    @pytest.mark.unit
    def test_order_request_ignores_extra_fields(self):
        """Test: OrderRequest ignores unknown fields (forward compatibility)."""
        data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "unknown_field": "should_be_ignored",
            "another_field": 123,
        }

        request = OrderRequest.model_validate(data)

        assert request.symbol == "BTCUSDT"
        assert not hasattr(request, "unknown_field")


# ============================================
# ORDER VALIDATION ERROR TESTS
# ============================================


class TestOrderValidationError:
    """Tests for OrderValidationError exception class."""

    @pytest.mark.unit
    def test_order_validation_error_creation(self):
        """Test: OrderValidationError can be created with message and details."""
        error = OrderValidationError(
            message="Order validation failed",
            details=["Invalid symbol", "Invalid quantity"],
        )

        assert error.message == "Order validation failed"
        assert len(error.details) == 2
        assert "Invalid symbol" in error.details

    @pytest.mark.unit
    def test_order_validation_error_to_dict(self):
        """Test: OrderValidationError.to_dict() returns correct structure."""
        error = OrderValidationError(
            message="Validation failed",
            details=["Field error 1", "Field error 2"],
        )

        result = error.to_dict()

        assert result["error"] == "Validation failed"
        assert result["details"] == ["Field error 1", "Field error 2"]

    @pytest.mark.unit
    def test_order_validation_error_to_dict_no_details(self):
        """Test: OrderValidationError.to_dict() without details omits details key."""
        error = OrderValidationError(message="Simple error")

        result = error.to_dict()

        assert result["error"] == "Simple error"
        assert "details" not in result

    @pytest.mark.unit
    def test_order_validation_error_str(self):
        """Test: OrderValidationError string representation."""
        error = OrderValidationError(message="Test error")

        assert str(error) == "Test error"


# ============================================
# SECURITY TESTS (Information Disclosure)
# ============================================


class TestSecurityErrorMessages:
    """Test that error messages don't expose internal details."""

    @pytest.mark.unit
    def test_error_messages_are_safe(self):
        """Test: Validation error messages are safe for client display."""
        payload = {
            "symbol": "BTC-USDT",  # Invalid
            "side": "BUY",
            "quantity": -1,  # Invalid
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        # Error messages should not contain:
        # - Stack traces
        # - Internal paths
        # - Implementation details
        error_str = str(exc_info.value.details)
        assert "traceback" not in error_str.lower()
        assert "file" not in error_str.lower() or "field" in error_str.lower()
        assert "/services/" not in error_str

    @pytest.mark.unit
    def test_validation_error_contains_field_names(self):
        """Test: Validation errors reference the problematic field."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "INVALID",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        # Should mention which field has the error
        details_str = str(exc_info.value.details).lower()
        assert "side" in details_str
