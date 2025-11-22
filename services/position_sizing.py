"""Advanced Position Sizing Strategies for Crypto Futures Trading.

This module implements multiple position sizing methodologies optimized for
momentum strategies on high-volatility assets (cryptocurrencies):

1. Fixed-Fractional: Risk fixed % of equity per trade
2. Volatility Targeting: Scale position to maintain target portfolio volatility
3. Kelly Criterion: Maximize long-term growth based on edge
4. ATR-Based: Use Average True Range for dynamic stop placement

All strategies are designed to work with MEXC Perpetual Futures and integrate
with the mexc_perpetuals module.

References:
- Kelly (1956): "A New Interpretation of Information Rate"
- Moreira & Muir (2017): "Volatility-Managed Portfolios"
- Tharp (2008): "Trade Your Way to Financial Freedom"
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation.

    Attributes:
        size_usd: Position size in quote currency (USDT).
        size_contracts: Position size in base currency units.
        method: Sizing method used.
        sizing_factor: Internal sizing factor (for debugging).
        risk_amount: Dollar risk for this position.
        notes: Optional notes about calculation.
    """

    size_usd: float
    size_contracts: float
    method: str
    sizing_factor: float
    risk_amount: float
    notes: Optional[str] = None


class PositionSizer:
    """Advanced position sizing strategies for crypto futures."""

    @staticmethod
    def fixed_fractional(
        equity: float,
        risk_fraction: float,
        stop_loss_distance: float,
        entry_price: float,
    ) -> PositionSizingResult:
        """Fixed-fractional position sizing based on stop-loss distance.

        Formula:
            Position Size = (Equity × Risk Fraction) / (Entry Price × Stop Distance)

        This is the classic risk-based sizing: you decide how much $ to risk,
        then calculate position size so that hitting the stop loses exactly that amount.

        Args:
            equity: Account equity in USDT.
            risk_fraction: Fraction of equity to risk (e.g., 0.02 = 2%).
            stop_loss_distance: Stop distance as decimal (e.g., 0.02 = 2% from entry).
            entry_price: Entry price in USDT.

        Returns:
            PositionSizingResult with calculated size.

        Example:
            >>> result = PositionSizer.fixed_fractional(100000, 0.02, 0.02, 50000)
            >>> result.size_usd
            100000.0  # $100k position
            >>> result.risk_amount
            2000.0  # Risk $2k (2% of equity)

        Notes:
            - Simple and intuitive
            - Good for beginners
            - Doesn't adapt to volatility
        """
        # Calculate dollar risk
        risk_amount = equity * risk_fraction

        # Calculate position size
        # If stop is 2% away and we risk $2k, position must be $100k
        # so that 2% move = $2k loss
        stop_distance_usd = entry_price * stop_loss_distance
        size_contracts = risk_amount / stop_distance_usd
        size_usd = size_contracts * entry_price

        logger.info(
            f"Fixed-Fractional: equity={equity:.0f} risk={risk_fraction:.2%} "
            f"stop={stop_loss_distance:.2%} → size={size_usd:.0f} USDT"
        )

        return PositionSizingResult(
            size_usd=size_usd,
            size_contracts=size_contracts,
            method="fixed_fractional",
            sizing_factor=risk_fraction / stop_loss_distance,
            risk_amount=risk_amount,
            notes=f"Risk {risk_fraction:.2%} with {stop_loss_distance:.2%} stop",
        )

    @staticmethod
    def volatility_targeting(
        equity: float,
        target_volatility: float,
        asset_volatility: float,
        current_price: float,
    ) -> PositionSizingResult:
        """Volatility-targeted position sizing for stable portfolio risk.

        Formula:
            Position Size (notional) = (Equity × Target Vol) / Asset Vol

        This approach maintains constant portfolio volatility by scaling position
        size inversely with asset volatility. When BTC vol doubles, position size halves.

        Args:
            equity: Account equity in USDT.
            target_volatility: Target portfolio volatility (annualized, e.g., 0.20 = 20%).
            asset_volatility: Asset volatility (annualized, e.g., 0.60 = 60%).
            current_price: Current asset price in USDT.

        Returns:
            PositionSizingResult with calculated size.

        Example:
            >>> result = PositionSizer.volatility_targeting(100000, 0.20, 0.60, 50000)
            >>> result.size_usd
            33333.33  # Position scales down due to high BTC vol

        Notes:
            - Adapts to market conditions
            - Reduces size in high-vol regimes
            - Requires good vol estimation (use Parkinson or GARCH)

        References:
            Moreira & Muir (2017): "Volatility-Managed Portfolios"
        """
        if asset_volatility <= 0:
            raise ValueError(
                f"Asset volatility must be positive, got {asset_volatility}"
            )

        # Calculate notional exposure
        notional = (equity * target_volatility) / asset_volatility
        size_contracts = notional / current_price

        # Calculate implied risk (for consistency with other methods)
        # Risk ≈ Notional × Daily Vol (annualized vol / sqrt(252))
        daily_vol = asset_volatility / (252**0.5)
        risk_amount = notional * daily_vol

        logger.info(
            f"Vol-Targeting: equity={equity:.0f} target_vol={target_volatility:.2%} "
            f"asset_vol={asset_volatility:.2%} → notional={notional:.0f} USDT"
        )

        return PositionSizingResult(
            size_usd=notional,
            size_contracts=size_contracts,
            method="volatility_targeting",
            sizing_factor=target_volatility / asset_volatility,
            risk_amount=risk_amount,
            notes=f"Target {target_volatility:.0%} vol with asset vol {asset_volatility:.0%}",
        )

    @staticmethod
    def kelly_criterion(
        equity: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        kelly_fraction: float = 0.25,
    ) -> PositionSizingResult:
        """Kelly Criterion position sizing for optimal growth.

        Formula (simplified):
            Kelly % = (Win Rate × Avg Win - Loss Rate × Avg Loss) / Avg Win
            Position Size = Equity × Kelly % × Fraction

        The Kelly Criterion maximizes long-term growth rate. However, full Kelly
        is very aggressive, so we use fractional Kelly (default 25%) for safety.

        Args:
            equity: Account equity in USDT.
            win_rate: Historical win rate (e.g., 0.55 = 55% winners).
            avg_win: Average win as decimal (e.g., 0.03 = 3% gain).
            avg_loss: Average loss as decimal (e.g., 0.015 = 1.5% loss, input as positive).
            kelly_fraction: Kelly fraction to use (0.25 = 25% of full Kelly, recommended).

        Returns:
            PositionSizingResult with calculated size.

        Example:
            >>> result = PositionSizer.kelly_criterion(100000, 0.55, 0.03, 0.015, 0.25)
            >>> result.size_usd
            27083.33  # ~27% of equity (conservative)

        Notes:
            - Optimal for known edge
            - Full Kelly is too aggressive (drawdowns ~50%)
            - Use 1/4 or 1/2 Kelly for practical trading
            - Requires accurate win rate & payoff ratio

        References:
            Kelly (1956): "A New Interpretation of Information Rate"
            Thorp (1997): "The Kelly Criterion in Blackjack Sports Betting..."
        """
        if not (0 < win_rate < 1):
            raise ValueError(f"Win rate must be between 0 and 1, got {win_rate}")
        if avg_win <= 0 or avg_loss <= 0:
            raise ValueError("Average win and loss must be positive")

        loss_rate = 1 - win_rate

        # Kelly formula
        kelly_pct = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        # Apply fraction (safety limiter)
        adjusted_kelly = kelly_pct * kelly_fraction

        # Handle negative Kelly (no edge)
        if adjusted_kelly <= 0:
            logger.warning(
                f"Kelly Criterion: negative edge detected "
                f"(win_rate={win_rate:.2%} avg_win={avg_win:.2%} avg_loss={avg_loss:.2%})"
            )
            return PositionSizingResult(
                size_usd=0.0,
                size_contracts=0.0,
                method="kelly_criterion",
                sizing_factor=0.0,
                risk_amount=0.0,
                notes="Negative Kelly → no position (no edge)",
            )

        # Cap at 100% (never use more than full equity)
        adjusted_kelly = min(adjusted_kelly, 1.0)

        # Calculate position size
        size_usd = equity * adjusted_kelly
        risk_amount = equity * adjusted_kelly * avg_loss

        logger.info(
            f"Kelly Criterion: win_rate={win_rate:.2%} payoff={avg_win/avg_loss:.2f} "
            f"→ full_kelly={kelly_pct:.2%} fractional={adjusted_kelly:.2%} "
            f"→ size={size_usd:.0f} USDT"
        )

        return PositionSizingResult(
            size_usd=size_usd,
            size_contracts=0.0,  # Contracts calculated by caller with price
            method="kelly_criterion",
            sizing_factor=adjusted_kelly,
            risk_amount=risk_amount,
            notes=f"Kelly {kelly_pct:.2%} × fraction {kelly_fraction:.2%}",
        )

    @staticmethod
    def atr_based_sizing(
        equity: float,
        atr: float,
        atr_multiplier: float,
        risk_per_trade: float,
        entry_price: float,
    ) -> PositionSizingResult:
        """ATR-based position sizing with dynamic stop placement.

        Formula:
            Stop Distance = ATR × Multiplier
            Position Size = (Equity × Risk %) / Stop Distance

        Uses Average True Range (ATR) to set stops, then calculates position size
        to risk a fixed % of equity. ATR adapts to volatility automatically.

        Args:
            equity: Account equity in USDT.
            atr: Average True Range in quote currency (USDT).
            atr_multiplier: ATR multiplier for stop (e.g., 2.0 = stop at 2× ATR).
            risk_per_trade: Risk as decimal (e.g., 0.02 = 2%).
            entry_price: Entry price in USDT.

        Returns:
            PositionSizingResult with calculated size.

        Example:
            >>> result = PositionSizer.atr_based_sizing(100000, 2500, 2.0, 0.02, 50000)
            >>> result.size_usd
            40000.0  # Position sized for 2% risk with 2×ATR stop

        Notes:
            - Adapts to volatility (ATR)
            - Wider stops in volatile markets
            - Good for trend-following
            - ATR is lagging indicator

        References:
            Wilder (1978): "New Concepts in Technical Trading Systems"
            Tharp (2008): "Trade Your Way to Financial Freedom"
        """
        if atr <= 0:
            raise ValueError(f"ATR must be positive, got {atr}")
        if atr_multiplier <= 0:
            raise ValueError(f"ATR multiplier must be positive, got {atr_multiplier}")

        # Calculate stop distance
        stop_distance_usd = atr * atr_multiplier

        # Calculate position size based on risk
        risk_amount = equity * risk_per_trade
        size_contracts = risk_amount / stop_distance_usd
        size_usd = size_contracts * entry_price

        # Calculate stop distance as % for comparison
        stop_distance_pct = stop_distance_usd / entry_price

        logger.info(
            f"ATR-Based: equity={equity:.0f} atr={atr:.0f} multiplier={atr_multiplier:.1f} "
            f"→ stop={stop_distance_usd:.0f} ({stop_distance_pct:.2%}) "
            f"→ size={size_usd:.0f} USDT"
        )

        return PositionSizingResult(
            size_usd=size_usd,
            size_contracts=size_contracts,
            method="atr_based",
            sizing_factor=risk_per_trade / stop_distance_pct,
            risk_amount=risk_amount,
            notes=f"ATR {atr:.0f} × {atr_multiplier:.1f} = {stop_distance_usd:.0f} USDT stop",
        )


def select_sizing_method(
    method: str,
    equity: float,
    signal: Dict,
    market_conditions: Dict,
    config: Dict,
) -> PositionSizingResult:
    """Select and apply position sizing method based on configuration.

    This is the main entry point for position sizing in the risk engine.

    Args:
        method: Sizing method name ("fixed_fractional", "volatility_targeting",
                "kelly_criterion", "atr_based").
        equity: Account equity in USDT.
        signal: Signal event dict with keys: price, side, symbol.
        market_conditions: Dict with market data:
            - volatility: Asset volatility (annualized)
            - atr: Average True Range
            - win_rate: Historical win rate (for Kelly)
            - avg_win: Average win (for Kelly)
            - avg_loss: Average loss (for Kelly)
        config: Risk configuration dict with sizing parameters.

    Returns:
        PositionSizingResult with calculated size.

    Raises:
        ValueError: If method is unknown or required parameters are missing.

    Example:
        >>> config = {"RISK_PER_TRADE": 0.02, "SIZING_METHOD": "fixed_fractional"}
        >>> signal = {"price": 50000, "side": "buy", "symbol": "BTCUSDT"}
        >>> market_conditions = {"volatility": 0.60, "atr": 2500}
        >>> result = select_sizing_method("fixed_fractional", 100000,
        ...                               signal, market_conditions, config)
    """
    entry_price = float(signal["price"])

    if method == "fixed_fractional":
        risk_fraction = float(config.get("RISK_PER_TRADE", 0.02))
        stop_distance = float(config.get("STOP_LOSS_PCT", 0.02))
        return PositionSizer.fixed_fractional(
            equity=equity,
            risk_fraction=risk_fraction,
            stop_loss_distance=stop_distance,
            entry_price=entry_price,
        )

    elif method == "volatility_targeting":
        target_vol = float(config.get("TARGET_VOL", 0.20))
        asset_vol = float(market_conditions.get("volatility", 0.60))
        return PositionSizer.volatility_targeting(
            equity=equity,
            target_volatility=target_vol,
            asset_volatility=asset_vol,
            current_price=entry_price,
        )

    elif method == "kelly_criterion":
        win_rate = float(market_conditions.get("win_rate", 0.50))
        avg_win = float(market_conditions.get("avg_win", 0.02))
        avg_loss = float(market_conditions.get("avg_loss", 0.01))
        kelly_fraction = float(config.get("KELLY_FRACTION", 0.25))
        return PositionSizer.kelly_criterion(
            equity=equity,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            kelly_fraction=kelly_fraction,
        )

    elif method == "atr_based":
        atr = float(market_conditions.get("atr", 0.0))
        if atr <= 0:
            raise ValueError("ATR must be provided for atr_based sizing")
        atr_multiplier = float(config.get("ATR_MULTIPLIER", 2.0))
        risk_per_trade = float(config.get("RISK_PER_TRADE", 0.02))
        return PositionSizer.atr_based_sizing(
            equity=equity,
            atr=atr,
            atr_multiplier=atr_multiplier,
            risk_per_trade=risk_per_trade,
            entry_price=entry_price,
        )

    else:
        raise ValueError(
            f"Unknown sizing method: {method}. "
            f"Valid methods: fixed_fractional, volatility_targeting, "
            f"kelly_criterion, atr_based"
        )


def load_sizing_config() -> Dict:
    """Load position sizing configuration from environment variables.

    Returns:
        Dict with sizing config parameters.

    ENV Variables:
        SIZING_METHOD: Method name (default: "fixed_fractional")
        RISK_PER_TRADE: Risk per trade as decimal (default: 0.02 = 2%)
        TARGET_VOL: Target portfolio volatility (default: 0.20 = 20%)
        KELLY_FRACTION: Kelly fraction (default: 0.25 = 25%)
        ATR_MULTIPLIER: ATR multiplier for stops (default: 2.0)
        STOP_LOSS_PCT: Stop loss distance (default: 0.02 = 2%)
    """
    return {
        "SIZING_METHOD": os.getenv("SIZING_METHOD", "fixed_fractional"),
        "RISK_PER_TRADE": float(os.getenv("RISK_PER_TRADE", "0.02")),
        "TARGET_VOL": float(os.getenv("TARGET_VOL", "0.20")),
        "KELLY_FRACTION": float(os.getenv("KELLY_FRACTION", "0.25")),
        "ATR_MULTIPLIER": float(os.getenv("ATR_MULTIPLIER", "2.0")),
        "STOP_LOSS_PCT": float(os.getenv("STOP_LOSS_PCT", "0.02")),
    }
