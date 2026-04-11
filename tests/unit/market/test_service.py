"""Unit tests for Market Data Service (Issue #1148 PR1)."""

import json
from unittest.mock import MagicMock, patch

import pytest

import services.market.service as svc


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module-level cache, stats, and health flags before each test."""
    with svc._cache_lock:
        svc._cache.clear()
    svc._stats["messages_received"] = 0
    svc._stats["messages_invalid"] = 0
    svc._redis_connected = False
    svc._subscription_active = False
    svc._redis_client = None
    yield


def _valid_raw() -> str:
    return json.dumps(
        {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1700000000000,
            "price": "50000.00",
            "trade_qty": "0.001",
            "side": "BUY",
        }
    )


@pytest.mark.unit
def test_process_valid_message_updates_cache():
    svc._process_message(_valid_raw())
    with svc._cache_lock:
        entry = svc._cache.get("BTCUSDT")
    assert entry is not None
    assert entry["price"] == "50000.00"
    assert entry["symbol"] == "BTCUSDT"
    assert svc._stats["messages_received"] == 1
    assert svc._stats["messages_invalid"] == 0


@pytest.mark.unit
def test_process_invalid_json_increments_invalid_stat():
    svc._process_message("not-json{{{")
    assert svc._stats["messages_invalid"] == 1
    assert svc._stats["messages_received"] == 0
    with svc._cache_lock:
        assert svc._cache == {}


@pytest.mark.unit
def test_process_missing_required_field_increments_invalid_stat():
    # Missing price field -- sanitize_market_data must raise ValueError
    raw = json.dumps(
        {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1700000000000,
            "trade_qty": "0.001",
            "side": "BUY",
        }
    )
    svc._process_message(raw)
    assert svc._stats["messages_invalid"] == 1
    assert svc._stats["messages_received"] == 0


@pytest.mark.unit
def test_process_valid_message_calls_redis_setex():
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._process_message(_valid_raw())
    mock_redis.setex.assert_called_once()
    call_key = mock_redis.setex.call_args[0][0]
    call_ttl = mock_redis.setex.call_args[0][1]
    assert call_key == "market_price:BTCUSDT"
    assert call_ttl == svc.MARKET_PRICE_TTL_SECONDS


@pytest.mark.unit
def test_market_price_endpoint_returns_cached_entry():
    with svc._cache_lock:
        svc._cache["ETHUSDT"] = {
            "symbol": "ETHUSDT",
            "price": "3000.00",
            "ts_ms": 1700000000000,
            "source": "mexc",
            "trade_qty": "0.5",
            "side": "SELL",
            "cached_at_ms": 1700000000001,
        }
    client = svc.app.test_client()
    response = client.get("/market/price/ETHUSDT")
    assert response.status_code == 200
    data = response.get_json()
    assert data["price"] == "3000.00"
    assert data["symbol"] == "ETHUSDT"


@pytest.mark.unit
def test_market_price_endpoint_404_for_unknown_symbol():
    client = svc.app.test_client()
    response = client.get("/market/price/UNKNWN")
    assert response.status_code == 404
    assert "error" in response.get_json()


@pytest.mark.unit
def test_health_degraded_when_not_connected():
    # _reset_state sets _redis_connected=False, _subscription_active=False
    client = svc.app.test_client()
    response = client.get("/health")
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "degraded"
    assert "redis unavailable" in data["detail"]


@pytest.mark.unit
def test_health_healthy_when_connected_and_subscribed():
    svc._redis_connected = True
    svc._subscription_active = True
    client = svc.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


@pytest.mark.unit
def test_status_endpoint_returns_operational_state():
    svc._redis_connected = True
    svc._subscription_active = True
    svc._stats["messages_received"] = 3
    with svc._cache_lock:
        svc._cache["BTCUSDT"] = {
            "symbol": "BTCUSDT",
            "price": "50000.00",
            "ts_ms": 1700000000000,
            "source": "mexc",
            "trade_qty": "0.001",
            "side": "BUY",
            "cached_at_ms": 1700000000001,
        }
    client = svc.app.test_client()
    response = client.get("/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "market_data"
    assert data["redis_connected"] is True
    assert data["subscription_active"] is True
    assert data["stats"]["messages_received"] == 3
    assert "BTCUSDT" in data["cached_symbols"]


@pytest.mark.unit
def test_metrics_endpoint_returns_prometheus_output():
    client = svc.app.test_client()
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.content_type
    assert b"market_messages_received_total" in response.data


@pytest.mark.unit
def test_connect_redis_loop_retries_then_recovers(monkeypatch):
    attempts = {"count": 0}
    expected_client = MagicMock()

    def fake_build_client():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise svc.redis.RedisError("temporary outage")
        return expected_client

    sleeps = []

    monkeypatch.setattr(svc, "_build_redis_client", fake_build_client)
    monkeypatch.setattr(svc.time, "sleep", lambda seconds: sleeps.append(seconds))

    recovered_client = svc._connect_redis_loop()

    assert recovered_client is expected_client
    assert attempts["count"] == 2
    assert sleeps == [svc.REDIS_RETRY_SECONDS]
    assert svc._redis_connected is True
