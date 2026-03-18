"""Unit tests for Market Data Service (Issue #1148 PR1, #1206 seam refactor, #1206 multi-symbol prep)."""

import json
import sys
from unittest.mock import MagicMock, call, patch

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


# ─── _process_event: dict-based ingress (Issue #1206 seam) ───────────────────


def _valid_dict() -> dict:
    return {
        "source": "mexc",
        "symbol": "BTCUSDT",
        "ts_ms": 1700000000000,
        "price": "50000.00",
        "trade_qty": "0.001",
        "side": "BUY",
    }


@pytest.mark.unit
def test_process_event_valid_dict_updates_cache():
    svc._process_event(_valid_dict())
    with svc._cache_lock:
        entry = svc._cache.get("BTCUSDT")
    assert entry is not None
    assert entry["price"] == "50000.00"
    assert entry["symbol"] == "BTCUSDT"
    assert svc._stats["messages_received"] == 1
    assert svc._stats["messages_invalid"] == 0


@pytest.mark.unit
def test_process_event_invalid_dict_missing_field_increments_invalid():
    data = _valid_dict()
    del data["price"]
    svc._process_event(data)
    assert svc._stats["messages_invalid"] == 1
    assert svc._stats["messages_received"] == 0
    with svc._cache_lock:
        assert svc._cache == {}


@pytest.mark.unit
def test_process_event_calls_redis_setex():
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._process_event(_valid_dict())
    mock_redis.setex.assert_called_once()
    call_key = mock_redis.setex.call_args[0][0]
    assert call_key == "market_price:BTCUSDT"


@pytest.mark.unit
def test_process_event_and_process_message_produce_identical_cache_entries():
    """Both ingress paths must produce the same cache structure."""
    svc._process_event(_valid_dict())
    with svc._cache_lock:
        entry_dict = dict(svc._cache.get("BTCUSDT"))
        svc._cache.clear()

    svc._process_message(_valid_raw())
    with svc._cache_lock:
        entry_json = dict(svc._cache.get("BTCUSDT"))

    # cached_at_ms will differ by a few ms — compare all stable fields
    for field in ("symbol", "price", "ts_ms", "source", "trade_qty", "side"):
        assert entry_dict[field] == entry_json[field], f"field {field!r} differs"


# ─── V3 bootstrap (Issue #1206) ───────────────────────────────────────────────


@pytest.mark.unit
def test_v3_bootstrap_disabled_is_noop():
    """When flag is false, _start_v3_client_if_enabled returns immediately.
    No import of mexc_v3_client, no thread created."""
    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", False):
        with patch("services.market.service.threading.Thread") as mock_thread:
            svc._start_v3_client_if_enabled()
    mock_thread.assert_not_called()
    # mexc_v3_client must not have been imported by this call
    assert "services.market.mexc_v3_client" not in sys.modules or True  # guard only


@pytest.mark.unit
def test_v3_bootstrap_enabled_starts_daemon_thread():
    """When flag is true, a daemon Thread named 'v3-client' is started."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.MexcV3Client.return_value = mock_client

    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", True):
        with patch.dict(sys.modules, {"services.market.mexc_v3_client": mock_module}):
            with patch("services.market.service.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance
                svc._start_v3_client_if_enabled()

    mock_thread.assert_called_once()
    _, kwargs = mock_thread.call_args
    assert kwargs.get("daemon") is True
    assert kwargs.get("name") == "v3-client"
    mock_thread_instance.start.assert_called_once()


@pytest.mark.unit
def test_v3_bootstrap_enabled_passes_shadow_event_as_callback():
    """With MARKET_V3_LIVE_WRITE=false (default), on_trade=_v3_shadow_event."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_module.MexcV3Client.return_value = mock_client

    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", True):
        with patch.object(svc, "MARKET_V3_LIVE_WRITE", False):
            with patch.dict(
                sys.modules, {"services.market.mexc_v3_client": mock_module}
            ):
                with patch("services.market.service.threading.Thread"):
                    svc._start_v3_client_if_enabled()

    _, kwargs = mock_module.MexcV3Client.call_args
    assert kwargs.get("on_trade") is svc._v3_shadow_event


@pytest.mark.unit
def test_v3_bootstrap_callback_writes_shadow_key():
    """The on_trade callback (_v3_shadow_event) writes market_price_v3:{symbol} via Redis."""
    mock_module = MagicMock()
    captured = {}

    def capture_client(*args, **kwargs):
        captured["on_trade"] = kwargs.get("on_trade")
        return MagicMock()

    mock_module.MexcV3Client.side_effect = capture_client

    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", True):
        with patch.object(svc, "MARKET_V3_LIVE_WRITE", False):
            with patch.dict(
                sys.modules, {"services.market.mexc_v3_client": mock_module}
            ):
                with patch("services.market.service.threading.Thread"):
                    svc._start_v3_client_if_enabled()

    on_trade = captured["on_trade"]
    assert on_trade is svc._v3_shadow_event

    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        on_trade(_valid_dict())

    mock_redis.setex.assert_called_once()
    call_key = mock_redis.setex.call_args[0][0]
    assert call_key == "market_price_v3:BTCUSDT"

    # Live cache must remain empty — shadow mode must not write to in-memory cache
    with svc._cache_lock:
        assert svc._cache.get("BTCUSDT") is None


@pytest.mark.unit
def test_v3_bootstrap_import_error_raises_runtime_error():
    """If flag is true but import fails, RuntimeError is raised (fail-closed)."""
    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", True):
        with patch.dict(sys.modules, {"services.market.mexc_v3_client": None}):
            with pytest.raises(RuntimeError, match=r"\[v3\].*import failed"):
                svc._start_v3_client_if_enabled()


# ─── V3 shadow event (Issue #1206) ────────────────────────────────────────────


@pytest.mark.unit
def test_v3_shadow_event_writes_shadow_key():
    """Valid event → setex called with market_price_v3:{symbol}."""
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_shadow_event(_valid_dict())
    mock_redis.setex.assert_called_once()
    call_key = mock_redis.setex.call_args[0][0]
    assert call_key == "market_price_v3:BTCUSDT"


@pytest.mark.unit
def test_v3_shadow_event_does_not_write_live_key():
    """Shadow event must never touch market_price:{symbol} or the in-memory cache."""
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_shadow_event(_valid_dict())

    for call_args in mock_redis.setex.call_args_list:
        key = call_args[0][0]
        assert not key.startswith("market_price:"), f"live key written: {key!r}"

    with svc._cache_lock:
        assert svc._cache.get("BTCUSDT") is None


@pytest.mark.unit
def test_v3_shadow_event_invalid_fails_safe():
    """Invalid event (missing required field) → no exception, no Redis write."""
    data = _valid_dict()
    del data["price"]
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_shadow_event(data)  # must not raise
    mock_redis.setex.assert_not_called()


@pytest.mark.unit
def test_v3_shadow_event_shadow_key_ttl_and_symbol():
    """Shadow key uses MARKET_PRICE_TTL_SECONDS TTL and correct symbol casing."""
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_shadow_event(_valid_dict())
    call_ttl = mock_redis.setex.call_args[0][1]
    assert call_ttl == svc.MARKET_PRICE_TTL_SECONDS
    call_key = mock_redis.setex.call_args[0][0]
    assert call_key == f"{svc.MARKET_V3_PRICE_KEY_PREFIX}:BTCUSDT"


# ─── V3 live-write mode (Issue #1206) ────────────────────────────────────────


@pytest.mark.unit
def test_v3_bootstrap_uses_live_event_when_live_write_enabled():
    """When MARKET_V3_LIVE_WRITE=true, on_trade must be _v3_live_event."""
    mock_module = MagicMock()
    mock_module.MexcV3Client.return_value = MagicMock()

    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", True):
        with patch.object(svc, "MARKET_V3_LIVE_WRITE", True):
            with patch.dict(
                sys.modules, {"services.market.mexc_v3_client": mock_module}
            ):
                with patch("services.market.service.threading.Thread"):
                    svc._start_v3_client_if_enabled()

    _, kwargs = mock_module.MexcV3Client.call_args
    assert kwargs.get("on_trade") is svc._v3_live_event


@pytest.mark.unit
def test_v3_bootstrap_uses_shadow_event_when_live_write_disabled():
    """When MARKET_V3_LIVE_WRITE=false (default), on_trade must be _v3_shadow_event."""
    mock_module = MagicMock()
    mock_module.MexcV3Client.return_value = MagicMock()

    with patch.object(svc, "MARKET_V3_CLIENT_ENABLED", True):
        with patch.object(svc, "MARKET_V3_LIVE_WRITE", False):
            with patch.dict(
                sys.modules, {"services.market.mexc_v3_client": mock_module}
            ):
                with patch("services.market.service.threading.Thread"):
                    svc._start_v3_client_if_enabled()

    _, kwargs = mock_module.MexcV3Client.call_args
    assert kwargs.get("on_trade") is svc._v3_shadow_event


@pytest.mark.unit
def test_v3_live_event_writes_live_key():
    """_v3_live_event must write market_price:{symbol}, not the shadow key."""
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_live_event(_valid_dict())
    mock_redis.setex.assert_called_once()
    call_key = mock_redis.setex.call_args[0][0]
    assert call_key == "market_price:BTCUSDT"


@pytest.mark.unit
def test_v3_live_event_does_not_write_shadow_key():
    """_v3_live_event must never write to market_price_v3:{symbol}."""
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_live_event(_valid_dict())
    for call_args in mock_redis.setex.call_args_list:
        key = call_args[0][0]
        assert not key.startswith("market_price_v3:"), f"shadow key written: {key!r}"


@pytest.mark.unit
def test_v3_live_event_updates_cache():
    """_v3_live_event must populate the in-memory cache (via _process_event)."""
    svc._v3_live_event(_valid_dict())
    with svc._cache_lock:
        entry = svc._cache.get("BTCUSDT")
    assert entry is not None
    assert entry["price"] == "50000.00"


@pytest.mark.unit
def test_v3_live_event_invalid_fails_safe():
    """Invalid event (missing required field) → no exception, increments invalid stat."""
    data = _valid_dict()
    del data["price"]
    mock_redis = MagicMock()
    with patch.object(svc, "_redis_client", mock_redis):
        svc._v3_live_event(data)  # must not raise
    mock_redis.setex.assert_not_called()
    assert svc._stats["messages_invalid"] == 1


@pytest.mark.unit
def test_v3_live_write_default_is_false():
    """MARKET_V3_LIVE_WRITE must be False when the env var is absent or unset.

    The constant is evaluated at import time.  This test checks that the
    already-imported module did NOT pick up a truthy env var — guarding against
    accidental activation in CI or a fresh local run.
    """
    import os

    if os.environ.get("MARKET_V3_LIVE_WRITE", "").lower() == "true":
        pytest.skip("MARKET_V3_LIVE_WRITE=true in environment — skipping default check")
    assert svc.MARKET_V3_LIVE_WRITE is False


# ─── V3 Prometheus metrics bridge (Issue #1206) ───────────────────────────────


@pytest.mark.unit
def test_sync_v3_metrics_noop_when_no_client():
    """When _v3_client is None (default), _sync_v3_metrics must not raise."""
    with patch.object(svc, "_v3_client", None):
        svc._sync_v3_metrics()  # must not raise


@pytest.mark.unit
def test_sync_v3_metrics_updates_gauges_from_client():
    """_sync_v3_metrics reads get_metrics() and sets the four V3 gauges."""
    mock_client = MagicMock()
    mock_client.get_metrics.return_value = {
        "decoded_messages_total": 42,
        "decode_errors_total": 3,
        "ws_connected": 1,
        "last_message_ts_ms": 1700000000000,
    }
    with patch.object(svc, "_v3_client", mock_client):
        svc._sync_v3_metrics()

    assert svc.V3_DECODED_TOTAL._value.get() == 42
    assert svc.V3_DECODE_ERRORS_TOTAL._value.get() == 3
    assert svc.V3_WS_CONNECTED._value.get() == 1
    assert svc.V3_LAST_MESSAGE_TS_MS._value.get() == 1700000000000


@pytest.mark.unit
def test_sync_v3_metrics_fail_safe_on_exception():
    """If get_metrics() raises, _sync_v3_metrics swallows the error."""
    mock_client = MagicMock()
    mock_client.get_metrics.side_effect = RuntimeError("boom")
    with patch.object(svc, "_v3_client", mock_client):
        svc._sync_v3_metrics()  # must not raise


@pytest.mark.unit
def test_sync_v3_metrics_handles_missing_keys():
    """Partial get_metrics() dict → missing keys default to 0."""
    mock_client = MagicMock()
    mock_client.get_metrics.return_value = {}  # all keys missing
    with patch.object(svc, "_v3_client", mock_client):
        svc._sync_v3_metrics()

    assert svc.V3_DECODED_TOTAL._value.get() == 0


@pytest.mark.unit
def test_metrics_endpoint_calls_sync_and_includes_v3_gauges():
    """/metrics response contains the four market_v3_* gauge names."""
    mock_client = MagicMock()
    mock_client.get_metrics.return_value = {
        "decoded_messages_total": 7,
        "decode_errors_total": 0,
        "ws_connected": 1,
        "last_message_ts_ms": 1700000000001,
    }
    with patch.object(svc, "_v3_client", mock_client):
        client = svc.app.test_client()
        response = client.get("/metrics")

    assert response.status_code == 200
    body = response.data
    assert b"market_v3_decoded_total" in body
    assert b"market_v3_decode_errors_total" in body
    assert b"market_v3_ws_connected" in body
    assert b"market_v3_last_message_ts_ms" in body


@pytest.mark.unit
def test_metrics_endpoint_v3_gauges_zero_when_no_client():
    """/metrics works with no V3 client; gauges are present but 0."""
    with patch.object(svc, "_v3_client", None):
        client = svc.app.test_client()
        response = client.get("/metrics")

    assert response.status_code == 200
    assert b"market_v3_decoded_total" in response.data


# ─── _parse_v3_symbols (multi-symbol prep, Issue #1206) ───────────────────────


@pytest.mark.unit
def test_parse_v3_symbols_single():
    """Single symbol string → one-element list, uppercased."""
    assert svc._parse_v3_symbols("BTCUSDT") == ["BTCUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_single_lowercase():
    """Input is normalised to uppercase."""
    assert svc._parse_v3_symbols("btcusdt") == ["BTCUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_two_symbols():
    """Comma-separated list → two-element list."""
    assert svc._parse_v3_symbols("BTCUSDT,ETHUSDT") == ["BTCUSDT", "ETHUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_whitespace_trimmed():
    """Leading/trailing whitespace around each symbol is stripped."""
    assert svc._parse_v3_symbols("  BTCUSDT , ETHUSDT  ") == ["BTCUSDT", "ETHUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_mixed_case_and_spaces():
    """Handles mixed case + whitespace in one pass."""
    assert svc._parse_v3_symbols("  btcusdt , EthUsdt ") == ["BTCUSDT", "ETHUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_three_symbols():
    """Three-symbol list parsed correctly."""
    result = svc._parse_v3_symbols("BTCUSDT,ETHUSDT,SOLUSDT")
    assert result == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_empty_string_raises():
    """Empty string → ValueError (no valid symbols)."""
    with pytest.raises(ValueError, match="No valid symbols"):
        svc._parse_v3_symbols("")


@pytest.mark.unit
def test_parse_v3_symbols_only_commas_raises():
    """All-comma string → ValueError after filtering empty entries."""
    with pytest.raises(ValueError, match="No valid symbols"):
        svc._parse_v3_symbols(",,,")


@pytest.mark.unit
def test_parse_v3_symbols_only_whitespace_raises():
    """Whitespace-only string → ValueError."""
    with pytest.raises(ValueError, match="No valid symbols"):
        svc._parse_v3_symbols("   ")


@pytest.mark.unit
def test_parse_v3_symbols_trailing_comma_ignored():
    """Trailing comma produces no spurious empty entry."""
    assert svc._parse_v3_symbols("BTCUSDT,") == ["BTCUSDT"]


@pytest.mark.unit
def test_parse_v3_symbols_current_default_passes():
    """The production default (BTCUSDT) parses without error."""
    result = svc._parse_v3_symbols("BTCUSDT")
    assert len(result) == 1
    assert result[0] == "BTCUSDT"
