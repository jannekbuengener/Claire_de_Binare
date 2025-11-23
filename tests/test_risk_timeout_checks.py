"""
Timeout-Check Tests für Risk Engine (Layer 7).

Diese Tests validieren die Data-Freshness-Validierung:
- Stale Data (>60s) blockiert Trade
- Fresh Data (<60s) erlaubt Trade
- Invalid Timestamps werden abgelehnt

Sprint 2 - Risk-Engine Hardening
"""

import pytest
from datetime import datetime, timedelta, timezone
from services.risk_engine import evaluate_signal_v2, EnhancedRiskDecision


@pytest.fixture
def standard_risk_config():
    """Standard Risk-Config mit Timeout."""
    return {
        "ACCOUNT_EQUITY": 100000.0,
        "MAX_POSITION_PCT": 0.10,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,
        "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.10,
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "DATA_STALE_TIMEOUT_SEC": 60,  # 60s Timeout
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
def clean_risk_state():
    """Clean Risk State (no losses)."""
    return {
        "equity": 100000.0,
        "daily_pnl": 0.0,
        "total_exposure_pct": 0.0,
    }


@pytest.mark.unit
def test_stale_data_blocks_trade_at_61_seconds(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Stale Data (61s) blockiert Trade.

    Gegeben: Signal timestamp ist 61s alt (über 60s Timeout)
    Wenn: Signal wird evaluiert
    Dann: Signal wird blockiert (approved=False)
    """
    # Arrange
    old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": old_timestamp,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert isinstance(decision, EnhancedRiskDecision)
    assert decision.approved is False, "Stale Data (61s) sollte blockiert werden"
    assert "stale_data" in decision.reason
    assert decision.position_size == 0.0


@pytest.mark.unit
def test_stale_data_blocks_trade_at_120_seconds(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Sehr alte Data (120s) blockiert Trade.

    Gegeben: Signal timestamp ist 120s alt
    Wenn: Signal wird evaluiert
    Dann: Signal wird blockiert
    """
    # Arrange
    old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": old_timestamp,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert decision.approved is False
    assert "stale_data" in decision.reason
    assert "age=120s" in decision.reason or "age=119s" in decision.reason  # Allow 1s tolerance


@pytest.mark.unit
def test_fresh_data_allows_trade_at_30_seconds(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Fresh Data (30s) erlaubt Trade.

    Gegeben: Signal timestamp ist 30s alt (unter 60s Timeout)
    Wenn: Signal wird evaluiert
    Dann: Timeout-Check passiert (andere Checks können noch blockieren)
    """
    # Arrange
    fresh_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": fresh_timestamp,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    # Timeout-Check sollte NICHT die Ursache sein
    assert "stale_data" not in (decision.reason or ""), (
        "Timeout-Check sollte bei 30s NICHT triggern"
    )
    # Hinweis: Signal kann trotzdem rejected werden durch andere Checks


@pytest.mark.unit
def test_very_fresh_data_allows_trade_at_5_seconds(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Sehr fresh Data (5s) erlaubt Trade.

    Gegeben: Signal timestamp ist 5s alt
    Wenn: Signal wird evaluiert
    Dann: Timeout-Check passiert
    """
    # Arrange
    very_fresh_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": very_fresh_timestamp,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert "stale_data" not in (decision.reason or "")


@pytest.mark.unit
def test_signal_without_timestamp_passes_timeout_check(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Signal ohne Timestamp passiert Timeout-Check.

    Gegeben: Signal hat KEIN timestamp Feld
    Wenn: Signal wird evaluiert
    Dann: Timeout-Check wird übersprungen (andere Checks greifen)
    """
    # Arrange
    signal_no_timestamp = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        # NO timestamp field!
    }

    # Act
    decision = evaluate_signal_v2(
        signal_no_timestamp, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    # Timeout-Check sollte übersprungen werden
    assert "stale_data" not in (decision.reason or "")
    # Hinweis: Signal kann durch andere Checks rejected werden


@pytest.mark.unit
def test_invalid_timestamp_format_rejected(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Invalid Timestamp Format wird abgelehnt.

    Gegeben: Signal mit invalider Timestamp-Syntax
    Wenn: Signal wird evaluiert
    Dann: Signal wird blockiert (invalid_timestamp_format)
    """
    # Arrange
    signal_invalid_ts = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": "NOT_A_VALID_TIMESTAMP",
    }

    # Act
    decision = evaluate_signal_v2(
        signal_invalid_ts, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert decision.approved is False
    assert decision.reason == "invalid_timestamp_format"
    assert decision.position_size == 0.0


@pytest.mark.unit
def test_timeout_check_respects_custom_timeout(
    standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Timeout-Check respektiert custom DATA_STALE_TIMEOUT_SEC.

    Gegeben: Custom timeout = 30s (statt 60s)
    Wenn: Signal mit 45s Alter evaluiert wird
    Dann: Signal wird blockiert (da 45s > 30s)
    """
    # Arrange
    custom_config = {
        "ACCOUNT_EQUITY": 100000.0,
        "MAX_POSITION_PCT": 0.10,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,
        "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.10,
        "MAX_TOTAL_EXPOSURE_PCT": 0.30,
        "DATA_STALE_TIMEOUT_SEC": 30,  # Custom: 30s statt 60s
        "SIZING_METHOD": "fixed_fractional",
    }

    timestamp_45s_old = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": timestamp_45s_old,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, custom_config, standard_market_conditions
    )

    # Assert
    assert decision.approved is False
    assert "stale_data" in decision.reason
    assert "age=45s" in decision.reason or "age=44s" in decision.reason


@pytest.mark.unit
def test_timezone_aware_timestamp_works(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Timezone-aware Timestamps funktionieren korrekt.

    Gegeben: Signal mit UTC+00:00 Timezone
    Wenn: Signal wird evaluiert (40s alt)
    Dann: Timeout-Check passiert
    """
    # Arrange
    tz_aware_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=40)).isoformat()

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": tz_aware_timestamp,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert "stale_data" not in (decision.reason or "")


@pytest.mark.unit
def test_timestamp_with_z_suffix_works(
    standard_risk_config, standard_market_conditions, clean_risk_state
):
    """
    Layer 7: Timestamps mit 'Z' Suffix (Zulu Time) funktionieren.

    Gegeben: Signal mit timestamp = "2025-01-01T12:00:00Z"
    Wenn: Signal wird evaluiert
    Dann: Timestamp wird korrekt geparsed
    """
    # Arrange
    # 50s ago with Z suffix
    z_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=50)).strftime("%Y-%m-%dT%H:%M:%SZ")

    signal = {
        "symbol": "BTCUSDT",
        "signal_type": "long",
        "side": "long",
        "price": 50000.0,
        "target_position_usd": 5000.0,
        "timestamp": z_timestamp,
    }

    # Act
    decision = evaluate_signal_v2(
        signal, clean_risk_state, standard_risk_config, standard_market_conditions
    )

    # Assert
    assert "stale_data" not in (decision.reason or "")
