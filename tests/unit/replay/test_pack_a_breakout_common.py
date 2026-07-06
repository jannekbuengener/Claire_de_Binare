"""Unit tests for Pack-A breakout helpers."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    ENTRY_CHANNEL_BARS,
    ONE_MINUTE_MS,
    build_trend_gate_series,
    compute_donchian_channels,
    cooldown_allows_entry,
    donchian_warmup_candles,
    validate_pack_a_candle_series,
)


def _candle(ts_ms: int, close: float, *, high: float | None = None, low: float | None = None) -> dict:
    return {
        "symbol": "BTCUSDT",
        "ts_ms": ts_ms,
        "open": close,
        "high": high if high is not None else close + 1,
        "low": low if low is not None else close - 1,
        "close": close,
        "volume": 1.0,
        "regime_id": 1,
    }


@pytest.mark.unit
def test_donchian_warmup_uses_max_channel() -> None:
    assert donchian_warmup_candles() == max(ENTRY_CHANNEL_BARS, 10)


@pytest.mark.unit
def test_compute_donchian_channels_uses_prior_bars_only() -> None:
    highs = [float(i) for i in range(1, 26)]
    lows = [float(i) - 0.5 for i in range(1, 26)]
    upper, lower = compute_donchian_channels(
        highs, lows, entry_channel_bars=5, exit_channel_bars=3
    )
    assert upper[5] == max(highs[0:5])
    assert lower[3] == min(lows[0:3])
    assert upper[4] is None


@pytest.mark.unit
def test_cooldown_blocks_rapid_reentry() -> None:
    assert cooldown_allows_entry(0, None, min_minutes_between_entries=30)
    assert not cooldown_allows_entry(
        10 * ONE_MINUTE_MS, 0, min_minutes_between_entries=30
    )


@pytest.mark.unit
def test_validate_pack_a_candle_series_rejects_bad_cadence() -> None:
    candles = [
        _candle(0, 100.0),
        _candle(ONE_MINUTE_MS + 1, 101.0),
    ]
    with pytest.raises(ValueError, match="1m cadence"):
        validate_pack_a_candle_series(candles)


@pytest.mark.unit
def test_trend_gate_requires_completed_5m_bars() -> None:
    ts_values = [i * ONE_MINUTE_MS for i in range(30)]
    closes = [100.0 + i * 0.1 for i in range(30)]
    gate = build_trend_gate_series(ts_values, closes, trend_ema_period_5m=3)
    assert gate[0] is None
    assert any(value is not None for value in gate)
