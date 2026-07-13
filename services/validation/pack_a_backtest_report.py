"""Shared strategy_validation_report.v1 builders for Pack-A backtest runners."""

from __future__ import annotations

from typing import Any

from core.replay.pack_a_breakout_common import ORDER_SIZE
from core.replay.regime_stats import build_regime_stats_from_replay
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid


def build_pack_a_full_report(
    *,
    strategy_id: str,
    source: str,
    candles: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    signals_total: int,
    entry_reasons: list[str],
    exit_reasons: list[str],
    config_snapshot: dict[str, Any],
    warmup: int,
    code_commit: str | None,
    run_id: str | None,
    thresholds_applied: dict[str, int] | None = None,
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
    snapshot = dict(config_snapshot)
    snapshot.setdefault("ranking_ready", False)
    snapshot.setdefault("warmup_candles", warmup)
    snapshot.setdefault("order_size", ORDER_SIZE)

    regime_stats = build_regime_stats_from_replay(
        candles,
        trades,
        warmup=warmup,
    )

    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": strategy_id,
        "run_metadata": {
            "run_id": resolved_run_id,
            "generated_at": _utc_now_iso(),
            "source": source,
            "code_commit": code_commit or "unknown",
        },
        "config_snapshot": snapshot,
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
        "thresholds_applied": thresholds_applied or {},
        "entry_reasons": entry_reasons,
        "exit_reasons": exit_reasons,
        "gate_result": {
            "status": "NOT_RANKING_READY",
            "ranking_ready": False,
        },
        "regime_stats": regime_stats,
    }


def build_pack_a_minimal_report(
    *,
    strategy_id: str,
    source: str,
    reason: str,
    code_commit: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_validation_report.v1",
        "strategy_id": strategy_id,
        "run_metadata": {
            "run_id": run_id or generate_uuid(),
            "generated_at": _utc_now_iso(),
            "source": source,
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
