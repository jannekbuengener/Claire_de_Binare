"""
Auth Validation for Redis & Postgres
Validates credentials on startup to prevent restart loops.
"""

import sys
import logging
from typing import Optional, Tuple
import redis
import psycopg2

logger = logging.getLogger(__name__)


def validate_redis_auth(
    host: str, port: int, password: Optional[str], db: int = 0
) -> Tuple[bool, str]:
    """
    Validate Redis connection and authentication.

    Args:
        host: Redis host
        port: Redis port
        password: Redis password (optional)
        db: Redis database number

    Returns:
        (success: bool, message: str)

    Examples:
        >>> success, msg = validate_redis_auth("localhost", 6379, "password")
        >>> if not success:
        >>>     logger.error(msg)
        >>>     sys.exit(1)
    """
    try:
        client = redis.Redis(
            host=host, port=port, password=password, db=db, socket_timeout=5
        )
        client.ping()
        logger.info(f"✅ Redis auth validated: {host}:{port}")
        return True, "Redis connection successful"
    except redis.AuthenticationError as e:
        msg = f"❌ Redis authentication FAILED: Invalid password for {host}:{port}"
        logger.error(msg)
        return False, msg
    except redis.ConnectionError as e:
        msg = f"❌ Redis connection FAILED: Cannot reach {host}:{port} ({e})"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"❌ Redis validation FAILED: {e}"
        logger.error(msg)
        return False, msg


def validate_postgres_auth(
    host: str, port: int, user: str, password: str, database: str
) -> Tuple[bool, str]:
    """
    Validate PostgreSQL connection and authentication.

    Args:
        host: Postgres host
        port: Postgres port
        user: Postgres user
        password: Postgres password
        database: Postgres database name

    Returns:
        (success: bool, message: str)

    Examples:
        >>> success, msg = validate_postgres_auth("localhost", 5432, "user", "pass", "db")
        >>> if not success:
        >>>     logger.error(msg)
        >>>     sys.exit(1)
    """
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=5,
        )
        conn.close()
        logger.info(f"✅ Postgres auth validated: {user}@{host}:{port}/{database}")
        return True, "Postgres connection successful"
    except psycopg2.OperationalError as e:
        error_str = str(e)
        if "password authentication failed" in error_str:
            msg = f"❌ Postgres authentication FAILED: Invalid password for {user}@{host}"
        elif "database" in error_str and "does not exist" in error_str:
            msg = f"❌ Postgres FAILED: Database '{database}' does not exist"
        elif "could not connect" in error_str:
            msg = f"❌ Postgres connection FAILED: Cannot reach {host}:{port}"
        else:
            msg = f"❌ Postgres FAILED: {error_str}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"❌ Postgres validation FAILED: {e}"
        logger.error(msg)
        return False, msg


def validate_all_auth(
    redis_host: str,
    redis_port: int,
    redis_password: Optional[str],
    postgres_host: str,
    postgres_port: int,
    postgres_user: str,
    postgres_password: str,
    postgres_db: str,
) -> bool:
    """
    Validate both Redis and Postgres auth.
    Exits process on failure (prevents restart loops).

    Returns:
        True if all validations pass, exits otherwise

    Usage in service main.py:
        >>> from core.auth import validate_all_auth
        >>> validate_all_auth(
        >>>     REDIS_HOST, REDIS_PORT, REDIS_PASSWORD,
        >>>     POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
        >>> )
    """
    logger.info("🔐 Validating auth credentials...")

    # Validate Redis
    redis_ok, redis_msg = validate_redis_auth(
        redis_host, redis_port, redis_password
    )
    if not redis_ok:
        logger.critical(f"Auth validation FAILED. Service cannot start.")
        logger.critical(f"Redis: {redis_msg}")
        sys.exit(1)
        return False

    # Validate Postgres
    pg_ok, pg_msg = validate_postgres_auth(
        postgres_host, postgres_port, postgres_user, postgres_password, postgres_db
    )
    if not pg_ok:
        logger.critical(f"Auth validation FAILED. Service cannot start.")
        logger.critical(f"Postgres: {pg_msg}")
        sys.exit(1)
        return False

    logger.info("✅ All auth validations passed. Service ready to start.")
    return True
