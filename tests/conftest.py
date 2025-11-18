"""
Pytest Fixtures - Claire de Binaire
Shared test fixtures for all services
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Generator


# ===== ENVIRONMENT FIXTURES =====

@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Load test environment variables"""
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "5432"
    os.environ["DB_NAME"] = "claire_de_binaire_test"
    os.environ["DB_USER"] = "claire"
    os.environ["DB_PASSWORD"] = "test_password"


# ===== REDIS FIXTURES =====

@pytest.fixture
def mock_redis() -> Generator[Mock, None, None]:
    """Mock Redis client for unit tests"""
    with patch("redis.Redis") as mock:
        mock_instance = Mock()
        mock_instance.ping.return_value = True
        mock_instance.publish.return_value = 1
        mock_instance.get.return_value = None
        mock.return_value = mock_instance
        yield mock_instance


# ===== POSTGRESQL FIXTURES =====

@pytest.fixture
def mock_postgres() -> Generator[Mock, None, None]:
    """Mock PostgreSQL connection for unit tests"""
    with patch("psycopg2.connect") as mock:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_conn


# ===== SAMPLE DATA FIXTURES =====

@pytest.fixture
def sample_signal_event() -> dict:
    """Sample signal event for testing"""
    return {
        "type": "signal",
        "symbol": "BTCUSDT",
        "signal_type": "buy",
        "price": 50000.0,
        "confidence": 0.85,
        "timestamp": "2025-01-11T12:00:00Z",
        "reason": "momentum_breakout"
    }


@pytest.fixture
def sample_risk_state() -> dict:
    """Sample risk state for testing"""
    return {
        "total_exposure": 0.0,
        "daily_pnl": 0.0,
        "open_positions": 0,
        "signals_approved": 0,
        "signals_blocked": 0,
        "circuit_breaker_active": False
    }


# ===== CONFIGURATION FIXTURES =====

@pytest.fixture
def risk_config() -> dict:
    """Risk-Manager configuration for tests"""
    return {
        "MAX_POSITION_PCT": 0.10,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.10
    }


@pytest.fixture
def signal_config() -> dict:
    """Signal-Engine configuration for tests"""
    return {
        "MIN_CONFIDENCE": 0.75,
        "LOOKBACK_CANDLES": 20,
        "MOMENTUM_THRESHOLD": 0.02
    }
