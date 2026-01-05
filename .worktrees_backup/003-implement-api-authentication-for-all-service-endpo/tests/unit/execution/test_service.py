"""
Unit-Tests for Execution Service.

Tests the execution service Flask endpoints including API authentication.
Covers:
- Health endpoint (unauthenticated)
- Status endpoint (authenticated)
- Metrics endpoint (authenticated)
- Orders endpoint (authenticated)

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask

from core.api_auth import configure_auth, reset_auth


# ============================================
# FIXTURES
# ============================================


@pytest.fixture(autouse=True)
def reset_auth_state():
    """Reset auth state before and after each test"""
    reset_auth()
    yield
    reset_auth()


@pytest.fixture
def mock_redis():
    """Mock Redis client for execution service"""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.publish.return_value = 1
    return mock


@pytest.fixture
def mock_database():
    """Mock database for execution service"""
    mock = MagicMock()
    mock.get_stats.return_value = {"connections": 1, "queries": 0}
    mock.get_recent_orders.return_value = [
        {
            "order_id": "test-order-1",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.1,
            "status": "FILLED",
        }
    ]
    return mock


@pytest.fixture
def execution_app(mock_redis, mock_database):
    """
    Create a Flask test app with execution service endpoints.

    Mocks external dependencies (Redis, Database) and provides
    the execution service Flask endpoints for testing.
    """
    from flask import Flask, jsonify, Response
    from core.api_auth import require_api_key

    app = Flask(__name__)
    app.config["TESTING"] = True

    # Simulate execution service stats
    stats = {
        "orders_received": 10,
        "orders_filled": 8,
        "orders_rejected": 2,
        "start_time": "2025-01-01T00:00:00+00:00",
        "last_result": None,
    }

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint (no authentication)"""
        return jsonify({
            "service": "execution",
            "status": "ok",
            "version": "1.0.0",
        }), 200

    @app.route("/status", methods=["GET"])
    @require_api_key
    def status():
        """Status endpoint with statistics (requires authentication)"""
        return jsonify({
            "service": "execution",
            "version": "1.0.0",
            "mode": "mock",
            "stats": stats,
            "redis": {"connected": mock_redis.ping()},
            "database": mock_database.get_stats(),
        }), 200

    @app.route("/metrics", methods=["GET"])
    @require_api_key
    def metrics():
        """Metrics endpoint for Prometheus (requires authentication)"""
        body = (
            "# HELP execution_orders_received_total\n"
            "# TYPE execution_orders_received_total counter\n"
            f"execution_orders_received_total {stats['orders_received']}\n"
            "# HELP execution_orders_filled_total\n"
            "# TYPE execution_orders_filled_total counter\n"
            f"execution_orders_filled_total {stats['orders_filled']}\n"
        )
        return Response(body, mimetype="text/plain")

    @app.route("/orders", methods=["GET"])
    @require_api_key
    def orders():
        """Get recent orders (requires authentication)"""
        recent_orders = mock_database.get_recent_orders(limit=20)
        return jsonify({
            "count": len(recent_orders),
            "orders": recent_orders,
        }), 200

    return app


@pytest.fixture
def client(execution_app):
    """Create Flask test client"""
    return execution_app.test_client()


# ============================================
# TEST: Health Endpoint (Unauthenticated)
# ============================================


class TestHealthEndpoint:
    """Tests for /health endpoint (no authentication required)"""

    @pytest.mark.unit
    def test_health_returns_200_without_auth(self, client):
        """Test /health endpoint accessible without API key"""
        configure_auth(api_key="secret-key", enabled=True)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json["status"] == "ok"
        assert response.json["service"] == "execution"

    @pytest.mark.unit
    def test_health_returns_service_info(self, client):
        """Test /health returns service name and version"""
        response = client.get("/health")

        assert response.status_code == 200
        assert "service" in response.json
        assert "version" in response.json
        assert response.json["service"] == "execution"

    @pytest.mark.unit
    def test_health_accessible_when_auth_enabled(self, client):
        """Test /health remains accessible even with strict auth enabled"""
        configure_auth(api_key="strict-key", enabled=True, exempt_paths=["/health"])

        response = client.get("/health")

        assert response.status_code == 200


# ============================================
# TEST: Status Endpoint (Authenticated)
# ============================================


class TestStatusEndpoint:
    """Tests for /status endpoint (requires authentication)"""

    @pytest.mark.unit
    def test_status_returns_401_without_api_key(self, client):
        """Test /status returns 401 when no API key provided"""
        configure_auth(api_key="secret-key", enabled=True)

        response = client.get("/status")

        assert response.status_code == 401
        assert response.json["error"] == "Unauthorized"
        assert "API key required" in response.json["message"]

    @pytest.mark.unit
    def test_status_returns_403_with_invalid_api_key(self, client):
        """Test /status returns 403 with wrong API key"""
        configure_auth(api_key="correct-key", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "wrong-key"})

        assert response.status_code == 403
        assert response.json["error"] == "Forbidden"
        assert "Invalid API key" in response.json["message"]

    @pytest.mark.unit
    def test_status_returns_200_with_valid_api_key(self, client):
        """Test /status returns 200 with correct API key"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        assert response.json["service"] == "execution"
        assert "stats" in response.json
        assert "redis" in response.json
        assert "database" in response.json

    @pytest.mark.unit
    def test_status_returns_200_with_bearer_token(self, client):
        """Test /status accepts Bearer token authentication"""
        configure_auth(api_key="bearer-token", enabled=True)

        response = client.get(
            "/status",
            headers={"Authorization": "Bearer bearer-token"}
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_status_accessible_when_auth_disabled(self, client):
        """Test /status accessible without auth when auth is disabled"""
        configure_auth(api_key="secret-key", enabled=False)

        response = client.get("/status")

        assert response.status_code == 200


# ============================================
# TEST: Metrics Endpoint (Authenticated)
# ============================================


class TestMetricsEndpoint:
    """Tests for /metrics endpoint (requires authentication)"""

    @pytest.mark.unit
    def test_metrics_returns_401_without_api_key(self, client):
        """Test /metrics returns 401 when no API key provided"""
        configure_auth(api_key="metrics-key", enabled=True)

        response = client.get("/metrics")

        assert response.status_code == 401
        assert response.json["error"] == "Unauthorized"

    @pytest.mark.unit
    def test_metrics_returns_403_with_invalid_api_key(self, client):
        """Test /metrics returns 403 with wrong API key"""
        configure_auth(api_key="correct-key", enabled=True)

        response = client.get("/metrics", headers={"X-API-Key": "invalid"})

        assert response.status_code == 403
        assert response.json["error"] == "Forbidden"

    @pytest.mark.unit
    def test_metrics_returns_200_with_valid_api_key(self, client):
        """Test /metrics returns 200 with correct API key"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/metrics", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"

    @pytest.mark.unit
    def test_metrics_returns_prometheus_format(self, client):
        """Test /metrics returns Prometheus-compatible format"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/metrics", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert "execution_orders_received_total" in data
        assert "execution_orders_filled_total" in data
        assert "# HELP" in data
        assert "# TYPE" in data


# ============================================
# TEST: Orders Endpoint (Authenticated)
# ============================================


class TestOrdersEndpoint:
    """Tests for /orders endpoint (requires authentication - sensitive data)"""

    @pytest.mark.unit
    def test_orders_returns_401_without_api_key(self, client):
        """Test /orders returns 401 when no API key provided"""
        configure_auth(api_key="orders-key", enabled=True)

        response = client.get("/orders")

        assert response.status_code == 401
        assert response.json["error"] == "Unauthorized"

    @pytest.mark.unit
    def test_orders_returns_403_with_invalid_api_key(self, client):
        """Test /orders returns 403 with wrong API key"""
        configure_auth(api_key="correct-key", enabled=True)

        response = client.get("/orders", headers={"X-API-Key": "attacker-key"})

        assert response.status_code == 403
        assert response.json["error"] == "Forbidden"

    @pytest.mark.unit
    def test_orders_returns_200_with_valid_api_key(self, client):
        """Test /orders returns 200 with correct API key"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/orders", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        assert "orders" in response.json
        assert "count" in response.json

    @pytest.mark.unit
    def test_orders_returns_order_data(self, client):
        """Test /orders returns actual order data"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/orders", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        assert response.json["count"] == 1
        orders = response.json["orders"]
        assert len(orders) == 1
        assert orders[0]["symbol"] == "BTCUSDT"
        assert orders[0]["side"] == "buy"

    @pytest.mark.unit
    def test_orders_accessible_when_auth_disabled(self, client):
        """Test /orders accessible without auth when auth is disabled"""
        configure_auth(api_key="secret-key", enabled=False)

        response = client.get("/orders")

        assert response.status_code == 200


# ============================================
# TEST: Authentication Header Formats
# ============================================


class TestAuthenticationHeaders:
    """Tests for different API key header formats"""

    @pytest.mark.unit
    def test_x_api_key_header_accepted(self, client):
        """Test X-API-Key header is accepted"""
        configure_auth(api_key="test-key", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "test-key"})

        assert response.status_code == 200

    @pytest.mark.unit
    def test_bearer_token_accepted(self, client):
        """Test Authorization: Bearer header is accepted"""
        configure_auth(api_key="bearer-key", enabled=True)

        response = client.get(
            "/status",
            headers={"Authorization": "Bearer bearer-key"}
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_apikey_scheme_accepted(self, client):
        """Test Authorization: ApiKey header is accepted"""
        configure_auth(api_key="api-key-value", enabled=True)

        response = client.get(
            "/status",
            headers={"Authorization": "ApiKey api-key-value"}
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_x_api_key_takes_priority(self, client):
        """Test X-API-Key takes priority over Authorization header"""
        configure_auth(api_key="correct-key", enabled=True)

        # X-API-Key is correct, Authorization is wrong
        response = client.get(
            "/status",
            headers={
                "X-API-Key": "correct-key",
                "Authorization": "Bearer wrong-key"
            }
        )

        assert response.status_code == 200


# ============================================
# TEST: Error Response Format
# ============================================


class TestErrorResponses:
    """Tests for authentication error response format"""

    @pytest.mark.unit
    def test_401_response_format(self, client):
        """Test 401 response has correct format"""
        configure_auth(api_key="secret", enabled=True)

        response = client.get("/status")

        assert response.status_code == 401
        assert response.content_type == "application/json"
        assert "error" in response.json
        assert "message" in response.json
        assert response.json["error"] == "Unauthorized"

    @pytest.mark.unit
    def test_403_response_format(self, client):
        """Test 403 response has correct format"""
        configure_auth(api_key="secret", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "wrong"})

        assert response.status_code == 403
        assert response.content_type == "application/json"
        assert "error" in response.json
        assert "message" in response.json
        assert response.json["error"] == "Forbidden"


# ============================================
# TEST: Original Placeholder Tests (preserved)
# ============================================


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_service_initialization(mock_redis, mock_postgres, test_config):
    """
    Test: Execution Service kann initialisiert werden.

    Prüft, dass der Service mit Mock-Dependencies korrekt erstellt wird.
    """
    # TODO: Implement when ExecutionService class is available
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
