"""
Risk Manager - Data Models (risk_manager specific)

Signal model moved to backoffice.services.common.models (canonical definition).
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import time
from datetime import datetime


@dataclass
class Order:
    """Order für Execution-Service"""

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
    """Order-Result Event vom Execution-Service"""

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


@dataclass
class Alert:
    """Alert bei Risk-Limit-Verletzung"""

    level: Literal["INFO", "WARNING", "CRITICAL"]
    code: str
    message: str
    context: dict
    timestamp: int
    type: Literal["alert"] = "alert"  # Type-safe event type

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp,
        }


@dataclass
class RiskState:
    """Aktueller Risk-Status mit erweiterten Safety Tracking"""

    total_exposure: float = 0.0
    daily_pnl: float = 0.0
    open_positions: int = 0
    signals_blocked: int = 0
    signals_approved: int = 0
    circuit_breaker_active: bool = False
    circuit_breaker_triggered_at: Optional[int] = None  # Timestamp when circuit breaker was triggered
    emergency_stop_active: bool = False  # Emergency kill switch status
    positions: dict[str, float] = field(default_factory=dict)  # symbol -> quantity
    pending_orders: int = 0
    last_prices: dict[str, float] = field(default_factory=dict)  # symbol -> last_price

    def get_position_count(self) -> int:
        """Get number of open positions"""
        return sum(1 for qty in self.positions.values() if abs(qty) > 1e-6)

    def get_symbol_position(self, symbol: str) -> float:
        """Get current position size for symbol"""
        return abs(self.positions.get(symbol, 0.0))

    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol"""
        return abs(self.positions.get(symbol, 0.0)) > 1e-6
