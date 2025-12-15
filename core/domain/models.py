---
relations:
  role: model_definition
  domain: datamodel
  upstream: []
  downstream:
    - services/db_writer/db_writer.py
    - services/execution/service.py
    - services/risk/service.py
    - services/signal/service.py
---
"""
Core Domain Models - Shared across all CDB services
Canonical definitions for Signal, Order, OrderResult, etc.
"""

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime
import time


@dataclass
class Signal:
    """Trading-Signal (canonical definition)"""

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
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "price": self.price,
            "pct_change": self.pct_change,
        }

    @staticmethod
    def generate_reason(pct_change: float, threshold: float) -> str:
        """Generiert Begründung für Signal"""
        return f"Momentum: {pct_change:+.2f}% (Schwelle: {threshold}%)"


@dataclass
class Order:
    """Order für Execution-Service (canonical definition)"""

    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    stop_loss_pct: float
    signal_id: int
    reason: str
    timestamp: int
    client_id: Optional[str] = None
    type: Literal["order"] = "order"  # Type-safe event type

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
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
