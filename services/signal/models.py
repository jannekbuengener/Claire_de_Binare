"""
Signal Engine - Data Models
Datenklassen für Market-Data (signal_engine specific)
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Signal:
    """Trading signal with lightweight fields used across services and tests."""

    schema_version: str = "v1.0"
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
        if self.side:
            self.side = self.side.upper()

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        """Create a Signal from a transport payload."""
        return cls(
            signal_id=data.get("signal_id"),
            strategy_id=data.get("strategy_id"),
            bot_id=data.get("bot_id"),
            symbol=data.get("symbol", ""),
            direction=data.get("direction", ""),
            strength=float(data.get("strength", 0.0)),
            timestamp=data.get("timestamp", 0.0),
            side=data.get("side"),
            confidence=data.get("confidence"),
            reason=data.get("reason"),
            price=data.get("price"),
            pct_change=data.get("pct_change"),
        )

    def to_dict(self) -> dict:
        """Convert to a plain dictionary for transport."""
        # Filter out None values for Redis compatibility (xadd doesn't accept None)
        return {
            k: v
            for k, v in {
                "type": self.type,
                "schema_version": self.schema_version,
                "signal_id": self.signal_id,
                "strategy_id": self.strategy_id,
                "bot_id": self.bot_id,
                "symbol": self.symbol,
                "strength": self.strength,
                "timestamp": int(self.timestamp),
                "side": self.side,
                "confidence": self.confidence,
                "reason": self.reason,
                "price": self.price,
                "pct_change": self.pct_change,
            }.items()
            if v is not None
        }


@dataclass
class MarketData:
    """Marktdaten vom Screener"""

    # Required fields (no defaults) must come first
    symbol: str
    price: float
    timestamp: int

    # Optional fields (with defaults) come after
    schema_version: str | None = None
    source: str | None = None
    trade_qty: float | None = None
    pct_change: float | None = None  # Optional: calculated by signal engine if missing
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float = 0.0
    interval: str = "15m"
    venue: str | None = None
    side: str | None = None
    trade_id: str | None = None
    type: Literal["market_data"] = "market_data"  # Type-safe event type

    @classmethod
    def from_dict(cls, data: dict):
        """Erstellt MarketData aus Dictionary"""
        # Handle pct_change with fallback for backward compatibility
        pct_change_raw = data.get("pct_change")
        pct_change = float(pct_change_raw) if pct_change_raw is not None else None

        trade_qty_raw = data.get("trade_qty")
        if trade_qty_raw is None:
            trade_qty_raw = data.get("qty")
        trade_qty = (
            float(trade_qty_raw) if trade_qty_raw is not None and trade_qty_raw != "" else None
        )

        volume_raw = data.get("volume")
        if volume_raw is not None and volume_raw != "":
            volume = float(volume_raw)
        elif trade_qty is not None:
            volume = trade_qty
        else:
            volume = 0.0

        symbol = data["symbol"].upper() if isinstance(data.get("symbol"), str) else data["symbol"]
        timestamp = data.get("timestamp")
        if timestamp is None:
            timestamp = data.get("ts_ms", 0)

        return cls(
            symbol=symbol,
            price=float(data["price"]),
            timestamp=int(timestamp or 0),
            schema_version=data.get("schema_version"),
            source=data.get("source"),
            trade_qty=trade_qty,
            pct_change=pct_change,
            open=(float(data["open"]) if data.get("open") is not None else None),
            high=(float(data["high"]) if data.get("high") is not None else None),
            low=(float(data["low"]) if data.get("low") is not None else None),
            close=(float(data["close"]) if data.get("close") is not None else None),
            volume=volume,
            interval=data.get("interval", "15m"),
            venue=data.get("venue"),
            side=data.get("side"),
            trade_id=data.get("trade_id"),
            type=data.get("type", "market_data"),
        )
