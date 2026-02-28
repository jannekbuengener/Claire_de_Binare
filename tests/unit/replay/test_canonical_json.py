"""Tests for core.replay.canonical_json — deterministic serialization.

Governance: LR-021 Slice 1 (Deterministic Replay Framework)
"""

import json

from core.replay.canonical_json import (
    _omit_none,
    _sanitize_float,
    canonical_hash,
    canonical_json_dumps,
    sha256_hex,
)


class TestSanitizeFloat:
    def test_nan_becomes_none(self):
        assert _sanitize_float(float("nan")) is None

    def test_inf_becomes_none(self):
        assert _sanitize_float(float("inf")) is None

    def test_neg_inf_becomes_none(self):
        assert _sanitize_float(float("-inf")) is None

    def test_normal_float_rounded(self):
        assert _sanitize_float(1.23456789012345) == 1.2345678901

    def test_negative_zero_normalized(self):
        result = _sanitize_float(-0.0)
        assert result == 0.0
        # Verify it serializes as "0.0", not "-0.0"
        assert json.dumps(result) == "0.0"

    def test_recurse_dict(self):
        result = _sanitize_float({"a": float("nan"), "b": 1.5})
        assert result == {"a": None, "b": 1.5}

    def test_recurse_list(self):
        result = _sanitize_float([float("inf"), 2.0])
        assert result == [None, 2.0]

    def test_int_passthrough(self):
        assert _sanitize_float(42) == 42

    def test_string_passthrough(self):
        assert _sanitize_float("hello") == "hello"


class TestOmitNone:
    def test_dict_none_omitted(self):
        assert _omit_none({"a": 1, "b": None, "c": 3}) == {"a": 1, "c": 3}

    def test_nested_dict_none_omitted(self):
        assert _omit_none({"outer": {"a": 1, "b": None}}) == {"outer": {"a": 1}}

    def test_list_none_preserved(self):
        """None in lists stays (removing would change indices)."""
        assert _omit_none([1, None, 3]) == [1, None, 3]

    def test_empty_dict(self):
        assert _omit_none({}) == {}

    def test_all_none_dict(self):
        assert _omit_none({"a": None, "b": None}) == {}


class TestCanonicalJsonDumps:
    def test_sorted_keys(self):
        result = canonical_json_dumps({"z": 1, "a": 2})
        assert result == '{"a":2,"z":1}'

    def test_compact_separators(self):
        result = canonical_json_dumps({"a": 1, "b": 2})
        assert " " not in result
        assert result == '{"a":1,"b":2}'

    def test_none_omitted(self):
        result = canonical_json_dumps({"a": 1, "b": None, "c": 3})
        assert result == '{"a":1,"c":3}'

    def test_nested_none_omitted(self):
        result = canonical_json_dumps({"outer": {"a": 1, "b": None}})
        assert result == '{"outer":{"a":1}}'

    def test_float_sanitization_nan(self):
        result = canonical_json_dumps({"val": float("nan"), "ok": 1.5})
        parsed = json.loads(result)
        assert "val" not in parsed
        assert parsed["ok"] == 1.5

    def test_float_sanitization_rounding(self):
        result = canonical_json_dumps({"v": 1.23456789012345})
        parsed = json.loads(result)
        assert parsed["v"] == 1.2345678901

    def test_negative_zero_in_dict(self):
        result = canonical_json_dumps({"v": -0.0})
        assert result == '{"v":0.0}'

    def test_key_order_canonical_bytes(self):
        """Same data, different key order -> identical canonical bytes."""
        a = canonical_json_dumps({"z": 1, "a": 2, "m": 3})
        b = canonical_json_dumps({"a": 2, "m": 3, "z": 1})
        assert a == b

    def test_pinned_bytes_known_input(self):
        """Known input produces exact expected canonical JSON string."""
        obj = {
            "event_type": "DECISION",
            "event_id": "test-1",
            "ts_ms": 1000,
            "payload": {"decision": "ALLOW", "symbol": "BTCUSDT"},
            "schema_version": "envelope.v1",
        }
        expected = (
            '{"event_id":"test-1","event_type":"DECISION",'
            '"payload":{"decision":"ALLOW","symbol":"BTCUSDT"},'
            '"schema_version":"envelope.v1","ts_ms":1000}'
        )
        assert canonical_json_dumps(obj) == expected


class TestSha256Hex:
    def test_deterministic(self):
        assert sha256_hex(b"hello") == sha256_hex(b"hello")

    def test_length(self):
        assert len(sha256_hex(b"test")) == 64

    def test_known_value(self):
        # SHA-256 of empty bytes
        assert (
            sha256_hex(b"")
            == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )


class TestCanonicalHash:
    def test_dict_order_independence(self):
        """Same data, different key order -> same hash."""
        h1 = canonical_hash({"z": 1, "a": 2, "m": 3})
        h2 = canonical_hash({"a": 2, "m": 3, "z": 1})
        assert h1 == h2

    def test_different_data_different_hash(self):
        assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})

    def test_returns_64_hex(self):
        result = canonical_hash({"x": 1})
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_bytes_and_hash_consistency(self):
        """canonical_json_dumps bytes -> sha256_hex == canonical_hash."""
        obj = {"b": 2, "a": 1}
        canonical_bytes = canonical_json_dumps(obj).encode("utf-8")
        assert sha256_hex(canonical_bytes) == canonical_hash(obj)
