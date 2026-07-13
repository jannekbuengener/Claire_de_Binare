"""Single-pass backtest runner for breakout_volatility_filter_v1 (Pack-A slice 2b)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    BREAKOUT_VOLATILITY_FILTER_STRATEGY_ID,
    BreakoutVolatilityFilterConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    compute_atr_series,
    compute_donchian_channels,
    cooldown_allows_entry,
    breakout_volatility_filter_warmup_candles,
    validate_pack_a_candle_series,
    vol_ratio_in_band,
)
from services.execution.simulator import ExecutionSimulator
from services.validation.pack_a_backtest_report import (
    build_pack_a_full_report,
    build_pack_a_minimal_report,
)

logger = logging.getLogger(__name__)


def run_breakout_volatility_filter_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: BreakoutVolatilityFilterConfig | None = None,
) -> dict[str, Any]:
    """Single-pass Breakout + Volatility Filter backtest returning a report dict."""
    config = bridge_config or BreakoutVolatilityFilterConfig()
    config.validate()
    warmup = breakout_volatility_filter_warmup_candles(config)

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

    upper, lower = compute_donchian_channels(
        highs,
        lows,
        entry_channel_bars=config.entry_channel_bars,
        exit_channel_bars=config.exit_channel_bars,
    )
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
        upper_level = upper[index]
        lower_level = lower[index]
        atr_value = atr_series[index]

        if open_position is None:
            vol_ok = vol_ratio_in_band(
                atr_value,
                close,
                vol_floor=config.vol_floor,
                vol_ceiling=config.vol_ceiling,
            )
            if (
                upper_level is not None
                and close > upper_level
                and vol_ok
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("donchian_upper_break_vol_ok")
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
        elif lower_level is not None and close < lower_level:
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
            trade_r = (fill.avg_fill_price - open_position["entry_price"]) / open_position[
                "entry_price"
            ]
            exit_reasons.append("donchian_lower_break")
            trades.append(
                {
                    "entry_ts_ms": open_position["entry_ts_ms"],
                    "exit_ts_ms": ts_ms,
                    "entry_price": open_position["entry_price"],
                    "exit_price": fill.avg_fill_price,
                    "entry_fee": open_position["entry_fee"],
                    "exit_fee": fill.fees,
                    "r_return": trade_r,
                    "reason": "donchian_lower_break",
                }
            )
            open_position = None

    report = build_pack_a_full_report(
        strategy_id=BREAKOUT_VOLATILITY_FILTER_STRATEGY_ID,
        source="breakout_volatility_filter_backtest_runner",
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config_snapshot={
            "entry_channel_bars": config.entry_channel_bars,
            "exit_channel_bars": config.exit_channel_bars,
            "min_minutes_between_entries": config.min_minutes_between_entries,
            "trade_side_mode": config.trade_side_mode,
            "atr_period": config.atr_period,
            "vol_floor": config.vol_floor,
            "vol_ceiling": config.vol_ceiling,
            "warmup_candles": warmup,
            "order_size": ORDER_SIZE,
            "ranking_ready": False,
        },
        warmup=warmup,
        code_commit=code_commit,
        run_id=run_id,
        thresholds_applied={
            "donchian_upper_break_vol_ok": entry_reasons.count(
                "donchian_upper_break_vol_ok"
            ),
            "donchian_lower_break": exit_reasons.count("donchian_lower_break"),
        },
    )
    return report


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return build_pack_a_minimal_report(
        strategy_id=BREAKOUT_VOLATILITY_FILTER_STRATEGY_ID,
        source="breakout_volatility_filter_backtest_runner",
        reason=reason,
        code_commit=code_commit,
        run_id=run_id,
    )
