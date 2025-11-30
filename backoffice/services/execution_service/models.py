"""
Data Models for Execution Service
Claire de Binare Trading Bot
"""

from typing import Literal, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    """Order side: BUY or SELL"""

    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"  # Alias for BUY
    SHORT = "SHORT"  # Alias for SELL


class OrderStatus(str, Enum):
    """Order execution status"""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class Order:
    """Order from Risk Manager (EVENT_SCHEMA kompatibel)"""

    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price: Optional[float] = None  # Signal price for realistic execution
    stop_loss_pct: Optional[float] = None
    client_id: Optional[str] = None
    timestamp: Optional[int | float | str] = None
    type: Literal["order"] = "order"

    @classmethod
    def from_event(cls, payload: dict) -> "Order":
        """Erstellt Order aus einem Event-Payload"""
        if payload.get("type") not in (None, "order"):
            raise ValueError(f"Ungueltiger Order-Typ: {payload.get('type')}")

        side = payload["side"].upper()
        if side not in ("BUY", "SELL"):
            raise ValueError(f"Unbekannte Order-Seite: {payload['side']}")

        return cls(
            symbol=payload["symbol"],
            side=side,
            quantity=float(payload["quantity"]),
            price=(
                float(payload["price"]) if payload.get("price") is not None else None
            ),
            stop_loss_pct=(
                float(payload["stop_loss_pct"])
                if payload.get("stop_loss_pct") is not None
                else None
            ),
            client_id=payload.get("client_id"),
            timestamp=payload.get("timestamp"),
        )

    def to_dict(self) -> dict:
        """Konvertiert in ein schema-konformes Dictionary"""
        timestamp_value = self.timestamp
        if isinstance(timestamp_value, str):
            try:
                timestamp_value = int(float(timestamp_value))
            except ValueError:
                timestamp_value = int(datetime.utcnow().timestamp())
        elif isinstance(timestamp_value, float):
            timestamp_value = int(timestamp_value)
        elif timestamp_value is None:
            timestamp_value = int(datetime.utcnow().timestamp())

        payload = {
            "type": self.type,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "timestamp": timestamp_value,
        }
        if self.stop_loss_pct is not None:
            payload["stop_loss_pct"] = self.stop_loss_pct
        if self.client_id is not None:
            payload["client_id"] = self.client_id
        return payload


@dataclass
class ExecutionResult:
    """Ergebnis der Orderausfuehrung (EVENT_SCHEMA kompatibel)"""

    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    filled_quantity: float
    status: str
    client_id: Optional[str] = None
    price: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
    type: Literal["order_result"] = "order_result"

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    @staticmethod
    def _schema_status(status: str) -> str:
        """Mappt interne Stati auf EVENT_SCHEMA-Konstanten"""
        if status in {"FILLED", "REJECTED", "ERROR"}:
            return status
        if status in {OrderStatus.FAILED.value, OrderStatus.CANCELLED.value}:
            return "ERROR"
        if status == OrderStatus.PARTIALLY_FILLED.value:
            return "FILLED"
        if status in {OrderStatus.SUBMITTED.value, OrderStatus.PENDING.value}:
            return "ERROR"
        return status

    def to_dict(self) -> dict:
        """Konvertiert in ein schema-konformes Dictionary"""
        timestamp_value = self.timestamp
        if isinstance(timestamp_value, str):
            try:
                timestamp_value = int(
                    datetime.fromisoformat(timestamp_value).timestamp()
                )
            except ValueError:
                try:
                    timestamp_value = int(float(timestamp_value))
                except ValueError:
                    timestamp_value = int(datetime.utcnow().timestamp())
        elif isinstance(timestamp_value, float):
            timestamp_value = int(timestamp_value)
        elif timestamp_value is None:
            timestamp_value = int(datetime.utcnow().timestamp())

        payload = {
            "type": self.type,
            "order_id": self.order_id,
            "status": self._schema_status(self.status),
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "timestamp": timestamp_value,
        }
        if self.price is not None:
            payload["price"] = self.price
        if self.client_id is not None:
            payload["client_id"] = self.client_id
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload


@dataclass
class Trade:
    """Executed trade for database"""

    trade_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "timestamp": self.timestamp,
        }
