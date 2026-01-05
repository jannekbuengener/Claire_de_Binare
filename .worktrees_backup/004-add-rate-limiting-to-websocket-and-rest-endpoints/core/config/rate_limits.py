"""
Rate Limiting Configuration (Issue #H-01)

Provides centralized rate limiting configuration with environment-based overrides.
Implements sensible defaults that prevent DoS attacks while allowing normal operation.

Environment Variables:
    REST API Rate Limits:
        RATE_LIMIT_REST_MAX_REQUESTS: Max requests per time window (default: 100)
        RATE_LIMIT_REST_TIME_WINDOW: Time window in seconds (default: 60.0)

    REST API Burst Limits (for endpoints that can handle more traffic):
        RATE_LIMIT_REST_BURST_MAX_REQUESTS: Max burst requests (default: 200)
        RATE_LIMIT_REST_BURST_TIME_WINDOW: Burst time window in seconds (default: 60.0)

    REST API Strict Limits (for sensitive endpoints like order submission):
        RATE_LIMIT_REST_STRICT_MAX_REQUESTS: Max strict requests (default: 10)
        RATE_LIMIT_REST_STRICT_TIME_WINDOW: Strict time window in seconds (default: 1.0)

    WebSocket Connection Limits:
        RATE_LIMIT_WS_MAX_CONNECTIONS_PER_IP: Max new connections per IP per window (default: 10)
        RATE_LIMIT_WS_CONNECTION_WINDOW: Connection rate limit window in seconds (default: 60.0)

    WebSocket Message Limits:
        RATE_LIMIT_WS_MAX_MESSAGES_PER_CONNECTION: Max messages per connection per window (default: 100)
        RATE_LIMIT_WS_MESSAGE_WINDOW: Message rate limit window in seconds (default: 1.0)

    Global Settings:
        RATE_LIMIT_ENABLED: Enable/disable all rate limiting (default: true)

Examples:
    # Use defaults (recommended for most deployments)
    config = get_rate_limit_config()

    # Get specific config for REST API
    rest_config = get_rest_rate_limit_config()

    # Get specific config for WebSocket
    ws_config = get_websocket_rate_limit_config()

    # Disable rate limiting (development/testing only)
    os.environ["RATE_LIMIT_ENABLED"] = "false"
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


def _get_env_float(name: str, default: float) -> float:
    """Get a float value from environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(
            "Invalid float value for %s: '%s'. Using default: %s",
            name,
            value,
            default
        )
        return default


def _get_env_int(name: str, default: int) -> int:
    """Get an integer value from environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(
            "Invalid integer value for %s: '%s'. Using default: %s",
            name,
            value,
            default
        )
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    """Get a boolean value from environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


@dataclass
class RESTRateLimitConfig:
    """
    Configuration for REST API rate limiting.

    Attributes:
        max_requests: Maximum requests per time window
        time_window: Time window in seconds
        burst_max_requests: Maximum requests for burst-capable endpoints
        burst_time_window: Time window for burst limits in seconds
        strict_max_requests: Maximum requests for sensitive endpoints
        strict_time_window: Time window for strict limits in seconds
    """
    max_requests: int
    time_window: float
    burst_max_requests: int
    burst_time_window: float
    strict_max_requests: int
    strict_time_window: float

    @property
    def requests_per_second(self) -> float:
        """Calculate effective requests per second for default limits."""
        if self.time_window == 0:
            return float("inf")
        return self.max_requests / self.time_window


@dataclass
class WebSocketRateLimitConfig:
    """
    Configuration for WebSocket rate limiting.

    Attributes:
        max_connections_per_ip: Max new connections per IP in connection window
        connection_window: Connection rate limit window in seconds
        max_messages_per_connection: Max messages per connection in message window
        message_window: Message rate limit window in seconds
    """
    max_connections_per_ip: int
    connection_window: float
    max_messages_per_connection: int
    message_window: float

    @property
    def connections_per_minute(self) -> float:
        """Calculate effective connections per minute."""
        if self.connection_window == 0:
            return float("inf")
        return self.max_connections_per_ip * (60.0 / self.connection_window)

    @property
    def messages_per_second(self) -> float:
        """Calculate effective messages per second."""
        if self.message_window == 0:
            return float("inf")
        return self.max_messages_per_connection / self.message_window


@dataclass
class RateLimitConfig:
    """
    Complete rate limiting configuration.

    Attributes:
        enabled: Whether rate limiting is enabled
        rest: REST API rate limit configuration
        websocket: WebSocket rate limit configuration
    """
    enabled: bool
    rest: RESTRateLimitConfig
    websocket: WebSocketRateLimitConfig


# Default values documented for easy reference
# These defaults are designed to:
# - Allow legitimate clients to operate without throttling
# - Prevent DoS attacks by limiting rapid request bursts
# - Match MEXC API limits where applicable

# REST defaults: 100 requests/minute (slightly under 2/second)
# This is generous for legitimate use while preventing rapid hammering
_DEFAULT_REST_MAX_REQUESTS = 100
_DEFAULT_REST_TIME_WINDOW = 60.0

# Burst defaults: 200 requests/minute for high-traffic endpoints like /health
_DEFAULT_REST_BURST_MAX_REQUESTS = 200
_DEFAULT_REST_BURST_TIME_WINDOW = 60.0

# Strict defaults: 10 requests/second for sensitive endpoints like /orders
# This prevents order spam while allowing reasonable trading activity
_DEFAULT_REST_STRICT_MAX_REQUESTS = 10
_DEFAULT_REST_STRICT_TIME_WINDOW = 1.0

# WebSocket connection defaults: 10 connections/minute per IP
# Prevents connection flooding while allowing reconnection retries
_DEFAULT_WS_MAX_CONNECTIONS_PER_IP = 10
_DEFAULT_WS_CONNECTION_WINDOW = 60.0

# WebSocket message defaults: 100 messages/second per connection
# Generous for legitimate use, blocks message flooding attacks
_DEFAULT_WS_MAX_MESSAGES_PER_CONNECTION = 100
_DEFAULT_WS_MESSAGE_WINDOW = 1.0


def get_rest_rate_limit_config() -> RESTRateLimitConfig:
    """
    Get REST API rate limit configuration from environment.

    Returns:
        RESTRateLimitConfig with values from environment or defaults

    Environment Variables:
        RATE_LIMIT_REST_MAX_REQUESTS: Max requests per window (default: 100)
        RATE_LIMIT_REST_TIME_WINDOW: Window in seconds (default: 60.0)
        RATE_LIMIT_REST_BURST_MAX_REQUESTS: Max burst requests (default: 200)
        RATE_LIMIT_REST_BURST_TIME_WINDOW: Burst window in seconds (default: 60.0)
        RATE_LIMIT_REST_STRICT_MAX_REQUESTS: Max strict requests (default: 10)
        RATE_LIMIT_REST_STRICT_TIME_WINDOW: Strict window in seconds (default: 1.0)
    """
    config = RESTRateLimitConfig(
        max_requests=_get_env_int(
            "RATE_LIMIT_REST_MAX_REQUESTS",
            _DEFAULT_REST_MAX_REQUESTS
        ),
        time_window=_get_env_float(
            "RATE_LIMIT_REST_TIME_WINDOW",
            _DEFAULT_REST_TIME_WINDOW
        ),
        burst_max_requests=_get_env_int(
            "RATE_LIMIT_REST_BURST_MAX_REQUESTS",
            _DEFAULT_REST_BURST_MAX_REQUESTS
        ),
        burst_time_window=_get_env_float(
            "RATE_LIMIT_REST_BURST_TIME_WINDOW",
            _DEFAULT_REST_BURST_TIME_WINDOW
        ),
        strict_max_requests=_get_env_int(
            "RATE_LIMIT_REST_STRICT_MAX_REQUESTS",
            _DEFAULT_REST_STRICT_MAX_REQUESTS
        ),
        strict_time_window=_get_env_float(
            "RATE_LIMIT_REST_STRICT_TIME_WINDOW",
            _DEFAULT_REST_STRICT_TIME_WINDOW
        ),
    )

    logger.debug(
        "REST rate limit config: %d req/%ds (standard), %d req/%ds (burst), "
        "%d req/%ds (strict)",
        config.max_requests,
        config.time_window,
        config.burst_max_requests,
        config.burst_time_window,
        config.strict_max_requests,
        config.strict_time_window
    )

    return config


def get_websocket_rate_limit_config() -> WebSocketRateLimitConfig:
    """
    Get WebSocket rate limit configuration from environment.

    Returns:
        WebSocketRateLimitConfig with values from environment or defaults

    Environment Variables:
        RATE_LIMIT_WS_MAX_CONNECTIONS_PER_IP: Max connections per IP (default: 10)
        RATE_LIMIT_WS_CONNECTION_WINDOW: Connection window in seconds (default: 60.0)
        RATE_LIMIT_WS_MAX_MESSAGES_PER_CONNECTION: Max messages per conn (default: 100)
        RATE_LIMIT_WS_MESSAGE_WINDOW: Message window in seconds (default: 1.0)
    """
    config = WebSocketRateLimitConfig(
        max_connections_per_ip=_get_env_int(
            "RATE_LIMIT_WS_MAX_CONNECTIONS_PER_IP",
            _DEFAULT_WS_MAX_CONNECTIONS_PER_IP
        ),
        connection_window=_get_env_float(
            "RATE_LIMIT_WS_CONNECTION_WINDOW",
            _DEFAULT_WS_CONNECTION_WINDOW
        ),
        max_messages_per_connection=_get_env_int(
            "RATE_LIMIT_WS_MAX_MESSAGES_PER_CONNECTION",
            _DEFAULT_WS_MAX_MESSAGES_PER_CONNECTION
        ),
        message_window=_get_env_float(
            "RATE_LIMIT_WS_MESSAGE_WINDOW",
            _DEFAULT_WS_MESSAGE_WINDOW
        ),
    )

    logger.debug(
        "WebSocket rate limit config: %d conn/%.0fs per IP, %d msg/%.0fs per connection",
        config.max_connections_per_ip,
        config.connection_window,
        config.max_messages_per_connection,
        config.message_window
    )

    return config


def get_rate_limit_config() -> RateLimitConfig:
    """
    Get complete rate limit configuration from environment.

    Returns:
        RateLimitConfig with all rate limiting settings

    Environment Variables:
        RATE_LIMIT_ENABLED: Enable/disable all rate limiting (default: true)
        (plus all REST and WebSocket environment variables)
    """
    enabled = _get_env_bool("RATE_LIMIT_ENABLED", True)

    if not enabled:
        logger.warning(
            "Rate limiting is DISABLED via RATE_LIMIT_ENABLED=false. "
            "This exposes the system to DoS attacks!"
        )

    config = RateLimitConfig(
        enabled=enabled,
        rest=get_rest_rate_limit_config(),
        websocket=get_websocket_rate_limit_config(),
    )

    return config


def is_rate_limiting_enabled() -> bool:
    """
    Check if rate limiting is enabled.

    Returns:
        True if rate limiting is enabled, False otherwise
    """
    return _get_env_bool("RATE_LIMIT_ENABLED", True)


# Cached configuration (lazily initialized)
_cached_config: Optional[RateLimitConfig] = None


def get_cached_rate_limit_config() -> RateLimitConfig:
    """
    Get cached rate limit configuration.

    The configuration is loaded once on first call and cached for performance.
    Use get_rate_limit_config() if you need fresh values after environment changes.

    Returns:
        Cached RateLimitConfig instance
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = get_rate_limit_config()
    return _cached_config


def reset_cached_config() -> None:
    """
    Reset the cached configuration (for testing).

    Forces the next call to get_cached_rate_limit_config() to reload from environment.
    """
    global _cached_config
    _cached_config = None
