"""Unit tests for Realistic Execution Simulator.

Tests cover:
- Market order simulation (slippage, fees, partial fills)
- Limit order simulation
- Funding fee calculation
- Slippage calculation (base + depth + volatility)
- Roundtrip cost calculation
"""

import pytest
from services.execution_simulator import (
    ExecutionResult,
    ExecutionSimulator,
    load_execution_config,
)


@pytest.fixture
def simulator():
    """Standard execution simulator with default config."""
    return ExecutionSimulator()


@pytest.fixture
def simulator_custom():
    """Execution simulator with custom config for testing."""
    config = {
        "MAKER_FEE": 0.0001,  # 0.01%
        "TAKER_FEE": 0.0005,  # 0.05%
        "BASE_SLIPPAGE_BPS": 10.0,  # 10 bps
        "DEPTH_IMPACT_FACTOR": 0.20,  # 20%
        "VOL_SLIPPAGE_MULTIPLIER": 3.0,  # 3×
        "FILL_THRESHOLD": 0.70,  # 70%
    }
    return ExecutionSimulator(config)


# ============================================================================
# Market Order Simulation
# ============================================================================


@pytest.mark.unit
def test_market_order_full_fill(simulator):
    """Test market order with full fill.

    Given:
        Order size = 25,000 USDT (0.5 BTC @ 50k)
        Order book depth = 1,000,000 USDT
    When:
        Simulating market order
    Then:
        Should fill completely (25k < 80% of 1M)
    """
    result = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.02,
    )

    assert result.filled_size == 0.5
    assert result.partial_fill is False
    assert result.fill_ratio == 1.0
    assert result.avg_fill_price > 50000.0  # Slippage on buy


@pytest.mark.unit
def test_market_order_partial_fill(simulator):
    """Test market order with partial fill.

    Given:
        Order size = 100,000 USDT (2 BTC @ 50k)
        Order book depth = 100,000 USDT
        Fill threshold = 80%
    When:
        Simulating market order
    Then:
        Should partial fill (100k > 80k usable)
        Fill ratio = 80k / 100k = 0.80
    """
    result = simulator.simulate_market_order(
        side="buy",
        size=2.0,
        current_price=50000.0,
        order_book_depth=100000.0,  # Thin liquidity
        volatility=0.02,
    )

    assert result.partial_fill is True
    assert result.fill_ratio < 1.0
    assert abs(result.fill_ratio - 0.80) < 0.01  # 80% fill threshold


@pytest.mark.unit
def test_market_order_buy_has_positive_slippage(simulator):
    """Test that buy orders have positive slippage (price increases).

    Given:
        Buy market order
    When:
        Executing
    Then:
        Fill price > current price (adverse slippage)
    """
    result = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.02,
    )

    assert result.avg_fill_price > 50000.0
    assert result.slippage_bps > 0


@pytest.mark.unit
def test_market_order_sell_has_negative_slippage(simulator):
    """Test that sell orders have negative slippage (price decreases).

    Given:
        Sell market order
    When:
        Executing
    Then:
        Fill price < current price (adverse slippage)
    """
    result = simulator.simulate_market_order(
        side="sell",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.02,
    )

    assert result.avg_fill_price < 50000.0
    assert result.slippage_bps > 0


@pytest.mark.unit
def test_market_order_fees_are_taker(simulator):
    """Test that market orders incur taker fees.

    Given:
        Market order (taker fee = 0.06%)
        Notional = 25,000 USDT
    When:
        Executing
    Then:
        Fees = 25,000 × 0.0006 = 15 USDT
    """
    result = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.02,
    )

    # Notional = 0.5 × 50,000 = 25,000
    # Taker fee = 25,000 × 0.0006 = 15
    assert abs(result.fees - 15.0) < 1.0


# ============================================================================
# Slippage Calculation
# ============================================================================


@pytest.mark.unit
def test_slippage_has_base_component(simulator):
    """Test that slippage includes base component.

    Given:
        Small order, low volatility
    When:
        Calculating slippage
    Then:
        Slippage >= base_slippage_bps (5 bps)
    """
    result = simulator.simulate_market_order(
        side="buy",
        size=0.01,  # Tiny order
        current_price=50000.0,
        order_book_depth=10000000.0,  # Deep liquidity
        volatility=0.001,  # Low vol
    )

    # Should have base slippage (5 bps) + minimal depth/vol impact
    # With very low vol (0.1%) and tiny order, total slippage should be low
    assert result.slippage_bps >= 5.0  # At least base
    assert result.slippage_bps < 30.0  # Not excessive


@pytest.mark.unit
def test_slippage_increases_with_thin_liquidity(simulator):
    """Test that slippage increases with thin liquidity.

    Given:
        Large order relative to depth
    When:
        Calculating slippage
    Then:
        Slippage should increase significantly
    """
    result_deep = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=10000000.0,  # Deep
        volatility=0.02,
    )

    result_thin = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=100000.0,  # Thin
        volatility=0.02,
    )

    # Thin liquidity → higher slippage
    assert result_thin.slippage_bps > result_deep.slippage_bps


@pytest.mark.unit
def test_slippage_increases_with_volatility(simulator):
    """Test that slippage increases with volatility.

    Given:
        High volatility vs low volatility
    When:
        Calculating slippage
    Then:
        High vol should have higher slippage
    """
    result_low_vol = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.01,  # Low vol
    )

    result_high_vol = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.08,  # High vol
    )

    # High volatility → higher slippage
    assert result_high_vol.slippage_bps > result_low_vol.slippage_bps


# ============================================================================
# Limit Order Simulation
# ============================================================================


@pytest.mark.unit
def test_limit_order_buy_fills_at_or_above_market(simulator):
    """Test that buy limit order fills when limit >= market.

    Given:
        Buy limit @ 50,000
        Current price @ 49,500
    When:
        Simulating limit order
    Then:
        Should fill (limit >= market)
    """
    result = simulator.simulate_limit_order(
        side="buy",
        size=0.5,
        limit_price=50000.0,
        current_price=49500.0,
    )

    assert result.filled_size == 0.5
    assert result.fill_ratio == 1.0
    assert result.avg_fill_price == 50000.0  # Fill at limit


@pytest.mark.unit
def test_limit_order_buy_no_fill_below_market(simulator):
    """Test that buy limit order doesn't fill when limit < market.

    Given:
        Buy limit @ 49,000
        Current price @ 50,000
    When:
        Simulating limit order
    Then:
        Should NOT fill (limit < market)
    """
    result = simulator.simulate_limit_order(
        side="buy",
        size=0.5,
        limit_price=49000.0,
        current_price=50000.0,  # Market above limit
    )

    assert result.filled_size == 0.0
    assert result.fill_ratio == 0.0


@pytest.mark.unit
def test_limit_order_sell_fills_at_or_below_market(simulator):
    """Test that sell limit order fills when limit <= market.

    Given:
        Sell limit @ 50,000
        Current price @ 50,500
    When:
        Simulating limit order
    Then:
        Should fill (limit <= market)
    """
    result = simulator.simulate_limit_order(
        side="sell",
        size=0.5,
        limit_price=50000.0,
        current_price=50500.0,
    )

    assert result.filled_size == 0.5
    assert result.avg_fill_price == 50000.0


@pytest.mark.unit
def test_limit_order_uses_maker_fee(simulator):
    """Test that limit orders incur maker fees (cheaper than taker).

    Given:
        Limit order (maker fee = 0.02%)
        Notional = 25,000 USDT
    When:
        Executing
    Then:
        Fees = 25,000 × 0.0002 = 5 USDT (less than taker)
    """
    result = simulator.simulate_limit_order(
        side="buy",
        size=0.5,
        limit_price=50000.0,
        current_price=49500.0,
    )

    # Maker fee is 1/3 of taker fee (0.02% vs 0.06%)
    assert result.fees < 10.0  # Less than taker fee (~15 USDT)
    assert abs(result.fees - 5.0) < 1.0  # ~5 USDT maker fee


@pytest.mark.unit
def test_limit_order_no_slippage(simulator):
    """Test that limit orders have no slippage (filled at limit price)."""
    result = simulator.simulate_limit_order(
        side="buy",
        size=0.5,
        limit_price=50000.0,
        current_price=49500.0,
    )

    assert result.slippage_bps == 0.0


# ============================================================================
# Funding Fees
# ============================================================================


@pytest.mark.unit
def test_funding_fee_calculation_basic(simulator):
    """Test basic funding fee calculation.

    Given:
        Position value = 5,000 USDT
        Funding rate = 0.0001 (0.01%)
        Hours held = 8h (1 settlement)
    When:
        Calculating funding fee
    Then:
        Fee = 5,000 × 0.0001 = 0.5 USDT
    """
    fee = simulator.calculate_funding_fees(
        position_size=0.1,
        position_value=5000.0,
        funding_rate=0.0001,
        hours_held=8.0,
    )

    assert abs(fee - 0.5) < 0.01


@pytest.mark.unit
def test_funding_fee_scales_with_time(simulator):
    """Test that funding fees scale linearly with time.

    Given:
        24 hours vs 8 hours
    When:
        Calculating funding fees
    Then:
        24h fee should be 3× 8h fee
    """
    fee_8h = simulator.calculate_funding_fees(
        position_size=0.1,
        position_value=5000.0,
        funding_rate=0.0001,
        hours_held=8.0,
    )

    fee_24h = simulator.calculate_funding_fees(
        position_size=0.1,
        position_value=5000.0,
        funding_rate=0.0001,
        hours_held=24.0,
    )

    assert abs(fee_24h / fee_8h - 3.0) < 0.01


@pytest.mark.unit
def test_funding_fee_negative_rate(simulator):
    """Test funding fee with negative rate (receive funding).

    Given:
        Negative funding rate
    When:
        Calculating funding fees
    Then:
        Fee should be negative (income)
    """
    fee = simulator.calculate_funding_fees(
        position_size=0.1,
        position_value=5000.0,
        funding_rate=-0.0001,  # Negative
        hours_held=8.0,
    )

    assert fee < 0  # Negative = receive funding


# ============================================================================
# Roundtrip Cost Calculation
# ============================================================================


@pytest.mark.unit
def test_roundtrip_cost_includes_all_components(simulator):
    """Test that roundtrip cost includes entry + exit slippage + fees.

    Given:
        Entry @ 50,000, Exit @ 51,000
    When:
        Calculating roundtrip cost
    Then:
        Total cost = entry slippage + exit slippage + entry fees + exit fees
    """
    costs = simulator.calculate_roundtrip_cost(
        size=1.0,
        entry_price=50000.0,
        exit_price=51000.0,
        order_book_depth=1000000.0,
        volatility=0.02,
    )

    # All components should be positive
    assert costs["entry_slippage"] > 0
    assert costs["exit_slippage"] > 0
    assert costs["entry_fees"] > 0
    assert costs["exit_fees"] > 0
    assert costs["total_cost"] > 0

    # Total should equal sum
    total_sum = (
        costs["entry_slippage"]
        + costs["exit_slippage"]
        + costs["entry_fees"]
        + costs["exit_fees"]
    )
    assert abs(costs["total_cost"] - total_sum) < 0.01


@pytest.mark.unit
def test_roundtrip_cost_higher_with_thin_liquidity(simulator):
    """Test that roundtrip cost increases with thin liquidity."""
    costs_deep = simulator.calculate_roundtrip_cost(
        size=1.0,
        entry_price=50000.0,
        exit_price=51000.0,
        order_book_depth=10000000.0,  # Deep
        volatility=0.02,
    )

    costs_thin = simulator.calculate_roundtrip_cost(
        size=1.0,
        entry_price=50000.0,
        exit_price=51000.0,
        order_book_depth=100000.0,  # Thin
        volatility=0.02,
    )

    assert costs_thin["total_cost"] > costs_deep["total_cost"]


# ============================================================================
# Custom Config
# ============================================================================


@pytest.mark.unit
def test_custom_config_fees(simulator_custom):
    """Test that custom config applies different fees."""
    result = simulator_custom.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.02,
    )

    # Custom taker fee = 0.05% (vs default 0.06%)
    # Notional = 25,000
    # Expected fee = 25,000 × 0.0005 = 12.5
    assert abs(result.fees - 12.5) < 1.0


@pytest.mark.unit
def test_custom_config_base_slippage(simulator_custom):
    """Test that custom config applies different base slippage."""
    result = simulator_custom.simulate_market_order(
        side="buy",
        size=0.01,  # Tiny order
        current_price=50000.0,
        order_book_depth=10000000.0,  # Deep
        volatility=0.001,  # Low vol
    )

    # Custom base slippage = 10 bps (vs default 5 bps)
    assert result.slippage_bps >= 10.0


# ============================================================================
# Config Loading
# ============================================================================


@pytest.mark.unit
def test_load_execution_config():
    """Test loading execution config from environment."""
    config = load_execution_config()

    assert "MAKER_FEE" in config
    assert "TAKER_FEE" in config
    assert "BASE_SLIPPAGE_BPS" in config
    assert "DEPTH_IMPACT_FACTOR" in config
    assert "VOL_SLIPPAGE_MULTIPLIER" in config
    assert "FILL_THRESHOLD" in config
    assert "FUNDING_RATE" in config

    # Check types
    assert isinstance(config["MAKER_FEE"], float)
    assert isinstance(config["TAKER_FEE"], float)


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.unit
def test_execution_result_dataclass():
    """Test ExecutionResult dataclass attributes."""
    result = ExecutionResult(
        filled_size=0.5,
        avg_fill_price=50100.0,
        slippage_bps=20.0,
        fees=15.0,
        partial_fill=False,
        fill_ratio=1.0,
        notes="Test execution",
    )

    assert result.filled_size == 0.5
    assert result.avg_fill_price == 50100.0
    assert result.slippage_bps == 20.0
    assert result.fees == 15.0
    assert result.partial_fill is False
    assert result.fill_ratio == 1.0
    assert result.notes == "Test execution"


@pytest.mark.unit
def test_market_order_zero_volatility(simulator):
    """Test market order with zero volatility (edge case)."""
    result = simulator.simulate_market_order(
        side="buy",
        size=0.5,
        current_price=50000.0,
        order_book_depth=1000000.0,
        volatility=0.0,  # Zero vol
    )

    # Should still work, slippage = base + depth impact
    assert result.filled_size == 0.5
    assert result.slippage_bps >= 5.0  # At least base slippage
