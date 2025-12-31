"""
Security Headers Middleware for Flask
Adds defense-in-depth security headers to all HTTP responses.
Addresses L-04 from penetration test report.

relations:
  role: middleware
  domain: security
  upstream: []
  downstream:
    - services/allocation/service.py
    - services/signal/service.py
    - services/risk/service.py
    - services/execution/service.py
    - services/regime/service.py
    - services/market/service.py
    - services/ws/service.py
    - tools/paper_trading/service.py
"""

import logging
import os
from typing import Optional

from flask import Flask, Response

logger = logging.getLogger(__name__)


# Default security header values
DEFAULT_X_CONTENT_TYPE_OPTIONS = "nosniff"
DEFAULT_X_FRAME_OPTIONS = "DENY"
DEFAULT_X_XSS_PROTECTION = "1; mode=block"
DEFAULT_CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'"
DEFAULT_STRICT_TRANSPORT_SECURITY = "max-age=31536000; includeSubDomains"
DEFAULT_REFERRER_POLICY = "strict-origin-when-cross-origin"
DEFAULT_PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=()"


class SecurityHeadersConfig:
    """
    Configuration for security headers middleware.

    Reads from environment variables with sensible defaults.
    Set SECURITY_HEADERS_ENABLED=false to disable all security headers.
    Set SECURITY_HEADERS_HSTS_ENABLED=false to disable HSTS (useful in dev).
    """

    def __init__(self):
        self.enabled = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true"
        self.hsts_enabled = os.getenv("SECURITY_HEADERS_HSTS_ENABLED", "true").lower() == "true"

        # Header values (configurable via env vars)
        self.x_content_type_options = os.getenv(
            "SECURITY_HEADER_X_CONTENT_TYPE_OPTIONS",
            DEFAULT_X_CONTENT_TYPE_OPTIONS
        )
        self.x_frame_options = os.getenv(
            "SECURITY_HEADER_X_FRAME_OPTIONS",
            DEFAULT_X_FRAME_OPTIONS
        )
        self.x_xss_protection = os.getenv(
            "SECURITY_HEADER_X_XSS_PROTECTION",
            DEFAULT_X_XSS_PROTECTION
        )
        self.content_security_policy = os.getenv(
            "SECURITY_HEADER_CSP",
            DEFAULT_CONTENT_SECURITY_POLICY
        )
        self.strict_transport_security = os.getenv(
            "SECURITY_HEADER_HSTS",
            DEFAULT_STRICT_TRANSPORT_SECURITY
        )
        self.referrer_policy = os.getenv(
            "SECURITY_HEADER_REFERRER_POLICY",
            DEFAULT_REFERRER_POLICY
        )
        self.permissions_policy = os.getenv(
            "SECURITY_HEADER_PERMISSIONS_POLICY",
            DEFAULT_PERMISSIONS_POLICY
        )


def add_security_headers(response: Response, config: Optional[SecurityHeadersConfig] = None) -> Response:
    """
    Add security headers to a Flask response.

    Args:
        response: Flask Response object
        config: SecurityHeadersConfig instance (uses defaults if None)

    Returns:
        Response with security headers added

    Headers added:
        - X-Content-Type-Options: Prevents MIME type sniffing
        - X-Frame-Options: Prevents clickjacking
        - X-XSS-Protection: Enables browser XSS filter
        - Content-Security-Policy: Controls resource loading
        - Strict-Transport-Security: Forces HTTPS (if enabled)
        - Referrer-Policy: Controls referrer information
        - Permissions-Policy: Restricts browser features
    """
    if config is None:
        config = SecurityHeadersConfig()

    if not config.enabled:
        return response

    # Prevent MIME type sniffing attacks
    response.headers["X-Content-Type-Options"] = config.x_content_type_options

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = config.x_frame_options

    # Enable browser XSS filter (legacy but still useful)
    response.headers["X-XSS-Protection"] = config.x_xss_protection

    # Content Security Policy - controls what resources can be loaded
    response.headers["Content-Security-Policy"] = config.content_security_policy

    # Referrer Policy - controls referrer information
    response.headers["Referrer-Policy"] = config.referrer_policy

    # Permissions Policy - restricts browser features
    response.headers["Permissions-Policy"] = config.permissions_policy

    # HSTS - force HTTPS connections (disabled by default in dev)
    if config.hsts_enabled:
        response.headers["Strict-Transport-Security"] = config.strict_transport_security

    return response


def init_security_headers(app: Flask, config: Optional[SecurityHeadersConfig] = None) -> None:
    """
    Initialize security headers middleware for a Flask application.

    Args:
        app: Flask application instance
        config: Optional SecurityHeadersConfig (uses defaults if None)

    Usage:
        >>> from flask import Flask
        >>> from core.security_headers import init_security_headers
        >>>
        >>> app = Flask(__name__)
        >>> init_security_headers(app)
        >>>
        >>> # Or with custom config:
        >>> config = SecurityHeadersConfig()
        >>> init_security_headers(app, config)
    """
    if config is None:
        config = SecurityHeadersConfig()

    @app.after_request
    def apply_security_headers(response: Response) -> Response:
        return add_security_headers(response, config)

    if config.enabled:
        logger.info("Security headers middleware initialized (HSTS=%s)", config.hsts_enabled)
    else:
        logger.warning("Security headers middleware is DISABLED")
