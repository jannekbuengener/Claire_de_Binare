"""#4149: High-Vol regime uses scale-stable ATR/close semantics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.regime.models import ATR_HIGH_VOL_UNIT, Candle, classify_raw_regime
from services.regime.service import RegimeService

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _candle(
    *,
    close: float,
    high: float | None = None,
    low: float | None = None,
    ts: int = 1,
) -> Candle:
    high_v = close if high is None else high
    low_v = close if low is None else low
    return Candle(
        ts=ts,
        symbol="BTCUSDT",
        timeframe="60s",
        open=close,
        high=high_v,
        low=low_v,
        close=close,
        volume=1.0,
    )


def test_identical_relative_volatility_same_class_across_price_levels() -> None:
    """Same ATR/close at price 100 and 60_000 must classify identically."""
    low = classify_raw_regime(
        adx=30.0,
        atr=0.15,
        close=100.0,
        current_regime="UNKNOWN",
        atr_high_vol_threshold=0.001,
        adx_trend_threshold=25.0,
        adx_range_threshold=20.0,
    )
    high = classify_raw_regime(
        adx=30.0,
        atr=90.0,
        close=60_000.0,
        current_regime="UNKNOWN",
        atr_high_vol_threshold=0.001,
        adx_trend_threshold=25.0,
        adx_range_threshold=20.0,
    )
    assert low == high == "HIGH_VOL_CHAOTIC"


@pytest.mark.parametrize(
    ("atr", "close", "expected"),
    [
        (0.0999, 100.0, "TREND"),  # ratio 0.000999 < 0.001
        (0.1, 100.0, "HIGH_VOL_CHAOTIC"),  # exact boundary
        (0.1001, 100.0, "HIGH_VOL_CHAOTIC"),  # above
    ],
)
def test_high_vol_boundary_atr_over_close(
    atr: float, close: float, expected: str
) -> None:
    result = classify_raw_regime(
        adx=30.0,
        atr=atr,
        close=close,
        current_regime="UNKNOWN",
        atr_high_vol_threshold=0.001,
        adx_trend_threshold=25.0,
        adx_range_threshold=20.0,
    )
    assert result == expected


def test_atr_checked_before_adx_trend() -> None:
    """ATR/close high-vol wins even when ADX would otherwise say TREND."""
    result = classify_raw_regime(
        adx=40.0,
        atr=1.0,
        close=100.0,
        current_regime="RANGE",
        atr_high_vol_threshold=0.001,
        adx_trend_threshold=25.0,
        adx_range_threshold=20.0,
    )
    assert result == "HIGH_VOL_CHAOTIC"


def test_non_positive_close_is_unknown_fail_closed() -> None:
    result = classify_raw_regime(
        adx=40.0,
        atr=1.0,
        close=0.0,
        current_regime="TREND",
        atr_high_vol_threshold=0.001,
        adx_trend_threshold=25.0,
        adx_range_threshold=20.0,
    )
    assert result == "UNKNOWN"


def test_service_emits_atr_over_close_unit_marker() -> None:
    service = RegimeService()
    service.config.atr_high_vol_threshold = 0.001
    service.config.confirmation_bars = 1
    mock_redis = MagicMock()
    service.redis_client = mock_redis

    # Build warmup candles with controlled range → ATR/close >= 0.001
    close = 100.0
    candles = []
    for i in range(20):
        # TR ≈ 0.2 → ATR ≈ 0.2 → ratio 0.002
        candles.append(
            _candle(close=close, high=close + 0.1, low=close - 0.1, ts=1_700_000_000 + i)
        )
    for candle in candles:
        service._derive_regime(candle)

    assert mock_redis.xadd.called
    fields = mock_redis.xadd.call_args[0][1]
    assert fields["regime"] == "HIGH_VOL_CHAOTIC"
    assert fields["atr_high_vol_unit"] == ATR_HIGH_VOL_UNIT
    assert float(fields["atr_over_close"]) == pytest.approx(0.002, rel=0.5)
