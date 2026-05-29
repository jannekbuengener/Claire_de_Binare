"""
Redis Client Factory with TLS Support
Issue #103: TLS/SSL Implementation

Provides a centralized way to create Redis connections with optional TLS.
All services should use this factory instead of direct redis.Redis() calls.

Environment Variables:
    REDIS_HOST: Redis server hostname (default: localhost)
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_PASSWORD: Redis password
    REDIS_TLS: Enable TLS (default: false)
    REDIS_CA_CERT: Path to CA certificate for TLS verification
    REDIS_CERT: Path to client certificate (optional, for mTLS)
    REDIS_KEY: Path to client private key (optional, for mTLS)
    REDIS_SOCKET_CONNECT_TIMEOUT: TCP connect timeout in seconds (default: 2.0)

Usage:
    from core.utils.redis_client import create_redis_client

    # Simple usage (reads from environment)
    client = create_redis_client()

    # With explicit config
    client = create_redis_client(
        host="redis.example.com",
        port=6379,
        password="secret",
        ssl=True,
        ssl_ca_certs="/path/to/ca.crt"
    )
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)

_POOL_CACHE: dict[tuple[Any, ...], redis.ConnectionPool] = {}
_PINGED_POOLS: set[tuple[Any, ...]] = set()


def _resolve_tls(
    use_tls: Optional[bool],
) -> bool:
    if use_tls is not None:
        return use_tls
    tls_env = os.getenv("REDIS_TLS", "false").lower()
    return tls_env in ("true", "1", "yes", "on")


def _default_socket_connect_timeout() -> float:
    raw = os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2.0")
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid REDIS_SOCKET_CONNECT_TIMEOUT=%r; using 2.0", raw)
        return 2.0


def _pool_cache_key(
    *,
    host: str,
    port: int,
    password: Optional[str],
    db: int,
    use_tls: bool,
    ssl_ca_certs: Optional[str],
    ssl_certfile: Optional[str],
    ssl_keyfile: Optional[str],
    socket_timeout: float,
    socket_connect_timeout: float,
    decode_responses: bool,
) -> tuple[Any, ...]:
    return (
        host,
        port,
        password,
        db,
        use_tls,
        ssl_ca_certs,
        ssl_certfile,
        ssl_keyfile,
        socket_timeout,
        socket_connect_timeout,
        decode_responses,
    )


def _build_pool_kwargs(
    *,
    host: str,
    port: int,
    password: Optional[str],
    db: int,
    use_tls: bool,
    ssl_ca_certs: Optional[str],
    ssl_certfile: Optional[str],
    ssl_keyfile: Optional[str],
    socket_timeout: float,
    socket_connect_timeout: float,
    decode_responses: bool,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "password": password,
        "db": db,
        "socket_timeout": socket_timeout,
        "socket_connect_timeout": socket_connect_timeout,
        "decode_responses": decode_responses,
    }

    if use_tls:
        if ssl_ca_certs and not os.path.exists(ssl_ca_certs):
            raise FileNotFoundError(f"TLS CA certificate not found: {ssl_ca_certs}")
        if ssl_certfile and not os.path.exists(ssl_certfile):
            raise FileNotFoundError(f"TLS client cert not found: {ssl_certfile}")
        if ssl_keyfile and not os.path.exists(ssl_keyfile):
            raise FileNotFoundError(f"TLS client key not found: {ssl_keyfile}")

        kwargs["ssl"] = True
        kwargs["ssl_ca_certs"] = ssl_ca_certs
        if ssl_certfile:
            kwargs["ssl_certfile"] = ssl_certfile
        if ssl_keyfile:
            kwargs["ssl_keyfile"] = ssl_keyfile

    return kwargs


def get_redis_connection_pool(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    db: int = 0,
    use_tls: Optional[bool] = None,
    ssl_ca_certs: Optional[str] = None,
    ssl_certfile: Optional[str] = None,
    ssl_keyfile: Optional[str] = None,
    socket_timeout: float = 5.0,
    socket_connect_timeout: Optional[float] = None,
    decode_responses: bool = False,
) -> redis.ConnectionPool:
    """
    Return a cached ConnectionPool for the given Redis configuration.

    Pools are keyed by host, port, db, TLS settings, and timeout/decode options.
    """
    host = host or os.getenv("REDIS_HOST", "localhost")
    port = port or int(os.getenv("REDIS_PORT", "6379"))
    password = password if password is not None else os.getenv("REDIS_PASSWORD")
    use_tls = _resolve_tls(use_tls)
    ssl_ca_certs = ssl_ca_certs or os.getenv("REDIS_CA_CERT")
    ssl_certfile = ssl_certfile or os.getenv("REDIS_CERT")
    ssl_keyfile = ssl_keyfile or os.getenv("REDIS_KEY")
    if socket_connect_timeout is None:
        socket_connect_timeout = _default_socket_connect_timeout()

    cache_key = _pool_cache_key(
        host=host,
        port=port,
        password=password,
        db=db,
        use_tls=use_tls,
        ssl_ca_certs=ssl_ca_certs,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        decode_responses=decode_responses,
    )

    pool = _POOL_CACHE.get(cache_key)
    if pool is not None:
        return pool

    pool_kwargs = _build_pool_kwargs(
        host=host,
        port=port,
        password=password,
        db=db,
        use_tls=use_tls,
        ssl_ca_certs=ssl_ca_certs,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        decode_responses=decode_responses,
    )

    if use_tls:
        logger.info("Creating Redis connection pool with TLS to %s:%s", host, port)
    else:
        logger.info("Creating Redis connection pool (no TLS) to %s:%s", host, port)

    pool = redis.ConnectionPool(**pool_kwargs)
    _POOL_CACHE[cache_key] = pool
    return pool


def _discard_cached_pool(
    cache_key: tuple[Any, ...],
    pool: Optional[redis.ConnectionPool],
) -> None:
    """Remove a pool from process caches after failed verification."""
    _POOL_CACHE.pop(cache_key, None)
    _PINGED_POOLS.discard(cache_key)
    if pool is not None:
        try:
            pool.disconnect()
        except Exception:
            logger.debug("Redis pool disconnect failed during cache eviction", exc_info=True)


def _ping_pool_once(
    cache_key: tuple[Any, ...],
    client: redis.Redis,
    pool: redis.ConnectionPool,
) -> None:
    if cache_key in _PINGED_POOLS:
        return
    try:
        client.ping()
    except redis.ConnectionError as e:
        logger.error("Redis connection failed: %s", e)
        _discard_cached_pool(cache_key, pool)
        raise
    _PINGED_POOLS.add(cache_key)
    logger.info("Redis connection pool verified")


def create_redis_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    db: int = 0,
    use_tls: Optional[bool] = None,
    ssl_ca_certs: Optional[str] = None,
    ssl_certfile: Optional[str] = None,
    ssl_keyfile: Optional[str] = None,
    socket_timeout: float = 5.0,
    socket_connect_timeout: Optional[float] = None,
    decode_responses: bool = False,
) -> redis.Redis:
    """
    Create a Redis client backed by a shared connection pool.

    Args:
        host: Redis server hostname. Defaults to REDIS_HOST env var or 'localhost'.
        port: Redis server port. Defaults to REDIS_PORT env var or 6379.
        password: Redis password. Defaults to REDIS_PASSWORD env var.
        db: Redis database number. Defaults to 0.
        use_tls: Enable TLS. Defaults to REDIS_TLS env var ('true'/'1').
        ssl_ca_certs: Path to CA certificate. Defaults to REDIS_CA_CERT env var.
        ssl_certfile: Path to client certificate. Defaults to REDIS_CERT env var.
        ssl_keyfile: Path to client private key. Defaults to REDIS_KEY env var.
        socket_timeout: Command/socket timeout in seconds. Defaults to 5.0.
        socket_connect_timeout: TCP connect timeout. Defaults to
            REDIS_SOCKET_CONNECT_TIMEOUT or 2.0.
        decode_responses: Decode responses to strings. Defaults to False.

    Returns:
        redis.Redis: Configured Redis client using a shared pool.

    Raises:
        redis.ConnectionError: If the first health check for this pool fails.
        FileNotFoundError: If TLS is enabled but certificate files are missing.
    """
    if socket_connect_timeout is None:
        socket_connect_timeout = _default_socket_connect_timeout()

    resolved_host = host or os.getenv("REDIS_HOST", "localhost")
    resolved_port = port or int(os.getenv("REDIS_PORT", "6379"))
    resolved_password = password if password is not None else os.getenv("REDIS_PASSWORD")
    resolved_tls = _resolve_tls(use_tls)
    resolved_ssl_ca = ssl_ca_certs or os.getenv("REDIS_CA_CERT")
    resolved_ssl_cert = ssl_certfile or os.getenv("REDIS_CERT")
    resolved_ssl_key = ssl_keyfile or os.getenv("REDIS_KEY")

    cache_key = _pool_cache_key(
        host=resolved_host,
        port=resolved_port,
        password=resolved_password,
        db=db,
        use_tls=resolved_tls,
        ssl_ca_certs=resolved_ssl_ca,
        ssl_certfile=resolved_ssl_cert,
        ssl_keyfile=resolved_ssl_key,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        decode_responses=decode_responses,
    )

    pool = get_redis_connection_pool(
        host=host,
        port=port,
        password=password,
        db=db,
        use_tls=use_tls,
        ssl_ca_certs=ssl_ca_certs,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        decode_responses=decode_responses,
    )
    client = redis.Redis(connection_pool=pool)
    _ping_pool_once(cache_key, client, pool)
    return client


def get_redis_url(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    db: int = 0,
    use_tls: Optional[bool] = None,
) -> str:
    """
    Build a Redis URL for connection.

    Args:
        host: Redis server hostname.
        port: Redis server port.
        password: Redis password.
        db: Redis database number.
        use_tls: Enable TLS.

    Returns:
        str: Redis URL (e.g., 'rediss://user:pass@host:port/db' for TLS)
    """
    host = host or os.getenv("REDIS_HOST", "localhost")
    port = port or int(os.getenv("REDIS_PORT", "6379"))
    password = password if password is not None else os.getenv("REDIS_PASSWORD")

    use_tls = _resolve_tls(use_tls)

    scheme = "rediss" if use_tls else "redis"

    if password:
        return f"{scheme}://:{password}@{host}:{port}/{db}"
    return f"{scheme}://{host}:{port}/{db}"
