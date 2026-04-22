"""Unit tests for candle_normalizer.normalize_candle_stream_entry.

These tests validate the stream payload → DB-row normalization logic introduced
for ARVP candles persistence (Issue #1855). No DB or Redis connections are used.

Test coverage:
- Valid payload → correct normalised dict
- ts (string seconds) → ts_ms (int milliseconds)
- Missing required fields (ts, symbol, close) → None
- Invalid decimal field → None
- regime_id absent → None in output (always; never accepted from payload)
- No floats in normalised numeric fields
- trades → trade_count mapping
- volume missing → Decimal("0") default
- volume present but invalid → None
- OHLC invariant violation (high < low) → None
- Positive-value checks for open/high/low
- Deterministic output for identical payload
"""

from decimal import Decimal

import pytest

from services.db_writer.candle_normalizer import normalize_candle_stream_entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_payload() -> dict:
    """Minimal valid stream.candles_1m payload (all strings, as from Redis)."""
    return {
        "ts": "1700000000",
        "symbol": "BTCUSDT",
        "timeframe": "60s",
        "open": "42000.00000000",
        "high": "42100.00000000",
        "low": "41900.00000000",
        "close": "42050.00000000",
        "volume": "12.34000000",
        "trades": "87",
        "schema_version": "1",
        "source_version": "1",
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_valid_payload_returns_dict(valid_payload):
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert isinstance(result, dict)


@pytest.mark.unit
def test_ts_string_seconds_converted_to_ts_ms(valid_payload):
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["ts_ms"] == 1700000000 * 1000


@pytest.mark.unit
def test_normalized_dict_has_all_required_keys(valid_payload):
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    expected_keys = {"symbol", "ts_ms", "open", "high", "low", "close", "volume", "trade_count", "regime_id"}
    assert set(result.keys()) == expected_keys


@pytest.mark.unit
def test_symbol_preserved(valid_payload):
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["symbol"] == "BTCUSDT"


@pytest.mark.unit
def test_trades_mapped_to_trade_count(valid_payload):
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["trade_count"] == 87


@pytest.mark.unit
def test_volume_parsed(valid_payload):
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["volume"] == Decimal("12.34000000")


@pytest.mark.unit
def test_regime_id_always_none(valid_payload):
    """regime_id must always be None — never accepted from the candle stream payload."""
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["regime_id"] is None


@pytest.mark.unit
def test_regime_id_none_even_if_present_in_payload(valid_payload):
    """Payload containing regime_id must not propagate it to the output."""
    valid_payload["regime_id"] = "3"
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["regime_id"] is None


# ---------------------------------------------------------------------------
# No floats rule
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_no_floats_in_numeric_fields(valid_payload):
    """All monetary / numeric fields must be Decimal or int — never float."""
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    for field in ("open", "high", "low", "close", "volume"):
        assert isinstance(result[field], Decimal), f"{field} should be Decimal, got {type(result[field])}"
    assert isinstance(result["trade_count"], int)
    assert isinstance(result["ts_ms"], int)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_deterministic_output_for_identical_payload(valid_payload):
    result1 = normalize_candle_stream_entry(valid_payload)
    result2 = normalize_candle_stream_entry(valid_payload)
    assert result1 == result2


# ---------------------------------------------------------------------------
# Missing required fields → None
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_missing_ts_returns_none(valid_payload):
    del valid_payload["ts"]
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_missing_symbol_returns_none(valid_payload):
    del valid_payload["symbol"]
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_missing_close_returns_none(valid_payload):
    del valid_payload["close"]
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_missing_open_returns_none(valid_payload):
    del valid_payload["open"]
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_missing_high_returns_none(valid_payload):
    del valid_payload["high"]
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_missing_low_returns_none(valid_payload):
    del valid_payload["low"]
    assert normalize_candle_stream_entry(valid_payload) is None


# ---------------------------------------------------------------------------
# Optional fields — defaults vs fail-closed
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_missing_volume_defaults_to_zero(valid_payload):
    del valid_payload["volume"]
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["volume"] == Decimal("0")


@pytest.mark.unit
def test_missing_trades_defaults_to_zero(valid_payload):
    del valid_payload["trades"]
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert result["trade_count"] == 0


@pytest.mark.unit
def test_present_but_invalid_volume_returns_none(valid_payload):
    valid_payload["volume"] = "not-a-number"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_present_but_invalid_trades_returns_none(valid_payload):
    valid_payload["trades"] = "INVALID"
    assert normalize_candle_stream_entry(valid_payload) is None


# ---------------------------------------------------------------------------
# Invalid decimal / type fields → None
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_invalid_close_decimal_returns_none(valid_payload):
    valid_payload["close"] = "not-a-price"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_invalid_open_decimal_returns_none(valid_payload):
    valid_payload["open"] = "abc"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_invalid_ts_returns_none(valid_payload):
    valid_payload["ts"] = "not-a-timestamp"
    assert normalize_candle_stream_entry(valid_payload) is None


# ---------------------------------------------------------------------------
# Positive-value checks (> 0)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_zero_close_returns_none(valid_payload):
    valid_payload["close"] = "0"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_negative_close_returns_none(valid_payload):
    valid_payload["close"] = "-1.0"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_zero_open_returns_none(valid_payload):
    valid_payload["open"] = "0"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_zero_high_returns_none(valid_payload):
    valid_payload["high"] = "0"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_zero_low_returns_none(valid_payload):
    valid_payload["low"] = "0"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_negative_ts_ms_returns_none(valid_payload):
    valid_payload["ts"] = "-1"
    assert normalize_candle_stream_entry(valid_payload) is None


# ---------------------------------------------------------------------------
# OHLCV invariant
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_high_less_than_low_returns_none(valid_payload):
    """high < low violates the OHLCV invariant → fail-closed."""
    valid_payload["high"] = "41000.00000000"  # below low=41900
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_high_equal_to_low_is_valid(valid_payload):
    """high == low is valid (flat candle, e.g., zero-volatility interval)."""
    valid_payload["high"] = "42000.00000000"
    valid_payload["low"] = "42000.00000000"
    valid_payload["open"] = "42000.00000000"
    valid_payload["close"] = "42000.00000000"
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None



# ---------------------------------------------------------------------------
# Non-finite Decimal values → None (NaN / Infinity guards)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_nan_close_returns_none(valid_payload):
    """Decimal('NaN') on a required OHLC field must fail-closed."""
    valid_payload["close"] = "NaN"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_infinity_close_returns_none(valid_payload):
    """Decimal('Infinity') must fail-closed — would bypass the > 0 check."""
    valid_payload["close"] = "Infinity"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_negative_infinity_close_returns_none(valid_payload):
    valid_payload["close"] = "-Infinity"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_nan_volume_returns_none(valid_payload):
    valid_payload["volume"] = "NaN"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_infinity_volume_returns_none(valid_payload):
    valid_payload["volume"] = "Infinity"
    assert normalize_candle_stream_entry(valid_payload) is None


# ---------------------------------------------------------------------------
# Negative optional-field values → None
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_negative_volume_returns_none(valid_payload):
    """Negative volume is an invalid OHLCV value → fail-closed."""
    valid_payload["volume"] = "-0.01"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_negative_trade_count_returns_none(valid_payload):
    """Negative trade_count is physically impossible → fail-closed."""
    valid_payload["trades"] = "-1"
    assert normalize_candle_stream_entry(valid_payload) is None


@pytest.mark.unit
def test_extra_fields_in_payload_are_ignored(valid_payload):
    valid_payload["unexpected_field"] = "should_be_ignored"
    valid_payload["another_extra"] = "42"
    result = normalize_candle_stream_entry(valid_payload)
    assert result is not None
    assert "unexpected_field" not in result
    assert "another_extra" not in result
