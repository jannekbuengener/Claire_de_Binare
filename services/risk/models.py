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
        }


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
    strategy_id: str
    bot_id: Optional[str] = None
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
            "strategy_id": self.strategy_id,
            "bot_id": self.bot_id,
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

    # Equity & Drawdown Tracking (#230)
    equity: float = 0.0
    peak_equity: float = 0.0
    initial_equity: float = 0.0
    equity_start_date: str = ""
    max_drawdown_pct: float = 0.0

    # Circuit Breaker State (#230)
    circuit_breaker_triggered_at: int = 0
    circuit_breaker_reason: str = ""
    last_event_timestamp: int = 0  # For deterministic cooldown reset (#226)
    failure_history: list[dict] = field(default_factory=list)
    consecutive_failures: int = 0
    shutdown_strategy_ids: list[str] = field(default_factory=list)
    shutdown_bot_ids: list[str] = field(default_factory=list)

    # Position tracking for P&L
    _position_entries: dict[str, list[dict]] = field(default_factory=dict)

    def initialize_equity(self, equity: float, date: str) -> None:
        """Initialize equity tracking with starting balance and date."""
        self.equity = equity
        self.peak_equity = equity
        self.initial_equity = equity
        self.equity_start_date = date

    def update_equity(self) -> None:
        """Update peak equity if current equity exceeds it, and update max drawdown."""
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        # Always update max_drawdown_pct if current drawdown is worse
        current_dd = self.current_drawdown_pct
        if current_dd > self.max_drawdown_pct:
            self.max_drawdown_pct = current_dd

    @property
    def current_drawdown_pct(self) -> float:
        """Calculate current drawdown percentage from peak."""
        if self.peak_equity <= 0.0:
            return 1.0
        return (self.peak_equity - self.equity) / self.peak_equity

    def apply_fill(self, symbol: str, side: str, quantity: float, price: float) -> None:
        """Apply a filled order to position tracking and update equity."""
        # Track position entries for FIFO P&L calculation
        if symbol not in self._position_entries:
            self._position_entries[symbol] = []

        if side == "BUY":
            # Add entry to position
            self._position_entries[symbol].append({
                "quantity": quantity,
                "price": price
            })
            # Update positions dict (net position)
            self.positions[symbol] = self.positions.get(symbol, 0.0) + quantity

        elif side == "SELL":
            # Calculate P&L using FIFO
            remaining = quantity
            realized_pnl = 0.0

            while remaining > 0 and self._position_entries[symbol]:
                entry = self._position_entries[symbol][0]
                entry_qty = entry["quantity"]
                entry_price = entry["price"]

                if entry_qty <= remaining:
                    # Close entire entry
                    realized_pnl += entry_qty * (price - entry_price)
                    remaining -= entry_qty
                    self._position_entries[symbol].pop(0)
                else:
                    # Partial close
                    realized_pnl += remaining * (price - entry_price)
                    entry["quantity"] -= remaining
                    remaining = 0

            # Update equity with realized P&L
            self.equity += realized_pnl

            # Update max drawdown if needed
            current_dd = self.current_drawdown_pct
            if current_dd > self.max_drawdown_pct:
                self.max_drawdown_pct = current_dd

            # Update positions dict (net position)
            self.positions[symbol] = self.positions.get(symbol, 0.0) - quantity
            if abs(self.positions[symbol]) < 1e-8:
                del self.positions[symbol]
                if not self._position_entries[symbol]:
                    del self._position_entries[symbol]

        # Update peak equity if applicable
        self.update_equity()

    def record_execution_failure(
        self,
        timestamp: int,
        reason: str,
        max_consecutive: int = 3,
        max_failures: int = 10,
        window_sec: int = 3600,
    ) -> bool:
        """
        Record an execution failure and check if circuit breaker should trigger.

        Returns True if circuit breaker was triggered, False otherwise.
        """
        # Add failure to history
        self.failure_history.append({
            "timestamp": timestamp,
            "reason": reason
        })

        # Increment consecutive failures
        self.consecutive_failures += 1

        # Check consecutive failures threshold
        if self.consecutive_failures >= max_consecutive:
            self.circuit_breaker_active = True
            self.circuit_breaker_triggered_at = timestamp
            self.circuit_breaker_reason = reason
            return True

        # Check total failures in time window
        cutoff_time = timestamp - window_sec
        recent_failures = [
            f for f in self.failure_history
            if f["timestamp"] >= cutoff_time
        ]

        if len(recent_failures) >= max_failures:
            self.circuit_breaker_active = True
            self.circuit_breaker_triggered_at = timestamp
            self.circuit_breaker_reason = reason
            return True

        return False

    def record_execution_success(self) -> None:
        """Record a successful execution, resetting consecutive failure counter."""
        self.consecutive_failures = 0

    def to_dict(self) -> dict:
        """Convert RiskState to a dictionary for serialization."""
        return {
            "total_exposure": self.total_exposure,
            "daily_pnl": self.daily_pnl,
            "open_positions": self.open_positions,
            "signals_blocked": self.signals_blocked,
            "signals_approved": self.signals_approved,
            "circuit_breaker_active": self.circuit_breaker_active,
            "positions": dict(self.positions),
            "pending_orders": self.pending_orders,
            "last_prices": dict(self.last_prices),
            "equity": self.equity,
            "peak_equity": self.peak_equity,
            "initial_equity": self.initial_equity,
            "equity_start_date": self.equity_start_date,
            "max_drawdown_pct": self.max_drawdown_pct,
            "circuit_breaker_triggered_at": self.circuit_breaker_triggered_at,
            "circuit_breaker_reason": self.circuit_breaker_reason,
            "last_event_timestamp": self.last_event_timestamp,
            "failure_history": list(self.failure_history),
            "consecutive_failures": self.consecutive_failures,
            "shutdown_strategy_ids": list(self.shutdown_strategy_ids),
            "shutdown_bot_ids": list(self.shutdown_bot_ids),
        }

    def apply_snapshot(self, snapshot: dict) -> None:
        """Restore RiskState from a dictionary snapshot with defensive type conversion."""
        # Basic fields
        self.total_exposure = float(snapshot.get("total_exposure", 0.0))
        self.daily_pnl = float(snapshot.get("daily_pnl", 0.0))
        self.open_positions = int(snapshot.get("open_positions", 0))
        self.signals_blocked = int(snapshot.get("signals_blocked", 0))
        self.signals_approved = int(snapshot.get("signals_approved", 0))
        self.circuit_breaker_active = bool(snapshot.get("circuit_breaker_active", False))
        self.pending_orders = int(snapshot.get("pending_orders", 0))

        # Dictionary fields (defensive conversion)
        positions_raw = snapshot.get("positions", {})
        self.positions = dict(positions_raw) if positions_raw else {}

        last_prices_raw = snapshot.get("last_prices", {})
        self.last_prices = dict(last_prices_raw) if last_prices_raw else {}

        # Equity tracking
        self.equity = float(snapshot.get("equity", 0.0))
        self.peak_equity = float(snapshot.get("peak_equity", 0.0))
        self.initial_equity = float(snapshot.get("initial_equity", 0.0))
        self.equity_start_date = str(snapshot.get("equity_start_date", ""))
        self.max_drawdown_pct = float(snapshot.get("max_drawdown_pct", 0.0))

        # Circuit breaker state
        self.circuit_breaker_triggered_at = int(snapshot.get("circuit_breaker_triggered_at", 0))
        self.circuit_breaker_reason = str(snapshot.get("circuit_breaker_reason", ""))
        self.last_event_timestamp = int(snapshot.get("last_event_timestamp", 0))
        self.consecutive_failures = int(snapshot.get("consecutive_failures", 0))

        # List fields (defensive conversion)
        failure_history_raw = snapshot.get("failure_history", [])
        self.failure_history = list(failure_history_raw) if failure_history_raw else []

        shutdown_strategy_ids_raw = snapshot.get("shutdown_strategy_ids", [])
        self.shutdown_strategy_ids = list(shutdown_strategy_ids_raw) if shutdown_strategy_ids_raw else []

        shutdown_bot_ids_raw = snapshot.get("shutdown_bot_ids", [])
        self.shutdown_bot_ids = list(shutdown_bot_ids_raw) if shutdown_bot_ids_raw else []
