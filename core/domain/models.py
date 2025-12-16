"""
Core Domain Models - Shared across all CDB services
Canonical definitions for Signal, Position, Order, OrderResult.

relations:
  role: model_definition
  domain: datamodel
  upstream: []
  downstream:
    - services/db_writer/db_writer.py
    - services/execution/service.py
    - services/risk/service.py
    - services/signal/service.py
"""

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime
import time


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
class Position:
    """Trading position for portfolio tracking."""

    position_id: str
    symbol: str
    size: float
    entry_price: float
    current_price: float


@dataclass
class Order:
    """Order for execution service."""

    order_id: str | None = None
    symbol: str = ""
    side: Literal["BUY", "SELL"] = "BUY"
    quantity: float = 0.0
    price: float | None = None
    stop_loss_pct: float | None = None
    signal_id: str | None = None
    reason: str | None = None
    timestamp: int | float | None = None
    client_id: Optional[str] = None
    type: Literal["order"] = "order"  # Type-safe event type

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "stop_loss_pct": self.stop_loss_pct,
            "signal_id": self.signal_id,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "client_id": self.client_id,
        }


@dataclass
class OrderResult:
    """Order-Result Event vom Execution-Service (canonical definition)"""

    order_id: str
    status: Literal["FILLED", "REJECTED", "ERROR"]
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    filled_quantity: float
    timestamp: int
    price: Optional[float] = None
    client_id: Optional[str] = None
    error_message: Optional[str] = None
    type: Literal["order_result"] = "order_result"

    @classmethod
    def from_dict(cls, data: dict) -> "OrderResult":
        ts_raw = data.get("timestamp")
        if isinstance(ts_raw, str):
            try:
                ts = int(datetime.fromisoformat(ts_raw).timestamp())
            except ValueError:
                try:
                    ts = int(float(ts_raw))
                except ValueError:
                    ts = int(time.time())
        elif isinstance(ts_raw, (int, float)):
            ts = int(ts_raw)
        else:
            ts = int(time.time())

        status = data["status"].upper()
        if status not in {"FILLED", "REJECTED", "ERROR"}:
            raise ValueError(f"Unbekannter Order-Result-Status: {status}")

        side = data.get("side", "BUY").upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Unbekannte Order-Result-Seite: {side}")

        return cls(
            order_id=data["order_id"],
            status=status,
            symbol=data.get("symbol", ""),
            side=side,
            quantity=float(data.get("quantity", 0.0)),
            filled_quantity=float(data.get("filled_quantity", 0.0)),
            price=(float(data["price"]) if data.get("price") is not None else None),
            client_id=data.get("client_id"),
            error_message=data.get("error_message"),
            timestamp=ts,
        )
