"""
Unit-Tests for Risk Manager Service.

Tests the risk service Flask endpoints including API authentication.
Covers:
- Health endpoint (unauthenticated)
- Status endpoint (authenticated) - exposes positions, exposure, PnL
- Metrics endpoint (authenticated)

Governance: CDB_AGENT_POLICY.md, CDB_RL_SAFETY_POLICY.md

Note: Placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import pytest
from unittest.mock import MagicMock
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
def mock_stats():
    """Mock risk manager statistics"""
    return {
        "started_at": "2025-01-01T00:00:00+00:00",
        "signals_received": 100,
        "orders_approved": 75,
        "orders_blocked": 25,
        "alerts_generated": 10,
        "order_results_received": 70,
        "orders_rejected_execution": 5,
        "last_order_result": {
            "order_id": "order-123",
            "status": "FILLED",
            "symbol": "BTCUSDT",
            "filled_quantity": 0.1,
        },
        "status": "running",
    }


@pytest.fixture
def mock_risk_state():
    """Mock risk state data"""
    return {
        "total_exposure": 5000.0,
        "daily_pnl": 150.0,
        "open_positions": 3,
        "signals_approved": 75,
        "signals_blocked": 25,
        "circuit_breaker": False,
        "positions": {
            "BTCUSDT": 0.1,
            "ETHUSDT": 1.5,
            "SOLUSDT": 10.0,
        },
        "pending_orders": 2,
        "last_prices": {
            "BTCUSDT": 42000.0,
            "ETHUSDT": 2500.0,
            "SOLUSDT": 100.0,
        },
    }


@pytest.fixture
def risk_app(mock_stats, mock_risk_state):
    """
    Create a Flask test app with risk service endpoints.

    Mocks external dependencies and provides the risk service
    Flask endpoints for testing.
    """
    from flask import Flask, jsonify, Response
    from core.api_auth import require_api_key

    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/health", methods=["GET"])
    def health():
        """Health-Check Endpoint (no authentication)"""
        return jsonify({
            "status": "ok" if mock_stats["status"] == "running" else "error",
            "service": "risk_manager",
            "version": "0.1.0",
        }), 200

    @app.route("/status", methods=["GET"])
    @require_api_key
    def status():
        """Status & Risk State (requires authentication)"""
        return jsonify({
            **mock_stats,
            "risk_state": mock_risk_state,
        }), 200

    @app.route("/metrics", methods=["GET"])
    @require_api_key
    def metrics():
        """Prometheus Metriken (requires authentication)"""
        body = (
            "# HELP orders_approved_total Orders freigegeben\n"
            "# TYPE orders_approved_total counter\n"
            f"orders_approved_total {mock_stats['orders_approved']}\n\n"
            "# HELP orders_blocked_total Orders blockiert\n"
            "# TYPE orders_blocked_total counter\n"
            f"orders_blocked_total {mock_stats['orders_blocked']}\n\n"
            "# HELP circuit_breaker_active Circuit Breaker Status\n"
            "# TYPE circuit_breaker_active gauge\n"
            f"circuit_breaker_active {1 if mock_risk_state['circuit_breaker'] else 0}\n\n"
            "# HELP order_results_received_total Anzahl verarbeiteter Order-Result Events\n"
            "# TYPE order_results_received_total counter\n"
            f"order_results_received_total {mock_stats['order_results_received']}\n\n"
            "# HELP risk_pending_orders_total Anzahl offener Auftragsbestaetigungen\n"
            "# TYPE risk_pending_orders_total gauge\n"
            f"risk_pending_orders_total {mock_risk_state['pending_orders']}\n\n"
            "# HELP risk_total_exposure_value Gesamtposition (Notional)\n"
            "# TYPE risk_total_exposure_value gauge\n"
            f"risk_total_exposure_value {mock_risk_state['total_exposure']}\n"
        )
        return Response(body, mimetype="text/plain")

    return app


@pytest.fixture
def client(risk_app):
    """Create Flask test client"""
    return risk_app.test_client()


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
        assert response.json["service"] == "risk_manager"

    @pytest.mark.unit
    def test_health_returns_service_info(self, client):
        """Test /health returns service name and version"""
        response = client.get("/health")

        assert response.status_code == 200
        assert "service" in response.json
        assert "version" in response.json
        assert response.json["service"] == "risk_manager"
        assert response.json["version"] == "0.1.0"

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
    """Tests for /status endpoint (requires authentication - exposes sensitive data)"""

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
        assert response.json["status"] == "running"
        assert "risk_state" in response.json
        assert "signals_received" in response.json
        assert "orders_approved" in response.json

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

    @pytest.mark.unit
    def test_status_returns_risk_state_data(self, client):
        """Test /status returns complete risk state information"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        risk_state = response.json["risk_state"]
        assert "total_exposure" in risk_state
        assert "daily_pnl" in risk_state
        assert "positions" in risk_state
        assert "pending_orders" in risk_state
        assert "circuit_breaker" in risk_state
        assert "last_prices" in risk_state

    @pytest.mark.unit
    def test_status_exposes_position_details(self, client):
        """Test /status includes detailed position data (sensitive)"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        positions = response.json["risk_state"]["positions"]
        assert "BTCUSDT" in positions
        assert "ETHUSDT" in positions
        assert positions["BTCUSDT"] == 0.1


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
        assert "orders_approved_total" in data
        assert "orders_blocked_total" in data
        assert "circuit_breaker_active" in data
        assert "risk_total_exposure_value" in data
        assert "# HELP" in data
        assert "# TYPE" in data

    @pytest.mark.unit
    def test_metrics_accessible_when_auth_disabled(self, client):
        """Test /metrics accessible without auth when auth is disabled"""
        configure_auth(api_key="secret-key", enabled=False)

        response = client.get("/metrics")

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
    Test: Risk Manager kann initialisiert werden.
    """
    # TODO: Implement when RiskManager class is available
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_config_validation(test_config):
    """
    Test: Config wird korrekt validiert (Hard Limits).
    """
    # TODO: Implement config validation (max_exposure, max_drawdown, etc.)
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_action_masking(signal_factory):
    """
    Test: Action Masking blockiert verbotene Aktionen.

    Governance: CDB_RL_SAFETY_POLICY.md (Deterministic Guardrails)
    """
    # TODO: Implement action masking test
    # signal = signal_factory(signal_type="buy")
    # masked_action = risk_manager.apply_action_mask(signal, current_state)
    # assert masked_action in allowed_actions
    pass
