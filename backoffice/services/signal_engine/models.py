"""
Signal Engine - Data Models
Datenklassen für Market-Data und Signals
"""

from dataclasses import dataclass
from typing import Literal


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


@dataclass
class Signal:
    """Trading-Signal"""

    symbol: str
    side: Literal["BUY", "SELL"]
    confidence: float  # 0.0 - 1.0
    reason: str
    timestamp: int
    price: float
    pct_change: float
    type: Literal["signal"] = "signal"  # Type-safe event type

    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary für Redis"""
        return {
            "type": self.type,
            "symbol": self.symbol,
            "side": self.side,
            "signal_type": self.side.lower(),  # DB-kompatibel: 'buy'/'sell'
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "price": self.price,
            "pct_change": self.pct_change,
            "source": "momentum_strategy",     # Quelle des Signals
        }

    @staticmethod
    def generate_reason(pct_change: float, threshold: float) -> str:
        """Generiert Begründung für Signal"""
        return f"Momentum: {pct_change:+.2f}% (Schwelle: {threshold}%)"

