"""
Price Buffer - Stateful pct_change calculation
Claire de Binare Signal Engine
"""

import logging
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger("signal_engine.price_buffer")


class PriceBuffer:
    """
    In-memory price history tracker for stateful pct_change calculation.

    Maintains a rolling window of prices per symbol to calculate percentage changes
    when pct_change is not provided in incoming market data (e.g., raw trade data from cdb_ws).

    Architecture:
    - In-memory only (no Redis persistence - signal engine is stateless by design)
    - Per-symbol price tracking using dict
    - Cold start handling: First price for symbol → pct_change = 0.0
    - Thread-safe for single-threaded usage (no locks needed in current architecture)

    Usage:
        buffer = PriceBuffer()
        pct_change = buffer.calculate_pct_change("BTCUSDT", 50000.0)
        # First call → 0.0 (cold start)
        # Second call → calculated from previous price
    """

    def __init__(self, max_history: int = 1):
        """
        Initialize PriceBuffer.

        Args:
            max_history: Number of historical prices to keep per symbol (default: 1)
                         Currently only last price is needed for pct_change calculation.
        """
        self._prices: Dict[str, deque] = {}
        self._max_history = max_history
        logger.info(f"PriceBuffer initialized (max_history={max_history})")

    def calculate_pct_change(self, symbol: str, current_price: float) -> float:
        """
        Calculate percentage change for given symbol and price.

        Formula: pct_change = (current_price - prev_price) / prev_price * 100

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            current_price: Current price to calculate change for

        Returns:
            float: Percentage change from previous price
                   0.0 on cold start (first price for symbol)
                   Calculated pct_change otherwise

        Side Effects:
            Updates internal price history with current_price
        """
        if symbol not in self._prices:
            # Cold start: First price for this symbol
            self._prices[symbol] = deque(maxlen=self._max_history)
            self._prices[symbol].append(current_price)
            logger.debug(f"{symbol}: Cold start @ ${current_price:.2f} → pct_change=0.0")
            return 0.0

        # Get previous price
        prev_price = self._prices[symbol][-1]

        # Calculate pct_change
        pct_change = ((current_price - prev_price) / prev_price) * 100.0

        # Update history
        self._prices[symbol].append(current_price)

        logger.debug(
            f"{symbol}: ${prev_price:.2f} → ${current_price:.2f} "
            f"({pct_change:+.4f}%)"
        )

        return pct_change

    def get_last_price(self, symbol: str) -> Optional[float]:
        """
        Get last known price for symbol (for diagnostics/testing).

        Args:
            symbol: Trading pair symbol

        Returns:
            float: Last price if available, None if symbol not tracked
        """
        if symbol not in self._prices or len(self._prices[symbol]) == 0:
            return None
        return self._prices[symbol][-1]

    def reset(self, symbol: Optional[str] = None):
        """
        Reset price history for symbol or all symbols.

        Args:
            symbol: Symbol to reset, or None to reset all
        """
        if symbol:
            if symbol in self._prices:
                del self._prices[symbol]
                logger.info(f"Price history reset for {symbol}")
        else:
            self._prices.clear()
            logger.info("Price history reset for all symbols")

    def get_tracked_symbols(self) -> list:
        """Get list of currently tracked symbols."""
        return list(self._prices.keys())

    def __len__(self) -> int:
        """Return number of tracked symbols."""
        return len(self._prices)
