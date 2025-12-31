"""
Composite Indicators (Issue #204)

- MACD: Moving Average Convergence Divergence
"""

from typing import Optional, NamedTuple

from core.indicators.base import Indicator
from core.indicators.trend import EMA


class MACDResult(NamedTuple):
    """MACD Ergebnis."""
    macd: float       # MACD Linie
    signal: float     # Signal Linie
    histogram: float  # Histogramm (MACD - Signal)


class MACD(Indicator):
    """
    Moving Average Convergence Divergence.

    - MACD Linie: EMA(fast) - EMA(slow)
    - Signal Linie: EMA(MACD, signal_period)
    - Histogramm: MACD - Signal

    Klassische Interpretation:
    - MACD kreuzt Signal von unten: Bullish (Kaufsignal)
    - MACD kreuzt Signal von oben: Bearish (Verkaufssignal)
    - Histogramm wechselt Vorzeichen: Trendwechsel

    Default: 12/26/9 (Standard-Parameter)

    Usage:
        macd = MACD()  # 12, 26, 9
        for price in prices:
            macd.update(price)
            if macd.is_ready:
                result = macd.result
                if result.histogram > 0:
                    print("Bullish")
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        # Period = slow_period (längste Wartezeit)
        super().__init__(slow_period, name=f"MACD({fast_period},{slow_period},{signal_period})")

        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period

        self._fast_ema = EMA(fast_period)
        self._slow_ema = EMA(slow_period)
        self._signal_ema = EMA(signal_period)

        self._macd_result: Optional[MACDResult] = None
        self._prev_histogram: Optional[float] = None

    def update(self, price: float) -> Optional[float]:
        """Fügt Preis hinzu und berechnet MACD."""
        self._fast_ema.update(price)
        self._slow_ema.update(price)

        # Dummy für is_ready
        self._values.append(price)

        # Beide EMAs müssen ready sein
        if not self._slow_ema.is_ready:
            return None

        # MACD Linie berechnen
        macd_line = self._fast_ema.value - self._slow_ema.value

        # Signal Linie berechnen
        self._signal_ema.update(macd_line)

        if not self._signal_ema.is_ready:
            return None

        signal_line = self._signal_ema.value
        histogram = macd_line - signal_line

        self._prev_histogram = (
            self._macd_result.histogram if self._macd_result else None
        )

        self._macd_result = MACDResult(
            macd=macd_line,
            signal=signal_line,
            histogram=histogram
        )
        self._result = macd_line

        return self._result

    @property
    def is_ready(self) -> bool:
        """True wenn MACD und Signal bereit sind."""
        return self._macd_result is not None

    @property
    def result(self) -> Optional[MACDResult]:
        """Vollständiges MACD Ergebnis."""
        return self._macd_result

    @property
    def histogram(self) -> Optional[float]:
        """MACD Histogramm."""
        return self._macd_result.histogram if self._macd_result else None

    @property
    def is_bullish_crossover(self) -> bool:
        """True wenn MACD gerade Signal von unten kreuzt."""
        if self._macd_result is None or self._prev_histogram is None:
            return False
        return self._prev_histogram < 0 and self._macd_result.histogram > 0

    @property
    def is_bearish_crossover(self) -> bool:
        """True wenn MACD gerade Signal von oben kreuzt."""
        if self._macd_result is None or self._prev_histogram is None:
            return False
        return self._prev_histogram > 0 and self._macd_result.histogram < 0

    def reset(self) -> None:
        super().reset()
        self._fast_ema.reset()
        self._slow_ema.reset()
        self._signal_ema.reset()
        self._macd_result = None
        self._prev_histogram = None
