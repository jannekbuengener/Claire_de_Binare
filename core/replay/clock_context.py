"""Replay clock context for deterministic replay time handling.

This module provides a narrow time-context abstraction for replay execution:
  - ReplayClockContext: deterministic clock driven by explicit event timestamp
  - UtcClockContext: live UTC clock for non-replay callers (default/production)
  - ClockContextProtocol: structural protocol for type-safe injection

Design rules:
  - ReplayClockContext is frozen and slots-based (deterministic, immutable)
  - No wall-clock calls inside ReplayClockContext (no wall-clock time, no sleep)
  - Identical inputs -> identical outputs (no hidden entropy)
  - UtcClockContext is isolated from replay logic
  - No dependency on core.utils.clock (replay domain stays self-contained)
  - now_iso() derives from ts_ms via core.replay.time.created_at_from_ts_ms

Governance: Issue #1801 (LR-021 ReplayClockContext)

relations:
  role: replay_clock_context_definition
  domain: replay
  upstream:
    - core.replay.time
  downstream:
    - core.replay.replay_contracts
    - services/validation/ (potential future use)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from core.replay.time import created_at_from_ts_ms


@runtime_checkable
class ClockContextProtocol(Protocol):
    """Structural protocol for injectable clock contexts.

    Both ReplayClockContext and UtcClockContext satisfy this protocol.
    Downstream consumers (replay runner, event loop) should accept
    ClockContextProtocol for determinism-safe injection.
    """

    def now_ts_ms(self) -> int:
        """Return current time as milliseconds since Unix epoch."""
        pass

    def now_iso(self) -> str:
        """Return current time as UTC ISO-8601 string with millisecond precision."""
        pass


@dataclass(frozen=True, slots=True)
class ReplayClockContext:
    """Deterministic clock context driven by an explicit replay event timestamp.

    Time is derived exclusively from ts_ms — no wall-clock calls are made.
    Identical ts_ms inputs always produce identical now_ts_ms() and now_iso() outputs.

    Usage:
        clock = ReplayClockContext(ts_ms=envelope.ts_ms)
        ts = clock.now_ts_ms()   # always == ts_ms
        iso = clock.now_iso()    # deterministic ISO string from ts_ms

    Optional:
        speedup_factor: metadata hint for future accelerated replay support.
        It does NOT affect time output — it is a diagnostic/informational field only.
        The replay scheduler (not yet implemented) may read this field to control
        event pacing, but ReplayClockContext itself has no scheduling logic.
    """

    ts_ms: int
    """Event timestamp in milliseconds since Unix epoch (replay time source)."""

    speedup_factor: Optional[float] = None
    """Optional replay speedup hint (e.g., 2.0 = 2x accelerated replay).

    This field is informational only. ReplayClockContext does not implement
    scheduling or sleep-based pacing. A future replay scheduler may read this.
    Must be > 0 if set.
    """

    def __post_init__(self) -> None:
        if self.ts_ms < 0:
            raise ValueError(f"ts_ms must be non-negative, got {self.ts_ms!r}")
        if self.speedup_factor is not None and self.speedup_factor <= 0:
            raise ValueError(
                f"speedup_factor must be > 0 if set, got {self.speedup_factor!r}"
            )

    def now_ts_ms(self) -> int:
        """Return replay event timestamp in milliseconds.

        Always returns self.ts_ms. No wall-clock dependency.
        """
        return self.ts_ms

    def now_iso(self) -> str:
        """Return replay event time as UTC ISO-8601 string with millisecond precision.

        Derived deterministically from ts_ms via core.replay.time.created_at_from_ts_ms.
        Identical ts_ms always produces identical ISO string.
        """
        return created_at_from_ts_ms(self.ts_ms)


class UtcClockContext:
    """Live UTC clock context for non-replay callers.

    Uses wall-clock time (time.time()). Intentionally NOT frozen — this
    is a live clock that returns different values on successive calls.

    This class is isolated from ReplayClockContext: no shared state, no shared
    base class. It exists as a clear production-side alternative to inject
    alongside ReplayClockContext in contexts that accept ClockContextProtocol.

    Usage:
        clock = UtcClockContext()
        ts = clock.now_ts_ms()   # current UTC epoch-ms
        iso = clock.now_iso()    # current UTC ISO string
    """

    def now_ts_ms(self) -> int:
        """Return current UTC time as milliseconds since Unix epoch."""
        return int(time.time() * 1000)

    def now_iso(self) -> str:
        """Return current UTC time as ISO-8601 string with millisecond precision.

        Delegates to created_at_from_ts_ms for consistent formatting with
        ReplayClockContext.now_iso().
        """
        return created_at_from_ts_ms(self.now_ts_ms())
