"""Tests for ema_trend_follow_v1 backtest runner (#4031 slice 2c)."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    FAST_EMA_PERIOD,
    SLOW_EMA_PERIOD,
    TREND_MIN_MINUTES_BETWEEN_ENTRIES,
)
from services.validation.ema_trend_follow_backtest_runner import (
    run_ema_trend_follow_backtest,
)

pytestmark = pytest.mark.unit


def _candle(ts_ms: int, close: float, *, spread: float = 0.1) -> dict:
    return {
        "symbol": "BTCUSDT",
        "ts_ms": ts_ms,
        "open": close,
        "high": close + spread,
        "low": close - spread,
        "close": close,
        "volume": 1_000.0,
    }


def _ema_crossover_candles() -> list[dict]:
    rows: list[dict] = []
    start_ts = 1_700_000_000_000
    for index in range(120):
        if index < 60:
            close = 100.0
        elif index < 80:
            close = 100.0 + (index - 59) * 1.5
        elif index < 95:
            close = 130.0 - (index - 79) * 2.0
        else:
            close = 100.0
        rows.append(_candle(start_ts + index * 60_000, close))
    return rows


def test_ema_trend_follow_runs_and_closes_trade() -> None:
    report = run_ema_trend_follow_backtest(
        _ema_crossover_candles(),
        code_commit="slice-2c-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "ema_trend_follow_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_ema_trend_follow_frozen_params_in_snapshot() -> None:
    report = run_ema_trend_follow_backtest(
        _ema_crossover_candles(),
        code_commit="slice-2c-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["fast_ema_period"] == FAST_EMA_PERIOD
    assert snapshot["slow_ema_period"] == SLOW_EMA_PERIOD
    assert snapshot["min_minutes_between_entries"] == TREND_MIN_MINUTES_BETWEEN_ENTRIES
    assert snapshot["trade_side_mode"] == "long_only"
