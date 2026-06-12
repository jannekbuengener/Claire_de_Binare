from __future__ import annotations

import json

import pytest

from tools.build_signal_aware_candle_trace import (
    build_signal_aware_trace,
    _regime_str_from_raw,
    _require_int,
)


class TestRegimeStrFromRaw:
    def test_numeric_mapping(self):
        assert _regime_str_from_raw(0) == "TREND"
        assert _regime_str_from_raw(1) == "RANGE"
        assert _regime_str_from_raw(2) == "HIGH_VOL_CHAOTIC"
        assert _regime_str_from_raw(3) == "CRISIS"

    def test_unknown_numeric(self):
        assert _regime_str_from_raw(99) == "UNKNOWN"

    def test_string_mapping(self):
        assert _regime_str_from_raw("trend") == "TREND"
        assert _regime_str_from_raw("RANGE") == "RANGE"

    def test_none(self):
        assert _regime_str_from_raw(None) is None

    def test_bool_is_not_int(self):
        assert _regime_str_from_raw(True) is None


class TestRequireInt:
    def test_valid(self):
        assert _require_int(42, "test") == 42

    def test_none_raises(self):
        with pytest.raises(ValueError, match="test is required"):
            _require_int(None, "test")

    def test_string_raises(self):
        with pytest.raises(ValueError, match="test must be an int"):
            _require_int("abc", "test")


class TestBuildSignalAwareTrace:
    def _make_candles(self, count: int = 5) -> list[dict]:
        return [{"ts_ms": 1000 + i * 100, "regime_id": 0} for i in range(count)]

    def _make_gate_trace(
        self, ts_list: list[int], entry_ready: list[bool]
    ) -> list[dict]:
        return [
            {
                "ts_ms": ts,
                "entry_ready": ready,
                "status": "signal_emitted" if ready else "no_signal",
                "symbol": "BTCUSDT",
                "regime_id": 0,
                "has_trend_regime": True,
            }
            for ts, ready in zip(ts_list, entry_ready)
        ]

    def test_empty_candles_produces_zero_steps(self):
        trace = build_signal_aware_trace([], [])
        assert len(trace["steps"]) == 0
        assert trace["signals_available"] is False
        assert trace["trades_available"] is False
        assert trace["trades"] == []

    def test_empty_gate_trace_all_missing(self):
        candles = self._make_candles(3)
        trace = build_signal_aware_trace(candles, [])
        assert len(trace["steps"]) == 3
        for step in trace["steps"]:
            assert step["buy_signal_attributable"] is False
            assert step["gate_trace_available"] is False
        assert trace["signals_available"] is False

    def test_entry_ready_true_counted_as_buy(self):
        candles = self._make_candles(3)
        gt = self._make_gate_trace([1000, 1100, 1200], [True, False, True])
        trace = build_signal_aware_trace(candles, gt)
        assert trace["signals_available"] is True
        assert trace["steps"][0]["buy_signal_attributable"] is True
        assert trace["steps"][0]["signals_emitted"] == 1
        assert trace["steps"][1]["buy_signal_attributable"] is False
        assert trace["steps"][1]["signals_emitted"] == 0
        assert trace["steps"][2]["buy_signal_attributable"] is True
        assert trace["steps"][2]["signals_emitted"] == 1

    def test_baseline_reconciliation_pass(self):
        candles = self._make_candles(3)
        gt = self._make_gate_trace([1000, 1100, 1200], [True, False, True])
        baseline = {"buy_signals_total": 2, "sell_signals_total": 1}
        trace = build_signal_aware_trace(candles, gt, baseline_metrics=baseline)
        assert trace["signals_available"] is True

    def test_baseline_reconciliation_fail(self):
        candles = self._make_candles(3)
        gt = self._make_gate_trace([1000, 1100, 1200], [True, False, False])
        baseline = {"buy_signals_total": 22}
        trace = build_signal_aware_trace(candles, gt, baseline_metrics=baseline)
        assert trace["signals_available"] is False

    def test_candles_outside_gate_trace_window(self):
        candles = [
            {"ts_ms": 500, "regime_id": 0},
            {"ts_ms": 1000, "regime_id": 0},
            {"ts_ms": 1500, "regime_id": 0},
        ]
        gt = self._make_gate_trace([1000], [False])
        trace = build_signal_aware_trace(candles, gt)
        assert trace["steps"][0]["gate_trace_available"] is False
        assert trace["steps"][0]["buy_signal_attributable"] is False
        assert "gate_trace_status" in trace["steps"][1]
        assert trace["steps"][2]["gate_trace_available"] is False

    def test_separate_attribution_contract(self):
        candles = self._make_candles(3)
        gt = self._make_gate_trace([1000, 1100, 1200], [True, False, True])
        baseline = {"buy_signals_total": 2}
        trace = build_signal_aware_trace(candles, gt, baseline_metrics=baseline)
        assert trace["attribution_contract"]["buy_entry_count"] == 2
        assert trace["attribution_contract"]["baseline_reconciled"] is True
        assert (
            trace["attribution_contract"]["sell_signal_attribution_available"] is False
        )
        assert (
            trace["attribution_contract"]["trade_closure_attribution_available"]
            is False
        )
        assert (
            trace["attribution_contract"]["attribution_scope"] == "entry_gate_buy_only"
        )
        assert trace["attribution_contract"]["natural_paper_evidence"] is False
        assert (
            trace["attribution_contract"]["signal_attribution_availability"]
            == "partial"
        )

    def test_regime_id_preserved(self):
        candles = [
            {"ts_ms": 1000, "regime_id": 0},
            {"ts_ms": 1100, "regime_id": "RANGE"},
        ]
        gt = self._make_gate_trace([1000, 1100], [False, False])
        trace = build_signal_aware_trace(candles, gt)
        assert trace["steps"][0]["regime_id"] == 0
        assert trace["steps"][1]["regime_id"] == "RANGE"

    def test_run_id_passed_through(self):
        trace = build_signal_aware_trace(self._make_candles(1), [], run_id="custom-001")
        assert trace["run_id"] == "custom-001"

    def test_notes_contain_partial_attribution(self):
        candles = self._make_candles(2)
        gt = self._make_gate_trace([1000], [True])
        trace = build_signal_aware_trace(
            candles, gt, baseline_metrics={"buy_signals_total": 1}
        )
        notes = trace.get("notes", [])
        assert any("partial_attribution" in n for n in notes)
        assert any("unavailable_trade_closures" in n for n in notes)

    def test_blocked_input_shape_on_reconciliation_failure(self):
        candles = self._make_candles(2)
        gt = self._make_gate_trace([1000, 1100], [False, False])
        baseline = {"buy_signals_total": 22}
        trace = build_signal_aware_trace(candles, gt, baseline_metrics=baseline)
        assert trace["signals_available"] is False
        assert trace["attribution_contract"]["baseline_reconciled"] is False
        assert trace["attribution_contract"]["buy_entry_count"] == 0
        notes = trace.get("notes", [])
        assert any("blocked_input_shape" in n for n in notes)

    def test_no_baseline_metrics_uses_entry_ready_count(self):
        candles = self._make_candles(3)
        gt = self._make_gate_trace([1000, 1100, 1200], [True, False, True])
        trace = build_signal_aware_trace(candles, gt)
        assert trace["signals_available"] is True
        assert trace["attribution_contract"]["buy_entry_count"] == 2
        assert trace["attribution_contract"]["baseline_reconciled"] is True

    def test_candle_without_regime_id(self):
        candles = [{"ts_ms": 1000}]
        gt = self._make_gate_trace([1000], [False])
        trace = build_signal_aware_trace(candles, gt)
        assert trace["steps"][0]["regime_id"] is None

    def test_trades_always_empty_and_unavailable(self):
        trace = build_signal_aware_trace(self._make_candles(1), [])
        assert trace["trades_available"] is False
        assert trace["trades"] == []
