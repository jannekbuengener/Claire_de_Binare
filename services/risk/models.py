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

    # Rejection diagnostics
    source_service: Optional[str] = None
    reject_reason_code: Optional[str] = None
    reject_stage: Optional[str] = None
    causing_event_id: Optional[str] = None

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
            # Rejection diagnostics
            source_service=data.get("source_service"),
            reject_reason_code=data.get("reject_reason_code"),
            reject_stage=data.get("reject_stage"),
            causing_event_id=data.get("causing_event_id"),
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
    circuit_breaker_reason: Optional[str] = None
    circuit_breaker_triggered_at: Optional[int] = None
    circuit_breaker_consecutive_failures: int = 0
    circuit_breaker_failure_timestamps: list[int] = field(default_factory=list)
    initial_balance: float = 0.0
    equity: float = 0.0
    peak_equity: float = 0.0
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    daily_equity_start: float = 0.0
    trading_day: str = ""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    positions: dict[str, float] = field(default_factory=dict)
    avg_prices: dict[str, float] = field(default_factory=dict)
    bot_positions: dict[str, dict[str, float]] = field(default_factory=dict)
    bot_avg_prices: dict[str, dict[str, float]] = field(default_factory=dict)
    bot_realized_pnl: dict[str, float] = field(default_factory=dict)
    pending_orders: int = 0
    last_prices: dict[str, float] = field(default_factory=dict)
    shutdown_strategy_ids: list[str] = field(default_factory=list)
    shutdown_bot_ids: list[str] = field(default_factory=list)

    def initialize_equity(self, balance: float, trading_day: str) -> None:
        if self.initial_balance <= 0:
            self.initial_balance = balance
        if self.equity <= 0:
            self.equity = balance
        if self.daily_equity_start <= 0:
            self.daily_equity_start = balance
        if self.peak_equity <= 0:
            self.peak_equity = balance
        if not self.trading_day:
            self.trading_day = trading_day

    def update_equity(self) -> None:
        # PSM not wired; equity is a local mark-to-market fallback.
        unrealized = 0.0
        for symbol, qty in self.positions.items():
            price = self.last_prices.get(symbol)
            avg = self.avg_prices.get(symbol)
            if price is None or avg is None:
                continue
            unrealized += (price - avg) * qty

        self.unrealized_pnl = unrealized
        self.equity = self.initial_balance + self.realized_pnl + self.unrealized_pnl
        self.daily_pnl = self.equity - self.daily_equity_start

        if self.peak_equity <= 0:
            self.peak_equity = max(self.equity, 1.0)

        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        if self.peak_equity > 0:
            self.current_drawdown_pct = (self.peak_equity - self.equity) / self.peak_equity
        else:
            self.current_drawdown_pct = 0.0
        if self.current_drawdown_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = self.current_drawdown_pct

        self.total_exposure = sum(
            abs(qty) * self.last_prices.get(symbol, 0.0)
            for symbol, qty in self.positions.items()
        )
        self.open_positions = sum(
            1 for qty in self.positions.values() if abs(qty) > 1e-6
        )

    def reset_daily_metrics(self, trading_day: str) -> None:
        baseline = self.equity if self.equity > 0 else 1.0
        self.daily_equity_start = self.equity
        self.peak_equity = baseline
        self.current_drawdown_pct = 0.0
        self.max_drawdown_pct = 0.0
        self.daily_pnl = 0.0
        self.trading_day = trading_day

    @staticmethod
    def _apply_fill_to_book(
        positions: dict[str, float],
        avg_prices: dict[str, float],
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: float,
        price: float,
    ) -> float:
        signed_qty = quantity if side == "BUY" else -quantity
        if abs(signed_qty) < 1e-12:
            return 0.0

        current_qty = positions.get(symbol, 0.0)
        current_avg = avg_prices.get(symbol, price)
        realized = 0.0

        if abs(current_qty) < 1e-12:
            positions[symbol] = signed_qty
            avg_prices[symbol] = price
            return 0.0

        if current_qty * signed_qty > 0:
            new_qty = current_qty + signed_qty
            weighted_value = (abs(current_qty) * current_avg) + (abs(signed_qty) * price)
            avg_prices[symbol] = weighted_value / abs(new_qty)
            positions[symbol] = new_qty
            return 0.0

        closing_qty = min(abs(current_qty), abs(signed_qty))
        pnl_per_unit = price - current_avg
        realized = pnl_per_unit * closing_qty * (1 if current_qty > 0 else -1)
        new_qty = current_qty + signed_qty

        if abs(new_qty) < 1e-12:
            positions.pop(symbol, None)
            avg_prices.pop(symbol, None)
        else:
            positions[symbol] = new_qty
            if current_qty * new_qty < 0:
                avg_prices[symbol] = price

        return realized

    def apply_fill(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: float,
        price: float,
        bot_key: Optional[str] = None,
    ) -> float:
        realized = self._apply_fill_to_book(
            self.positions, self.avg_prices, symbol, side, quantity, price
        )
        self.realized_pnl += realized
        self.last_prices[symbol] = price

        if bot_key:
            bot_positions = self.bot_positions.setdefault(bot_key, {})
            bot_avg_prices = self.bot_avg_prices.setdefault(bot_key, {})
            bot_realized = self._apply_fill_to_book(
                bot_positions, bot_avg_prices, symbol, side, quantity, price
            )
            self.bot_realized_pnl[bot_key] = self.bot_realized_pnl.get(bot_key, 0.0) + bot_realized

        self.update_equity()
        return realized

    def record_execution_success(self) -> None:
        self.circuit_breaker_consecutive_failures = 0

    def record_execution_failure(
        self,
        now_ts: int,
        reason: str,
        max_consecutive: int,
        max_failures: int,
        window_sec: int,
    ) -> bool:
        if self.circuit_breaker_active:
            return True

        self.circuit_breaker_consecutive_failures += 1
        self.circuit_breaker_failure_timestamps.append(now_ts)
        if window_sec > 0:
            cutoff = now_ts - window_sec
            self.circuit_breaker_failure_timestamps = [
                ts for ts in self.circuit_breaker_failure_timestamps if ts >= cutoff
            ]

        if (
            self.circuit_breaker_consecutive_failures >= max_consecutive
            or len(self.circuit_breaker_failure_timestamps) >= max_failures
        ):
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = reason
            self.circuit_breaker_triggered_at = now_ts
            return True

        return False

    def reset_circuit_breaker(self) -> None:
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = None
        self.circuit_breaker_triggered_at = None
        self.circuit_breaker_consecutive_failures = 0
        self.circuit_breaker_failure_timestamps = []

    def to_dict(self) -> dict:
        return {
            "total_exposure": self.total_exposure,
            "daily_pnl": self.daily_pnl,
            "open_positions": self.open_positions,
            "signals_blocked": self.signals_blocked,
            "signals_approved": self.signals_approved,
            "circuit_breaker_active": self.circuit_breaker_active,
            "circuit_breaker_reason": self.circuit_breaker_reason,
            "circuit_breaker_triggered_at": self.circuit_breaker_triggered_at,
            "circuit_breaker_consecutive_failures": self.circuit_breaker_consecutive_failures,
            "circuit_breaker_failure_timestamps": list(self.circuit_breaker_failure_timestamps),
            "initial_balance": self.initial_balance,
            "equity": self.equity,
            "peak_equity": self.peak_equity,
            "current_drawdown_pct": self.current_drawdown_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "daily_equity_start": self.daily_equity_start,
            "trading_day": self.trading_day,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "positions": self.positions,
            "avg_prices": self.avg_prices,
            "bot_positions": self.bot_positions,
            "bot_avg_prices": self.bot_avg_prices,
            "bot_realized_pnl": self.bot_realized_pnl,
            "pending_orders": self.pending_orders,
            "last_prices": self.last_prices,
            "shutdown_strategy_ids": list(self.shutdown_strategy_ids),
            "shutdown_bot_ids": list(self.shutdown_bot_ids),
        }

    def apply_snapshot(self, data: dict) -> None:
        self.total_exposure = float(data.get("total_exposure", self.total_exposure))
        self.daily_pnl = float(data.get("daily_pnl", self.daily_pnl))
        self.open_positions = int(data.get("open_positions", self.open_positions))
        self.signals_blocked = int(data.get("signals_blocked", self.signals_blocked))
        self.signals_approved = int(
            data.get("signals_approved", self.signals_approved)
        )
        self.circuit_breaker_active = bool(
            data.get("circuit_breaker_active", self.circuit_breaker_active)
        )
        self.circuit_breaker_reason = data.get(
            "circuit_breaker_reason", self.circuit_breaker_reason
        )
        self.circuit_breaker_triggered_at = data.get(
            "circuit_breaker_triggered_at", self.circuit_breaker_triggered_at
        )
        self.circuit_breaker_consecutive_failures = int(
            data.get(
                "circuit_breaker_consecutive_failures",
                self.circuit_breaker_consecutive_failures,
            )
        )
        self.circuit_breaker_failure_timestamps = list(
            data.get(
                "circuit_breaker_failure_timestamps",
                self.circuit_breaker_failure_timestamps,
            )
        )
        self.initial_balance = float(data.get("initial_balance", self.initial_balance))
        self.equity = float(data.get("equity", self.equity))
        self.peak_equity = float(data.get("peak_equity", self.peak_equity))
        self.current_drawdown_pct = float(
            data.get("current_drawdown_pct", self.current_drawdown_pct)
        )
        self.max_drawdown_pct = float(
            data.get("max_drawdown_pct", self.max_drawdown_pct)
        )
        self.daily_equity_start = float(
            data.get("daily_equity_start", self.daily_equity_start)
        )
        self.trading_day = data.get("trading_day", self.trading_day)
        self.realized_pnl = float(data.get("realized_pnl", self.realized_pnl))
        self.unrealized_pnl = float(data.get("unrealized_pnl", self.unrealized_pnl))
        self.positions = dict(data.get("positions", self.positions))
        self.avg_prices = dict(data.get("avg_prices", self.avg_prices))
        self.bot_positions = dict(data.get("bot_positions", self.bot_positions))
        self.bot_avg_prices = dict(data.get("bot_avg_prices", self.bot_avg_prices))
        self.bot_realized_pnl = dict(data.get("bot_realized_pnl", self.bot_realized_pnl))
        self.pending_orders = int(data.get("pending_orders", self.pending_orders))
        self.last_prices = dict(data.get("last_prices", self.last_prices))
        self.shutdown_strategy_ids = list(
            data.get("shutdown_strategy_ids", self.shutdown_strategy_ids)
        )
        self.shutdown_bot_ids = list(data.get("shutdown_bot_ids", self.shutdown_bot_ids))
