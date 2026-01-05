"""
Rate Limiter (Issue #202)

Thread-safe sliding window rate limiter for MEXC API compliance.

MEXC API Limits:
- REST API: 20 requests/second
- Order placement: 100 orders/10 seconds

Usage:
    limiter = RateLimiter(max_requests=15, time_window=1.0)
    if limiter.acquire():
        # Make API call
    else:
        # Rate limited, wait or retry
"""

import time
import logging
from collections import deque
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter using token bucket algorithm.

    Thread-safe implementation for concurrent API access.

    Args:
        max_requests: Maximum requests allowed in time window
        time_window: Time window in seconds
        name: Optional name for logging
    """

    def __init__(
        self,
        max_requests: int,
        time_window: float,
        name: str = "default"
    ):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if time_window <= 0:
            raise ValueError("time_window must be positive")

        self.max_requests = max_requests
        self.time_window = time_window
        self.name = name
        self._tokens: deque = deque()
        self._lock = Lock()

    def _cleanup_expired(self, now: float) -> None:
        """Remove expired tokens from the window."""
        cutoff = now - self.time_window
        while self._tokens and self._tokens[0] < cutoff:
            self._tokens.popleft()

    def acquire(self) -> bool:
        """
        Try to acquire a rate limit token.

        Returns:
            True if token acquired, False if rate limited
        """
        with self._lock:
            now = time.time()
            self._cleanup_expired(now)

            if len(self._tokens) < self.max_requests:
                self._tokens.append(now)
                return True

            return False

    def wait_and_acquire(self, timeout: float = 5.0) -> bool:
        """
        Wait until a token is available or timeout.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if token acquired, False if timeout
        """
        start = time.time()
        backoff = 0.01  # Start with 10ms
        max_backoff = 0.1  # Max 100ms between retries

        while time.time() - start < timeout:
            if self.acquire():
                return True

            # Calculate wait time until next token expires
            with self._lock:
                if self._tokens:
                    wait_time = max(
                        0,
                        self._tokens[0] + self.time_window - time.time()
                    )
                    # Sleep for min of wait_time or current backoff
                    time.sleep(min(wait_time + 0.001, backoff))
                else:
                    time.sleep(backoff)

            # Exponential backoff capped at max_backoff
            backoff = min(backoff * 1.5, max_backoff)

        logger.warning(
            "Rate limit timeout [%s]: waited %.2fs, limit=%d/%ss",
            self.name, timeout, self.max_requests, self.time_window
        )
        return False

    @property
    def available_tokens(self) -> int:
        """Get number of available tokens."""
        with self._lock:
            self._cleanup_expired(time.time())
            return self.max_requests - len(self._tokens)

    @property
    def utilization(self) -> float:
        """Get current utilization as percentage (0.0 - 1.0)."""
        with self._lock:
            self._cleanup_expired(time.time())
            return len(self._tokens) / self.max_requests

    def reset(self) -> None:
        """Clear all tokens (for testing)."""
        with self._lock:
            self._tokens.clear()


class MexcRateLimiters:
    """
    Pre-configured rate limiters for MEXC API.

    Limits (with safety margin):
    - General API: 15 req/sec (limit is 20)
    - Orders: 80 orders/10sec (limit is 100)
    - Account: 8 req/sec (limit is 10)
    """

    def __init__(self):
        # General API: 20 req/sec (use 15 for safety)
        self.general = RateLimiter(15, 1.0, name="mexc_general")

        # Orders: 100 orders/10sec (use 80 for safety)
        self.orders = RateLimiter(80, 10.0, name="mexc_orders")

        # Account queries: 10/sec (use 8 for safety)
        self.account = RateLimiter(8, 1.0, name="mexc_account")

    def acquire_general(self, timeout: float = 5.0) -> bool:
        """Acquire general API rate limit."""
        return self.general.wait_and_acquire(timeout)

    def acquire_order(self, timeout: float = 5.0) -> bool:
        """Acquire order placement rate limit (includes general)."""
        if not self.general.wait_and_acquire(timeout):
            return False
        return self.orders.wait_and_acquire(timeout)

    def acquire_account(self, timeout: float = 5.0) -> bool:
        """Acquire account query rate limit."""
        if not self.general.wait_and_acquire(timeout):
            return False
        return self.account.wait_and_acquire(timeout)


class RateLimitException(Exception):
    """Raised when rate limit is exceeded and timeout occurs."""
    pass
