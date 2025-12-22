"""
Pytest Fixtures für CDB Tests.

Zentrale Fixtures für Unit-, Integration- und Replay-Tests.
Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md
"""

import sys
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import psycopg2

try:
    from redis import Redis
except ModuleNotFoundError:
    # Fallback stub for test mocks when redis isn't installed in CI.
    class Redis:  # type: ignore[no-redef]
        pass


from core.domain.models import Signal, Order, OrderResult

# Add project root to sys.path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================
# MOCK FIXTURES (External Dependencies)
# ============================================


@pytest.fixture
def mock_redis() -> Mock:
    """
    Mock Redis Client für Tests.

    Verhindert echte Redis-Connections in Unit-Tests.
    """
    mock = MagicMock(spec=Redis)

    # Mock basic Redis operations
    mock.get.return_value = None
    mock.set.return_value = True
    mock.publish.return_value = 1
    mock.ping.return_value = True

    return mock


@pytest.fixture
def mock_postgres() -> Mock:
    """
    Mock PostgreSQL Connection für Tests.

    Verhindert echte DB-Connections in Unit-Tests.
    """
    mock_conn = MagicMock(spec=psycopg2.extensions.connection)
    mock_cursor = MagicMock(spec=psycopg2.extensions.cursor)

    # Mock cursor operations
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute.return_value = None

    # Mock connection
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None

    return mock_conn


# ============================================
# DOMAIN MODEL FACTORIES
# ============================================


@pytest.fixture
def signal_factory() -> Callable[..., Signal]:
    """
    Factory für Signal-Objekte.

    Usage:
        def test_foo(signal_factory):
            signal = signal_factory(symbol="BTCUSDT", signal_type="buy")
    """

    def _create_signal(
        symbol: str = "BTCUSDT",
        signal_type: str = "buy",
        timestamp: datetime | None = None,
        price: Decimal | None = None,
        confidence: float = 0.75,
        metadata: dict | None = None,
    ) -> Signal:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        if price is None:
            price = Decimal("50000.00")
        if metadata is None:
            metadata = {}

        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            timestamp=timestamp,
            price=price,
            confidence=confidence,
            metadata=metadata,
        )

    return _create_signal


@pytest.fixture
def order_factory() -> Callable[..., Order]:
    """
    Factory für Order-Objekte.

    Usage:
        def test_foo(order_factory):
            order = order_factory(symbol="BTCUSDT", side="buy", quantity=0.1)
    """

    def _create_order(
        symbol: str = "BTCUSDT",
        side: str = "buy",
        quantity: Decimal | None = None,
        order_type: str = "market",
        price: Decimal | None = None,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
    ) -> Order:
        if quantity is None:
            quantity = Decimal("0.1")
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        if metadata is None:
            metadata = {}

        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            timestamp=timestamp,
            metadata=metadata,
        )

    return _create_order


@pytest.fixture
def order_result_factory() -> Callable[..., OrderResult]:
    """
    Factory für OrderResult-Objekte.

    Usage:
        def test_foo(order_result_factory):
            result = order_result_factory(status="filled")
    """

    def _create_order_result(
        order_id: str = "test-order-123",
        status: str = "filled",
        filled_quantity: Decimal | None = None,
        avg_price: Decimal | None = None,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
    ) -> OrderResult:
        if filled_quantity is None:
            filled_quantity = Decimal("0.1")
        if avg_price is None:
            avg_price = Decimal("50000.00")
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        if metadata is None:
            metadata = {}

        return OrderResult(
            order_id=order_id,
            status=status,
            filled_quantity=filled_quantity,
            avg_price=avg_price,
            timestamp=timestamp,
            metadata=metadata,
        )

    return _create_order_result


# ============================================
# CONFIGURATION FIXTURES
# ============================================


@pytest.fixture
def test_config() -> dict:
    """
    Standard-Test-Konfiguration für Services.

    Überschreibt echte ENV-Variablen mit Test-Werten.
    """
    return {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": 5432,
        "POSTGRES_DB": "cdb_test",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
    }


# ============================================
# MARKERS (bereits in pytest.ini definiert)
# ============================================
# - unit: Unit-Tests (schnell, isoliert)
# - integration: Integration-Tests (Services, DB)
# - e2e: End-to-End-Tests (Full-Stack)
# - local_only: Tests, die nur lokal laufen
# - slow: Langsame Tests (>1s)
# - chaos: Chaos-Engineering-Tests

# ============================================
# COVERAGE OVERRIDES (Targeted Runs)
# ============================================


def pytest_configure(config):
    """Relax coverage for highly targeted unit/e2e runs."""
    args = [str(arg) for arg in (config.args or [])]
    if len(args) != 1:
        return
    target = args[0].replace("\\", "/")
    if not (
        target.endswith("tests/unit/risk/test_guards.py")
        or "tests/e2e/test_paper_trading_p0.py" in target
    ):
        return
    if getattr(config.option, "cov_fail_under", None) is not None:
        config.option.cov_fail_under = 0
    cov_plugin = config.pluginmanager.getplugin("_cov")
    if cov_plugin and hasattr(cov_plugin, "options"):
        cov_plugin.options.cov_fail_under = 0

