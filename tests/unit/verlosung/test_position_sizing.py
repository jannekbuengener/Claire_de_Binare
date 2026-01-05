"""Unit tests for Advanced Position Sizing Strategies.

Tests cover:
- Fixed-Fractional Sizing
- Volatility Targeting
- Kelly Criterion
- ATR-Based Sizing
- Method Selection Logic
"""

import pytest
from services.position_sizing import (
    PositionSizer,
    PositionSizingResult,
    load_sizing_config,
    select_sizing_method,
)


# ============================================================================
# Fixed-Fractional Sizing
# ============================================================================


@pytest.mark.unit
def test_fixed_fractional_basic():
    """Test fixed-fractional sizing with standard parameters.

    Given:
        Equity = 100,000 USDT
        Risk = 2%
        Stop Distance = 2%
        Entry Price = 50,000 USDT
    When:
        Calculating position size
    Then:
        Risk Amount = 2,000 USDT
        Stop in USD = 50,000 × 0.02 = 1,000 USDT
        Position = 2,000 / 1,000 = 2.0 contracts
        Position USD = 2.0 × 50,000 = 100,000 USDT
    """
    result = PositionSizer.fixed_fractional(
        equity=100000.0,
        risk_fraction=0.02,
        stop_loss_distance=0.02,
        entry_price=50000.0,
    )

    assert result.method == "fixed_fractional"
    assert result.risk_amount == 2000.0
    assert abs(result.size_usd - 100000.0) < 1.0
    assert abs(result.size_contracts - 2.0) < 0.01


@pytest.mark.unit
def test_fixed_fractional_tighter_stop_larger_position():
    """Test that tighter stop allows larger position for same risk.

    Given:
        Same equity and risk
        Tighter stop (1% vs 2%)
    When:
        Calculating position size
    Then:
        Position size should double (stop is half)
    """
    result_2pct_stop = PositionSizer.fixed_fractional(
        equity=100000.0,
        risk_fraction=0.02,
        stop_loss_distance=0.02,
        entry_price=50000.0,
    )

    result_1pct_stop = PositionSizer.fixed_fractional(
        equity=100000.0,
        risk_fraction=0.02,
        stop_loss_distance=0.01,  # Tighter stop
        entry_price=50000.0,
    )

    # Tighter stop → larger position for same risk
    assert result_1pct_stop.size_usd > result_2pct_stop.size_usd
    assert abs(result_1pct_stop.size_usd / result_2pct_stop.size_usd - 2.0) < 0.01


@pytest.mark.unit
def test_fixed_fractional_higher_risk_larger_position():
    """Test that higher risk % increases position size.

    Given:
        Risk 4% instead of 2%
    When:
        Calculating position size
    Then:
        Position should double
    """
    result_2pct_risk = PositionSizer.fixed_fractional(
        equity=100000.0,
        risk_fraction=0.02,
        stop_loss_distance=0.02,
        entry_price=50000.0,
    )

    result_4pct_risk = PositionSizer.fixed_fractional(
        equity=100000.0,
        risk_fraction=0.04,  # Double risk
        stop_loss_distance=0.02,
        entry_price=50000.0,
    )

    assert abs(result_4pct_risk.size_usd / result_2pct_risk.size_usd - 2.0) < 0.01


# ============================================================================
# Volatility Targeting
# ============================================================================


@pytest.mark.unit
def test_volatility_targeting_basic():
    """Test volatility targeting with standard parameters.

    Given:
        Equity = 100,000 USDT
        Target Vol = 20% (annual)
        Asset Vol = 60% (BTC typical)
        Price = 50,000 USDT
    When:
        Calculating position size
    Then:
        Notional = (100k × 0.20) / 0.60 = 33,333 USDT
        Contracts = 33,333 / 50,000 = 0.6667 BTC
    """
    result = PositionSizer.volatility_targeting(
        equity=100000.0,
        target_volatility=0.20,
        asset_volatility=0.60,
        current_price=50000.0,
    )

    assert result.method == "volatility_targeting"
    assert abs(result.size_usd - 33333.33) < 1.0
    assert abs(result.size_contracts - 0.6667) < 0.001


@pytest.mark.unit
def test_volatility_targeting_inverse_scaling():
    """Test that position size scales inversely with volatility.

    Given:
        Asset vol doubles (60% → 120%)
    When:
        Calculating position size
    Then:
        Position should halve
    """
    result_60pct_vol = PositionSizer.volatility_targeting(
        equity=100000.0,
        target_volatility=0.20,
        asset_volatility=0.60,
        current_price=50000.0,
    )

    result_120pct_vol = PositionSizer.volatility_targeting(
        equity=100000.0,
        target_volatility=0.20,
        asset_volatility=1.20,  # Double vol
        current_price=50000.0,
    )

    # Position should halve when vol doubles
    assert abs(result_120pct_vol.size_usd / result_60pct_vol.size_usd - 0.5) < 0.01


@pytest.mark.unit
def test_volatility_targeting_zero_vol_raises_error():
    """Test that zero volatility raises ValueError."""
    with pytest.raises(ValueError, match="Asset volatility must be positive"):
        PositionSizer.volatility_targeting(
            equity=100000.0,
            target_volatility=0.20,
            asset_volatility=0.0,  # Invalid
            current_price=50000.0,
        )


@pytest.mark.unit
def test_volatility_targeting_low_vol_increases_position():
    """Test that low volatility increases position size.

    Given:
        Asset vol = 30% (half of typical BTC)
    When:
        Calculating position size
    Then:
        Position should double vs 60% vol
    """
    result_low_vol = PositionSizer.volatility_targeting(
        equity=100000.0,
        target_volatility=0.20,
        asset_volatility=0.30,  # Low vol
        current_price=50000.0,
    )

    result_normal_vol = PositionSizer.volatility_targeting(
        equity=100000.0,
        target_volatility=0.20,
        asset_volatility=0.60,
        current_price=50000.0,
    )

    assert abs(result_low_vol.size_usd / result_normal_vol.size_usd - 2.0) < 0.01


# ============================================================================
# Kelly Criterion
# ============================================================================


@pytest.mark.unit
def test_kelly_criterion_basic():
    """Test Kelly Criterion with positive edge.

    Given:
        Win Rate = 55%
        Avg Win = 3%
        Avg Loss = 1.5%
        Kelly Fraction = 25%
    When:
        Calculating position size
    Then:
        Full Kelly = (0.55 × 0.03 - 0.45 × 0.015) / 0.03 = 0.325 (32.5%)
        Fractional Kelly = 0.325 × 0.25 = 0.08125 (8.125%)
        Position = 100k × 0.08125 = 8,125 USDT
    """
    result = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.55,
        avg_win=0.03,
        avg_loss=0.015,
        kelly_fraction=0.25,
    )

    assert result.method == "kelly_criterion"
    # Full Kelly ≈ 32.5%, Fractional (25%) ≈ 8.125%
    full_kelly = (0.55 * 0.03 - 0.45 * 0.015) / 0.03
    fractional_kelly = full_kelly * 0.25
    expected_size = 100000.0 * fractional_kelly

    assert abs(result.size_usd - expected_size) < 1.0
    assert result.size_usd > 0


@pytest.mark.unit
def test_kelly_criterion_negative_edge_returns_zero():
    """Test Kelly with negative edge (losing strategy).

    Given:
        Win Rate = 40% (losing)
        Avg Win = 2%
        Avg Loss = 3%
    When:
        Calculating position size
    Then:
        Kelly should be negative → return 0
    """
    result = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.40,  # Losing strategy
        avg_win=0.02,
        avg_loss=0.03,
        kelly_fraction=0.25,
    )

    assert result.size_usd == 0.0
    assert "no edge" in result.notes.lower()


@pytest.mark.unit
def test_kelly_criterion_high_winrate_increases_size():
    """Test that higher win rate increases position size.

    Given:
        Win rate 60% vs 55%
    When:
        Calculating position size
    Then:
        60% win rate should give larger position
    """
    result_55pct = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.55,
        avg_win=0.03,
        avg_loss=0.015,
        kelly_fraction=0.25,
    )

    result_60pct = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.60,  # Higher win rate
        avg_win=0.03,
        avg_loss=0.015,
        kelly_fraction=0.25,
    )

    assert result_60pct.size_usd > result_55pct.size_usd


@pytest.mark.unit
def test_kelly_criterion_invalid_winrate_raises_error():
    """Test that invalid win rate raises ValueError."""
    with pytest.raises(ValueError, match="Win rate must be between 0 and 1"):
        PositionSizer.kelly_criterion(
            equity=100000.0,
            win_rate=1.5,  # Invalid
            avg_win=0.03,
            avg_loss=0.015,
        )


@pytest.mark.unit
def test_kelly_criterion_full_kelly_more_aggressive():
    """Test that full Kelly (100%) is more aggressive than fractional.

    Given:
        Kelly fraction 100% vs 25%
    When:
        Calculating position size
    Then:
        Full Kelly should be 4× fractional
    """
    result_fractional = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.55,
        avg_win=0.03,
        avg_loss=0.015,
        kelly_fraction=0.25,
    )

    result_full = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.55,
        avg_win=0.03,
        avg_loss=0.015,
        kelly_fraction=1.0,  # Full Kelly
    )

    assert abs(result_full.size_usd / result_fractional.size_usd - 4.0) < 0.01


# ============================================================================
# ATR-Based Sizing
# ============================================================================


@pytest.mark.unit
def test_atr_based_sizing_basic():
    """Test ATR-based sizing with standard parameters.

    Given:
        Equity = 100,000 USDT
        ATR = 2,500 USDT
        ATR Multiplier = 2.0
        Risk per Trade = 2%
        Entry Price = 50,000 USDT
    When:
        Calculating position size
    Then:
        Stop Distance = 2,500 × 2.0 = 5,000 USDT
        Risk Amount = 100k × 0.02 = 2,000 USDT
        Contracts = 2,000 / 5,000 = 0.4
        Position USD = 0.4 × 50,000 = 20,000 USDT
    """
    result = PositionSizer.atr_based_sizing(
        equity=100000.0,
        atr=2500.0,
        atr_multiplier=2.0,
        risk_per_trade=0.02,
        entry_price=50000.0,
    )

    assert result.method == "atr_based"
    assert result.risk_amount == 2000.0
    assert abs(result.size_contracts - 0.4) < 0.01
    assert abs(result.size_usd - 20000.0) < 1.0


@pytest.mark.unit
def test_atr_based_sizing_higher_atr_smaller_position():
    """Test that higher ATR reduces position size.

    Given:
        ATR doubles (2,500 → 5,000)
    When:
        Calculating position size
    Then:
        Position should halve
    """
    result_low_atr = PositionSizer.atr_based_sizing(
        equity=100000.0,
        atr=2500.0,
        atr_multiplier=2.0,
        risk_per_trade=0.02,
        entry_price=50000.0,
    )

    result_high_atr = PositionSizer.atr_based_sizing(
        equity=100000.0,
        atr=5000.0,  # Double ATR
        atr_multiplier=2.0,
        risk_per_trade=0.02,
        entry_price=50000.0,
    )

    assert abs(result_high_atr.size_usd / result_low_atr.size_usd - 0.5) < 0.01


@pytest.mark.unit
def test_atr_based_sizing_zero_atr_raises_error():
    """Test that zero ATR raises ValueError."""
    with pytest.raises(ValueError, match="ATR must be positive"):
        PositionSizer.atr_based_sizing(
            equity=100000.0,
            atr=0.0,  # Invalid
            atr_multiplier=2.0,
            risk_per_trade=0.02,
            entry_price=50000.0,
        )


@pytest.mark.unit
def test_atr_based_sizing_higher_multiplier_wider_stop():
    """Test that higher ATR multiplier widens stop (smaller position).

    Given:
        ATR multiplier 3.0 vs 2.0
    When:
        Calculating position size
    Then:
        Position should be 2/3 of original (stop 1.5× wider)
    """
    result_2x = PositionSizer.atr_based_sizing(
        equity=100000.0,
        atr=2500.0,
        atr_multiplier=2.0,
        risk_per_trade=0.02,
        entry_price=50000.0,
    )

    result_3x = PositionSizer.atr_based_sizing(
        equity=100000.0,
        atr=2500.0,
        atr_multiplier=3.0,  # Wider stop
        risk_per_trade=0.02,
        entry_price=50000.0,
    )

    assert abs(result_3x.size_usd / result_2x.size_usd - 2.0 / 3.0) < 0.01


# ============================================================================
# Method Selection
# ============================================================================


@pytest.mark.unit
def test_select_sizing_method_fixed_fractional():
    """Test select_sizing_method with fixed_fractional."""
    signal = {"price": 50000.0, "side": "buy", "symbol": "BTCUSDT"}
    market_conditions = {"volatility": 0.60, "atr": 2500.0}
    config = {
        "RISK_PER_TRADE": 0.02,
        "STOP_LOSS_PCT": 0.02,
    }

    result = select_sizing_method(
        method="fixed_fractional",
        equity=100000.0,
        signal=signal,
        market_conditions=market_conditions,
        config=config,
    )

    assert result.method == "fixed_fractional"
    assert result.size_usd > 0


@pytest.mark.unit
def test_select_sizing_method_volatility_targeting():
    """Test select_sizing_method with volatility_targeting."""
    signal = {"price": 50000.0, "side": "buy", "symbol": "BTCUSDT"}
    market_conditions = {"volatility": 0.60}
    config = {"TARGET_VOL": 0.20}

    result = select_sizing_method(
        method="volatility_targeting",
        equity=100000.0,
        signal=signal,
        market_conditions=market_conditions,
        config=config,
    )

    assert result.method == "volatility_targeting"
    assert result.size_usd > 0


@pytest.mark.unit
def test_select_sizing_method_kelly_criterion():
    """Test select_sizing_method with kelly_criterion."""
    signal = {"price": 50000.0, "side": "buy", "symbol": "BTCUSDT"}
    market_conditions = {
        "volatility": 0.60,
        "win_rate": 0.55,
        "avg_win": 0.03,
        "avg_loss": 0.015,
    }
    config = {"KELLY_FRACTION": 0.25}

    result = select_sizing_method(
        method="kelly_criterion",
        equity=100000.0,
        signal=signal,
        market_conditions=market_conditions,
        config=config,
    )

    assert result.method == "kelly_criterion"
    assert result.size_usd > 0


@pytest.mark.unit
def test_select_sizing_method_atr_based():
    """Test select_sizing_method with atr_based."""
    signal = {"price": 50000.0, "side": "buy", "symbol": "BTCUSDT"}
    market_conditions = {"atr": 2500.0}
    config = {
        "ATR_MULTIPLIER": 2.0,
        "RISK_PER_TRADE": 0.02,
    }

    result = select_sizing_method(
        method="atr_based",
        equity=100000.0,
        signal=signal,
        market_conditions=market_conditions,
        config=config,
    )

    assert result.method == "atr_based"
    assert result.size_usd > 0


@pytest.mark.unit
def test_select_sizing_method_unknown_raises_error():
    """Test that unknown method raises ValueError."""
    signal = {"price": 50000.0, "side": "buy", "symbol": "BTCUSDT"}
    market_conditions = {}
    config = {}

    with pytest.raises(ValueError, match="Unknown sizing method"):
        select_sizing_method(
            method="unknown_method",
            equity=100000.0,
            signal=signal,
            market_conditions=market_conditions,
            config=config,
        )


@pytest.mark.unit
def test_select_sizing_method_atr_missing_raises_error():
    """Test that ATR-based sizing without ATR raises error."""
    signal = {"price": 50000.0, "side": "buy", "symbol": "BTCUSDT"}
    market_conditions = {}  # No ATR
    config = {"ATR_MULTIPLIER": 2.0, "RISK_PER_TRADE": 0.02}

    with pytest.raises(ValueError, match="ATR must be provided"):
        select_sizing_method(
            method="atr_based",
            equity=100000.0,
            signal=signal,
            market_conditions=market_conditions,
            config=config,
        )


# ============================================================================
# Config Loading
# ============================================================================


@pytest.mark.unit
def test_load_sizing_config():
    """Test loading sizing config from environment."""
    config = load_sizing_config()

    assert "SIZING_METHOD" in config
    assert "RISK_PER_TRADE" in config
    assert "TARGET_VOL" in config
    assert "KELLY_FRACTION" in config
    assert "ATR_MULTIPLIER" in config

    # Check types
    assert isinstance(config["RISK_PER_TRADE"], float)
    assert isinstance(config["TARGET_VOL"], float)
    assert isinstance(config["KELLY_FRACTION"], float)


# ============================================================================
# Edge Cases & Validation
# ============================================================================


@pytest.mark.unit
def test_position_sizing_result_dataclass():
    """Test PositionSizingResult dataclass attributes."""
    result = PositionSizingResult(
        size_usd=50000.0,
        size_contracts=1.0,
        method="test_method",
        sizing_factor=0.5,
        risk_amount=2000.0,
        notes="Test note",
    )

    assert result.size_usd == 50000.0
    assert result.size_contracts == 1.0
    assert result.method == "test_method"
    assert result.sizing_factor == 0.5
    assert result.risk_amount == 2000.0
    assert result.notes == "Test note"


@pytest.mark.unit
def test_kelly_criterion_caps_at_100_percent():
    """Test that Kelly never exceeds 100% of equity.

    Given:
        Very high edge (unrealistic but theoretical)
    When:
        Calculating Kelly
    Then:
        Should cap at 100% equity
    """
    result = PositionSizer.kelly_criterion(
        equity=100000.0,
        win_rate=0.90,  # Unrealistic
        avg_win=0.10,
        avg_loss=0.01,
        kelly_fraction=1.0,  # Full Kelly
    )

    # Should be capped at 100% of equity
    assert result.size_usd <= 100000.0
