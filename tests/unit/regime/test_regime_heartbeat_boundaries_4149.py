"""#4149: Regime heartbeat boundary re-emit contract."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.regime.models import Candle
from services.regime.service import RegimeService

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _fill_trend_state(service: RegimeService, *, close: float = 100.0) -> Candle:
    """Warm indicators and confirm TREND (ADX high, ATR/close below threshold)."""
    service.config.atr_high_vol_threshold = 0.05  # 5% — keep relative ATR low
    service.config.adx_trend_threshold = 0.0  # force TREND once ready
    service.config.adx_range_threshold = -1.0
    service.config.confirmation_bars = 1
    last = None
    for i in range(20):
        # Mild range so atr/close << 0.05; rising highs help ADX when threshold is 0.
        c = close + i * 0.01
        last = Candle(
            ts=1_700_000_000 + i,
            symbol="BTCUSDT",
            timeframe="60s",
            open=c,
            high=c + 0.01,
            low=c - 0.01,
            close=c,
            volume=1.0,
        )
        service._derive_regime(last)
    assert last is not None
    return last


def test_heartbeat_boundary_before_on_after(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RegimeService()
    service.config.heartbeat_interval_s = 60
    mock_redis = MagicMock()
    service.redis_client = mock_redis

    clock = {"t": 1_000.0}
    monkeypatch.setattr("services.regime.service.time.time", lambda: clock["t"])

    last = _fill_trend_state(service)
    key = "BTCUSDT:60s:"
    assert service.current_regime[key] == "TREND"
    initial_calls = mock_redis.xadd.call_count
    service.last_emitted_ts[key] = clock["t"]

    # Exactly before timeout: no heartbeat
    clock["t"] = 1_000.0 + 59.0
    service._derive_regime(
        Candle(
            ts=last.ts + 1,
            symbol="BTCUSDT",
            timeframe="60s",
            open=last.close,
            high=last.close + 0.01,
            low=last.close - 0.01,
            close=last.close,
            volume=1.0,
        )
    )
    assert mock_redis.xadd.call_count == initial_calls

    # Exactly on timeout (> interval): heartbeat fires
    clock["t"] = 1_000.0 + 60.0 + 0.001
    service._derive_regime(
        Candle(
            ts=last.ts + 2,
            symbol="BTCUSDT",
            timeframe="60s",
            open=last.close,
            high=last.close + 0.01,
            low=last.close - 0.01,
            close=last.close,
            volume=1.0,
        )
    )
    assert mock_redis.xadd.call_count == initial_calls + 1
