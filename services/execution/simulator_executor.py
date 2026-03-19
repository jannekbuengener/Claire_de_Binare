"""Explicit market-like simulator executor for safe mock execution paths.

This executor reuses the existing ExecutionSimulator model but keeps the
published execution contract conservative: by default it emits only FILLED or
REJECTED results so it can plug into the current execution service without
looking like a live exchange path.
"""

from __future__ import annotations

import logging
from typing import Mapping, Optional

from core.utils.clock import utcnow

try:
    from .models import ExecutionResult, Order, OrderStatus
    from .simulator import ExecutionSimulator, load_execution_config
except ImportError:
    from models import ExecutionResult, Order, OrderStatus
    from simulator import ExecutionSimulator, load_execution_config

logger = logging.getLogger(__name__)

_DEFAULT_REFERENCE_PRICES = {
    "BTC": 50000.0,
    "ETH": 3000.0,
    "SOL": 100.0,
}
_FALLBACK_REFERENCE_PRICE = 100.0


class SimulatorExecutor:
    """Market-like execution simulator behind an explicit non-live mode."""

    def __init__(
        self,
        *,
        order_book_depth: float = 1_000_000.0,
        volatility: float = 0.02,
        reference_prices: Optional[Mapping[str, float]] = None,
        reject_on_partial_fill: bool = True,
    ) -> None:
        if order_book_depth <= 0:
            raise ValueError("order_book_depth must be positive")
        if volatility < 0:
            raise ValueError("volatility must be non-negative")

        self.order_book_depth = float(order_book_depth)
        self.volatility = float(volatility)
        self.reject_on_partial_fill = reject_on_partial_fill
        self.reference_prices = {
            key.upper(): float(value)
            for key, value in (reference_prices or _DEFAULT_REFERENCE_PRICES).items()
        }
        self._simulator = ExecutionSimulator(load_execution_config())
        self._sequence = 0

    def execute_order(self, order: Order) -> ExecutionResult:
        order_id = self._next_order_id()
        client_id = order.client_id or f"CDB_SIM_{self._sequence:08d}"
        reference_price = self._resolve_reference_price(order.symbol)

        sim_result = self._simulator.simulate_market_order(
            side=order.side,
            size=order.quantity,
            current_price=reference_price,
            order_book_depth=self.order_book_depth,
            volatility=self.volatility,
        )

        if sim_result.filled_size <= 0 or sim_result.fill_ratio <= 0:
            return self._rejected_result(
                order=order,
                order_id=order_id,
                client_id=client_id,
                reason="Simulated reject: no executable modeled depth",
            )

        if sim_result.partial_fill and self.reject_on_partial_fill:
            return self._rejected_result(
                order=order,
                order_id=order_id,
                client_id=client_id,
                reason=(
                    "Simulated reject: modeled depth supports only "
                    f"{sim_result.fill_ratio:.2%} of requested size"
                ),
            )

        status = (
            OrderStatus.PARTIALLY_FILLED.value
            if sim_result.partial_fill
            else OrderStatus.FILLED.value
        )
        result = ExecutionResult(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=round(float(sim_result.filled_size), 8),
            status=status,
            strategy_id=order.strategy_id,
            bot_id=order.bot_id,
            client_id=client_id,
            price=round(float(sim_result.avg_fill_price), 2),
            error_message=None,
            timestamp=utcnow().isoformat(),
            fill_id=order_id,
        )

        logger.info(
            "SIMULATED execution: %s %s qty=%.8f filled=%.8f price=%.2f "
            "slippage=%.2fbps partial=%s",
            order.symbol,
            order.side,
            order.quantity,
            result.filled_quantity,
            result.price or 0.0,
            sim_result.slippage_bps,
            sim_result.partial_fill,
        )
        return result

    def _next_order_id(self) -> str:
        self._sequence += 1
        return f"SIM_{self._sequence:08d}"

    def _resolve_reference_price(self, symbol: str) -> float:
        symbol_upper = symbol.upper()
        for prefix, price in self.reference_prices.items():
            if prefix in symbol_upper:
                return price
        return _FALLBACK_REFERENCE_PRICE

    def _rejected_result(
        self,
        *,
        order: Order,
        order_id: str,
        client_id: str,
        reason: str,
    ) -> ExecutionResult:
        logger.warning(
            "SIMULATED reject: %s %s qty=%.8f reason=%s",
            order.symbol,
            order.side,
            order.quantity,
            reason,
        )
        return ExecutionResult(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=0.0,
            status=OrderStatus.REJECTED.value,
            strategy_id=order.strategy_id,
            bot_id=order.bot_id,
            client_id=client_id,
            price=None,
            error_message=reason,
            timestamp=utcnow().isoformat(),
            fill_id=None,
        )
