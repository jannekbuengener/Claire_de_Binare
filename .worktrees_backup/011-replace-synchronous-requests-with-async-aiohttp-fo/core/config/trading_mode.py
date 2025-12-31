"""
Trading Mode Configuration
Provides centralized trading mode management with safe defaults.

CRITICAL SAFETY:
- Default mode is PAPER (no real money)
- LIVE mode requires explicit confirmation
- STAGED mode uses testnet
"""

import os
import sys
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode enumeration with safety levels."""

    PAPER = "paper"  # Simulated trading, no real money, no exchange connection
    STAGED = "staged"  # Testnet trading, no real money, uses exchange testnet
    LIVE = "live"  # REAL MONEY - production trading on real exchange

    @property
    def is_safe(self) -> bool:
        """Returns True if mode does not risk real money."""
        return self in (TradingMode.PAPER, TradingMode.STAGED)

    @property
    def uses_exchange(self) -> bool:
        """Returns True if mode connects to exchange (testnet or live)."""
        return self in (TradingMode.STAGED, TradingMode.LIVE)

    @property
    def requires_confirmation(self) -> bool:
        """Returns True if mode requires explicit user confirmation."""
        return self == TradingMode.LIVE


def get_trading_mode(
    env_var: str = "TRADING_MODE",
    default: TradingMode = TradingMode.PAPER,
    require_confirmation: bool = True,
) -> TradingMode:
    """
    Get trading mode from environment with safe defaults.

    Args:
        env_var: Environment variable name (default: TRADING_MODE)
        default: Default mode if env var not set (default: PAPER)
        require_confirmation: Require LIVE_TRADING_CONFIRMED=yes for live mode

    Returns:
        TradingMode enum value

    Raises:
        SystemExit: If LIVE mode requested without confirmation

    Examples:
        >>> # Safe default (no env var)
        >>> mode = get_trading_mode()
        >>> assert mode == TradingMode.PAPER

        >>> # Explicit paper mode
        >>> os.environ["TRADING_MODE"] = "paper"
        >>> mode = get_trading_mode()
        >>> assert mode == TradingMode.PAPER

        >>> # Staged mode (testnet)
        >>> os.environ["TRADING_MODE"] = "staged"
        >>> mode = get_trading_mode()
        >>> assert mode == TradingMode.STAGED

        >>> # Live mode requires confirmation
        >>> os.environ["TRADING_MODE"] = "live"
        >>> os.environ["LIVE_TRADING_CONFIRMED"] = "yes"
        >>> mode = get_trading_mode()
        >>> assert mode == TradingMode.LIVE
    """
    mode_str = os.getenv(env_var, default.value).lower().strip()

    try:
        mode = TradingMode(mode_str)
    except ValueError:
        logger.error(
            f"Invalid trading mode: '{mode_str}'. Must be one of: paper, staged, live"
        )
        logger.error(f"Defaulting to PAPER mode for safety")
        return TradingMode.PAPER

    # SAFETY: LIVE mode requires explicit confirmation
    if mode == TradingMode.LIVE and require_confirmation:
        confirmation = os.getenv("LIVE_TRADING_CONFIRMED", "").lower().strip()
        if confirmation != "yes":
            logger.critical(
                "🚨 LIVE TRADING MODE BLOCKED 🚨"
            )
            logger.critical(
                "LIVE mode requires LIVE_TRADING_CONFIRMED=yes environment variable"
            )
            logger.critical(
                "This is a safety measure to prevent accidental real-money trading"
            )
            logger.critical(
                "Current LIVE_TRADING_CONFIRMED value: '%s'", confirmation or "(not set)"
            )
            sys.exit(1)

        logger.warning("=" * 80)
        logger.warning("🔴 LIVE TRADING MODE ACTIVE - REAL MONEY AT RISK 🔴")
        logger.warning("=" * 80)

    # Log mode selection
    if mode == TradingMode.PAPER:
        logger.info("🟢 Trading mode: PAPER (simulated trading, no real money)")
    elif mode == TradingMode.STAGED:
        logger.info("🟡 Trading mode: STAGED (testnet, no real money)")
    elif mode == TradingMode.LIVE:
        logger.warning("🔴 Trading mode: LIVE (REAL MONEY - production)")

    return mode


def validate_trading_mode(mode: TradingMode, **kwargs) -> bool:
    """
    Validate trading mode configuration.

    Args:
        mode: Trading mode to validate
        **kwargs: Additional validation context (e.g., api_key, api_secret)

    Returns:
        True if mode is valid and safe to use

    Raises:
        ValueError: If mode configuration is invalid
        SystemExit: If LIVE mode without confirmation

    Examples:
        >>> validate_trading_mode(TradingMode.PAPER)
        True

        >>> validate_trading_mode(TradingMode.STAGED, api_key="test", api_secret="test")
        True

        >>> # Live mode validation
        >>> os.environ["LIVE_TRADING_CONFIRMED"] = "yes"
        >>> validate_trading_mode(TradingMode.LIVE, api_key="real", api_secret="real")
        True
    """
    if not isinstance(mode, TradingMode):
        raise ValueError(f"Invalid mode type: {type(mode)}. Expected TradingMode enum")

    # STAGED and LIVE modes require API credentials
    if mode.uses_exchange:
        api_key = kwargs.get("api_key")
        api_secret = kwargs.get("api_secret")

        if not api_key or not api_secret:
            raise ValueError(
                f"{mode.value.upper()} mode requires API credentials "
                "(api_key and api_secret)"
            )

    # LIVE mode safety check
    if mode == TradingMode.LIVE:
        confirmation = os.getenv("LIVE_TRADING_CONFIRMED", "").lower().strip()
        if confirmation != "yes":
            logger.critical("LIVE mode requires LIVE_TRADING_CONFIRMED=yes")
            sys.exit(1)

    return True


def get_legacy_config(mode: TradingMode) -> dict:
    """
    Convert TradingMode to legacy config flags for backward compatibility.

    Args:
        mode: Trading mode

    Returns:
        Dict with legacy config flags (MOCK_TRADING, DRY_RUN, MEXC_TESTNET)

    Examples:
        >>> config = get_legacy_config(TradingMode.PAPER)
        >>> assert config == {"MOCK_TRADING": True, "DRY_RUN": True, "MEXC_TESTNET": True}

        >>> config = get_legacy_config(TradingMode.STAGED)
        >>> assert config == {"MOCK_TRADING": False, "DRY_RUN": False, "MEXC_TESTNET": True}

        >>> config = get_legacy_config(TradingMode.LIVE)
        >>> assert config == {"MOCK_TRADING": False, "DRY_RUN": False, "MEXC_TESTNET": False}
    """
    if mode == TradingMode.PAPER:
        return {
            "MOCK_TRADING": True,  # Use mock executor
            "DRY_RUN": True,  # Log only, no execution
            "MEXC_TESTNET": True,  # Testnet (even though not used in paper mode)
        }
    elif mode == TradingMode.STAGED:
        return {
            "MOCK_TRADING": False,  # Use real executor
            "DRY_RUN": False,  # Execute orders
            "MEXC_TESTNET": True,  # Use testnet
        }
    elif mode == TradingMode.LIVE:
        return {
            "MOCK_TRADING": False,  # Use real executor
            "DRY_RUN": False,  # Execute orders
            "MEXC_TESTNET": False,  # Use production exchange
        }
    else:
        raise ValueError(f"Unknown trading mode: {mode}")
