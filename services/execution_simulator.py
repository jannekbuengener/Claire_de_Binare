"""Realistic Execution Simulator for Paper Trading.

This module simulates realistic order execution for MEXC Perpetual Futures,
including:
- Slippage (base + volatility-adjusted + depth impact)
- Trading fees (maker/taker)
- Partial fills
- Funding fees
- Order book depth impact

Designed for backtesting and paper trading to minimize backtest bias.

References:
- Almgren & Chriss (2000): "Optimal Execution of Portfolio Transactions"
- Kissell & Glantz (2003): "Optimal Trading Strategies"
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of simulated order execution.

    Attributes:
        filled_size: Actual filled size (may be partial).
        avg_fill_price: Average fill price including slippage.
        slippage_bps: Total slippage in basis points.
        fees: Total trading fees in quote currency.
        partial_fill: Whether this was a partial fill.
        fill_ratio: Ratio of filled to requested size (0.0-1.0).
        notes: Optional execution notes.
    """

    filled_size: float
    avg_fill_price: float
    slippage_bps: float
    fees: float
    partial_fill: bool
    fill_ratio: float
    notes: Optional[str] = None


class ExecutionSimulator:
    """Realistic execution simulation for crypto futures."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize execution simulator with configuration.

        Args:
            config: Configuration dict with keys:
                - MAKER_FEE: Maker fee rate (default 0.0002 = 0.02%)
                - TAKER_FEE: Taker fee rate (default 0.0006 = 0.06%)
                - BASE_SLIPPAGE_BPS: Base slippage in bps (default 5)
                - DEPTH_IMPACT_FACTOR: Depth impact factor (default 0.10)
                - VOL_SLIPPAGE_MULTIPLIER: Volatility multiplier (default 2.0)
                - FILL_THRESHOLD: Max % of depth usable (default 0.80)
                - FUNDING_RATE: Funding rate per 8h (default 0.0001)
        """
        self.config = config or {}

        # Fee structure (MEXC 2024)
        self.maker_fee = float(self.config.get("MAKER_FEE", 0.0002))
        self.taker_fee = float(self.config.get("TAKER_FEE", 0.0006))

        # Slippage parameters
        self.base_slippage_bps = float(self.config.get("BASE_SLIPPAGE_BPS", 5.0))
        self.depth_impact_factor = float(self.config.get("DEPTH_IMPACT_FACTOR", 0.10))
        self.vol_slippage_multiplier = float(self.config.get("VOL_SLIPPAGE_MULTIPLIER", 2.0))

        # Partial fill parameters
        self.fill_threshold = float(self.config.get("FILL_THRESHOLD", 0.80))

        # Funding rate
        self.funding_rate = float(self.config.get("FUNDING_RATE", 0.0001))

        logger.info(
            f"ExecutionSimulator initialized: "
            f"maker_fee={self.maker_fee:.4f} taker_fee={self.taker_fee:.4f} "
            f"base_slippage={self.base_slippage_bps:.1f}bps"
        )

    def simulate_market_order(
        self,
        side: str,
        size: float,
        current_price: float,
        order_book_depth: float,
        volatility: float,
    ) -> ExecutionResult:
        """Simulate market order execution with realistic slippage and fees.

        Args:
            side: Order side ("buy" or "sell").
            size: Order size in base currency (e.g., BTC).
            current_price: Current market price in quote currency (USDT).
            order_book_depth: Available liquidity in quote currency (USDT).
            volatility: Current volatility (e.g., 0.02 = 2% hourly).

        Returns:
            ExecutionResult with fill details.

        Example:
            >>> sim = ExecutionSimulator()
            >>> result = sim.simulate_market_order("buy", 0.5, 50000, 1000000, 0.02)
            >>> result.filled_size
            0.5  # Full fill
            >>> result.slippage_bps
            15.0  # 0.15% slippage
        """
        notional = size * current_price

        # Check for partial fill
        usable_depth = order_book_depth * self.fill_threshold
        if notional > usable_depth:
            # Partial fill
            filled_notional = usable_depth
            filled_size = filled_notional / current_price
            fill_ratio = filled_size / size
            partial_fill = True
            logger.warning(
                f"Partial fill: requested={notional:.0f} available={usable_depth:.0f} "
                f"filled={filled_notional:.0f} ({fill_ratio:.2%})"
            )
        else:
            # Full fill
            filled_notional = notional
            filled_size = size
            fill_ratio = 1.0
            partial_fill = False

        # Calculate slippage
        slippage_bps = self._calculate_slippage(
            order_size=filled_notional,
            order_book_depth=order_book_depth,
            volatility=volatility,
        )

        # Apply slippage to price
        slippage_fraction = slippage_bps / 10000.0
        if side.lower() in ["buy", "long"]:
            # Buy: price increases (adverse)
            avg_fill_price = current_price * (1 + slippage_fraction)
        else:  # sell/short
            # Sell: price decreases (adverse)
            avg_fill_price = current_price * (1 - slippage_fraction)

        # Calculate fees (market order = taker)
        fees = filled_notional * self.taker_fee

        logger.info(
            f"Market Order: {side} {filled_size:.4f} @ {avg_fill_price:.2f} "
            f"(slippage={slippage_bps:.1f}bps fees={fees:.2f})"
        )

        return ExecutionResult(
            filled_size=filled_size,
            avg_fill_price=avg_fill_price,
            slippage_bps=slippage_bps,
            fees=fees,
            partial_fill=partial_fill,
            fill_ratio=fill_ratio,
            notes=f"Market order {side} with {slippage_bps:.1f}bps slippage",
        )

    def simulate_limit_order(
        self,
        side: str,
        size: float,
        limit_price: float,
        current_price: float,
        time_in_force: str = "GTC",
    ) -> ExecutionResult:
        """Simulate limit order execution (simplified model).

        For limit orders, we use a simplified model:
        - If limit price is better than market: no fill (too aggressive)
        - If limit price is at or worse than market: fill as maker

        Args:
            side: Order side ("buy" or "sell").
            size: Order size in base currency.
            limit_price: Limit price in quote currency.
            current_price: Current market price.
            time_in_force: Time in force (default "GTC").

        Returns:
            ExecutionResult with fill details.

        Example:
            >>> sim = ExecutionSimulator()
            >>> result = sim.simulate_limit_order("buy", 0.5, 49000, 50000)
            >>> result.filled_size
            0.5  # Fill at limit price (maker fee)
        """
        notional = size * limit_price

        # Simplified fill logic
        if side.lower() in ["buy", "long"]:
            # Buy limit: fill if limit >= current (at or above market)
            if limit_price >= current_price:
                filled = True
                avg_fill_price = limit_price
            else:
                filled = False
                avg_fill_price = 0.0
        else:  # sell/short
            # Sell limit: fill if limit <= current (at or below market)
            if limit_price <= current_price:
                filled = True
                avg_fill_price = limit_price
            else:
                filled = False
                avg_fill_price = 0.0

        if filled:
            # Filled as maker
            fees = notional * self.maker_fee
            logger.info(
                f"Limit Order: {side} {size:.4f} @ {avg_fill_price:.2f} "
                f"(maker fee={fees:.2f})"
            )
            return ExecutionResult(
                filled_size=size,
                avg_fill_price=avg_fill_price,
                slippage_bps=0.0,  # No slippage for limit orders
                fees=fees,
                partial_fill=False,
                fill_ratio=1.0,
                notes=f"Limit order {side} filled as maker",
            )
        else:
            # Not filled
            logger.info(f"Limit Order: {side} {size:.4f} @ {limit_price:.2f} NOT FILLED")
            return ExecutionResult(
                filled_size=0.0,
                avg_fill_price=0.0,
                slippage_bps=0.0,
                fees=0.0,
                partial_fill=False,
                fill_ratio=0.0,
                notes=f"Limit order {side} not filled (price not reached)",
            )

    def calculate_funding_fees(
        self,
        position_size: float,
        position_value: float,
        funding_rate: Optional[float] = None,
        hours_held: float = 8.0,
    ) -> float:
        """Calculate funding fees for a perpetual position.

        Args:
            position_size: Position size in base currency.
            position_value: Position value in quote currency.
            funding_rate: Funding rate (default from config).
            hours_held: Hours position was held (default 8h = 1 settlement).

        Returns:
            Funding fee in quote currency. Positive = pay, Negative = receive.

        Example:
            >>> sim = ExecutionSimulator()
            >>> fee = sim.calculate_funding_fees(0.1, 5000, 0.0001, 8.0)
            >>> fee
            0.5  # Pay 0.5 USDT per 8h settlement
        """
        rate = funding_rate if funding_rate is not None else self.funding_rate
        settlement_periods = hours_held / 8.0
        fee = position_value * rate * settlement_periods

        logger.debug(
            f"Funding Fee: value={position_value:.0f} rate={rate:.6f} "
            f"hours={hours_held:.1f} → fee={fee:.4f}"
        )

        return fee

    def _calculate_slippage(
        self,
        order_size: float,
        order_book_depth: float,
        volatility: float,
    ) -> float:
        """Calculate total slippage in basis points.

        Formula:
            Slippage = Base + Depth Impact + Volatility Impact

            Depth Impact = (Order Size / Depth) × Impact Factor × 10000
            Volatility Impact = Volatility × Multiplier × 10000

        Args:
            order_size: Order size in quote currency (USDT).
            order_book_depth: Order book depth in quote currency.
            volatility: Current volatility (e.g., 0.02 = 2%).

        Returns:
            Total slippage in basis points.

        Example:
            >>> sim = ExecutionSimulator()
            >>> slippage = sim._calculate_slippage(50000, 1000000, 0.02)
            >>> slippage
            50.0  # 50 bps (0.50%)
        """
        # Base slippage
        slippage = self.base_slippage_bps

        # Depth impact
        if order_book_depth > 0:
            depth_ratio = order_size / order_book_depth
            depth_impact = depth_ratio * self.depth_impact_factor * 10000
            slippage += depth_impact

        # Volatility impact
        vol_impact = volatility * self.vol_slippage_multiplier * 10000
        slippage += vol_impact

        logger.debug(
            f"Slippage Breakdown: base={self.base_slippage_bps:.1f} "
            f"depth={depth_impact:.1f} vol={vol_impact:.1f} → total={slippage:.1f}bps"
        )

        return slippage

    def calculate_roundtrip_cost(
        self,
        size: float,
        entry_price: float,
        exit_price: float,
        order_book_depth: float,
        volatility: float,
    ) -> Dict[str, float]:
        """Calculate total roundtrip cost (entry + exit).

        Args:
            size: Position size in base currency.
            entry_price: Entry price.
            exit_price: Exit price.
            order_book_depth: Order book depth.
            volatility: Volatility.

        Returns:
            Dict with cost breakdown:
                - entry_slippage: Entry slippage in USDT
                - exit_slippage: Exit slippage in USDT
                - entry_fees: Entry fees
                - exit_fees: Exit fees
                - total_cost: Total roundtrip cost
                - cost_bps: Total cost in bps of notional

        Example:
            >>> sim = ExecutionSimulator()
            >>> costs = sim.calculate_roundtrip_cost(1.0, 50000, 51000, 1000000, 0.02)
            >>> costs["total_cost"]
            60.0  # ~60 USDT total cost
        """
        # Entry execution
        entry_result = self.simulate_market_order(
            side="buy",
            size=size,
            current_price=entry_price,
            order_book_depth=order_book_depth,
            volatility=volatility,
        )

        # Exit execution
        exit_result = self.simulate_market_order(
            side="sell",
            size=size,
            current_price=exit_price,
            order_book_depth=order_book_depth,
            volatility=volatility,
        )

        # Calculate slippage in USD
        entry_notional = size * entry_price
        exit_notional = size * exit_price

        entry_slippage_usd = (entry_result.slippage_bps / 10000.0) * entry_notional
        exit_slippage_usd = (exit_result.slippage_bps / 10000.0) * exit_notional

        # Total cost
        total_cost = (
            entry_slippage_usd + exit_slippage_usd + entry_result.fees + exit_result.fees
        )

        # Cost as % of avg notional
        avg_notional = (entry_notional + exit_notional) / 2
        cost_bps = (total_cost / avg_notional) * 10000

        logger.info(
            f"Roundtrip Cost: entry_slip={entry_slippage_usd:.2f} "
            f"exit_slip={exit_slippage_usd:.2f} "
            f"entry_fees={entry_result.fees:.2f} exit_fees={exit_result.fees:.2f} "
            f"→ total={total_cost:.2f} ({cost_bps:.1f}bps)"
        )

        return {
            "entry_slippage": entry_slippage_usd,
            "exit_slippage": exit_slippage_usd,
            "entry_fees": entry_result.fees,
            "exit_fees": exit_result.fees,
            "total_cost": total_cost,
            "cost_bps": cost_bps,
        }


def load_execution_config() -> Dict:
    """Load execution simulation config from environment variables.

    Returns:
        Dict with execution config parameters.

    ENV Variables:
        MAKER_FEE: Maker fee rate (default 0.0002)
        TAKER_FEE: Taker fee rate (default 0.0006)
        BASE_SLIPPAGE_BPS: Base slippage in bps (default 5)
        DEPTH_IMPACT_FACTOR: Depth impact factor (default 0.10)
        VOL_SLIPPAGE_MULTIPLIER: Volatility multiplier (default 2.0)
        FILL_THRESHOLD: Max % of depth usable (default 0.80)
        FUNDING_RATE: Funding rate per 8h (default 0.0001)
    """
    return {
        "MAKER_FEE": float(os.getenv("MAKER_FEE", "0.0002")),
        "TAKER_FEE": float(os.getenv("TAKER_FEE", "0.0006")),
        "BASE_SLIPPAGE_BPS": float(os.getenv("BASE_SLIPPAGE_BPS", "5.0")),
        "DEPTH_IMPACT_FACTOR": float(os.getenv("DEPTH_IMPACT_FACTOR", "0.10")),
        "VOL_SLIPPAGE_MULTIPLIER": float(os.getenv("VOL_SLIPPAGE_MULTIPLIER", "2.0")),
        "FILL_THRESHOLD": float(os.getenv("FILL_THRESHOLD", "0.80")),
        "FUNDING_RATE": float(os.getenv("FUNDING_RATE", "0.0001")),
    }
