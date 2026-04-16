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
from typing import Any, Mapping, Sequence

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
            raise PrimaryBreakoutBacktestError("order_book_depth_multiplier must be > 0")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _deterministic_run_id(
    requests: Sequence[StrategyAdapterRequest],
    config: PrimaryBreakoutBacktestRunConfig,
    code_commit: str,
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


def _evaluate_gate(metrics: Mapping[str, Any], thresholds: Mapping[str, Any]) -> dict[str, Any]:
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
    if float(metrics["market_state_fresh_ratio"]) < pass_fail["min_market_state_fresh_ratio"]:
        failed_criteria.append("min_market_state_fresh_ratio")
    if float(metrics["regime_fresh_ratio"]) < pass_fail["min_regime_fresh_ratio"]:
        failed_criteria.append("min_regime_fresh_ratio")
    if bool(metrics["data_integrity_ok"]) is not pass_fail["require_data_integrity_ok"]:
        failed_criteria.append("data_integrity_ok")
    if bool(metrics["deterministic_replay_ok"]) is not pass_fail["require_deterministic_replay_ok"]:
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
        notes = "failed criteria" if failed_criteria else "review-only thresholds flagged"

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
    output_requests: Sequence[dict[str, Any]],
    trades: Sequence[dict[str, Any]],
    market_state_fresh_ratio: float,
    regime_fresh_ratio: float,
    data_integrity_ok: bool,
    deterministic_replay_ok: bool,
    requested_period_start_ts_ms: int,
    requested_period_end_ts_ms: int,
) -> dict[str, Any]:
    if not bridge_requests:
        raise PrimaryBreakoutBacktestError("bridge produced no requests")

    run_id = _deterministic_run_id(bridge_requests, run_config, code_commit)
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

    signals_total = len(output_requests)
    buy_signals_total = sum(1 for signal in output_requests if signal["side"] == "BUY")
    sell_signals_total = sum(1 for signal in output_requests if signal["side"] == "SELL")
    metrics = {
        "signals_total": signals_total,
        "buy_signals_total": buy_signals_total,
        "sell_signals_total": sell_signals_total,
        "closed_trades_total": len(trades),
        "win_rate": (len(wins) / len(trade_returns)) if trade_returns else 0.0,
        "profit_factor": profit_factor,
        "expectancy_r": expectancy_r,
        "max_drawdown_r": max_drawdown_r,
        "market_state_fresh_ratio": market_state_fresh_ratio,
        "regime_fresh_ratio": regime_fresh_ratio,
        "data_integrity_ok": data_integrity_ok,
        "deterministic_replay_ok": deterministic_replay_ok,
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
            "candles_total": len(bridge_requests) + max(
                run_config.bridge.entry_lookback_minutes, run_config.bridge.exit_lookback_minutes
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
    code_commit: str = "unknown",
) -> dict[str, Any]:
    """Run the deterministic historical backtest and return the schema report."""

    active_config = run_config or PrimaryBreakoutBacktestRunConfig()
    active_config.validate()
    bridge_requests = build_primary_breakout_historical_bridge(
        candles, config=active_config.bridge
    )
    # Extract raw candle boundaries after bridge validation succeeds (guarantees non-empty + valid).
    requested_period_start_ts_ms = int(candles[0]["ts_ms"])
    requested_period_end_ts_ms = int(candles[-1]["ts_ms"])
    simulator = ExecutionSimulator()

    output_requests: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    open_position: dict[str, Any] | None = None
    last_entry_ts_ms: int | None = None
    market_state_fresh_count = 0
    regime_fresh_count = 0
    replay_signature: list[dict[str, Any]] = []

    for request in bridge_requests:
        market_state = request.market_event["market_state"]
        market_state_fresh = bool(market_state.get("market_state_fresh"))
        regime_fresh = bool(market_state.get("regime_fresh"))
        market_state_fresh_count += int(market_state_fresh)
        regime_fresh_count += int(regime_fresh)

        response, last_entry_ts_ms = _evaluate_primary_breakout_request(
            request,
            position_open=open_position is not None,
            last_entry_ts_ms=last_entry_ts_ms,
            config=active_config,
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

            signal_price = _first_number(signal.price, request.market_snapshot.get("close"))
            if signal_price is None:
                raise PrimaryBreakoutBacktestError("signal missing price")
            ts_ms = int(request.market_event["ts_ms"])
            volume = _first_number(request.market_snapshot.get("volume")) or 0.0
            volatility = abs(
                (
                    signal_price
                    - _first_number(request.market_snapshot.get("close"), signal_price)
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

    replay_check_signature: list[dict[str, Any]] = []
    replay_position_open = False
    replay_last_entry_ts_ms: int | None = None
    for request in bridge_requests:
        response, replay_last_entry_ts_ms = _evaluate_primary_breakout_request(
            request,
            position_open=replay_position_open,
            last_entry_ts_ms=replay_last_entry_ts_ms,
            config=active_config,
        )
        replay_check_signature.append(_serialize_response(response))
        for signal in response.signals:
            if signal.side == "BUY":
                replay_position_open = True
            elif signal.side == "SELL":
                replay_position_open = False
    deterministic_replay_ok = replay_signature == replay_check_signature

    data_integrity_ok = len(bridge_requests) > 0 and open_position is None
    return _build_report(
        bridge_requests=bridge_requests,
        run_config=active_config,
        code_commit=code_commit,
        output_requests=output_requests,
        trades=trades,
        market_state_fresh_ratio=(
            market_state_fresh_count / len(bridge_requests) if bridge_requests else 0.0
        ),
        regime_fresh_ratio=(regime_fresh_count / len(bridge_requests) if bridge_requests else 0.0),
        data_integrity_ok=data_integrity_ok,
        deterministic_replay_ok=deterministic_replay_ok,
        requested_period_start_ts_ms=requested_period_start_ts_ms,
        requested_period_end_ts_ms=requested_period_end_ts_ms,
    )
