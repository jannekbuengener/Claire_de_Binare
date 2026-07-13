"""Tests for opening_range_breakout_v1 backtest runner (#4031 slice 2c)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.replay.pack_a_breakout_common import (
    OR_END_UTC,
    OR_START_UTC,
    ORB_MIN_MINUTES_BETWEEN_ENTRIES,
    TRADE_END_UTC,
    orb_session_phase,
    utc_day_key,
)
from services.validation.opening_range_breakout_backtest_runner import (
    run_opening_range_breakout_backtest,
)

pytestmark = pytest.mark.unit


def _utc_ts_ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    return int(
        datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp()
        * 1000
    )


def _candle(ts_ms: int, close: float, *, spread: float = 0.5) -> dict:
    return {
        "symbol": "BTCUSDT",
        "ts_ms": ts_ms,
        "timestamp_ms": ts_ms,
        "open": close,
        "high": close + spread,
        "low": close - spread,
        "close": close,
        "volume": 1_000.0,
    }


def _orb_day_candles(
    *,
    start_ts_ms: int,
    or_high: float,
    or_low: float,
    breakout_close: float,
    breakout_offset_minutes: int = 90,
    hold_until_session_end: bool = False,
) -> list[dict]:
    rows: list[dict] = []
    for minute in range(breakout_offset_minutes + 1):
        ts_ms = start_ts_ms + minute * 60_000
        if minute < 60:
            close = (or_high + or_low) / 2
            spread = max(or_high - close, close - or_low, 0.1)
        elif minute < breakout_offset_minutes:
            close = (or_high + or_low) / 2
            spread = 0.1
        else:
            close = breakout_close
            spread = 0.1
        rows.append(_candle(ts_ms, close, spread=spread))

    if hold_until_session_end:
        session_end_offset = 20 * 60
        for minute in range(breakout_offset_minutes + 1, session_end_offset + 1):
            ts_ms = start_ts_ms + minute * 60_000
            rows.append(_candle(ts_ms, breakout_close))
    return rows


def _orb_fixture_candles() -> list[dict]:
    warmup_start = _utc_ts_ms(2024, 6, 1, 23, 0)
    warmup = [
        _candle(warmup_start + index * 60_000, 100.0) for index in range(60)
    ]
    session = _orb_day_candles(
        start_ts_ms=_utc_ts_ms(2024, 6, 2, 0, 0),
        or_high=101.0,
        or_low=99.0,
        breakout_close=102.5,
        breakout_offset_minutes=90,
        hold_until_session_end=True,
    )
    return warmup + session


def test_opening_range_breakout_runs_and_closes_trade() -> None:
    report = run_opening_range_breakout_backtest(
        _orb_fixture_candles(),
        code_commit="slice-2c-test",
    )

    assert report["schema_version"] == "strategy_validation_report.v1"
    assert report["strategy_id"] == "opening_range_breakout_v1"
    assert report["metrics"]["closed_trades_total"] >= 1
    assert report["config_snapshot"]["ranking_ready"] is False
    assert report["metrics"]["ranking_ready"] is False
    assert report["gate_result"]["ranking_ready"] is False


def test_opening_range_breakout_frozen_params_in_snapshot() -> None:
    report = run_opening_range_breakout_backtest(
        _orb_fixture_candles(),
        code_commit="slice-2c-test",
    )
    snapshot = report["config_snapshot"]

    assert snapshot["or_start_utc"] == OR_START_UTC
    assert snapshot["or_end_utc"] == OR_END_UTC
    assert snapshot["trade_end_utc"] == TRADE_END_UTC
    assert snapshot["min_minutes_between_entries"] == ORB_MIN_MINUTES_BETWEEN_ENTRIES
    assert snapshot["trade_side_mode"] == "long_only"


def test_orb_midnight_utc_resets_opening_range_per_day() -> None:
    day_one_start = _utc_ts_ms(2024, 6, 2, 0, 0)
    day_one = _orb_day_candles(
        start_ts_ms=day_one_start,
        or_high=101.0,
        or_low=99.0,
        breakout_close=102.5,
        breakout_offset_minutes=75,
    )
    minutes_day_one = len(day_one)
    day_two_start = day_one_start + minutes_day_one * 60_000
    while utc_day_key(day_two_start) == utc_day_key(day_one_start):
        day_two_start += 60_000
    gap_fill = []
    cursor = day_one_start + minutes_day_one * 60_000
    while cursor < day_two_start:
        gap_fill.append(_candle(cursor, 102.0))
        cursor += 60_000
    day_two = _orb_day_candles(
        start_ts_ms=day_two_start,
        or_high=50.2,
        or_low=49.8,
        breakout_close=50.0,
        breakout_offset_minutes=75,
    )

    report = run_opening_range_breakout_backtest(
        day_one + gap_fill + day_two,
        code_commit="slice-2c-test",
    )

    assert report["metrics"]["buy_signals_total"] == 1
    assert report["thresholds_applied"]["orb_upper_break"] == 1


def test_orb_session_end_utc_closes_open_position() -> None:
    warmup_start = _utc_ts_ms(2024, 6, 1, 23, 0)
    warmup = [
        _candle(warmup_start + index * 60_000, 100.0) for index in range(60)
    ]
    session = _orb_day_candles(
        start_ts_ms=_utc_ts_ms(2024, 6, 2, 0, 0),
        or_high=101.0,
        or_low=99.0,
        breakout_close=102.0,
        breakout_offset_minutes=90,
        hold_until_session_end=True,
    )

    report = run_opening_range_breakout_backtest(
        warmup + session,
        code_commit="slice-2c-test",
    )

    assert report["metrics"]["closed_trades_total"] == 1
    assert report["exit_reasons"] == ["session_end_utc"]
    assert report["thresholds_applied"]["session_end_utc"] == 1


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (0, 30, "opening_range"),
        (1, 0, "trading"),
        (12, 0, "trading"),
        (19, 59, "trading"),
        (20, 0, "closed"),
        (23, 0, "closed"),
    ],
)
def test_orb_session_phase_utc_boundaries(
    hour: int, minute: int, expected: str
) -> None:
    ts_ms = _utc_ts_ms(2024, 6, 2, hour, minute)
    assert (
        orb_session_phase(
            ts_ms,
            or_start_utc=OR_START_UTC,
            or_end_utc=OR_END_UTC,
            trade_end_utc=TRADE_END_UTC,
        )
        == expected
    )
