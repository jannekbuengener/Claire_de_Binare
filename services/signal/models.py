"""
Signal Engine - Data Models
Datenklassen für Market-Data (signal_engine specific)
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Signal:
    """Trading signal with lightweight fields used across services and tests."""

    signal_id: str | None = None
    symbol: str = ""
    direction: str = ""
    strength: float = 0.0
    timestamp: float | int = 0.0
    side: Literal["BUY", "SELL"] | None = None
    confidence: float | None = None  # 0.0 - 1.0
    reason: str | None = None
    price: float | None = None
    pct_change: float | None = None
    type: Literal["signal"] = "signal"  # Type-safe event type

    def __post_init__(self):
        # Backfill legacy fields from simplified inputs.
        if self.side is None and self.direction:
            self.side = self.direction
        if self.confidence is None:
            self.confidence = self.strength

    def to_dict(self) -> dict:
        """Convert to a plain dictionary for transport."""
        return {
            "type": self.type,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "strength": self.strength,
            "timestamp": self.timestamp,
            "side": self.side,
            "confidence": self.confidence,
            "reason": self.reason,
            "price": self.price,
            "pct_change": self.pct_change,
        }


@dataclass
class MarketData:
    """Marktdaten vom Screener"""

    symbol: str
    price: float
    volume: float
    pct_change: float
    timestamp: int
    interval: str = "15m"
    type: Literal["market_data"] = "market_data"  # Type-safe event type

    @classmethod
    def from_dict(cls, data: dict):
        """Erstellt MarketData aus Dictionary"""
        return cls(
            symbol=data["symbol"],
            price=float(data["price"]),
            volume=float(data["volume"]),
            pct_change=float(data["pct_change"]),
            timestamp=int(data["timestamp"]),
            interval=data.get("interval", "15m"),
            type=data.get("type", "market_data"),
        )
