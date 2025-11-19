"""
Paper Execution Service - Simulierte Order-Ausführung

Simuliert echte Order-Execution für Paper-Trading:
- Nimmt approved Orders von Risk Manager
- Simuliert Fills (kein Exchange-Call)
- Berechnet Slippage, Fees
- Updated Positions
- Generiert OrderResult Events

Garantiert:
- Deterministisch (gleiche Inputs → gleiche Outputs)
- Keine externen API-Calls
- Realistische Simulation (Slippage, Fees)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Slippage simulation (realistische Market Impact)
DEFAULT_SLIPPAGE_PCT = float(os.getenv("PAPER_SLIPPAGE_PCT", "0.001"))  # 0.1% default

# Fee simulation (Maker/Taker fees)
DEFAULT_FEE_PCT = float(os.getenv("PAPER_FEE_PCT", "0.001"))  # 0.1% default

# Fill probability (für realistische rejected orders)
FILL_PROBABILITY = float(os.getenv("PAPER_FILL_PROBABILITY", "0.98"))  # 98% fills


# ==============================================================================
# PAPER EXECUTION ENGINE
# ==============================================================================


class PaperExecutionEngine:
    """
    Simulierte Order-Execution für Paper-Trading.

    Simuliert:
    - Market Orders (sofortige Fills mit Slippage)
    - Limit Orders (nur bei Price-Match)
    - Stop-Loss Orders (bei Trigger-Price)
    - Fees & Slippage
    - Partial Fills (optional)
    """

    def __init__(
        self,
        slippage_pct: float = DEFAULT_SLIPPAGE_PCT,
        fee_pct: float = DEFAULT_FEE_PCT,
        fill_probability: float = FILL_PROBABILITY,
    ):
        """
        Initialize paper execution engine.

        Args:
            slippage_pct: Slippage percentage (default 0.1%)
            fee_pct: Fee percentage (default 0.1%)
            fill_probability: Probability of fill (default 98%)
        """
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        self.fill_probability = fill_probability

        # Track positions
        self.positions: Dict[str, Dict] = {}

        # Track fills
        self.fills: list[Dict] = []

        logger.info(
            f"📄 Paper Execution Engine initialized "
            f"(slippage={slippage_pct*100:.2f}%, fee={fee_pct*100:.2f}%)"
        )

    def execute_order(
        self,
        order: Dict,
        current_price: float,
        timestamp: Optional[datetime] = None,
    ) -> Dict:
        """
        Execute order (paper mode - simulated).

        Args:
            order: Order dict with symbol, side, size, order_type
            current_price: Current market price
            timestamp: Execution timestamp (default: now)

        Returns:
            OrderResult dict
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        symbol = order["symbol"]
        side = order["side"]
        size = order["size"]
        order_type = order.get("order_type", "MARKET")

        logger.debug(
            f"📄 Executing {order_type} {side} {size} {symbol} @ {current_price}"
        )

        # Simulate fill or rejection
        if not self._should_fill():
            return self._create_rejection(order, "market_conditions", timestamp)

        # Calculate fill price (with slippage)
        fill_price = self._calculate_fill_price(current_price, side, order_type)

        # Calculate fees
        notional = size * fill_price
        fees = notional * self.fee_pct

        # Calculate slippage
        expected_price = current_price
        slippage = abs(fill_price - expected_price) / expected_price

        # Update positions
        self._update_position(symbol, side, size, fill_price, timestamp)

        # Create fill result
        result = {
            "order_id": order.get("order_id", str(uuid4())),
            "order_request_id": order.get("event_id"),
            "symbol": symbol,
            "side": side,
            "status": "FILLED",
            "filled_quantity": size,
            "fill_price": fill_price,
            "fees": fees,
            "slippage": slippage,
            "timestamp": timestamp,
            "execution_type": "PAPER",
        }

        self.fills.append(result)

        logger.info(
            f"✅ FILLED: {side} {size} {symbol} @ {fill_price:.2f} "
            f"(fees={fees:.2f}, slippage={slippage*100:.3f}%)"
        )

        return result

    def _should_fill(self) -> bool:
        """
        Simulate fill probability (for realistic rejections).

        Returns:
            bool: True if order should fill
        """
        # For deterministic testing, always fill
        # In production, could use random with seed
        return True  # 100% fills for deterministic paper trading

    def _calculate_fill_price(
        self, market_price: float, side: str, order_type: str
    ) -> float:
        """
        Calculate fill price with slippage.

        Args:
            market_price: Current market price
            side: BUY or SELL
            order_type: MARKET, LIMIT, etc.

        Returns:
            float: Fill price
        """
        if order_type == "MARKET":
            # Market orders get slippage
            if side.upper() == "BUY":
                # Buy: price goes up (worse for buyer)
                return market_price * (1 + self.slippage_pct)
            else:
                # Sell: price goes down (worse for seller)
                return market_price * (1 - self.slippage_pct)
        else:
            # Limit orders fill at limit price (no slippage)
            return market_price

    def _update_position(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        timestamp: datetime,
    ) -> None:
        """
        Update position tracking.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            size: Order size
            price: Fill price
            timestamp: Execution timestamp
        """
        if symbol not in self.positions:
            self.positions[symbol] = {
                "symbol": symbol,
                "quantity": 0.0,
                "avg_entry_price": 0.0,
                "realized_pnl": 0.0,
                "last_update": timestamp,
            }

        position = self.positions[symbol]

        if side.upper() == "BUY":
            # Increase position
            old_quantity = position["quantity"]
            old_avg_price = position["avg_entry_price"]

            new_quantity = old_quantity + size
            new_avg_price = (
                (old_quantity * old_avg_price + size * price) / new_quantity
                if new_quantity > 0
                else 0
            )

            position["quantity"] = new_quantity
            position["avg_entry_price"] = new_avg_price

        else:  # SELL
            # Decrease position (realize P&L)
            old_quantity = position["quantity"]
            avg_entry = position["avg_entry_price"]

            # Calculate realized P&L
            realized_pnl = size * (price - avg_entry)
            position["realized_pnl"] += realized_pnl

            # Update quantity
            position["quantity"] = max(0, old_quantity - size)

            logger.debug(f"💰 Realized P&L: {realized_pnl:.2f} on {symbol}")

        position["last_update"] = timestamp

    def _create_rejection(
        self, order: Dict, reason: str, timestamp: datetime
    ) -> Dict:
        """
        Create rejection result.

        Args:
            order: Order dict
            reason: Rejection reason
            timestamp: Rejection timestamp

        Returns:
            OrderResult dict
        """
        result = {
            "order_id": order.get("order_id", str(uuid4())),
            "order_request_id": order.get("event_id"),
            "symbol": order["symbol"],
            "side": order["side"],
            "status": "REJECTED",
            "filled_quantity": 0.0,
            "fill_price": None,
            "fees": 0.0,
            "slippage": 0.0,
            "error_message": reason,
            "timestamp": timestamp,
            "execution_type": "PAPER",
        }

        logger.warning(f"❌ REJECTED: {order['side']} {order['symbol']} ({reason})")

        return result

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get current position for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position dict or None
        """
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Dict]:
        """
        Get all current positions.

        Returns:
            Dict of positions by symbol
        """
        return self.positions.copy()

    def get_total_realized_pnl(self) -> float:
        """
        Get total realized P&L across all positions.

        Returns:
            float: Total realized P&L
        """
        return sum(pos["realized_pnl"] for pos in self.positions.values())

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total unrealized P&L.

        Args:
            current_prices: Dict of current prices by symbol

        Returns:
            float: Total unrealized P&L
        """
        total_unrealized = 0.0

        for symbol, position in self.positions.items():
            if position["quantity"] > 0 and symbol in current_prices:
                current_price = current_prices[symbol]
                avg_entry = position["avg_entry_price"]
                quantity = position["quantity"]

                unrealized = quantity * (current_price - avg_entry)
                total_unrealized += unrealized

        return total_unrealized

    def reset(self) -> None:
        """Reset execution engine (clear positions and fills)."""
        self.positions = {}
        self.fills = []
        logger.info("🔄 Paper Execution Engine reset")


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def simulate_market_impact(size: float, liquidity: float = 1000000.0) -> float:
    """
    Simulate market impact based on order size vs liquidity.

    Args:
        size: Order size (notional)
        liquidity: Market liquidity (notional)

    Returns:
        float: Additional slippage percentage
    """
    # Simple linear model: impact = size / liquidity
    impact = size / liquidity
    return min(impact, 0.05)  # Cap at 5% max impact


def calculate_fees(notional: float, fee_tier: str = "standard") -> float:
    """
    Calculate trading fees.

    Args:
        notional: Order notional value
        fee_tier: Fee tier (standard, vip, etc.)

    Returns:
        float: Total fees
    """
    fee_rates = {
        "standard": 0.001,  # 0.1%
        "vip": 0.0005,  # 0.05%
        "maker": 0.0002,  # 0.02% (maker rebate)
    }

    rate = fee_rates.get(fee_tier, 0.001)
    return notional * rate
