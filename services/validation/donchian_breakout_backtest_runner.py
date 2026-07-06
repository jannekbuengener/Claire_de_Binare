"""Single-pass backtest runner for donchian_breakout_v1 (Pack-A wave 1)."""

from __future__ import annotations

import logging
from typing import Any

from core.replay.pack_a_breakout_common import (
    DONCHIAN_BREAKOUT_STRATEGY_ID,
    DonchianBreakoutConfig,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    compute_donchian_channels,
    cooldown_allows_entry,
    donchian_warmup_candles,
    validate_pack_a_candle_series,
)
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid
from services.execution.simulator import ExecutionSimulator

logger = logging.getLogger(__name__)

SCENARIO_OVERRIDE_KEYS = frozenset(
    {
        "BASE_SLIPPAGE_BPS",
        "VOLATILITY_SLIPPAGE_FACTOR",
        "FILL_THRESHOLD",
        "PRICE_IMPACT_FACTOR",
        "DEPTH_IMPACT_FACTOR",
        "EXECUTION_DELAY_BARS",
    }
)


def run_donchian_breakout_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
    *,
    bridge_config: DonchianBreakoutConfig | None = None,
) -> dict[str, Any]:
    """Single-pass Donchian breakout backtest returning a report dict."""
    config = bridge_config or DonchianBreakoutConfig()
    config.validate()
    warmup = donchian_warmup_candles(config)

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

        if open_position is None:
            if (
                upper_level is not None
                and close > upper_level
                and cooldown_allows_entry(
                    ts_ms,
                    last_entry_ts_ms,
                    min_minutes_between_entries=config.min_minutes_between_entries,
                )
            ):
                signals_total += 1
                entry_reasons.append("donchian_upper_break")
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

    return _build_full_report(
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


def _build_full_report(
    *,
    candles: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    signals_total: int,
    entry_reasons: list[str],
    exit_reasons: list[str],
    config: DonchianBreakoutConfig,
    warmup: int,
    code_commit: str | None,
    run_id: str | None,
) -> dict[str, Any]:
    closed_count = len(trades)
    trade_returns = [t["r_return"] for t in trades]
    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r < 0]
    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    epsilon = 1e-12
    if gross_loss <= 0 and gross_profit > 0:
        gross_loss = epsilon
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    expectancy_r = sum(trade_returns) / closed_count if closed_count > 0 else 0.0

    fee_adj_returns = []
    for trade in trades:
        adj = trade["r_return"] - (trade["entry_fee"] + trade["exit_fee"]) / (
            trade["entry_price"] * ORDER_SIZE
        )
        fee_adj_returns.append(adj)
    fee_adj_expectancy = (
        sum(fee_adj_returns) / closed_count if closed_count > 0 else 0.0
    )
    fee_adj_wins = [r for r in fee_adj_returns if r > 0]
    fee_adj_losses = [r for r in fee_adj_returns if r < 0]
    fee_adj_pf = (
        sum(fee_adj_wins) / abs(sum(fee_adj_losses))
        if fee_adj_losses and abs(sum(fee_adj_losses)) > 0
        else 0.0
    )

    equity = 0.0
    peak = 0.0
    max_drawdown_r = 0.0
    for r_val in trade_returns:
        equity += r_val
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown_r:
            max_drawdown_r = drawdown

    gross_return_r = equity
    avg_win_r = sum(wins) / win_count if win_count > 0 else None
    avg_loss_r = sum(losses) / loss_count if loss_count > 0 else None
    gross_pnl = sum((t["exit_price"] - t["entry_price"]) * ORDER_SIZE for t in trades)
    fees_total = sum(t["entry_fee"] + t["exit_fee"] for t in trades)
    net_pnl = gross_pnl - fees_total
    fee_adj_return_r = sum(fee_adj_returns)

    first_ts = candles[0]["ts_ms"]
    last_ts = candles[-1]["ts_ms"]
    resolved_run_id = run_id or generate_uuid()

    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": DONCHIAN_BREAKOUT_STRATEGY_ID,
        "run_metadata": {
            "run_id": resolved_run_id,
            "generated_at": _utc_now_iso(),
            "source": "donchian_breakout_backtest_runner",
            "code_commit": code_commit or "unknown",
        },
        "config_snapshot": {
            "entry_channel_bars": config.entry_channel_bars,
            "exit_channel_bars": config.exit_channel_bars,
            "min_minutes_between_entries": config.min_minutes_between_entries,
            "trade_side_mode": config.trade_side_mode,
            "warmup_candles": warmup,
            "order_size": ORDER_SIZE,
            "ranking_ready": False,
        },
        "dataset_summary": {
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "candles_total": len(candles),
            "candles_live": max(0, len(candles) - warmup),
            "period_start_ts_ms": first_ts,
            "period_end_ts_ms": last_ts,
            "warmup_candles": warmup,
        },
        "metrics": {
            "signals_total": signals_total,
            "buy_signals_total": signals_total,
            "sell_signals_total": closed_count,
            "closed_trades_total": closed_count,
            "gross_return_r": gross_return_r,
            "fee_adjusted_return_r": fee_adj_return_r,
            "profit_factor": profit_factor,
            "fee_adjusted_profit_factor": fee_adj_pf,
            "expectancy_r": expectancy_r,
            "fee_adjusted_expectancy_r": fee_adj_expectancy,
            "max_drawdown_r": max_drawdown_r,
            "win_rate": win_count / closed_count if closed_count > 0 else 0.0,
            "avg_win_r": avg_win_r,
            "avg_loss_r": avg_loss_r,
            "trades_win_count": win_count,
            "trades_loss_count": loss_count,
            "gross_pnl_quote": gross_pnl,
            "net_pnl_quote": net_pnl,
            "fees_total_quote": fees_total,
            "deterministic_replay_ok": False,
            "ranking_ready": False,
        },
        "trades": trades,
        "thresholds_applied": {
            "donchian_upper_break": entry_reasons.count("donchian_upper_break"),
            "donchian_lower_break": exit_reasons.count("donchian_lower_break"),
        },
        "entry_reasons": entry_reasons,
        "exit_reasons": exit_reasons,
        "gate_result": {
            "status": "NOT_RANKING_READY",
            "ranking_ready": False,
        },
    }


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": DONCHIAN_BREAKOUT_STRATEGY_ID,
        "run_metadata": {
            "run_id": run_id or generate_uuid(),
            "generated_at": _utc_now_iso(),
            "source": "donchian_breakout_backtest_runner",
            "code_commit": code_commit or "unknown",
            "early_exit_reason": reason,
        },
        "config_snapshot": {"ranking_ready": False},
        "dataset_summary": {},
        "metrics": {"ranking_ready": False, "deterministic_replay_ok": False},
        "trades": [],
        "entry_reasons": [],
        "exit_reasons": [],
        "gate_result": {"status": "NOT_RANKING_READY", "ranking_ready": False},
    }


def _utc_now_iso() -> str:
    return utcnow().replace(tzinfo=None).isoformat() + "Z"
