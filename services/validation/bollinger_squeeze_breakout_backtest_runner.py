"""Single-pass backtest runner for bollinger_squeeze_breakout_v1 (Pack-A slice 2b)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    BOLLINGER_SQUEEZE_BREAKOUT_STRATEGY_ID,
    BollingerSqueezeConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    bollinger_squeeze_warmup_candles,
    compute_bollinger_series,
    cooldown_allows_entry,
    squeeze_precedes_breakout,
    validate_pack_a_candle_series,
)
from services.execution.simulator import ExecutionSimulator
from services.validation.pack_a_backtest_report import (
    build_pack_a_full_report,
    build_pack_a_minimal_report,
)

logger = logging.getLogger(__name__)


def run_bollinger_squeeze_breakout_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: BollingerSqueezeConfig | None = None,
) -> dict[str, Any]:
    """Single-pass Bollinger Squeeze Breakout backtest returning a report dict."""
    config = bridge_config or BollingerSqueezeConfig()
    config.validate()
    warmup = bollinger_squeeze_warmup_candles(config)

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

    upper, middle, lower, bandwidth = compute_bollinger_series(
        closes,
        period=config.bb_period,
        std_dev=config.bb_std_dev,
    )

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
        upper_band = upper[index]
        middle_band = middle[index]
        lower_band = lower[index]
        bw = bandwidth[index]

        if open_position is None:
            squeeze_ok = squeeze_precedes_breakout(
                bandwidth,
                index,
                squeeze_threshold=config.squeeze_threshold,
                squeeze_bars_min=config.squeeze_bars_min,
            )
            expansion_ok = bw is not None and bw < config.expansion_ceiling
            if (
                upper_band is not None
                and close > upper_band
                and squeeze_ok
                and expansion_ok
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("bb_squeeze_upper_break")
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
            middle_exit = middle_band is not None and close < middle_band
            lower_exit = lower_band is not None and close < lower_band
            if middle_exit or lower_exit:
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
                reason = "bb_middle_break" if middle_exit and not lower_exit else "bb_lower_break"
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
        strategy_id=BOLLINGER_SQUEEZE_BREAKOUT_STRATEGY_ID,
        source="bollinger_squeeze_breakout_backtest_runner",
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config_snapshot={
            "bb_period": config.bb_period,
            "bb_std_dev": config.bb_std_dev,
            "squeeze_threshold": config.squeeze_threshold,
            "squeeze_bars_min": config.squeeze_bars_min,
            "expansion_ceiling": config.expansion_ceiling,
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
            "bb_squeeze_upper_break": entry_reasons.count("bb_squeeze_upper_break"),
            "bb_middle_break": exit_reasons.count("bb_middle_break"),
            "bb_lower_break": exit_reasons.count("bb_lower_break"),
        },
    )


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return build_pack_a_minimal_report(
        strategy_id=BOLLINGER_SQUEEZE_BREAKOUT_STRATEGY_ID,
        source="bollinger_squeeze_breakout_backtest_runner",
        reason=reason,
        code_commit=code_commit,
        run_id=run_id,
    )
