"""
Mock Executor for Paper Trading
Claire de Binare Trading Bot

Features:
- Realistic latency simulation (50-200ms)
- Market slippage (0.01-0.05%)
- Success rate simulation (95%)
- Price impact modeling
"""

import uuid
import random
import time
from datetime import datetime
from typing import Optional

try:
    from .models import Order, ExecutionResult, OrderStatus
except ImportError:
    from models import Order, ExecutionResult, OrderStatus


class MockExecutor:
    """Simulates order execution without real API calls"""

    def __init__(
        self,
        success_rate: float = 0.95,
        min_latency_ms: int = 50,
        max_latency_ms: int = 200,
        base_slippage_pct: float = 0.02,
    ):
        """
        Initialize Mock Executor

        Args:
            success_rate: Probability of order success (0.0-1.0)
            min_latency_ms: Minimum execution latency in milliseconds
            max_latency_ms: Maximum execution latency in milliseconds
            base_slippage_pct: Base slippage percentage (0.02 = 0.02%)
        """
        self.orders = {}
        self.success_rate = success_rate
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.base_slippage_pct = base_slippage_pct

    def execute_order(self, order: Order) -> ExecutionResult:
        """
        Simulate order execution with realistic latency and slippage

        Returns ExecutionResult with simulated data
        """
        # Simulate execution latency
        latency_ms = random.randint(self.min_latency_ms, self.max_latency_ms)
        time.sleep(latency_ms / 1000.0)  # Convert ms to seconds

        # Generate order ID
        order_id = f"MOCK_{uuid.uuid4().hex[:8]}"
        client_id = order.client_id or f"CDB_{uuid.uuid4().hex[:8]}"

        # Simulate success/failure
        success = random.random() < self.success_rate

        if success:
            # Simulate successful execution with slippage
            # Use signal price from order, or fallback to simulation if not provided
            base_price = (
                order.price
                if order.price is not None
                else self._simulate_price(order.symbol)
            )
            slippage = self._simulate_slippage(order.quantity)

            # Apply slippage based on order side
            if order.side.lower() == "buy":
                execution_price = base_price * (1 + slippage)  # Buy higher
            else:
                execution_price = base_price * (1 - slippage)  # Sell lower

            filled_quantity = order.quantity

            result = ExecutionResult(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=filled_quantity,
                status=OrderStatus.FILLED.value,
                price=round(execution_price, 8),  # 8 decimals for crypto precision
                client_id=client_id,
                error_message=None,
                timestamp=datetime.utcnow().isoformat(),
            )

            # Store order
            self.orders[order_id] = result

            return result

        else:
            # Simulate rejection
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
                timestamp=datetime.utcnow().isoformat(),
            )

            return result

    def _simulate_price(self, symbol: str) -> float:
        """
        Simulate realistic price based on symbol
        """
        # Simple price simulation
        if "BTC" in symbol:
            base_price = 50000
        elif "ETH" in symbol:
            base_price = 3000
        else:
            base_price = 100

        # Add random variance (-0.1% to +0.1%)
        variance = random.uniform(-0.001, 0.001)
        price = base_price * (1 + variance)

        return round(price, 2)

    def _simulate_slippage(self, quantity: float) -> float:
        """
        Simulate market slippage based on order size

        Larger orders experience more slippage due to price impact

        Args:
            quantity: Order size

        Returns:
            Slippage as decimal (e.g., 0.0002 = 0.02%)
        """
        # Base slippage (e.g., 0.02% = 0.0002)
        base = self.base_slippage_pct / 100.0

        # Price impact increases with order size
        # Larger orders move the market more
        size_factor = min(quantity / 10.0, 2.0)  # Cap at 2x

        # Random component (market conditions)
        random_factor = random.uniform(0.5, 1.5)

        total_slippage = base * size_factor * random_factor

        # Cap maximum slippage at 0.1% (reasonable for liquid markets)
        return min(total_slippage, 0.001)

    def get_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        """Get status of a mock order"""
        return self.orders.get(order_id)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a mock order (always succeeds)"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED.value
            return True
        return False
