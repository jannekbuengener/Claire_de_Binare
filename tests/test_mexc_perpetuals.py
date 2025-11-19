"""Unit tests for MEXC Perpetual Futures Position Management.

Tests cover:
- Position creation & validation
- Margin calculations (position & maintenance)
- Liquidation price formulas (long & short)
- Unrealized PnL calculation
- Funding fee calculation
- MMR tracking
- Liquidation distance validation
"""

import pytest
from services.mexc_perpetuals import (
    MarginMode,
    MexcPerpetualPosition,
    PositionSide,
    create_position_from_signal,
    load_perpetuals_config,
    validate_liquidation_distance,
)


@pytest.fixture
def btc_long_position():
    """Sample BTC long position with 10x leverage."""
    return MexcPerpetualPosition(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        size=0.1,  # 0.1 BTC
        entry_price=50000.0,  # 50k USDT
        leverage=10,
        margin_mode=MarginMode.ISOLATED,
    )


@pytest.fixture
def btc_short_position():
    """Sample BTC short position with 10x leverage."""
    return MexcPerpetualPosition(
        symbol="BTCUSDT",
        side=PositionSide.SHORT,
        size=0.1,
        entry_price=50000.0,
        leverage=10,
        margin_mode=MarginMode.ISOLATED,
    )


@pytest.fixture
def high_leverage_position():
    """High leverage position (25x) for edge case testing."""
    return MexcPerpetualPosition(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        size=0.1,
        entry_price=50000.0,
        leverage=25,
        margin_mode=MarginMode.ISOLATED,
    )


# ============================================================================
# Position Creation & Validation
# ============================================================================


@pytest.mark.unit
def test_position_creation_long(btc_long_position):
    """Test basic long position creation."""
    assert btc_long_position.symbol == "BTCUSDT"
    assert btc_long_position.side == PositionSide.LONG
    assert btc_long_position.size == 0.1
    assert btc_long_position.entry_price == 50000.0
    assert btc_long_position.leverage == 10
    assert btc_long_position.margin_mode == MarginMode.ISOLATED


@pytest.mark.unit
def test_position_creation_short(btc_short_position):
    """Test basic short position creation."""
    assert btc_short_position.side == PositionSide.SHORT


@pytest.mark.unit
def test_position_value(btc_long_position):
    """Test position notional value calculation."""
    # Position Value = Entry Price × Size
    expected_value = 50000.0 * 0.1
    assert btc_long_position.position_value == expected_value


@pytest.mark.unit
def test_invalid_leverage_raises_error():
    """Test that invalid leverage raises ValueError."""
    with pytest.raises(ValueError, match="Leverage must be between 1-125"):
        MexcPerpetualPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=0.1,
            entry_price=50000.0,
            leverage=200,  # Invalid: > 125
        )


@pytest.mark.unit
def test_negative_size_raises_error():
    """Test that negative size raises ValueError."""
    with pytest.raises(ValueError, match="Position size must be positive"):
        MexcPerpetualPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=-0.1,  # Invalid: negative
            entry_price=50000.0,
            leverage=10,
        )


@pytest.mark.unit
def test_zero_price_raises_error():
    """Test that zero price raises ValueError."""
    with pytest.raises(ValueError, match="Entry price must be positive"):
        MexcPerpetualPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=0.1,
            entry_price=0.0,  # Invalid: zero
            leverage=10,
        )


# ============================================================================
# Margin Calculations
# ============================================================================


@pytest.mark.unit
def test_position_margin_calculation(btc_long_position):
    """Test position margin formula: PM = Position Value / Leverage.

    Given:
        Position Value = 50,000 × 0.1 = 5,000 USDT
        Leverage = 10x
    When:
        Calculating position margin
    Then:
        PM = 5,000 / 10 = 500 USDT
    """
    expected_margin = 5000.0 / 10
    assert btc_long_position.calculate_position_margin() == expected_margin


@pytest.mark.unit
def test_maintenance_margin_calculation(btc_long_position):
    """Test maintenance margin formula: MM = Position Value × MMR.

    Given:
        Position Value = 5,000 USDT
        MMR = 0.005 (0.5% default)
    When:
        Calculating maintenance margin
    Then:
        MM = 5,000 × 0.005 = 25 USDT
    """
    expected_mm = 5000.0 * 0.005
    assert btc_long_position.calculate_maintenance_margin() == expected_mm


@pytest.mark.unit
def test_higher_leverage_reduces_position_margin(high_leverage_position):
    """Test that higher leverage reduces required position margin.

    Given:
        Position Value = 5,000 USDT
        Leverage = 25x
    When:
        Calculating position margin
    Then:
        PM = 5,000 / 25 = 200 USDT (lower than 10x)
    """
    expected_margin = 5000.0 / 25
    assert high_leverage_position.calculate_position_margin() == expected_margin
    assert expected_margin < 500.0  # Lower than 10x leverage


# ============================================================================
# Liquidation Price Calculation
# ============================================================================


@pytest.mark.unit
def test_liquidation_price_long(btc_long_position):
    """Test long position liquidation price calculation.

    Formula:
        LP = (MM - PM + Entry × Size) / Size

    Given:
        Entry = 50,000 USDT
        Size = 0.1 BTC
        MM = 25 USDT
        PM = 500 USDT
    When:
        Calculating liquidation price
    Then:
        LP = (25 - 500 + 50,000 × 0.1) / 0.1
        LP = (25 - 500 + 5,000) / 0.1
        LP = 4,525 / 0.1 = 45,250 USDT
    """
    liq_price = btc_long_position.calculate_liquidation_price()
    expected_liq_price = (25.0 - 500.0 + 50000.0 * 0.1) / 0.1

    # Allow small floating point error
    assert abs(liq_price - expected_liq_price) < 0.01
    assert abs(liq_price - 45250.0) < 0.01


@pytest.mark.unit
def test_liquidation_price_short(btc_short_position):
    """Test short position liquidation price calculation.

    Formula:
        LP = (Entry × Size - MM + PM) / Size

    Given:
        Entry = 50,000 USDT
        Size = 0.1 BTC
        MM = 25 USDT
        PM = 500 USDT
    When:
        Calculating liquidation price
    Then:
        LP = (50,000 × 0.1 - 25 + 500) / 0.1
        LP = (5,000 - 25 + 500) / 0.1
        LP = 5,475 / 0.1 = 54,750 USDT
    """
    liq_price = btc_short_position.calculate_liquidation_price()
    expected_liq_price = (50000.0 * 0.1 - 25.0 + 500.0) / 0.1

    assert abs(liq_price - expected_liq_price) < 0.01
    assert abs(liq_price - 54750.0) < 0.01


@pytest.mark.unit
def test_liquidation_distance_long(btc_long_position):
    """Test liquidation distance calculation for long position.

    Given:
        Entry = 50,000 USDT
        Liquidation Price = 45,250 USDT
    When:
        Calculating liquidation distance
    Then:
        Distance = (50,000 - 45,250) / 50,000 = 0.095 (9.5%)
    """
    distance = btc_long_position.calculate_liquidation_distance()
    expected_distance = (50000.0 - 45250.0) / 50000.0

    assert abs(distance - expected_distance) < 0.001
    assert abs(distance - 0.095) < 0.001


@pytest.mark.unit
def test_liquidation_distance_short(btc_short_position):
    """Test liquidation distance calculation for short position.

    Given:
        Entry = 50,000 USDT
        Liquidation Price = 54,750 USDT
    When:
        Calculating liquidation distance
    Then:
        Distance = (54,750 - 50,000) / 50,000 = 0.095 (9.5%)
    """
    distance = btc_short_position.calculate_liquidation_distance()
    expected_distance = (54750.0 - 50000.0) / 50000.0

    assert abs(distance - expected_distance) < 0.001
    assert abs(distance - 0.095) < 0.001


@pytest.mark.unit
def test_higher_leverage_reduces_liquidation_distance(high_leverage_position):
    """Test that higher leverage reduces liquidation distance (more risky).

    Given:
        25x leverage position
    When:
        Comparing to 10x leverage
    Then:
        Liquidation distance should be smaller (closer to entry)
    """
    # 10x position
    pos_10x = MexcPerpetualPosition(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        size=0.1,
        entry_price=50000.0,
        leverage=10,
    )

    distance_10x = pos_10x.calculate_liquidation_distance()
    distance_25x = high_leverage_position.calculate_liquidation_distance()

    assert distance_25x < distance_10x


# ============================================================================
# Unrealized PnL Calculation
# ============================================================================


@pytest.mark.unit
def test_unrealized_pnl_long_profit(btc_long_position):
    """Test unrealized PnL for profitable long position.

    Given:
        Entry = 50,000 USDT
        Current = 52,000 USDT
        Size = 0.1 BTC
    When:
        Calculating unrealized PnL
    Then:
        PnL = (52,000 - 50,000) × 0.1 = 200 USDT (profit)
    """
    current_price = 52000.0
    pnl = btc_long_position.calculate_unrealized_pnl(current_price)
    expected_pnl = (52000.0 - 50000.0) * 0.1

    assert pnl == expected_pnl
    assert pnl > 0  # Profit


@pytest.mark.unit
def test_unrealized_pnl_long_loss(btc_long_position):
    """Test unrealized PnL for losing long position.

    Given:
        Entry = 50,000 USDT
        Current = 48,000 USDT
        Size = 0.1 BTC
    When:
        Calculating unrealized PnL
    Then:
        PnL = (48,000 - 50,000) × 0.1 = -200 USDT (loss)
    """
    current_price = 48000.0
    pnl = btc_long_position.calculate_unrealized_pnl(current_price)
    expected_pnl = (48000.0 - 50000.0) * 0.1

    assert pnl == expected_pnl
    assert pnl < 0  # Loss


@pytest.mark.unit
def test_unrealized_pnl_short_profit(btc_short_position):
    """Test unrealized PnL for profitable short position.

    Given:
        Entry = 50,000 USDT
        Current = 48,000 USDT (price dropped)
        Size = 0.1 BTC
    When:
        Calculating unrealized PnL
    Then:
        PnL = (50,000 - 48,000) × 0.1 = 200 USDT (profit)
    """
    current_price = 48000.0
    pnl = btc_short_position.calculate_unrealized_pnl(current_price)
    expected_pnl = (50000.0 - 48000.0) * 0.1

    assert pnl == expected_pnl
    assert pnl > 0  # Profit for short when price drops


@pytest.mark.unit
def test_unrealized_pnl_short_loss(btc_short_position):
    """Test unrealized PnL for losing short position.

    Given:
        Entry = 50,000 USDT
        Current = 52,000 USDT (price rose)
        Size = 0.1 BTC
    When:
        Calculating unrealized PnL
    Then:
        PnL = (50,000 - 52,000) × 0.1 = -200 USDT (loss)
    """
    current_price = 52000.0
    pnl = btc_short_position.calculate_unrealized_pnl(current_price)
    expected_pnl = (50000.0 - 52000.0) * 0.1

    assert pnl == expected_pnl
    assert pnl < 0  # Loss for short when price rises


# ============================================================================
# Funding Fee Calculation
# ============================================================================


@pytest.mark.unit
def test_funding_fee_long_positive_rate(btc_long_position):
    """Test funding fee for long position with positive rate (long pays short).

    Given:
        Position Value = 5,000 USDT
        Funding Rate = 0.0001 (0.01%)
        Time = 8h (1 settlement period)
    When:
        Calculating funding fee
    Then:
        Fee = 5,000 × 0.0001 = 0.5 USDT (long pays)
    """
    funding_rate = 0.0001
    fee = btc_long_position.calculate_funding_fee(funding_rate, hours=8.0)
    expected_fee = 5000.0 * 0.0001

    assert abs(fee - expected_fee) < 0.001
    assert fee > 0  # Long pays


@pytest.mark.unit
def test_funding_fee_short_positive_rate(btc_short_position):
    """Test funding fee for short position with positive rate (short receives).

    Given:
        Position Value = 5,000 USDT
        Funding Rate = 0.0001 (0.01%)
        Time = 8h
    When:
        Calculating funding fee
    Then:
        Fee = -5,000 × 0.0001 = -0.5 USDT (short receives)
    """
    funding_rate = 0.0001
    fee = btc_short_position.calculate_funding_fee(funding_rate, hours=8.0)
    expected_fee = -5000.0 * 0.0001

    assert abs(fee - expected_fee) < 0.001
    assert fee < 0  # Short receives (negative = income)


@pytest.mark.unit
def test_funding_fee_scales_with_time(btc_long_position):
    """Test that funding fee scales linearly with time.

    Given:
        Funding Rate = 0.0001
        Base Period = 8h
    When:
        Calculating for 24h (3 settlements)
    Then:
        Fee should be 3× the 8h fee
    """
    funding_rate = 0.0001
    fee_8h = btc_long_position.calculate_funding_fee(funding_rate, hours=8.0)
    fee_24h = btc_long_position.calculate_funding_fee(funding_rate, hours=24.0)

    assert abs(fee_24h - 3 * fee_8h) < 0.001


@pytest.mark.unit
def test_funding_fee_negative_rate(btc_long_position):
    """Test funding fee with negative rate (shorts pay longs).

    Given:
        Funding Rate = -0.0001 (negative)
    When:
        Long position
    Then:
        Long receives funding (negative fee)
    """
    funding_rate = -0.0001
    fee = btc_long_position.calculate_funding_fee(funding_rate, hours=8.0)

    assert fee < 0  # Long receives


# ============================================================================
# Maintenance Margin Rate (MMR) Tracking
# ============================================================================


@pytest.mark.unit
def test_mmr_at_entry_price(btc_long_position):
    """Test MMR calculation at entry price.

    Given:
        Entry Price = 50,000 USDT
        Maintenance Margin = 25 USDT
        Position Value = 5,000 USDT
    When:
        Calculating MMR at entry
    Then:
        MMR = 25 / 5,000 = 0.005 (0.5%)
    """
    mmr = btc_long_position.calculate_mmr(50000.0)
    expected_mmr = 25.0 / 5000.0

    assert abs(mmr - expected_mmr) < 0.0001
    assert abs(mmr - 0.005) < 0.0001


@pytest.mark.unit
def test_mmr_increases_as_price_drops_long(btc_long_position):
    """Test that MMR increases as price drops for long position.

    Given:
        Long position with entry at 50,000
    When:
        Price drops to 45,250 (near liquidation)
    Then:
        MMR should increase (maintenance margin stays constant,
        but position value decreases, so MMR = MM / Value increases)
    """
    mmr_entry = btc_long_position.calculate_mmr(50000.0)
    mmr_lower_price = btc_long_position.calculate_mmr(45250.0)

    # MMR should increase as price drops (same MM, lower value)
    assert mmr_lower_price > mmr_entry

    # At entry: MMR = 25 / 5000 = 0.005 (0.5%)
    # At 45,250: MMR = 25 / 4525 = 0.0055 (0.55%)
    assert abs(mmr_entry - 0.005) < 0.001
    assert mmr_lower_price > 0.0055


# ============================================================================
# Validation Functions
# ============================================================================


@pytest.mark.unit
def test_validate_liquidation_distance_pass(btc_long_position):
    """Test liquidation distance validation (passing case).

    Given:
        Liquidation Distance = 9.5%
        Min Required = 5%
    When:
        Validating
    Then:
        Should approve (9.5% > 5%)
    """
    result = validate_liquidation_distance(btc_long_position, min_distance=0.05)

    assert result["approved"] is True
    assert result["reason"] is None
    assert abs(result["distance"] - 0.095) < 0.001


@pytest.mark.unit
def test_validate_liquidation_distance_fail(btc_long_position):
    """Test liquidation distance validation (failing case).

    Given:
        Liquidation Distance = 9.5%
        Min Required = 15%
    When:
        Validating
    Then:
        Should reject (9.5% < 15%)
    """
    result = validate_liquidation_distance(btc_long_position, min_distance=0.15)

    assert result["approved"] is False
    assert "liquidation_risk_too_high" in result["reason"]
    assert abs(result["distance"] - 0.095) < 0.001


# ============================================================================
# Helper Functions
# ============================================================================


@pytest.mark.unit
def test_create_position_from_signal():
    """Test position creation from signal event.

    Given:
        Signal with buy side, price 50,000
        Config with 10x leverage, isolated margin
    When:
        Creating position
    Then:
        Should create correct MexcPerpetualPosition
    """
    signal = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50000.0,
    }
    config = {
        "MAX_LEVERAGE": 10,
        "MARGIN_MODE": "isolated",
    }

    position = create_position_from_signal(signal, size=0.1, config=config)

    assert position.symbol == "BTCUSDT"
    assert position.side == PositionSide.LONG
    assert position.entry_price == 50000.0
    assert position.size == 0.1
    assert position.leverage == 10
    assert position.margin_mode == MarginMode.ISOLATED


@pytest.mark.unit
def test_create_position_from_signal_short():
    """Test short position creation from sell signal."""
    signal = {
        "symbol": "BTCUSDT",
        "side": "sell",
        "price": 50000.0,
    }
    config = {"MAX_LEVERAGE": 5}

    position = create_position_from_signal(signal, size=0.2, config=config)

    assert position.side == PositionSide.SHORT
    assert position.leverage == 5


@pytest.mark.unit
def test_position_to_dict(btc_long_position):
    """Test position serialization to dictionary.

    Given:
        Position object
    When:
        Converting to dict
    Then:
        Should contain all key attributes
    """
    pos_dict = btc_long_position.to_dict()

    assert pos_dict["symbol"] == "BTCUSDT"
    assert pos_dict["side"] == "long"
    assert pos_dict["size"] == 0.1
    assert pos_dict["entry_price"] == 50000.0
    assert pos_dict["leverage"] == 10
    assert "liquidation_price" in pos_dict
    assert "liquidation_distance" in pos_dict


@pytest.mark.unit
def test_load_perpetuals_config():
    """Test loading config from environment variables.

    Given:
        ENV variables (or defaults)
    When:
        Loading config
    Then:
        Should return dict with all parameters
    """
    config = load_perpetuals_config()

    assert "MARGIN_MODE" in config
    assert "MAX_LEVERAGE" in config
    assert "MIN_LIQUIDATION_DISTANCE" in config
    assert "FUNDING_RATE" in config

    # Check types
    assert isinstance(config["MAX_LEVERAGE"], int)
    assert isinstance(config["MIN_LIQUIDATION_DISTANCE"], float)
