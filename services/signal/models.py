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
    strategy_id: str | None = None
    bot_id: str | None = None
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

    def to_dict(self) -> dict:
        """Convert to a plain dictionary for transport."""
        return {
            "type": self.type,
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "bot_id": self.bot_id,
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

    # Required fields (no defaults) must come first
    symbol: str
    price: float
    pct_change: float
    timestamp: int

    # Optional fields (with defaults) come after
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float = 0.0
    interval: str = "15m"
    venue: str | None = None
    type: Literal["market_data"] = "market_data"  # Type-safe event type

    @classmethod
    def from_dict(cls, data: dict):
        """Erstellt MarketData aus Dictionary"""
        return cls(
            symbol=data["symbol"],
            price=float(data["price"]),
            open=(float(data["open"]) if data.get("open") is not None else None),
            high=(float(data["high"]) if data.get("high") is not None else None),
            low=(float(data["low"]) if data.get("low") is not None else None),
            close=(float(data["close"]) if data.get("close") is not None else None),
            volume=float(data.get("volume", 0.0)),
            pct_change=float(data["pct_change"]),
            timestamp=int(data["timestamp"]),
            interval=data.get("interval", "15m"),
            venue=data.get("venue"),
            type=data.get("type", "market_data"),
        )
