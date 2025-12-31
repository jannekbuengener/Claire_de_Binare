"""
HTTP Rate Limiter for Flask endpoints (Issue #H-01)

Flask-compatible rate limiting decorator that protects REST API endpoints
from DoS attacks. Leverages the existing RateLimiter class for thread-safe
sliding window rate limiting.

Usage:
    from core.utils.http_rate_limiter import rate_limit

    @app.route("/health")
    @rate_limit(max_requests=100, time_window=60.0)
    def health():
        return jsonify({"status": "ok"})
"""

import logging
import math
from functools import wraps
from threading import Lock
from typing import Callable, Optional

from flask import Response, jsonify, request

from core.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class IPRateLimiterRegistry:
    """
    Registry for per-IP rate limiters.

    Thread-safe management of rate limiters for individual IP addresses.
    Uses lazy initialization to create limiters only when needed.
    """

    def __init__(self, max_requests: int, time_window: float, name: str = "http"):
        """
        Initialize the registry.

        Args:
            max_requests: Maximum requests per IP in time window
            time_window: Time window in seconds
            name: Name for logging/identification
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.name = name
        self._limiters: dict[str, RateLimiter] = {}
        self._lock = Lock()

    def get_limiter(self, ip: str) -> RateLimiter:
        """
        Get or create a rate limiter for the given IP.

        Thread-safe retrieval with lazy initialization.

        Args:
            ip: Client IP address

        Returns:
            RateLimiter instance for the IP
        """
        with self._lock:
            if ip not in self._limiters:
                self._limiters[ip] = RateLimiter(
                    max_requests=self.max_requests,
                    time_window=self.time_window,
                    name=f"{self.name}:{ip}"
                )
            return self._limiters[ip]

    def cleanup_expired(self) -> int:
        """
        Remove limiters with no recent activity.

        Limiters that have no tokens (all expired) are removed
        to prevent memory growth.

        Returns:
            Number of limiters removed
        """
        removed = 0
        with self._lock:
            expired_ips = [
                ip for ip, limiter in self._limiters.items()
                if limiter.available_tokens == limiter.max_requests
            ]
            for ip in expired_ips:
                del self._limiters[ip]
                removed += 1
        return removed

    @property
    def active_limiters(self) -> int:
        """Get count of active limiters."""
        with self._lock:
            return len(self._limiters)


# Global registry for endpoint rate limiters
_endpoint_registries: dict[str, IPRateLimiterRegistry] = {}
_registry_lock = Lock()


def _get_client_ip() -> str:
    """
    Extract client IP from Flask request.

    Handles X-Forwarded-For header for proxied requests.

    Returns:
        Client IP address string
    """
    # Check for proxy headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For format: "client, proxy1, proxy2"
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (common with nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to remote_addr
    return request.remote_addr or "unknown"


def _get_registry(
    endpoint_name: str,
    max_requests: int,
    time_window: float
) -> IPRateLimiterRegistry:
    """
    Get or create a registry for the endpoint.

    Thread-safe registry management.

    Args:
        endpoint_name: Unique identifier for the endpoint
        max_requests: Maximum requests per IP
        time_window: Time window in seconds

    Returns:
        IPRateLimiterRegistry for the endpoint
    """
    with _registry_lock:
        if endpoint_name not in _endpoint_registries:
            _endpoint_registries[endpoint_name] = IPRateLimiterRegistry(
                max_requests=max_requests,
                time_window=time_window,
                name=endpoint_name
            )
        return _endpoint_registries[endpoint_name]


def rate_limit(
    max_requests: int = 100,
    time_window: float = 60.0,
    key_func: Optional[Callable[[], str]] = None
):
    """
    Flask decorator for rate limiting endpoints.

    Applies per-IP rate limiting using a sliding window algorithm.
    Returns HTTP 429 Too Many Requests when limit is exceeded.

    Args:
        max_requests: Maximum requests allowed per IP in time window
        time_window: Time window in seconds (default: 60 seconds)
        key_func: Optional custom function to determine rate limit key
                  (defaults to client IP)

    Returns:
        Decorator function

    Example:
        @app.route("/api/data")
        @rate_limit(max_requests=10, time_window=1.0)
        def get_data():
            return jsonify({"data": "value"})
    """
    def decorator(func: Callable) -> Callable:
        endpoint_name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get rate limit key (IP by default)
            if key_func:
                limit_key = key_func()
            else:
                limit_key = _get_client_ip()

            # Get registry and limiter for this endpoint and key
            registry = _get_registry(endpoint_name, max_requests, time_window)
            limiter = registry.get_limiter(limit_key)

            # Try to acquire a token
            if limiter.acquire():
                return func(*args, **kwargs)

            # Rate limited - calculate retry-after time
            # Approximate time until next token is available
            retry_after = math.ceil(time_window / max_requests)

            logger.warning(
                "Rate limit exceeded: endpoint=%s ip=%s limit=%d/%ds",
                endpoint_name,
                limit_key,
                max_requests,
                time_window
            )

            response = jsonify({
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Maximum {max_requests} "
                           f"requests per {time_window} seconds.",
                "retry_after": retry_after
            })
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)

            return response

        return wrapper
    return decorator


def rate_limit_with_response(
    max_requests: int = 100,
    time_window: float = 60.0,
    error_response: Optional[Callable[[], Response]] = None
):
    """
    Flask decorator for rate limiting with custom error response.

    Similar to rate_limit but allows custom 429 response handling.

    Args:
        max_requests: Maximum requests per IP in time window
        time_window: Time window in seconds
        error_response: Optional function returning custom Response

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        endpoint_name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            limit_key = _get_client_ip()
            registry = _get_registry(endpoint_name, max_requests, time_window)
            limiter = registry.get_limiter(limit_key)

            if limiter.acquire():
                return func(*args, **kwargs)

            retry_after = math.ceil(time_window / max_requests)

            logger.warning(
                "Rate limit exceeded: endpoint=%s ip=%s limit=%d/%ds",
                endpoint_name,
                limit_key,
                max_requests,
                time_window
            )

            if error_response:
                response = error_response()
                response.headers["Retry-After"] = str(retry_after)
                return response

            response = jsonify({
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Maximum {max_requests} "
                           f"requests per {time_window} seconds.",
                "retry_after": retry_after
            })
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)

            return response

        return wrapper
    return decorator


def get_rate_limit_stats() -> dict:
    """
    Get statistics about current rate limiting.

    Returns:
        Dictionary with rate limit statistics
    """
    with _registry_lock:
        stats = {}
        for endpoint_name, registry in _endpoint_registries.items():
            stats[endpoint_name] = {
                "active_clients": registry.active_limiters,
                "max_requests": registry.max_requests,
                "time_window": registry.time_window
            }
        return stats


def reset_all_limiters() -> None:
    """
    Reset all rate limiters (for testing).

    Clears all endpoint registries and their associated limiters.
    """
    with _registry_lock:
        _endpoint_registries.clear()
