"""Regime service contract tests (#3832).

No live Redis or runtime service start.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.regime.models import Candle
from services.regime.service import RegimeService

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"symbol": "BTCUSDT"},
        {"symbol": "BTCUSDT", "timeframe": "60s"},
        {"symbol": "BTCUSDT", "timeframe": "60s", "ts": "1", "open": "1"},
        {"symbol": "BTCUSDT", "timeframe": "60s", "ts": "bad", "open": "1", "high": "2", "low": "1", "close": "1.5"},
    ],
)
def test_candle_from_payload_invalid_matrix(payload: dict) -> None:
    assert Candle.from_payload(payload) is None


def test_candle_from_payload_valid_minimal() -> None:
    candle = Candle.from_payload(
        {
            "symbol": "BTCUSDT",
            "timeframe": "60s",
            "ts": "1700000000",
            "open": "100",
            "high": "101",
            "low": "99",
            "close": "100.5",
            "volume": "10",
        }
    )
    assert candle is not None
    assert candle.symbol == "BTCUSDT"
    assert candle.close == 100.5


def test_handle_missing_ohlcv_emits_unknown_fail_closed() -> None:
    service = RegimeService()
    mock_redis = MagicMock()
    service.redis_client = mock_redis
    service._handle_missing_ohlcv(
        {"symbol": "BTCUSDT", "timeframe": "60s", "ts": "1700000000"}
    )
    mock_redis.xadd.assert_called_once()
    fields = mock_redis.xadd.call_args[0][1]
    assert fields["regime"] == "UNKNOWN"
    assert "schema_version" in fields


def test_derive_regime_warmup_does_not_emit_before_indicators_ready() -> None:
    service = RegimeService()
    mock_redis = MagicMock()
    service.redis_client = mock_redis
    candle = Candle(
        ts=1,
        symbol="BTCUSDT",
        timeframe="60s",
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
        volume=1.0,
    )
    service._derive_regime(candle)
    mock_redis.xadd.assert_not_called()


def test_emit_regime_payload_has_no_secret_fields() -> None:
    service = RegimeService()
    mock_redis = MagicMock()
    service.redis_client = mock_redis
    candle = Candle(
        ts=1700000000,
        symbol="BTCUSDT",
        timeframe="60s",
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1.0,
    )
    service._emit_regime(candle, "TREND", 30.0, 0.5)
    fields = mock_redis.xadd.call_args[0][1]
    secret_keys = {"password", "api_key", "api_secret", "token"}
    assert secret_keys.isdisjoint(set(fields.keys()))
    assert fields["schema_version"] == service.config.schema_version
