"""#4149: pct_change_15m is a true event-time lookback metric."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_services_signal = Path(__file__).resolve().parents[3] / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from price_buffer import PriceBuffer  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_lookback_pct_change_uses_event_time_window() -> None:
    buffer = PriceBuffer(lookback_minutes=15)
    t0 = 1_700_000_000_000
    buffer.observe("BTCUSDT", 100.0, t0)
    buffer.observe("BTCUSDT", 105.0, t0 + 5 * 60_000)
    pct = buffer.pct_change_lookback(
        "BTCUSDT",
        current_price=110.0,
        now_ms=t0 + 15 * 60_000,
        lookback_minutes=15,
    )
    # Reference must be the price at/before t0 (100), not the mid-window 105.
    assert pct == pytest.approx(10.0, rel=1e-9)


def test_lookback_pct_change_with_price_at_horizon() -> None:
    buffer = PriceBuffer(lookback_minutes=15)
    t0 = 1_700_000_000_000
    buffer.observe("BTCUSDT", 100.0, t0)
    pct = buffer.pct_change_lookback(
        "BTCUSDT",
        current_price=103.0,
        now_ms=t0 + 15 * 60_000,
        lookback_minutes=15,
    )
    assert pct == pytest.approx(3.0, rel=1e-9)


def test_insufficient_history_returns_none() -> None:
    buffer = PriceBuffer(lookback_minutes=15)
    t0 = 1_700_000_000_000
    buffer.observe("BTCUSDT", 100.0, t0)
    assert (
        buffer.pct_change_lookback(
            "BTCUSDT",
            current_price=105.0,
            now_ms=t0 + 60_000,
            lookback_minutes=15,
        )
        is None
    )


def test_out_of_order_event_does_not_silently_invent_value() -> None:
    buffer = PriceBuffer(lookback_minutes=15)
    t0 = 1_700_000_000_000
    buffer.observe("BTCUSDT", 100.0, t0)
    buffer.observe("BTCUSDT", 120.0, t0 + 15 * 60_000)
    # Late old tick must not replace the horizon reference for later now_ms.
    buffer.observe("BTCUSDT", 50.0, t0 + 60_000)
    pct = buffer.pct_change_lookback(
        "BTCUSDT",
        current_price=120.0,
        now_ms=t0 + 15 * 60_000,
        lookback_minutes=15,
    )
    assert pct == pytest.approx(20.0, rel=1e-9)


def test_tick_pct_change_remains_last_tick_semantics() -> None:
    buffer = PriceBuffer(lookback_minutes=15)
    assert buffer.calculate_pct_change("BTCUSDT", 100.0) == 0.0
    assert buffer.calculate_pct_change("BTCUSDT", 102.0) == pytest.approx(2.0)
