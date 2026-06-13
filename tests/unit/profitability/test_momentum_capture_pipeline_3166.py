"""Unit tests for momentum_capture_v1 pipeline (#3166).

Tests focus on the core signal logic and computation functions.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.profitability.run_momentum_capture_pipeline_3166 import (
    ATR_PERIOD,
    DIRECTIONAL_CANDLE_ATR_MULTIPLE,
    EXIT_ATR_CONTRACTION_MULTIPLE,
    EXIT_TRAILING_STOP_ATR_MULTIPLE,
    MAX_HOLD_BARS,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    REGIME_HVC,
    WARMUP_CANDLES,
    AggregateResult,
    PipelineError,
    SignalDecision,
    TradeRecord,
    WindowResult,
    aggregate_windows,
    check_candle_integrity,
    compute_atr,
    evaluate_momentum_capture_candle,
    load_candles,
    run_dataset_quality_gate,
    run_single_window,
)


@pytest.fixture
def flat_candles() -> list[float]:
    return [50000.0] * 20


# ---------------------------------------------------------------------------
# ATR Computation
# ---------------------------------------------------------------------------


class TestATRComputation:
    def test_constant_prices_produce_zero_atr(self) -> None:
        highs = [100.0] * 30
        lows = [99.0] * 30
        closes = [99.5] * 30
        atr = compute_atr(highs, lows, closes, 14)
        assert len(atr) == 30
        for i in range(14):
            assert atr[i] is None
        for i in range(14, 30):
            assert atr[i] is not None
            assert atr[i] == pytest.approx(1.0, abs=0.01)

    def test_volatile_sequence(self) -> None:
        highs = [110.0, 120.0, 115.0, 130.0, 125.0] * 10
        lows = [90.0, 95.0, 100.0, 85.0, 95.0] * 10
        closes = [105.0, 110.0, 108.0, 115.0, 112.0] * 10
        atr = compute_atr(highs, lows, closes, 14)
        assert len(atr) == 50
        for i in range(14):
            assert atr[i] is None
        for i in range(14, 50):
            assert atr[i] is not None
            assert atr[i] > 0


# ---------------------------------------------------------------------------
# Signal Logic
# ---------------------------------------------------------------------------


class TestSignalLogic:
    def test_hvc_gate_blocks_non_hvc(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50000.0,
            open_price=49900.0,
            atr=100.0,
            regime_id=0,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=0,
        )
        assert not decision.entry
        assert not decision.exit_signal
        assert decision.reason == "blocked_regime"

    def test_blocked_in_range(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50000.0,
            open_price=49900.0,
            atr=100.0,
            regime_id=1,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=1,
        )
        assert not decision.entry
        assert decision.reason == "blocked_regime"

    def test_bearish_candle_blocked(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=49900.0,
            open_price=50000.0,
            atr=100.0,
            regime_id=REGIME_HVC,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=REGIME_HVC,
        )
        assert not decision.entry
        assert decision.reason == "bearish_candle"

    def test_small_body_blocked(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50010.0,
            open_price=50000.0,
            atr=100.0,
            regime_id=REGIME_HVC,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=REGIME_HVC,
        )
        assert not decision.entry
        assert decision.reason == "body_too_small"

    def test_entry_on_bullish_directional_candle(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50200.0,
            open_price=50000.0,
            atr=150.0,
            regime_id=REGIME_HVC,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=REGIME_HVC,
        )
        assert decision.entry
        assert not decision.exit_signal
        assert decision.reason == "directional_momentum_entry"
        assert decision.entry_price == 50200.0

    def test_exit_on_atr_contraction(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50100.0,
            open_price=50050.0,
            atr=50.0,
            regime_id=REGIME_HVC,
            position_open=True,
            entry_price=50000.0,
            entry_atr=100.0,
            entry_ts_ms=1000000,
            hold_bars=10,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
            current_market_regime=REGIME_HVC,
        )
        # atr=50 < 100 * 0.6 = 60 -> contraction exit
        assert not decision.entry
        assert decision.exit_signal
        assert decision.reason == "atr_contraction"
        assert not decision.stop_hit

    def test_exit_on_trailing_stop(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=49500.0,
            open_price=49600.0,
            atr=200.0,
            regime_id=REGIME_HVC,
            position_open=True,
            entry_price=50000.0,
            entry_atr=200.0,
            entry_ts_ms=1000000,
            hold_bars=10,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
            current_market_regime=REGIME_HVC,
        )
        # stop = 50000 - 200 * 0.5 = 49900; close=49500 <= 49900 -> stop hit
        assert not decision.entry
        assert decision.exit_signal
        assert decision.reason == "trailing_stop"
        assert decision.stop_hit

    def test_exit_on_max_hold(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50500.0,
            open_price=50400.0,
            atr=100.0,
            regime_id=REGIME_HVC,
            position_open=True,
            entry_price=50000.0,
            entry_atr=100.0,
            entry_ts_ms=1000000,
            hold_bars=MAX_HOLD_BARS,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
            current_market_regime=REGIME_HVC,
        )
        assert not decision.entry
        assert decision.exit_signal
        assert decision.reason == "max_hold"
        assert not decision.stop_hit

    def test_no_exit_while_holding_within_bounds(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50100.0,
            open_price=50050.0,
            atr=100.0,
            regime_id=REGIME_HVC,
            position_open=True,
            entry_price=50000.0,
            entry_atr=100.0,
            entry_ts_ms=1000000,
            hold_bars=10,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
            current_market_regime=REGIME_HVC,
        )
        # atr=100, no contraction (100 >= 100*0.6)
        # stop=50000-100*0.5=49950, close=50100 > 49950, no stop
        # hold_bars=10 < 240, no max hold
        assert not decision.entry
        assert not decision.exit_signal
        assert decision.reason == "holding"

    def test_cooldown_blocks_entry(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50200.0,
            open_price=50000.0,
            atr=150.0,
            regime_id=REGIME_HVC,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=990000,
            current_market_regime=REGIME_HVC,
        )
        assert not decision.entry
        assert decision.reason == "cooldown_active"

    def test_atr_unavailable_blocks_entry(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=50200.0,
            open_price=50000.0,
            atr=None,
            regime_id=REGIME_HVC,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=REGIME_HVC,
        )
        assert not decision.entry
        assert decision.reason == "atr_unavailable"

    def test_no_exit_without_open_position(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=49500.0,
            open_price=49600.0,
            atr=200.0,
            regime_id=REGIME_HVC,
            position_open=False,
            entry_price=None,
            entry_atr=None,
            entry_ts_ms=None,
            hold_bars=0,
            ts_ms=1000000,
            last_entry_ts_ms=None,
            current_market_regime=REGIME_HVC,
        )
        assert not decision.entry
        assert not decision.exit_signal

    def test_contract_exit_precedence(self) -> None:
        decision = evaluate_momentum_capture_candle(
            close=49500.0,
            open_price=49600.0,
            atr=50.0,
            regime_id=REGIME_HVC,
            position_open=True,
            entry_price=50000.0,
            entry_atr=100.0,
            entry_ts_ms=1000000,
            hold_bars=10,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
            current_market_regime=REGIME_HVC,
        )
        # atr=50 < 100*0.6=60 -> contraction exit
        # stop=50000-50*0.5=49950; close=49500 <= 49950 -> trailing stop also fires
        # trailing_stop checked first in the function
        assert not decision.entry
        assert decision.exit_signal
        assert decision.reason == "trailing_stop"
        assert decision.stop_hit


# ---------------------------------------------------------------------------
# Candle Integrity
# ---------------------------------------------------------------------------


class TestCandleIntegrity:
    def test_valid_candles_pass(self) -> None:
        candles = [
            {"ts_ms": 1000000, "high": "101", "low": "99", "close": "100", "open": "99"},
            {"ts_ms": 1060000, "high": "102", "low": "100", "close": "101", "open": "100"},
        ]
        check_candle_integrity(candles, "test")

    def test_missing_field_raises(self) -> None:
        candles = [{"ts_ms": 1000000, "high": "101"}]
        with pytest.raises(PipelineError, match="missing "):
            check_candle_integrity(candles, "test")

    def test_non_increasing_ts_ms_raises(self) -> None:
        candles = [
            {"ts_ms": 2000000, "high": "102", "low": "100", "close": "101", "open": "100"},
            {"ts_ms": 1000000, "high": "101", "low": "99", "close": "100", "open": "99"},
        ]
        with pytest.raises(PipelineError, match="ts_ms not increasing"):
            check_candle_integrity(candles, "test")


# ---------------------------------------------------------------------------
# Aggregate Economics Shape
# ---------------------------------------------------------------------------


class TestAggregateEconomics:
    def test_empty_results(self) -> None:
        agg = aggregate_windows([])
        assert agg.total_windows == 0
        assert agg.closed_trades_total == 0
        assert agg.sample_size_verdict == "no_trades"

    def test_single_trade(self) -> None:
        results = [
            WindowResult(
                window_id="test",
                source_segment_id=1,
                row_count=1000,
                start_ts_ms=0,
                end_ts_ms=1000000,
                effective_candle_count=760,
                regime_distribution={"HIGH_VOL_CHAOTIC": {"count": 300, "pct": 30.0}},
                signals_total=1,
                closed_trades_total=1,
                trades=[
                    {
                        "entry_ts_ms": 100000,
                        "exit_ts_ms": 200000,
                        "entry_price": 100.0,
                        "exit_price": 102.0,
                        "entry_fee": 0.1,
                        "exit_fee": 0.1,
                        "r_return": 0.02,
                        "reason": "trailing_stop",
                    }
                ],
                gross_pnl_quote=2.0,
                net_pnl_quote=1.8,
                fees_total_quote=0.2,
                gross_return_r=0.02,
                fee_adjusted_return_r=0.018,
                profit_factor=0.0,
                expectancy_r=0.02,
                fee_adjusted_expectancy_r=0.018,
                fee_adjusted_profit_factor=0.0,
                max_drawdown_r=0.0,
                win_rate=1.0,
                avg_win_r=0.02,
                avg_loss_r=None,
                trades_win_count=1,
                trades_loss_count=0,
                sample_size_verdict="insufficient",
                data_integrity_ok=True,
                entry_reasons=["directional_momentum_entry"],
                exit_reasons=["trailing_stop"],
            )
        ]
        agg = aggregate_windows(results)
        assert agg.total_windows == 1
        assert agg.closed_trades_total == 1
        assert agg.windows_with_trades == 1
        assert agg.gross_pnl_quote == pytest.approx(2.0)
        assert agg.net_pnl_quote == pytest.approx(1.8)
        assert agg.sample_size_verdict == "insufficient"

    def test_aggregate_shape_multiple_windows(self) -> None:
        results = []
        for i in range(3):
            results.append(
                WindowResult(
                    window_id=f"window_{i:03d}",
                    source_segment_id=i,
                    row_count=1000,
                    start_ts_ms=0,
                    end_ts_ms=1000000,
                    effective_candle_count=760,
                    regime_distribution={"HIGH_VOL_CHAOTIC": {"count": 300, "pct": 30.0}},
                    signals_total=i + 1,
                    closed_trades_total=i + 1,
                    trades=[
                        {
                            "entry_ts_ms": 100000,
                            "exit_ts_ms": 200000,
                            "entry_price": 100.0,
                            "exit_price": 100.5,
                            "entry_fee": 0.1,
                            "exit_fee": 0.1,
                            "r_return": 0.005,
                            "reason": "atr_contraction",
                        }
                        for _ in range(i + 1)
                    ],
                    gross_pnl_quote=float(i + 1) * 0.5,
                    net_pnl_quote=float(i + 1) * 0.3,
                    fees_total_quote=float(i + 1) * 0.2,
                    gross_return_r=float(i + 1) * 0.005,
                    fee_adjusted_return_r=float(i + 1) * 0.004,
                    profit_factor=0.0,
                    expectancy_r=0.005,
                    fee_adjusted_expectancy_r=0.004,
                    fee_adjusted_profit_factor=0.0,
                    max_drawdown_r=0.0,
                    win_rate=1.0,
                    avg_win_r=0.005,
                    avg_loss_r=None,
                    trades_win_count=i + 1,
                    trades_loss_count=0,
                    sample_size_verdict="insufficient",
                    data_integrity_ok=True,
                    entry_reasons=["directional_momentum_entry"],
                    exit_reasons=["atr_contraction"],
                )
            )
        agg = aggregate_windows(results)
        assert agg.total_windows == 3
        assert agg.closed_trades_total == 6
        assert agg.windows_with_trades == 3
        assert agg.signals_total == 6
        assert agg.trades_win_count == 6
        assert agg.trades_loss_count == 0
        assert agg.win_rate == 1.0
        assert agg.sample_size_verdict == "insufficient"


# ---------------------------------------------------------------------------
# Dataset Quality Gate
# ---------------------------------------------------------------------------


class TestDatasetQualityGate:
    def test_pass_with_20_trades(self) -> None:
        results = []
        for i in range(20):
            results.append(
                WindowResult(
                    window_id=f"w{i}",
                    source_segment_id=i,
                    row_count=1000,
                    start_ts_ms=0,
                    end_ts_ms=1000000,
                    effective_candle_count=760,
                    regime_distribution={},
                    signals_total=1,
                    closed_trades_total=1,
                    trades=[
                        {
                            "entry_ts_ms": 0,
                            "exit_ts_ms": 1,
                            "entry_price": 100.0,
                            "exit_price": 101.0,
                            "entry_fee": 0.0,
                            "exit_fee": 0.0,
                            "r_return": 0.01,
                            "reason": "atr_contraction",
                        }
                    ],
                    gross_pnl_quote=1.0,
                    net_pnl_quote=1.0,
                    fees_total_quote=0.0,
                    gross_return_r=0.01,
                    fee_adjusted_return_r=0.01,
                    profit_factor=0.0,
                    expectancy_r=0.01,
                    fee_adjusted_expectancy_r=0.01,
                    fee_adjusted_profit_factor=0.0,
                    max_drawdown_r=0.0,
                    win_rate=1.0,
                    avg_win_r=0.01,
                    avg_loss_r=None,
                    trades_win_count=1,
                    trades_loss_count=0,
                    sample_size_verdict="insufficient",
                    data_integrity_ok=True,
                    entry_reasons=["directional_momentum_entry"],
                    exit_reasons=["atr_contraction"],
                )
            )
        agg = AggregateResult(
            total_windows=20,
            windows_with_trades=20,
            signals_total=20,
            closed_trades_total=20,
            trades_win_count=20,
            trades_loss_count=0,
            win_rate=1.0,
            gross_pnl_quote=20.0,
            net_pnl_quote=20.0,
            fees_total_quote=0.0,
            gross_return_r=0.2,
            fee_adjusted_return_r=0.2,
            profit_factor=0.0,
            expectancy_r=0.01,
            fee_adjusted_expectancy_r=0.01,
            fee_adjusted_profit_factor=0.0,
            max_drawdown_r=0.0,
            avg_win_r=0.01,
            avg_loss_r=None,
            sample_size_verdict="pass",
        )
        gate = run_dataset_quality_gate(results, agg)
        assert gate["status"] == "PASS"
        assert gate["passed"] is True

    def test_fail_with_few_trades(self) -> None:
        agg = AggregateResult(
            total_windows=1,
            windows_with_trades=1,
            signals_total=1,
            closed_trades_total=1,
            trades_win_count=0,
            trades_loss_count=1,
            win_rate=0.0,
            gross_pnl_quote=-1.0,
            net_pnl_quote=-1.2,
            fees_total_quote=0.2,
            gross_return_r=-0.01,
            fee_adjusted_return_r=-0.012,
            profit_factor=0.0,
            expectancy_r=-0.01,
            fee_adjusted_expectancy_r=-0.012,
            fee_adjusted_profit_factor=0.0,
            max_drawdown_r=0.01,
            avg_win_r=None,
            avg_loss_r=-0.01,
            sample_size_verdict="insufficient",
        )
        gate = run_dataset_quality_gate([], agg)
        assert gate["status"] == "FAIL"
        assert gate["passed"] is False
        assert any("closed_trades_total" in f for f in gate["findings"])


# ---------------------------------------------------------------------------
# Contract Exists
# ---------------------------------------------------------------------------


class TestContractExists:
    def test_candidate_contract_exists(self) -> None:
        contract_path = Path(
            "docs/evidence/profitability_candidate_momentum_capture_v1_3166.json"
        )
        assert contract_path.exists(), "Candidate contract must exist"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        assert contract.get("direction") == "long_only_first_pass"
        assert contract["candidate_id"] == "cand-momentum-capture-v1-btcusdt-mexc"
        assert contract["strategy_id"] == "momentum_capture_v1"
        assert contract["evidence_class"] == "controlled_lab_evidence"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_candles_file_raises(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "nonexistent"
        with pytest.raises(PipelineError, match="Candles file not found"):
            load_candles(fake_dir)

    def test_empty_candles_file_raises(self, tmp_path: Path) -> None:
        cal_dir = tmp_path / "regime_calibrated"
        cal_dir.mkdir(parents=True)
        candle_file = cal_dir / "candles.jsonl"
        candle_file.write_text("", encoding="utf-8")
        with pytest.raises(PipelineError, match="Empty candles file"):
            load_candles(tmp_path)

    def test_atr_zero_for_flat_prices(self) -> None:
        highs = [50000.0] * 30
        lows = [50000.0] * 30
        closes = [50000.0] * 30
        atr = compute_atr(highs, lows, closes, 14)
        for i in range(14, 30):
            assert atr[i] is not None
            assert atr[i] == 0.0
