"""Single-pass backtest runner for atr_expansion_v1 (Pack-A slice 2b)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    ATR_EXPANSION_STRATEGY_ID,
    AtrExpansionConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    atr_expansion_warmup_candles,
    compute_atr_series,
    compute_sma_series,
    cooldown_allows_entry,
    validate_pack_a_candle_series,
)
from services.execution.simulator import ExecutionSimulator
from services.validation.pack_a_backtest_report import (
    build_pack_a_full_report,
    build_pack_a_minimal_report,
)

logger = logging.getLogger(__name__)


def run_atr_expansion_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: AtrExpansionConfig | None = None,
) -> dict[str, Any]:
    """Single-pass ATR Expansion backtest returning a report dict."""
    config = bridge_config or AtrExpansionConfig()
    config.validate()
    warmup = atr_expansion_warmup_candles(config)

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

    atr_series = compute_atr_series(highs, lows, closes, config.atr_period)
    sma_series = compute_sma_series(closes, config.sma_period)

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
        atr_value = atr_series[index]
        sma_value = sma_series[index]
        atr_ratio = (atr_value / close) if atr_value is not None and close > 0 else None

        if open_position is None:
            trend_ok = sma_value is not None and close > sma_value
            ratio_ok = atr_ratio is not None and atr_ratio > config.atr_ratio_threshold
            if (
                trend_ok
                and ratio_ok
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("atr_ratio_expansion_entry")
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
            ratio_exit = atr_ratio is not None and atr_ratio < config.atr_ratio_exit
            trend_fail = sma_value is not None and close < sma_value
            if ratio_exit or trend_fail:
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
                reason = "atr_ratio_contract" if ratio_exit and not trend_fail else "sma_trend_fail"
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
        strategy_id=ATR_EXPANSION_STRATEGY_ID,
        source="atr_expansion_backtest_runner",
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config_snapshot={
            "atr_period": config.atr_period,
            "atr_ratio_threshold": config.atr_ratio_threshold,
            "atr_ratio_exit": config.atr_ratio_exit,
            "sma_period": config.sma_period,
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
            "atr_ratio_expansion_entry": entry_reasons.count("atr_ratio_expansion_entry"),
            "atr_ratio_contract": exit_reasons.count("atr_ratio_contract"),
            "sma_trend_fail": exit_reasons.count("sma_trend_fail"),
        },
    )


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return build_pack_a_minimal_report(
        strategy_id=ATR_EXPANSION_STRATEGY_ID,
        source="atr_expansion_backtest_runner",
        reason=reason,
        code_commit=code_commit,
        run_id=run_id,
    )
