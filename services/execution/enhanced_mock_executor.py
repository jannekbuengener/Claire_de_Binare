"""
Enhanced Mock Executor for Paper Trading v2.0
Claire de Binare Trading Bot

Features:
- Realistic slippage simulation (0.05-0.3%)
- Trading fees (0.1% taker, 0.05% maker)
- Partial fills (configurable probability)
- Order types: Market, Limit, Stop
- Multi-asset support (BTC, ETH, SOL, +7 more)
- Prometheus metrics
- Configurable parameters
- Realistic rejection scenarios
"""

import uuid
import random
import time
import logging
from datetime import datetime
from typing import Optional, Dict
from enum import Enum

try:
    from .models import Order, ExecutionResult, OrderStatus
    from .paper_trading_config import paper_config
    from .paper_trading_metrics import MetricsCollector
except ImportError:
    from models import Order, ExecutionResult, OrderStatus
    from paper_trading_config import paper_config
    from paper_trading_metrics import MetricsCollector


class OrderType(Enum):
    """Order types supported"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class RejectionReason(Enum):
    """Order rejection reasons"""
    INSUFFICIENT_BALANCE = "Insufficient balance"
    INVALID_PRICE = "Invalid price"
    INSUFFICIENT_LIQUIDITY = "Insufficient liquidity"
    PRICE_OUT_OF_RANGE = "Price out of acceptable range"
    MARKET_CLOSED = "Market closed"
    SYMBOL_NOT_SUPPORTED = "Symbol not supported"
    QUANTITY_TOO_SMALL = "Quantity below minimum"
    QUANTITY_TOO_LARGE = "Quantity above maximum"


class EnhancedMockExecutor:
    """
    Production-ready paper trading executor with realistic market simulation

    Version 2.0: Enhanced with fees, partial fills, metrics
    """

    def __init__(
        self,
        config: Optional[object] = None,
        enable_metrics: bool = True
    ):
        """
        Initialize Enhanced Mock Executor

        Args:
            config: Paper trading configuration (uses global if None)
            enable_metrics: Enable Prometheus metrics collection
        """
        self.config = config or paper_config
        self.enable_metrics = enable_metrics
        self.logger = logging.getLogger(__name__)

        # Order storage
        self.orders: Dict[str, ExecutionResult] = {}

        # Statistics tracking
        self.stats = {
            "total_orders": 0,
            "filled_orders": 0,
            "partial_fills": 0,
            "rejected_orders": 0,
            "total_volume_usdt": 0.0,
            "total_fees_usdt": 0.0,
        }

        # Validate config
        try:
            self.config.validate()
            self.logger.info("Enhanced Mock Executor initialized with v2.0 simulation")
        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            raise

    def execute_order(self, order: Order) -> ExecutionResult:
        """
        Execute order with realistic simulation

        Args:
            order: Order to execute

        Returns:
            ExecutionResult with simulated execution
        """
        start_time = time.time()
        self.stats["total_orders"] += 1

        # Simulate execution latency
        self._simulate_latency()

        # Generate IDs
        order_id = f"PAPER_{uuid.uuid4().hex[:12]}"
        client_id = order.client_id or f"CDB_{uuid.uuid4().hex[:8]}"

        # Validate order
        rejection = self._validate_order(order)
        if rejection:
            result = self._create_rejected_result(
                order, order_id, client_id, rejection
            )
            self._record_metrics(order, result, time.time() - start_time)
            return result

        # Determine if order succeeds
        if random.random() >= self.config.success_rate:
            # Random rejection
            rejection = random.choice(list(RejectionReason))
            result = self._create_rejected_result(
                order, order_id, client_id, rejection.value
            )
            self._record_metrics(order, result, time.time() - start_time)
            return result

        # Execute order (success path)
        result = self._execute_successful_order(order, order_id, client_id)

        # Record execution time
        execution_time = time.time() - start_time
        self._record_metrics(order, result, execution_time)

        # Store order
        self.orders[order_id] = result

        return result

    def _validate_order(self, order: Order) -> Optional[str]:
        """
        Validate order before execution

        Returns:
            Rejection reason if invalid, None if valid
        """
        # Check symbol support
        if order.symbol not in self.config.asset_prices:
            return RejectionReason.SYMBOL_NOT_SUPPORTED.value

        # Check quantity
        if order.quantity <= 0:
            return RejectionReason.QUANTITY_TOO_SMALL.value

        if order.quantity > 1000000:  # Arbitrary large limit
            return RejectionReason.QUANTITY_TOO_LARGE.value

        # Check price (if limit order)
        if hasattr(order, 'price') and order.price is not None:
            current_price = self._get_current_price(order.symbol)
            # Reject if limit price is >10% away from current
            if abs(order.price - current_price) / current_price > 0.10:
                return RejectionReason.PRICE_OUT_OF_RANGE.value

        return None

    def _execute_successful_order(
        self,
        order: Order,
        order_id: str,
        client_id: str
    ) -> ExecutionResult:
        """Execute order successfully"""

        # Get current price
        base_price = self._get_current_price(order.symbol)

        # Calculate slippage
        slippage_pct = self._calculate_slippage(order.quantity)
        slippage_decimal = slippage_pct / 100.0

        # Apply slippage
        if order.side.upper() == "BUY":
            execution_price = base_price * (1 + slippage_decimal)
        else:
            execution_price = base_price * (1 - slippage_decimal)

        # Determine fill (full or partial)
        is_partial = random.random() < self.config.partial_fill_probability

        if is_partial:
            fill_ratio = random.uniform(
                self.config.min_fill_ratio,
                self.config.max_fill_ratio
            )
            filled_quantity = order.quantity * fill_ratio
            status = OrderStatus.PARTIAL.value
            self.stats["partial_fills"] += 1
        else:
            filled_quantity = order.quantity
            status = OrderStatus.FILLED.value
            self.stats["filled_orders"] += 1

        # Calculate fees
        # Market orders = taker fee, Limit orders = maker fee (simplified)
        order_type = getattr(order, 'order_type', OrderType.MARKET.value)
        if order_type == OrderType.MARKET.value:
            fee_pct = self.config.taker_fee_pct
            fee_type = "TAKER"
        else:
            fee_pct = self.config.maker_fee_pct
            fee_type = "MAKER"

        fee_decimal = fee_pct / 100.0
        fee_amount = filled_quantity * execution_price * fee_decimal

        # Update stats
        volume = filled_quantity * execution_price
        self.stats["total_volume_usdt"] += volume
        self.stats["total_fees_usdt"] += fee_amount

        # Round execution price
        execution_price = round(execution_price, 8)

        result = ExecutionResult(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=filled_quantity,
            status=status,
            price=execution_price,
            client_id=client_id,
            error_message=None,
            timestamp=datetime.utcnow().isoformat(),
            # Additional metadata
            metadata={
                "slippage_pct": slippage_pct,
                "fee_amount": fee_amount,
                "fee_type": fee_type,
                "fee_pct": fee_pct,
                "base_price": base_price,
                "is_partial": is_partial,
            }
        )

        return result

    def _create_rejected_result(
        self,
        order: Order,
        order_id: str,
        client_id: str,
        reason: str
    ) -> ExecutionResult:
        """Create rejected order result"""
        self.stats["rejected_orders"] += 1

        return ExecutionResult(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=0.0,
            status=OrderStatus.REJECTED.value,
            price=None,
            client_id=client_id,
            error_message=f"Paper trading rejection: {reason}",
            timestamp=datetime.utcnow().isoformat(),
            metadata={"rejection_reason": reason}
        )

    def _get_current_price(self, symbol: str) -> float:
        """
        Get current simulated price for symbol

        Args:
            symbol: Trading pair

        Returns:
            Simulated current price
        """
        base_price = self.config.get_base_price(symbol)

        # Add realistic price variance (-0.5% to +0.5%)
        variance = random.uniform(-0.005, 0.005)
        current_price = base_price * (1 + variance)

        return current_price

    def _calculate_slippage(self, quantity: float) -> float:
        """
        Calculate realistic slippage based on order size

        Args:
            quantity: Order size

        Returns:
            Slippage percentage (e.g., 0.15 = 0.15%)
        """
        # Base slippage
        base_slippage = random.uniform(
            self.config.min_slippage_pct,
            self.config.max_slippage_pct
        )

        # Price impact (larger orders = more slippage)
        # Scale up to 2x for very large orders
        size_factor = min(1.0 + (quantity / 100.0), 2.0)

        total_slippage = base_slippage * size_factor

        # Cap at 1% maximum
        return min(total_slippage, 1.0)

    def _simulate_latency(self):
        """Simulate realistic execution latency"""
        latency_ms = random.randint(
            self.config.min_latency_ms,
            self.config.max_latency_ms
        )
        time.sleep(latency_ms / 1000.0)

    def _record_metrics(
        self,
        order: Order,
        result: ExecutionResult,
        execution_time: float
    ):
        """Record Prometheus metrics"""
        if not self.enable_metrics:
            return

        try:
            # Extract metadata
            metadata = result.metadata or {}
            slippage_pct = metadata.get("slippage_pct", 0.0)
            fee_amount = metadata.get("fee_amount", 0.0)
            fee_type = metadata.get("fee_type", "UNKNOWN")

            # Record execution
            MetricsCollector.record_order_execution(
                symbol=order.symbol,
                side=order.side,
                status=result.status,
                filled_quantity=result.filled_quantity,
                total_quantity=result.quantity,
                execution_price=result.price or 0.0,
                latency_seconds=execution_time,
                slippage_pct=slippage_pct,
                fee_amount=fee_amount,
                fee_type=fee_type
            )
        except Exception as e:
            self.logger.warning(f"Failed to record metrics: {e}")

    def get_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        """Get status of a paper trading order"""
        return self.orders.get(order_id)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a paper trading order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            # Only cancel if not already filled
            if order.status not in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value]:
                order.status = OrderStatus.CANCELLED.value
                self.logger.info(f"Paper order {order_id} cancelled")
                return True
        return False

    def get_statistics(self) -> Dict:
        """Get executor statistics"""
        fill_rate = (
            self.stats["filled_orders"] / self.stats["total_orders"]
            if self.stats["total_orders"] > 0
            else 0.0
        )

        return {
            **self.stats,
            "fill_rate": fill_rate,
            "average_fee_pct": (
                (self.stats["total_fees_usdt"] / self.stats["total_volume_usdt"] * 100)
                if self.stats["total_volume_usdt"] > 0
                else 0.0
            )
        }

    def health_check(self) -> bool:
        """Health check (always healthy for mock)"""
        return True
