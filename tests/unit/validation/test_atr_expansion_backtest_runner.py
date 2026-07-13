"""Tests for atr_expansion_v1 backtest runner (#4031 slice 2b)."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    ATR_EXPANSION_MIN_MINUTES_BETWEEN_ENTRIES,
    ATR_PERIOD,
    ATR_RATIO_EXIT,
    ATR_RATIO_THRESHOLD,
    SMA_PERIOD,
)
from services.validation.atr_expansion_backtest_runner import run_atr_expansion_backtest

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


def _atr_expansion_candles() -> list[dict]:
    rows: list[dict] = []
    start_ts = 1_700_000_000_000
    for index in range(100):
        close = 100.0 + index * 0.01
        spread = 0.08
        if 55 <= index <= 65:
            spread = 0.35
        elif index == 70:
            close = 100.0
            spread = 0.05
        elif 71 <= index <= 80:
            close = 100.0 - (index - 71) * 0.05
            spread = 0.05
        rows.append(_candle(start_ts + index * 60_000, close, spread=spread))
    return rows


def test_atr_expansion_runs_and_closes_trade() -> None:
    report = run_atr_expansion_backtest(
        _atr_expansion_candles(),
        code_commit="slice-2b-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "atr_expansion_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_atr_expansion_frozen_params_in_snapshot() -> None:
    report = run_atr_expansion_backtest(
        _atr_expansion_candles(),
        code_commit="slice-2b-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["atr_period"] == ATR_PERIOD
    assert snapshot["atr_ratio_threshold"] == ATR_RATIO_THRESHOLD
    assert snapshot["atr_ratio_exit"] == ATR_RATIO_EXIT
    assert snapshot["sma_period"] == SMA_PERIOD
    assert (
        snapshot["min_minutes_between_entries"]
        == ATR_EXPANSION_MIN_MINUTES_BETWEEN_ENTRIES
    )
    assert snapshot["trade_side_mode"] == "long_only"
