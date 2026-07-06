"""Single-pass backtest runner for breakout_trend_filter_v1 (Pack-A wave 1)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    BREAKOUT_TREND_FILTER_STRATEGY_ID,
    BreakoutTrendFilterConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    build_trend_gate_series,
    compute_donchian_channels,
    cooldown_allows_entry,
    breakout_trend_warmup_candles,
    validate_pack_a_candle_series,
)
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid
from services.execution.simulator import ExecutionSimulator
from services.validation.donchian_breakout_backtest_runner import (
    _build_full_report as _build_donchian_full_report,
    _build_minimal_report as _build_donchian_minimal_report,
)

logger = logging.getLogger(__name__)


def run_breakout_trend_filter_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: BreakoutTrendFilterConfig | None = None,
) -> dict[str, Any]:
    """Single-pass Breakout + Trend Filter backtest returning a report dict."""
    config = bridge_config or BreakoutTrendFilterConfig()
    config.validate()
    warmup = breakout_trend_warmup_candles(config)

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
    trend_gate = build_trend_gate_series(
        ts_values,
        closes,
        trend_ema_period_5m=config.trend_ema_period_5m,
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
        upper_level = upper[index]
        lower_level = lower[index]
        trend_ok = trend_gate[index]

        if open_position is None:
            if (
                upper_level is not None
                and close > upper_level
                and trend_ok is True
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("donchian_upper_break_trend_ok")
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
            trend_fail = trend_ok is False
            channel_exit = lower_level is not None and close < lower_level
            if channel_exit or trend_fail:
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
                reason = "trend_gate_fail" if trend_fail and not channel_exit else "donchian_lower_break"
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

    report = _build_donchian_full_report(
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config=config,
        warmup=warmup,
        code_commit=code_commit,
        run_id=run_id,
    )
    report["strategy_id"] = BREAKOUT_TREND_FILTER_STRATEGY_ID
    report["run_metadata"]["source"] = "breakout_trend_filter_backtest_runner"
    report["config_snapshot"]["trend_ema_period_5m"] = config.trend_ema_period_5m
    report["thresholds_applied"] = {
        "donchian_upper_break_trend_ok": entry_reasons.count(
            "donchian_upper_break_trend_ok"
        ),
        "donchian_lower_break": exit_reasons.count("donchian_lower_break"),
        "trend_gate_fail": exit_reasons.count("trend_gate_fail"),
    }
    return report


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    report = _build_donchian_minimal_report(reason, code_commit, run_id=run_id)
    report["strategy_id"] = BREAKOUT_TREND_FILTER_STRATEGY_ID
    report["run_metadata"]["source"] = "breakout_trend_filter_backtest_runner"
    return report


def _utc_now_iso() -> str:
    return utcnow().replace(tzinfo=None).isoformat() + "Z"
