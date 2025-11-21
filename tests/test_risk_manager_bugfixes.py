"""
Tests für Risk Manager Bug-Fixes (P0)

Testet alle 4 kritischen Bugs, die im Risk Manager gefixt wurden:
- Bug #1: Position Size USD→Coins Konvertierung
- Bug #2: Position Limit Check
- Bug #3: Exposure Check für future exposure
- Bug #4: Daily P&L Tracking

Status: Diese Bugs wurden am 2025-11-21 gefixt.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backoffice/services to path
services_path = Path(__file__).parent.parent / "backoffice" / "services" / "risk_manager"
sys.path.insert(0, str(services_path))

from models import Signal, RiskState, OrderResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock Config-Objekt"""
    config = MagicMock()
    config.test_balance = 10000.0
    config.max_position_pct = 0.10  # 10%
    config.max_exposure_pct = 0.50  # 50%
    config.max_daily_drawdown_pct = 0.05  # 5%
    config.stop_loss_pct = 0.02  # 2%
    config.redis_host = "localhost"
    config.redis_port = 6379
    config.redis_password = None
    config.redis_db = 0
    config.input_topic = "signals"
    config.input_topic_order_results = "order_results"
    config.output_topic_orders = "orders"
    config.output_topic_alerts = "alerts"
    config.port = 8002
    config.validate = MagicMock()
    return config


@pytest.fixture
def risk_manager(mock_config):
    """Risk Manager Instanz (ohne Redis-Verbindung)"""
    # Import hier, damit config gemockt werden kann
    with patch("service.config", mock_config):
        from service import RiskManager
        manager = RiskManager()
        # Mock Redis client
        manager.redis_client = MagicMock()
        return manager


@pytest.fixture
def sample_signal():
    """Beispiel-Signal: BTC @ 45000, confidence=0.85"""
    return Signal(
        symbol="BTCUSDT",
        side="BUY",
        confidence=0.85,
        reason="MOMENTUM_BREAKOUT",
        timestamp=1700000000,
        price=45000.0,
        pct_change=0.03,
        type="signal"
    )


@pytest.fixture
def clean_risk_state():
    """Sauberer Risk-State"""
    # Import global risk_state und setze zurück
    from service import risk_state
    risk_state.total_exposure = 0.0
    risk_state.daily_pnl = 0.0
    risk_state.open_positions = 0
    risk_state.signals_blocked = 0
    risk_state.signals_approved = 0
    risk_state.circuit_breaker_active = False
    risk_state.positions.clear()
    risk_state.pending_orders = 0
    risk_state.last_prices.clear()
    risk_state.entry_prices.clear()
    risk_state.position_sides.clear()
    risk_state.realized_pnl_today = 0.0
    return risk_state


# ============================================================================
# Bug #1: Position Size USD→Coins Konvertierung
# ============================================================================


@pytest.mark.unit
def test_bug1_position_size_returns_coins_not_usd(risk_manager, sample_signal):
    """
    Bug #1 Fix: calculate_position_size() sollte COINS zurückgeben, nicht USD

    Gegeben: BTC @ 45000, confidence=0.85, balance=10000, max_position=10%
    Wenn: Position Size berechnet wird
    Dann: Ergebnis ist 0.01889 BTC (nicht 850 USD)
    """
    # Arrange
    expected_usd = 10000 * 0.10 * 0.85  # 850 USD
    expected_btc = expected_usd / 45000  # 0.01889 BTC

    # Act
    result = risk_manager.calculate_position_size(sample_signal)

    # Assert
    assert abs(result - expected_btc) < 0.0001, (
        f"Position size sollte {expected_btc:.6f} BTC sein, nicht {result:.6f}"
    )
    # Verify it's NOT returning USD
    assert result < 1.0, "Position size sollte BTC sein (<1), nicht USD (>100)"

    # Verify position value
    position_value = result * sample_signal.price
    assert abs(position_value - expected_usd) < 0.01, (
        f"Position value sollte {expected_usd:.2f} USD sein"
    )


@pytest.mark.unit
def test_bug1_zero_price_returns_zero(risk_manager, sample_signal):
    """Bug #1 Fix: Sollte 0.0 zurückgeben bei ungültigem Preis"""
    # Arrange
    sample_signal.price = 0.0

    # Act
    result = risk_manager.calculate_position_size(sample_signal)

    # Assert
    assert result == 0.0, "Ungültiger Preis sollte zu 0.0 Position führen"


# ============================================================================
# Bug #2: Position Limit Check
# ============================================================================


@pytest.mark.unit
def test_bug2_position_limit_check_validates_actual_size(risk_manager, sample_signal):
    """
    Bug #2 Fix: check_position_limit() sollte tatsächliche Position-Size prüfen

    Gegeben: Signal mit zu großer Confidence (2.5)
    Wenn: Position Limit geprüft wird
    Dann: Signal wird blockiert (Position > Limit)
    """
    # Arrange
    sample_signal.confidence = 2.5  # Absurd hohe Confidence

    # Act
    approved, reason = risk_manager.check_position_limit(sample_signal)

    # Assert
    assert approved is False, "Signal sollte blockiert sein (Position > Limit)"
    assert "zu groß" in reason.lower(), f"Reason sollte 'zu groß' enthalten: {reason}"


@pytest.mark.unit
def test_bug2_position_limit_approves_normal_size(risk_manager, sample_signal):
    """Bug #2 Fix: Normale Position sollte approved werden"""
    # Arrange
    sample_signal.confidence = 0.85  # Normale Confidence

    # Act
    approved, reason = risk_manager.check_position_limit(sample_signal)

    # Assert
    assert approved is True, f"Signal sollte approved sein: {reason}"
    assert "OK" in reason, f"Reason sollte 'OK' enthalten: {reason}"


# ============================================================================
# Bug #3: Exposure Check für Future Exposure
# ============================================================================


@pytest.mark.unit
def test_bug3_exposure_check_blocks_future_overflow(risk_manager, sample_signal, clean_risk_state):
    """
    Bug #3 Fix: check_exposure_limit() sollte FUTURE exposure prüfen

    Gegeben: Aktuelle Exposure = 4800 USD (96% vom 5000 Limit)
    Wenn: Neues Signal kommt (850 USD)
    Dann: Signal wird blockiert (Future: 5650 > 5000)
    """
    # Arrange
    clean_risk_state.total_exposure = 4800.0  # 96% vom 5000 USD Limit

    # Act
    approved, reason = risk_manager.check_exposure_limit(sample_signal)

    # Assert
    assert approved is False, "Signal sollte blockiert sein (Future Exposure > Limit)"
    assert "überschritten" in reason.lower(), f"Reason sollte 'überschritten' enthalten: {reason}"
    assert "4800" in reason, "Reason sollte aktuelle Exposure enthalten"


@pytest.mark.unit
def test_bug3_exposure_check_approves_within_limit(risk_manager, sample_signal, clean_risk_state):
    """Bug #3 Fix: Signal sollte approved werden wenn Future Exposure OK ist"""
    # Arrange
    clean_risk_state.total_exposure = 2000.0  # 40% vom 5000 USD Limit

    # Act
    approved, reason = risk_manager.check_exposure_limit(sample_signal)

    # Assert
    assert approved is True, f"Signal sollte approved sein: {reason}"
    assert "OK" in reason, f"Reason sollte 'OK' enthalten: {reason}"


# ============================================================================
# Bug #4: Daily P&L Tracking
# ============================================================================


@pytest.mark.unit
def test_bug4_pnl_updates_after_trade(risk_manager, clean_risk_state):
    """
    Bug #4 Fix: _update_pnl() sollte daily_pnl berechnen

    Gegeben: BTC Position @ 44000 Entry, jetzt @ 45000
    Wenn: P&L aktualisiert wird
    Dann: daily_pnl = 0.5 BTC * (45000 - 44000) = 500 USD
    """
    # Arrange
    clean_risk_state.positions["BTCUSDT"] = 0.5
    clean_risk_state.entry_prices["BTCUSDT"] = 44000.0
    clean_risk_state.last_prices["BTCUSDT"] = 45000.0
    clean_risk_state.position_sides["BTCUSDT"] = "BUY"
    clean_risk_state.realized_pnl_today = 0.0

    # Act
    risk_manager._update_pnl()

    # Assert
    expected_pnl = 0.5 * (45000 - 44000)  # 500 USD
    assert abs(clean_risk_state.daily_pnl - expected_pnl) < 0.01, (
        f"Daily P&L sollte {expected_pnl:.2f} sein, ist {clean_risk_state.daily_pnl:.2f}"
    )


@pytest.mark.unit
def test_bug4_pnl_includes_realized_and_unrealized(risk_manager, clean_risk_state):
    """Bug #4 Fix: Daily P&L sollte Realized + Unrealized sein"""
    # Arrange
    # Offene Position: BTC @ 44000 Entry, jetzt @ 45000
    clean_risk_state.positions["BTCUSDT"] = 0.5
    clean_risk_state.entry_prices["BTCUSDT"] = 44000.0
    clean_risk_state.last_prices["BTCUSDT"] = 45000.0
    clean_risk_state.position_sides["BTCUSDT"] = "BUY"

    # Geschlossene Position heute: +150 USD
    clean_risk_state.realized_pnl_today = 150.0

    # Act
    risk_manager._update_pnl()

    # Assert
    unrealized = 0.5 * (45000 - 44000)  # 500 USD
    expected_total = 150 + unrealized  # 650 USD
    assert abs(clean_risk_state.daily_pnl - expected_total) < 0.01, (
        f"Daily P&L sollte {expected_total:.2f} sein (realized + unrealized)"
    )


@pytest.mark.unit
def test_bug4_circuit_breaker_triggers_on_drawdown(risk_manager, sample_signal, clean_risk_state):
    """
    Bug #4 Fix: Circuit Breaker sollte bei -5% Drawdown aktivieren

    Gegeben: Daily P&L = -600 USD (< -500 Limit bei 10k Balance)
    Wenn: Drawdown-Check durchgeführt wird
    Dann: Circuit Breaker aktiviert, Signal blockiert
    """
    # Arrange
    clean_risk_state.daily_pnl = -600.0  # -6% vom 10k Balance

    # Act
    approved, reason = risk_manager.check_drawdown_limit()

    # Assert
    assert approved is False, "Signal sollte blockiert sein (Drawdown > Limit)"
    assert clean_risk_state.circuit_breaker_active is True, "Circuit Breaker sollte aktiv sein"
    assert "circuit breaker" in reason.lower(), f"Reason sollte 'circuit breaker' enthalten: {reason}"


@pytest.mark.unit
def test_bug4_exposure_update_tracks_entry_price(risk_manager, clean_risk_state):
    """Bug #4 Fix: _update_exposure() sollte Entry-Price speichern"""
    # Arrange
    order_result = OrderResult(
        order_id="TEST_001",
        status="FILLED",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.5,
        filled_quantity=0.5,
        price=45000.0,
        timestamp=1700000000,
        type="order_result"
    )

    # Act
    risk_manager._update_exposure(order_result)

    # Assert
    assert "BTCUSDT" in clean_risk_state.entry_prices, "Entry price sollte gespeichert sein"
    assert clean_risk_state.entry_prices["BTCUSDT"] == 45000.0
    assert clean_risk_state.position_sides["BTCUSDT"] == "BUY"


@pytest.mark.unit
def test_bug4_exposure_update_calculates_realized_pnl(risk_manager, clean_risk_state):
    """Bug #4 Fix: _update_exposure() sollte Realized P&L bei Position-Close berechnen"""
    # Arrange - Open position
    clean_risk_state.positions["BTCUSDT"] = 0.5
    clean_risk_state.entry_prices["BTCUSDT"] = 44000.0
    clean_risk_state.position_sides["BTCUSDT"] = "BUY"

    # Close position @ 45000
    order_result = OrderResult(
        order_id="TEST_002",
        status="FILLED",
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.5,
        filled_quantity=0.5,
        price=45000.0,
        timestamp=1700000000,
        type="order_result"
    )

    # Act
    risk_manager._update_exposure(order_result)

    # Assert
    expected_realized = 0.5 * (45000 - 44000)  # 500 USD
    assert abs(clean_risk_state.realized_pnl_today - expected_realized) < 0.01, (
        f"Realized P&L sollte {expected_realized:.2f} sein"
    )
    assert "BTCUSDT" not in clean_risk_state.positions, "Position sollte geschlossen sein"


# ============================================================================
# Integration Test: Full Signal Processing
# ============================================================================


@pytest.mark.integration
def test_integration_signal_processing_with_all_fixes(risk_manager, sample_signal, clean_risk_state):
    """
    Integration Test: Vollständige Signal-Verarbeitung mit allen Fixes

    Testet, dass alle 4 Bugs zusammen funktionieren:
    1. Position Size in Coins berechnet
    2. Position Limit Check funktioniert
    3. Exposure Check prüft Future
    4. P&L Tracking funktioniert
    """
    # Act
    order = risk_manager.process_signal(sample_signal)

    # Assert
    assert order is not None, "Signal sollte approved werden"

    # Check Bug #1: Quantity ist in Coins
    assert order.quantity < 1.0, "Quantity sollte in BTC sein, nicht USD"
    expected_qty = (10000 * 0.10 * 0.85) / 45000
    assert abs(order.quantity - expected_qty) < 0.0001, "Quantity sollte korrekt berechnet sein"

    # Check Bug #2 & #3: Position und Exposure Limits wurden geprüft
    assert clean_risk_state.signals_approved == 1, "Signal sollte als approved gezählt sein"
    assert clean_risk_state.signals_blocked == 0, "Keine Signals sollten blockiert sein"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
