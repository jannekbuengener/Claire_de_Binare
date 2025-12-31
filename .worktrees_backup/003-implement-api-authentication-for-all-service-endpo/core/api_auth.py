"""
API Authentication Module for Flask Services
Claire de Binare Trading Bot

Provides API key-based authentication for Flask endpoints with:
- Constant-time comparison to prevent timing attacks
- Environment-based configuration
- Decorator-based route protection
- Configurable exempt paths

relations:
  role: security_module
  domain: runtime
  upstream:
    - core/secrets.py
  downstream:
    - services/execution/service.py
    - services/allocation/service.py
    - services/regime/service.py
    - services/signal/service.py
    - services/risk/service.py
    - services/market/service.py
"""

import os
import hmac
import logging
from functools import wraps
from typing import Optional, List, Callable, Any

from flask import request, jsonify, Response

from core.secrets import read_secret

logger = logging.getLogger(__name__)

# Configuration
_api_key: Optional[str] = None
_auth_enabled: bool = True
_exempt_paths: List[str] = ["/health"]


def _load_config() -> None:
    """
    Load API authentication configuration from environment.

    Configuration:
        API_KEY: The API key for authentication (via Docker secret or env var)
        API_AUTH_ENABLED: Enable/disable authentication (default: true)
        API_AUTH_EXEMPT_PATHS: Comma-separated list of paths to exempt (default: /health)
    """
    global _api_key, _auth_enabled, _exempt_paths

    # Load API key from Docker secret or environment variable
    _api_key = read_secret("api_key", "API_KEY")

    # Load auth enabled flag (default: True for production safety)
    auth_enabled_str = os.getenv("API_AUTH_ENABLED", "true").lower()
    _auth_enabled = auth_enabled_str in ("true", "1", "yes", "on")

    # Load exempt paths (default: /health for Docker health checks)
    exempt_paths_str = os.getenv("API_AUTH_EXEMPT_PATHS", "/health")
    _exempt_paths = [p.strip() for p in exempt_paths_str.split(",") if p.strip()]

    if _auth_enabled:
        if _api_key:
            logger.info("API authentication enabled with configured key")
        else:
            logger.warning(
                "API authentication enabled but no API_KEY configured - "
                "all authenticated requests will be rejected"
            )
    else:
        logger.warning("API authentication DISABLED - endpoints unprotected")


def get_api_key() -> Optional[str]:
    """
    Get the configured API key.

    Returns:
        The API key if configured, None otherwise.
    """
    return _api_key


def is_auth_enabled() -> bool:
    """
    Check if API authentication is enabled.

    Returns:
        True if authentication is enabled, False otherwise.
    """
    return _auth_enabled


def get_exempt_paths() -> List[str]:
    """
    Get the list of paths exempt from authentication.

    Returns:
        List of path strings that don't require authentication.
    """
    return _exempt_paths.copy()


def validate_api_key(provided_key: Optional[str]) -> bool:
    """
    Validate the provided API key using constant-time comparison.

    Uses hmac.compare_digest to prevent timing attacks where an attacker
    could infer the correct key by measuring response times.

    Args:
        provided_key: The API key provided in the request.

    Returns:
        True if the key is valid, False otherwise.

    Security:
        - Uses constant-time comparison to prevent timing attacks
        - Returns False if no API key is configured (fail-closed)
        - Handles None values safely
    """
    if not _api_key:
        # No API key configured - reject all requests (fail-closed)
        return False

    if not provided_key:
        return False

    # Use constant-time comparison to prevent timing attacks
    try:
        return hmac.compare_digest(
            _api_key.encode("utf-8"),
            provided_key.encode("utf-8")
        )
    except (AttributeError, TypeError):
        return False


def extract_api_key(req: Any) -> Optional[str]:
    """
    Extract API key from request headers.

    Supports multiple header formats:
        - X-API-Key: <key>
        - Authorization: Bearer <key>
        - Authorization: ApiKey <key>

    Args:
        req: Flask request object.

    Returns:
        The API key if found, None otherwise.
    """
    # Try X-API-Key header first (preferred)
    api_key = req.headers.get("X-API-Key")
    if api_key:
        return api_key

    # Try Authorization header
    auth_header = req.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split(" ", 1)
        if len(parts) == 2:
            scheme, token = parts
            # Accept Bearer or ApiKey schemes
            if scheme.lower() in ("bearer", "apikey"):
                return token

    return None


def is_path_exempt(path: str) -> bool:
    """
    Check if a path is exempt from authentication.

    Args:
        path: The request path to check.

    Returns:
        True if the path is exempt, False otherwise.
    """
    # Normalize path (remove trailing slash)
    normalized = path.rstrip("/") if path != "/" else "/"

    for exempt_path in _exempt_paths:
        exempt_normalized = exempt_path.rstrip("/") if exempt_path != "/" else "/"
        if normalized == exempt_normalized:
            return True

    return False


def require_api_key(f: Callable) -> Callable:
    """
    Decorator to require API key authentication for a Flask route.

    If authentication is disabled (API_AUTH_ENABLED=false), the decorator
    passes through without checking. If the path is in the exempt list,
    it also passes through.

    Usage:
        @app.route("/status")
        @require_api_key
        def status():
            return jsonify({"status": "ok"})

    Returns:
        401 Unauthorized if no API key is provided.
        403 Forbidden if the API key is invalid.

    Security:
        - Always checks authentication before executing the protected function
        - Uses constant-time comparison for key validation
        - Logs authentication failures (without exposing keys)
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Response:
        # Check if auth is disabled globally
        if not _auth_enabled:
            return f(*args, **kwargs)

        # Check if path is exempt
        if is_path_exempt(request.path):
            return f(*args, **kwargs)

        # Extract API key from request
        provided_key = extract_api_key(request)

        if not provided_key:
            logger.warning(
                "Authentication failed: No API key provided for %s %s",
                request.method,
                request.path
            )
            return jsonify({
                "error": "Unauthorized",
                "message": "API key required"
            }), 401

        # Validate the API key
        if not validate_api_key(provided_key):
            logger.warning(
                "Authentication failed: Invalid API key for %s %s",
                request.method,
                request.path
            )
            return jsonify({
                "error": "Forbidden",
                "message": "Invalid API key"
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def configure_auth(
    api_key: Optional[str] = None,
    enabled: Optional[bool] = None,
    exempt_paths: Optional[List[str]] = None
) -> None:
    """
    Programmatically configure API authentication.

    Useful for testing or when configuration needs to be set
    after module initialization.

    Args:
        api_key: The API key to use for validation.
        enabled: Whether authentication is enabled.
        exempt_paths: List of paths to exempt from authentication.

    Example:
        >>> configure_auth(api_key="test-key", enabled=True)
        >>> configure_auth(exempt_paths=["/health", "/ready"])
    """
    global _api_key, _auth_enabled, _exempt_paths

    if api_key is not None:
        _api_key = api_key

    if enabled is not None:
        _auth_enabled = enabled

    if exempt_paths is not None:
        _exempt_paths = list(exempt_paths)


def reset_auth() -> None:
    """
    Reset authentication configuration to defaults.

    Primarily used for testing to ensure clean state between tests.
    """
    global _api_key, _auth_enabled, _exempt_paths
    _api_key = None
    _auth_enabled = True
    _exempt_paths = ["/health"]


# Initialize configuration on module load
_load_config()
