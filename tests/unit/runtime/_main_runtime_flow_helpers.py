"""Shared helpers for main runtime flow contract tests (#3838)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.execution.models import ExecutionResult, OrderStatus
from services.risk import service as risk_service


def base_flow_inputs() -> tuple[
    int, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    """Mirror tests.contract.test_decision_contract._base_inputs for flow reuse."""
    now_ms = 1_700_000_000_000
    signal = {
        "signal_id": "sig-flow-0001",
        "symbol": "BTCUSDT",
        "pct_change_15m": 3.5,
        "volume_15m": 200000.0,
        "ts_ms": now_ms - 1000,
        "side": "BUY",
        "strategy_id": "primary_breakout_v1",
    }
    market_state = {
        "regime_id": 0,
        "return_1m": -1.0,
        "return_5m": -1.0,
        "price_change_5m": 5.0,
        "last_tick_ts_ms": now_ms - 500,
        "ts_ms": now_ms - 900,
    }
    account_state = {
        "daily_drawdown_pct": 1.0,
        "total_exposure_pct": 10.0,
        "ts_ms": now_ms - 800,
    }
    market_health = {"slippage_pct": 0.5, "ts_ms": now_ms - 700}
    return now_ms, signal, market_state, account_state, market_health


@dataclass
class PaperExecutionOutcome:
    approved: bool
    reason_code: str | None
    execution: ExecutionResult | None


def evaluate_risk_gate(
    *,
    now_ms: int,
    signal: dict[str, Any],
    market_state: dict[str, Any],
    account_state: dict[str, Any],
    market_health: dict[str, Any],
) -> tuple[str, str | None]:
    decision, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    return decision, reason_code


def simulate_paper_execution(signal: dict[str, Any]) -> ExecutionResult:
    return ExecutionResult(
        order_id="paper_flow_001",
        symbol=signal["symbol"],
        side=str(signal.get("side", "BUY")),
        quantity=0.001,
        filled_quantity=0.001,
        status=OrderStatus.FILLED.value,
        price=50000.0,
        client_id="flow-client",
        fill_id="paper_flow_001",
        strategy_id=str(signal.get("strategy_id", "primary_breakout_v1")),
        bot_id="flow-bot",
        metadata={"signal_id": signal["signal_id"], "mode": "paper"},
    )
