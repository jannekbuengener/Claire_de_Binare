"""Single-pass backtest runner for hh_hl_continuation_v1 (#4372)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.hh_hl_continuation_common import (
    HH_HL_CONTINUATION_STRATEGY_ID,
    HhHlContinuationConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    confirmed_swing_at,
    cooldown_allows_entry,
    frozen_hh_hl_parameters,
    hh_hl_warmup_candles,
    structure_is_hh_hl,
    validate_hh_hl_candle_series,
)
from services.execution.simulator import ExecutionSimulator
from services.validation.pack_a_backtest_report import (
    build_pack_a_full_report,
    build_pack_a_minimal_report,
)

logger = logging.getLogger(__name__)


def run_hh_hl_continuation_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: HhHlContinuationConfig | None = None,
) -> dict[str, Any]:
    """Deterministic HH/HL continuation backtest returning a Pack-A-style report."""
    del run_config  # frozen config only
    config = bridge_config or HhHlContinuationConfig()
    config.validate()
    warmup = hh_hl_warmup_candles(config)

    if not candles:
        return _build_minimal_report("no_data", code_commit, run_id=run_id)
    try:
        validate_hh_hl_candle_series(candles)
    except ValueError as exc:
        return _build_minimal_report(str(exc), code_commit, run_id=run_id)

    if len(candles) <= warmup:
        return _build_minimal_report("insufficient_candles", code_commit, run_id=run_id)

    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    ts_values = [int(c["ts_ms"]) for c in candles]

    sim = ExecutionSimulator(config=simulator_config or {})
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    signals_total = 0
    last_entry_ts_ms: int | None = None
    entry_reasons: list[str] = []
    exit_reasons: list[str] = []
    swing_highs: list[Any] = []
    swing_lows: list[Any] = []
    structure_ready_before = False

    for index in range(warmup, len(candles)):
        candle = candles[index]
        close = closes[index]
        ts_ms = ts_values[index]
        volume = float(candle.get("volume", 0.0))

        new_high = confirmed_swing_at(
            highs,
            lows,
            ts_values,
            index,
            config=config,
            kind="high",
        )
        new_low = confirmed_swing_at(
            highs,
            lows,
            ts_values,
            index,
            config=config,
            kind="low",
        )
        if new_high is not None:
            swing_highs.append(new_high)
        if new_low is not None:
            swing_lows.append(new_low)

        structure_ready = structure_is_hh_hl(swing_highs, swing_lows)

        if open_position is None:
            if (
                structure_ready
                and not structure_ready_before
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("hh_hl_structure_confirm")
                volatility = (
                    abs(highs[index] - lows[index]) / close if close > 0 else 0.0
                )
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
        elif new_low is not None and len(swing_lows) >= 2:
            if swing_lows[-1].price < swing_lows[-2].price:
                exit_price = close
                volatility = (
                    abs(highs[index] - lows[index]) / close if close > 0 else 0.0
                )
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
                exit_reasons.append("hl_structure_break")
                trades.append(
                    {
                        "entry_ts_ms": open_position["entry_ts_ms"],
                        "exit_ts_ms": ts_ms,
                        "entry_price": open_position["entry_price"],
                        "exit_price": fill.avg_fill_price,
                        "entry_fee": open_position["entry_fee"],
                        "exit_fee": fill.fees,
                        "r_return": trade_r,
                        "reason": "hl_structure_break",
                    }
                )
                open_position = None

        structure_ready_before = structure_ready

    if open_position is not None:
        index = len(candles) - 1
        close = closes[index]
        ts_ms = ts_values[index]
        volume = float(candles[index].get("volume", 0.0))
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
        exit_reasons.append("series_end_closeout")
        trades.append(
            {
                "entry_ts_ms": open_position["entry_ts_ms"],
                "exit_ts_ms": ts_ms,
                "entry_price": open_position["entry_price"],
                "exit_price": fill.avg_fill_price,
                "entry_fee": open_position["entry_fee"],
                "exit_fee": fill.fees,
                "r_return": trade_r,
                "reason": "series_end_closeout",
            }
        )

    params = frozen_hh_hl_parameters(config)
    return build_pack_a_full_report(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        source="hh_hl_continuation_backtest_runner",
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        config_snapshot={
            **params,
            "warmup_candles": warmup,
            "order_size": ORDER_SIZE,
            "ranking_ready": False,
            "confirmed_swing_highs": len(swing_highs),
            "confirmed_swing_lows": len(swing_lows),
        },
        warmup=warmup,
        code_commit=code_commit,
        run_id=run_id,
        thresholds_applied={
            "hh_hl_structure_confirm": entry_reasons.count("hh_hl_structure_confirm"),
            "hl_structure_break": exit_reasons.count("hl_structure_break"),
            "series_end_closeout": exit_reasons.count("series_end_closeout"),
        },
    )


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return build_pack_a_minimal_report(
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        source="hh_hl_continuation_backtest_runner",
        reason=reason,
        code_commit=code_commit,
        run_id=run_id,
    )
