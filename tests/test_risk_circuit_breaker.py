"""
Circuit-Breaker Tests für Risk Engine (Layer 5).

Diese Tests validieren den Emergency Stop Mechanismus:
- Circuit-Breaker aktiviert bei 10% Tagesverlust
- Alle Signals blockiert wenn Circuit-Breaker aktiv
- Härter als Daily Drawdown (10% vs 5%)

Sprint 2 - Risk-Engine Hardening
"""

import pytest
from services.risk_engine import evaluate_signal_v2, EnhancedRiskDecision


@pytest.fixture
def standard_risk_config():
    """Standard Risk-Config mit Circuit-Breaker."""
    return {
        "ACCOUNT_EQUITY": 100000.0,
        "MAX_POSITION_PCT": 0.10,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,  # 5% Daily Drawdown
        "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.10,  # 10% Circuit-Breaker (härter!)
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "SIZING_METHOD": "fixed_fractional",
    }


@pytest.fixture
def standard_market_conditions():
    """Standard Market Conditions."""
    return {
        "volatility": 0.60,
        "atr": 2500.0,
        "order_book_depth": 1000000.0,
    }


@pytest.fixture
def clean_signal():
    """Clean Trading Signal."""
    return {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",  # Required by MEXC Perpetuals module
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }


@pytest.mark.unit
def test_circuit_breaker_activates_at_10_percent_loss(
    clean_signal, standard_risk_config, standard_market_conditions
):
    """
    Layer 5: Circuit-Breaker aktiviert bei exakt 10% Tagesverlust.

    Gegeben: Daily PnL = -10,000 USD (10% bei 100k Equity)
    Wenn: Signal wird evaluiert
    Dann: Circuit-Breaker blockiert (approved=False)
    """
    # Arrange
    risk_state = {
        "equity": 100000.0,
        "daily_pnl": -10000.0,  # Exakt 10% Loss
        "total_exposure_pct": 0.0,
    }

    # Act
    decision = evaluate_signal_v2(
        clean_signal, risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert isinstance(decision, EnhancedRiskDecision)
    assert decision.approved is False, "Circuit-Breaker sollte bei 10% Loss aktivieren"
    assert decision.reason == "circuit_breaker_triggered"
    assert decision.position_size == 0.0


@pytest.mark.unit
def test_circuit_breaker_blocks_at_11_percent_loss(
    clean_signal, standard_risk_config, standard_market_conditions
):
    """
    Layer 5: Circuit-Breaker blockiert bei >10% Loss.

    Gegeben: Daily PnL = -11,000 USD (11% Loss)
    Wenn: Signal wird evaluiert
    Dann: Circuit-Breaker blockiert
    """
    # Arrange
    risk_state = {
        "equity": 100000.0,
        "daily_pnl": -11000.0,  # 11% Loss (über Threshold)
        "total_exposure_pct": 0.0,
    }

    # Act
    decision = evaluate_signal_v2(
        clean_signal, risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert decision.approved is False
    assert decision.reason == "circuit_breaker_triggered"


@pytest.mark.unit
def test_circuit_breaker_allows_at_9_percent_loss(
    clean_signal, standard_risk_config, standard_market_conditions
):
    """
    Layer 5: Circuit-Breaker erlaubt Trading bei <10% Loss.

    Gegeben: Daily PnL = -9,000 USD (9% Loss, unter Circuit-Breaker)
    Wenn: Signal wird evaluiert
    Dann: Signal passiert Circuit-Breaker Check (aber Daily Drawdown blockiert bei 5%)
    """
    # Arrange
    risk_state = {
        "equity": 100000.0,
        "daily_pnl": -9000.0,  # 9% Loss (unter Circuit-Breaker, aber über Daily Drawdown)
        "total_exposure_pct": 0.0,
    }

    # Act
    decision = evaluate_signal_v2(
        clean_signal, risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    # Circuit-Breaker sollte NICHT triggern
    # ABER: Daily Drawdown (5%) sollte triggern
    assert decision.approved is False
    assert decision.reason == "max_daily_drawdown_exceeded", (
        "Bei 9% Loss: Circuit-Breaker OK, aber Daily Drawdown (5%) blockiert"
    )


@pytest.mark.unit
def test_circuit_breaker_harder_than_daily_drawdown(
    clean_signal, standard_risk_config, standard_market_conditions
):
    """
    Layer 5 vs Layer 3: Circuit-Breaker ist härter als Daily Drawdown.

    Gegeben: 2 Szenarien (5% Loss vs 10% Loss)
    Wenn: Signals werden evaluiert
    Dann: 5% → Daily Drawdown blockiert, 10% → Circuit-Breaker blockiert
    """
    # Scenario 1: 5% Loss → Daily Drawdown
    state_5pct = {
        "equity": 100000.0,
        "daily_pnl": -5000.0,  # 5%
        "total_exposure_pct": 0.0,
    }

    decision_5pct = evaluate_signal_v2(
        clean_signal, state_5pct, standard_risk_config, standard_market_conditions
    )

    assert decision_5pct.approved is False
    assert decision_5pct.reason == "max_daily_drawdown_exceeded"

    # Scenario 2: 10% Loss → Circuit-Breaker
    state_10pct = {
        "equity": 100000.0,
        "daily_pnl": -10000.0,  # 10%
        "total_exposure_pct": 0.0,
    }

    decision_10pct = evaluate_signal_v2(
        clean_signal, state_10pct, standard_risk_config, standard_market_conditions
    )

    assert decision_10pct.approved is False
    assert decision_10pct.reason == "circuit_breaker_triggered"


@pytest.mark.unit
def test_circuit_breaker_with_positive_pnl(
    clean_signal, standard_risk_config, standard_market_conditions
):
    """
    Layer 5: Circuit-Breaker erlaubt Trading bei positivem PnL.

    Gegeben: Daily PnL = +5,000 USD (Profit)
    Wenn: Signal wird evaluiert
    Dann: Circuit-Breaker blockiert NICHT (andere Checks können noch blockieren)
    """
    # Arrange
    risk_state = {
        "equity": 100000.0,
        "daily_pnl": 5000.0,  # +5% Profit
        "total_exposure_pct": 0.0,
    }

    # Act
    decision = evaluate_signal_v2(
        clean_signal, risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    # Circuit-Breaker sollte NICHT die Ursache sein
    assert decision.reason != "circuit_breaker_triggered", (
        "Circuit-Breaker sollte bei Profit NICHT triggern"
    )
    # Hinweis: Signal kann trotzdem rejected werden durch andere Checks (Liquidation, Slippage, etc.)


@pytest.mark.unit
def test_circuit_breaker_respects_custom_threshold(
    clean_signal, standard_market_conditions
):
    """
    Layer 5: Circuit-Breaker respektiert custom Threshold aus Config.

    Gegeben: Custom CIRCUIT_BREAKER_THRESHOLD_PCT = 0.15 (15%)
    Wenn: Signal mit 12% Loss evaluiert wird
    Dann: Signal passiert (da 12% < 15%)
    """
    # Arrange
    custom_config = {
        "ACCOUNT_EQUITY": 100000.0,
        "MAX_POSITION_PCT": 0.10,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,
        "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.15,  # Custom: 15% statt 10%
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "SIZING_METHOD": "fixed_fractional",
    }

    risk_state = {
        "equity": 100000.0,
        "daily_pnl": -12000.0,  # 12% Loss (über 10%, aber unter 15%)
        "total_exposure_pct": 0.0,
    }

    # Act
    decision = evaluate_signal_v2(
        clean_signal, risk_state, custom_config, standard_market_conditions
    )

    # Assert
    # Circuit-Breaker (15%) sollte NICHT triggern
    # ABER: Daily Drawdown (5%) sollte triggern
    assert decision.approved is False
    assert decision.reason == "max_daily_drawdown_exceeded"


@pytest.mark.integration
def test_circuit_breaker_blocks_multiple_signals(
    standard_risk_config, standard_market_conditions
):
    """
    Integration: Circuit-Breaker blockiert ALLE Signals wenn aktiv.

    Gegeben: Circuit-Breaker ist triggered (10% Loss)
    Wenn: 3 verschiedene Signals evaluiert werden
    Dann: Alle 3 werden blockiert
    """
    # Arrange
    risk_state = {
        "equity": 100000.0,
        "daily_pnl": -10500.0,  # 10.5% Loss
        "total_exposure_pct": 0.0,
    }

    signals = [
        {"symbol": "BTCUSDT", "signal_type": "long", "side": "long", "price": 50000.0, "target_position_usd": 5000.0},
        {"symbol": "ETHUSDT", "signal_type": "short", "side": "short", "price": 3000.0, "target_position_usd": 3000.0},
        {"symbol": "SOLUSDT", "signal_type": "long", "side": "long", "price": 100.0, "target_position_usd": 1000.0},
    ]

    # Act & Assert
    for signal in signals:
        decision = evaluate_signal_v2(
            signal, risk_state, standard_risk_config, standard_market_conditions
        )

        assert decision.approved is False, f"Signal {signal['symbol']} sollte blockiert sein"
        assert decision.reason == "circuit_breaker_triggered"
        assert decision.position_size == 0.0
