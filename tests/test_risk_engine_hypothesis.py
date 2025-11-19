"""Property-Based Tests für Risk Engine - Phase 4 Test Improvements.

Diese Tests nutzen Hypothesis für property-based testing um
Invarianten und Edge-Cases automatisch zu finden.
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st, assume

from services import risk_engine


# =============================================================================
# Property-Based Tests für Position Sizing
# =============================================================================


@pytest.mark.unit
@given(
    equity=st.floats(min_value=1000.0, max_value=10_000_000.0),
    price=st.floats(min_value=0.01, max_value=1_000_000.0),
    max_pct=st.floats(min_value=0.01, max_value=0.5),
    requested_size=st.floats(min_value=0.01, max_value=100.0),
)
def test_position_size_never_exceeds_max_pct(equity, price, max_pct, requested_size):
    """Position-Size überschreitet nie MAX_POSITION_PCT * equity.

    Property: position_size * price <= equity * max_pct
    """
    # Arrange
    config = {"ACCOUNT_EQUITY": equity, "MAX_POSITION_PCT": max_pct}
    signal = {"price": price, "size": requested_size}

    # Act
    size = risk_engine.limit_position_size(signal, config, equity=equity)
    notional = size * price

    # Assert: Position value never exceeds max percentage
    max_notional = equity * max_pct
    assert notional <= max_notional * 1.001  # 0.1% tolerance for float arithmetic


@pytest.mark.unit
@given(
    price=st.floats(min_value=0.01, max_value=1_000_000.0),
    stop_pct=st.floats(min_value=0.001, max_value=0.5),
)
def test_stop_loss_always_below_entry_for_longs(price, stop_pct):
    """Stop-Loss ist immer unterhalb Entry für Long-Positionen.

    Property: stop_price < entry_price für side == 'buy'
    """
    # Arrange
    signal = {"symbol": "TEST", "side": "buy", "price": price}
    config = {"STOP_LOSS_PCT": stop_pct}

    # Act
    stop_data = risk_engine.generate_stop_loss(signal, config)

    # Assert
    assert stop_data["stop_price"] < price


@pytest.mark.unit
@given(
    price=st.floats(min_value=0.01, max_value=1_000_000.0),
    stop_pct=st.floats(min_value=0.001, max_value=0.5),
)
def test_stop_loss_always_above_entry_for_shorts(price, stop_pct):
    """Stop-Loss ist immer oberhalb Entry für Short-Positionen.

    Property: stop_price > entry_price für side == 'sell'
    """
    # Arrange
    signal = {"symbol": "TEST", "side": "sell", "price": price}
    config = {"STOP_LOSS_PCT": stop_pct}

    # Act
    stop_data = risk_engine.generate_stop_loss(signal, config)

    # Assert
    assert stop_data["stop_price"] > price


@pytest.mark.unit
@given(
    equity=st.floats(min_value=1000.0, max_value=1_000_000.0),
    daily_pnl_pct=st.floats(min_value=-0.20, max_value=0.20),
)
def test_drawdown_decision_consistency(equity, daily_pnl_pct):
    """Drawdown-Decision ist konsistent mit Grenzwert.

    Property: Wenn daily_pnl <= -equity * 0.05, dann approved == False
    """
    # Arrange
    daily_pnl = equity * daily_pnl_pct
    state = {
        "equity": equity,
        "daily_pnl": daily_pnl,
        "total_exposure_pct": 0.0,
    }
    config = {
        "ACCOUNT_EQUITY": equity,
        "MAX_DRAWDOWN_PCT": 0.05,
        "MAX_POSITION_PCT": 0.10,
        "MAX_EXPOSURE_PCT": 0.30,
    }
    signal = {"symbol": "TEST", "side": "buy", "price": 50_000.0, "size": 0.1}

    # Act
    decision = risk_engine.evaluate_signal(signal, state, config)

    # Assert: Consistency check
    drawdown_threshold = -equity * 0.05
    if daily_pnl <= drawdown_threshold:
        assert decision.approved is False
        assert decision.reason == "max_daily_drawdown_exceeded"


@pytest.mark.unit
@given(
    current_exposure=st.floats(min_value=0.0, max_value=0.5),
    signal_exposure=st.floats(min_value=0.0, max_value=0.5),
)
def test_exposure_limit_respected(current_exposure, signal_exposure):
    """Exposure-Limit wird respektiert.

    Property: Wenn total_exposure > 0.30, dann approved == False
    """
    # Arrange
    max_exposure = 0.30
    equity = 100_000.0

    # Calculate position size that would create signal_exposure
    price = 50_000.0
    target_notional = equity * signal_exposure
    size = target_notional / price

    state = {
        "equity": equity,
        "daily_pnl": 0.0,
        "total_exposure_pct": current_exposure,
    }
    config = {
        "ACCOUNT_EQUITY": equity,
        "MAX_DRAWDOWN_PCT": 0.05,
        "MAX_POSITION_PCT": 0.50,  # High enough to not interfere
        "MAX_EXPOSURE_PCT": max_exposure,
    }
    signal = {"symbol": "TEST", "side": "buy", "price": price, "size": size}

    # Act
    decision = risk_engine.evaluate_signal(signal, state, config)

    # Assert
    total_exposure = current_exposure + signal_exposure
    if total_exposure > max_exposure:
        assert decision.approved is False


@pytest.mark.unit
@given(
    price1=st.floats(min_value=1.0, max_value=100_000.0),
    price2=st.floats(min_value=1.0, max_value=100_000.0),
)
def test_position_size_scales_with_price(price1, price2):
    """Position-Size skaliert invers mit Preis bei gleichem Kapital.

    Property: Wenn price2 > price1, dann size2 < size1
    """
    # Arrange
    assume(price1 != price2)  # Skip wenn gleich
    assume(abs(price2 - price1) / min(price1, price2) > 0.01)  # Mindestens 1% Unterschied

    equity = 100_000.0
    max_pct = 0.10
    config = {"ACCOUNT_EQUITY": equity, "MAX_POSITION_PCT": max_pct}

    signal1 = {"price": price1, "size": 999.0}  # Große Anfrage
    signal2 = {"price": price2, "size": 999.0}

    # Act
    size1 = risk_engine.limit_position_size(signal1, config, equity=equity)
    size2 = risk_engine.limit_position_size(signal2, config, equity=equity)

    # Assert: Inverse Relationship
    if price2 > price1:
        assert size2 < size1 or abs(size2 - size1) < 1e-6  # Allow tiny rounding errors


@pytest.mark.unit
@given(
    equity=st.floats(min_value=1000.0, max_value=1_000_000.0),
    max_pct=st.floats(min_value=0.01, max_value=0.50),
)
def test_approved_signal_has_valid_position_size(equity, max_pct):
    """Approved Signals haben immer eine valide Position-Size > 0.

    Property: Wenn approved == True, dann position_size > 0
    """
    # Arrange
    state = {
        "equity": equity,
        "daily_pnl": 0.0,  # Kein Drawdown
        "total_exposure_pct": 0.0,  # Kein Exposure
    }
    config = {
        "ACCOUNT_EQUITY": equity,
        "MAX_DRAWDOWN_PCT": 0.05,
        "MAX_POSITION_PCT": max_pct,
        "MAX_EXPOSURE_PCT": 0.50,  # Hoch genug
    }
    signal = {"symbol": "TEST", "side": "buy", "price": 50_000.0, "size": 1.0}

    # Act
    decision = risk_engine.evaluate_signal(signal, state, config)

    # Assert
    if decision.approved:
        assert decision.position_size > 0
        assert decision.stop_price is not None


@pytest.mark.unit
@given(
    price=st.floats(min_value=0.01, max_value=1_000_000.0),
    requested_size=st.floats(min_value=0.0, max_value=100.0),
)
def test_position_size_never_exceeds_requested(price, requested_size):
    """Position-Size überschreitet nie die angeforderte Size.

    Property: returned_size <= requested_size
    """
    # Arrange
    equity = 1_000_000.0  # Große equity
    max_pct = 0.50  # Großzügiges Limit
    config = {"ACCOUNT_EQUITY": equity, "MAX_POSITION_PCT": max_pct}
    signal = {"price": price, "size": requested_size}

    # Act
    size = risk_engine.limit_position_size(signal, config, equity=equity)

    # Assert
    assert size <= requested_size * 1.0001  # Tiny tolerance for float precision
