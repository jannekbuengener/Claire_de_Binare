"""
Signal Engine - Data Models
Datenklassen für Market-Data (signal_engine specific)

Signal model moved to backoffice.services.common.models (canonical definition).
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
