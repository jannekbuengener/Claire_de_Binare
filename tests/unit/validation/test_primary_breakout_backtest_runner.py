"""Tests for the deterministic primary_breakout_v1 backtest runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from services.validation.strategy_backtest_runner import (
    PrimaryBreakoutBacktestError,
    PrimaryBreakoutBacktestRunConfig,
    run_primary_breakout_backtest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "docs" / "contracts" / "strategy_validation_report_v1.schema.json"


def _candles() -> list[dict]:
    rows: list[dict] = []
    close = 100.0
    start_ts_ms = 1_700_000_000_000
    for index in range(380):
        if index < 240:
            close = 100.0
        elif index == 240:
            close = 101.5
        elif 241 <= index <= 360:
            close += 0.2
        elif index == 361:
            close = 100.0
        else:
            close += 0.05
        rows.append(
            {
                "symbol": "BTCUSDT",
                "ts_ms": start_ts_ms + index * 60_000,
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 10_000.0 + index,
                "regime_id": 0,
                "market_state_fresh": True,
                "regime_fresh": True,
            }
        )
    return rows


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_primary_breakout_backtest_runner_is_deterministic_and_schema_valid() -> None:
    candles = _candles()
    config = PrimaryBreakoutBacktestRunConfig()

    first = run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")
    second = run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")

    assert first == second

    validator = Draft7Validator(_load_schema())
    assert list(validator.iter_errors(first)) == []
    assert first["strategy_id"] == "primary_breakout_v1"
    assert first["run_metadata"]["source"] == "historical_backtest_v1"
    assert first["metrics"]["closed_trades_total"] >= 1
    assert first["gate_result"]["status"] in {"PASS", "REVIEW", "FAIL"}


@pytest.mark.unit
def test_primary_breakout_backtest_runner_period_window_semantics() -> None:
    """Requested vs effective period boundaries are distinct and correctly related.

    _candles() produces 380 candles starting at ts_ms=1_700_000_000_000 with 1m cadence.
    With entry_lookback_minutes=240 the bridge warm-up consumes candles[0..239], so the
    first effective bridge request corresponds to candles[240].
    """
    candles = _candles()
    config = PrimaryBreakoutBacktestRunConfig()
    report = run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")

    ds = report["dataset_summary"]
    start_ts = 1_700_000_000_000
    end_ts = start_ts + 379 * 60_000
    max_lookback = max(
        config.bridge.entry_lookback_minutes, config.bridge.exit_lookback_minutes
    )

    assert ds["requested_period_start_ts_ms"] == start_ts
    assert ds["requested_period_end_ts_ms"] == end_ts
    # Effective start is offset by exactly max_lookback * 60_000 ms from requested start.
    assert ds["period_start_ts_ms"] == start_ts + max_lookback * 60_000
    # Effective end aligns with the last raw candle.
    assert ds["period_end_ts_ms"] == end_ts
    # Invariant: effective start must be strictly after requested start.
    assert ds["period_start_ts_ms"] > ds["requested_period_start_ts_ms"]


@pytest.mark.unit
def test_primary_breakout_backtest_runner_fail_closed_on_invalid_config() -> None:
    candles = _candles()
    config = PrimaryBreakoutBacktestRunConfig(order_size=0.0)

    with pytest.raises(PrimaryBreakoutBacktestError, match="order_size must be > 0"):
        run_primary_breakout_backtest(candles, run_config=config, code_commit="a9a62be")
