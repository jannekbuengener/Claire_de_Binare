"""
Unit-Tests for Signal Engine Service.

Tests the signal service Flask endpoints including API authentication.
Covers:
- Health endpoint (unauthenticated)
- Status endpoint (authenticated)
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
    """Mock signal engine statistics"""
    return {
        "started_at": "2025-01-01T00:00:00+00:00",
        "signals_generated": 42,
        "last_signal": {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735689600,
        },
        "status": "running",
    }


@pytest.fixture
def signal_app(mock_stats):
    """
    Create a Flask test app with signal service endpoints.

    Mocks external dependencies and provides the signal service
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
            "service": "signal_engine",
            "version": "0.1.0",
        }), 200

    @app.route("/status", methods=["GET"])
    @require_api_key
    def status():
        """Status & Statistiken (requires authentication)"""
        return jsonify(mock_stats), 200

    @app.route("/metrics", methods=["GET"])
    @require_api_key
    def metrics():
        """Prometheus Metriken (requires authentication)"""
        body = (
            "# HELP signals_generated_total Anzahl generierter Signale\n"
            "# TYPE signals_generated_total counter\n"
            f"signals_generated_total {mock_stats['signals_generated']}\n\n"
            "# HELP signal_engine_status Service Status (1=running, 0=stopped)\n"
            "# TYPE signal_engine_status gauge\n"
            f"signal_engine_status {1 if mock_stats['status'] == 'running' else 0}\n"
        )
        return Response(body, mimetype="text/plain")

    return app


@pytest.fixture
def client(signal_app):
    """Create Flask test client"""
    return signal_app.test_client()


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
        assert response.json["service"] == "signal_engine"

    @pytest.mark.unit
    def test_health_returns_service_info(self, client):
        """Test /health returns service name and version"""
        response = client.get("/health")

        assert response.status_code == 200
        assert "service" in response.json
        assert "version" in response.json
        assert response.json["service"] == "signal_engine"
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
        assert response.json["status"] == "running"
        assert "signals_generated" in response.json
        assert "started_at" in response.json

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
    def test_status_returns_signal_stats(self, client):
        """Test /status returns signal generation statistics"""
        configure_auth(api_key="valid-key", enabled=True)

        response = client.get("/status", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        assert response.json["signals_generated"] == 42
        assert response.json["last_signal"]["symbol"] == "BTCUSDT"
        assert response.json["last_signal"]["side"] == "BUY"


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
        assert "signals_generated_total" in data
        assert "signal_engine_status" in data
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
def test_service_initialization(mock_redis, test_config):
    """
    Test: Signal Engine kann initialisiert werden.
    """
    # TODO: Implement when SignalEngine class is available
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_config_validation(test_config):
    """
    Test: Config wird korrekt validiert.
    """
    # TODO: Implement config validation test
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_signal_generation(mock_redis):
    """
    Test: Signals werden korrekt generiert.

    Prüft, dass RL-Policy Signals mit korrektem Format erzeugt.
    """
    # TODO: Implement signal generation test
    # signal = signal_engine.generate_signal(market_data)
    # assert signal.symbol == "BTCUSDT"
    # assert signal.signal_type in ["buy", "sell", "hold"]
    pass
