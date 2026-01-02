"""Edge-Case Tests für Risk Engine - Phase 1 Coverage Improvements.

Diese Tests decken die kritischen Lücken ab:
- evaluate_signal: Exposure Limit & Approval Path (36% -> 80%+)
- _calculate_signal_notional: Vollständige Coverage (0% -> 100%)
- limit_position_size: Edge Cases (80% -> 100%)
- generate_stop_loss: Short-Signals & Invalid Price (78% -> 100%)

Ziel: Gesamt-Coverage von 66% auf 75-80% erhöhen.
"""

from __future__ import annotations

import pytest

from services import risk_engine


# =============================================================================
# evaluate_signal() - Kritische Lücken (Lines 138-153)
# =============================================================================


@pytest.mark.unit
def test_evaluate_signal_exposure_limit_exceeded(risk_config, sample_signal_event):
    """Signal wird blockiert wenn total_exposure_pct > MAX_EXPOSURE_PCT."""

    # Arrange: Portfolio hat bereits 28% Exposure
    state = {
        "equity": 100_000.0,
        "daily_pnl": 0.0,
        "total_exposure_pct": 0.28,  # Schon 28% exposure
    }
    # Signal würde ~10% hinzufügen (10k bei 100k equity) → 38% > 30% limit

    # Act
    decision = risk_engine.evaluate_signal(sample_signal_event, state, risk_config)

    # Assert
    assert decision.approved is False
    assert decision.reason == "max_exposure_reached"
    assert decision.position_size == 0.0


@pytest.mark.unit
def test_evaluate_signal_approves_valid_signal(
    risk_config, sample_signal_event, sample_risk_state
):
    """Valides Signal wird mit korrekter Position-Size approved."""

    # Arrange: Gesunder Portfolio-Zustand
    state = {
        **sample_risk_state,
        "daily_pnl": 1000.0,  # Positiver PnL
        "total_exposure_pct": 0.05,  # Niedriges Exposure
    }

    # Act
    decision = risk_engine.evaluate_signal(sample_signal_event, state, risk_config)

    # Assert
    assert decision.approved is True
    assert decision.reason is None
    assert decision.position_size > 0
    assert decision.stop_price is not None
    assert decision.stop_price == pytest.approx(49_000.0)  # 2% unter Entry


# =============================================================================
# _calculate_signal_notional() - Vollständige Coverage (Lines 80-84)
# =============================================================================


@pytest.mark.unit
def test_calculate_signal_notional_from_price():
    """Notional wird aus price * size berechnet wenn notional fehlt."""

    # Arrange
    signal = {"price": 50_000.0, "size": 0.5}

    # Act
    notional = risk_engine._calculate_signal_notional(signal, 0.5)

    # Assert
    assert notional == pytest.approx(25_000.0)


@pytest.mark.unit
def test_calculate_signal_notional_uses_provided_value():
    """Vorhandener notional-Wert wird bevorzugt."""

    # Arrange
    signal = {"price": 50_000.0, "size": 1.0, "notional": 60_000.0}

    # Act
    notional = risk_engine._calculate_signal_notional(signal, 1.0)

    # Assert: Expliziter notional-Wert wird verwendet, nicht price * size
    assert notional == 60_000.0


# =============================================================================
# limit_position_size() - Edge Cases (Lines 67, 71)
# =============================================================================


@pytest.mark.unit
def test_limit_position_size_invalid_price(risk_config, sample_signal_event):
    """Position-Size ist 0 bei ungültigem Preis."""

    # Arrange
    signal = {**sample_signal_event, "price": 0.0}

    # Act
    size = risk_engine.limit_position_size(signal, risk_config)

    # Assert
    assert size == 0.0


@pytest.mark.unit
def test_limit_position_size_zero_max_position_pct(risk_config, sample_signal_event):
    """Position-Size ist 0 wenn MAX_POSITION_PCT = 0."""

    # Arrange
    config = {**risk_config, "MAX_POSITION_PCT": 0.0}

    # Act
    size = risk_engine.limit_position_size(sample_signal_event, config)

    # Assert
    assert size == 0.0


# =============================================================================
# generate_stop_loss() - Short-Signals & Invalid Price (Lines 105, 108)
# =============================================================================


@pytest.mark.unit
def test_stop_loss_generation_for_short_signal(risk_config):
    """Stop-loss wird oberhalb Entry für Short-Signale platziert."""

    # Arrange
    signal = {"symbol": "BTCUSDT", "side": "sell", "price": 50_000.0}

    # Act
    stop_data = risk_engine.generate_stop_loss(signal, risk_config)

    # Assert: Stop bei Short-Positions oberhalb Entry (2% höher)
    assert stop_data["side"] == "sell"
    assert stop_data["stop_price"] == pytest.approx(51_000.0)  # +2%


@pytest.mark.unit
def test_stop_loss_invalid_price(risk_config):
    """Stop-loss ist 0 bei ungültigem Preis."""

    # Arrange
    signal = {"symbol": "BTCUSDT", "side": "buy", "price": 0.0}

    # Act
    stop_data = risk_engine.generate_stop_loss(signal, risk_config)

    # Assert
    assert stop_data["stop_price"] == 0.0
    assert stop_data["side"] == "buy"
