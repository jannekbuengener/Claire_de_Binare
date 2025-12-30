"""
Redis Payload Sanitization Tests - Issue #349
Tests für core/utils/redis_payload.py
"""

import pytest
from core.utils.redis_payload import sanitize_payload, sanitize_market_data, sanitize_signal


class TestSanitizePayload:
    """Tests für generische sanitize_payload() Funktion"""

    def test_basic_none_filtering(self):
        """None-Werte müssen gefiltert werden"""
        raw = {"symbol": "BTCUSDT", "price": "50000", "qty": None, "side": "buy"}
        result = sanitize_payload(raw)

        assert "symbol" in result
        assert "price" in result
        assert "side" in result
        assert "qty" not in result  # None gefiltert

    def test_empty_string_preserved(self):
        """Leere Strings sind valide und müssen erhalten bleiben"""
        raw = {"symbol": "BTCUSDT", "reason": ""}
        result = sanitize_payload(raw)

        assert result["reason"] == ""  # Empty string NICHT gefiltert

    def test_bytes_decoded_to_utf8(self):
        """Bytes müssen zu UTF-8 Strings decodiert werden"""
        raw = {"symbol": b"BTCUSDT", "price": "50000"}
        result = sanitize_payload(raw)

        assert result["symbol"] == "BTCUSDT"
        assert isinstance(result["symbol"], str)

    def test_complex_types_auto_json_serialized_non_strict(self):
        """Listen/Dicts werden automatisch JSON-serialisiert (non-strict mode)"""
        raw = {"symbol": "BTCUSDT", "metadata": {"source": "mexc", "tags": ["crypto", "btc"]}}
        result = sanitize_payload(raw, strict=False)

        assert "metadata" in result
        # Auto-serialisiert zu JSON string
        assert '"source": "mexc"' in result["metadata"]

    def test_complex_types_raise_in_strict_mode(self):
        """Listen/Dicts müssen in strict mode rejected werden"""
        raw = {"symbol": "BTCUSDT", "metadata": {"source": "mexc"}}

        with pytest.raises(ValueError, match="Unsupported type dict"):
            sanitize_payload(raw, strict=True)

    def test_unknown_types_coerced_to_string_non_strict(self):
        """Unbekannte Typen werden zu Strings coerced (non-strict)"""
        class CustomType:
            def __str__(self):
                return "custom_value"

        raw = {"symbol": "BTCUSDT", "custom": CustomType()}
        result = sanitize_payload(raw, strict=False)

        assert result["custom"] == "custom_value"

    def test_unknown_types_raise_in_strict_mode(self):
        """Unbekannte Typen müssen in strict mode rejected werden"""
        class CustomType:
            pass

        raw = {"symbol": "BTCUSDT", "custom": CustomType()}

        with pytest.raises(ValueError, match="Unsupported type CustomType"):
            sanitize_payload(raw, strict=True)

    def test_invalid_utf8_bytes_fallback(self):
        """Nicht-decodierbare Bytes werden als repr() behandelt (non-strict)"""
        raw = {"symbol": b"\xff\xfe invalid utf8"}
        result = sanitize_payload(raw, strict=False)

        # Fallback zu repr()
        assert "\\xff\\xfe" in result["symbol"]

    def test_invalid_utf8_bytes_raise_in_strict_mode(self):
        """Nicht-decodierbare Bytes müssen in strict mode rejected werden"""
        raw = {"symbol": b"\xff\xfe invalid utf8"}

        with pytest.raises(ValueError, match="Failed to decode bytes"):
            sanitize_payload(raw, strict=True)

    def test_non_dict_payload_raises_typeerror(self):
        """Payload muss ein dict sein"""
        with pytest.raises(TypeError, match="Payload must be dict"):
            sanitize_payload("not a dict")


class TestSanitizeMarketData:
    """Tests für market_data Contract v1.0 Sanitization"""

    def test_valid_market_data_passthrough(self):
        """Valide market_data Payloads müssen durchgehen"""
        raw = {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "trade_qty": "1.5",
            "side": "buy",
        }
        result = sanitize_market_data(raw)

        assert result["source"] == "mexc"
        assert result["symbol"] == "BTCUSDT"
        assert result["ts_ms"] == 1735574400000
        assert result["price"] == "50000.50"
        assert result["trade_qty"] == "1.5"
        assert result["side"] == "buy"
        assert result["schema_version"] == "v1.0"  # Auto-added

    def test_schema_version_auto_added(self):
        """schema_version muss automatisch hinzugefügt werden"""
        raw = {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "trade_qty": "1.5",
            "side": "buy",
        }
        result = sanitize_market_data(raw)

        assert result["schema_version"] == "v1.0"

    def test_none_values_filtered(self):
        """None-Werte müssen gefiltert werden (z.B. volume=None)"""
        raw = {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "trade_qty": "1.5",
            "side": "buy",
            "trade_id": None,  # Optional, None
        }
        result = sanitize_market_data(raw)

        assert "trade_id" not in result

    def test_missing_required_field_raises(self):
        """Fehlende required fields müssen rejected werden"""
        raw = {
            "source": "mexc",
            # "symbol": "BTCUSDT",  # MISSING
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "trade_qty": "1.5",
            "side": "buy",
        }

        with pytest.raises(ValueError, match="Missing required fields.*symbol"):
            sanitize_market_data(raw)

    def test_ts_ms_must_be_int(self):
        """ts_ms muss integer sein"""
        raw = {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": "1735574400000",  # STRING statt INT
            "price": "50000.50",
            "trade_qty": "1.5",
            "side": "buy",
        }

        with pytest.raises(ValueError, match="ts_ms must be int"):
            sanitize_market_data(raw)

    def test_price_must_be_string(self):
        """price muss string sein (Precision-Erhaltung)"""
        raw = {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": 50000.50,  # NUMBER statt STRING
            "trade_qty": "1.5",
            "side": "buy",
        }

        with pytest.raises(ValueError, match="price must be str"):
            sanitize_market_data(raw)

    def test_trade_qty_must_be_string(self):
        """trade_qty muss string sein (Precision-Erhaltung)"""
        raw = {
            "source": "mexc",
            "symbol": "BTCUSDT",
            "ts_ms": 1735574400000,
            "price": "50000.50",
            "trade_qty": 1.5,  # NUMBER statt STRING
            "side": "buy",
        }

        with pytest.raises(ValueError, match="trade_qty must be str"):
            sanitize_market_data(raw)


class TestSanitizeSignal:
    """Tests für signal Contract v1.0 Sanitization"""

    def test_valid_signal_passthrough(self):
        """Valide signal Payloads müssen durchgehen"""
        raw = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
        }
        result = sanitize_signal(raw)

        assert result["signal_id"] == "sig-001"
        assert result["strategy_id"] == "momentum-v2"
        assert result["symbol"] == "BTCUSDT"
        assert result["side"] == "BUY"
        assert result["timestamp"] == 1735574400
        assert result["schema_version"] == "v1.0"  # Auto-added
        assert result["type"] == "signal"  # Auto-added

    def test_schema_version_and_type_auto_added(self):
        """schema_version + type müssen automatisch hinzugefügt werden"""
        raw = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
        }
        result = sanitize_signal(raw)

        assert result["schema_version"] == "v1.0"
        assert result["type"] == "signal"

    def test_none_values_filtered(self):
        """None-Werte müssen gefiltert werden (confidence, reason, etc.)"""
        raw = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "confidence": None,  # Optional, None
            "reason": None,  # Optional, None
        }
        result = sanitize_signal(raw)

        assert "confidence" not in result
        assert "reason" not in result

    def test_missing_required_field_raises(self):
        """Fehlende required fields müssen rejected werden"""
        raw = {
            # "signal_id": "sig-001",  # MISSING
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
        }

        with pytest.raises(ValueError, match="Missing required fields.*signal_id"):
            sanitize_signal(raw)

    def test_timestamp_auto_coerced_from_float(self):
        """timestamp float→int auto-coercion (Migration case)"""
        raw = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400.123,  # FLOAT (alt)
        }
        result = sanitize_signal(raw)

        assert result["timestamp"] == 1735574400  # Coerced zu int
        assert isinstance(result["timestamp"], int)

    def test_timestamp_invalid_type_raises(self):
        """timestamp mit invaliden Typen muss rejected werden"""
        raw = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": "not_a_number",  # STRING
        }

        with pytest.raises(ValueError, match="timestamp must be int"):
            sanitize_signal(raw)

    def test_strength_range_validation(self):
        """strength muss in Range [0.0, 1.0] liegen"""
        # Valid: 0.0
        raw_valid_low = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "strength": 0.0,
        }
        result = sanitize_signal(raw_valid_low)
        assert result["strength"] == 0.0

        # Valid: 1.0
        raw_valid_high = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "strength": 1.0,
        }
        result = sanitize_signal(raw_valid_high)
        assert result["strength"] == 1.0

        # Invalid: > 1.0
        raw_invalid_high = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "strength": 1.5,  # > 1.0
        }
        with pytest.raises(ValueError, match="strength must be in range"):
            sanitize_signal(raw_invalid_high)

        # Invalid: < 0.0
        raw_invalid_low = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "strength": -0.1,  # < 0.0
        }
        with pytest.raises(ValueError, match="strength must be in range"):
            sanitize_signal(raw_invalid_low)

    def test_confidence_range_validation(self):
        """confidence muss in Range [0.0, 1.0] liegen"""
        # Valid
        raw_valid = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "confidence": 0.85,
        }
        result = sanitize_signal(raw_valid)
        assert result["confidence"] == 0.85

        # Invalid
        raw_invalid = {
            "signal_id": "sig-001",
            "strategy_id": "momentum-v2",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "timestamp": 1735574400,
            "confidence": 1.5,  # > 1.0
        }
        with pytest.raises(ValueError, match="confidence must be in range"):
            sanitize_signal(raw_invalid)
