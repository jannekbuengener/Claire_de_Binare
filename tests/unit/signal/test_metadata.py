"""
Unit-Tests: Signal Phase-1 Metadata
Issue #1488
"""

import sys
from pathlib import Path

import pytest

services_path = Path(__file__).parent.parent.parent.parent / "services" / "signal"
if str(services_path) not in sys.path:
    sys.path.insert(0, str(services_path))

from models import Signal  # noqa: E402


@pytest.mark.unit
def test_signal_metadata_populated():
    """Signal-Payload enthält metadata mit allen Phase-1-Feldern."""
    sig = Signal(
        signal_id="sig-abc",
        symbol="BTCUSDT",
        side="BUY",
        strategy_id="momentum_v1",
        bot_id="bot-1",
        reason="Momentum: +1.23%",
        price=50000.0,
        pct_change=1.23,
        pct_change_15m=0.5,
        volume_15m=200.0,
        ts_ms=1700000000000,
    )
    sig.metadata = {
        "strategy_id": sig.strategy_id,
        "bot_id": sig.bot_id,
        "signal_reason": sig.reason,
        "signal_inputs": {
            "price": sig.price,
            "pct_change": sig.pct_change,
            "pct_change_15m": sig.pct_change_15m,
            "volume_15m": sig.volume_15m,
        },
        "timing": {"signal_ts_ms": sig.ts_ms},
    }

    payload = sig.to_dict()

    assert "metadata" in payload
    meta = payload["metadata"]
    assert meta["strategy_id"] == "momentum_v1"
    assert meta["bot_id"] == "bot-1"
    assert meta["signal_reason"] == "Momentum: +1.23%"
    assert meta["signal_inputs"]["price"] == 50000.0
    assert meta["signal_inputs"]["pct_change"] == 1.23
    assert meta["signal_inputs"]["pct_change_15m"] == 0.5
    assert meta["signal_inputs"]["volume_15m"] == 200.0
    assert meta["timing"]["signal_ts_ms"] == 1700000000000


@pytest.mark.unit
def test_signal_metadata_none_not_emitted():
    """Signal ohne metadata → kein metadata-Key im to_dict()."""
    sig = Signal(symbol="BTCUSDT", side="BUY")
    payload = sig.to_dict()
    assert "metadata" not in payload


@pytest.mark.unit
def test_signal_metadata_no_null_inputs():
    """Fehlende optionale Inputs werden aus signal_inputs ausgelassen, nicht erfunden."""
    sig = Signal(
        signal_id="sig-xyz",
        symbol="ETHUSDT",
        side="BUY",
        price=2000.0,
        ts_ms=1700000001000,
    )
    # pct_change_15m und volume_15m fehlen
    _signal_inputs = {
        k: v
        for k, v in {
            "price": sig.price,
            "pct_change": sig.pct_change,
            "pct_change_15m": sig.pct_change_15m,
            "volume_15m": sig.volume_15m,
        }.items()
        if v is not None
    }
    sig.metadata = {
        "strategy_id": sig.strategy_id,
        "bot_id": sig.bot_id,
        "signal_reason": sig.reason,
        "signal_inputs": _signal_inputs,
        "timing": {"signal_ts_ms": sig.ts_ms},
    }

    payload = sig.to_dict()
    inputs = payload["metadata"]["signal_inputs"]

    assert "price" in inputs
    assert "pct_change" not in inputs       # war None
    assert "pct_change_15m" not in inputs   # war None
    assert "volume_15m" not in inputs       # war None
