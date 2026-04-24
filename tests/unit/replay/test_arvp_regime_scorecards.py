"""Unit tests for core/replay/arvp_regime_scorecards.py (#1904)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.replay.arvp_regime_scorecards import (
    ARVPRegimeScorecardError,
    build_comparison_regime_scorecard_or_unavailable,
    build_replay_regime_scorecard_from_trace,
    build_scorecard_summary,
)


def test_multiple_regimes_with_distinct_metrics() -> None:
    trace = {
        "run_id": "replay-aabbccddee11-0001",
        "steps": [
            {"ts_ms": 1, "regime_id": 0, "signals_emitted": 1},  # TREND
            {"ts_ms": 2, "regime_id": 1, "signals_emitted": 0},  # RANGE
            {"ts_ms": 3, "regime_id": 1, "signals_emitted": 2},  # RANGE
        ],
        "trades": [
            {"exit_ts_ms": 3, "exit_regime_id": 1, "r_return": "0.10"},
            {"exit_ts_ms": 2, "exit_regime_id": 0, "r_return": "-0.05"},
        ],
    }
    scorecard = build_replay_regime_scorecard_from_trace(trace)
    assert scorecard.status == "ok"
    assert scorecard.run_id == "replay-aabbccddee11-0001"
    assert {s.regime_id for s in scorecard.segments} == {"TREND", "RANGE"}

    trend = next(s for s in scorecard.segments if s.regime_id == "TREND")
    assert trend.observation_count == 1
    assert trend.signal_count == 1
    assert trend.trade_close_count == 1
    assert trend.pnl_sum_r == Decimal("-0.05")

    rng = next(s for s in scorecard.segments if s.regime_id == "RANGE")
    assert rng.observation_count == 2
    assert rng.signal_count == 2
    assert rng.trade_close_count == 1
    assert rng.pnl_sum_r == Decimal("0.10")


def test_missing_regime_data_is_unavailable() -> None:
    trace = {
        "run_id": "replay-aabbccddee11-0001",
        "steps": [{"ts_ms": 1, "regime_id": None, "signals_emitted": 1}],
        "trades": [],
    }
    scorecard = build_replay_regime_scorecard_from_trace(trace)
    assert scorecard.status == "unavailable"
    assert any("no regime_id" in n for n in scorecard.notes)


def test_comparison_aware_regime_output_when_supported() -> None:
    comparison = {
        "status": "aligned",
        "regime_segments": [
            {
                "regime_id": "TREND",
                "observation_count": 10,
                "signal_count": 3,
                "trade_close_count": 1,
                "pnl_sum_r": "0.01",
            }
        ],
    }
    scorecard = build_comparison_regime_scorecard_or_unavailable(
        comparison, run_id="replay-aabbccddee11-0001"
    )
    assert scorecard.status == "ok"
    assert scorecard.source == "comparison"
    assert len(scorecard.segments) == 1
    assert scorecard.segments[0].regime_id == "TREND"


def test_summary_generation_contains_table() -> None:
    trace = {
        "run_id": "replay-aabbccddee11-0001",
        "steps": [{"ts_ms": 1, "regime_id": 0, "signals_emitted": 1}],
        "trades": [],
    }
    scorecard = build_replay_regime_scorecard_from_trace(trace)
    summary = build_scorecard_summary(scorecard)
    assert "| Regime | Observations | Signals |" in summary
    assert "TREND" in summary


def test_trace_rejects_invalid_shape() -> None:
    with pytest.raises(ARVPRegimeScorecardError, match="steps must be a list"):
        build_replay_regime_scorecard_from_trace({"run_id": "x", "steps": {}, "trades": []})  # type: ignore[arg-type]

