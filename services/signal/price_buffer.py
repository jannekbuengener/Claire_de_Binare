"""
Price Buffer - Stateful pct_change calculation
Claire de Binare Signal Engine
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Deque, Dict, Optional, Tuple

logger = logging.getLogger("signal_engine.price_buffer")


class PriceBuffer:
    """
    In-memory price history tracker for stateful pct_change calculation.

    Maintains a rolling window of prices per symbol to calculate:
    - tick-to-tick ``calculate_pct_change`` (momentum path)
    - event-time lookback ``pct_change_lookback`` for ``pct_change_15m``
      driven by ``SIGNAL_LOOKBACK_MIN`` (#4149)

    Architecture:
    - In-memory only (no Redis persistence - signal engine is stateless by design)
    - Per-symbol price tracking using dict
    - Cold start handling: First price for symbol → tick pct_change = 0.0
    - Lookback: insufficient history → None (no invented value)
    """

    def __init__(self, max_history: int = 1, lookback_minutes: int = 15):
        """
        Args:
            max_history: Number of historical prices for tick-to-tick calc.
            lookback_minutes: Default event-time window for pct_change_lookback.
        """
        self._prices: Dict[str, deque] = {}
        self._ticks: Dict[str, Deque[Tuple[int, float]]] = {}
        self._max_history = max_history
        self._lookback_minutes = lookback_minutes
        # Keep a generous time buffer so out-of-order ticks remain usable.
        self._tick_retention_ms = max(lookback_minutes, 1) * 60_000 * 3
        logger.info(
            "PriceBuffer initialized (max_history=%s, lookback_minutes=%s)",
            max_history,
            lookback_minutes,
        )

    def observe(self, symbol: str, price: float, ts_ms: int) -> None:
        """Record an event-time price sample for lookback calculations."""
        ticks = self._ticks.setdefault(symbol, deque())
        ticks.append((int(ts_ms), float(price)))
        cutoff = int(ts_ms) - self._tick_retention_ms
        while ticks and ticks[0][0] < cutoff:
            ticks.popleft()

    def pct_change_lookback(
        self,
        symbol: str,
        current_price: float,
        now_ms: int,
        lookback_minutes: int | None = None,
    ) -> Optional[float]:
        """
        Percentage-point change over an event-time lookback window.

        Reference = latest observed price with ``ts_ms <= now_ms - lookback``.
        Returns None when no such reference exists (insufficient history).
        """
        minutes = (
            self._lookback_minutes if lookback_minutes is None else lookback_minutes
        )
        if minutes <= 0:
            return None
        target_ms = int(now_ms) - minutes * 60_000
        ticks = self._ticks.get(symbol)
        if not ticks:
            return None
        # Choose latest sample at/before the lookback horizon (out-of-order safe).
        ref_price: Optional[float] = None
        ref_ts: Optional[int] = None
        for ts_ms, price in ticks:
            if ts_ms <= target_ms and (ref_ts is None or ts_ms >= ref_ts):
                ref_ts = ts_ms
                ref_price = price
        if ref_price is None or ref_price == 0:
            return None
        return ((float(current_price) - ref_price) / ref_price) * 100.0

    def calculate_pct_change(self, symbol: str, current_price: float) -> float:
        """
        Calculate tick-to-tick percentage change for given symbol and price.

        Formula: pct_change = (current_price - prev_price) / prev_price * 100
        """
        if symbol not in self._prices:
            self._prices[symbol] = deque(maxlen=self._max_history)
            self._prices[symbol].append(current_price)
            logger.debug(
                f"{symbol}: Cold start @ ${current_price:.2f} → pct_change=0.0"
            )
            return 0.0

        prev_price = self._prices[symbol][-1]
        pct_change = ((current_price - prev_price) / prev_price) * 100.0
        self._prices[symbol].append(current_price)

        logger.debug(
            f"{symbol}: ${prev_price:.2f} → ${current_price:.2f} "
            f"({pct_change:+.4f}%)"
        )

        return pct_change

    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get last known tick price for symbol (for diagnostics/testing)."""
        if symbol not in self._prices or len(self._prices[symbol]) == 0:
            return None
        return self._prices[symbol][-1]

    def reset(self, symbol: Optional[str] = None):
        """Reset price history for symbol or all symbols."""
        if symbol:
            if symbol in self._prices:
                del self._prices[symbol]
                logger.info(f"Price history reset for {symbol}")
            if symbol in self._ticks:
                del self._ticks[symbol]
        else:
            self._prices.clear()
            self._ticks.clear()
            logger.info("Price history reset for all symbols")

    def get_tracked_symbols(self) -> list:
        """Get list of currently tracked symbols."""
        return list(self._prices.keys())

    def __len__(self) -> int:
        """Return number of tracked symbols."""
        return len(self._prices)
