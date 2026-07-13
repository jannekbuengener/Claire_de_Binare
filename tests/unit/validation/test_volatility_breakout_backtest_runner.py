"""Tests for volatility_breakout_v1 backtest runner (#4031 slice 2b)."""

from __future__ import annotations

import pytest

from core.replay.pack_a_breakout_common import (
    ATR_PERIOD,
    BREAKOUT_LOOKBACK,
    EXIT_LOOKBACK,
    EXPANSION_LAG,
    EXPANSION_MULTIPLIER,
    VOL_BREAKOUT_MIN_MINUTES_BETWEEN_ENTRIES,
)
from services.validation.volatility_breakout_backtest_runner import (
    run_volatility_breakout_backtest,
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


def _volatility_breakout_candles() -> list[dict]:
    rows: list[dict] = []
    start_ts = 1_700_000_000_000
    for index in range(90):
        close = 100.0
        spread = 0.05
        if 40 <= index <= 54:
            spread = 0.05 + (index - 40) * 0.08
        elif index == 55:
            close = 101.5
            spread = 0.6
        elif 56 <= index <= 70:
            close = 101.5 + (index - 56) * 0.05
            spread = 0.5
        elif index == 71:
            close = 99.2
            spread = 0.4
        rows.append(_candle(start_ts + index * 60_000, close, spread=spread))
    return rows


def test_volatility_breakout_runs_and_closes_trade() -> None:
    report = run_volatility_breakout_backtest(
        _volatility_breakout_candles(),
        code_commit="slice-2b-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "volatility_breakout_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_volatility_breakout_frozen_params_in_snapshot() -> None:
    report = run_volatility_breakout_backtest(
        _volatility_breakout_candles(),
        code_commit="slice-2b-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["breakout_lookback"] == BREAKOUT_LOOKBACK
    assert snapshot["exit_lookback"] == EXIT_LOOKBACK
    assert snapshot["atr_period"] == ATR_PERIOD
    assert snapshot["expansion_lag"] == EXPANSION_LAG
    assert snapshot["expansion_multiplier"] == EXPANSION_MULTIPLIER
    assert (
        snapshot["min_minutes_between_entries"]
        == VOL_BREAKOUT_MIN_MINUTES_BETWEEN_ENTRIES
    )
    assert snapshot["trade_side_mode"] == "long_only"
