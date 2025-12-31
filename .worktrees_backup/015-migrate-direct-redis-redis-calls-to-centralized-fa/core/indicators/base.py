"""
Base Indicator Protocol (Issue #204)

Abstrakte Basis für alle technischen Indikatoren.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from collections import deque


class Indicator(ABC):
    """
    Basis-Klasse für alle technischen Indikatoren.

    Alle Indikatoren sind streaming-fähig:
    - update() fügt neuen Wert hinzu
    - value gibt aktuellen Indikator-Wert zurück
    - is_ready zeigt an, ob genug Daten vorhanden sind
    """

    def __init__(self, period: int, name: str = "indicator"):
        if period <= 0:
            raise ValueError("period must be positive")
        self._period = period
        self._name = name
        self._values: deque = deque(maxlen=period)
        self._result: Optional[float] = None

    @property
    def name(self) -> str:
        """Indikator-Name."""
        return self._name

    @property
    def period(self) -> int:
        """Berechnungs-Periode."""
        return self._period

    @property
    def is_ready(self) -> bool:
        """True wenn genug Daten für Berechnung vorhanden."""
        return len(self._values) >= self._period

    @property
    def value(self) -> Optional[float]:
        """Aktueller Indikator-Wert (None wenn nicht ready)."""
        return self._result if self.is_ready else None

    @abstractmethod
    def update(self, price: float) -> Optional[float]:
        """
        Fügt neuen Preis hinzu und berechnet Indikator.

        Args:
            price: Neuer Preis-Wert

        Returns:
            Aktueller Indikator-Wert oder None
        """
        pass

    def reset(self) -> None:
        """Setzt Indikator zurück."""
        self._values.clear()
        self._result = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(period={self._period})"
