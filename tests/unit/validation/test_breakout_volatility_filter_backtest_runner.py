"""Tests for breakout_volatility_filter_v1 backtest runner (#4031 slice 2b)."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    ATR_PERIOD,
    ENTRY_CHANNEL_BARS,
    EXIT_CHANNEL_BARS,
    MIN_MINUTES_BETWEEN_ENTRIES,
    VOL_CEILING,
    VOL_FLOOR,
)
from services.validation.breakout_volatility_filter_backtest_runner import (
    run_breakout_volatility_filter_backtest,
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


def _breakout_vol_filter_candles() -> list[dict]:
    rows: list[dict] = []
    start_ts = 1_700_000_000_000
    for index in range(90):
        close = 100.0
        spread = 0.1
        if index == 60:
            close = 101.2
            spread = 0.15
        elif 61 <= index <= 75:
            close = 101.5 + (index - 61) * 0.05
            spread = 0.15
        elif index == 76:
            close = 99.4
            spread = 0.15
        rows.append(_candle(start_ts + index * 60_000, close, spread=spread))
    return rows


def test_breakout_volatility_filter_runs_and_closes_trade() -> None:
    report = run_breakout_volatility_filter_backtest(
        _breakout_vol_filter_candles(),
        code_commit="slice-2b-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "breakout_volatility_filter_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_breakout_volatility_filter_frozen_params_in_snapshot() -> None:
    report = run_breakout_volatility_filter_backtest(
        _breakout_vol_filter_candles(),
        code_commit="slice-2b-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["entry_channel_bars"] == ENTRY_CHANNEL_BARS
    assert snapshot["exit_channel_bars"] == EXIT_CHANNEL_BARS
    assert snapshot["atr_period"] == ATR_PERIOD
    assert snapshot["vol_floor"] == VOL_FLOOR
    assert snapshot["vol_ceiling"] == VOL_CEILING
    assert snapshot["min_minutes_between_entries"] == MIN_MINUTES_BETWEEN_ENTRIES
    assert snapshot["trade_side_mode"] == "long_only"
