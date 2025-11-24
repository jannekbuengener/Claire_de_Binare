"""
Exception Path Tests für Risk Engine (100% Coverage).

Diese Tests verwenden Mocking/Patching um gezielt Exception-Handler zu triggern:
- Lines 307-311: Sizing method ValueError/KeyError fallback
- Line 315: Zero position size rejection
- Lines 367-369: Perpetuals validation Exception
- Lines 407-413: Partial fill branch
- Lines 415-420: Execution simulation Exception

100% Coverage Sprint - Exception Paths
"""

import pytest
from unittest.mock import patch, MagicMock
from services.risk_engine import evaluate_signal_v2, EnhancedRiskDecision
from services.execution_simulator import ExecutionResult


@pytest.fixture
def minimal_config():
    """Minimale Config für Exception-Tests."""
    return {
        "ACCOUNT_EQUITY": 100000.0,
        "MAX_POSITION_PCT": 0.10,
        "MAX_DRAWDOWN_PCT": 0.05,
        "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.10,
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "SIZING_METHOD": "fixed_fractional",
    }


@pytest.fixture
def minimal_market_conditions():
    """Minimale Market Conditions."""
    return {
        "volatility": 0.60,
        "atr": 2500.0,
        "order_book_depth": 1000000.0,
    }


@pytest.fixture
def clean_state():
    """Clean Risk State."""
    return {
        "equity": 100000.0,
        "daily_pnl": 0.0,
        "total_exposure_pct": 0.0,
    }


# =============================================================================
# Lines 307-311: Sizing Method Exception Fallback
# =============================================================================


@pytest.mark.unit
def test_sizing_method_valueerror_triggers_fallback(
    minimal_config, minimal_market_conditions, clean_state
):
    """
    Coverage: risk_engine.py Lines 307-311 (ValueError in sizing).

    Gegeben: select_sizing_method wirft ValueError
    Wenn: Signal wird evaluiert
    Dann: Fallback zu limit_position_size wird verwendet
    """
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }

    # Mock select_sizing_method to raise ValueError
    with patch("services.position_sizing.select_sizing_method") as mock_sizing:
        mock_sizing.side_effect = ValueError("Invalid sizing configuration")

        # Act
        decision = evaluate_signal_v2(
            signal, clean_state, minimal_config, minimal_market_conditions
        )

        # Assert - Should use fallback sizing and NOT crash
        assert isinstance(decision, EnhancedRiskDecision)
        mock_sizing.assert_called_once()


@pytest.mark.unit
def test_sizing_method_keyerror_triggers_fallback(
    minimal_config, minimal_market_conditions, clean_state
):
    """
    Coverage: risk_engine.py Lines 307-311 (KeyError in sizing).

    Gegeben: select_sizing_method wirft KeyError
    Wenn: Signal wird evaluiert
    Dann: Fallback zu limit_position_size wird verwendet
    """
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }

    # Mock select_sizing_method to raise KeyError
    with patch("services.position_sizing.select_sizing_method") as mock_sizing:
        mock_sizing.side_effect = KeyError("Missing config key")

        # Act
        decision = evaluate_signal_v2(
            signal, clean_state, minimal_config, minimal_market_conditions
        )

        # Assert
        assert isinstance(decision, EnhancedRiskDecision)
        mock_sizing.assert_called_once()


# =============================================================================
# Line 315: Zero Position Size Rejection
# =============================================================================


@pytest.mark.unit
def test_zero_position_size_triggers_rejection(
    minimal_config, minimal_market_conditions, clean_state
):
    """
    Coverage: risk_engine.py Line 315 (position_size_zero check).

    Gegeben: Sizing liefert size_usd = 0.0
    Wenn: Signal wird evaluiert
    Dann: position_size_zero_after_sizing rejection
    """
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }

    # Mock select_sizing_method to return zero size
    mock_sizing_result = MagicMock()
    mock_sizing_result.size_usd = 0.0
    mock_sizing_result.method = "mocked"

    with patch("services.position_sizing.select_sizing_method") as mock_sizing:
        mock_sizing.return_value = mock_sizing_result

        # Act
        decision = evaluate_signal_v2(
            signal, clean_state, minimal_config, minimal_market_conditions
        )

        # Assert
        assert decision.approved is False
        assert "position_size_zero" in decision.reason.lower()
        assert decision.position_size == 0.0


# =============================================================================
# Lines 367-369: Perpetuals Validation Exception
# =============================================================================


@pytest.mark.unit
def test_perpetuals_exception_triggers_rejection(
    minimal_config, minimal_market_conditions, clean_state
):
    """
    Coverage: risk_engine.py Lines 367-369 (perpetuals Exception).

    Gegeben: create_position_from_signal wirft Exception
    Wenn: Signal wird evaluiert
    Dann: perpetuals_validation_error rejection
    """
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }

    # Mock create_position_from_signal to raise Exception
    with patch("services.mexc_perpetuals.create_position_from_signal") as mock_perp:
        mock_perp.side_effect = Exception("Perpetuals calculation error")

        # Act
        decision = evaluate_signal_v2(
            signal, clean_state, minimal_config, minimal_market_conditions
        )

        # Assert
        assert decision.approved is False
        assert "perpetuals_validation_error" in decision.reason
        assert decision.position_size == 0.0


# =============================================================================
# Lines 407-413: Partial Fill Branch
# =============================================================================


@pytest.mark.unit
def test_partial_fill_branch_recalculates_position(
    minimal_config, minimal_market_conditions, clean_state
):
    """
    Coverage: risk_engine.py Lines 407-413 (partial fill branch).

    Gegeben: ExecutionSimulator liefert partial_fill=True
    Wenn: Signal wird evaluiert
    Dann: Position wird mit partial size neu berechnet
    """
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }

    # Mock ExecutionSimulator to return partial fill
    mock_execution = ExecutionResult(
        filled_size=0.05,  # Partial fill (half of expected)
        avg_fill_price=50050.0,
        fees=10.0,
        slippage_bps=10.0,
        partial_fill=True,  # THIS triggers lines 407-413
        fill_ratio=0.5,  # Required parameter
    )

    # Also mock create_position_from_signal to ensure it can be called twice
    mock_position = MagicMock()
    mock_position.calculate_liquidation_price.return_value = 48000.0
    mock_position.calculate_liquidation_distance.return_value = 0.20
    mock_position.leverage = 10

    with patch("services.execution_simulator.ExecutionSimulator") as mock_sim_class, \
         patch("services.mexc_perpetuals.create_position_from_signal") as mock_create_pos, \
         patch("services.mexc_perpetuals.validate_liquidation_distance") as mock_validate_liq:

        # Setup mocks
        mock_sim = MagicMock()
        mock_sim.simulate_market_order.return_value = mock_execution
        mock_sim_class.return_value = mock_sim

        mock_create_pos.return_value = mock_position
        mock_validate_liq.return_value = {"approved": True, "distance": 0.20, "reason": None}

        # Act
        decision = evaluate_signal_v2(
            signal, clean_state, minimal_config, minimal_market_conditions
        )

        # Assert - Partial fill branch should be executed
        assert isinstance(decision, EnhancedRiskDecision)
        # create_position_from_signal should be called twice (once initially, once for partial fill)
        assert mock_create_pos.call_count >= 2, "create_position should be called for partial fill recalculation"


# =============================================================================
# Lines 415-420: Execution Simulation Exception Fallback
# =============================================================================


@pytest.mark.unit
def test_execution_exception_uses_fallback_values(
    minimal_config, minimal_market_conditions, clean_state
):
    """
    Coverage: risk_engine.py Lines 415-420 (execution Exception fallback).

    Gegeben: ExecutionSimulator wirft Exception
    Wenn: Signal wird evaluiert
    Dann: Original sizing values werden verwendet (fallback)
    """
    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
    }

    # Mock perpetuals to pass, so we reach execution simulation
    mock_position = MagicMock()
    mock_position.calculate_liquidation_price.return_value = 48000.0
    mock_position.calculate_liquidation_distance.return_value = 0.20
    mock_position.calculate_funding_fee.return_value = 5.0
    mock_position.leverage = 10

    # Mock ExecutionSimulator to raise Exception
    with patch("services.execution_simulator.ExecutionSimulator") as mock_sim_class, \
         patch("services.mexc_perpetuals.create_position_from_signal") as mock_create_pos, \
         patch("services.mexc_perpetuals.validate_liquidation_distance") as mock_validate_liq:

        # Setup perpetuals mocks to pass all checks
        mock_create_pos.return_value = mock_position
        mock_validate_liq.return_value = {"approved": True, "distance": 0.20, "reason": None}

        # Setup ExecutionSimulator to raise Exception
        mock_sim = MagicMock()
        mock_sim.simulate_market_order.side_effect = Exception("Execution error")
        mock_sim_class.return_value = mock_sim

        # Act
        decision = evaluate_signal_v2(
            signal, clean_state, minimal_config, minimal_market_conditions
        )

        # Assert - Should use fallback values (exception handler triggered)
        assert isinstance(decision, EnhancedRiskDecision)
        if decision.approved:
            # execution_fees should be 0.0 (fallback value from exception handler)
            assert decision.execution_fees == 0.0
            # Should still have liquidation info from perpetuals check
            assert decision.liquidation_price is not None
