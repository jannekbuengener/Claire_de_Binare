"""
PostgreSQL Client Factory with SSL Support
Issue #103: TLS/SSL Implementation

Provides a centralized way to create PostgreSQL connections with optional SSL.
All services should use this factory instead of direct psycopg2 calls.

Environment Variables:
    POSTGRES_HOST: PostgreSQL server hostname (default: localhost)
    POSTGRES_PORT: PostgreSQL server port (default: 5432)
    POSTGRES_DB: Database name (default: claire_de_binare)
    POSTGRES_USER: Database user (default: claire_user)
    POSTGRES_PASSWORD: Database password
    POSTGRES_SSLMODE: SSL mode (default: prefer)
        - disable: No SSL
        - allow: Try SSL, fallback to non-SSL
        - prefer: Try SSL, fallback to non-SSL (default)
        - require: Require SSL, no verification
        - verify-ca: Require SSL with CA verification
        - verify-full: Require SSL with full verification
    POSTGRES_SSLROOTCERT: Path to CA certificate for verification
    POSTGRES_SSLCERT: Path to client certificate (optional)
    POSTGRES_SSLKEY: Path to client private key (optional)

Usage:
    from core.utils.postgres_client import create_postgres_connection, get_postgres_dsn

    # Simple usage (reads from environment)
    conn = create_postgres_connection()

    # With explicit config
    conn = create_postgres_connection(
        host="postgres.example.com",
        sslmode="verify-ca",
        sslrootcert="/path/to/ca.crt"
    )

    # Get DSN string for ORMs
    dsn = get_postgres_dsn(sslmode="verify-ca")
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_postgres_dsn(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    sslmode: Optional[str] = None,
    sslrootcert: Optional[str] = None,
    sslcert: Optional[str] = None,
    sslkey: Optional[str] = None,
) -> str:
    """
    Build a PostgreSQL DSN (connection string) with SSL support.

    Args:
        host: PostgreSQL server hostname.
        port: PostgreSQL server port.
        database: Database name.
        user: Database user.
        password: Database password.
        sslmode: SSL mode.
        sslrootcert: Path to CA certificate.
        sslcert: Path to client certificate.
        sslkey: Path to client private key.

    Returns:
        str: PostgreSQL DSN string.
    """
    host = host or os.getenv("POSTGRES_HOST", "localhost")
    port = port or int(os.getenv("POSTGRES_PORT", "5432"))
    database = database or os.getenv("POSTGRES_DB", "claire_de_binare")
    user = user or os.getenv("POSTGRES_USER", "claire_user")
    password = password or os.getenv("POSTGRES_PASSWORD", "")
    sslmode = sslmode or os.getenv("POSTGRES_SSLMODE", "prefer")
    sslrootcert = sslrootcert or os.getenv("POSTGRES_SSLROOTCERT")
    sslcert = sslcert or os.getenv("POSTGRES_SSLCERT")
    sslkey = sslkey or os.getenv("POSTGRES_SSLKEY")

    # Build DSN
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}"

    if sslrootcert:
        dsn += f"&sslrootcert={sslrootcert}"
    if sslcert:
        dsn += f"&sslcert={sslcert}"
    if sslkey:
        dsn += f"&sslkey={sslkey}"

    return dsn


def create_postgres_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    sslmode: Optional[str] = None,
    sslrootcert: Optional[str] = None,
    sslcert: Optional[str] = None,
    sslkey: Optional[str] = None,
    connect_timeout: int = 10,
):
    """
    Create a PostgreSQL connection with SSL support.

    Args:
        host: PostgreSQL server hostname.
        port: PostgreSQL server port.
        database: Database name.
        user: Database user.
        password: Database password.
        sslmode: SSL mode.
        sslrootcert: Path to CA certificate.
        sslcert: Path to client certificate.
        sslkey: Path to client private key.
        connect_timeout: Connection timeout in seconds.

    Returns:
        psycopg2.connection: PostgreSQL connection object.

    Raises:
        psycopg2.OperationalError: If connection fails.
        FileNotFoundError: If SSL cert files not found.
    """
    import psycopg2

    # Read from environment with fallbacks
    host = host or os.getenv("POSTGRES_HOST", "localhost")
    port = port or int(os.getenv("POSTGRES_PORT", "5432"))
    database = database or os.getenv("POSTGRES_DB", "claire_de_binare")
    user = user or os.getenv("POSTGRES_USER", "claire_user")
    password = password or os.getenv("POSTGRES_PASSWORD")
    sslmode = sslmode or os.getenv("POSTGRES_SSLMODE", "prefer")
    sslrootcert = sslrootcert or os.getenv("POSTGRES_SSLROOTCERT")
    sslcert = sslcert or os.getenv("POSTGRES_SSLCERT")
    sslkey = sslkey or os.getenv("POSTGRES_SSLKEY")

    # Verify SSL files exist if specified
    if sslrootcert and not os.path.exists(sslrootcert):
        raise FileNotFoundError(f"SSL root cert not found: {sslrootcert}")
    if sslcert and not os.path.exists(sslcert):
        raise FileNotFoundError(f"SSL client cert not found: {sslcert}")
    if sslkey and not os.path.exists(sslkey):
        raise FileNotFoundError(f"SSL client key not found: {sslkey}")

    # Build connection kwargs
    kwargs = {
        "host": host,
        "port": port,
        "dbname": database,
        "user": user,
        "password": password,
        "sslmode": sslmode,
        "connect_timeout": connect_timeout,
    }

    if sslrootcert:
        kwargs["sslrootcert"] = sslrootcert
    if sslcert:
        kwargs["sslcert"] = sslcert
    if sslkey:
        kwargs["sslkey"] = sslkey

    ssl_info = f"sslmode={sslmode}"
    if sslrootcert:
        ssl_info += f", CA verified"
    logger.info(f"Connecting to PostgreSQL at {host}:{port}/{database} ({ssl_info})")

    try:
        conn = psycopg2.connect(**kwargs)
        logger.info("PostgreSQL connection successful")
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise


def verify_ssl_connection(conn) -> dict:
    """
    Verify SSL status of an existing PostgreSQL connection.

    Args:
        conn: PostgreSQL connection object.

    Returns:
        dict: SSL connection info including cipher and protocol.
    """
    with conn.cursor() as cur:
        cur.execute("SHOW ssl")
        ssl_enabled = cur.fetchone()[0]

        cur.execute("SELECT ssl_cipher()")
        cipher = cur.fetchone()[0]

        # Get connection info
        info = conn.info

    return {
        "ssl_enabled": ssl_enabled == "on",
        "ssl_cipher": cipher,
        "ssl_in_use": info.ssl_in_use if hasattr(info, "ssl_in_use") else None,
    }
