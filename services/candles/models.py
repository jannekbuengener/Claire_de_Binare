"""
Candle Aggregator - Models and logic
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


@dataclass
class CandleWindow:
    """1-minute OHLCV aggregation window"""

    symbol: str
    start_ts: int  # Window start timestamp (seconds, aligned to minute)
    interval_seconds: int

    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: float = 0.0
    trade_count: int = 0

    def update_trade(self, price: float, qty: float, ts_ms: int):
        """Update window with new trade"""
        if self.open is None:
            self.open = price

        if self.high is None or price > self.high:
            self.high = price

        if self.low is None or price < self.low:
            self.low = price

        self.close = price
        self.volume += qty
        self.trade_count += 1

    def is_complete(self, current_ts: int) -> bool:
        """Check if window should be closed (current time >= window end)"""
        window_end = self.start_ts + self.interval_seconds
        return current_ts >= window_end

    def to_candle_payload(self) -> Optional[dict]:
        """Convert to candle payload for stream"""
        if (
            self.open is None
            or self.high is None
            or self.low is None
            or self.close is None
        ):
            return None

        return {
            "ts": str(self.start_ts),
            "symbol": self.symbol,
            "timeframe": f"{self.interval_seconds}s",
            "open": f"{self.open:.8f}",
            "high": f"{self.high:.8f}",
            "low": f"{self.low:.8f}",
            "close": f"{self.close:.8f}",
            "volume": f"{self.volume:.8f}",
            "trades": str(self.trade_count),
        }


class CandleAggregator:
    """Aggregates trades into OHLCV candles"""

    def __init__(self, interval_seconds: int):
        self.interval_seconds = interval_seconds
        # Active windows: {symbol: CandleWindow}
        self.windows: dict[str, CandleWindow] = {}

    def _align_timestamp(self, ts: int) -> int:
        """Align timestamp to interval boundary (floor)"""
        return (ts // self.interval_seconds) * self.interval_seconds

    def process_trade(self, trade: dict) -> list[dict]:
        """
        Process incoming trade and return completed candles.

        Args:
            trade: market_data payload with ts_ms, symbol, price, trade_qty

        Returns:
            List of completed candle payloads (empty if no candles closed)
        """
        try:
            ts_ms = trade.get("ts_ms")
            symbol = trade.get("symbol")
            price_str = trade.get("price")
            qty_str = trade.get("trade_qty")

            if not all([ts_ms, symbol, price_str, qty_str]):
                return []

            ts_sec = int(ts_ms) // 1000
            price = float(price_str)
            qty = float(qty_str)

            # Check if we need to close existing window
            completed = []
            if symbol in self.windows:
                window = self.windows[symbol]
                if window.is_complete(ts_sec):
                    # Close and emit window
                    payload = window.to_candle_payload()
                    if payload:
                        completed.append(payload)
                    # Remove old window
                    del self.windows[symbol]

            # Get or create window for this trade
            window_start = self._align_timestamp(ts_sec)
            if symbol not in self.windows:
                self.windows[symbol] = CandleWindow(
                    symbol=symbol,
                    start_ts=window_start,
                    interval_seconds=self.interval_seconds,
                )

            # Update window
            self.windows[symbol].update_trade(price, qty, ts_ms)

            return completed

        except (ValueError, TypeError, KeyError):
            return []

    def get_completed_windows(self, current_ts: Optional[int] = None) -> list[dict]:
        """
        Force-close windows that have expired.
        Call this periodically to emit candles even if no new trades arrive.
        """
        if current_ts is None:
            current_ts = int(time.time())

        completed = []
        expired_symbols = []

        for symbol, window in self.windows.items():
            if window.is_complete(current_ts):
                payload = window.to_candle_payload()
                if payload:
                    completed.append(payload)
                expired_symbols.append(symbol)

        # Remove expired windows
        for symbol in expired_symbols:
            del self.windows[symbol]

        return completed
