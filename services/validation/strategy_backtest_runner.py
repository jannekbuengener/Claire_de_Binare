"""Deterministic historical backtest runner for ``primary_breakout_v1``.

This module stays intentionally narrow:
- one strategy id
- one historical bridge
- one adapter
- one validation report shape
- one fail-closed gate decision
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from core.contracts.external_adapter_contracts import (
    StrategyAdapterRequest,
    StrategyAdapterResponse,
    StrategySignalCandidate,
)
from core.replay.historical_bridge import (
    PRIMARY_BREAKOUT_STRATEGY_ID,
    PRIMARY_BREAKOUT_SYMBOL,
    PrimaryBreakoutBridgeConfig,
    build_primary_breakout_historical_bridge,
)
from services.execution.simulator import ExecutionSimulator

REPORT_SCHEMA_VERSION = "strategy_validation_report.v1"
REPORT_SOURCE = "historical_backtest_v1"
THRESHOLD_PROFILE_ID = "primary_breakout_v1_validation_thresholds"
THRESHOLD_PROFILE_VERSION = "1"
DEFAULT_REPORT_DIR = Path("reports") / "primary_breakout_v1_backtest"
_EPSILON = 1e-12
_RUNNER_ADAPTER_ID = "primary_breakout_runner_v1"


class PrimaryBreakoutBacktestError(ValueError):
    """Raised when the runner cannot produce a valid deterministic report."""


@dataclass(frozen=True, slots=True)
class PrimaryBreakoutBacktestRunConfig:
    """Small runner-facing config surface."""

    bridge: PrimaryBreakoutBridgeConfig = PrimaryBreakoutBridgeConfig()
    order_size: float = 1.0
    order_book_depth_multiplier: float = 10_000.0

    def validate(self) -> None:
        self.bridge.validate()
        if self.order_size <= 0:
            raise PrimaryBreakoutBacktestError("order_size must be > 0")
        if self.order_book_depth_multiplier <= 0:
            raise PrimaryBreakoutBacktestError(
                "order_book_depth_multiplier must be > 0"
            )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _deterministic_run_id(
    requests: Sequence[StrategyAdapterRequest],
    config: PrimaryBreakoutBacktestRunConfig,
    code_commit: str,
    simulator_config: Mapping[str, Any] | None = None,
) -> str:
    payload = {
        "code_commit": code_commit,
        "config": asdict(config),
        "requests": [
            {
                "symbol": request.symbol,
                "market_event": request.market_event,
                "market_snapshot": request.market_snapshot,
                "runtime_context": request.runtime_context,
            }
            for request in requests
        ],
    }
    if simulator_config:
        payload["simulator_config"] = dict(simulator_config)
    return f"bt-{_sha256_text(_canonical_json(payload))[:16]}"


def _ts_ms_to_utc_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()


def _first_number(*values: Any) -> float | None:
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_execution_delay_bars(
    simulator_config: Mapping[str, Any] | None,
) -> int:
    if simulator_config is None:
        return 0
    delay_bars = simulator_config.get("EXECUTION_DELAY_BARS", 0)
    if delay_bars is None:
        return 0
    if isinstance(delay_bars, bool) or not isinstance(delay_bars, int):
        raise PrimaryBreakoutBacktestError(
            "EXECUTION_DELAY_BARS must be an integer >= 0"
        )
    if delay_bars < 0:
        raise PrimaryBreakoutBacktestError("EXECUTION_DELAY_BARS must be >= 0")
    return delay_bars


def _execution_bar_volatility(
    request: StrategyAdapterRequest,
    reference_price: float,
) -> float:
    if reference_price <= 0:
        return 0.0

    open_price = _first_number(
        request.market_snapshot.get("open"),
        request.market_event.get("open"),
        reference_price,
    )
    close_price = _first_number(
        request.market_snapshot.get("close"),
        request.market_event.get("close"),
        request.market_event.get("price"),
        reference_price,
    )
    high_price = _first_number(
        request.market_snapshot.get("high"),
        request.market_event.get("high"),
    )
    low_price = _first_number(
        request.market_snapshot.get("low"),
        request.market_event.get("low"),
    )

    bar_move = (
        abs(close_price - open_price) / reference_price
        if open_price is not None and close_price is not None
        else 0.0
    )
    bar_range = (
        abs(high_price - low_price) / reference_price
        if high_price is not None and low_price is not None
        else 0.0
    )
    return max(bar_move, bar_range, 0.0)


def _build_pending_execution(
    signal: StrategySignalCandidate,
    request_index: int,
    bridge_requests: Sequence[StrategyAdapterRequest],
    execution_delay_bars: int,
) -> dict[str, Any]:
    target_idx = request_index + execution_delay_bars
    if target_idx >= len(bridge_requests):
        raise PrimaryBreakoutBacktestError(
            "Delayed execution out of range: "
            f"signal at index {request_index} with execution_delay_bars="
            f"{execution_delay_bars} targets index {target_idx}, "
            f"but only {len(bridge_requests)} bridge requests are available"
        )

    execution_request = bridge_requests[target_idx]
    execution_price = _first_number(
        execution_request.market_snapshot.get("close"),
        execution_request.market_event.get("close"),
        execution_request.market_event.get("price"),
        signal.price,
    )
    if execution_price is None:
        raise PrimaryBreakoutBacktestError("delayed execution target missing price")

    return {
        "side": signal.side,
        "target_idx": target_idx,
        "execution_price": execution_price,
        "ts_ms": int(execution_request.market_event["ts_ms"]),
        "volume": _first_number(execution_request.market_snapshot.get("volume")) or 0.0,
        "volatility": _execution_bar_volatility(execution_request, execution_price),
    }


def _extract_thresholds() -> dict[str, Any]:
    return {
        "threshold_profile_id": THRESHOLD_PROFILE_ID,
        "threshold_profile_version": THRESHOLD_PROFILE_VERSION,
        "pass_fail": {
            "min_closed_trades_total": 20,
            "min_profit_factor": 1.05,
            "min_expectancy_r": 0.0,
            "max_max_drawdown_r": 3.0,
            "min_market_state_fresh_ratio": 0.99,
            "min_regime_fresh_ratio": 0.99,
            "require_data_integrity_ok": True,
            "require_deterministic_replay_ok": True,
        },
    }


def _evaluate_gate(
    metrics: Mapping[str, Any], thresholds: Mapping[str, Any]
) -> dict[str, Any]:
    pass_fail = thresholds["pass_fail"]
    failed_criteria: list[str] = []
    if int(metrics["closed_trades_total"]) < pass_fail["min_closed_trades_total"]:
        failed_criteria.append("min_closed_trades_total")
    if float(metrics["profit_factor"]) < pass_fail["min_profit_factor"]:
        failed_criteria.append("min_profit_factor")
    if float(metrics["expectancy_r"]) < pass_fail["min_expectancy_r"]:
        failed_criteria.append("min_expectancy_r")
    if float(metrics["max_drawdown_r"]) > pass_fail["max_max_drawdown_r"]:
        failed_criteria.append("max_max_drawdown_r")
    if (
        float(metrics["market_state_fresh_ratio"])
        < pass_fail["min_market_state_fresh_ratio"]
    ):
        failed_criteria.append("min_market_state_fresh_ratio")
    if float(metrics["regime_fresh_ratio"]) < pass_fail["min_regime_fresh_ratio"]:
        failed_criteria.append("min_regime_fresh_ratio")
    if bool(metrics["data_integrity_ok"]) is not pass_fail["require_data_integrity_ok"]:
        failed_criteria.append("data_integrity_ok")
    if (
        bool(metrics["deterministic_replay_ok"])
        is not pass_fail["require_deterministic_replay_ok"]
    ):
        failed_criteria.append("deterministic_replay_ok")

    review_flags: list[str] = []
    if not failed_criteria:
        if int(metrics["closed_trades_total"]) < 40:
            review_flags.append("closed_trades_total")
        if float(metrics["profit_factor"]) < 1.2:
            review_flags.append("profit_factor")
        if float(metrics["max_drawdown_r"]) > 2.0:
            review_flags.append("max_drawdown_r")

    if failed_criteria:
        status = "FAIL"
    elif review_flags:
        status = "REVIEW"
    else:
        status = "PASS"

    notes = None
    if status != "PASS":
        notes = (
            "failed criteria" if failed_criteria else "review-only thresholds flagged"
        )

    payload: dict[str, Any] = {
        "status": status,
        "failed_criteria": failed_criteria,
        "review_flags": review_flags,
    }
    if notes is not None:
        payload["notes"] = notes
    return payload


def _simulate_trade(
    *,
    side: str,
    price: float,
    ts_ms: int,
    volume: float,
    simulator: ExecutionSimulator,
    order_size: float,
    order_book_depth_multiplier: float,
    volatility: float,
) -> dict[str, Any]:
    result = simulator.simulate_market_order(
        side=side.lower(),
        size=order_size,
        current_price=price,
        order_book_depth=max(volume * price * order_book_depth_multiplier, price),
        volatility=max(volatility, 0.0),
    )
    return {
        "side": side,
        "ts_ms": ts_ms,
        "filled_size": result.filled_size,
        "avg_fill_price": result.avg_fill_price,
        "slippage_bps": result.slippage_bps,
        "fees": result.fees,
        "partial_fill": result.partial_fill,
        "fill_ratio": result.fill_ratio,
        "notes": result.notes,
    }


def _execute_pending_signal(
    exec_info: dict[str, Any],
    open_position: dict[str, Any] | None,
    trades: list[dict[str, Any]],
    simulator: ExecutionSimulator,
    config: PrimaryBreakoutBacktestRunConfig,
) -> dict[str, Any] | None:
    """Execute a pending signal from the delayed execution queue."""
    side = exec_info["side"]
    execution_price = exec_info["execution_price"]
    ts_ms = exec_info["ts_ms"]
    volume = exec_info["volume"]
    volatility = exec_info["volatility"]

    if side == "BUY":
        if open_position is not None:
            return open_position
        fill = _simulate_trade(
            side="buy",
            price=execution_price,
            ts_ms=ts_ms,
            volume=volume,
            simulator=simulator,
            order_size=config.order_size,
            order_book_depth_multiplier=config.order_book_depth_multiplier,
            volatility=volatility,
        )
        return {
            "entry_price": fill["avg_fill_price"],
            "entry_ts_ms": ts_ms,
            "entry_fee": fill["fees"],
        }
    elif side == "SELL" and open_position is not None:
        fill = _simulate_trade(
            side="sell",
            price=execution_price,
            ts_ms=ts_ms,
            volume=volume,
            simulator=simulator,
            order_size=config.order_size,
            order_book_depth_multiplier=config.order_book_depth_multiplier,
            volatility=volatility,
        )
        entry_price = float(open_position["entry_price"])
        exit_price = float(fill["avg_fill_price"])
        trade_r = (exit_price - entry_price) / entry_price
        trades.append(
            {
                "entry_ts_ms": int(open_position["entry_ts_ms"]),
                "exit_ts_ms": ts_ms,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_fee": float(open_position["entry_fee"]),
                "exit_fee": float(fill["fees"]),
                "r_return": trade_r,
            }
        )
        return None
    return open_position


def _build_data_integrity_diagnostics(
    open_position: Mapping[str, Any] | None,
    pending_signals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Serialize the terminal runner state without changing gate semantics."""

    serialized_open_position: dict[str, Any] | None = None
    if open_position is not None:
        serialized_open_position = {
            "entry_price": float(open_position["entry_price"]),
            "entry_ts_ms": int(open_position["entry_ts_ms"]),
            "entry_fee": float(open_position["entry_fee"]),
        }

    serialized_pending_signals = [
        {
            "side": str(pending["side"]),
            "target_idx": int(pending["target_idx"]),
            "execution_price": float(pending["execution_price"]),
            "ts_ms": int(pending["ts_ms"]),
            "volume": float(pending["volume"]),
            "volatility": float(pending["volatility"]),
        }
        for pending in pending_signals
    ]

    has_open_position = serialized_open_position is not None
    has_pending_signals = bool(serialized_pending_signals)
    if has_open_position and has_pending_signals:
        reason = "open_position_and_pending_signals_at_end"
    elif has_open_position:
        reason = "open_position_at_end"
    elif has_pending_signals:
        reason = "pending_signals_at_end"
    else:
        reason = "clean"

    return {
        "data_integrity_reason": reason,
        "open_position_at_end": serialized_open_position,
        "pending_signals_at_end": serialized_pending_signals,
    }


def _serialize_response(response: StrategyAdapterResponse) -> dict[str, Any]:
    return {
        "signals": [
            {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "side": signal.side,
                "reason": signal.reason,
                "price": signal.price,
                "metadata": dict(signal.metadata or {}),
            }
            for signal in response.signals
        ],
        "diagnostics": dict(response.diagnostics or {}),
    }


def _evaluate_primary_breakout_request(
    request: StrategyAdapterRequest,
    *,
    position_open: bool,
    last_entry_ts_ms: int | None,
    config: PrimaryBreakoutBacktestRunConfig,
    gate_trace_callback: Optional[Callable[[Mapping[str, Any]], None]] = None,
) -> tuple[StrategyAdapterResponse, int | None]:
    market_state = request.market_event.get("market_state")
    if not isinstance(market_state, Mapping):
        raise PrimaryBreakoutBacktestError("market_state missing in historical request")

    ts_ms_raw = request.market_event.get("ts_ms")
    if ts_ms_raw is None:
        raise PrimaryBreakoutBacktestError("ts_ms missing in historical request")
    ts_ms = int(ts_ms_raw)

    close_now = _first_number(
        market_state.get("close_now"),
        request.market_snapshot.get("close"),
        request.market_event.get("close"),
        request.market_event.get("price"),
    )
    highest_high = _first_number(market_state.get("highest_high"))
    lowest_low = _first_number(market_state.get("lowest_low"))
    if close_now is None or highest_high is None or lowest_low is None:
        return (
            StrategyAdapterResponse(
                diagnostics={
                    "adapter_id": _RUNNER_ADAPTER_ID,
                    "status": "insufficient_input",
                }
            ),
            last_entry_ts_ms,
        )

    regime_id = market_state.get("regime_id")
    market_state_fresh = bool(market_state.get("market_state_fresh"))
    regime_fresh = bool(market_state.get("regime_fresh"))
    has_trend_regime = regime_id in {0, "TREND"}
    entry_blocked = any(
        bool(market_state.get(name))
        for name in (
            "shutdown_active",
            "kill_switch_active",
            "risk_blocked",
            "allocation_blocked",
            "core_blocked",
        )
    )
    entry_cooldown_active = bool(market_state.get("entry_cooldown_active"))
    if not entry_cooldown_active and last_entry_ts_ms is not None:
        cooldown_ms = config.bridge.min_minutes_between_entries * 60_000
        entry_cooldown_active = ts_ms - last_entry_ts_ms < cooldown_ms

    if position_open and close_now < lowest_low:
        return (
            StrategyAdapterResponse(
                signals=(
                    StrategySignalCandidate(
                        strategy_id=PRIMARY_BREAKOUT_STRATEGY_ID,
                        symbol=PRIMARY_BREAKOUT_SYMBOL,
                        side="SELL",
                        reason="channel_exit",
                        price=close_now,
                        metadata={"adapter_id": _RUNNER_ADAPTER_ID},
                    ),
                ),
                diagnostics={
                    "adapter_id": _RUNNER_ADAPTER_ID,
                    "status": "signal_emitted",
                },
            ),
            last_entry_ts_ms,
        )

    entry_ready = (
        not position_open
        and market_state_fresh
        and regime_fresh
        and has_trend_regime
        and not entry_blocked
        and not entry_cooldown_active
        and close_now > highest_high * (1 + config.bridge.breakout_buffer)
    )

    if gate_trace_callback:
        gate_trace_callback(
            {
                "ts_ms": ts_ms,
                "symbol": request.symbol,
                "close_now": close_now,
                "highest_high": highest_high,
                "breakout_threshold": highest_high * (1 + config.bridge.breakout_buffer),
                "breakout_buffer": config.bridge.breakout_buffer,
                "market_state_fresh": market_state_fresh,
                "regime_fresh": regime_fresh,
                "regime_id": regime_id,
                "has_trend_regime": has_trend_regime,
                "entry_blocked": entry_blocked,
                "entry_cooldown_active": entry_cooldown_active,
                "position_open": position_open,
                "last_entry_ts_ms": last_entry_ts_ms,
                "entry_ready": entry_ready,
                "status": "signal_emitted" if entry_ready else "no_signal",
            }
        )

    if entry_ready:
        return (
            StrategyAdapterResponse(
                signals=(
                    StrategySignalCandidate(
                        strategy_id=PRIMARY_BREAKOUT_STRATEGY_ID,
                        symbol=PRIMARY_BREAKOUT_SYMBOL,
                        side="BUY",
                        reason="breakout_entry",
                        price=close_now,
                        metadata={"adapter_id": _RUNNER_ADAPTER_ID},
                    ),
                ),
                diagnostics={
                    "adapter_id": _RUNNER_ADAPTER_ID,
                    "status": "signal_emitted",
                },
            ),
            ts_ms,
        )

    return (
        StrategyAdapterResponse(
            diagnostics={
                "adapter_id": _RUNNER_ADAPTER_ID,
                "status": "no_signal",
            }
        ),
        last_entry_ts_ms,
    )


def _build_report(
    *,
    bridge_requests: Sequence[StrategyAdapterRequest],
    run_config: PrimaryBreakoutBacktestRunConfig,
    code_commit: str,
    simulator_config: Mapping[str, Any] | None,
    output_requests: Sequence[dict[str, Any]],
    trades: Sequence[dict[str, Any]],
    market_state_fresh_ratio: float,
    regime_fresh_ratio: float,
    data_integrity_ok: bool,
    data_integrity_diagnostics: Mapping[str, Any],
    deterministic_replay_ok: bool,
    requested_period_start_ts_ms: int,
    requested_period_end_ts_ms: int,
) -> dict[str, Any]:
    if not bridge_requests:
        raise PrimaryBreakoutBacktestError("bridge produced no requests")

    run_id = _deterministic_run_id(
        bridge_requests,
        run_config,
        code_commit,
        simulator_config=simulator_config,
    )
    # Effective bridge start: first candle after the warm-up window
    # (max(entry_lookback, exit_lookback) candles consumed as lookback).
    # Offset from requested_period_start_ts_ms by max_lookback * 60_000 ms.
    first_ts_ms = int(bridge_requests[0].market_event["ts_ms"])
    last_ts_ms = int(bridge_requests[-1].market_event["ts_ms"])

    trade_returns = [float(trade["r_return"]) for trade in trades]
    wins = [trade_r for trade_r in trade_returns if trade_r > 0]
    losses = [trade_r for trade_r in trade_returns if trade_r < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss <= 0 and gross_profit > 0:
        gross_loss = _EPSILON
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    expectancy_r = sum(trade_returns) / len(trade_returns) if trade_returns else 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown_r = 0.0
    for trade_r in trade_returns:
        equity += trade_r
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown_r:
            max_drawdown_r = drawdown

    gross_return_r = equity
    avg_win_r = sum(wins) / len(wins) if wins else None
    avg_loss_r = sum(losses) / len(losses) if losses else None
    largest_win_r = max(wins) if wins else None
    largest_loss_r = min(losses) if losses else None
    trades_win_count = len(wins)
    trades_loss_count = len(losses)

    order_size = float(run_config.order_size)
    gross_pnl_quote = sum(
        (float(t["exit_price"]) - float(t["entry_price"])) * order_size
        for t in trades
    )
    fees_total = sum(
        float(t.get("entry_fee", 0.0)) + float(t.get("exit_fee", 0.0))
        for t in trades
    )
    net_pnl_quote = gross_pnl_quote - fees_total

    # Fee-adjusted trade returns for r-multiple metrics
    fee_adj_trade_returns = [
        float(trade.get("exit_price", 0.0)) / float(trade.get("entry_price", 1.0)) - 1.0
        - (float(trade.get("entry_fee", 0.0)) + float(trade.get("exit_fee", 0.0)))
        / (float(trade.get("entry_price", 1.0)) * order_size)
        for trade in trades
    ] if trades else []
    if fee_adj_trade_returns:
        fee_adj_equity = 0.0
        fee_adj_peak = 0.0
        fee_adj_max_drawdown_r = 0.0
        for r in fee_adj_trade_returns:
            fee_adj_equity += r
            fee_adj_peak = max(fee_adj_peak, fee_adj_equity)
            fee_adj_max_drawdown_r = max(
                fee_adj_max_drawdown_r, fee_adj_peak - fee_adj_equity
            )
        fee_adj_expectancy_r = sum(fee_adj_trade_returns) / len(fee_adj_trade_returns)
        fee_adj_wins = [r for r in fee_adj_trade_returns if r > 0]
        fee_adj_losses = [r for r in fee_adj_trade_returns if r < 0]
        fee_adj_gross_profit = sum(fee_adj_wins)
        fee_adj_gross_loss = abs(sum(fee_adj_losses))
        if fee_adj_gross_loss <= 0 and fee_adj_gross_profit > 0:
            fee_adj_gross_loss = _EPSILON
        fee_adj_profit_factor = (
            fee_adj_gross_profit / fee_adj_gross_loss
            if fee_adj_gross_loss > 0
            else 0.0
        )
    else:
        fee_adj_expectancy_r = None
        fee_adj_profit_factor = None
        fee_adj_max_drawdown_r = None

    signals_total = len(output_requests)
    buy_signals_total = sum(1 for signal in output_requests if signal["side"] == "BUY")
    sell_signals_total = sum(
        1 for signal in output_requests if signal["side"] == "SELL"
    )
    closed_trades_total = len(trades)

    # Sample size verdict for economics interpretability
    if closed_trades_total == 0:
        sample_size_verdict = "no_trades"
    elif closed_trades_total < 5:
        sample_size_verdict = "insufficient"
    elif closed_trades_total < 30:
        sample_size_verdict = "weak"
    elif closed_trades_total < 100:
        sample_size_verdict = "usable"
    else:
        sample_size_verdict = "adequate"

    metrics = {
        "signals_total": signals_total,
        "buy_signals_total": buy_signals_total,
        "sell_signals_total": sell_signals_total,
        "closed_trades_total": closed_trades_total,
        "win_rate": (len(wins) / len(trade_returns)) if trade_returns else 0.0,
        "profit_factor": profit_factor,
        "expectancy_r": expectancy_r,
        "max_drawdown_r": max_drawdown_r,
        "market_state_fresh_ratio": market_state_fresh_ratio,
        "regime_fresh_ratio": regime_fresh_ratio,
        "data_integrity_ok": data_integrity_ok,
        "data_integrity_diagnostics": dict(data_integrity_diagnostics),
        "deterministic_replay_ok": deterministic_replay_ok,
        # Extended economics fields
        "gross_return_r": gross_return_r,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "largest_win_r": largest_win_r,
        "largest_loss_r": largest_loss_r,
        "trades_win_count": trades_win_count,
        "trades_loss_count": trades_loss_count,
        "gross_pnl_quote": gross_pnl_quote,
        "net_pnl_quote": net_pnl_quote,
        "fees_total_quote": fees_total,
        "fee_adjusted_expectancy_r": fee_adj_expectancy_r,
        "fee_adjusted_profit_factor": fee_adj_profit_factor,
        "fee_adjusted_max_drawdown_r": fee_adj_max_drawdown_r,
        "sample_size_verdict": sample_size_verdict,
        "metrics_availability": {
            "trade_level_pnl_available": bool(trades),
            "fee_adjusted_returns_available": bool(trades),
            "equity_curve_available": False,
            "equity_curve_note": (
                "Per-bar equity snapshots not available. "
                "Drawdown computed from end-of-trade point estimates only."
            ),
            "absolute_drawdown_quote_available": False,
            "absolute_drawdown_quote_note": (
                "Max drawdown available as r-multiple only (max_drawdown_r). "
                "Absolute quote drawdown requires an equity curve with per-bar nav."
            ),
            "sharpe_ratio_available": False,
            "sharpe_ratio_note": (
                "Requires return time series (per-bar or per-trade with durations). "
                "Not computable from end-of-trade point returns alone."
            ),
            "slippage_per_trade_available": False,
            "slippage_note": (
                "Execution simulator slippage is accounted for in fill prices. "
                "Per-trade slippage breakdown not exposed in trade dict."
            ),
        },
    }
    thresholds = _extract_thresholds()
    gate_result = _evaluate_gate(metrics, thresholds)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "strategy_id": PRIMARY_BREAKOUT_STRATEGY_ID,
        "run_metadata": {
            "run_id": run_id,
            "generated_at": _ts_ms_to_utc_iso(last_ts_ms),
            "source": REPORT_SOURCE,
            "code_commit": code_commit,
        },
        "config_snapshot": {
            "entry_lookback_minutes": run_config.bridge.entry_lookback_minutes,
            "exit_lookback_minutes": run_config.bridge.exit_lookback_minutes,
            "breakout_buffer": run_config.bridge.breakout_buffer,
            "min_minutes_between_entries": run_config.bridge.min_minutes_between_entries,
            "trade_side_mode": run_config.bridge.trade_side_mode,
        },
        "dataset_summary": {
            "symbol": PRIMARY_BREAKOUT_SYMBOL,
            "timeframe": "1m",
            "candles_total": len(bridge_requests)
            + max(
                run_config.bridge.entry_lookback_minutes,
                run_config.bridge.exit_lookback_minutes,
            ),
            "requested_period_start_ts_ms": requested_period_start_ts_ms,
            "requested_period_end_ts_ms": requested_period_end_ts_ms,
            "period_start_ts_ms": first_ts_ms,
            "period_end_ts_ms": last_ts_ms,
        },
        "metrics": metrics,
        "thresholds_applied": thresholds,
        "gate_result": gate_result,
    }


def run_primary_breakout_backtest(
    candles: Sequence[Mapping[str, Any]],
    *,
    run_config: PrimaryBreakoutBacktestRunConfig | None = None,
    simulator_config: Mapping[str, Any] | None = None,
    code_commit: str = "unknown",
    gate_trace_path: Path | None = None,
) -> dict[str, Any]:
    """Run the deterministic historical backtest and return the schema report."""

    active_config = run_config or PrimaryBreakoutBacktestRunConfig()
    active_config.validate()
    if simulator_config is not None and not isinstance(simulator_config, Mapping):
        raise PrimaryBreakoutBacktestError("simulator_config must be a mapping")
    active_simulator_config = dict(simulator_config or {})
    execution_delay_bars = _extract_execution_delay_bars(active_simulator_config)
    bridge_requests = build_primary_breakout_historical_bridge(
        candles, config=active_config.bridge
    )
    # Extract raw candle boundaries after bridge validation succeeds (guarantees non-empty + valid).
    requested_period_start_ts_ms = int(candles[0]["ts_ms"])
    requested_period_end_ts_ms = int(candles[-1]["ts_ms"])
    simulator = ExecutionSimulator(active_simulator_config)

    output_requests: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    last_entry_ts_ms: int | None = None
    market_state_fresh_count = 0
    regime_fresh_count = 0
    pending_signals: list[dict[str, Any]] = []
    replay_signature: list[dict[str, Any]] = []

    trace_writer = None
    if gate_trace_path:
        try:
            trace_writer = open(gate_trace_path, "w", encoding="utf-8")
        except OSError as exc:
            raise PrimaryBreakoutBacktestError(
                f"Failed to open gate trace path {gate_trace_path}: {exc}"
            ) from exc

    try:
        for request_index, request in enumerate(bridge_requests):
            if execution_delay_bars > 0 and pending_signals:
                due_signals: list[dict[str, Any]] = []
                remaining_signals: list[dict[str, Any]] = []
                for pending in pending_signals:
                    if pending["target_idx"] == request_index:
                        due_signals.append(pending)
                    else:
                        remaining_signals.append(pending)
                pending_signals = remaining_signals
                for exec_info in due_signals:
                    open_position = _execute_pending_signal(
                        exec_info,
                        open_position,
                        trades,
                        simulator,
                        active_config,
                    )

            market_state = request.market_event["market_state"]
            market_state_fresh = bool(market_state.get("market_state_fresh"))
            regime_fresh = bool(market_state.get("regime_fresh"))
            market_state_fresh_count += int(market_state_fresh)
            regime_fresh_count += int(regime_fresh)

            gate_trace_callback = None
            if trace_writer:

                def gate_trace_callback(data: Mapping[str, Any]) -> None:
                    trace_writer.write(
                        json.dumps({**data, "request_index": request_index}) + "\n"
                    )

            response, last_entry_ts_ms = _evaluate_primary_breakout_request(
                request,
                position_open=open_position is not None,
                last_entry_ts_ms=last_entry_ts_ms,
                config=active_config,
                gate_trace_callback=gate_trace_callback,
            )
            replay_signature.append(_serialize_response(response))

            for signal in response.signals:
                signal_payload = {
                    "strategy_id": signal.strategy_id,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "reason": signal.reason,
                    "price": signal.price,
                    "metadata": dict(signal.metadata or {}),
                }
                output_requests.append(signal_payload)

                if execution_delay_bars > 0:
                    pending_signals.append(
                        _build_pending_execution(
                            signal,
                            request_index,
                            bridge_requests,
                            execution_delay_bars,
                        )
                    )
                    continue

                signal_price = _first_number(
                    signal.price, request.market_snapshot.get("close")
                )
                if signal_price is None:
                    raise PrimaryBreakoutBacktestError("signal missing price")
                ts_ms = int(request.market_event["ts_ms"])
                volume = _first_number(request.market_snapshot.get("volume")) or 0.0
                volatility = abs(
                    (
                        signal_price
                        - _first_number(
                            request.market_snapshot.get("close"), signal_price
                        )
                    )
                    / signal_price
                )

                if signal.side == "BUY":
                    if open_position is not None:
                        continue
                    fill = _simulate_trade(
                        side="buy",
                        price=signal_price,
                        ts_ms=ts_ms,
                        volume=volume,
                        simulator=simulator,
                        order_size=active_config.order_size,
                        order_book_depth_multiplier=active_config.order_book_depth_multiplier,
                        volatility=volatility,
                    )
                    open_position = {
                        "entry_price": fill["avg_fill_price"],
                        "entry_ts_ms": ts_ms,
                        "entry_fee": fill["fees"],
                    }
                elif signal.side == "SELL" and open_position is not None:
                    fill = _simulate_trade(
                        side="sell",
                        price=signal_price,
                        ts_ms=ts_ms,
                        volume=volume,
                        simulator=simulator,
                        order_size=active_config.order_size,
                        order_book_depth_multiplier=active_config.order_book_depth_multiplier,
                        volatility=volatility,
                    )
                    entry_price = float(open_position["entry_price"])
                    exit_price = float(fill["avg_fill_price"])
                    trade_r = (exit_price - entry_price) / entry_price
                    trades.append(
                        {
                            "entry_ts_ms": int(open_position["entry_ts_ms"]),
                            "exit_ts_ms": ts_ms,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "entry_fee": float(open_position["entry_fee"]),
                            "exit_fee": float(fill["fees"]),
                            "r_return": trade_r,
                        }
                    )
                    open_position = None
    finally:
        if trace_writer:
            trace_writer.close()

    replay_check_signature: list[dict[str, Any]] = []
    replay_position_open = False
    replay_last_entry_ts_ms: int | None = None
    replay_pending_signals: list[dict[str, Any]] = []
    for request_index, request in enumerate(bridge_requests):
        if execution_delay_bars > 0 and replay_pending_signals:
            due_signals: list[dict[str, Any]] = []
            remaining_signals: list[dict[str, Any]] = []
            for pending in replay_pending_signals:
                if pending["target_idx"] == request_index:
                    due_signals.append(pending)
                else:
                    remaining_signals.append(pending)
            replay_pending_signals = remaining_signals
            for pending in due_signals:
                if pending["side"] == "BUY":
                    if not replay_position_open:
                        replay_position_open = True
                elif pending["side"] == "SELL" and replay_position_open:
                    replay_position_open = False

        response, replay_last_entry_ts_ms = _evaluate_primary_breakout_request(
            request,
            position_open=replay_position_open,
            last_entry_ts_ms=replay_last_entry_ts_ms,
            config=active_config,
            gate_trace_callback=None,  # Do not trace in second pass
        )
        replay_check_signature.append(_serialize_response(response))
        for signal in response.signals:
            if execution_delay_bars > 0:
                replay_pending_signals.append(
                    _build_pending_execution(
                        signal,
                        request_index,
                        bridge_requests,
                        execution_delay_bars,
                    )
                )
                continue
            if signal.side == "BUY":
                replay_position_open = True
            elif signal.side == "SELL":
                replay_position_open = False
    deterministic_replay_ok = replay_signature == replay_check_signature

    data_integrity_diagnostics = _build_data_integrity_diagnostics(
        open_position,
        pending_signals,
    )
    data_integrity_ok = (
        len(bridge_requests) > 0 and open_position is None and not pending_signals
    )
    return _build_report(
        bridge_requests=bridge_requests,
        run_config=active_config,
        code_commit=code_commit,
        simulator_config=active_simulator_config,
        output_requests=output_requests,
        trades=trades,
        market_state_fresh_ratio=(
            market_state_fresh_count / len(bridge_requests) if bridge_requests else 0.0
        ),
        regime_fresh_ratio=(
            regime_fresh_count / len(bridge_requests) if bridge_requests else 0.0
        ),
        data_integrity_ok=data_integrity_ok,
        data_integrity_diagnostics=data_integrity_diagnostics,
        deterministic_replay_ok=deterministic_replay_ok,
        requested_period_start_ts_ms=requested_period_start_ts_ms,
        requested_period_end_ts_ms=requested_period_end_ts_ms,
    )
