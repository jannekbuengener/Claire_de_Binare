"""Single-pass backtest runner for opening_range_breakout_v1 (Pack-A slice 2c)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    OPENING_RANGE_BREAKOUT_STRATEGY_ID,
    OpeningRangeBreakoutConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    cooldown_allows_entry,
    opening_range_breakout_warmup_candles,
    orb_session_phase,
    resolve_candle_ts_ms,
    utc_day_key,
    validate_pack_a_candle_series,
)
from services.execution.simulator import ExecutionSimulator
from services.validation.pack_a_backtest_report import (
    build_pack_a_full_report,
    build_pack_a_minimal_report,
)

logger = logging.getLogger(__name__)


def run_opening_range_breakout_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: OpeningRangeBreakoutConfig | None = None,
) -> dict[str, Any]:
    """Single-pass UTC opening-range breakout backtest returning a report dict."""
    config = bridge_config or OpeningRangeBreakoutConfig()
    config.validate()
    warmup = opening_range_breakout_warmup_candles(config)

    if not candles:
        return _build_minimal_report("no_data", code_commit, run_id=run_id)
    try:
        validate_pack_a_candle_series(candles)
    except ValueError as exc:
        return _build_minimal_report(str(exc), code_commit, run_id=run_id)

    if len(candles) <= warmup:
        return _build_minimal_report("insufficient_candles", code_commit, run_id=run_id)

    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    ts_values = [resolve_candle_ts_ms(c) for c in candles]

    sim = ExecutionSimulator(config=simulator_config or {})
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    signals_total = 0
    last_entry_ts_ms: int | None = None
    entry_reasons: list[str] = []
    exit_reasons: list[str] = []

    current_day: str | None = None
    or_high: float | None = None
    or_low: float | None = None
    or_locked = False

    for index, candle in enumerate(candles):
        close = closes[index]
        ts_ms = ts_values[index]
        high = highs[index]
        low = lows[index]
        volume = float(candle.get("volume", 0.0))
        day_key = utc_day_key(ts_ms)
        phase = orb_session_phase(
            ts_ms,
            or_start_utc=config.or_start_utc,
            or_end_utc=config.or_end_utc,
            trade_end_utc=config.trade_end_utc,
        )

        if day_key != current_day:
            current_day = day_key
            or_high = None
            or_low = None
            or_locked = False

        if phase == "opening_range":
            or_high = high if or_high is None else max(or_high, high)
            or_low = low if or_low is None else min(or_low, low)
            continue

        if phase == "trading" and not or_locked:
            or_locked = or_high is not None and or_low is not None

        if index < warmup:
            continue

        if phase == "closed" and open_position is not None:
            exit_reasons.append("session_end_utc")
            open_position = _close_position(
                sim=sim,
                open_position=open_position,
                index=index,
                ts_ms=ts_ms,
                close=close,
                highs=highs,
                lows=lows,
                volume=volume,
                trades=trades,
                reason="session_end_utc",
            )
            continue

        if phase != "trading" or not or_locked or or_high is None or or_low is None:
            continue

        if open_position is None:
            if (
                close > or_high
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("orb_upper_break")
                volatility = abs(high - low) / close if close > 0 else 0.0
                order_book_depth = max(volume * close * ORDER_BOOK_DEPTH_MULT, close)
                fill = sim.simulate_market_order(
                    side="buy",
                    size=ORDER_SIZE,
                    current_price=close,
                    order_book_depth=order_book_depth,
                    volatility=max(volatility, 0.0),
                )
                open_position = {
                    "entry_ts_ms": ts_ms,
                    "entry_price": fill.avg_fill_price,
                    "entry_fee": fill.fees,
                }
                last_entry_ts_ms = ts_ms
        elif close < or_low:
            exit_reasons.append("orb_lower_break")
            open_position = _close_position(
                sim=sim,
                open_position=open_position,
                index=index,
                ts_ms=ts_ms,
                close=close,
                highs=highs,
                lows=lows,
                volume=volume,
                trades=trades,
                reason="orb_lower_break",
            )

    return build_pack_a_full_report(
        strategy_id=OPENING_RANGE_BREAKOUT_STRATEGY_ID,
        source="opening_range_breakout_backtest_runner",
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config_snapshot={
            "or_start_utc": config.or_start_utc,
            "or_end_utc": config.or_end_utc,
            "trade_end_utc": config.trade_end_utc,
            "min_minutes_between_entries": config.min_minutes_between_entries,
            "trade_side_mode": config.trade_side_mode,
            "warmup_candles": warmup,
            "order_size": ORDER_SIZE,
            "ranking_ready": False,
        },
        warmup=warmup,
        code_commit=code_commit,
        run_id=run_id,
        thresholds_applied={
            "orb_upper_break": entry_reasons.count("orb_upper_break"),
            "orb_lower_break": exit_reasons.count("orb_lower_break"),
            "session_end_utc": exit_reasons.count("session_end_utc"),
        },
    )


def _close_position(
    *,
    sim: ExecutionSimulator,
    open_position: dict[str, Any],
    index: int,
    ts_ms: int,
    close: float,
    highs: list[float],
    lows: list[float],
    volume: float,
    trades: list[dict[str, Any]],
    reason: str,
) -> None:
    volatility = abs(highs[index] - lows[index]) / close if close > 0 else 0.0
    order_book_depth = max(volume * close * ORDER_BOOK_DEPTH_MULT, close)
    fill = sim.simulate_market_order(
        side="sell",
        size=ORDER_SIZE,
        current_price=close,
        order_book_depth=order_book_depth,
        volatility=max(volatility, 0.0),
    )
    trade_r = (fill.avg_fill_price - open_position["entry_price"]) / open_position[
        "entry_price"
    ]
    trades.append(
        {
            "entry_ts_ms": open_position["entry_ts_ms"],
            "exit_ts_ms": ts_ms,
            "entry_price": open_position["entry_price"],
            "exit_price": fill.avg_fill_price,
            "entry_fee": open_position["entry_fee"],
            "exit_fee": fill.fees,
            "r_return": trade_r,
            "reason": reason,
        }
    )
    return None


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return build_pack_a_minimal_report(
        strategy_id=OPENING_RANGE_BREAKOUT_STRATEGY_ID,
        source="opening_range_breakout_backtest_runner",
        reason=reason,
        code_commit=code_commit,
        run_id=run_id,
    )
