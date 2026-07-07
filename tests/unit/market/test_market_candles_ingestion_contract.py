"""Market/Candles ingestion contract tests (#3831).

Fixture-backed — no live Redis, WebSocket, or MEXC connection.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import services.market.service as market_svc
from core.utils.redis_payload import sanitize_market_data

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INVALID_EXAMPLES = _REPO_ROOT / "docs/contracts/examples/market_data_invalid.json"


@pytest.fixture(autouse=True)
def _reset_market_stats() -> None:
    market_svc._stats["messages_received"] = 0
    market_svc._stats["messages_invalid"] = 0
    market_svc._stats["market_state_updates"] = 0
    market_svc._stats["market_state_skipped"] = 0
    yield


def _load_invalid_examples() -> list[dict]:
    return json.loads(_INVALID_EXAMPLES.read_text(encoding="utf-8"))


def test_sanitize_market_data_rejects_invalid_schema_examples() -> None:
    for example in _load_invalid_examples():
        with pytest.raises((ValueError, TypeError, KeyError)):
            sanitize_market_data(example["payload"])


def test_fewer_than_six_candles_skips_market_state_write() -> None:
    mock_redis = MagicMock()
    mock_redis.xrevrange.return_value = []
    market_svc._update_market_state("BTCUSDT", 1_700_000_000_000, mock_redis)
    mock_redis.setex.assert_not_called()
    assert market_svc._stats["market_state_skipped"] == 1


def test_stale_regime_lookup_omits_regime_id_fail_closed() -> None:
    import time

    stale_ts = str(int(time.time()) - 10_000)
    regime_entries = [
        (
            "1-0",
            {
                "ts": stale_ts,
                "symbol": "BTCUSDT",
                "timeframe": "60s",
                "regime": "TREND",
            },
        )
    ]
    mock_redis = MagicMock()

    def xrevrange(stream, start, stop, count=None):
        if stream == market_svc.MARKET_REGIME_STREAM:
            return regime_entries
        return []

    mock_redis.xrevrange.side_effect = xrevrange
    regime_id = market_svc._lookup_regime_id("BTCUSDT", mock_redis)
    assert regime_id is None


@pytest.mark.parametrize(
    ("regime", "expected"),
    [
        ("TREND", 0),
        ("RANGE", 1),
        ("HIGH_VOL_CHAOTIC", 2),
        ("CRISIS", 3),
    ],
)
def test_regime_string_maps_to_regime_id_contract(regime: str, expected: int) -> None:
    import time

    fresh_ts = str(int(time.time()))
    regime_entries = [
        (
            "1-0",
            {
                "ts": fresh_ts,
                "symbol": "BTCUSDT",
                "timeframe": "60s",
                "regime": regime,
            },
        )
    ]
    mock_redis = MagicMock()

    def xrevrange(stream, start, stop, count=None):
        if stream == market_svc.MARKET_REGIME_STREAM:
            return regime_entries
        return []

    mock_redis.xrevrange.side_effect = xrevrange
    assert market_svc._lookup_regime_id("BTCUSDT", mock_redis) == expected


def test_process_message_invalid_json_increments_invalid_counter() -> None:
    market_svc._process_message("not-json")
    assert market_svc._stats["messages_invalid"] == 1


@pytest.mark.skipif(market_svc.app is None, reason="Flask not installed")
def test_status_endpoint_does_not_echo_secrets() -> None:
    client = market_svc.app.test_client()
    response = client.get("/status")
    assert response.status_code == 200
    body = response.get_data(as_text=True).lower()
    for secret_token in ("password", "api_key", "api_secret", "bearer"):
        assert secret_token not in body
