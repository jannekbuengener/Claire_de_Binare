"""Shared pytest fixtures for the Claire de Binare test-suite."""

from __future__ import annotations

from typing import Dict

import pytest


@pytest.fixture
def risk_config() -> Dict[str, float]:
    """Provide default risk parameters for unit tests."""

    return {
        "ACCOUNT_EQUITY": 100_000.0,
        "MAX_DRAWDOWN_PCT": 0.05,
        "MAX_POSITION_PCT": 0.10,
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "STOP_LOSS_PCT": 0.02,
    }


@pytest.fixture
def sample_risk_state() -> Dict[str, float]:
    """Example portfolio snapshot used by the risk engine tests."""

    return {
        "equity": 100_000.0,
        "daily_pnl": 0.0,
        "total_exposure_pct": 0.15,
    }


@pytest.fixture
def sample_signal_event() -> Dict[str, float]:
    """Minimal signal event stub for testing."""

    return {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50_000.0,
        "size": 1.0,
    }


@pytest.fixture
def mock_redis(mocker):
    """Simulate a Redis client using pytest-mock."""

    redis_mock = mocker.Mock()
    redis_mock.ping.return_value = True
    return mocker.patch("redis.Redis", return_value=redis_mock)


@pytest.fixture
def mock_postgres(mocker):
    """Simulate a PostgreSQL connection pool using pytest-mock."""

    pool_mock = mocker.Mock()
    pool_mock.getconn.return_value = mocker.Mock()
    return mocker.patch("psycopg2.pool.SimpleConnectionPool", return_value=pool_mock)
