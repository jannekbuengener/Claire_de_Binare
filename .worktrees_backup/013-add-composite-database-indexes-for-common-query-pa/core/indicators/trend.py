"""
Trend Indicators (Issue #204)

- SMA: Simple Moving Average
- EMA: Exponential Moving Average
"""

from typing import Optional
from collections import deque

from core.indicators.base import Indicator


class SMA(Indicator):
    """
    Simple Moving Average.

    SMA = Summe(Preise) / Periode

    Usage:
        sma = SMA(period=20)
        sma.update(100.0)
        if sma.is_ready:
            print(sma.value)
    """

    def __init__(self, period: int):
        super().__init__(period, name=f"SMA({period})")
        self._sum: float = 0.0

    def update(self, price: float) -> Optional[float]:
        """Fügt Preis hinzu und berechnet SMA."""
        # Bei vollem Buffer: alten Wert abziehen
        if len(self._values) == self._period:
            self._sum -= self._values[0]

        self._values.append(price)
        self._sum += price

        if self.is_ready:
            self._result = self._sum / self._period
            return self._result
        return None

    def reset(self) -> None:
        super().reset()
        self._sum = 0.0


class EMA(Indicator):
    """
    Exponential Moving Average.

    EMA = Preis * k + EMA_prev * (1 - k)
    wobei k = 2 / (Periode + 1)

    Reagiert schneller auf Preisänderungen als SMA.

    Usage:
        ema = EMA(period=12)
        ema.update(100.0)
        if ema.is_ready:
            print(ema.value)
    """

    def __init__(self, period: int):
        super().__init__(period, name=f"EMA({period})")
        self._multiplier = 2.0 / (period + 1)
        self._initialized = False

    def update(self, price: float) -> Optional[float]:
        """Fügt Preis hinzu und berechnet EMA."""
        self._values.append(price)

        if not self.is_ready:
            return None

        if not self._initialized:
            # Erste EMA = SMA der ersten N Werte
            self._result = sum(self._values) / self._period
            self._initialized = True
        else:
            # EMA = Preis * k + EMA_prev * (1-k)
            self._result = (price * self._multiplier +
                           self._result * (1 - self._multiplier))

        return self._result

    def reset(self) -> None:
        super().reset()
        self._initialized = False
