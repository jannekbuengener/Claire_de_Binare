"""Single-pass backtest runner for range_mean_reversion_v1.

Reuses existing signal functions from the RMR pipeline script but operates
on a single candle array (instead of the pipeline's multi-window manifest).
Produces a report dict compatible with the strategy_replay_runner dispatch.
"""

from __future__ import annotations

import logging
from typing import Any

from core.replay.historical_bridge import RANGE_MEAN_REVERSION_STRATEGY_ID
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid
from scripts.profitability.run_range_mean_reversion_pipeline_3157 import (
    compute_atr,
    compute_z_scores,
    evaluate_range_reversion_candle,
    ATR_PERIOD,
    ATR_STOP_MULT,
    COOLDOWN_MINUTES,
    ENTRY_THRESHOLD,
    EXIT_THRESHOLD,
    ORDER_BOOK_DEPTH_MULT,
    ORDER_SIZE,
    REGIME_BLOCKED,
    REGIME_RANGE,
    WARMUP_CANDLES,
    ZS_LOOKBACK,
)
from services.execution.simulator import ExecutionSimulator

logger = logging.getLogger(__name__)

SCENARIO_OVERRIDE_KEYS = frozenset({
    "BASE_SLIPPAGE_BPS", "VOLATILITY_SLIPPAGE_FACTOR",
    "FILL_THRESHOLD", "PRICE_IMPACT_FACTOR",
})


def run_range_mean_reversion_backtest(
    candles: list[dict[str, Any]],
    run_config: dict[str, Any] | None = None,
    simulator_config: dict[str, Any] | None = None,
    code_commit: str | None = None,
) -> dict[str, Any]:
    """Single-pass RMR backtest returning a report dict.

    Args:
        candles: Regime-calibrated candle dicts with ts_ms, high, low, close,
            volume, regime_id.
        run_config: Optional override dict (entry_threshold, etc.).
        simulator_config: Optional overrides for ExecutionSimulator.
        code_commit: Optional commit SHA for provenance.

    Returns:
        Report dict with run_metadata, metrics, trades, etc.
    """
    if not candles:
        return _build_minimal_report("no_data", code_commit)

    if len(candles) <= WARMUP_CANDLES:
        return _build_minimal_report("insufficient_candles", code_commit)

    # Extract price arrays
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    # Compute indicators
    z_scores = compute_z_scores(closes, ZS_LOOKBACK)
    atr_values = compute_atr(highs, lows, closes, ATR_PERIOD)

    # Apply config overrides
    entry_threshold = ENTRY_THRESHOLD
    exit_threshold = EXIT_THRESHOLD
    atr_stop_mult = ATR_STOP_MULT
    if run_config:
        entry_threshold = run_config.get("entry_threshold", entry_threshold)
        exit_threshold = run_config.get("exit_threshold", exit_threshold)
        atr_stop_mult = run_config.get("atr_stop_mult", atr_stop_mult)

    # Build simulator
    sim = ExecutionSimulator(config=simulator_config or {})

    live_candles = candles[WARMUP_CANDLES:]
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    signals_total = 0
    last_entry_ts_ms: int | None = None
    entry_reasons: list[str] = []
    exit_reasons: list[str] = []
    warmup_len = WARMUP_CANDLES

    for idx, candle in enumerate(live_candles):
        candle_idx = warmup_len + idx
        close = float(candle["close"])
        z_score = z_scores[candle_idx]
        atr_val = atr_values[candle_idx]
        regime_id = candle["regime_id"]
        ts_ms = candle["ts_ms"]
        volume = float(candle.get("volume", 0.0))

        decision = evaluate_range_reversion_candle(
            close=close,
            z_score=z_score,
            atr=atr_val,
            regime_id=regime_id,
            position_open=open_position is not None,
            entry_price=open_position["entry_price"] if open_position else None,
            entry_ts_ms=open_position["entry_ts_ms"] if open_position else None,
            ts_ms=ts_ms,
            last_entry_ts_ms=last_entry_ts_ms,
        )

        if decision.entry:
            signals_total += 1
            entry_reasons.append("zscore_entry")
            volatility = atr_val / close if atr_val and close > 0 else 0.0
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

        elif decision.exit_signal and open_position is not None:
            exit_price = (
                decision.exit_price if decision.exit_price is not None else close
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

            trades.append({
                "entry_ts_ms": open_position["entry_ts_ms"],
                "exit_ts_ms": ts_ms,
                "entry_price": open_position["entry_price"],
                "exit_price": fill.avg_fill_price,
                "entry_fee": open_position["entry_fee"],
                "exit_fee": fill.fees,
                "r_return": trade_r,
                "reason": decision.reason,
            })
            open_position = None

    return _build_full_report(
        candles=candles,
        trades=trades,
        signals_total=signals_total,
        entry_reasons=entry_reasons,
        exit_reasons=exit_reasons,
        run_config=run_config,
        simulator_config=simulator_config,
        code_commit=code_commit,
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
    run_id = generate_uuid()

    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": RANGE_MEAN_REVERSION_STRATEGY_ID,
        "run_metadata": {
            "run_id": run_id,
            "generated_at": _utc_now_iso(),
            "source": "rmr_backtest_runner",
            "code_commit": code_commit or "unknown",
        },
        "config_snapshot": {
            "entry_threshold": (run_config or {}).get(
                "entry_threshold", ENTRY_THRESHOLD
            ),
            "exit_threshold": (run_config or {}).get(
                "exit_threshold", EXIT_THRESHOLD
            ),
            "zs_lookback": ZS_LOOKBACK,
            "atr_period": ATR_PERIOD,
            "atr_stop_mult": (run_config or {}).get(
                "atr_stop_mult", ATR_STOP_MULT
            ),
            "cooldown_minutes": COOLDOWN_MINUTES,
            "warmup_candles": WARMUP_CANDLES,
            "order_size": ORDER_SIZE,
        },
        "dataset_summary": {
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "candles_total": len(candles),
            "candles_live": max(0, len(candles) - WARMUP_CANDLES),
            "period_start_ms": first_ts,
            "period_end_ms": last_ts,
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
            "entry_threshold": entry_reasons.count("zscore_entry"),
            "exit_mean_reversion": exit_reasons.count("mean_reversion"),
            "exit_atr_stop": exit_reasons.count("atr_stop"),
        },
        "entry_reasons": entry_reasons,
        "exit_reasons": exit_reasons,
    }


def _build_minimal_report(
    reason: str, code_commit: str | None = None
) -> dict[str, Any]:
    """Minimal report for early-exit conditions (no trades possible)."""
    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": RANGE_MEAN_REVERSION_STRATEGY_ID,
        "run_metadata": {
            "run_id": generate_uuid(),
            "generated_at": _utc_now_iso(),
            "source": "rmr_backtest_runner",
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
