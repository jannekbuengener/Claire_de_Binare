"""
Momentum Indicators (Issue #204)

- RSI: Relative Strength Index
"""

from typing import Optional
from collections import deque

from core.indicators.base import Indicator


class RSI(Indicator):
    """
    Relative Strength Index.

    RSI = 100 - (100 / (1 + RS))
    wobei RS = Avg(Gains) / Avg(Losses)

    Klassische Interpretation:
    - RSI > 70: Überkauft (möglicher Verkauf)
    - RSI < 30: Überverkauft (möglicher Kauf)

    Usage:
        rsi = RSI(period=14)
        for price in prices:
            rsi.update(price)
            if rsi.is_ready:
                if rsi.value < 30:
                    print("Überverkauft - Kaufsignal?")
    """

    def __init__(self, period: int = 14):
        super().__init__(period, name=f"RSI({period})")
        self._prev_price: Optional[float] = None
        self._avg_gain: float = 0.0
        self._avg_loss: float = 0.0
        self._gains: deque = deque(maxlen=period)
        self._losses: deque = deque(maxlen=period)
        self._count: int = 0

    def update(self, price: float) -> Optional[float]:
        """Fügt Preis hinzu und berechnet RSI."""
        if self._prev_price is None:
            self._prev_price = price
            return None

        # Berechne Gain/Loss
        change = price - self._prev_price
        gain = max(0, change)
        loss = max(0, -change)

        self._gains.append(gain)
        self._losses.append(loss)
        self._prev_price = price
        self._count += 1

        # Brauchen period Änderungen (period+1 Preise)
        if self._count < self._period:
            # Dummy-Wert in _values für is_ready check
            self._values.append(price)
            return None

        # Erste RSI: Einfacher Durchschnitt
        if self._count == self._period:
            self._avg_gain = sum(self._gains) / self._period
            self._avg_loss = sum(self._losses) / self._period
            self._values.append(price)
        else:
            # Wilder's Smoothing
            self._avg_gain = (self._avg_gain * (self._period - 1) + gain) / self._period
            self._avg_loss = (self._avg_loss * (self._period - 1) + loss) / self._period

        # RSI Berechnung
        if self._avg_loss == 0:
            self._result = 100.0
        else:
            rs = self._avg_gain / self._avg_loss
            self._result = 100.0 - (100.0 / (1.0 + rs))

        return self._result

    @property
    def is_overbought(self) -> bool:
        """True wenn RSI > 70."""
        return self._result is not None and self._result > 70

    @property
    def is_oversold(self) -> bool:
        """True wenn RSI < 30."""
        return self._result is not None and self._result < 30

    def reset(self) -> None:
        super().reset()
        self._prev_price = None
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._gains.clear()
        self._losses.clear()
        self._count = 0
