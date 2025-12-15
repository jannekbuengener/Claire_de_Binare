---
relations:
  role: clock_abstraction
  domain: utility
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - tests/replay/test_deterministic_replay.py
---
"""
Clock Abstraction für deterministische Replay.
Governance: CDB_PSM_POLICY.md (Event-Sourcing, Replay-fähig)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class Clock(ABC):
    """Abstract Base Class für Zeit-Abstraktion."""

    @abstractmethod
    def now(self) -> datetime:
        """Liefert aktuelle Zeit."""
        pass


class SystemClock(Clock):
    """Echte System-Zeit (für Produktion)."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock(Clock):
    """Feste Zeit (für deterministische Tests & Replay)."""

    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time

    def set_time(self, new_time: datetime):
        """Setzt neue feste Zeit (für Test-Sequenzen)."""
        self._fixed_time = new_time
