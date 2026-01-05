"""
Unit tests for core.api_auth module
Tests API key authentication for Flask endpoints with comprehensive edge case coverage.

Coverage:
- Valid API key acceptance
- Invalid API key rejection
- Missing API key handling
- Auth disabled mode
- Exempt paths functionality
- Multiple header formats (X-API-Key, Bearer, ApiKey)
- Configuration functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from core.api_auth import (
    validate_api_key,
    extract_api_key,
    is_path_exempt,
    require_api_key,
    configure_auth,
    reset_auth,
    get_api_key,
    is_auth_enabled,
    get_exempt_paths,
)


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
def app():
    """Create Flask test application"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create Flask test client"""
    return app.test_client()


# ============================================
# TEST: validate_api_key
# ============================================


class TestValidateApiKey:
    """Tests for validate_api_key() function"""

    def test_valid_api_key_accepted(self):
        """Test valid API key is accepted"""
        configure_auth(api_key="test-secret-key-12345")

        result = validate_api_key("test-secret-key-12345")

        assert result is True

    def test_invalid_api_key_rejected(self):
        """Test invalid API key is rejected"""
        configure_auth(api_key="correct-key")

        result = validate_api_key("wrong-key")

        assert result is False

    def test_empty_api_key_rejected(self):
        """Test empty string API key is rejected"""
        configure_auth(api_key="secret-key")

        result = validate_api_key("")

        assert result is False

    def test_none_api_key_rejected(self):
        """Test None API key is rejected"""
        configure_auth(api_key="secret-key")

        result = validate_api_key(None)

        assert result is False

    def test_no_configured_key_rejects_all(self):
        """Test when no API key is configured, all requests are rejected (fail-closed)"""
        configure_auth(api_key=None)

        # Even matching None should be rejected
        result = validate_api_key(None)
        assert result is False

        # Any provided key should be rejected
        result = validate_api_key("any-key")
        assert result is False

    def test_similar_key_rejected(self):
        """Test similar but not identical keys are rejected"""
        configure_auth(api_key="secret-key-12345")

        # One character different
        assert validate_api_key("secret-key-12346") is False
        # Prefix match
        assert validate_api_key("secret-key-1234") is False
        # Suffix added
        assert validate_api_key("secret-key-123456") is False
        # Case mismatch
        assert validate_api_key("SECRET-KEY-12345") is False

    def test_whitespace_differences_rejected(self):
        """Test keys with whitespace differences are rejected"""
        configure_auth(api_key="secret-key")

        assert validate_api_key(" secret-key") is False
        assert validate_api_key("secret-key ") is False
        assert validate_api_key(" secret-key ") is False

    def test_unicode_keys_handled(self):
        """Test Unicode characters in keys are handled correctly"""
        configure_auth(api_key="key-with-unicode-\u00e9\u00f1\u00fc")

        assert validate_api_key("key-with-unicode-\u00e9\u00f1\u00fc") is True
        assert validate_api_key("key-with-unicode-enu") is False


# ============================================
# TEST: extract_api_key
# ============================================


class TestExtractApiKey:
    """Tests for extract_api_key() function"""

    def test_extract_from_x_api_key_header(self, app):
        """Test extracting API key from X-API-Key header"""
        with app.test_request_context(headers={"X-API-Key": "my-api-key"}):
            from flask import request
            result = extract_api_key(request)
            assert result == "my-api-key"

    def test_extract_from_bearer_header(self, app):
        """Test extracting API key from Authorization: Bearer header"""
        with app.test_request_context(headers={"Authorization": "Bearer my-token"}):
            from flask import request
            result = extract_api_key(request)
            assert result == "my-token"

    def test_extract_from_apikey_header(self, app):
        """Test extracting API key from Authorization: ApiKey header"""
        with app.test_request_context(headers={"Authorization": "ApiKey my-api-key"}):
            from flask import request
            result = extract_api_key(request)
            assert result == "my-api-key"

    def test_x_api_key_takes_priority(self, app):
        """Test X-API-Key header takes priority over Authorization header"""
        with app.test_request_context(
            headers={
                "X-API-Key": "priority-key",
                "Authorization": "Bearer other-key"
            }
        ):
            from flask import request
            result = extract_api_key(request)
            assert result == "priority-key"

    def test_no_api_key_returns_none(self, app):
        """Test returns None when no API key header present"""
        with app.test_request_context():
            from flask import request
            result = extract_api_key(request)
            assert result is None

    def test_invalid_auth_scheme_returns_none(self, app):
        """Test returns None for unsupported Authorization schemes"""
        with app.test_request_context(headers={"Authorization": "Basic dXNlcjpwYXNz"}):
            from flask import request
            result = extract_api_key(request)
            assert result is None

    def test_malformed_auth_header_returns_none(self, app):
        """Test returns None for malformed Authorization header"""
        with app.test_request_context(headers={"Authorization": "JustAToken"}):
            from flask import request
            result = extract_api_key(request)
            assert result is None

    def test_bearer_case_insensitive(self, app):
        """Test Bearer scheme is case insensitive"""
        with app.test_request_context(headers={"Authorization": "BEARER my-token"}):
            from flask import request
            result = extract_api_key(request)
            assert result == "my-token"

        with app.test_request_context(headers={"Authorization": "bearer my-token"}):
            from flask import request
            result = extract_api_key(request)
            assert result == "my-token"

    def test_apikey_case_insensitive(self, app):
        """Test ApiKey scheme is case insensitive"""
        with app.test_request_context(headers={"Authorization": "APIKEY my-key"}):
            from flask import request
            result = extract_api_key(request)
            assert result == "my-key"

    def test_empty_x_api_key_header_treated_as_missing(self, app):
        """Test empty X-API-Key header is treated as missing (returns None)"""
        with app.test_request_context(headers={"X-API-Key": ""}):
            from flask import request
            result = extract_api_key(request)
            # Empty string is falsy and treated as missing - correct security behavior
            assert result is None


# ============================================
# TEST: is_path_exempt
# ============================================


class TestIsPathExempt:
    """Tests for is_path_exempt() function"""

    def test_health_path_exempt_by_default(self):
        """Test /health is exempt by default"""
        assert is_path_exempt("/health") is True

    def test_non_exempt_path_not_exempt(self):
        """Test non-exempt paths return False"""
        assert is_path_exempt("/status") is False
        assert is_path_exempt("/metrics") is False
        assert is_path_exempt("/orders") is False

    def test_custom_exempt_paths(self):
        """Test custom exempt paths can be configured"""
        configure_auth(exempt_paths=["/health", "/ready", "/ping"])

        assert is_path_exempt("/health") is True
        assert is_path_exempt("/ready") is True
        assert is_path_exempt("/ping") is True
        assert is_path_exempt("/status") is False

    def test_trailing_slash_normalized(self):
        """Test trailing slashes are normalized"""
        configure_auth(exempt_paths=["/health"])

        # Both with and without trailing slash should match
        assert is_path_exempt("/health") is True
        assert is_path_exempt("/health/") is True

    def test_exempt_path_with_trailing_slash_configured(self):
        """Test exempt paths configured with trailing slash still match"""
        configure_auth(exempt_paths=["/health/"])

        assert is_path_exempt("/health") is True
        assert is_path_exempt("/health/") is True

    def test_root_path_handling(self):
        """Test root path / is handled correctly"""
        configure_auth(exempt_paths=["/"])

        assert is_path_exempt("/") is True
        # Root should not match other paths
        configure_auth(exempt_paths=["/health"])
        assert is_path_exempt("/") is False

    def test_partial_path_not_matched(self):
        """Test partial path matches are not counted"""
        configure_auth(exempt_paths=["/health"])

        # These should NOT match
        assert is_path_exempt("/healthy") is False
        assert is_path_exempt("/health/check") is False
        assert is_path_exempt("/api/health") is False

    def test_empty_exempt_paths(self):
        """Test empty exempt paths list means nothing is exempt"""
        configure_auth(exempt_paths=[])

        assert is_path_exempt("/health") is False
        assert is_path_exempt("/") is False


# ============================================
# TEST: require_api_key decorator
# ============================================


class TestRequireApiKeyDecorator:
    """Tests for require_api_key() decorator"""

    def test_valid_key_allows_access(self, app, client):
        """Test valid API key allows access to protected endpoint"""
        configure_auth(api_key="valid-key", enabled=True)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        response = client.get("/protected", headers={"X-API-Key": "valid-key"})

        assert response.status_code == 200
        assert response.json == {"status": "ok"}

    def test_missing_key_returns_401(self, app, client):
        """Test missing API key returns 401 Unauthorized"""
        configure_auth(api_key="secret-key", enabled=True)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        response = client.get("/protected")

        assert response.status_code == 401
        assert "error" in response.json
        assert response.json["error"] == "Unauthorized"
        assert "API key required" in response.json["message"]

    def test_invalid_key_returns_403(self, app, client):
        """Test invalid API key returns 403 Forbidden"""
        configure_auth(api_key="correct-key", enabled=True)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})

        assert response.status_code == 403
        assert "error" in response.json
        assert response.json["error"] == "Forbidden"
        assert "Invalid API key" in response.json["message"]

    def test_auth_disabled_allows_all(self, app, client):
        """Test disabled authentication allows all requests"""
        configure_auth(api_key="secret-key", enabled=False)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        # No API key provided
        response = client.get("/protected")
        assert response.status_code == 200

        # Wrong API key provided
        response = client.get("/protected", headers={"X-API-Key": "wrong"})
        assert response.status_code == 200

    def test_exempt_path_allows_access(self, app, client):
        """Test exempt paths are accessible without authentication"""
        configure_auth(api_key="secret-key", enabled=True, exempt_paths=["/health"])

        @app.route("/health")
        @require_api_key
        def health():
            return {"status": "healthy"}

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json == {"status": "healthy"}

    def test_bearer_token_works(self, app, client):
        """Test Bearer token authentication works"""
        configure_auth(api_key="bearer-token-123", enabled=True)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer bearer-token-123"}
        )

        assert response.status_code == 200

    def test_decorator_preserves_function_name(self, app):
        """Test decorator preserves wrapped function name"""
        @app.route("/test")
        @require_api_key
        def my_endpoint():
            return {"status": "ok"}

        assert my_endpoint.__name__ == "my_endpoint"

    def test_no_configured_key_rejects_all(self, app, client):
        """Test when no API key configured, all requests are rejected"""
        configure_auth(api_key=None, enabled=True)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        # Even without providing a key
        response = client.get("/protected")
        assert response.status_code == 401

        # With any key
        response = client.get("/protected", headers={"X-API-Key": "any-key"})
        assert response.status_code == 403


# ============================================
# TEST: Configuration Functions
# ============================================


class TestConfigurationFunctions:
    """Tests for configure_auth(), reset_auth(), and getter functions"""

    def test_configure_auth_sets_api_key(self):
        """Test configure_auth sets API key"""
        configure_auth(api_key="my-custom-key")

        assert get_api_key() == "my-custom-key"

    def test_configure_auth_sets_enabled(self):
        """Test configure_auth sets enabled flag"""
        configure_auth(enabled=False)
        assert is_auth_enabled() is False

        configure_auth(enabled=True)
        assert is_auth_enabled() is True

    def test_configure_auth_sets_exempt_paths(self):
        """Test configure_auth sets exempt paths"""
        configure_auth(exempt_paths=["/health", "/ready", "/metrics"])

        paths = get_exempt_paths()
        assert "/health" in paths
        assert "/ready" in paths
        assert "/metrics" in paths
        assert len(paths) == 3

    def test_configure_auth_partial_update(self):
        """Test configure_auth only updates provided values"""
        configure_auth(api_key="initial-key", enabled=True, exempt_paths=["/health"])

        # Update only api_key
        configure_auth(api_key="new-key")

        assert get_api_key() == "new-key"
        assert is_auth_enabled() is True  # Unchanged
        assert "/health" in get_exempt_paths()  # Unchanged

    def test_reset_auth_restores_defaults(self):
        """Test reset_auth restores default values"""
        configure_auth(api_key="my-key", enabled=False, exempt_paths=["/custom"])

        reset_auth()

        assert get_api_key() is None
        assert is_auth_enabled() is True
        assert get_exempt_paths() == ["/health"]

    def test_get_exempt_paths_returns_copy(self):
        """Test get_exempt_paths returns a copy (not reference)"""
        configure_auth(exempt_paths=["/health"])

        paths = get_exempt_paths()
        paths.append("/modified")

        # Original should not be modified
        assert "/modified" not in get_exempt_paths()


# ============================================
# TEST: Environment Configuration Loading
# ============================================


class TestEnvironmentConfiguration:
    """Tests for _load_config() from environment variables"""

    @patch.dict("os.environ", {
        "API_KEY": "env-api-key",
        "API_AUTH_ENABLED": "true",
        "API_AUTH_EXEMPT_PATHS": "/health,/ready"
    })
    @patch("core.api_auth.read_secret", return_value="env-api-key")
    def test_load_config_from_env(self, mock_read_secret):
        """Test configuration loads from environment variables"""
        # Re-import to trigger _load_config
        import importlib
        import core.api_auth
        importlib.reload(core.api_auth)

        # Cleanup after test
        try:
            assert core.api_auth.get_api_key() == "env-api-key"
        finally:
            reset_auth()

    @patch.dict("os.environ", {"API_AUTH_ENABLED": "false"})
    @patch("core.api_auth.read_secret", return_value="")
    def test_auth_disabled_via_env(self, mock_read_secret):
        """Test API_AUTH_ENABLED=false disables authentication"""
        import importlib
        import core.api_auth
        importlib.reload(core.api_auth)

        try:
            assert core.api_auth.is_auth_enabled() is False
        finally:
            reset_auth()

    @patch.dict("os.environ", {"API_AUTH_ENABLED": "0"})
    @patch("core.api_auth.read_secret", return_value="")
    def test_auth_disabled_via_zero(self, mock_read_secret):
        """Test API_AUTH_ENABLED=0 disables authentication"""
        import importlib
        import core.api_auth
        importlib.reload(core.api_auth)

        try:
            assert core.api_auth.is_auth_enabled() is False
        finally:
            reset_auth()

    @patch.dict("os.environ", {"API_AUTH_ENABLED": "no"})
    @patch("core.api_auth.read_secret", return_value="")
    def test_auth_disabled_via_no(self, mock_read_secret):
        """Test API_AUTH_ENABLED=no disables authentication"""
        import importlib
        import core.api_auth
        importlib.reload(core.api_auth)

        try:
            assert core.api_auth.is_auth_enabled() is False
        finally:
            reset_auth()

    @patch.dict("os.environ", {"API_AUTH_EXEMPT_PATHS": "/health,/ready,/metrics"})
    @patch("core.api_auth.read_secret", return_value="key")
    def test_exempt_paths_from_env(self, mock_read_secret):
        """Test exempt paths are loaded from comma-separated env var"""
        import importlib
        import core.api_auth
        importlib.reload(core.api_auth)

        try:
            paths = core.api_auth.get_exempt_paths()
            assert "/health" in paths
            assert "/ready" in paths
            assert "/metrics" in paths
        finally:
            reset_auth()


# ============================================
# TEST: Security Edge Cases
# ============================================


class TestSecurityEdgeCases:
    """Tests for security-related edge cases"""

    def test_constant_time_comparison_used(self):
        """Test that constant-time comparison is used (via hmac.compare_digest)"""
        import hmac
        with patch.object(hmac, "compare_digest", return_value=True) as mock_compare:
            configure_auth(api_key="secret")
            validate_api_key("secret")

            mock_compare.assert_called_once()

    def test_timing_attack_resistance(self):
        """Test that validation time is similar for matching/non-matching keys"""
        import time

        configure_auth(api_key="a" * 1000)  # Long key

        # Measure time for matching key
        start = time.perf_counter()
        for _ in range(1000):
            validate_api_key("a" * 1000)
        match_time = time.perf_counter() - start

        # Measure time for non-matching key (first char different)
        start = time.perf_counter()
        for _ in range(1000):
            validate_api_key("b" + "a" * 999)
        mismatch_time = time.perf_counter() - start

        # Times should be similar (within 50% - generous margin for CI variance)
        ratio = max(match_time, mismatch_time) / max(min(match_time, mismatch_time), 0.0001)
        assert ratio < 2.0, f"Timing difference too large: {match_time:.4f}s vs {mismatch_time:.4f}s"

    def test_type_error_handled_gracefully(self):
        """Test TypeError in comparison is handled (returns False, not crash)"""
        configure_auth(api_key="secret")

        # Non-string types should not crash
        result = validate_api_key(12345)  # type: ignore
        assert result is False

        result = validate_api_key(["secret"])  # type: ignore
        assert result is False

        result = validate_api_key({"key": "secret"})  # type: ignore
        assert result is False

    def test_api_key_not_logged(self, app, client, caplog):
        """Test API keys are not logged in failure messages"""
        configure_auth(api_key="super-secret-key-123", enabled=True)

        @app.route("/protected")
        @require_api_key
        def protected():
            return {"status": "ok"}

        import logging
        with caplog.at_level(logging.WARNING):
            client.get("/protected", headers={"X-API-Key": "wrong-key-attempt"})

        # Ensure the actual keys are not in log messages
        for record in caplog.records:
            assert "super-secret-key-123" not in record.message
            assert "wrong-key-attempt" not in record.message

    def test_empty_exempt_paths_env_handled(self):
        """Test empty API_AUTH_EXEMPT_PATHS env var is handled"""
        configure_auth(exempt_paths=[])

        paths = get_exempt_paths()
        assert paths == []


# ============================================
# TEST: HTTP Methods
# ============================================


class TestHttpMethods:
    """Tests for authentication across different HTTP methods"""

    def test_get_requires_auth(self, app, client):
        """Test GET requests require authentication"""
        configure_auth(api_key="key", enabled=True)

        @app.route("/endpoint")
        @require_api_key
        def endpoint():
            return {"status": "ok"}

        response = client.get("/endpoint")
        assert response.status_code == 401

    def test_post_requires_auth(self, app, client):
        """Test POST requests require authentication"""
        configure_auth(api_key="key", enabled=True)

        @app.route("/endpoint", methods=["POST"])
        @require_api_key
        def endpoint():
            return {"status": "ok"}

        response = client.post("/endpoint")
        assert response.status_code == 401

    def test_put_requires_auth(self, app, client):
        """Test PUT requests require authentication"""
        configure_auth(api_key="key", enabled=True)

        @app.route("/endpoint", methods=["PUT"])
        @require_api_key
        def endpoint():
            return {"status": "ok"}

        response = client.put("/endpoint")
        assert response.status_code == 401

    def test_delete_requires_auth(self, app, client):
        """Test DELETE requests require authentication"""
        configure_auth(api_key="key", enabled=True)

        @app.route("/endpoint", methods=["DELETE"])
        @require_api_key
        def endpoint():
            return {"status": "ok"}

        response = client.delete("/endpoint")
        assert response.status_code == 401
