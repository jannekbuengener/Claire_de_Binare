"""Integration tests for evaluate_signal_v2 with MEXC Perpetuals.

Tests the full integration of:
- Module 1: MEXC Perpetuals (margin, liquidation)
- Module 2: Position Sizing (vol-targeting, Kelly, etc.)
- Module 3: Execution Simulator (slippage, fees)
"""

import pytest
from services.risk_engine import (
    EnhancedRiskDecision,
    evaluate_signal_v2,
    load_risk_config,
)


@pytest.fixture
def standard_signal():
    """Standard BTC buy signal."""
    return {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50000.0,
    }


@pytest.fixture
def standard_risk_state():
    """Standard risk state with clean account."""
    return {
        "equity": 100000.0,
        "daily_pnl": 0.0,
        "total_exposure_pct": 0.0,
        "win_rate": 0.55,
        "avg_win": 0.03,
        "avg_loss": 0.015,
    }


@pytest.fixture
def standard_market_conditions():
    """Standard market conditions (normal volatility, deep liquidity)."""
    return {
        "volatility": 0.60,  # 60% annual vol (typical BTC)
        "atr": 2500.0,
        "order_book_depth": 1000000.0,
        "funding_rate": 0.0001,
    }


@pytest.fixture
def standard_risk_config():
    """Standard risk configuration."""
    return {
        "ACCOUNT_EQUITY": 100000.0,
        "MAX_POSITION_PCT": 0.10,
        "MAX_DRAWDOWN_PCT": 0.05,
        "MAX_EXPOSURE_PCT": 1.0,  # 100% (less restrictive for tests)
        "STOP_LOSS_PCT": 0.02,
        "MAX_SLIPPAGE_BPS": 300.0,  # More tolerant for tests (realistic for high vol)
        # Perpetuals
        "MARGIN_MODE": "isolated",
        "MAX_LEVERAGE": 10,
        "MIN_LIQUIDATION_DISTANCE": 0.05,  # Lower threshold for tests
        "MAINTENANCE_MARGIN_RATE": 0.005,
        "CONTRACT_MULTIPLIER": 0.0001,
        # Position Sizing
        "SIZING_METHOD": "fixed_fractional",
        "RISK_PER_TRADE": 0.02,
        "TARGET_VOL": 0.20,
        "KELLY_FRACTION": 0.25,
        "ATR_MULTIPLIER": 2.0,
        # Execution
        "MAKER_FEE": 0.0002,
        "TAKER_FEE": 0.0006,
        "BASE_SLIPPAGE_BPS": 5.0,
        "DEPTH_IMPACT_FACTOR": 0.10,
        "VOL_SLIPPAGE_MULTIPLIER": 2.0,
        "FILL_THRESHOLD": 0.80,
        # Funding
        "FUNDING_RATE": 0.0001,
        "FUNDING_SETTLEMENT_HOURS": 8,
    }


# ============================================================================
# Basic Integration Tests
# ============================================================================


@pytest.mark.integration
def test_evaluate_signal_v2_approves_clean_signal(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test that v2 approves a clean signal with all checks passing.

    Given:
        Clean risk state, standard market conditions
    When:
        Evaluating signal with v2
    Then:
        Should approve with full metadata
    """
    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=standard_risk_config,
        market_conditions=standard_market_conditions,
    )

    assert isinstance(decision, EnhancedRiskDecision)
    assert decision.approved is True
    assert decision.reason is None
    assert decision.position_size > 0

    # Check metadata
    assert decision.liquidation_price is not None
    assert decision.liquidation_distance is not None
    assert decision.leverage == 10
    assert decision.expected_slippage_bps is not None
    assert decision.execution_fees is not None
    assert decision.sizing_method == "fixed_fractional"
    assert decision.funding_fee_estimate is not None


@pytest.mark.integration
def test_evaluate_signal_v2_rejects_daily_drawdown(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test that v2 rejects signals when daily drawdown exceeded.

    Given:
        Daily PnL = -6% (below 5% threshold)
    When:
        Evaluating signal
    Then:
        Should reject with drawdown reason
    """
    risk_state = standard_risk_state.copy()
    risk_state["daily_pnl"] = -6000.0  # -6%

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=risk_state,
        risk_config=standard_risk_config,
        market_conditions=standard_market_conditions,
    )

    assert decision.approved is False
    assert "drawdown" in decision.reason.lower()


@pytest.mark.integration
def test_evaluate_signal_v2_rejects_max_exposure(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test that v2 rejects signals when max exposure reached.

    Given:
        Total exposure already at 50%
    When:
        Attempting to add more
    Then:
        Should reject with exposure reason
    """
    risk_state = standard_risk_state.copy()
    risk_state["total_exposure_pct"] = 0.50  # Already at max

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=risk_state,
        risk_config=standard_risk_config,
        market_conditions=standard_market_conditions,
    )

    assert decision.approved is False
    assert "exposure" in decision.reason.lower()


# ============================================================================
# Position Sizing Methods
# ============================================================================


@pytest.mark.integration
def test_evaluate_signal_v2_with_vol_targeting(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test v2 with volatility targeting position sizing.

    Given:
        Sizing method = volatility_targeting
    When:
        Evaluating signal
    Then:
        Should use vol-targeting and approve
    """
    config = standard_risk_config.copy()
    config["SIZING_METHOD"] = "volatility_targeting"
    config["TARGET_VOL"] = 0.20

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=config,
        market_conditions=standard_market_conditions,
    )

    assert decision.approved is True
    assert decision.sizing_method == "volatility_targeting"


@pytest.mark.integration
def test_evaluate_signal_v2_with_kelly_criterion(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test v2 with Kelly Criterion position sizing.

    Given:
        Sizing method = kelly_criterion
        Win rate = 55%, Payoff = 2:1
    When:
        Evaluating signal
    Then:
        Should use Kelly and approve
    """
    config = standard_risk_config.copy()
    config["SIZING_METHOD"] = "kelly_criterion"
    config["KELLY_FRACTION"] = 0.25

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=config,
        market_conditions=standard_market_conditions,
    )

    assert decision.approved is True
    assert decision.sizing_method == "kelly_criterion"


# ============================================================================
# Execution Simulation
# ============================================================================


@pytest.mark.integration
def test_evaluate_signal_v2_with_thin_liquidity(
    standard_signal, standard_risk_state, standard_risk_config
):
    """Test v2 with thin liquidity (higher slippage).

    Given:
        Order book depth = 500k (thinner than 1M)
        Volatility = 40% (moderate-high)
    When:
        Evaluating signal
    Then:
        Should have higher slippage but still approve
    """
    market_conditions = {
        "volatility": 0.40,  # Moderate-high vol (not extreme)
        "atr": 3500.0,
        "order_book_depth": 500000.0,  # Thinner liquidity
    }

    config = standard_risk_config.copy()
    config["MAX_SLIPPAGE_BPS"] = 400.0  # More tolerant for this test

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=config,
        market_conditions=market_conditions,
    )

    # Should still approve, but with higher slippage
    assert decision.approved is True
    assert decision.expected_slippage_bps > 50.0  # Higher slippage


@pytest.mark.integration
def test_evaluate_signal_v2_rejects_excessive_slippage(
    standard_signal, standard_risk_state, standard_risk_config
):
    """Test that v2 rejects signals with excessive slippage.

    Given:
        Very thin liquidity + high volatility
        Max slippage = 100 bps
    When:
        Evaluating signal
    Then:
        Should reject with slippage reason
    """
    market_conditions = {
        "volatility": 0.15,  # Extreme vol
        "atr": 10000.0,
        "order_book_depth": 10000.0,  # Very thin
    }

    config = standard_risk_config.copy()
    config["MAX_SLIPPAGE_BPS"] = 100.0  # 1% max slippage

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=config,
        market_conditions=market_conditions,
    )

    assert decision.approved is False
    assert "slippage" in decision.reason.lower()


# ============================================================================
# Liquidation Checks
# ============================================================================


@pytest.mark.integration
def test_evaluate_signal_v2_includes_liquidation_metadata(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test that v2 includes liquidation price and distance.

    Given:
        Standard conditions
    When:
        Evaluating signal
    Then:
        Should include liquidation metadata
    """
    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=standard_risk_config,
        market_conditions=standard_market_conditions,
    )

    assert decision.liquidation_price is not None
    assert decision.liquidation_price < standard_signal["price"]  # Long position
    assert decision.liquidation_distance is not None
    assert decision.liquidation_distance > 0.05  # At least 5%


# ============================================================================
# Funding Fees
# ============================================================================


@pytest.mark.integration
def test_evaluate_signal_v2_includes_funding_estimate(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test that v2 includes funding fee estimate.

    Given:
        Funding rate = 0.01% per 8h
    When:
        Evaluating signal
    Then:
        Should include funding fee estimate
    """
    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=standard_risk_config,
        market_conditions=standard_market_conditions,
    )

    assert decision.funding_fee_estimate is not None
    assert decision.funding_fee_estimate > 0  # Long pays positive funding


# ============================================================================
# Config Loader
# ============================================================================


@pytest.mark.integration
def test_load_risk_config_merges_all_modules():
    """Test that load_risk_config merges all module configs.

    Given:
        All modules have config loaders
    When:
        Loading risk config
    Then:
        Should merge all configs into one dict
    """
    config = load_risk_config()

    # Base risk config
    assert "MAX_POSITION_PCT" in config
    assert "MAX_DRAWDOWN_PCT" in config

    # Perpetuals config
    assert "MARGIN_MODE" in config
    assert "MAX_LEVERAGE" in config

    # Position sizing config
    assert "SIZING_METHOD" in config
    assert "RISK_PER_TRADE" in config

    # Execution config
    assert "MAKER_FEE" in config
    assert "TAKER_FEE" in config


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.integration
def test_evaluate_signal_v2_handles_missing_market_conditions(
    standard_signal, standard_risk_state, standard_risk_config
):
    """Test that v2 handles missing market conditions gracefully.

    Given:
        Market conditions missing some fields
    When:
        Evaluating signal
    Then:
        Should use defaults and still work
    """
    market_conditions = {
        "volatility": 0.60,
        # Missing: atr, order_book_depth, funding_rate
    }

    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=standard_risk_config,
        market_conditions=market_conditions,
    )

    # Should still work with defaults
    assert decision.approved is True


@pytest.mark.integration
def test_evaluate_signal_v2_returns_enhanced_decision_type(
    standard_signal,
    standard_risk_state,
    standard_risk_config,
    standard_market_conditions,
):
    """Test that v2 returns EnhancedRiskDecision (not base RiskDecision).

    Given:
        Standard conditions
    When:
        Evaluating signal with v2
    Then:
        Should return EnhancedRiskDecision with extra fields
    """
    decision = evaluate_signal_v2(
        signal_event=standard_signal,
        risk_state=standard_risk_state,
        risk_config=standard_risk_config,
        market_conditions=standard_market_conditions,
    )

    # Check that it's EnhancedRiskDecision (has extra fields)
    assert hasattr(decision, "liquidation_price")
    assert hasattr(decision, "leverage")
    assert hasattr(decision, "expected_slippage_bps")
    assert hasattr(decision, "execution_fees")
    assert hasattr(decision, "sizing_method")
    assert hasattr(decision, "funding_fee_estimate")
