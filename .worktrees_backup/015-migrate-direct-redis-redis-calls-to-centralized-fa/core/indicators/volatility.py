"""
Volatility Indicators (Issue #204)

- BollingerBands: Volatilitäts-basierte Bänder
- ATR: Average True Range
"""

from typing import Optional, NamedTuple
from collections import deque
import math

from core.indicators.base import Indicator


class BollingerResult(NamedTuple):
    """Bollinger Bands Ergebnis."""
    upper: float
    middle: float
    lower: float
    bandwidth: float  # (upper - lower) / middle


class BollingerBands(Indicator):
    """
    Bollinger Bands.

    - Mittleres Band: SMA(period)
    - Oberes Band: SMA + (std_dev_multiplier * StdDev)
    - Unteres Band: SMA - (std_dev_multiplier * StdDev)

    Klassische Interpretation:
    - Preis nahe oberem Band: Überkauft
    - Preis nahe unterem Band: Überverkauft
    - Enge Bänder: Niedrige Volatilität (Ausbruch möglich)

    Usage:
        bb = BollingerBands(period=20, std_dev=2.0)
        bb.update(100.0)
        if bb.is_ready:
            bands = bb.bands
            print(f"Upper: {bands.upper}, Middle: {bands.middle}, Lower: {bands.lower}")
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(period, name=f"BB({period},{std_dev})")
        self._std_dev_mult = std_dev
        self._bands: Optional[BollingerResult] = None

    def update(self, price: float) -> Optional[float]:
        """Fügt Preis hinzu und berechnet Bollinger Bands."""
        self._values.append(price)

        if not self.is_ready:
            return None

        # SMA berechnen
        values = list(self._values)
        sma = sum(values) / self._period

        # Standardabweichung berechnen
        variance = sum((x - sma) ** 2 for x in values) / self._period
        std_dev = math.sqrt(variance)

        # Bänder berechnen
        upper = sma + (self._std_dev_mult * std_dev)
        lower = sma - (self._std_dev_mult * std_dev)
        bandwidth = (upper - lower) / sma if sma > 0 else 0

        self._bands = BollingerResult(
            upper=upper,
            middle=sma,
            lower=lower,
            bandwidth=bandwidth
        )
        self._result = sma  # Middle band als Hauptwert

        return self._result

    @property
    def bands(self) -> Optional[BollingerResult]:
        """Alle drei Bänder als Tuple."""
        return self._bands if self.is_ready else None

    @property
    def upper(self) -> Optional[float]:
        """Oberes Band."""
        return self._bands.upper if self._bands else None

    @property
    def lower(self) -> Optional[float]:
        """Unteres Band."""
        return self._bands.lower if self._bands else None

    @property
    def bandwidth(self) -> Optional[float]:
        """Bandbreite (Volatilitäts-Maß)."""
        return self._bands.bandwidth if self._bands else None

    def reset(self) -> None:
        super().reset()
        self._bands = None


class ATR(Indicator):
    """
    Average True Range.

    True Range = max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )

    ATR = Wilder's Smoothed Average of True Range

    Misst Volatilität unabhängig von Preis-Richtung.

    Usage:
        atr = ATR(period=14)
        atr.update_ohlc(high=105, low=95, close=100)
        if atr.is_ready:
            print(f"ATR: {atr.value}")
    """

    def __init__(self, period: int = 14):
        super().__init__(period, name=f"ATR({period})")
        self._prev_close: Optional[float] = None
        self._true_ranges: deque = deque(maxlen=period)
        self._initialized = False

    def update_ohlc(
        self,
        high: float,
        low: float,
        close: float
    ) -> Optional[float]:
        """
        Fügt OHLC-Daten hinzu und berechnet ATR.

        Args:
            high: Höchster Preis
            low: Niedrigster Preis
            close: Schlusskurs
        """
        if self._prev_close is None:
            self._prev_close = close
            return None

        # True Range berechnen
        tr1 = high - low
        tr2 = abs(high - self._prev_close)
        tr3 = abs(low - self._prev_close)
        true_range = max(tr1, tr2, tr3)

        self._true_ranges.append(true_range)
        self._prev_close = close
        self._values.append(true_range)

        if len(self._true_ranges) < self._period:
            return None

        if not self._initialized:
            # Erste ATR = Durchschnitt der True Ranges
            self._result = sum(self._true_ranges) / self._period
            self._initialized = True
        else:
            # Wilder's Smoothing
            self._result = (self._result * (self._period - 1) + true_range) / self._period

        return self._result

    def update(self, price: float) -> Optional[float]:
        """
        Simplified update mit nur Close-Preis.

        Verwendet Close als High und Low (approximiert).
        Für genaue ATR: update_ohlc() verwenden.
        """
        return self.update_ohlc(high=price, low=price, close=price)

    def reset(self) -> None:
        super().reset()
        self._prev_close = None
        self._true_ranges.clear()
        self._initialized = False
