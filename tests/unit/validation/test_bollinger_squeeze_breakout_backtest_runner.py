"""Tests for bollinger_squeeze_breakout_v1 backtest runner (#4031 slice 2b)."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    BB_PERIOD,
    BB_STD_DEV,
    BOLLINGER_MIN_MINUTES_BETWEEN_ENTRIES,
    EXPANSION_CEILING,
    SQUEEZE_BARS_MIN,
    SQUEEZE_THRESHOLD,
)
from services.validation.bollinger_squeeze_breakout_backtest_runner import (
    run_bollinger_squeeze_breakout_backtest,
)

pytestmark = pytest.mark.unit


def _candle(ts_ms: int, close: float, *, spread: float = 0.01) -> dict:
    return {
        "symbol": "BTCUSDT",
        "ts_ms": ts_ms,
        "open": close,
        "high": close + spread,
        "low": close - spread,
        "close": close,
        "volume": 1_000.0,
    }


def _bollinger_squeeze_candles() -> list[dict]:
    rows: list[dict] = []
    start_ts = 1_700_000_000_000
    for index in range(80):
        close = 100.0
        spread = 0.01
        if index == 40:
            close = 100.8
            spread = 0.05
        elif 41 <= index <= 55:
            close = 100.8 + (index - 41) * 0.03
            spread = 0.05
        elif index == 56:
            close = 99.5
            spread = 0.05
        rows.append(_candle(start_ts + index * 60_000, close, spread=spread))
    return rows


def test_bollinger_squeeze_breakout_runs_and_closes_trade() -> None:
    report = run_bollinger_squeeze_breakout_backtest(
        _bollinger_squeeze_candles(),
        code_commit="slice-2b-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "bollinger_squeeze_breakout_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_bollinger_squeeze_breakout_frozen_params_in_snapshot() -> None:
    report = run_bollinger_squeeze_breakout_backtest(
        _bollinger_squeeze_candles(),
        code_commit="slice-2b-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["bb_period"] == BB_PERIOD
    assert snapshot["bb_std_dev"] == BB_STD_DEV
    assert snapshot["squeeze_threshold"] == SQUEEZE_THRESHOLD
    assert snapshot["squeeze_bars_min"] == SQUEEZE_BARS_MIN
    assert snapshot["expansion_ceiling"] == EXPANSION_CEILING
    assert (
        snapshot["min_minutes_between_entries"] == BOLLINGER_MIN_MINUTES_BETWEEN_ENTRIES
    )
    assert snapshot["trade_side_mode"] == "long_only"
