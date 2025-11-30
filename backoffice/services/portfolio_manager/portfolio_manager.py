"""
Portfolio Manager - Core Logic
Claire de Binare Trading Bot

Manages portfolio state in Redis and persists to PostgreSQL
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime

import redis

try:
    from .models import Position, PositionSide, PortfolioState, PortfolioSnapshot
except ImportError:
    from models import Position, PositionSide, PortfolioState, PortfolioSnapshot


logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Manages portfolio state with Redis (real-time) and PostgreSQL (persistence)

    Responsibilities:
    - Track open positions
    - Calculate equity & exposure
    - Update P&L (realized + unrealized)
    - Persist snapshots to PostgreSQL
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        postgres_conn,
        initial_capital: float = 100000.0,
    ):
        """
        Initialize Portfolio Manager

        Args:
            redis_client: Redis connection for state storage
            postgres_conn: PostgreSQL connection for persistence
            initial_capital: Starting capital (default: 100k)
        """
        self.redis = redis_client
        self.db = postgres_conn
        self.initial_capital = initial_capital

        # Redis keys
        self.STATE_KEY = "portfolio:state"
        self.POSITIONS_KEY = "portfolio:positions"

        # Initialize if needed
        self._initialize_portfolio()

    def _initialize_portfolio(self):
        """Initialize portfolio if not exists"""
        if not self.redis.exists(self.STATE_KEY):
            logger.info(f"Initializing portfolio with {self.initial_capital} capital")

            initial_state = PortfolioState(
                equity=self.initial_capital,
                cash=self.initial_capital,
                positions={},
                total_unrealized_pnl=0.0,
                total_realized_pnl=0.0,
                daily_pnl=0.0,
                daily_volume=0.0,
                num_trades=0,
            )

            self._save_state(initial_state)

    def get_state(self) -> PortfolioState:
        """Retrieve current portfolio state from Redis"""
        data = self.redis.hgetall(self.STATE_KEY)

        if not data:
            # Fallback to initialization
            self._initialize_portfolio()
            data = self.redis.hgetall(self.STATE_KEY)

        # Parse positions
        positions_json = self.redis.get(self.POSITIONS_KEY)
        positions = {}

        if positions_json:
            positions_data = json.loads(positions_json)
            positions = {
                symbol: Position(**pos_data)
                for symbol, pos_data in positions_data.items()
            }

        # Handle timestamp (might be bytes or string from mock)
        timestamp_raw = data.get(b"timestamp", datetime.now(datetime.UTC).isoformat())
        timestamp = (
            timestamp_raw.decode()
            if isinstance(timestamp_raw, bytes)
            else timestamp_raw
        )

        return PortfolioState(
            equity=float(data.get(b"equity", self.initial_capital)),
            cash=float(data.get(b"cash", self.initial_capital)),
            positions=positions,
            total_unrealized_pnl=float(data.get(b"total_unrealized_pnl", 0.0)),
            total_realized_pnl=float(data.get(b"total_realized_pnl", 0.0)),
            daily_pnl=float(data.get(b"daily_pnl", 0.0)),
            daily_volume=float(data.get(b"daily_volume", 0.0)),
            num_trades=int(data.get(b"num_trades", 0)),
            timestamp=timestamp,
        )

    def _save_state(self, state: PortfolioState):
        """Save portfolio state to Redis"""
        # Save main state
        self.redis.hset(
            self.STATE_KEY,
            mapping={
                "equity": state.equity,
                "cash": state.cash,
                "total_unrealized_pnl": state.total_unrealized_pnl,
                "total_realized_pnl": state.total_realized_pnl,
                "daily_pnl": state.daily_pnl,
                "daily_volume": state.daily_volume,
                "num_trades": state.num_trades,
                "timestamp": state.timestamp,
            },
        )

        # Save positions separately (JSON)
        positions_data = {
            symbol: {
                "symbol": pos.symbol,
                "side": pos.side.value if hasattr(pos.side, "value") else pos.side,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": pos.realized_pnl,
                "stop_loss": pos.stop_loss,
                "entry_timestamp": pos.entry_timestamp,
            }
            for symbol, pos in state.positions.items()
        }

        self.redis.set(self.POSITIONS_KEY, json.dumps(positions_data))

        logger.debug(
            f"Saved portfolio state: Equity={state.equity:.2f}, Positions={len(state.positions)}"
        )

    def open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_loss: Optional[float] = None,
    ) -> PortfolioState:
        """
        Open a new position

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: BUY/SELL or LONG/SHORT
            quantity: Order quantity
            price: Execution price
            stop_loss: Optional stop-loss price

        Returns:
            Updated PortfolioState
        """
        state = self.get_state()

        # Normalize side
        position_side = (
            PositionSide.LONG if side.upper() in ["BUY", "LONG"] else PositionSide.SHORT
        )

        # Calculate notional cost
        notional = quantity * price

        # Check if we have enough cash
        if notional > state.cash:
            logger.warning(
                f"Insufficient cash for {symbol}: {notional:.2f} > {state.cash:.2f}"
            )
            return state

        # Create position
        position = Position(
            symbol=symbol,
            side=position_side,
            quantity=quantity,
            entry_price=price,
            current_price=price,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            stop_loss=stop_loss,
        )

        # Update state
        state.positions[symbol] = position
        state.cash -= notional
        state.daily_volume += notional
        state.num_trades += 1

        self._save_state(state)

        logger.info(f"Opened position: {symbol} {side} {quantity} @ {price}")

        return state

    def close_position(self, symbol: str, exit_price: float) -> PortfolioState:
        """
        Close an existing position

        Args:
            symbol: Trading symbol
            exit_price: Exit price

        Returns:
            Updated PortfolioState
        """
        state = self.get_state()

        if symbol not in state.positions:
            logger.warning(f"Position {symbol} not found")
            return state

        position = state.positions[symbol]

        # Calculate realized P&L
        if position.side == PositionSide.LONG:
            pnl = (exit_price - position.entry_price) * position.quantity
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * position.quantity

        # Update state
        notional = position.quantity * exit_price
        state.cash += notional
        state.total_realized_pnl += pnl
        state.daily_pnl += pnl
        state.daily_volume += notional
        state.num_trades += 1

        # Remove position
        del state.positions[symbol]

        # Recalculate equity
        state.equity = state.cash + state.total_unrealized_pnl

        self._save_state(state)

        logger.info(f"Closed position: {symbol} @ {exit_price}, P&L: {pnl:.2f}")

        return state

    def update_prices(self, price_updates: Dict[str, float]) -> PortfolioState:
        """
        Update current prices for all positions

        Args:
            price_updates: Dict of {symbol: current_price}

        Returns:
            Updated PortfolioState
        """
        state = self.get_state()

        total_unrealized = 0.0

        for symbol, position in state.positions.items():
            if symbol in price_updates:
                new_price = price_updates[symbol]
                position.current_price = new_price

                # Calculate unrealized P&L
                if position.side == PositionSide.LONG:
                    position.unrealized_pnl = (
                        new_price - position.entry_price
                    ) * position.quantity
                else:  # SHORT
                    position.unrealized_pnl = (
                        position.entry_price - new_price
                    ) * position.quantity

                total_unrealized += position.unrealized_pnl

        state.total_unrealized_pnl = total_unrealized
        state.equity = state.cash + total_unrealized

        self._save_state(state)

        return state

    def get_risk_state(self) -> Dict:
        """
        Get risk-relevant state for Risk Manager

        Returns:
            Dict with equity, daily_pnl, total_exposure_pct
        """
        state = self.get_state()

        return {
            "equity": state.equity,
            "daily_pnl": state.daily_pnl,
            "total_exposure_pct": state.total_exposure_pct / 100.0,  # As decimal
            "num_positions": len(state.positions),
            "cash": state.cash,
        }

    def create_snapshot(self) -> PortfolioSnapshot:
        """Create a snapshot for persistence"""
        state = self.get_state()

        daily_pnl_pct = (
            (state.daily_pnl / self.initial_capital) * 100
            if self.initial_capital > 0
            else 0.0
        )

        return PortfolioSnapshot(
            timestamp=datetime.now(datetime.UTC).isoformat(),
            equity=state.equity,
            cash=state.cash,
            total_exposure=state.total_exposure,
            total_exposure_pct=state.total_exposure_pct,
            num_positions=len(state.positions),
            daily_pnl=state.daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            total_realized_pnl=state.total_realized_pnl,
            num_trades=state.num_trades,
        )

    def persist_snapshot(self):
        """Persist current state snapshot to PostgreSQL"""
        snapshot = self.create_snapshot()

        try:
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT INTO portfolio_snapshots
                (timestamp, equity, cash, total_exposure, total_exposure_pct,
                 num_positions, daily_pnl, daily_pnl_pct, total_realized_pnl, num_trades)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    snapshot.timestamp,
                    snapshot.equity,
                    snapshot.cash,
                    snapshot.total_exposure,
                    snapshot.total_exposure_pct,
                    snapshot.num_positions,
                    snapshot.daily_pnl,
                    snapshot.daily_pnl_pct,
                    snapshot.total_realized_pnl,
                    snapshot.num_trades,
                ),
            )
            self.db.commit()
            logger.debug(f"Persisted snapshot: Equity={snapshot.equity:.2f}")
        except Exception as e:
            logger.error(f"Failed to persist snapshot: {e}")
            self.db.rollback()

    def reset_daily_stats(self):
        """Reset daily statistics (call at start of day)"""
        state = self.get_state()
        state.daily_pnl = 0.0
        state.daily_volume = 0.0
        self._save_state(state)
        logger.info("Reset daily statistics")
