"""
Fixtures für lokale-only Tests
Claire de Binaire - Erweiterte Test-Suite
"""
import pytest
import os
import time
import redis
import psycopg2
from typing import Generator, Callable
from decimal import Decimal

# Docker-Import optional (für Resilience-Tests)
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def redis_client() -> Generator[redis.Redis, None, None]:
    """
    Redis client connected to cdb_redis container.

    Requires:
    - docker compose up -d
    - REDIS_PASSWORD in .env
    """
    password = os.getenv("REDIS_PASSWORD", "claire_redis_secret_2024")

    client = redis.Redis(
        host="localhost",
        port=6379,
        password=password,
        decode_responses=True
    )

    # Verify connection
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis not available. Run 'docker compose up -d'")

    yield client

    # Cleanup: Flush test keys (optional)
    # client.flushdb()
    client.close()


@pytest.fixture(scope="function")
def redis_pubsub(redis_client: redis.Redis) -> Generator[redis.client.PubSub, None, None]:
    """
    Redis Pub/Sub client for testing message flows.
    """
    pubsub = redis_client.pubsub()
    yield pubsub
    pubsub.close()


# ============================================================================
# PostgreSQL Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def postgres_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    PostgreSQL connection to cdb_postgres container.

    Requires:
    - docker compose up -d
    - POSTGRES_USER, POSTGRES_PASSWORD in .env
    """
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="claire_de_binare",
        user=os.getenv("POSTGRES_USER", "claire_user"),
        password=os.getenv("POSTGRES_PASSWORD", "claire_db_secret_2024")
    )

    yield conn

    # Cleanup
    conn.rollback()
    conn.close()


@pytest.fixture(scope="function")
def postgres_cursor(postgres_connection):
    """
    PostgreSQL cursor for executing queries.
    """
    cursor = postgres_connection.cursor()
    yield cursor
    cursor.close()


# ============================================================================
# Docker Fixtures (für Resilience-Tests)
# ============================================================================

if DOCKER_AVAILABLE:
    @pytest.fixture(scope="session")
    def docker_client() -> docker.DockerClient:
        """Docker client for container control."""
        return docker.from_env()

    @pytest.fixture(scope="function")
    def restart_container(docker_client) -> Callable[[str, int], None]:
        """
        Helper to restart a Docker container.

        Usage:
            restart_container("cdb_core", wait_seconds=10)
        """
        def _restart(container_name: str, wait_seconds: int = 10) -> None:
            container = docker_client.containers.get(container_name)
            container.restart()
            time.sleep(wait_seconds)

        return _restart

    @pytest.fixture(scope="function")
    def wait_for_health(docker_client) -> Callable[[str, int], bool]:
        """
        Helper to wait for container health.

        Usage:
            assert wait_for_health("cdb_postgres", timeout=30)
        """
        def _wait(container_name: str, timeout: int = 30) -> bool:
            start_time = time.time()
            while time.time() - start_time < timeout:
                container = docker_client.containers.get(container_name)
                state = container.attrs.get("State", {})
                health = state.get("Health", {}).get("Status")

                if health == "healthy":
                    return True

                time.sleep(1)

            return False

        return _wait


# ============================================================================
# Service Health Check Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def check_service_health() -> Callable[[str, int], bool]:
    """
    Helper to check service health via HTTP endpoint.

    Usage:
        assert check_service_health("http://localhost:8001/health")
    """
    import requests

    def _check(url: str, timeout: int = 5) -> bool:
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except requests.RequestException:
            return False

    return _check


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def sample_market_data() -> dict:
    """Sample market_data event for testing."""
    return {
        "type": "market_data",
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume": 123.45,
        "timestamp": "2025-01-20T10:00:00Z",
        "bid": 49995.0,
        "ask": 50005.0
    }


@pytest.fixture(scope="function")
def sample_signal_event() -> dict:
    """Sample signal event for testing."""
    return {
        "type": "signal",
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "price": 50000.0,
        "confidence": 0.75,
        "timestamp": "2025-01-20T10:00:01Z",
        "strategy": "momentum"
    }


@pytest.fixture(scope="function")
def sample_order_event() -> dict:
    """Sample order event for testing."""
    return {
        "type": "order",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.5,
        "price": 50000.0,
        "timestamp": "2025-01-20T10:00:02Z",
        "risk_approved": True
    }


@pytest.fixture(scope="function")
def sample_execution_result() -> dict:
    """Sample execution_result event for testing."""
    return {
        "type": "execution_result",
        "symbol": "BTCUSDT",
        "side": "buy",
        "quantity": 0.5,
        "executed_price": 50010.0,
        "fees": 25.0,
        "slippage": 0.02,
        "timestamp": "2025-01-20T10:00:03Z",
        "status": "filled"
    }


# ============================================================================
# Database Cleanup Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def clean_database(postgres_connection):
    """
    Clean test data from database before each test.
    """
    cursor = postgres_connection.cursor()

    # Delete in reverse order due to foreign keys
    cursor.execute("DELETE FROM portfolio_snapshots WHERE 1=1")
    cursor.execute("DELETE FROM positions WHERE 1=1")
    cursor.execute("DELETE FROM trades WHERE 1=1")
    cursor.execute("DELETE FROM orders WHERE 1=1")
    cursor.execute("DELETE FROM signals WHERE 1=1")

    postgres_connection.commit()
    cursor.close()

    yield

    # Cleanup after test (optional)
    cursor = postgres_connection.cursor()
    cursor.execute("DELETE FROM portfolio_snapshots WHERE 1=1")
    cursor.execute("DELETE FROM positions WHERE 1=1")
    cursor.execute("DELETE FROM trades WHERE 1=1")
    cursor.execute("DELETE FROM orders WHERE 1=1")
    cursor.execute("DELETE FROM signals WHERE 1=1")
    postgres_connection.commit()
    cursor.close()
