"""Unit tests for the risk engine scaffolding."""

from __future__ import annotations

import pytest

from services import risk_engine


@pytest.mark.unit
def test_daily_drawdown_blocks_orders(
    risk_config, sample_risk_state, sample_signal_event
):
    """Orders are rejected once the daily drawdown limit is breached."""

    state = {**sample_risk_state, "daily_pnl": -6_000}

    decision = risk_engine.evaluate_signal(sample_signal_event, state, risk_config)

    assert decision.approved is False
    assert decision.reason == "max_daily_drawdown_exceeded"
    assert decision.position_size == 0.0


@pytest.mark.unit
def test_position_size_respects_max_pct(risk_config, sample_signal_event):
    """Position sizing is capped by ``MAX_POSITION_PCT`` of equity."""

    size = risk_engine.limit_position_size(sample_signal_event, risk_config)

    assert size == pytest.approx(0.2)


@pytest.mark.unit
def test_stop_loss_generation_for_long_signal(risk_config, sample_signal_event):
    """Stop-loss level is placed below the entry for long signals."""

    stop_data = risk_engine.generate_stop_loss(sample_signal_event, risk_config)

    assert stop_data["side"] == "buy"
    assert stop_data["stop_price"] == pytest.approx(49_000.0)
