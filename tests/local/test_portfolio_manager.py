"""
Unit Tests für Portfolio Manager
Test Portfolio State Management, Position Tracking, P&L Calculation
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add service path
service_path = Path(__file__).parent.parent / "backoffice" / "services" / "portfolio_manager"
sys.path.insert(0, str(service_path))

from portfolio_manager import PortfolioManager  # noqa: E402
from models import PositionSide  # noqa: E402

# Diese Tests sind als local_only markiert wegen Import-Komplexität
pytestmark = pytest.mark.local_only


@pytest.fixture
def mock_redis():
    """Mock Redis client with in-memory state"""
    class MockRedis:
        def __init__(self):
            self._hash_data = {}  # Hash storage
            self._string_data = {}  # String storage

        def exists(self, key):
            return key in self._hash_data or key in self._string_data

        def hgetall(self, key):
            # Return dict with bytes keys (like real Redis)
            data = self._hash_data.get(key, {})
            return {k.encode() if isinstance(k, str) else k: v
                    for k, v in data.items()}

        def hset(self, key, mapping=None, **kwargs):
            if key not in self._hash_data:
                self._hash_data[key] = {}
            if mapping:
                self._hash_data[key].update(mapping)
            if kwargs:
                self._hash_data[key].update(kwargs)

        def get(self, key):
            return self._string_data.get(key, None)

        def set(self, key, value):
            self._string_data[key] = value

    return MockRedis()


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL connection"""
    pg_mock = Mock()
    pg_mock.cursor = Mock(return_value=Mock())
    pg_mock.commit = Mock()
    pg_mock.rollback = Mock()
    return pg_mock


@pytest.fixture
def portfolio_manager(mock_redis, mock_postgres):
    """PortfolioManager with mocked dependencies"""
    return PortfolioManager(
        redis_client=mock_redis,
        postgres_conn=mock_postgres,
        initial_capital=100000.0
    )


@pytest.mark.unit
def test_portfolio_initialization(portfolio_manager, mock_redis):
    """Test: Portfolio wird mit Initial Capital initialisiert"""
    # get_state sollte Initialize triggern
    state = portfolio_manager.get_state()

    # Verify state wurde in Redis gespeichert
    assert mock_redis.exists("portfolio:state")
    assert state.equity == 100000.0
    assert state.cash == 100000.0
    assert len(state.positions) == 0


@pytest.mark.unit
def test_open_position_long(portfolio_manager):
    """Test: Long Position kann geöffnet werden"""
    state = portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    assert "BTCUSDT" in state.positions
    position = state.positions["BTCUSDT"]

    assert position.symbol == "BTCUSDT"
    assert position.side == PositionSide.LONG
    assert position.quantity == 1.0
    assert position.entry_price == 50000.0
    assert position.current_price == 50000.0
    assert position.unrealized_pnl == 0.0

    # Cash should be reduced
    assert state.cash == 100000.0 - 50000.0


@pytest.mark.unit
def test_open_position_short(portfolio_manager):
    """Test: Short Position kann geöffnet werden"""
    state = portfolio_manager.open_position(
        symbol="ETHUSDT",
        side="SELL",
        quantity=10.0,
        price=3000.0
    )

    assert "ETHUSDT" in state.positions
    position = state.positions["ETHUSDT"]

    assert position.side == PositionSide.SHORT
    assert position.quantity == 10.0
    assert position.entry_price == 3000.0


@pytest.mark.unit
def test_insufficient_cash(portfolio_manager):
    """Test: Position wird rejected bei insufficient cash"""
    # Versuche Position zu öffnen die mehr als Equity kostet
    state = portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=3.0,  # 150k notional
        price=50000.0
    )

    # Position sollte NICHT geöffnet werden
    assert "BTCUSDT" not in state.positions
    assert state.cash == 100000.0  # Unverändert


@pytest.mark.unit
def test_close_position_profit(portfolio_manager):
    """Test: Position schließen mit Profit"""
    # Open position
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    # Close with profit
    state = portfolio_manager.close_position(
        symbol="BTCUSDT",
        exit_price=51000.0
    )

    # Position should be removed
    assert "BTCUSDT" not in state.positions

    # P&L should be +1000
    assert state.total_realized_pnl == 1000.0
    assert state.daily_pnl == 1000.0

    # Cash should be 50k (initial) + 51k (exit)
    assert state.cash == 50000.0 + 51000.0


@pytest.mark.unit
def test_close_position_loss(portfolio_manager):
    """Test: Position schließen mit Loss"""
    # Open
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    # Close with loss
    state = portfolio_manager.close_position(
        symbol="BTCUSDT",
        exit_price=49000.0
    )

    # P&L should be -1000
    assert state.total_realized_pnl == -1000.0
    assert state.daily_pnl == -1000.0


@pytest.mark.unit
def test_update_prices(portfolio_manager):
    """Test: Price Updates aktualisieren unrealized P&L"""
    # Open position
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    # Update price
    state = portfolio_manager.update_prices({
        "BTCUSDT": 51000.0
    })

    position = state.positions["BTCUSDT"]

    # Unrealized P&L should be +1000
    assert position.unrealized_pnl == 1000.0
    assert position.current_price == 51000.0

    # Equity should include unrealized
    assert state.equity == 50000.0 + 1000.0  # cash + unrealized


@pytest.mark.unit
def test_multiple_positions(portfolio_manager):
    """Test: Mehrere Positionen gleichzeitig"""
    # Open BTC Long
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    # Open ETH Short
    portfolio_manager.open_position(
        symbol="ETHUSDT",
        side="SELL",
        quantity=10.0,
        price=3000.0
    )

    state = portfolio_manager.get_state()

    assert len(state.positions) == 2
    assert "BTCUSDT" in state.positions
    assert "ETHUSDT" in state.positions

    # Total exposure
    total_notional = 50000 + 30000
    assert state.total_exposure == total_notional


@pytest.mark.unit
def test_get_risk_state(portfolio_manager):
    """Test: Risk State wird korrekt formatiert"""
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    risk_state = portfolio_manager.get_risk_state()

    assert "equity" in risk_state
    assert "daily_pnl" in risk_state
    assert "total_exposure_pct" in risk_state
    assert "num_positions" in risk_state

    assert risk_state["equity"] == 100000.0
    assert risk_state["num_positions"] == 1


@pytest.mark.unit
def test_exposure_percentage(portfolio_manager):
    """Test: Exposure Percentage wird korrekt berechnet"""
    # Open 50k position (50% exposure)
    state = portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    # Total exposure should be 50%
    assert state.total_exposure == 50000.0
    assert state.total_exposure_pct == 50.0


@pytest.mark.unit
def test_create_snapshot(portfolio_manager):
    """Test: Portfolio Snapshot kann erstellt werden"""
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    snapshot = portfolio_manager.create_snapshot()

    assert snapshot.equity == 100000.0
    assert snapshot.num_positions == 1
    assert snapshot.total_exposure == 50000.0
    assert snapshot.timestamp is not None


@pytest.mark.unit
def test_reset_daily_stats(portfolio_manager):
    """Test: Daily Stats können resettet werden"""
    # Make some trades
    portfolio_manager.open_position(
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0
    )

    state = portfolio_manager.get_state()
    assert state.daily_volume > 0

    # Reset
    portfolio_manager.reset_daily_stats()

    state = portfolio_manager.get_state()
    assert state.daily_pnl == 0.0
    assert state.daily_volume == 0.0
