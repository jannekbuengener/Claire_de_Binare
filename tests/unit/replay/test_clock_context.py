"""Unit tests for core.replay.clock_context.

Scope:
  - ReplayClockContext: deterministic ts_ms-based time derivation
  - UtcClockContext: live UTC clock, isolated from replay
  - ClockContextProtocol: structural protocol satisfaction
  - No sleep-based tests; no wall-clock dependency inside replay clock
"""

import re

import pytest

from core.replay.clock_context import (
    ClockContextProtocol,
    ReplayClockContext,
    UtcClockContext,
)
from core.replay.time import created_at_from_ts_ms

_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@pytest.mark.unit
class TestReplayClockContext:
    """Tests for ReplayClockContext determinism and interface."""

    def test_now_ts_ms_returns_event_ts(self) -> None:
        """now_ts_ms() returns the exact ts_ms it was initialised with."""
        clock = ReplayClockContext(ts_ms=1_700_000_000_000)
        assert clock.now_ts_ms() == 1_700_000_000_000

    def test_identical_inputs_identical_now_ts_ms(self) -> None:
        """Identical ts_ms inputs produce identical now_ts_ms() outputs."""
        ts = 1_609_459_200_000  # 2021-01-01T00:00:00.000Z
        c1 = ReplayClockContext(ts_ms=ts)
        c2 = ReplayClockContext(ts_ms=ts)
        assert c1.now_ts_ms() == c2.now_ts_ms()

    def test_identical_inputs_identical_now_iso(self) -> None:
        """Identical ts_ms inputs produce identical now_iso() strings."""
        ts = 1_609_459_200_000
        c1 = ReplayClockContext(ts_ms=ts)
        c2 = ReplayClockContext(ts_ms=ts)
        assert c1.now_iso() == c2.now_iso()

    def test_now_iso_matches_created_at_from_ts_ms(self) -> None:
        """now_iso() output matches created_at_from_ts_ms() for same ts_ms."""
        ts = 1_609_459_200_123
        clock = ReplayClockContext(ts_ms=ts)
        assert clock.now_iso() == created_at_from_ts_ms(ts)

    def test_now_iso_format(self) -> None:
        """now_iso() returns ISO-8601 UTC string with millisecond precision."""
        clock = ReplayClockContext(ts_ms=1_609_459_200_000)
        iso = clock.now_iso()
        assert _ISO_PATTERN.match(iso), f"Unexpected ISO format: {iso!r}"
        assert iso.endswith("Z")

    def test_now_iso_epoch_zero(self) -> None:
        """now_iso() is stable for ts_ms=0 (Unix epoch)."""
        clock = ReplayClockContext(ts_ms=0)
        iso = clock.now_iso()
        assert "1970-01-01" in iso
        assert iso.endswith("Z")

    def test_frozen_immutable(self) -> None:
        """ReplayClockContext is immutable (frozen dataclass)."""
        clock = ReplayClockContext(ts_ms=1_000_000)
        with pytest.raises(Exception):  # FrozenInstanceError
            clock.ts_ms = 999  # type: ignore

    def test_rejects_negative_ts_ms(self) -> None:
        """Raises ValueError for negative ts_ms."""
        with pytest.raises(ValueError, match="ts_ms"):
            ReplayClockContext(ts_ms=-1)

    def test_speedup_factor_stored(self) -> None:
        """Optional speedup_factor is stored as informational metadata."""
        clock = ReplayClockContext(ts_ms=1_000_000, speedup_factor=5.0)
        assert clock.speedup_factor == 5.0
        # now_ts_ms() is unaffected by speedup_factor
        assert clock.now_ts_ms() == 1_000_000

    def test_speedup_factor_none_by_default(self) -> None:
        """speedup_factor defaults to None."""
        clock = ReplayClockContext(ts_ms=1_000_000)
        assert clock.speedup_factor is None

    def test_rejects_zero_speedup_factor(self) -> None:
        """Raises ValueError for speedup_factor=0."""
        with pytest.raises(ValueError, match="speedup_factor"):
            ReplayClockContext(ts_ms=1_000_000, speedup_factor=0.0)

    def test_rejects_negative_speedup_factor(self) -> None:
        """Raises ValueError for negative speedup_factor."""
        with pytest.raises(ValueError, match="speedup_factor"):
            ReplayClockContext(ts_ms=1_000_000, speedup_factor=-1.0)

    def test_now_ts_ms_called_multiple_times_stable(self) -> None:
        """now_ts_ms() called multiple times returns the same value (no mutation)."""
        clock = ReplayClockContext(ts_ms=42_000_000)
        results = [clock.now_ts_ms() for _ in range(5)]
        assert all(r == 42_000_000 for r in results)

    def test_different_ts_ms_different_outputs(self) -> None:
        """Different ts_ms values produce different now_ts_ms() and now_iso()."""
        c1 = ReplayClockContext(ts_ms=1_000_000)
        c2 = ReplayClockContext(ts_ms=2_000_000)
        assert c1.now_ts_ms() != c2.now_ts_ms()
        assert c1.now_iso() != c2.now_iso()


@pytest.mark.unit
class TestUtcClockContext:
    """Tests for UtcClockContext (live UTC clock)."""

    def test_now_ts_ms_positive(self) -> None:
        """now_ts_ms() returns a positive integer (after Unix epoch)."""
        clock = UtcClockContext()
        ts = clock.now_ts_ms()
        assert isinstance(ts, int)
        assert ts > 0

    def test_now_ts_ms_reasonable_range(self) -> None:
        """now_ts_ms() is within a plausible range (year 2020–2040)."""
        clock = UtcClockContext()
        ts = clock.now_ts_ms()
        # 2020-01-01 in ms
        assert ts > 1_577_836_800_000
        # 2040-01-01 in ms
        assert ts < 2_208_988_800_000

    def test_now_iso_format(self) -> None:
        """now_iso() returns ISO-8601 UTC string with millisecond precision."""
        clock = UtcClockContext()
        iso = clock.now_iso()
        assert _ISO_PATTERN.match(iso), f"Unexpected ISO format: {iso!r}"
        assert iso.endswith("Z")

    def test_independent_from_replay_clock(self) -> None:
        """UtcClockContext does not share state with ReplayClockContext."""
        replay_clock = ReplayClockContext(ts_ms=1_000_000)  # distant past
        utc_clock = UtcClockContext()
        # UTC clock should return a much larger value than 1970 + 1000 seconds
        assert utc_clock.now_ts_ms() > replay_clock.now_ts_ms()

    def test_multiple_calls_not_identical(self) -> None:
        """UtcClockContext.now_ts_ms() may return different values on successive calls
        (live clock). We only verify the type contract here — no sleep needed."""
        clock = UtcClockContext()
        ts = clock.now_ts_ms()
        assert isinstance(ts, int)


@pytest.mark.unit
class TestClockContextProtocol:
    """Tests for ClockContextProtocol structural compliance."""

    def test_replay_clock_satisfies_protocol(self) -> None:
        """ReplayClockContext satisfies ClockContextProtocol."""
        clock = ReplayClockContext(ts_ms=1_000_000)
        assert isinstance(clock, ClockContextProtocol)

    def test_utc_clock_satisfies_protocol(self) -> None:
        """UtcClockContext satisfies ClockContextProtocol."""
        clock = UtcClockContext()
        assert isinstance(clock, ClockContextProtocol)

    def test_protocol_usable_as_type_annotation(self) -> None:
        """A function accepting ClockContextProtocol works with both implementations."""

        def get_ts(ctx: ClockContextProtocol) -> int:
            return ctx.now_ts_ms()

        replay = ReplayClockContext(ts_ms=5_000)
        utc = UtcClockContext()
        assert get_ts(replay) == 5_000
        assert isinstance(get_ts(utc), int)

    def test_arbitrary_object_does_not_satisfy_protocol(self) -> None:
        """An object without now_ts_ms/now_iso does not satisfy ClockContextProtocol."""

        class NotAClock:
            pass

        assert not isinstance(NotAClock(), ClockContextProtocol)
