"""
Technical Indicators Library (Issue #204)

Wiederverwendbare, streaming-fähige Indikatoren für Signal-Generierung.

Usage:
    from core.indicators import EMA, RSI, MACD, BollingerBands

    ema = EMA(period=20)
    for price in prices:
        ema.update(price)
        if ema.is_ready:
            print(ema.value)
"""

from core.indicators.base import Indicator
from core.indicators.trend import EMA, SMA
from core.indicators.momentum import RSI
from core.indicators.volatility import BollingerBands, ATR
from core.indicators.composite import MACD

__all__ = [
    "Indicator",
    "EMA",
    "SMA",
    "RSI",
    "BollingerBands",
    "ATR",
    "MACD",
]

__version__ = "0.1.0"
