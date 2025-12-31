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

import logging
import os
import ssl
from typing import Optional

import redis

logger = logging.getLogger(__name__)


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
    decode_responses: bool = False,
) -> redis.Redis:
    """
    Create a Redis client with optional TLS support.

    Args:
        host: Redis server hostname. Defaults to REDIS_HOST env var or 'localhost'.
        port: Redis server port. Defaults to REDIS_PORT env var or 6379.
        password: Redis password. Defaults to REDIS_PASSWORD env var.
        db: Redis database number. Defaults to 0.
        use_tls: Enable TLS. Defaults to REDIS_TLS env var ('true'/'1').
        ssl_ca_certs: Path to CA certificate. Defaults to REDIS_CA_CERT env var.
        ssl_certfile: Path to client certificate. Defaults to REDIS_CERT env var.
        ssl_keyfile: Path to client private key. Defaults to REDIS_KEY env var.
        socket_timeout: Connection timeout in seconds. Defaults to 5.0.
        decode_responses: Decode responses to strings. Defaults to False.

    Returns:
        redis.Redis: Configured Redis client.

    Raises:
        redis.ConnectionError: If connection fails.
        FileNotFoundError: If TLS is enabled but certificate files not found.
    """
    # Read from environment with fallbacks
    host = host or os.getenv("REDIS_HOST", "localhost")
    port = port or int(os.getenv("REDIS_PORT", "6379"))
    password = password or os.getenv("REDIS_PASSWORD")

    # TLS configuration
    if use_tls is None:
        tls_env = os.getenv("REDIS_TLS", "false").lower()
        use_tls = tls_env in ("true", "1", "yes", "on")

    ssl_ca_certs = ssl_ca_certs or os.getenv("REDIS_CA_CERT")
    ssl_certfile = ssl_certfile or os.getenv("REDIS_CERT")
    ssl_keyfile = ssl_keyfile or os.getenv("REDIS_KEY")

    # Build connection kwargs
    kwargs = {
        "host": host,
        "port": port,
        "password": password,
        "db": db,
        "socket_timeout": socket_timeout,
        "decode_responses": decode_responses,
    }

    if use_tls:
        logger.info(f"Creating Redis client with TLS to {host}:{port}")

        # Verify CA cert exists
        if ssl_ca_certs and not os.path.exists(ssl_ca_certs):
            raise FileNotFoundError(f"TLS CA certificate not found: {ssl_ca_certs}")

        # Build SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        if ssl_ca_certs:
            ssl_context.load_verify_locations(ssl_ca_certs)
            logger.debug(f"Loaded CA certificate: {ssl_ca_certs}")

        # Client certificate (mTLS) - optional
        if ssl_certfile and ssl_keyfile:
            if not os.path.exists(ssl_certfile):
                raise FileNotFoundError(f"TLS client cert not found: {ssl_certfile}")
            if not os.path.exists(ssl_keyfile):
                raise FileNotFoundError(f"TLS client key not found: {ssl_keyfile}")

            ssl_context.load_cert_chain(
                certfile=ssl_certfile,
                keyfile=ssl_keyfile,
            )
            logger.debug(f"Loaded client certificate: {ssl_certfile}")

        kwargs["ssl"] = True
        kwargs["ssl_ca_certs"] = ssl_ca_certs
        if ssl_certfile:
            kwargs["ssl_certfile"] = ssl_certfile
        if ssl_keyfile:
            kwargs["ssl_keyfile"] = ssl_keyfile

    else:
        logger.info(f"Creating Redis client (no TLS) to {host}:{port}")

    client = redis.Redis(**kwargs)

    # Test connection
    try:
        client.ping()
        tls_status = "with TLS" if use_tls else "without TLS"
        logger.info(f"Redis connection successful ({tls_status})")
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        raise

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
    password = password or os.getenv("REDIS_PASSWORD")

    if use_tls is None:
        tls_env = os.getenv("REDIS_TLS", "false").lower()
        use_tls = tls_env in ("true", "1", "yes", "on")

    scheme = "rediss" if use_tls else "redis"

    if password:
        return f"{scheme}://:{password}@{host}:{port}/{db}"
    else:
        return f"{scheme}://{host}:{port}/{db}"
