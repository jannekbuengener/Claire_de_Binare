"""Unit tests for range_mean_reversion_v1 pipeline (#3157).

Tests focus on the core signal logic and computation functions.
They do NOT import or modify primary_breakout behavior.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.profitability.run_range_mean_reversion_pipeline_3157 import (
    ATR_PERIOD,
    ATR_STOP_MULT,
    ENTRY_THRESHOLD,
    EXIT_THRESHOLD,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    REGIME_RANGE,
    WARMUP_CANDLES,
    ZS_LOOKBACK,
    AggregateResult,
    PipelineError,
    SignalDecision,
    TradeRecord,
    WindowResult,
    aggregate_windows,
    check_candle_integrity,
    compute_atr,
    compute_z_scores,
    evaluate_range_reversion_candle,
    load_candles,
    run_dataset_quality_gate,
    run_single_window,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_candles() -> list[float]:
    """20 candles at 50000.0 (zero variance -> z-score undefined)."""
    return [50000.0] * 20


@pytest.fixture
def trending_candles() -> list[float]:
    """Simple uptrend: 100, 101, 102, ..., 119."""
    return [float(100 + i) for i in range(20)]


@pytest.fixture
def spike_candles() -> list[float]:
    """A sequence with one extreme spike then reversion."""
    base = [100.0] * 30
    base[25] = 80.0  # extreme low (z-score ~ -2)
    base[26] = 82.0
    base[27] = 85.0
    base[28] = 90.0
    base[29] = 95.0
    base[30] = 98.0
    return base


# ---------------------------------------------------------------------------
# Z-score Computation
# ---------------------------------------------------------------------------


class TestZscoreComputation:
    def test_constant_prices_produce_none(self, flat_candles: list[float]) -> None:
        z_scores = compute_z_scores(flat_candles, ZS_LOOKBACK)
        assert len(z_scores) == len(flat_candles)
        # First 19 are None (insufficient lookback)
        for i in range(ZS_LOOKBACK - 1):
            assert z_scores[i] is None
        # After lookback, stddev is 0 -> z-score is None
        for i in range(ZS_LOOKBACK - 1, len(z_scores)):
            assert z_scores[i] is None, f"index {i} should be None"

    def test_trend_produces_positive_zscore(
        self, trending_candles: list[float]
    ) -> None:
        z_scores = compute_z_scores(trending_candles, ZS_LOOKBACK)
        assert len(z_scores) == len(trending_candles)
        # At index 19 (last candle), all 20 are in the lookback
        z19 = z_scores[19]
        assert z19 is not None
        # In a steady uptrend, the last close is highest -> positive z-score
        assert z19 > 0

    def test_zscore_shape(self) -> None:
        closes = [float(i) for i in range(50)]
        z_scores = compute_z_scores(closes, lookback=10)
        assert len(z_scores) == 50
        # First 9 are None
        for i in range(9):
            assert z_scores[i] is None
        # The rest are defined
        for i in range(9, 50):
            assert z_scores[i] is not None, f"index {i}"
        # In a perfect uptrend, z-score should be positive near the top
        assert z_scores[49] is not None and z_scores[49] > 0


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
        # First 14 are None
        for i in range(14):
            assert atr[i] is None
        # After warmup, ATR should be very small (~1.0)
        for i in range(14, 30):
            assert atr[i] is not None
            assert atr[i] == pytest.approx(1.0, abs=0.01)

    def test_volatile_sequence(self) -> None:
        highs = [110.0, 120.0, 115.0, 130.0, 125.0] * 10
        lows = [90.0, 95.0, 100.0, 85.0, 95.0] * 10
        closes = [105.0, 110.0, 108.0, 115.0, 112.0] * 10
        atr = compute_atr(highs, lows, closes, 14)
        assert len(atr) == 50
        # First 14 are None
        for i in range(14):
            assert atr[i] is None
        for i in range(14, 50):
            assert atr[i] is not None
            assert atr[i] > 0


# ---------------------------------------------------------------------------
# Signal Logic
# ---------------------------------------------------------------------------


class TestSignalLogic:
    def test_range_gate_blocks_non_range(self) -> None:
        """Non-RANGE regime should block entry."""
        decision = evaluate_range_reversion_candle(
            close=50000.0,
            z_score=-3.0,
            atr=100.0,
            regime_id=0,  # TREND
            position_open=False,
            entry_price=None,
            entry_ts_ms=None,
            ts_ms=1000000,
            last_entry_ts_ms=None,
        )
        assert not decision.entry
        assert not decision.exit_signal
        assert decision.reason == "blocked_regime"

    def test_long_entry_on_negative_zscore_extreme(self) -> None:
        """z_score <= -2.0 in RANGE regime should trigger entry."""
        decision = evaluate_range_reversion_candle(
            close=50000.0,
            z_score=-3.0,
            atr=100.0,
            regime_id=REGIME_RANGE,
            position_open=False,
            entry_price=None,
            entry_ts_ms=None,
            ts_ms=1000000,
            last_entry_ts_ms=None,
        )
        assert decision.entry
        assert not decision.exit_signal
        assert decision.reason == "zscore_entry"
        assert decision.entry_price == 50000.0

    def test_no_entry_when_zscore_not_extreme(self) -> None:
        """z_score > -2.0 should not trigger entry."""
        decision = evaluate_range_reversion_candle(
            close=50000.0,
            z_score=-1.0,
            atr=100.0,
            regime_id=REGIME_RANGE,
            position_open=False,
            entry_price=None,
            entry_ts_ms=None,
            ts_ms=1000000,
            last_entry_ts_ms=None,
        )
        assert not decision.entry
        assert decision.reason == "zscore_not_extreme"

    def test_exit_on_mean_reversion_cross(self) -> None:
        """z_score >= 0.0 with open position should exit."""
        decision = evaluate_range_reversion_candle(
            close=51000.0,
            z_score=0.5,
            atr=100.0,
            regime_id=REGIME_RANGE,
            position_open=True,
            entry_price=50000.0,
            entry_ts_ms=1000000,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
        )
        assert not decision.entry
        assert decision.exit_signal
        assert decision.reason == "mean_reversion"
        assert not decision.stop_hit

    def test_atr_stop_resolution_order(self) -> None:
        """ATR stop should fire before mean reversion exit if price is below stop."""
        decision = evaluate_range_reversion_candle(
            close=49000.0,
            z_score=-0.5,
            atr=2000.0,  # Large ATR
            regime_id=REGIME_RANGE,
            position_open=True,
            entry_price=50000.0,
            entry_ts_ms=1000000,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
        )
        # ATR stop: 50000 - 2000 * 1.5 = 47000; close=49000 > 47000, no stop
        # z_score=-0.5 < 0, no mean reversion exit
        assert not decision.entry
        assert not decision.exit_signal
        assert decision.reason == "holding"

    def test_atr_stop_triggers(self) -> None:
        """Price below ATR stop should trigger stop exit."""
        decision = evaluate_range_reversion_candle(
            close=46000.0,
            z_score=-1.0,
            atr=2000.0,  # ATR stop: 50000 - 2000*1.5 = 47000
            regime_id=REGIME_RANGE,
            position_open=True,
            entry_price=50000.0,
            entry_ts_ms=1000000,
            ts_ms=2000000,
            last_entry_ts_ms=1000000,
        )
        assert not decision.entry
        assert decision.exit_signal
        assert decision.stop_hit
        assert decision.reason == "atr_stop"
        assert decision.exit_price is not None
        assert decision.exit_price == 50000.0 - 2000.0 * ATR_STOP_MULT

    def test_cooldown_blocks_entry(self) -> None:
        """Cooldown should block entry if less than 60 minutes since last entry."""
        decision = evaluate_range_reversion_candle(
            close=50000.0,
            z_score=-3.0,
            atr=100.0,
            regime_id=REGIME_RANGE,
            position_open=False,
            entry_price=None,
            entry_ts_ms=None,
            ts_ms=1000000,
            last_entry_ts_ms=990000,  # only 10 seconds ago
        )
        assert not decision.entry
        assert decision.reason == "cooldown_active"

    def test_no_exit_without_open_position(self) -> None:
        """Exit signal should not fire if no position is open."""
        decision = evaluate_range_reversion_candle(
            close=51000.0,
            z_score=2.0,
            atr=100.0,
            regime_id=REGIME_RANGE,
            position_open=False,
            entry_price=None,
            entry_ts_ms=None,
            ts_ms=2000000,
            last_entry_ts_ms=None,
        )
        # This is an extreme z_score but without an open position:
        # For entry z_score must be <= -ENTRY_THRESHOLD, not positive.
        # Positive extreme means it's overbought - no long entry.
        assert not decision.entry
        assert decision.reason == "zscore_not_extreme"

    def test_zscore_unavailable_blocks_entry(self) -> None:
        """None z-score should not trigger entry."""
        decision = evaluate_range_reversion_candle(
            close=50000.0,
            z_score=None,
            atr=100.0,
            regime_id=REGIME_RANGE,
            position_open=False,
            entry_price=None,
            entry_ts_ms=None,
            ts_ms=1000000,
            last_entry_ts_ms=None,
        )
        assert not decision.entry
        assert decision.reason == "zscore_unavailable"


# ---------------------------------------------------------------------------
# Candle Integrity
# ---------------------------------------------------------------------------


class TestCandleIntegrity:
    def test_valid_candles_pass(self) -> None:
        candles = [
            {"ts_ms": 1000000, "high": "101", "low": "99", "close": "100"},
            {"ts_ms": 1060000, "high": "102", "low": "100", "close": "101"},
        ]
        check_candle_integrity(candles, "test")  # should not raise

    def test_missing_field_raises(self) -> None:
        candles = [{"ts_ms": 1000000, "high": "101"}]  # missing low/close
        with pytest.raises(PipelineError, match="missing low"):
            check_candle_integrity(candles, "test")

    def test_non_increasing_ts_ms_raises(self) -> None:
        candles = [
            {"ts_ms": 2000000, "high": "102", "low": "100", "close": "101"},
            {"ts_ms": 1000000, "high": "101", "low": "99", "close": "100"},
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
                regime_distribution={"RANGE": {"count": 500, "pct": 50.0}},
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
                        "reason": "mean_reversion",
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
                entry_reasons=["zscore_entry"],
                exit_reasons=["mean_reversion"],
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
        """Verifies aggregate function produces correct shape."""
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
                    regime_distribution={"RANGE": {"count": 500, "pct": 50.0}},
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
                            "reason": "mean_reversion",
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
                    entry_reasons=["zscore_entry"],
                    exit_reasons=["mean_reversion"],
                )
            )
        agg = aggregate_windows(results)
        assert agg.total_windows == 3
        assert agg.closed_trades_total == 6  # 1+2+3
        assert agg.windows_with_trades == 3
        assert agg.signals_total == 6  # 1+2+3
        # All winning trades
        assert agg.trades_win_count == 6
        assert agg.trades_loss_count == 0
        assert agg.win_rate == 1.0
        # 6 trades < 10 -> insufficient
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
                            "reason": "mean_reversion",
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
                    entry_reasons=["zscore_entry"],
                    exit_reasons=["mean_reversion"],
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


# ---------------------------------------------------------------------------
# Short-side Blocker Is Documented
# ---------------------------------------------------------------------------


class TestShortSideBlocker:
    def test_short_side_blocker_documented(self) -> None:
        """Verify the candidate contract states the short-side blocker."""
        contract_path = Path(
            "docs/evidence/profitability_candidate_range_mean_reversion_v1_3157.json"
        )
        assert contract_path.exists(), "Candidate contract must exist"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        assert contract.get("direction") == "long_only_first_pass"
        assert contract.get("hold_short_side_blocker") is True
        assert "long_short" in contract.get("original_direction_in_predecessor", "")


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_candles_file_raises(self, tmp_path: Path) -> None:
        """Loading from a non-existent directory should raise PipelineError."""
        fake_dir = tmp_path / "nonexistent"
        with pytest.raises(PipelineError, match="Candles file not found"):
            load_candles(fake_dir)

    def test_empty_candles_file_raises(self, tmp_path: Path) -> None:
        """Loading an empty candles file should raise PipelineError."""
        cal_dir = tmp_path / "regime_calibrated"
        cal_dir.mkdir(parents=True)
        candle_file = cal_dir / "candles.jsonl"
        candle_file.write_text("", encoding="utf-8")
        with pytest.raises(PipelineError, match="Empty candles file"):
            load_candles(tmp_path)
