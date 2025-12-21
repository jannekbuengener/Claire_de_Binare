"""
Clock abstraction for deterministic replay.
Governance: CDB_PSM_POLICY.md (Event-Sourcing, Replay-faehig)

relations:
  role: clock_abstraction
  domain: utility
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - tests/replay/test_deterministic_replay.py
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable, Optional, Protocol


class Clock:
    """Utility clock with deterministic toggle for unit tests."""

    _deterministic: bool = False
    _current_time: float = 0.0

    @classmethod
    def now(cls) -> float:
        """Return a float timestamp; deterministic when enabled."""
        if cls._deterministic:
            return cls._current_time
        return time.time()

    @classmethod
    def set_deterministic(cls, enabled: bool, start_time: float | None = None) -> None:
        """Enable or disable deterministic mode for the utility clock."""
        cls._deterministic = enabled
        if enabled:
            cls._current_time = start_time if start_time is not None else time.time()
        else:
            cls._current_time = time.time()

    @classmethod
    def advance(cls, delta: float) -> float:
        """Advance the deterministic clock by a delta and return the new time."""
        if not cls._deterministic:
            cls._current_time = time.time()
            return cls._current_time
        cls._current_time += delta
        return cls._current_time


class SystemClock:
    """Wall-clock time (UTC)."""

    def now(self) -> datetime:
        return datetime.utcnow()


class FixedClock:
    """Fixed timestamp for deterministic tests and replay."""

    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time

    def set_time(self, new_time: datetime) -> None:
        """Set a new fixed time for test sequences."""
        self._fixed_time = new_time


class ClockProvider(Protocol):
    """Protocol for injectable clock sources."""

    def now(self) -> datetime:
        """Return current UTC time as datetime."""


class ReplayClock:
    """Replay-driven clock that returns a deterministic sequence of timestamps."""

    def __init__(self, timestamps: Iterable[datetime], fallback: Optional[datetime] = None):
        self._iterator = iter(timestamps)
        self._last_time = fallback

    def now(self) -> datetime:
        try:
            self._last_time = next(self._iterator)
        except StopIteration:
            if self._last_time is None:
                raise RuntimeError("ReplayClock has no timestamps and no fallback set")
        return self._last_time


_DEFAULT_CLOCK: ClockProvider = SystemClock()


def set_default_clock(clock: ClockProvider) -> None:
    """Set the global default clock for deterministic replay/testing."""
    global _DEFAULT_CLOCK
    _DEFAULT_CLOCK = clock


def get_default_clock() -> ClockProvider:
    """Get the global default clock instance."""
    return _DEFAULT_CLOCK


def utcnow(clock: Optional[ClockProvider] = None) -> datetime:
    """Return current UTC time using the injected clock (or default)."""
    return (clock or _DEFAULT_CLOCK).now()
