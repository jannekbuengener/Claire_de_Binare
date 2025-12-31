"""
Unit-Tests für Execution Service.

Tests for order validation integration (M-01) and error sanitization (L-01).

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md

Note: Some placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import json
import pytest
from unittest.mock import MagicMock, Mock, patch

from services.execution.validation import OrderValidationError, validate_order_payload
from services.execution.error_handling import (
    ERROR_SERVICE_UNAVAILABLE,
    ERROR_DATABASE_UNAVAILABLE,
    sanitize_database_error,
)
from services.execution.models import OrderStatus


# ============================================
# PLACEHOLDER TESTS (Issue #308)
# ============================================


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_service_initialization(mock_redis, mock_postgres, test_config):
    """
    Test: Execution Service kann initialisiert werden.

    Prüft, dass der Service mit Mock-Dependencies korrekt erstellt wird.
    """
    # TODO: Implement when ExecutionService class is available
    # service = ExecutionService(redis_client=mock_redis, db_conn=mock_postgres, config=test_config)
    # assert service is not None
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_config_validation(test_config):
    """
    Test: Config wird korrekt validiert.

    Prüft, dass ungültige Configs abgelehnt werden.
    """
    # TODO: Implement config validation test
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_order_submission(mock_redis, order_factory):
    """
    Test: Order kann submitted werden.

    Prüft, dass Orders korrekt an die Exchange weitergeleitet werden.
    """
    # TODO: Implement order submission test
    pass


# ============================================
# PROCESS_ORDER VALIDATION INTEGRATION TESTS (M-01)
# ============================================


class TestProcessOrderValidationIntegration:
    """Test process_order integration with Pydantic validation (M-01 fix)."""

    @pytest.mark.unit
    def test_process_order_rejects_negative_quantity(self):
        """Test: process_order rejects negative quantity (pen test M-01)."""
        # Import service module with mocked dependencies
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish:

            from services.execution.service import process_order

            payload = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": -1.5,
            }

            result = process_order(payload)

            # Should return a REJECTED result
            assert result is not None
            assert result.status == OrderStatus.REJECTED.value
            assert "VALIDATION_" in result.order_id
            assert result.error_message == "Order validation failed"

    @pytest.mark.unit
    def test_process_order_rejects_zero_quantity(self):
        """Test: process_order rejects zero quantity (pen test M-01)."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish:

            from services.execution.service import process_order

            payload = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0,
            }

            result = process_order(payload)

            assert result is not None
            assert result.status == OrderStatus.REJECTED.value
            assert "VALIDATION_" in result.order_id

    @pytest.mark.unit
    def test_process_order_rejects_invalid_symbol(self):
        """Test: process_order rejects invalid symbol format (pen test M-01)."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish:

            from services.execution.service import process_order

            payload = {
                "symbol": "BTC-USDT",  # Invalid: contains hyphen
                "side": "BUY",
                "quantity": 1.5,
            }

            result = process_order(payload)

            assert result is not None
            assert result.status == OrderStatus.REJECTED.value
            assert "VALIDATION_" in result.order_id

    @pytest.mark.unit
    def test_process_order_rejects_invalid_side(self):
        """Test: process_order rejects invalid side (pen test M-01)."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish:

            from services.execution.service import process_order

            payload = {
                "symbol": "BTCUSDT",
                "side": "HOLD",  # Invalid: must be BUY or SELL
                "quantity": 1.5,
            }

            result = process_order(payload)

            assert result is not None
            assert result.status == OrderStatus.REJECTED.value
            assert "VALIDATION_" in result.order_id

    @pytest.mark.unit
    def test_process_order_rejects_missing_required_fields(self):
        """Test: process_order rejects payload with missing required fields."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish:

            from services.execution.service import process_order

            # Missing 'quantity' field
            payload = {
                "symbol": "BTCUSDT",
                "side": "BUY",
            }

            result = process_order(payload)

            assert result is not None
            assert result.status == OrderStatus.REJECTED.value

    @pytest.mark.unit
    def test_process_order_accepts_valid_payload(self):
        """Test: process_order accepts valid payload and executes order."""
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "FILLED"
        mock_executor.execute_order.return_value = mock_result

        with patch("services.execution.service.executor", mock_executor), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish, \
             patch("services.execution.service.bot_shutdown_active", False), \
             patch("services.execution.service.blocked_strategy_ids", set()), \
             patch("services.execution.service.blocked_bot_ids", set()):

            from services.execution.service import process_order

            payload = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 1.5,
            }

            result = process_order(payload)

            # Should execute the order
            mock_executor.execute_order.assert_called_once()
            assert result is not None

    @pytest.mark.unit
    def test_process_order_logs_validation_errors(self):
        """Test: process_order logs validation details but doesn't expose them."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish, \
             patch("services.execution.service.logger") as mock_logger:

            from services.execution.service import process_order

            payload = {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": -100,  # Invalid
            }

            result = process_order(payload)

            # Should log the validation error
            mock_logger.warning.assert_called()

            # Error message in result should be safe, generic message
            assert result.error_message == "Order validation failed"

    @pytest.mark.unit
    def test_process_order_publishes_rejected_result_for_invalid_payload(self):
        """Test: process_order publishes REJECTED result for invalid payloads."""
        mock_publish = MagicMock()

        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result", mock_publish):

            from services.execution.service import process_order

            payload = {
                "symbol": "INVALID-SYMBOL",
                "side": "BUY",
                "quantity": 1.0,
            }

            result = process_order(payload)

            # Should publish the rejected result
            mock_publish.assert_called_once()
            # Verify the published result is REJECTED
            published_result = mock_publish.call_args[0][0]
            assert published_result.status == OrderStatus.REJECTED.value

    @pytest.mark.unit
    def test_process_order_increments_rejected_stat_for_invalid_payload(self):
        """Test: process_order increments orders_rejected stat for invalid payloads."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result"), \
             patch("services.execution.service.increment_stat") as mock_stat:

            from services.execution.service import process_order

            payload = {
                "symbol": "BTCUSDT",
                "side": "INVALID",
                "quantity": 1.0,
            }

            result = process_order(payload)

            # Should increment orders_rejected
            mock_stat.assert_called_with("orders_rejected")

    @pytest.mark.unit
    def test_process_order_ignores_non_order_events(self):
        """Test: process_order ignores events with non-order type."""
        with patch("services.execution.service.executor", None), \
             patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.db", MagicMock()), \
             patch("services.execution.service._publish_result") as mock_publish:

            from services.execution.service import process_order

            payload = {
                "type": "heartbeat",  # Non-order event
                "timestamp": 1234567890,
            }

            result = process_order(payload)

            # Should return None without validation error
            assert result is None
            # Should not publish any result
            mock_publish.assert_not_called()


# ============================================
# /ORDERS ENDPOINT ERROR SANITIZATION TESTS (L-01)
# ============================================


class TestOrdersEndpointErrorSanitization:
    """Test /orders endpoint returns sanitized error responses (L-01 fix)."""

    @pytest.fixture
    def app_client(self):
        """Create Flask test client with mocked dependencies."""
        # Import app after patching dependencies
        with patch("services.execution.service.redis_client", MagicMock()), \
             patch("services.execution.service.executor", MagicMock()), \
             patch("services.execution.service.pubsub", MagicMock()):
            from services.execution.service import app
            app.config["TESTING"] = True
            with app.test_client() as client:
                yield client

    @pytest.mark.unit
    def test_orders_endpoint_returns_503_when_db_not_initialized(self, app_client):
        """Test: /orders returns 503 with safe message when DB not initialized."""
        with patch("services.execution.service.db", None):
            response = app_client.get("/orders")

            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["error"] == ERROR_SERVICE_UNAVAILABLE
            assert data["code"] == "SERVICE_UNAVAILABLE"

    @pytest.mark.unit
    def test_orders_endpoint_returns_sanitized_error_on_db_exception(self, app_client):
        """Test: /orders returns sanitized error on database exception (L-01 fix)."""
        mock_db = MagicMock()
        mock_db.get_recent_orders.side_effect = Exception(
            "FATAL: password authentication failed for user 'admin'"
        )

        with patch("services.execution.service.db", mock_db):
            response = app_client.get("/orders")

            # Should return 503 (service unavailable)
            assert response.status_code == 503
            data = json.loads(response.data)

            # Error message should be safe, not exposing internal details
            assert data["error"] == ERROR_DATABASE_UNAVAILABLE
            assert "password" not in str(data)
            assert "admin" not in str(data)
            assert "FATAL" not in str(data)

    @pytest.mark.unit
    def test_orders_endpoint_includes_request_id(self, app_client):
        """Test: /orders error response includes request_id for debugging."""
        mock_db = MagicMock()
        mock_db.get_recent_orders.side_effect = Exception("Database error")

        with patch("services.execution.service.db", mock_db):
            response = app_client.get("/orders")

            data = json.loads(response.data)
            assert "request_id" in data
            assert len(data["request_id"]) > 0

    @pytest.mark.unit
    def test_orders_endpoint_no_stack_traces(self, app_client):
        """Test: /orders error response contains no stack traces."""
        mock_db = MagicMock()
        mock_db.get_recent_orders.side_effect = ValueError(
            "Error at line 123 in /app/services/execution/database.py"
        )

        with patch("services.execution.service.db", mock_db):
            response = app_client.get("/orders")

            data = json.loads(response.data)
            response_str = str(data)

            # Should not contain file paths or line numbers
            assert "/app/" not in response_str
            assert "database.py" not in response_str
            assert "line 123" not in response_str

    @pytest.mark.unit
    def test_orders_endpoint_success_response(self, app_client):
        """Test: /orders returns order data on success."""
        mock_db = MagicMock()
        mock_db.get_recent_orders.return_value = [
            {"order_id": "test123", "symbol": "BTCUSDT", "status": "FILLED"}
        ]

        with patch("services.execution.service.db", mock_db):
            response = app_client.get("/orders")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert "orders" in data
            assert "count" in data
            assert data["count"] == 1


# ============================================
# VALIDATION MODULE INTEGRATION TESTS
# ============================================


class TestValidationModuleIntegration:
    """Test validation module integration with service layer."""

    @pytest.mark.unit
    def test_validate_order_payload_returns_order_dataclass(self):
        """Test: validate_order_payload returns Order dataclass instance."""
        from services.execution.models import Order

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
    def test_validate_order_payload_raises_order_validation_error(self):
        """Test: validate_order_payload raises OrderValidationError on invalid input."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "INVALID",
            "quantity": 1.5,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        assert exc_info.value.message == "Order validation failed"
        assert len(exc_info.value.details) > 0

    @pytest.mark.unit
    def test_order_validation_error_has_safe_message(self):
        """Test: OrderValidationError contains safe, user-facing message."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": -1,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        # Error message should be generic
        assert "Order validation failed" in exc_info.value.message

        # Details should mention the field but not expose internals
        details_str = str(exc_info.value.details)
        assert "quantity" in details_str.lower()
        # Should not contain internal paths or traceback info
        assert "services/execution" not in details_str
        assert "traceback" not in details_str.lower()


# ============================================
# ERROR HANDLING INTEGRATION TESTS
# ============================================


class TestErrorHandlingIntegration:
    """Test error handling module integration with service layer."""

    @pytest.mark.unit
    def test_sanitize_database_error_returns_safe_response(self):
        """Test: sanitize_database_error returns SafeErrorResponse."""
        from services.execution.error_handling import SafeErrorResponse

        exception = Exception("Connection refused to postgresql://admin:secret@localhost:5432/db")

        response = sanitize_database_error(exception, request_id="test-123")

        assert isinstance(response, SafeErrorResponse)
        assert response.message == ERROR_DATABASE_UNAVAILABLE
        assert response.request_id == "test-123"
        assert response.http_status == 503

        # Should not contain sensitive info
        assert "postgresql" not in response.message
        assert "admin" not in response.message
        assert "secret" not in response.message

    @pytest.mark.unit
    def test_safe_error_response_to_dict(self):
        """Test: SafeErrorResponse.to_dict() produces valid JSON structure."""
        from services.execution.error_handling import SafeErrorResponse

        response = SafeErrorResponse(
            code="TEST_ERROR",
            message="Test message",
            request_id="abc123",
            http_status=500,
        )

        result = response.to_dict()

        assert result["error"] == "Test message"
        assert result["code"] == "TEST_ERROR"
        assert result["request_id"] == "abc123"

        # Should be JSON serializable
        json_str = json.dumps(result)
        assert len(json_str) > 0


# ============================================
# SECURITY TESTS
# ============================================


class TestSecurityValidationIntegration:
    """Security tests for validation integration (pen test M-01, L-01)."""

    @pytest.mark.unit
    def test_validation_prevents_negative_quantity_attack(self):
        """Test: Validation prevents negative quantity manipulation attack (M-01)."""
        # Attack vector: negative quantity to steal funds
        attack_payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": -1000000,  # Attacker tries to steal funds
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(attack_payload)

    @pytest.mark.unit
    def test_validation_prevents_sql_injection_in_symbol(self):
        """Test: Validation prevents SQL injection in symbol field."""
        # Attack vector: SQL injection in symbol
        attack_payload = {
            "symbol": "BTCUSDT'; DROP TABLE orders;--",
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError):
            validate_order_payload(attack_payload)

    @pytest.mark.unit
    def test_error_messages_do_not_expose_internal_paths(self):
        """Test: Error messages do not expose internal file paths (L-01)."""
        payload = {
            "symbol": "INVALID-SYMBOL",
            "side": "BUY",
            "quantity": 1.0,
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        error_str = str(exc_info.value.details)

        # Should not expose internal paths
        assert "/services/" not in error_str
        assert "/app/" not in error_str
        assert ".py" not in error_str or "type" in error_str.lower()

    @pytest.mark.unit
    def test_error_messages_do_not_expose_python_types(self):
        """Test: Error messages do not expose Python type names (L-01)."""
        payload = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "not-a-number",
        }

        with pytest.raises(OrderValidationError) as exc_info:
            validate_order_payload(payload)

        error_str = str(exc_info.value.details)

        # Should not expose internal Python type names
        assert "NoneType" not in error_str
        assert "__main__" not in error_str
