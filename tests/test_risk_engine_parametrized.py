"""Parametrized Tests für Risk Engine - Phase 2 Test Improvements.

Diese Tests nutzen pytest.mark.parametrize um mehrere Szenarien
mit einem Test abzudecken. Verbessert Test-Qualität und reduziert
Code-Duplikation.
"""

from __future__ import annotations

import pytest

from services import risk_engine


# =============================================================================
# Parametrized Tests für Daily Drawdown Scenarios
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "daily_pnl,expected_approved,description",
    [
        (-6000.0, False, "Über Limit (-6%)"),
        (-5000.0, False, "Exakt am Limit (-5%)"),
        (-4999.9, True, "Knapp unter Limit"),
        (-1000.0, True, "Kleiner Verlust (-1%)"),
        (0.0, True, "Neutral (0%)"),
        (1000.0, True, "Gewinn (+1%)"),
        (5000.0, True, "Großer Gewinn (+5%)"),
    ],
)
def test_daily_drawdown_scenarios(
    risk_config, sample_signal_event, daily_pnl, expected_approved, description
):
    """Daily Drawdown mit verschiedenen PnL-Werten.

    Testet die Grenzwerte des MAX_DRAWDOWN_PCT (5% = -5000 bei 100k equity).
    """
    # Arrange
    state = {
        "equity": 100_000.0,
        "daily_pnl": daily_pnl,
        "total_exposure_pct": 0.1,
    }

    # Act
    decision = risk_engine.evaluate_signal(sample_signal_event, state, risk_config)

    # Assert
    assert (
        decision.approved is expected_approved
    ), f"Failed for scenario: {description} (PnL={daily_pnl})"

    if not expected_approved:
        assert decision.reason == "max_daily_drawdown_exceeded"
        assert decision.position_size == 0.0


# =============================================================================
# Parametrized Tests für Exposure Limits
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "current_exposure,expected_approved,description",
    [
        (0.05, True, "Niedriges Exposure + normales Signal (5% + 10% = 15%)"),
        (0.19, True, "Mittleres Exposure unter Limit (19% + 10% = 29% < 30%)"),
        (0.20, False, "Mittleres Exposure am Limit (20% + 10% = 30%)"),
        (0.21, False, "Mittleres Exposure würde Limit überschreiten (21% + 10% > 30%)"),
        (0.25, False, "Hohes Exposure + Signal = über Limit (25% + 10% > 30%)"),
        (0.30, False, "Bereits am Limit (30% + 10% > 30%)"),
        (0.35, False, "Über Limit (35% + 10% > 30%)"),
    ],
)
def test_exposure_limit_scenarios(
    risk_config, sample_signal_event, current_exposure, expected_approved, description
):
    """Exposure Limit mit verschiedenen Portfolio-Zuständen.

    MAX_EXPOSURE_PCT = 30% (0.30)
    Signal fügt ~10% hinzu (10k position bei 100k equity, price=50k, size wird auf 0.2 limitiert)
    """
    # Arrange
    state = {
        "equity": 100_000.0,
        "daily_pnl": 0.0,
        "total_exposure_pct": current_exposure,
    }

    # Act
    decision = risk_engine.evaluate_signal(sample_signal_event, state, risk_config)

    # Assert
    assert decision.approved is expected_approved, (
        f"Failed for scenario: {description} " f"(current_exposure={current_exposure})"
    )

    if not expected_approved:
        assert decision.reason == "max_exposure_reached"


# =============================================================================
# Parametrized Tests für Position Sizing
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "price,requested_size,max_pct,equity,expected_size,description",
    [
        # Normal cases
        (50_000.0, 1.0, 0.10, 100_000.0, 0.2, "Normal: 10% of 100k equity"),
        (100_000.0, 1.0, 0.10, 100_000.0, 0.1, "High price: Position limited"),
        (10_000.0, 10.0, 0.10, 100_000.0, 1.0, "Low price: Requested < Max"),
        # Edge cases
        (50_000.0, 1.0, 0.0, 100_000.0, 0.0, "Zero max_pct"),
        (0.0, 1.0, 0.10, 100_000.0, 0.0, "Zero price"),
        (50_000.0, 0.0, 0.10, 100_000.0, 0.0, "Zero requested"),
        # Different equity levels
        (50_000.0, 1.0, 0.10, 10_000.0, 0.02, "Small equity"),
        (
            50_000.0,
            5.0,
            0.10,
            1_000_000.0,
            2.0,
            "Large equity (requested 5, allowed 2)",
        ),
        # Different max_pct values
        (50_000.0, 1.0, 0.05, 100_000.0, 0.1, "Conservative 5%"),
        (50_000.0, 1.0, 0.20, 100_000.0, 0.4, "Aggressive 20%"),
    ],
)
def test_position_sizing_scenarios(
    price, requested_size, max_pct, equity, expected_size, description
):
    """Position Sizing mit verschiedenen Parametern."""
    # Arrange
    signal = {"price": price, "size": requested_size}
    config = {"ACCOUNT_EQUITY": equity, "MAX_POSITION_PCT": max_pct}

    # Act
    result_size = risk_engine.limit_position_size(signal, config, equity=equity)

    # Assert
    assert result_size == pytest.approx(
        expected_size, abs=1e-6
    ), f"Failed for scenario: {description}"


# =============================================================================
# Parametrized Tests für Stop-Loss Generation
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "side,price,stop_pct,expected_stop,description",
    [
        # Long positions (stop below entry)
        ("buy", 50_000.0, 0.02, 49_000.0, "Long: 2% stop below"),
        ("buy", 50_000.0, 0.05, 47_500.0, "Long: 5% stop below"),
        ("buy", 50_000.0, 0.01, 49_500.0, "Long: 1% tight stop"),
        ("buy", 100_000.0, 0.02, 98_000.0, "Long: High price asset"),
        # Short positions (stop above entry)
        ("sell", 50_000.0, 0.02, 51_000.0, "Short: 2% stop above"),
        ("sell", 50_000.0, 0.05, 52_500.0, "Short: 5% stop above"),
        ("sell", 50_000.0, 0.01, 50_500.0, "Short: 1% tight stop"),
        ("sell", 100_000.0, 0.02, 102_000.0, "Short: High price asset"),
        # Edge cases
        ("buy", 0.0, 0.02, 0.0, "Zero price"),
        ("sell", 0.0, 0.02, 0.0, "Zero price (short)"),
    ],
)
def test_stop_loss_scenarios(side, price, stop_pct, expected_stop, description):
    """Stop-Loss Generation mit verschiedenen Sides und Prozentsätzen."""
    # Arrange
    signal = {"symbol": "BTCUSDT", "side": side, "price": price}
    config = {"STOP_LOSS_PCT": stop_pct}

    # Act
    stop_data = risk_engine.generate_stop_loss(signal, config)

    # Assert
    assert stop_data["stop_price"] == pytest.approx(
        expected_stop, abs=1e-6
    ), f"Failed for scenario: {description}"
    assert stop_data["side"] == side


# =============================================================================
# Boundary Value Tests (Grenzwerte)
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "equity,daily_pnl_pct,expected_approved",
    [
        (100_000.0, -0.0499, True),  # 4.99% loss - just below limit
        (100_000.0, -0.0500, False),  # 5.00% loss - at limit
        (100_000.0, -0.0501, False),  # 5.01% loss - just above limit
        (50_000.0, -0.0499, True),  # Different equity, same %
        (200_000.0, -0.0500, False),  # Different equity, at limit
    ],
)
def test_drawdown_boundary_values(
    risk_config, sample_signal_event, equity, daily_pnl_pct, expected_approved
):
    """Boundary Value Testing für Daily Drawdown Grenzwerte."""
    # Arrange
    daily_pnl = equity * daily_pnl_pct
    state = {
        "equity": equity,
        "daily_pnl": daily_pnl,
        "total_exposure_pct": 0.1,
    }

    # Act
    decision = risk_engine.evaluate_signal(sample_signal_event, state, risk_config)

    # Assert
    assert decision.approved is expected_approved
