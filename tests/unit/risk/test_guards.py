"""
Unit tests for runtime risk guard state.
"""

import pytest

from services.risk.models import RiskState


@pytest.mark.unit
def test_drawdown_updates_with_realized_loss():
    state = RiskState()
    state.initialize_equity(10000.0, "2025-01-01")
    state.update_equity()

    state.apply_fill("BTCUSDT", "BUY", 1.0, 100.0)
    assert state.equity == pytest.approx(10000.0)
    assert state.max_drawdown_pct == pytest.approx(0.0)

    state.apply_fill("BTCUSDT", "SELL", 1.0, 90.0)
    assert state.equity == pytest.approx(9990.0)
    assert state.current_drawdown_pct == pytest.approx(0.001)
    assert state.max_drawdown_pct == pytest.approx(0.001)

    state.apply_fill("BTCUSDT", "BUY", 1.0, 90.0)
    state.apply_fill("BTCUSDT", "SELL", 1.0, 110.0)
    assert state.equity == pytest.approx(10010.0)
    assert state.peak_equity == pytest.approx(10010.0)
    assert state.max_drawdown_pct == pytest.approx(0.001)


@pytest.mark.unit
def test_drawdown_handles_zero_equity():
    state = RiskState()
    state.update_equity()
    assert state.current_drawdown_pct == pytest.approx(1.0)
    assert state.max_drawdown_pct == pytest.approx(1.0)


@pytest.mark.unit
def test_circuit_breaker_triggers_and_latches():
    state = RiskState()
    now_ts = 1_700_000_000

    triggered = state.record_execution_failure(
        now_ts,
        reason="EXECUTION_ERROR",
        max_consecutive=2,
        max_failures=5,
        window_sec=3600,
    )
    assert triggered is False
    assert state.circuit_breaker_active is False

    triggered = state.record_execution_failure(
        now_ts + 1,
        reason="EXECUTION_ERROR",
        max_consecutive=2,
        max_failures=5,
        window_sec=3600,
    )
    assert triggered is True
    assert state.circuit_breaker_active is True
    assert state.circuit_breaker_reason == "EXECUTION_ERROR"

    state.record_execution_success()
    assert state.circuit_breaker_active is True


@pytest.mark.unit
def test_risk_state_persistence_roundtrip():
    state = RiskState()
    state.initialize_equity(10000.0, "2025-01-01")
    state.apply_fill("ETHUSDT", "BUY", 2.0, 200.0)
    state.apply_fill("ETHUSDT", "SELL", 2.0, 150.0)
    state.circuit_breaker_active = True
    state.circuit_breaker_reason = "DAILY_DRAWDOWN"
    state.circuit_breaker_triggered_at = 1700000000
    state.shutdown_strategy_ids = ["strat_a"]
    state.shutdown_bot_ids = ["bot_a"]

    snapshot = state.to_dict()
    restored = RiskState()
    restored.apply_snapshot(snapshot)

    assert restored.circuit_breaker_active is True
    assert restored.circuit_breaker_reason == "DAILY_DRAWDOWN"
    assert restored.circuit_breaker_triggered_at == 1700000000
    assert "ETHUSDT" not in restored.positions
    assert restored.shutdown_strategy_ids == ["strat_a"]
    assert restored.shutdown_bot_ids == ["bot_a"]
