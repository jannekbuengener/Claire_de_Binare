"""Unit tests for signal metadata wiring."""

import pytest

from services.signal.models import Signal
from services.signal.service import _build_signal_metadata


@pytest.mark.unit
def test_build_signal_metadata_uses_existing_signal_fields() -> None:
    signal = Signal(
        signal_id="sig-1",
        strategy_id="paper",
        bot_id="bot-1",
        symbol="BTCUSDT",
        side="BUY",
        timestamp=1700000000,
        ts_ms=1700000000123,
        price=50000.0,
        pct_change=0.031,
        pct_change_15m=0.031,
        volume_15m=1234.5,
        reason="Momentum breakout",
    )

    metadata = _build_signal_metadata(signal)

    assert metadata == {
        "strategy_id": "paper",
        "bot_id": "bot-1",
        "signal_reason": "Momentum breakout",
        "signal_inputs": {
            "price": 50000.0,
            "pct_change": 0.031,
            "pct_change_15m": 0.031,
            "volume_15m": 1234.5,
        },
        "timing": {
            "signal_ts_ms": 1700000000123,
        },
    }
