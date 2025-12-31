"""
WebSocket Rate Limiter (Issue #H-01)

WebSocket-specific rate limiting for connection and message rate control.
Protects WebSocket endpoints from DoS attacks via connection flooding
and message flooding.

Provides async-compatible interface for use with asyncio WebSocket servers.

Usage:
    from core.utils.ws_rate_limiter import WebSocketRateLimiter

    # Create limiter with connection and message limits
    limiter = WebSocketRateLimiter(
        max_connections_per_ip=10,
        connection_window=60.0,
        max_messages_per_connection=100,
        message_window=1.0
    )

    # Check connection limit before accepting new connection
    if limiter.allow_connection(client_ip):
        connection_id = limiter.register_connection(client_ip)
        # ... handle connection

        # Check message limit before processing each message
        if limiter.allow_message(connection_id):
            # ... process message
        else:
            # Rate limited - optionally close connection
            pass
    else:
        # Reject connection - too many from this IP
        pass
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """
    Result of a rate limit check.

    Attributes:
        allowed: Whether the action is allowed
        remaining: Remaining tokens in the current window
        retry_after: Seconds until next token is available (0 if allowed)
        limit: Maximum allowed in window
        window: Time window in seconds
    """
    allowed: bool
    remaining: int
    retry_after: float
    limit: int
    window: float


@dataclass
class ConnectionState:
    """
    State tracking for a single WebSocket connection.

    Attributes:
        connection_id: Unique identifier for this connection
        ip: Client IP address
        created_at: Timestamp when connection was established
        message_times: Deque of message timestamps for rate limiting
    """
    connection_id: str
    ip: str
    created_at: float
    message_times: deque = field(default_factory=deque)


class AsyncRateLimiter:
    """
    Async-compatible rate limiter using sliding window algorithm.

    Thread-safe implementation for concurrent access from both
    sync and async code.

    Args:
        max_tokens: Maximum tokens allowed in time window
        time_window: Time window in seconds
        name: Optional name for logging
    """

    def __init__(
        self,
        max_tokens: int,
        time_window: float,
        name: str = "async_limiter"
    ):
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if time_window <= 0:
            raise ValueError("time_window must be positive")

        self.max_tokens = max_tokens
        self.time_window = time_window
        self.name = name
        self._tokens: deque = deque()
        self._lock = Lock()

    def _cleanup_expired(self, now: float) -> None:
        """Remove expired tokens from the window."""
        cutoff = now - self.time_window
        while self._tokens and self._tokens[0] < cutoff:
            self._tokens.popleft()

    def acquire(self) -> RateLimitResult:
        """
        Try to acquire a rate limit token (synchronous).

        Returns:
            RateLimitResult with allowed status and metadata
        """
        with self._lock:
            now = time.time()
            self._cleanup_expired(now)

            current_count = len(self._tokens)

            if current_count < self.max_tokens:
                self._tokens.append(now)
                return RateLimitResult(
                    allowed=True,
                    remaining=self.max_tokens - current_count - 1,
                    retry_after=0,
                    limit=self.max_tokens,
                    window=self.time_window
                )

            # Calculate retry_after: time until oldest token expires
            retry_after = self._tokens[0] + self.time_window - now
            retry_after = max(0, retry_after)

            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
                limit=self.max_tokens,
                window=self.time_window
            )

    async def acquire_async(self) -> RateLimitResult:
        """
        Try to acquire a rate limit token (async-compatible).

        Runs the synchronous acquire in the default executor to
        avoid blocking the event loop on lock contention.

        Returns:
            RateLimitResult with allowed status and metadata
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.acquire)

    @property
    def available_tokens(self) -> int:
        """Get number of available tokens."""
        with self._lock:
            self._cleanup_expired(time.time())
            return self.max_tokens - len(self._tokens)

    @property
    def utilization(self) -> float:
        """Get current utilization as percentage (0.0 - 1.0)."""
        with self._lock:
            self._cleanup_expired(time.time())
            if self.max_tokens == 0:
                return 1.0
            return len(self._tokens) / self.max_tokens

    def reset(self) -> None:
        """Clear all tokens (for testing)."""
        with self._lock:
            self._tokens.clear()


class IPConnectionLimiter:
    """
    Rate limiter for new WebSocket connections per IP.

    Thread-safe management of connection rate limiting for individual
    IP addresses using lazy initialization.
    """

    def __init__(
        self,
        max_connections: int,
        time_window: float,
        name: str = "ws_connections"
    ):
        """
        Initialize the IP connection limiter.

        Args:
            max_connections: Maximum new connections per IP in time window
            time_window: Time window in seconds
            name: Name for logging/identification
        """
        self.max_connections = max_connections
        self.time_window = time_window
        self.name = name
        self._limiters: dict[str, AsyncRateLimiter] = {}
        self._lock = Lock()

    def get_limiter(self, ip: str) -> AsyncRateLimiter:
        """
        Get or create a rate limiter for the given IP.

        Thread-safe retrieval with lazy initialization.

        Args:
            ip: Client IP address

        Returns:
            AsyncRateLimiter instance for the IP
        """
        with self._lock:
            if ip not in self._limiters:
                self._limiters[ip] = AsyncRateLimiter(
                    max_tokens=self.max_connections,
                    time_window=self.time_window,
                    name=f"{self.name}:{ip}"
                )
            return self._limiters[ip]

    def allow_connection(self, ip: str) -> RateLimitResult:
        """
        Check if a new connection from the IP is allowed.

        Args:
            ip: Client IP address

        Returns:
            RateLimitResult indicating if connection is allowed
        """
        limiter = self.get_limiter(ip)
        return limiter.acquire()

    async def allow_connection_async(self, ip: str) -> RateLimitResult:
        """
        Check if a new connection from the IP is allowed (async version).

        Args:
            ip: Client IP address

        Returns:
            RateLimitResult indicating if connection is allowed
        """
        limiter = self.get_limiter(ip)
        return await limiter.acquire_async()

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
                if limiter.available_tokens == limiter.max_tokens
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


class WebSocketRateLimiter:
    """
    Complete WebSocket rate limiting solution.

    Provides both connection rate limiting (per IP) and message rate
    limiting (per connection). Designed for use with asyncio WebSocket
    servers.

    Features:
    - Limits new connections per IP per time window
    - Limits messages per connection per time window
    - Async-compatible interface
    - Thread-safe for mixed sync/async usage
    - Graceful handling when limits exceeded

    Args:
        max_connections_per_ip: Max new connections per IP in connection window
        connection_window: Connection rate limit window in seconds
        max_messages_per_connection: Max messages per connection in message window
        message_window: Message rate limit window in seconds
        name: Name for logging/identification
    """

    def __init__(
        self,
        max_connections_per_ip: int = 10,
        connection_window: float = 60.0,
        max_messages_per_connection: int = 100,
        message_window: float = 1.0,
        name: str = "websocket"
    ):
        self.max_connections_per_ip = max_connections_per_ip
        self.connection_window = connection_window
        self.max_messages_per_connection = max_messages_per_connection
        self.message_window = message_window
        self.name = name

        # Connection rate limiting per IP
        self._connection_limiter = IPConnectionLimiter(
            max_connections=max_connections_per_ip,
            time_window=connection_window,
            name=f"{name}_connections"
        )

        # Message rate limiting per connection
        self._message_limiters: dict[str, AsyncRateLimiter] = {}
        self._connections: dict[str, ConnectionState] = {}
        self._lock = Lock()

        # Metrics
        self._connections_blocked = 0
        self._messages_blocked = 0

    def allow_connection(self, ip: str) -> RateLimitResult:
        """
        Check if a new connection from the IP is allowed.

        Call this before accepting a new WebSocket connection.

        Args:
            ip: Client IP address

        Returns:
            RateLimitResult indicating if connection is allowed
        """
        result = self._connection_limiter.allow_connection(ip)

        if not result.allowed:
            self._connections_blocked += 1
            logger.warning(
                "WebSocket connection rate limit exceeded: ip=%s limit=%d/%ds",
                ip,
                self.max_connections_per_ip,
                self.connection_window
            )

        return result

    async def allow_connection_async(self, ip: str) -> RateLimitResult:
        """
        Check if a new connection from the IP is allowed (async version).

        Call this before accepting a new WebSocket connection.

        Args:
            ip: Client IP address

        Returns:
            RateLimitResult indicating if connection is allowed
        """
        result = await self._connection_limiter.allow_connection_async(ip)

        if not result.allowed:
            self._connections_blocked += 1
            logger.warning(
                "WebSocket connection rate limit exceeded: ip=%s limit=%d/%ds",
                ip,
                self.max_connections_per_ip,
                self.connection_window
            )

        return result

    def register_connection(self, ip: str, connection_id: Optional[str] = None) -> str:
        """
        Register a new accepted connection for message rate limiting.

        Call this after accepting a new WebSocket connection.

        Args:
            ip: Client IP address
            connection_id: Optional custom connection ID (generated if not provided)

        Returns:
            Connection ID for use in message rate limiting
        """
        if connection_id is None:
            connection_id = str(uuid4())

        with self._lock:
            self._connections[connection_id] = ConnectionState(
                connection_id=connection_id,
                ip=ip,
                created_at=time.time()
            )
            self._message_limiters[connection_id] = AsyncRateLimiter(
                max_tokens=self.max_messages_per_connection,
                time_window=self.message_window,
                name=f"{self.name}_messages:{connection_id[:8]}"
            )

        logger.debug(
            "WebSocket connection registered: id=%s ip=%s",
            connection_id[:8],
            ip
        )

        return connection_id

    def unregister_connection(self, connection_id: str) -> bool:
        """
        Unregister a connection when it closes.

        Call this when a WebSocket connection closes to clean up state.

        Args:
            connection_id: Connection ID from register_connection

        Returns:
            True if connection was found and removed, False otherwise
        """
        with self._lock:
            if connection_id in self._connections:
                del self._connections[connection_id]
                del self._message_limiters[connection_id]
                logger.debug(
                    "WebSocket connection unregistered: id=%s",
                    connection_id[:8]
                )
                return True
            return False

    def allow_message(self, connection_id: str) -> RateLimitResult:
        """
        Check if a message from the connection is allowed.

        Call this before processing each incoming WebSocket message.

        Args:
            connection_id: Connection ID from register_connection

        Returns:
            RateLimitResult indicating if message is allowed.
            Returns denied result if connection_id is unknown.
        """
        with self._lock:
            limiter = self._message_limiters.get(connection_id)

        if limiter is None:
            logger.warning(
                "WebSocket message from unknown connection: id=%s",
                connection_id[:8] if connection_id else "none"
            )
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=0,
                limit=self.max_messages_per_connection,
                window=self.message_window
            )

        result = limiter.acquire()

        if not result.allowed:
            self._messages_blocked += 1
            # Get IP for logging
            with self._lock:
                conn = self._connections.get(connection_id)
                ip = conn.ip if conn else "unknown"
            logger.warning(
                "WebSocket message rate limit exceeded: id=%s ip=%s limit=%d/%ds",
                connection_id[:8],
                ip,
                self.max_messages_per_connection,
                self.message_window
            )

        return result

    async def allow_message_async(self, connection_id: str) -> RateLimitResult:
        """
        Check if a message from the connection is allowed (async version).

        Call this before processing each incoming WebSocket message.

        Args:
            connection_id: Connection ID from register_connection

        Returns:
            RateLimitResult indicating if message is allowed.
            Returns denied result if connection_id is unknown.
        """
        with self._lock:
            limiter = self._message_limiters.get(connection_id)

        if limiter is None:
            logger.warning(
                "WebSocket message from unknown connection: id=%s",
                connection_id[:8] if connection_id else "none"
            )
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=0,
                limit=self.max_messages_per_connection,
                window=self.message_window
            )

        result = await limiter.acquire_async()

        if not result.allowed:
            self._messages_blocked += 1
            # Get IP for logging
            with self._lock:
                conn = self._connections.get(connection_id)
                ip = conn.ip if conn else "unknown"
            logger.warning(
                "WebSocket message rate limit exceeded: id=%s ip=%s limit=%d/%ds",
                connection_id[:8],
                ip,
                self.max_messages_per_connection,
                self.message_window
            )

        return result

    def get_connection_info(self, connection_id: str) -> Optional[ConnectionState]:
        """
        Get information about a connection.

        Args:
            connection_id: Connection ID from register_connection

        Returns:
            ConnectionState if found, None otherwise
        """
        with self._lock:
            return self._connections.get(connection_id)

    def get_stats(self) -> dict:
        """
        Get statistics about current rate limiting state.

        Returns:
            Dictionary with rate limit statistics
        """
        with self._lock:
            active_connections = len(self._connections)
            connections_by_ip: dict[str, int] = {}
            for conn in self._connections.values():
                connections_by_ip[conn.ip] = connections_by_ip.get(conn.ip, 0) + 1

        return {
            "active_connections": active_connections,
            "connections_by_ip": connections_by_ip,
            "connections_blocked_total": self._connections_blocked,
            "messages_blocked_total": self._messages_blocked,
            "connection_limit": self.max_connections_per_ip,
            "connection_window": self.connection_window,
            "message_limit": self.max_messages_per_connection,
            "message_window": self.message_window,
        }

    def cleanup_expired_connections(self, max_age: float = 3600.0) -> int:
        """
        Remove stale connections that haven't been explicitly closed.

        Use this periodically to clean up connections that were not
        properly unregistered (e.g., due to crashes).

        Args:
            max_age: Maximum age in seconds for a connection to remain registered

        Returns:
            Number of connections removed
        """
        now = time.time()
        removed = 0

        with self._lock:
            stale_ids = [
                conn_id for conn_id, conn in self._connections.items()
                if now - conn.created_at > max_age
            ]
            for conn_id in stale_ids:
                del self._connections[conn_id]
                del self._message_limiters[conn_id]
                removed += 1

        if removed > 0:
            logger.info(
                "Cleaned up %d stale WebSocket connections (max_age=%ds)",
                removed,
                max_age
            )

        return removed

    def reset(self) -> None:
        """
        Reset all rate limiting state (for testing).

        Clears all connections and rate limiters.
        """
        with self._lock:
            self._connections.clear()
            self._message_limiters.clear()
            self._connections_blocked = 0
            self._messages_blocked = 0

        # Reset IP connection limiter
        self._connection_limiter = IPConnectionLimiter(
            max_connections=self.max_connections_per_ip,
            time_window=self.connection_window,
            name=f"{self.name}_connections"
        )


# Default global instance for convenience
_default_limiter: Optional[WebSocketRateLimiter] = None
_default_lock = Lock()


def get_default_limiter() -> WebSocketRateLimiter:
    """
    Get or create the default WebSocket rate limiter.

    Uses sensible defaults suitable for most applications:
    - 10 connections per IP per minute
    - 100 messages per connection per second

    Returns:
        Default WebSocketRateLimiter instance
    """
    global _default_limiter

    with _default_lock:
        if _default_limiter is None:
            _default_limiter = WebSocketRateLimiter(
                max_connections_per_ip=10,
                connection_window=60.0,
                max_messages_per_connection=100,
                message_window=1.0,
                name="default_websocket"
            )
        return _default_limiter


def reset_default_limiter() -> None:
    """
    Reset the default limiter (for testing).

    Clears the global default limiter instance.
    """
    global _default_limiter

    with _default_lock:
        _default_limiter = None
