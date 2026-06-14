"""Single-pass backtest runner for momentum_capture_v1.

Reuses existing signal functions from the momentum capture pipeline script
but operates on a single candle array (instead of the pipeline's multi-window
manifest). Produces a report dict compatible with the strategy_replay_runner
dispatch.
"""

from __future__ import annotations

import logging
from typing import Any

from core.replay.historical_bridge import MOMENTUM_CAPTURE_STRATEGY_ID
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid
from scripts.profitability.run_momentum_capture_pipeline_3166 import (
    DIRECTIONAL_CANDLE_ATR_MULTIPLE,
    EXIT_ATR_CONTRACTION_MULTIPLE,
    EXIT_TRAILING_STOP_ATR_MULTIPLE,
    MAX_HOLD_BARS,
    COOLDOWN_MINUTES,
    ORDER_SIZE,
    ORDER_BOOK_DEPTH_MULT,
    ATR_PERIOD,
    WARMUP_CANDLES,
    REGIME_HVC,
    REGIME_BLOCKED,
    compute_atr,
    evaluate_momentum_capture_candle,
)
from services.execution.simulator import ExecutionSimulator

logger = logging.getLogger(__name__)


def run_momentum_capture_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Single-pass momentum capture backtest returning a report dict.

    Args:
        candles: Regime-calibrated candle dicts with ts_ms, open, high, low,
            close, volume, regime_id.
        run_config: Optional override dict (reserved for future scenario
            overrides; currently unused by momentum_capture_v1).
        simulator_config: Optional overrides for ExecutionSimulator.
        code_commit: Optional commit SHA for provenance.
        run_id: Optional deterministic run ID. When provided, used instead of
            generate_uuid() in the report.

    Returns:
        Report dict with run_metadata, metrics, trades, etc.
    """
    if not candles:
        return _build_minimal_report("no_data", code_commit, run_id=run_id)

    if len(candles) <= WARMUP_CANDLES:
        return _build_minimal_report(
            "insufficient_candles", code_commit, run_id=run_id
        )

    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    atr_values = compute_atr(highs, lows, closes, ATR_PERIOD)

    sim = ExecutionSimulator(config=simulator_config or {})

    live_candles = candles[WARMUP_CANDLES:]
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    signals_total = 0
    last_entry_ts_ms: int | None = None
    entry_reasons: list[str] = []
    exit_reasons: list[str] = []
    warmup_len = WARMUP_CANDLES
    hold_bars = 0
    entry_atr: float | None = None

    for idx, candle in enumerate(live_candles):
        candle_idx = warmup_len + idx
        close = float(candle["close"])
        open_price = float(candle["open"])
        atr_val = atr_values[candle_idx]
        regime_id = int(candle["regime_id"])
        ts_ms = int(candle["ts_ms"])
        volume = float(candle.get("volume", 0.0))

        if open_position is not None:
            hold_bars += 1

        decision = evaluate_momentum_capture_candle(
            close=close,
            open_price=open_price,
            atr=atr_val,
            regime_id=regime_id,
            position_open=open_position is not None,
            entry_price=open_position["entry_price"] if open_position else None,
            entry_atr=entry_atr if open_position else None,
            entry_ts_ms=(
                open_position["entry_ts_ms"] if open_position else None
            ),
            hold_bars=hold_bars if open_position else 0,
            ts_ms=ts_ms,
            last_entry_ts_ms=last_entry_ts_ms,
            current_market_regime=regime_id,
        )

        if decision.entry:
            signals_total += 1
            entry_reasons.append("directional_momentum_entry")
            volatility = atr_val / close if atr_val and close > 0 else 0.0
            order_book_depth = max(volume * close * ORDER_BOOK_DEPTH_MULT, close)

            fill = sim.simulate_market_order(
                side="buy",
                size=ORDER_SIZE,
                current_price=close,
                order_book_depth=order_book_depth,
                volatility=max(volatility, 0.0),
            )

            entry_atr = atr_val
            hold_bars = 0
            open_position = {
                "entry_ts_ms": ts_ms,
                "entry_price": fill.avg_fill_price,
                "entry_fee": fill.fees,
            }
            last_entry_ts_ms = ts_ms

        elif decision.exit_signal and open_position is not None:
            exit_price = (
                decision.exit_price
                if decision.exit_price is not None
                else close
            )
            volatility = atr_val / close if atr_val and close > 0 else 0.0
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
            exit_reasons.append(decision.reason)

            trades.append(
                {
                    "entry_ts_ms": open_position["entry_ts_ms"],
                    "exit_ts_ms": ts_ms,
                    "entry_price": open_position["entry_price"],
                    "exit_price": fill.avg_fill_price,
                    "entry_fee": open_position["entry_fee"],
                    "exit_fee": fill.fees,
                    "r_return": trade_r,
                    "reason": decision.reason,
                }
            )
            open_position = None
            hold_bars = 0

    return _build_full_report(
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        run_config=run_config,
        simulator_config=simulator_config,
        code_commit=code_commit,
        run_id=run_id,
    )


def _build_full_report(
    candles: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    signals_total: int,
    entry_reasons: list[str],
    exit_reasons: list[str],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a full report dict matching the schema expected by dispatch."""
    closed_count = len(trades)
    trade_returns = [t["r_return"] for t in trades]
    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r < 0]
    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    EPSILON = 1e-12
    if gross_loss <= 0 and gross_profit > 0:
        gross_loss = EPSILON
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    expectancy_r = sum(trade_returns) / closed_count if closed_count > 0 else 0.0

    fee_adj_returns = []
    for t in trades:
        adj = t["r_return"] - (t["entry_fee"] + t["exit_fee"]) / (
            t["entry_price"] * ORDER_SIZE
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
    for r in trade_returns:
        equity += r
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown_r:
            max_drawdown_r = drawdown

    gross_return_r = equity
    avg_win_r = sum(wins) / win_count if win_count > 0 else None
    avg_loss_r = sum(losses) / loss_count if loss_count > 0 else None
    gross_pnl = sum(
        (t["exit_price"] - t["entry_price"]) * ORDER_SIZE for t in trades
    )
    fees_total = sum(t["entry_fee"] + t["exit_fee"] for t in trades)
    net_pnl = gross_pnl - fees_total
    fee_adj_return_r = sum(fee_adj_returns)

    first_ts = candles[0]["ts_ms"]
    last_ts = candles[-1]["ts_ms"]
    run_id = run_id or generate_uuid()

    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": MOMENTUM_CAPTURE_STRATEGY_ID,
        "run_metadata": {
            "run_id": run_id,
            "generated_at": _utc_now_iso(),
            "source": "momentum_backtest_runner",
            "code_commit": code_commit or "unknown",
        },
        "config_snapshot": {
            "atr_period": ATR_PERIOD,
            "directional_candle_atr_multiple": DIRECTIONAL_CANDLE_ATR_MULTIPLE,
            "exit_atr_contraction_multiple": EXIT_ATR_CONTRACTION_MULTIPLE,
            "exit_trailing_stop_atr_multiple": EXIT_TRAILING_STOP_ATR_MULTIPLE,
            "max_hold_bars": MAX_HOLD_BARS,
            "cooldown_minutes": COOLDOWN_MINUTES,
            "warmup_candles": WARMUP_CANDLES,
            "order_size": ORDER_SIZE,
            "regime_hvc": REGIME_HVC,
        },
        "dataset_summary": {
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "candles_total": len(candles),
            "candles_live": max(0, len(candles) - WARMUP_CANDLES),
            "period_start_ts_ms": first_ts,
            "period_end_ts_ms": last_ts,
            "warmup_candles": WARMUP_CANDLES,
        },
        "metrics": {
            "signals_total": signals_total,
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
        },
        "trades": trades,
        "thresholds_applied": {
            "entry_directional_momentum": entry_reasons.count(
                "directional_momentum_entry"
            ),
            "exit_max_hold": exit_reasons.count("max_hold"),
            "exit_atr_contraction": exit_reasons.count("atr_contraction"),
            "exit_trailing_stop": exit_reasons.count("trailing_stop"),
        },
        "entry_reasons": entry_reasons,
        "exit_reasons": exit_reasons,
    }


def _build_minimal_report(
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Minimal report for early-exit conditions (no trades possible)."""
    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": MOMENTUM_CAPTURE_STRATEGY_ID,
        "run_metadata": {
            "run_id": run_id or generate_uuid(),
            "generated_at": _utc_now_iso(),
            "source": "momentum_backtest_runner",
            "code_commit": code_commit or "unknown",
            "early_exit_reason": reason,
        },
        "config_snapshot": {},
        "dataset_summary": {},
        "metrics": {},
        "trades": [],
        "entry_reasons": [],
        "exit_reasons": [],
    }


def _utc_now_iso() -> str:
    return utcnow().isoformat()
