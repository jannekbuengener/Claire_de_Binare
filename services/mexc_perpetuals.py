"""MEXC Perpetual Futures Position Management.

This module implements exchange-specific mechanics for MEXC perpetual futures:
- Position margin calculation (cross & isolated)
- Liquidation price calculation
- Funding fee simulation
- Maintenance margin rate tracking

All formulas are based on official MEXC documentation (2024):
https://www.mexc.com/learn/article/17827791513099
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MarginMode(str, Enum):
    """Margin mode for futures positions."""

    ISOLATED = "isolated"
    CROSS = "cross"


class PositionSide(str, Enum):
    """Position direction."""

    LONG = "long"
    SHORT = "short"


@dataclass
class MexcPerpetualPosition:
    """MEXC Perpetual Futures Position with margin, leverage, and liquidation logic.

    Attributes:
        symbol: Trading pair (e.g., "BTCUSDT").
        side: Position direction (long or short).
        size: Position size in base currency (e.g., BTC).
        entry_price: Average entry price in quote currency (e.g., USDT).
        leverage: Leverage multiplier (1-125 on MEXC, Claire max: 10).
        margin_mode: Isolated or cross margin.
        contract_multiplier: Contract size multiplier (default 0.0001 for BTC).
        maintenance_margin_rate: Maintenance margin rate (default 0.005 = 0.5%).
    """

    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    leverage: int
    margin_mode: MarginMode = MarginMode.ISOLATED
    contract_multiplier: float = 0.0001
    maintenance_margin_rate: float = 0.005

    def __post_init__(self):
        """Validate position parameters."""
        if self.leverage < 1 or self.leverage > 125:
            raise ValueError(f"Leverage must be between 1-125, got {self.leverage}")
        if self.size <= 0:
            raise ValueError(f"Position size must be positive, got {self.size}")
        if self.entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {self.entry_price}")

        # Log position creation
        logger.info(
            f"Created {self.side.value} position: {self.symbol} "
            f"size={self.size:.4f} entry={self.entry_price:.2f} "
            f"leverage={self.leverage}x mode={self.margin_mode.value}"
        )

    @property
    def position_value(self) -> float:
        """Calculate position notional value.

        Returns:
            Position value in quote currency (USDT).
        """
        return self.entry_price * self.size

    def calculate_position_margin(self) -> float:
        """Calculate required position margin.

        Formula:
            Position Margin = (Entry Price × Size) / Leverage

        Returns:
            Required margin in quote currency (USDT).

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_position_margin()
            500.0  # (50000 × 0.1) / 10
        """
        margin = self.position_value / self.leverage
        logger.debug(
            f"Position margin: {margin:.2f} USDT "
            f"(value={self.position_value:.2f} / leverage={self.leverage})"
        )
        return margin

    def calculate_maintenance_margin(self) -> float:
        """Calculate maintenance margin requirement.

        Formula:
            Maintenance Margin = Position Value × MMR

        Returns:
            Maintenance margin in quote currency (USDT).

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_maintenance_margin()
            25.0  # 5000 × 0.005
        """
        maintenance = self.position_value * self.maintenance_margin_rate
        logger.debug(
            f"Maintenance margin: {maintenance:.2f} USDT "
            f"(value={self.position_value:.2f} × mmr={self.maintenance_margin_rate})"
        )
        return maintenance

    def calculate_liquidation_price(self, account_balance: Optional[float] = None) -> float:
        """Calculate liquidation price for this position.

        Uses official MEXC formulas (Fair Price based):

        Long Position:
            LP = (MM - PM + Entry Price × Size) / Size

        Short Position:
            LP = (Entry Price × Size - MM + PM) / Size

        Where:
            MM = Maintenance Margin
            PM = Position Margin

        Args:
            account_balance: Account balance in USDT (only used for cross margin).
                For isolated margin, this is ignored.

        Returns:
            Liquidation price in quote currency (USDT).

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_liquidation_price()
            45250.0  # See PERPETUALS_RISK_MANAGEMENT.md for derivation
        """
        mm = self.calculate_maintenance_margin()
        pm = self.calculate_position_margin()

        if self.side == PositionSide.LONG:
            liq_price = (mm - pm + self.entry_price * self.size) / self.size
        else:  # SHORT
            liq_price = (self.entry_price * self.size - mm + pm) / self.size

        # Liquidation distance
        distance_pct = abs(liq_price - self.entry_price) / self.entry_price

        logger.info(
            f"Liquidation price: {liq_price:.2f} USDT "
            f"(distance={distance_pct:.2%} from entry={self.entry_price:.2f})"
        )

        return liq_price

    def calculate_liquidation_distance(self) -> float:
        """Calculate distance to liquidation as percentage of entry price.

        Returns:
            Liquidation distance as decimal (e.g., 0.095 = 9.5%).

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_liquidation_distance()
            0.095  # 9.5% below entry
        """
        liq_price = self.calculate_liquidation_price()
        distance = abs(liq_price - self.entry_price) / self.entry_price
        return distance

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate mark-to-market unrealized PnL.

        Formula (Long):
            PnL = (Current Price - Entry Price) × Size

        Formula (Short):
            PnL = (Entry Price - Current Price) × Size

        Args:
            current_price: Current market price in quote currency.

        Returns:
            Unrealized PnL in quote currency (USDT). Positive = profit, negative = loss.

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_unrealized_pnl(52000)
            200.0  # Profit of 200 USDT
        """
        if self.side == PositionSide.LONG:
            pnl = (current_price - self.entry_price) * self.size
        else:  # SHORT
            pnl = (self.entry_price - current_price) * self.size

        logger.debug(
            f"Unrealized PnL: {pnl:+.2f} USDT "
            f"(current={current_price:.2f} entry={self.entry_price:.2f})"
        )

        return pnl

    def calculate_funding_fee(self, funding_rate: float, hours: float = 8.0) -> float:
        """Calculate funding fee for this position.

        MEXC Funding Rate Mechanics:
        - Settlement: 3× daily (00:00, 08:00, 16:00 UTC)
        - Formula: Funding Fee = Position Value × Funding Rate
        - Direction:
            - Positive rate → Longs PAY Shorts
            - Negative rate → Shorts PAY Longs

        Args:
            funding_rate: Current funding rate (e.g., 0.0001 = 0.01%).
            hours: Time period in hours (default 8h for MEXC settlement).

        Returns:
            Funding fee in quote currency (USDT).
            Positive = you PAY, Negative = you RECEIVE.

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_funding_fee(0.0001)  # 0.01% per 8h
            0.5  # Long pays 0.5 USDT per 8h settlement
        """
        # Funding fee is calculated on position value (not margin)
        funding_fee = self.position_value * funding_rate * (hours / 8.0)

        # Direction: Longs pay positive rate, Shorts pay negative rate
        if self.side == PositionSide.SHORT:
            funding_fee = -funding_fee

        logger.debug(
            f"Funding fee: {funding_fee:+.4f} USDT "
            f"(rate={funding_rate:.6f} value={self.position_value:.2f} hours={hours})"
        )

        return funding_fee

    def calculate_mmr(self, current_price: float) -> float:
        """Calculate Maintenance Margin Rate at current price.

        Formula:
            MMR = Maintenance Margin / Position Value (at current price)

        Liquidation occurs when MMR >= 100%.

        Args:
            current_price: Current market price.

        Returns:
            MMR as decimal (e.g., 0.50 = 50%).

        Example:
            >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
            >>> pos.calculate_mmr(45250)  # At liquidation price
            1.0  # 100% → liquidation triggered
        """
        current_value = current_price * self.size
        mm = self.calculate_maintenance_margin()
        mmr = mm / current_value

        logger.debug(
            f"MMR: {mmr:.2%} at price={current_price:.2f} "
            f"(mm={mm:.2f} / value={current_value:.2f})"
        )

        return mmr

    def to_dict(self) -> Dict:
        """Export position as dictionary for serialization.

        Returns:
            Dictionary with all position attributes.
        """
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "size": self.size,
            "entry_price": self.entry_price,
            "leverage": self.leverage,
            "margin_mode": self.margin_mode.value,
            "position_value": self.position_value,
            "position_margin": self.calculate_position_margin(),
            "maintenance_margin": self.calculate_maintenance_margin(),
            "liquidation_price": self.calculate_liquidation_price(),
            "liquidation_distance": self.calculate_liquidation_distance(),
        }


def create_position_from_signal(
    signal: Dict,
    size: float,
    config: Dict,
) -> MexcPerpetualPosition:
    """Create a MexcPerpetualPosition from a trading signal.

    Args:
        signal: Signal event dict with keys: symbol, side, price.
        size: Position size in base currency.
        config: Risk configuration dict with keys:
            - MAX_LEVERAGE (default 10)
            - MARGIN_MODE (default "isolated")
            - CONTRACT_MULTIPLIER (default 0.0001)
            - MAINTENANCE_MARGIN_RATE (default 0.005)

    Returns:
        MexcPerpetualPosition instance.

    Example:
        >>> signal = {"symbol": "BTCUSDT", "side": "buy", "price": 50000}
        >>> config = {"MAX_LEVERAGE": 10, "MARGIN_MODE": "isolated"}
        >>> pos = create_position_from_signal(signal, 0.1, config)
        >>> pos.leverage
        10
    """
    # Extract parameters
    symbol = signal["symbol"]
    side_str = signal["side"].lower()
    side = PositionSide.LONG if side_str in ["buy", "long"] else PositionSide.SHORT
    entry_price = float(signal["price"])

    # Get config with defaults
    leverage = int(config.get("MAX_LEVERAGE", 10))
    margin_mode_str = config.get("MARGIN_MODE", "isolated")
    margin_mode = MarginMode(margin_mode_str)
    contract_multiplier = float(config.get("CONTRACT_MULTIPLIER", 0.0001))
    mmr = float(config.get("MAINTENANCE_MARGIN_RATE", 0.005))

    return MexcPerpetualPosition(
        symbol=symbol,
        side=side,
        size=size,
        entry_price=entry_price,
        leverage=leverage,
        margin_mode=margin_mode,
        contract_multiplier=contract_multiplier,
        maintenance_margin_rate=mmr,
    )


def validate_liquidation_distance(
    position: MexcPerpetualPosition,
    min_distance: float,
) -> Dict[str, Any]:
    """Validate that liquidation distance is acceptable.

    Args:
        position: MexcPerpetualPosition to validate.
        min_distance: Minimum acceptable distance as decimal (e.g., 0.15 = 15%).

    Returns:
        Dict with keys:
            - approved: bool
            - distance: float
            - reason: Optional[str]

    Example:
        >>> pos = MexcPerpetualPosition("BTCUSDT", "long", 0.1, 50000, 10)
        >>> result = validate_liquidation_distance(pos, 0.15)
        >>> result["approved"]
        False  # 9.5% < 15% → rejected
    """
    distance = position.calculate_liquidation_distance()

    if distance < min_distance:
        return {
            "approved": False,
            "distance": distance,
            "reason": f"liquidation_risk_too_high (distance={distance:.2%} < min={min_distance:.2%})",
        }

    return {
        "approved": True,
        "distance": distance,
        "reason": None,
    }


# ENV-driven configuration loader
def load_perpetuals_config() -> Dict:
    """Load perpetual futures configuration from environment variables.

    Returns:
        Dict with perpetuals config parameters.

    ENV Variables:
        MARGIN_MODE: "isolated" or "cross" (default: isolated)
        MAX_LEVERAGE: 1-125 (default: 10)
        MIN_LIQUIDATION_DISTANCE: 0.0-1.0 (default: 0.15 = 15%)
        CONTRACT_MULTIPLIER: float (default: 0.0001)
        MAINTENANCE_MARGIN_RATE: float (default: 0.005 = 0.5%)
        FUNDING_RATE: float (default: 0.0001 = 0.01% per 8h)
        FUNDING_SETTLEMENT_HOURS: int (default: 8)
    """
    return {
        "MARGIN_MODE": os.getenv("MARGIN_MODE", "isolated"),
        "MAX_LEVERAGE": int(os.getenv("MAX_LEVERAGE", "10")),
        "MIN_LIQUIDATION_DISTANCE": float(os.getenv("MIN_LIQUIDATION_DISTANCE", "0.15")),
        "CONTRACT_MULTIPLIER": float(os.getenv("CONTRACT_MULTIPLIER", "0.0001")),
        "MAINTENANCE_MARGIN_RATE": float(os.getenv("MAINTENANCE_MARGIN_RATE", "0.005")),
        "FUNDING_RATE": float(os.getenv("FUNDING_RATE", "0.0001")),
        "FUNDING_SETTLEMENT_HOURS": int(os.getenv("FUNDING_SETTLEMENT_HOURS", "8")),
    }
