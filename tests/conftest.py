"""
Pytest Fixtures für CDB Tests.

Zentrale Fixtures für Unit-, Integration- und Replay-Tests.
Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md
"""

import sys
from dataclasses import dataclass
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
# DATABASE FIXTURES (Deterministic State)
# ============================================

# Import DB fixtures from fixtures module
from tests.fixtures.db_fixtures import reset_db, seed_db, clean_db

# Re-export for easy access in tests
__all__ = ["reset_db", "seed_db", "clean_db"]


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
# DETERMINISTIC GATE (Issue #427)
# ============================================

E2E_NODEID_PREFIX = "tests/e2e/test_smoke_pipeline.py::"
E2E_EXPECTED_COUNT = 5
TOTAL_MIN_PASS = 267


@dataclass
class _GateState:
    total_pass: int = 0
    e2e_pass: int = 0
    e2e_total: int = 0
    total_collected: int = 0
    enabled: bool = False


_GATE_STATE: _GateState | None = None


def pytest_sessionstart(session):
    global _GATE_STATE
    _GATE_STATE = _GateState(enabled=_should_enable_gate(session.config))


def _should_enable_gate(config) -> bool:
    args = [str(arg).replace("\\", "/").rstrip("/") for arg in config.args]
    if "tests" not in args:
        return False
    if config.option.keyword:
        return False
    if config.option.markexpr:
        return False
    if getattr(config.option, "last_failed", False):
        return False
    if getattr(config.option, "failedfirst", False):
        return False
    if getattr(config.option, "collectonly", False):
        return False
    return True


def pytest_runtest_logreport(report):
    if report.when != "call":
        return

    global _GATE_STATE
    if _GATE_STATE is None:
        _GATE_STATE = _GateState()
    if not _GATE_STATE.enabled:
        return

    if report.passed:
        _GATE_STATE.total_pass += 1

    if report.nodeid.startswith(E2E_NODEID_PREFIX):
        _GATE_STATE.e2e_total += 1
        if report.passed:
            _GATE_STATE.e2e_pass += 1


def pytest_collection_finish(session):
    if _GATE_STATE is None:
        return
    if not _GATE_STATE.enabled:
        return
    _GATE_STATE.total_collected = len(session.items)


def pytest_sessionfinish(session, exitstatus):
    if _GATE_STATE is None:
        return
    if not _GATE_STATE.enabled:
        return

    gate_failed = False
    if _GATE_STATE.e2e_total != E2E_EXPECTED_COUNT:
        gate_failed = True
    if _GATE_STATE.e2e_pass != E2E_EXPECTED_COUNT:
        gate_failed = True
    if _GATE_STATE.total_pass < TOTAL_MIN_PASS:
        gate_failed = True

    if gate_failed and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if _GATE_STATE is None:
        return
    if not _GATE_STATE.enabled:
        return

    total_collected = _GATE_STATE.total_collected
    pass_rate = 0.0
    if total_collected > 0:
        pass_rate = (_GATE_STATE.total_pass / total_collected) * 100

    terminalreporter.write_line(
        f"E2E: {_GATE_STATE.e2e_pass}/{E2E_EXPECTED_COUNT} PASS"
    )
    terminalreporter.write_line(
        f"Total: {_GATE_STATE.total_pass}/{total_collected} PASS"
    )
    terminalreporter.write_line(f"Pass-Rate: {pass_rate:.2f}%")
