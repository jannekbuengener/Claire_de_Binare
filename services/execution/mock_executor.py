"""
Mock Executor for Paper Trading
Claire de Binare Trading Bot

Features:
- Realistic latency simulation (50-200ms)
- Market slippage (0.01-0.05%)
- Success rate simulation (95%)
- Price impact modeling
- Optional resting-order mode for kill-cancel drills (#4185)
"""

from __future__ import annotations

import time
from typing import Optional

from core.utils.clock import utcnow
from core.utils.seed import Seed, SeedManager

try:
    from .models import Order, ExecutionResult, OrderStatus
except ImportError:
    from models import Order, ExecutionResult, OrderStatus


class MockExecutor:
    """Simulates order execution without real API calls"""

    supports_reduce_only = True

    def __init__(
        self,
        success_rate: float = 0.95,
        min_latency_ms: int = 50,
        max_latency_ms: int = 200,
        base_slippage_pct: float = 0.02,
        seed_manager: Optional[SeedManager] = None,
        resting_orders: bool = False,
        cancel_behavior: str = "confirm",
    ):
        """
        Initialize Mock Executor

        Args:
            success_rate: Probability of order success (0.0-1.0)
            min_latency_ms: Minimum execution latency in milliseconds
            max_latency_ms: Maximum execution latency in milliseconds
            base_slippage_pct: Base slippage percentage (0.02 = 0.02%)
            resting_orders: When True, successful submits stay PENDING/SUBMITTED
                instead of immediately FILLED (kill-cancel drills).
            cancel_behavior: confirm | reject | error | accepted_unconfirmed | malformed
        """
        self.orders = {}
        self.success_rate = success_rate
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.base_slippage_pct = base_slippage_pct
        self._seed_manager = seed_manager or SeedManager(Seed.get())
        self.resting_orders = resting_orders
        self.cancel_behavior = cancel_behavior
        # Per-order cancel overrides: order_id -> behavior
        self.cancel_behavior_by_id: dict[str, str] = {}

    def execute_order(self, order: Order) -> ExecutionResult:
        """
        Simulate order execution with realistic latency and slippage

        Returns ExecutionResult with simulated data
        """
        # Simulate execution latency
        latency_ms = self._seed_manager.random_int(
            self.min_latency_ms, self.max_latency_ms
        )
        time.sleep(latency_ms / 1000.0)  # Convert ms to seconds

        # Prefer caller-provided order_id so registry can track pre-submit IDs
        if order.order_id:
            order_id = order.order_id
            order_suffix = order_id[-8:] if len(order_id) >= 8 else order_id
        else:
            order_suffix = f"{self._seed_manager.random_int(0, 99999999):08d}"
            order_id = f"MOCK_{order_suffix}"
        client_id = order.client_id or f"CDB_{order_suffix}"

        # Simulate success/failure
        success = self._seed_manager.random_float() < self.success_rate

        if success:
            base_price = self._simulate_price(order.symbol)
            slippage = self._simulate_slippage(order.quantity)

            if order.side.lower() == "buy":
                execution_price = base_price * (1 + slippage)
            else:
                execution_price = base_price * (1 - slippage)

            if self.resting_orders:
                result = ExecutionResult(
                    order_id=order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    filled_quantity=0.0,
                    status=OrderStatus.SUBMITTED.value,
                    price=round(execution_price, 2),
                    client_id=client_id,
                    error_message=None,
                    timestamp=utcnow().isoformat(),
                    fill_id=None,
                )
            else:
                filled_quantity = order.quantity
                result = ExecutionResult(
                    order_id=order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    filled_quantity=filled_quantity,
                    status=OrderStatus.FILLED.value,
                    price=round(execution_price, 2),
                    client_id=client_id,
                    error_message=None,
                    timestamp=utcnow().isoformat(),
                    fill_id=order_id,
                )

            self.orders[order_id] = result
            return result

        result = ExecutionResult(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=0.0,
            status=OrderStatus.REJECTED.value,
            price=None,
            client_id=client_id,
            error_message="Mock rejection: Insufficient liquidity",
            timestamp=utcnow().isoformat(),
        )
        return result

    def place_resting_order(
        self,
        *,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        status: str = "PENDING",
        filled_quantity: float = 0.0,
        price: float | None = None,
    ) -> ExecutionResult:
        """Test/drill helper: inject a resting open order without filling."""
        if status not in {
            OrderStatus.PENDING.value,
            OrderStatus.SUBMITTED.value,
            OrderStatus.PARTIALLY_FILLED.value,
        }:
            raise ValueError(f"resting status must be open, got {status}")
        result = ExecutionResult(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            filled_quantity=filled_quantity,
            status=status,
            price=price,
            client_id=f"CDB_{order_id[-8:]}",
            error_message=None,
            timestamp=utcnow().isoformat(),
            fill_id=None,
        )
        self.orders[order_id] = result
        return result

    def force_fill(
        self, order_id: str, *, filled_quantity: float | None = None
    ) -> ExecutionResult:
        """Synthetic late fill used to prove FILL_AFTER_KILL_ACTIVATION."""
        existing = self.orders.get(order_id)
        if existing is None:
            raise KeyError(order_id)
        qty = filled_quantity if filled_quantity is not None else existing.quantity
        existing.status = OrderStatus.FILLED.value
        existing.filled_quantity = qty
        existing.fill_id = order_id
        existing.timestamp = utcnow().isoformat()
        return existing

    def _simulate_price(self, symbol: str) -> float:
        if "BTC" in symbol:
            base_price = 50000
        elif "ETH" in symbol:
            base_price = 3000
        else:
            base_price = 100
        variance = self._seed_manager.random_uniform(-0.001, 0.001)
        price = base_price * (1 + variance)
        return round(price, 2)

    def _simulate_slippage(self, quantity: float) -> float:
        base = self.base_slippage_pct / 100.0
        size_factor = min(quantity / 10.0, 2.0)
        random_factor = self._seed_manager.random_uniform(0.5, 1.5)
        total_slippage = base * size_factor * random_factor
        return min(total_slippage, 0.001)

    def get_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        """Get status of a mock order"""
        return self.orders.get(order_id)

    def cancel_order(self, order_id: str) -> bool:
        """Legacy bool cancel.

        Only cancels truly open orders. Already FILLED/REJECTED/CANCELLED return
        False and are not rewritten (no FILLED→CANCELLED).
        """
        existing = self.orders.get(order_id)
        if existing is None:
            return False
        if existing.status not in {
            OrderStatus.PENDING.value,
            OrderStatus.SUBMITTED.value,
            OrderStatus.PARTIALLY_FILLED.value,
        }:
            return False
        behavior = self.cancel_behavior_by_id.get(order_id, self.cancel_behavior)
        if behavior == "reject":
            return False
        if behavior == "error":
            raise RuntimeError(f"mock cancel error for {order_id}")
        if behavior in {"accepted_unconfirmed", "malformed"}:
            # Bool API cannot express accepted-but-unconfirmed; leave open and True
            # would be dishonest confirmation. Return False (= not confirmed).
            return False
        existing.status = OrderStatus.CANCELLED.value
        existing.timestamp = utcnow().isoformat()
        return True
