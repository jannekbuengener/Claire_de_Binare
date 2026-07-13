"""Single-pass backtest runner for volatility_breakout_v1 (Pack-A slice 2b)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    VOLATILITY_BREAKOUT_STRATEGY_ID,
    VolatilityBreakoutConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    atr_expansion_holds,
    compute_atr_series,
    compute_highest_high,
    compute_lowest_low,
    cooldown_allows_entry,
    volatility_breakout_warmup_candles,
    validate_pack_a_candle_series,
)
from services.execution.simulator import ExecutionSimulator
from services.validation.pack_a_backtest_report import (
    build_pack_a_full_report,
    build_pack_a_minimal_report,
)

logger = logging.getLogger(__name__)


def run_volatility_breakout_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: VolatilityBreakoutConfig | None = None,
) -> dict[str, Any]:
    """Single-pass Volatility Breakout backtest returning a report dict."""
    config = bridge_config or VolatilityBreakoutConfig()
    config.validate()
    warmup = volatility_breakout_warmup_candles(config)

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
    ts_values = [int(c["ts_ms"]) for c in candles]

    highest_high = compute_highest_high(highs, config.breakout_lookback)
    lowest_low = compute_lowest_low(lows, config.exit_lookback)
    atr_series = compute_atr_series(highs, lows, closes, config.atr_period)

    sim = ExecutionSimulator(config=simulator_config or {})
    live_candles = candles[warmup:]
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    signals_total = 0
    last_entry_ts_ms: int | None = None
    entry_reasons: list[str] = []
    exit_reasons: list[str] = []

    for offset, candle in enumerate(live_candles):
        index = warmup + offset
        close = closes[index]
        ts_ms = ts_values[index]
        volume = float(candle.get("volume", 0.0))
        breakout_level = highest_high[index]
        exit_level = lowest_low[index]
        expansion_ok = atr_expansion_holds(
            atr_series,
            index,
            expansion_lag=config.expansion_lag,
            expansion_multiplier=config.expansion_multiplier,
        )

        if open_position is None:
            if (
                breakout_level is not None
                and close > breakout_level
                and expansion_ok
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("volatility_breakout_entry")
                volatility = abs(highs[index] - lows[index]) / close if close > 0 else 0.0
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
        elif open_position is not None:
            channel_exit = exit_level is not None and close < exit_level
            expansion_fail = not expansion_ok
            if channel_exit or expansion_fail:
                exit_price = close
                volatility = abs(highs[index] - lows[index]) / close if close > 0 else 0.0
                order_book_depth = max(volume * close * ORDER_BOOK_DEPTH_MULT, close)
                fill = sim.simulate_market_order(
                    side="sell",
                    size=ORDER_SIZE,
                    current_price=exit_price,
                    order_book_depth=order_book_depth,
                    volatility=max(volatility, 0.0),
                )
                trade_r = (
                    fill.avg_fill_price - open_position["entry_price"]
                ) / open_position["entry_price"]
                reason = (
                    "atr_expansion_fail"
                    if expansion_fail and not channel_exit
                    else "lowest_low_break"
                )
                exit_reasons.append(reason)
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
                open_position = None

    return build_pack_a_full_report(
        strategy_id=VOLATILITY_BREAKOUT_STRATEGY_ID,
        source="volatility_breakout_backtest_runner",
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config_snapshot={
            "breakout_lookback": config.breakout_lookback,
            "exit_lookback": config.exit_lookback,
            "atr_period": config.atr_period,
            "expansion_lag": config.expansion_lag,
            "expansion_multiplier": config.expansion_multiplier,
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
            "volatility_breakout_entry": entry_reasons.count("volatility_breakout_entry"),
            "lowest_low_break": exit_reasons.count("lowest_low_break"),
            "atr_expansion_fail": exit_reasons.count("atr_expansion_fail"),
        },
    )


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return build_pack_a_minimal_report(
        strategy_id=VOLATILITY_BREAKOUT_STRATEGY_ID,
        source="volatility_breakout_backtest_runner",
        reason=reason,
        code_commit=code_commit,
        run_id=run_id,
    )
