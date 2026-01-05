"""
Unit tests for core.security_headers module.
Tests security headers middleware for Flask applications.
Addresses L-04 from penetration test report.
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask

from core.security_headers import (
    SecurityHeadersConfig,
    add_security_headers,
    init_security_headers,
    DEFAULT_X_CONTENT_TYPE_OPTIONS,
    DEFAULT_X_FRAME_OPTIONS,
    DEFAULT_X_XSS_PROTECTION,
    DEFAULT_CONTENT_SECURITY_POLICY,
    DEFAULT_STRICT_TRANSPORT_SECURITY,
    DEFAULT_REFERRER_POLICY,
    DEFAULT_PERMISSIONS_POLICY,
)


class TestSecurityHeadersConfig:
    """Tests for SecurityHeadersConfig class"""

    def test_default_enabled(self, monkeypatch):
        """Test security headers are enabled by default"""
        monkeypatch.delenv("SECURITY_HEADERS_ENABLED", raising=False)
        config = SecurityHeadersConfig()
        assert config.enabled is True

    def test_default_hsts_enabled(self, monkeypatch):
        """Test HSTS is enabled by default"""
        monkeypatch.delenv("SECURITY_HEADERS_HSTS_ENABLED", raising=False)
        config = SecurityHeadersConfig()
        assert config.hsts_enabled is True

    def test_disabled_via_env(self, monkeypatch):
        """Test security headers can be disabled via environment"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "false")
        config = SecurityHeadersConfig()
        assert config.enabled is False

    def test_hsts_disabled_via_env(self, monkeypatch):
        """Test HSTS can be disabled via environment"""
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "false")
        config = SecurityHeadersConfig()
        assert config.hsts_enabled is False

    def test_case_insensitive_boolean(self, monkeypatch):
        """Test boolean parsing is case insensitive"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "TRUE")
        config = SecurityHeadersConfig()
        assert config.enabled is True

        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "False")
        config = SecurityHeadersConfig()
        assert config.enabled is False

    def test_default_header_values(self, monkeypatch):
        """Test default header values are correct"""
        # Clear any env overrides
        for env_var in [
            "SECURITY_HEADER_X_CONTENT_TYPE_OPTIONS",
            "SECURITY_HEADER_X_FRAME_OPTIONS",
            "SECURITY_HEADER_X_XSS_PROTECTION",
            "SECURITY_HEADER_CSP",
            "SECURITY_HEADER_HSTS",
            "SECURITY_HEADER_REFERRER_POLICY",
            "SECURITY_HEADER_PERMISSIONS_POLICY",
        ]:
            monkeypatch.delenv(env_var, raising=False)

        config = SecurityHeadersConfig()

        assert config.x_content_type_options == DEFAULT_X_CONTENT_TYPE_OPTIONS
        assert config.x_frame_options == DEFAULT_X_FRAME_OPTIONS
        assert config.x_xss_protection == DEFAULT_X_XSS_PROTECTION
        assert config.content_security_policy == DEFAULT_CONTENT_SECURITY_POLICY
        assert config.strict_transport_security == DEFAULT_STRICT_TRANSPORT_SECURITY
        assert config.referrer_policy == DEFAULT_REFERRER_POLICY
        assert config.permissions_policy == DEFAULT_PERMISSIONS_POLICY

    def test_custom_x_content_type_options(self, monkeypatch):
        """Test X-Content-Type-Options can be customized"""
        monkeypatch.setenv("SECURITY_HEADER_X_CONTENT_TYPE_OPTIONS", "custom-value")
        config = SecurityHeadersConfig()
        assert config.x_content_type_options == "custom-value"

    def test_custom_x_frame_options(self, monkeypatch):
        """Test X-Frame-Options can be customized"""
        monkeypatch.setenv("SECURITY_HEADER_X_FRAME_OPTIONS", "SAMEORIGIN")
        config = SecurityHeadersConfig()
        assert config.x_frame_options == "SAMEORIGIN"

    def test_custom_x_xss_protection(self, monkeypatch):
        """Test X-XSS-Protection can be customized"""
        monkeypatch.setenv("SECURITY_HEADER_X_XSS_PROTECTION", "0")
        config = SecurityHeadersConfig()
        assert config.x_xss_protection == "0"

    def test_custom_csp(self, monkeypatch):
        """Test Content-Security-Policy can be customized"""
        custom_csp = "default-src 'none'; script-src 'self'"
        monkeypatch.setenv("SECURITY_HEADER_CSP", custom_csp)
        config = SecurityHeadersConfig()
        assert config.content_security_policy == custom_csp

    def test_custom_hsts(self, monkeypatch):
        """Test Strict-Transport-Security can be customized"""
        custom_hsts = "max-age=86400"
        monkeypatch.setenv("SECURITY_HEADER_HSTS", custom_hsts)
        config = SecurityHeadersConfig()
        assert config.strict_transport_security == custom_hsts

    def test_custom_referrer_policy(self, monkeypatch):
        """Test Referrer-Policy can be customized"""
        monkeypatch.setenv("SECURITY_HEADER_REFERRER_POLICY", "no-referrer")
        config = SecurityHeadersConfig()
        assert config.referrer_policy == "no-referrer"

    def test_custom_permissions_policy(self, monkeypatch):
        """Test Permissions-Policy can be customized"""
        custom_pp = "geolocation=(self), microphone=()"
        monkeypatch.setenv("SECURITY_HEADER_PERMISSIONS_POLICY", custom_pp)
        config = SecurityHeadersConfig()
        assert config.permissions_policy == custom_pp


class TestAddSecurityHeaders:
    """Tests for add_security_headers() function"""

    @pytest.fixture
    def mock_response(self):
        """Create a mock Flask response"""
        response = Mock()
        response.headers = {}
        return response

    @pytest.fixture
    def enabled_config(self, monkeypatch):
        """Config with security headers enabled"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "true")
        return SecurityHeadersConfig()

    @pytest.fixture
    def disabled_config(self, monkeypatch):
        """Config with security headers disabled"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "false")
        return SecurityHeadersConfig()

    def test_adds_all_headers_when_enabled(self, mock_response, enabled_config):
        """Test all security headers are added when enabled"""
        result = add_security_headers(mock_response, enabled_config)

        assert result is mock_response
        assert "X-Content-Type-Options" in mock_response.headers
        assert "X-Frame-Options" in mock_response.headers
        assert "X-XSS-Protection" in mock_response.headers
        assert "Content-Security-Policy" in mock_response.headers
        assert "Strict-Transport-Security" in mock_response.headers
        assert "Referrer-Policy" in mock_response.headers
        assert "Permissions-Policy" in mock_response.headers

    def test_correct_header_values(self, mock_response, enabled_config):
        """Test headers have correct default values"""
        add_security_headers(mock_response, enabled_config)

        assert mock_response.headers["X-Content-Type-Options"] == "nosniff"
        assert mock_response.headers["X-Frame-Options"] == "DENY"
        assert mock_response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "default-src 'self'" in mock_response.headers["Content-Security-Policy"]
        assert "max-age=31536000" in mock_response.headers["Strict-Transport-Security"]
        assert mock_response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "geolocation=()" in mock_response.headers["Permissions-Policy"]

    def test_no_headers_when_disabled(self, mock_response, disabled_config):
        """Test no headers are added when disabled"""
        result = add_security_headers(mock_response, disabled_config)

        assert result is mock_response
        assert "X-Content-Type-Options" not in mock_response.headers
        assert "X-Frame-Options" not in mock_response.headers
        assert "X-XSS-Protection" not in mock_response.headers
        assert "Content-Security-Policy" not in mock_response.headers
        assert "Strict-Transport-Security" not in mock_response.headers
        assert "Referrer-Policy" not in mock_response.headers
        assert "Permissions-Policy" not in mock_response.headers

    def test_hsts_not_added_when_hsts_disabled(self, mock_response, monkeypatch):
        """Test HSTS header not added when specifically disabled"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "false")
        config = SecurityHeadersConfig()

        add_security_headers(mock_response, config)

        # Other headers should be present
        assert "X-Content-Type-Options" in mock_response.headers
        assert "X-Frame-Options" in mock_response.headers
        # HSTS should NOT be present
        assert "Strict-Transport-Security" not in mock_response.headers

    def test_uses_default_config_if_none_provided(self, mock_response, monkeypatch):
        """Test default config is used when none provided"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "true")

        add_security_headers(mock_response, None)

        # Should still add headers using default config
        assert "X-Content-Type-Options" in mock_response.headers

    def test_response_returned(self, mock_response, enabled_config):
        """Test response object is returned"""
        result = add_security_headers(mock_response, enabled_config)
        assert result is mock_response


class TestInitSecurityHeaders:
    """Tests for init_security_headers() function"""

    @pytest.fixture
    def flask_app(self):
        """Create a minimal Flask application for testing"""
        app = Flask(__name__)

        @app.route("/test")
        def test_endpoint():
            return "OK"

        @app.route("/health")
        def health():
            return {"status": "healthy"}

        return app

    def test_registers_after_request_handler(self, flask_app, monkeypatch):
        """Test that after_request handler is registered"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")

        initial_handlers = len(flask_app.after_request_funcs.get(None, []))
        init_security_headers(flask_app)
        final_handlers = len(flask_app.after_request_funcs.get(None, []))

        assert final_handlers == initial_handlers + 1

    def test_headers_added_to_responses(self, flask_app, monkeypatch):
        """Test headers are added to all responses"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "true")

        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/test")

            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"
            assert response.headers.get("X-XSS-Protection") == "1; mode=block"
            assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")
            assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")
            assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert "geolocation=()" in response.headers.get("Permissions-Policy", "")

    def test_headers_on_health_endpoint(self, flask_app, monkeypatch):
        """Test headers are added to health check endpoints"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")

        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/health")

            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"

    def test_no_headers_when_disabled(self, flask_app, monkeypatch):
        """Test no headers when middleware is disabled"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "false")

        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/test")

            # Standard Flask headers may exist, but not our security headers
            assert response.headers.get("X-Content-Type-Options") is None
            assert response.headers.get("X-Frame-Options") is None
            assert response.headers.get("Strict-Transport-Security") is None

    def test_custom_config(self, flask_app, monkeypatch):
        """Test using custom configuration"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADER_X_FRAME_OPTIONS", "SAMEORIGIN")

        config = SecurityHeadersConfig()
        init_security_headers(flask_app, config)

        with flask_app.test_client() as client:
            response = client.get("/test")

            # Custom value should be used
            assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_logs_initialization(self, flask_app, monkeypatch):
        """Test initialization is logged"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")

        with patch("core.security_headers.logger") as mock_logger:
            init_security_headers(flask_app)
            mock_logger.info.assert_called_once()
            assert "initialized" in mock_logger.info.call_args[0][0]

    def test_logs_warning_when_disabled(self, flask_app, monkeypatch):
        """Test warning is logged when disabled"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "false")

        with patch("core.security_headers.logger") as mock_logger:
            init_security_headers(flask_app)
            mock_logger.warning.assert_called_once()
            assert "DISABLED" in mock_logger.warning.call_args[0][0]


class TestDefaultValues:
    """Tests for default security header values"""

    def test_x_content_type_options_default(self):
        """Test X-Content-Type-Options default value prevents MIME sniffing"""
        assert DEFAULT_X_CONTENT_TYPE_OPTIONS == "nosniff"

    def test_x_frame_options_default(self):
        """Test X-Frame-Options default value prevents clickjacking"""
        assert DEFAULT_X_FRAME_OPTIONS == "DENY"

    def test_x_xss_protection_default(self):
        """Test X-XSS-Protection default enables browser XSS filter"""
        assert DEFAULT_X_XSS_PROTECTION == "1; mode=block"

    def test_csp_default_contains_self(self):
        """Test Content-Security-Policy includes 'self' directive"""
        assert "default-src 'self'" in DEFAULT_CONTENT_SECURITY_POLICY
        assert "script-src 'self'" in DEFAULT_CONTENT_SECURITY_POLICY

    def test_csp_default_blocks_framing(self):
        """Test CSP blocks framing by default"""
        assert "frame-ancestors 'none'" in DEFAULT_CONTENT_SECURITY_POLICY

    def test_hsts_default_one_year(self):
        """Test HSTS default is one year (31536000 seconds)"""
        assert "max-age=31536000" in DEFAULT_STRICT_TRANSPORT_SECURITY
        assert "includeSubDomains" in DEFAULT_STRICT_TRANSPORT_SECURITY

    def test_referrer_policy_default(self):
        """Test Referrer-Policy default is secure"""
        assert DEFAULT_REFERRER_POLICY == "strict-origin-when-cross-origin"

    def test_permissions_policy_default(self):
        """Test Permissions-Policy disables dangerous features"""
        assert "geolocation=()" in DEFAULT_PERMISSIONS_POLICY
        assert "microphone=()" in DEFAULT_PERMISSIONS_POLICY
        assert "camera=()" in DEFAULT_PERMISSIONS_POLICY


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    @pytest.fixture
    def flask_app(self):
        """Create a Flask app with various response types"""
        app = Flask(__name__)

        @app.route("/json")
        def json_response():
            return {"key": "value"}, 200

        @app.route("/error")
        def error_response():
            return "Error", 500

        @app.route("/redirect")
        def redirect_response():
            from flask import redirect
            return redirect("/test")

        @app.route("/empty")
        def empty_response():
            return "", 204

        return app

    def test_headers_on_json_response(self, flask_app, monkeypatch):
        """Test headers are added to JSON responses"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/json")

            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"

    def test_headers_on_error_response(self, flask_app, monkeypatch):
        """Test headers are added to error responses"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/error")

            assert response.status_code == 500
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"

    def test_headers_on_redirect_response(self, flask_app, monkeypatch):
        """Test headers are added to redirect responses"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/redirect", follow_redirects=False)

            assert response.status_code == 302
            assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_headers_on_empty_response(self, flask_app, monkeypatch):
        """Test headers are added to empty 204 responses"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/empty")

            assert response.status_code == 204
            assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_post_request_headers(self, flask_app, monkeypatch):
        """Test headers are added to POST responses"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")

        @flask_app.route("/post", methods=["POST"])
        def post_endpoint():
            return {"received": True}, 201

        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.post("/post")

            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"

    def test_multiple_init_calls(self, flask_app, monkeypatch):
        """Test multiple init calls don't duplicate headers"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")

        # Initialize twice
        init_security_headers(flask_app)
        init_security_headers(flask_app)

        with flask_app.test_client() as client:
            response = client.get("/json")

            # Header value should still be correct (not duplicated)
            assert response.headers.get("X-Content-Type-Options") == "nosniff"


class TestIntegration:
    """Integration tests for real-world scenarios"""

    def test_full_security_header_set(self, monkeypatch):
        """Test all required security headers are present in response"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "true")

        app = Flask(__name__)

        @app.route("/api/data")
        def api_endpoint():
            return {"data": [1, 2, 3]}, 200

        init_security_headers(app)

        with app.test_client() as client:
            response = client.get("/api/data")

            # All L-04 required headers present
            assert response.headers.get("X-Content-Type-Options") is not None
            assert response.headers.get("X-Frame-Options") is not None
            assert response.headers.get("X-XSS-Protection") is not None
            assert response.headers.get("Content-Security-Policy") is not None
            assert response.headers.get("Strict-Transport-Security") is not None
            # Additional headers
            assert response.headers.get("Referrer-Policy") is not None
            assert response.headers.get("Permissions-Policy") is not None

    def test_development_mode_no_hsts(self, monkeypatch):
        """Test typical development configuration (HSTS disabled)"""
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADERS_HSTS_ENABLED", "false")

        app = Flask(__name__)

        @app.route("/test")
        def test_endpoint():
            return "OK"

        init_security_headers(app)

        with app.test_client() as client:
            response = client.get("/test")

            # Other headers present
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"
            # HSTS not present (safe for dev)
            assert response.headers.get("Strict-Transport-Security") is None

    def test_custom_csp_for_spa(self, monkeypatch):
        """Test custom CSP configuration for single-page application"""
        custom_csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
        monkeypatch.setenv("SECURITY_HEADER_CSP", custom_csp)

        app = Flask(__name__)

        @app.route("/")
        def index():
            return "<html><body>SPA</body></html>"

        init_security_headers(app)

        with app.test_client() as client:
            response = client.get("/")

            assert response.headers.get("Content-Security-Policy") == custom_csp
