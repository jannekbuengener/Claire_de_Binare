"""Injectable clock for deterministic timeout/budget checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return timezone-aware UTC datetime."""


@dataclass
class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass
class FrozenClock:
    """Deterministic clock for tests and dry-run digests."""

    instant: datetime

    def now(self) -> datetime:
        if self.instant.tzinfo is None:
            return self.instant.replace(tzinfo=timezone.utc)
        return self.instant.astimezone(timezone.utc)

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self.instant = self.now() + timedelta(seconds=seconds)
