"""
Portfolio Manager - Data Models
Claire de Binaire Trading Bot

Models für Portfolio State, Positions, und Equity Tracking
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from enum import Enum


class PositionSide(str, Enum):
    """Position side: LONG or SHORT"""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Single position in portfolio"""

    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    entry_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def notional_value(self) -> float:
        """Calculate notional value"""
        return self.quantity * self.current_price

    @property
    def pnl_pct(self) -> float:
        """Calculate P&L percentage"""
        if self.entry_price == 0:
            return 0.0
        return (self.unrealized_pnl / (self.quantity * self.entry_price)) * 100


@dataclass
class PortfolioState:
    """Complete portfolio state"""

    equity: float
    cash: float
    positions: Dict[str, Position]
    total_unrealized_pnl: float
    total_realized_pnl: float
    daily_pnl: float
    daily_volume: float
    num_trades: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def total_exposure(self) -> float:
        """Total notional exposure across all positions"""
        return sum(pos.notional_value for pos in self.positions.values())

    @property
    def total_exposure_pct(self) -> float:
        """Total exposure as percentage of equity"""
        if self.equity == 0:
            return 0.0
        return (self.total_exposure / self.equity) * 100

    @property
    def available_cash_pct(self) -> float:
        """Available cash as percentage of equity"""
        if self.equity == 0:
            return 0.0
        return (self.cash / self.equity) * 100


@dataclass
class PortfolioSnapshot:
    """Historical snapshot for analytics"""

    timestamp: str
    equity: float
    cash: float
    total_exposure: float
    total_exposure_pct: float
    num_positions: int
    daily_pnl: float
    daily_pnl_pct: float
    total_realized_pnl: float
    num_trades: int

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "timestamp": self.timestamp,
            "equity": self.equity,
            "cash": self.cash,
            "total_exposure": self.total_exposure,
            "total_exposure_pct": self.total_exposure_pct,
            "num_positions": self.num_positions,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.daily_pnl_pct,
            "total_realized_pnl": self.total_realized_pnl,
            "num_trades": self.num_trades,
        }
