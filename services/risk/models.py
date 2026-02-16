"""
Risk Manager - Data Models (risk_manager specific)
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import time
from datetime import datetime


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
    pct_change_15m: float | None = None
    volume_15m: float | None = None
    ts_ms: int | None = None
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
            "pct_change_15m": self.pct_change_15m,
            "volume_15m": self.volume_15m,
            "ts_ms": self.ts_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        """Create Signal from dictionary (inverse of to_dict)."""
        pct_change_15m_raw = data.get("pct_change_15m")
        try:
            pct_change_15m = (
                float(pct_change_15m_raw) if pct_change_15m_raw is not None else None
            )
        except (TypeError, ValueError):
            pct_change_15m = None

        volume_15m_raw = data.get("volume_15m")
        try:
            volume_15m = float(volume_15m_raw) if volume_15m_raw is not None else None
        except (TypeError, ValueError):
            volume_15m = None

        ts_ms_raw = data.get("ts_ms")
        try:
            ts_ms = int(ts_ms_raw) if ts_ms_raw is not None else None
        except (TypeError, ValueError):
            ts_ms = None

        return cls(
            signal_id=data.get("signal_id"),
            strategy_id=data.get("strategy_id"),
            bot_id=data.get("bot_id"),
            symbol=data.get("symbol", ""),
            direction=data.get("direction", ""),
            strength=float(data.get("strength", 0.0)),
            timestamp=float(data.get("timestamp", 0.0)),
            side=data.get("side"),
            confidence=(
                float(data["confidence"])
                if data.get("confidence") is not None
                else None
            ),
            reason=data.get("reason"),
            price=(float(data["price"]) if data.get("price") is not None else None),
            pct_change=(
                float(data["pct_change"])
                if data.get("pct_change") is not None
                else None
            ),
            pct_change_15m=pct_change_15m,
            volume_15m=volume_15m,
            ts_ms=ts_ms,
        )


@dataclass
class Order:
    """Order für Execution-Service"""

    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    stop_loss_pct: float
    signal_id: str  # Changed from int to str (signal_id from Signal service)
    reason: str
    timestamp: int
    strategy_id: str
    bot_id: Optional[str] = None
    client_id: Optional[str] = None
    price: Optional[float] = None  # For observability/debugging
    type: Literal["order"] = "order"  # Type-safe event type
    # Correlation IDs for replay/audit (Correlation Backbone)
    order_id: Optional[str] = None
    decision_id: Optional[str] = None
    trace_id: Optional[str] = None
    # Phase 9: Trace Contract v1 - Policy governance
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None

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
            "strategy_id": self.strategy_id,
            "bot_id": self.bot_id,
            "client_id": self.client_id,
            "price": self.price,
            # Correlation IDs for replay/audit
            "order_id": self.order_id,
            "decision_id": self.decision_id,
            "trace_id": self.trace_id,
            # Phase 9: Trace Contract v1 - Policy governance
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
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
    strategy_id: Optional[str] = None
    bot_id: Optional[str] = None
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
            strategy_id=data.get("strategy_id"),
            bot_id=data.get("bot_id"),
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
    """Aktueller Risk-Status"""

    total_exposure: float = 0.0
    daily_pnl: float = 0.0
    open_positions: int = 0
    signals_blocked: int = 0
    signals_approved: int = 0
    circuit_breaker_active: bool = False
    positions: dict[str, float] = field(default_factory=dict)
    pending_orders: int = 0
    last_prices: dict[str, float] = field(default_factory=dict)

    # PR #XXX: Pre-Approval Exposure Reservation (Race Condition Fix)
    pending_exposure_usdt: float = 0.0
    pending_reservations: dict[str, float] = field(default_factory=dict)
