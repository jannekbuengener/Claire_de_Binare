from __future__ import annotations

import json
import pytest

from tools.build_candle_trace import build_trace, regime_str_from_raw


class TestRegimeStrFromRaw:
    def test_numeric_mapping(self):
        assert regime_str_from_raw(0) == "TREND"
        assert regime_str_from_raw(1) == "RANGE"
        assert regime_str_from_raw(2) == "HIGH_VOL_CHAOTIC"
        assert regime_str_from_raw(3) == "CRISIS"

    def test_unknown_numeric(self):
        assert regime_str_from_raw(99) == "UNKNOWN"
        assert regime_str_from_raw(-1) == "UNKNOWN"

    def test_string_mapping(self):
        assert regime_str_from_raw("TREND") == "TREND"
        assert regime_str_from_raw("range") == "RANGE"
        assert regime_str_from_raw("High_Vol_Chaotic") == "HIGH_VOL_CHAOTIC"

    def test_none(self):
        assert regime_str_from_raw(None) is None

    def test_bool_is_not_int(self):
        assert regime_str_from_raw(True) is None
        assert regime_str_from_raw(False) is None

    def test_empty_string(self):
        assert regime_str_from_raw("") is None
        assert regime_str_from_raw("  ") is None


class TestBuildTrace:
    def test_empty_candles(self):
        trace = build_trace([])
        assert trace["run_id"].startswith("candle-trace-")
        assert trace["steps"] == []
        assert trace["trades"] == []

    def test_single_candle(self):
        candles = [{"ts_ms": 1000, "regime_id": 0}]
        trace = build_trace(candles)
        assert len(trace["steps"]) == 1
        step = trace["steps"][0]
        assert step["ts_ms"] == 1000
        assert step["regime_id"] == 0
        assert step["signals_emitted"] == 0
        assert trace["trades"] == []

    def test_multiple_candles_different_regimes(self):
        candles = [
            {"ts_ms": 1000, "regime_id": 0},
            {"ts_ms": 2000, "regime_id": 1},
            {"ts_ms": 3000, "regime_id": 2},
        ]
        trace = build_trace(candles)
        assert len(trace["steps"]) == 3
        assert [s["regime_id"] for s in trace["steps"]] == [0, 1, 2]

    def test_candle_without_regime_id(self):
        candles = [{"ts_ms": 1000}]
        trace = build_trace(candles)
        assert trace["steps"][0]["regime_id"] is None

    def test_explicit_run_id(self):
        candles = [{"ts_ms": 1000, "regime_id": 0}]
        trace = build_trace(candles, run_id="my-test-run")
        assert trace["run_id"] == "my-test-run"

    def test_deterministic_run_id(self):
        candles_a = [{"ts_ms": 100, "regime_id": 0}, {"ts_ms": 200, "regime_id": 1}]
        candles_b = [{"ts_ms": 100, "regime_id": 0}, {"ts_ms": 200, "regime_id": 1}]
        trace_a = build_trace(candles_a)
        trace_b = build_trace(candles_b)
        assert trace_a["run_id"] == trace_b["run_id"]

    def test_missing_ts_ms_raises(self):
        with pytest.raises(ValueError, match="ts_ms"):
            build_trace([{"regime_id": 0}])

    def test_invalid_ts_ms_raises(self):
        with pytest.raises(ValueError, match="ts_ms"):
            build_trace([{"ts_ms": "not-a-number", "regime_id": 0}])
