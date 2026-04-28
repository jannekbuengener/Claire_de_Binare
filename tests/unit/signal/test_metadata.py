"""Unit tests for signal metadata wiring."""

import pytest

from services.signal.config import SignalConfig
from services.signal.models import Signal
from services.signal.service import (
    _build_config_hash,
    _build_runtime_config_snapshot,
    _build_signal_metadata,
)


def _primary_breakout_config(*, bot_id: str | None = "bot-1") -> SignalConfig:
    return SignalConfig(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        bot_id=bot_id,
        entry_lookback_minutes=240,
        exit_lookback_minutes=120,
        breakout_buffer=0.0005,
        min_minutes_between_entries=60,
        trade_side_mode="long_only",
    )


@pytest.mark.unit
def test_build_runtime_config_snapshot_contains_expected_fields() -> None:
    config = _primary_breakout_config()

    assert _build_runtime_config_snapshot(config) == {
        "strategy_id": "primary_breakout_v1",
        "symbol": "BTCUSDT",
        "bot_id": "bot-1",
        "entry_lookback_minutes": 240,
        "exit_lookback_minutes": 120,
        "breakout_buffer": 0.0005,
        "min_minutes_between_entries": 60,
        "trade_side_mode": "long_only",
    }


@pytest.mark.unit
def test_build_runtime_config_snapshot_normalizes_missing_bot_id_to_empty_string() -> None:
    config = _primary_breakout_config(bot_id=None)

    assert _build_runtime_config_snapshot(config)["bot_id"] == ""


@pytest.mark.unit
def test_build_config_hash_is_deterministic() -> None:
    snapshot_a = {
        "strategy_id": "primary_breakout_v1",
        "symbol": "BTCUSDT",
        "bot_id": "bot-1",
        "entry_lookback_minutes": 240,
        "exit_lookback_minutes": 120,
        "breakout_buffer": 0.0005,
        "min_minutes_between_entries": 60,
        "trade_side_mode": "long_only",
    }
    snapshot_b = {
        "trade_side_mode": "long_only",
        "min_minutes_between_entries": 60,
        "breakout_buffer": 0.0005,
        "exit_lookback_minutes": 120,
        "entry_lookback_minutes": 240,
        "bot_id": "bot-1",
        "symbol": "BTCUSDT",
        "strategy_id": "primary_breakout_v1",
    }

    assert _build_config_hash(snapshot_a) == _build_config_hash(snapshot_b)


@pytest.mark.unit
def test_build_config_hash_is_deterministic_with_empty_bot_id() -> None:
    snapshot = _build_runtime_config_snapshot(_primary_breakout_config(bot_id=None))

    assert snapshot["bot_id"] == ""
    assert _build_config_hash(snapshot) == _build_config_hash(dict(snapshot))


@pytest.mark.unit
def test_build_signal_metadata_uses_existing_signal_fields() -> None:
    config = _primary_breakout_config()
    config_snapshot = _build_runtime_config_snapshot(config)
    config_hash = _build_config_hash(config_snapshot)
    signal = Signal(
        signal_id="sig-1",
        strategy_id="paper",
        bot_id="bot-1",
        symbol="BTCUSDT",
        side="BUY",
        timestamp=1700000000,
        ts_ms=1700000000123,
        price=50000.0,
        pct_change=3.1,
        pct_change_15m=3.1,
        volume_15m=1234.5,
        reason="Momentum breakout",
    )

    metadata = _build_signal_metadata(
        signal,
        config_snapshot=config_snapshot,
        config_hash=config_hash,
    )

    assert metadata == {
        "strategy_id": "paper",
        "bot_id": "bot-1",
        "signal_reason": "Momentum breakout",
        "signal_inputs": {
            "price": 50000.0,
            "pct_change": 3.1,
            "pct_change_15m": 3.1,
            "volume_15m": 1234.5,
        },
        "timing": {
            "signal_ts_ms": 1700000000123,
        },
        "config_snapshot": config_snapshot,
        "config_hash": config_hash,
    }
