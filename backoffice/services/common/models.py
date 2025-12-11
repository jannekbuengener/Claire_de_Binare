"""
Shared data models for inter-service communication

This module contains canonical definitions of data models used across multiple services.
All services must import from this module to ensure consistency and avoid duplication.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class Signal:
    """Trading signal (canonical definition for signals topic)

    This is the single source of truth for the Signal model.
    Produced by: signal_engine
    Consumed by: risk_manager
    """

    symbol: str
    side: Literal["BUY", "SELL"]
    confidence: float  # 0.0 - 1.0
    reason: str
    timestamp: int
    price: float
    pct_change: float
    type: Literal["signal"] = "signal"  # Type-safe event type

    def to_dict(self) -> dict:
        """Convert to dictionary for Redis publish"""
        return {
            "type": self.type,
            "symbol": self.symbol,
            "side": self.side,
            "signal_type": self.side.lower(),  # DB-compatible: 'buy'/'sell'
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "price": self.price,
            "pct_change": self.pct_change,
            "source": "momentum_strategy",
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Parse from Redis message"""
        return cls(
            symbol=data["symbol"],
            side=data["side"],
            confidence=float(data["confidence"]),
            reason=data["reason"],
            timestamp=int(data["timestamp"]),
            price=float(data["price"]),
            pct_change=float(data["pct_change"]),
            type=data.get("type", "signal"),
        )

    @staticmethod
    def generate_reason(pct_change: float, threshold: float) -> str:
        """Generate signal reason text"""
        return f"Momentum: {pct_change:+.2f}% (Schwelle: {threshold}%)"
