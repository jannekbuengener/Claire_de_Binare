"""Unit tests for cdb_market Market State V1 write path (Issue #1201 Delta 1).

Tests verify that services/market/service.py:
- correctly computes return_1m, return_5m, price_change_5m from candle history
- writes market_state:{symbol} with the correct payload
- skips write if < 6 candles (fail-closed, RC_002)
- skips write if close=0 in history (fail-closed, division-by-zero guard)
- propagates last_tick_ts_ms from market_data entry
- regime_id absent in payload when regime is missing (fail-closed, RC_001)
"""

import json
import time
from unittest.mock import MagicMock, call

import pytest

import services.market.service as svc


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module-level stats before each test."""
    svc._stats["messages_received"] = 0
    svc._stats["messages_invalid"] = 0
    svc._stats["market_state_updates"] = 0
    svc._stats["market_state_skipped"] = 0
    yield


def _make_candle_payload(symbol: str, close: float) -> dict:
    return {
        "symbol": symbol,
        "open": str(close),
        "high": str(close),
        "low": str(close),
        "close": str(close),
        "volume": "1.0",
        "ts": str(int(time.time())),
    }


def _candle_entries(symbol: str, closes: list) -> list:
    """Build XREVRANGE-style list: newest first (index 0 = now)."""
    return [(f"{i}-0", _make_candle_payload(symbol, c)) for i, c in enumerate(closes)]


def _make_mock_redis(candle_entries: list, regime_entries: list) -> MagicMock:
    mock = MagicMock()

    def xrevrange(stream, start, stop, count=None):
        if stream == svc.MARKET_CANDLES_STREAM:
            return candle_entries
        if stream == svc.MARKET_REGIME_STREAM:
            return regime_entries
        return []

    mock.xrevrange.side_effect = xrevrange
    return mock


# ─── Return calculation ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_correct_return_calculation():
    """return_1m and return_5m are emitted as percentage points."""
    # candles[0]=110, candles[1]=100, candles[5]=50 (newest first)
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    mock_redis.setex.assert_called_once()
    key, ttl, raw = mock_redis.setex.call_args[0]
    assert key == f"{svc.MARKET_STATE_KEY_PREFIX}:BTCUSDT"
    assert ttl == svc.MARKET_STATE_TTL_SECONDS
    payload = json.loads(raw)
    assert payload["return_1m"] == pytest.approx(((110 - 100) / 100) * 100)
    assert payload["return_5m"] == pytest.approx(((110 - 50) / 50) * 100)
    assert payload["price_change_5m"] == pytest.approx(abs(((110 - 50) / 50) * 100))
    assert svc._stats["market_state_updates"] == 1
    assert svc._stats["market_state_skipped"] == 0


@pytest.mark.unit
def test_price_change_5m_is_absolute_value():
    """price_change_5m = abs(return_5m) — positive even for negative returns."""
    # close_now < close_5m_ago → negative return_5m
    closes = [40.0, 50.0, 55.0, 60.0, 65.0, 80.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", None, mock_redis)

    payload = json.loads(mock_redis.setex.call_args[0][2])
    assert payload["return_5m"] < 0
    assert payload["price_change_5m"] >= 0
    assert payload["price_change_5m"] == pytest.approx(abs(payload["return_5m"]))


# ─── Fail-closed: < 6 candles ─────────────────────────────────────────────────


@pytest.mark.unit
def test_skip_when_fewer_than_6_candles():
    """No write if only 5 candles available (fail-closed, RC_002)."""
    closes = [100.0, 99.0, 98.0, 97.0, 96.0]  # only 5
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    mock_redis.setex.assert_not_called()
    assert svc._stats["market_state_skipped"] == 1
    assert svc._stats["market_state_updates"] == 0


@pytest.mark.unit
def test_skip_when_zero_candles():
    """No write if stream is empty (fail-closed)."""
    mock_redis = _make_mock_redis([], [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    mock_redis.setex.assert_not_called()
    assert svc._stats["market_state_skipped"] == 1


@pytest.mark.unit
def test_skip_filters_by_symbol():
    """Candles for other symbols must not count towards the 6-candle requirement."""
    # 6 candles, all for ETHUSDT — BTCUSDT has zero
    closes = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
    entries = _candle_entries("ETHUSDT", closes)
    mock_redis = _make_mock_redis(entries, [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    mock_redis.setex.assert_not_called()
    assert svc._stats["market_state_skipped"] == 1


# ─── Fail-closed: close=0 ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_skip_when_close_1m_ago_is_zero():
    """No write if candles[1].close == 0 (division-by-zero guard)."""
    closes = [110.0, 0.0, 99.0, 98.0, 97.0, 50.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    mock_redis.setex.assert_not_called()
    assert svc._stats["market_state_skipped"] == 1


@pytest.mark.unit
def test_skip_when_close_5m_ago_is_zero():
    """No write if candles[5].close == 0 (division-by-zero guard)."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 0.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    mock_redis.setex.assert_not_called()
    assert svc._stats["market_state_skipped"] == 1


# ─── last_tick_ts_ms propagation ──────────────────────────────────────────────


@pytest.mark.unit
def test_last_tick_ts_ms_written_from_parameter():
    """last_tick_ts_ms in payload must equal the value passed from market_data entry."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])
    expected_ts = 1700000099999

    svc._update_market_state("BTCUSDT", expected_ts, mock_redis)

    payload = json.loads(mock_redis.setex.call_args[0][2])
    assert payload["last_tick_ts_ms"] == expected_ts


@pytest.mark.unit
def test_last_tick_ts_ms_monotone_across_two_calls():
    """Second call with higher ts_ms must produce a higher last_tick_ts_ms in payload."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    entries = _candle_entries("BTCUSDT", closes)
    mock_redis = _make_mock_redis(entries, [])

    ts_first = 1700000000000
    ts_second = 1700000060000

    svc._update_market_state("BTCUSDT", ts_first, mock_redis)
    svc._update_market_state("BTCUSDT", ts_second, mock_redis)

    assert mock_redis.setex.call_count == 2
    payload_first = json.loads(mock_redis.setex.call_args_list[0][0][2])
    payload_second = json.loads(mock_redis.setex.call_args_list[1][0][2])
    assert payload_second["last_tick_ts_ms"] > payload_first["last_tick_ts_ms"]


@pytest.mark.unit
def test_last_tick_ts_ms_none_written_when_not_available():
    """last_tick_ts_ms=None must be written as null (not omitted)."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", None, mock_redis)

    payload = json.loads(mock_redis.setex.call_args[0][2])
    assert "last_tick_ts_ms" in payload
    assert payload["last_tick_ts_ms"] is None


# ─── regime_id handling ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_regime_id_included_when_valid():
    """regime_id present in payload when regime signal is fresh and valid."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    now_s = int(time.time())
    regime_entries = [
        ("1-0", {"symbol": "BTCUSDT", "regime": "TREND", "ts": str(now_s - 10)})
    ]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), regime_entries)

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    payload = json.loads(mock_redis.setex.call_args[0][2])
    assert payload["regime_id"] == 0  # TREND → 0


@pytest.mark.unit
def test_regime_id_absent_when_no_regime_signal():
    """regime_id must NOT be set in payload when no regime signal found (fail-closed)."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    payload = json.loads(mock_redis.setex.call_args[0][2])
    assert "regime_id" not in payload


# ─── TTL and key format ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_redis_key_format_and_ttl():
    """Key must be {MARKET_STATE_KEY_PREFIX}:{symbol} and TTL must be 120s (Contract V1)."""
    closes = [110.0, 100.0, 99.0, 98.0, 97.0, 50.0]
    mock_redis = _make_mock_redis(_candle_entries("BTCUSDT", closes), [])

    svc._update_market_state("BTCUSDT", 1700000000000, mock_redis)

    key, ttl, _raw = mock_redis.setex.call_args[0]
    assert key == f"{svc.MARKET_STATE_KEY_PREFIX}:BTCUSDT"
    assert ttl == svc.MARKET_STATE_TTL_SECONDS
