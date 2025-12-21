"""
Data Models for Execution Service
Claire de Binare Trading Bot
"""

from typing import Literal, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.utils.clock import utcnow

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


class RejectionReason(str, Enum):
    """Structured rejection reason codes"""

    BOT_SHUTDOWN = "BOT_SHUTDOWN"
    STRATEGY_BLOCKED = "STRATEGY_BLOCKED"
    BOT_BLOCKED = "BOT_BLOCKED"
    INSUFFICIENT_LIQUIDITY = "INSUFFICIENT_LIQUIDITY"
    EXCHANGE_ERROR = "EXCHANGE_ERROR"
    API_ERROR = "API_ERROR"
    E2E_CIRCUIT_BREAKER = "E2E_CIRCUIT_BREAKER"


@dataclass
class Order:
    """Order from Risk Manager (EVENT_SCHEMA kompatibel)"""

    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    stop_loss_pct: Optional[float] = None
    strategy_id: Optional[str] = None
    bot_id: Optional[str] = None
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
            stop_loss_pct=(
                float(payload["stop_loss_pct"])
                if payload.get("stop_loss_pct") is not None
                else None
            ),
            strategy_id=payload.get("strategy_id"),
            bot_id=payload.get("bot_id"),
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
                timestamp_value = int(utcnow().timestamp())
        elif isinstance(timestamp_value, float):
            timestamp_value = int(timestamp_value)
        elif timestamp_value is None:
            timestamp_value = int(utcnow().timestamp())

        payload = {
            "type": self.type,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "timestamp": timestamp_value,
        }
        if self.stop_loss_pct is not None:
            payload["stop_loss_pct"] = self.stop_loss_pct
        if self.strategy_id is not None:
            payload["strategy_id"] = self.strategy_id
        if self.bot_id is not None:
            payload["bot_id"] = self.bot_id
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
    strategy_id: Optional[str] = None
    bot_id: Optional[str] = None
    client_id: Optional[str] = None
    price: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
    type: Literal["order_result"] = "order_result"

    # Rejection diagnostics
    source_service: Optional[str] = None
    reject_reason_code: Optional[str] = None
    reject_stage: Optional[str] = None
    causing_event_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = utcnow().isoformat()

    @staticmethod
    def _schema_status(status: str) -> str:
        """Mappt interne Stati auf EVENT_SCHEMA-Konstanten"""
        if isinstance(status, Enum):
            status = status.value
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
                    timestamp_value = int(utcnow().timestamp())
        elif isinstance(timestamp_value, float):
            timestamp_value = int(timestamp_value)
        elif timestamp_value is None:
            timestamp_value = int(utcnow().timestamp())

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
        if self.strategy_id is not None:
            payload["strategy_id"] = self.strategy_id
        if self.bot_id is not None:
            payload["bot_id"] = self.bot_id
        if self.price is not None:
            payload["price"] = self.price
        if self.client_id is not None:
            payload["client_id"] = self.client_id
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        if self.source_service is not None:
            payload["source_service"] = self.source_service
        if self.reject_reason_code is not None:
            payload["reject_reason_code"] = self.reject_reason_code
        if self.reject_stage is not None:
            payload["reject_stage"] = self.reject_stage
        if self.causing_event_id is not None:
            payload["causing_event_id"] = self.causing_event_id
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
