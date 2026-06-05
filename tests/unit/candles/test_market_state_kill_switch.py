"""Unit tests for CANDLE_WRITE_MARKET_STATE kill-switch (Issue #1201 Cutover prep).

Verifies that:
- default (true) → _update_market_state called after candle emission
- kill-switch false → _update_market_state NOT called (no market_state write)
- garbage env value → treated as true (fail-safe)
- candle emission itself is unaffected by the kill-switch in either case
"""

import copy
import os
from unittest.mock import MagicMock, patch

import pytest

# Required before importing the service
os.environ.setdefault("CANDLE_INTERVAL_SECONDS", "60")

from services.candles.service import CandleService


def _make_service(write_market_state: bool) -> CandleService:
    """Create CandleService with kill-switch configured and Redis mocked.

    Uses a copy of the config to avoid mutating the module-level singleton.
    """
    service = CandleService()
    service.config = copy.copy(service.config)  # isolate from global singleton
    service.config.write_market_state = write_market_state
    service.redis_client = MagicMock()
    service.redis_client.xadd.return_value = None
    return service


_CANDLE = {
    "symbol": "BTCUSDT",
    "ts": "1700000000",
    "open": "50000",
    "high": "51000",
    "low": "49000",
    "close": "50500",
    "volume": "1.0",
    "trades": "10",
    "timeframe": "60s",
}


# ─── Kill-switch behaviour ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_kill_switch_false_skips_market_state_write():
    """CANDLE_WRITE_MARKET_STATE=false → _update_market_state must NOT be called."""
    service = _make_service(write_market_state=False)
    with patch.object(service, "_update_market_state") as mock_update:
        service._emit_candle(_CANDLE.copy())
    mock_update.assert_not_called()


@pytest.mark.unit
def test_kill_switch_true_calls_market_state_write():
    """CANDLE_WRITE_MARKET_STATE=true → _update_market_state called with symbol."""
    service = _make_service(write_market_state=True)
    with patch.object(service, "_update_market_state") as mock_update:
        service._emit_candle(_CANDLE.copy())
    mock_update.assert_called_once_with("BTCUSDT", 1700000000)


@pytest.mark.unit
def test_candle_emitted_regardless_of_kill_switch():
    """Candle stream write (xadd) must happen in both kill-switch states."""
    for enabled in (True, False):
        service = _make_service(write_market_state=enabled)
        with patch.object(service, "_update_market_state"):
            service._emit_candle(_CANDLE.copy())
        service.redis_client.xadd.assert_called_once()


@pytest.mark.unit
def test_kill_switch_false_no_market_state_on_symbol_absent():
    """No crash and no write when candle has no symbol field."""
    service = _make_service(write_market_state=False)
    candle_no_symbol = {k: v for k, v in _CANDLE.items() if k != "symbol"}
    with patch.object(service, "_update_market_state") as mock_update:
        service._emit_candle(candle_no_symbol)
    mock_update.assert_not_called()


# ─── Config default ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_default_write_market_state_is_true():
    """Default (no env var) → write_market_state=True (kill-switch OFF)."""
    service = CandleService()
    assert service.config.write_market_state is True


@pytest.mark.unit
def test_config_false_string_disables_write():
    """CANDLE_WRITE_MARKET_STATE='false' (string) → write_market_state=False."""
    original = os.environ.get("CANDLE_WRITE_MARKET_STATE")
    try:
        os.environ["CANDLE_WRITE_MARKET_STATE"] = "false"
        # Re-parse env vars by re-importing config directly
        import importlib
        import services.candles.config as cfg_mod

        importlib.reload(cfg_mod)
        assert cfg_mod.config.write_market_state is False
    finally:
        if original is None:
            os.environ.pop("CANDLE_WRITE_MARKET_STATE", None)
        else:
            os.environ["CANDLE_WRITE_MARKET_STATE"] = original
        importlib.reload(cfg_mod)


@pytest.mark.unit
def test_config_false_case_insensitive():
    """CANDLE_WRITE_MARKET_STATE='FALSE' (uppercase) → write_market_state=False."""
    original = os.environ.get("CANDLE_WRITE_MARKET_STATE")
    try:
        os.environ["CANDLE_WRITE_MARKET_STATE"] = "FALSE"
        import importlib
        import services.candles.config as cfg_mod

        importlib.reload(cfg_mod)
        assert cfg_mod.config.write_market_state is False
    finally:
        if original is None:
            os.environ.pop("CANDLE_WRITE_MARKET_STATE", None)
        else:
            os.environ["CANDLE_WRITE_MARKET_STATE"] = original
        importlib.reload(cfg_mod)


@pytest.mark.unit
def test_config_garbage_value_defaults_to_true():
    """CANDLE_WRITE_MARKET_STATE='yes' (not 'false') → write_market_state=True (fail-safe)."""
    original = os.environ.get("CANDLE_WRITE_MARKET_STATE")
    try:
        os.environ["CANDLE_WRITE_MARKET_STATE"] = "yes"
        import importlib
        import services.candles.config as cfg_mod

        importlib.reload(cfg_mod)
        assert cfg_mod.config.write_market_state is True
    finally:
        if original is None:
            os.environ.pop("CANDLE_WRITE_MARKET_STATE", None)
        else:
            os.environ["CANDLE_WRITE_MARKET_STATE"] = original
        importlib.reload(cfg_mod)


# ─── Stimulus fixture freshness (#3021) ─────────────────────────────────────────


@pytest.mark.unit
def test_stimulus_fixture_uses_wall_clock_last_tick():
    """When last_tick_source=stimulus_fixture, _update_market_state must use
    wall-clock last_tick_ts_ms to preserve freshness for cdb_risk RC_004."""
    service = _make_service(write_market_state=True)
    service.aggregator.last_tick_ts_ms["BTCUSDT"] = 1700000000000  # historical
    service.aggregator.last_tick_source["BTCUSDT"] = "stimulus_fixture"

    from unittest.mock import patch
    import time

    wall_clock = 1780702600000

    # Simulate 6 candles in the stream so market_state is not skipped
    candles = [
        {"symbol": "BTCUSDT", "close": "50000", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50001", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50002", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50003", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50004", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50005", "ts": str(wall_clock // 1000)},
    ]
    xrevrange_result = [(f"{wall_clock}-{i}", c) for i, c in enumerate(candles)]
    service.redis_client.xrevrange.return_value = xrevrange_result

    # Mock regime lookup to avoid Redis regime stream dependency
    with patch.object(service, "_lookup_regime_id", return_value=0):
        with patch.object(time, "time", return_value=wall_clock / 1000.0):
            service._update_market_state("BTCUSDT", 1700000000000)

    # Extract the payload that was setex'd into Redis
    # setex(key, ttl, value) → args[0]=key, args[1]=ttl, args[2]=json_string
    args, _kwargs = service.redis_client.setex.call_args
    payload = __import__("json").loads(args[2])

    # last_tick_ts_ms must be wall-clock, not the historical aggregator value
    assert payload["last_tick_ts_ms"] == wall_clock


@pytest.mark.unit
def test_non_stimulus_source_preserves_aggregator_last_tick():
    """When last_tick_source is not stimulus_fixture, _update_market_state must use
    the aggregator's historical last_tick_ts_ms (existing behaviour, no regression)."""
    service = _make_service(write_market_state=True)
    service.aggregator.last_tick_ts_ms["BTCUSDT"] = 1700000000000  # historical
    service.aggregator.last_tick_source["BTCUSDT"] = "live_exchange"

    from unittest.mock import patch
    import time

    wall_clock = 1780702600000

    candles = [
        {"symbol": "BTCUSDT", "close": "50000", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50001", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50002", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50003", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50004", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50005", "ts": str(wall_clock // 1000)},
    ]
    xrevrange_result = [(f"{wall_clock}-{i}", c) for i, c in enumerate(candles)]
    service.redis_client.xrevrange.return_value = xrevrange_result

    with patch.object(service, "_lookup_regime_id", return_value=0):
        with patch.object(time, "time", return_value=wall_clock / 1000.0):
            service._update_market_state("BTCUSDT", 1700000000000)

    args, _kwargs = service.redis_client.setex.call_args
    payload = __import__("json").loads(args[2])

    # last_tick_ts_ms must still be the aggregator's historical value
    assert payload["last_tick_ts_ms"] == 1700000000000


@pytest.mark.unit
def test_stimulus_fixture_preserves_other_market_state_fields():
    """The wall-clock override for last_tick_ts_ms must not change other fields."""
    service = _make_service(write_market_state=True)
    service.aggregator.last_tick_ts_ms["BTCUSDT"] = 1700000000000
    service.aggregator.last_tick_source["BTCUSDT"] = "stimulus_fixture"

    from unittest.mock import patch
    import time

    wall_clock = 1780702600000

    candles = [
        {"symbol": "BTCUSDT", "close": "50000", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50001", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50002", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50003", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50004", "ts": str(wall_clock // 1000)},
        {"symbol": "BTCUSDT", "close": "50005", "ts": str(wall_clock // 1000)},
    ]
    xrevrange_result = [(f"{wall_clock}-{i}", c) for i, c in enumerate(candles)]
    service.redis_client.xrevrange.return_value = xrevrange_result

    with patch.object(service, "_lookup_regime_id", return_value=0):
        with patch.object(time, "time", return_value=wall_clock / 1000.0):
            service._update_market_state("BTCUSDT", 1700000000000)

    args, _kwargs = service.redis_client.setex.call_args
    payload = __import__("json").loads(args[2])

    assert payload["symbol"] == "BTCUSDT"
    assert payload["ts_ms"] == wall_clock
    assert payload["close_now"] == 50000.0
    assert payload["close_1m_ago"] == 50001.0
    assert payload["close_5m_ago"] == 50005.0
    assert payload["regime_id"] == 0
