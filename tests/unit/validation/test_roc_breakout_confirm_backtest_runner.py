"""Tests for roc_breakout_confirm_v1 backtest runner (#4031 slice 2d)."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    BREAKOUT_LOOKBACK,
    EXIT_LOOKBACK,
    ROC_ENTRY_THRESHOLD,
    ROC_EXIT_THRESHOLD,
    ROC_MIN_MINUTES_BETWEEN_ENTRIES,
    ROC_PERIOD,
)
from services.validation.roc_breakout_confirm_backtest_runner import (
    run_roc_breakout_confirm_backtest,
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


def _roc_breakout_candles() -> list[dict]:
    rows: list[dict] = []
    start_ts = 1_700_000_000_000
    for index in range(90):
        close = 100.0
        spread = 0.05
        if 30 <= index < 55:
            close = 100.0 + (index - 30) * 0.08
            spread = 0.08
        elif index == 55:
            close = 102.5
            spread = 0.5
        elif 56 <= index <= 70:
            close = 102.5 + (index - 56) * 0.04
            spread = 0.3
        elif index == 71:
            close = 99.0
            spread = 0.4
        rows.append(_candle(start_ts + index * 60_000, close, spread=spread))
    return rows


def test_roc_breakout_runs_and_closes_trade() -> None:
    report = run_roc_breakout_confirm_backtest(
        _roc_breakout_candles(),
        code_commit="slice-2d-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "roc_breakout_confirm_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_roc_breakout_frozen_params_in_snapshot() -> None:
    report = run_roc_breakout_confirm_backtest(
        _roc_breakout_candles(),
        code_commit="slice-2d-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["breakout_lookback"] == BREAKOUT_LOOKBACK
    assert snapshot["exit_lookback"] == EXIT_LOOKBACK
    assert snapshot["roc_period"] == ROC_PERIOD
    assert snapshot["roc_entry_threshold"] == ROC_ENTRY_THRESHOLD
    assert snapshot["roc_exit_threshold"] == ROC_EXIT_THRESHOLD
    assert (
        snapshot["min_minutes_between_entries"] == ROC_MIN_MINUTES_BETWEEN_ENTRIES
    )
    assert snapshot["trade_side_mode"] == "long_only"
