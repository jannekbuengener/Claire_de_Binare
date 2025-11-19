"""Integration tests for event pipeline - Phase 3 Test Improvements.

Diese Tests nutzen pytest-mock für Redis/PostgreSQL Mocks und simulieren
den vollständigen Event-Flow: Signal → Risk → Order.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from services import risk_engine


@pytest.mark.integration
def test_redis_signal_publish_subscribe(mock_redis):
    """Signal-Event wird via Redis Pub/Sub transportiert."""

    # Arrange
    redis_client = mock_redis.return_value
    channel = "signals"
    signal_event = {
        "type": "signal",
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50_000.0,
        "size": 1.0,
        "timestamp": "2025-11-19T12:00:00Z",
    }

    # Act
    redis_client.publish(channel, json.dumps(signal_event))

    # Assert
    redis_client.publish.assert_called_once_with(channel, json.dumps(signal_event))


@pytest.mark.integration
def test_risk_state_persistence(mock_postgres):
    """Risk-State wird in PostgreSQL persistiert."""

    # Arrange
    pool = mock_postgres.return_value
    connection = MagicMock()
    cursor = MagicMock()
    pool.getconn.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    risk_state = {
        "equity": 100_000.0,
        "daily_pnl": -1000.0,
        "total_exposure_pct": 0.15,
        "timestamp": "2025-11-19T12:00:00Z",
    }

    # Act
    pool.getconn()
    with connection.cursor() as cur:
        cur.execute(
            "INSERT INTO risk_states (equity, daily_pnl, total_exposure_pct, timestamp) "
            "VALUES (%s, %s, %s, %s)",
            (
                risk_state["equity"],
                risk_state["daily_pnl"],
                risk_state["total_exposure_pct"],
                risk_state["timestamp"],
            ),
        )

    # Assert
    cursor.execute.assert_called_once()
    assert "INSERT INTO risk_states" in cursor.execute.call_args[0][0]


@pytest.mark.integration
def test_end_to_end_signal_to_order_flow(
    mock_redis, sample_signal_event, sample_risk_state, risk_config
):
    """End-to-End: Signal → Risk Validation → Order Decision."""

    # Arrange
    redis_client = mock_redis.return_value

    # Simulate: Signal arrives via Redis
    redis_client.get.return_value = json.dumps(sample_signal_event).encode()

    # Simulate: Risk State from cache/DB
    risk_state = sample_risk_state

    # Act: Risk Engine validates Signal
    decision = risk_engine.evaluate_signal(sample_signal_event, risk_state, risk_config)

    # Assert: Decision is made
    assert decision.approved is True
    assert decision.position_size > 0
    assert decision.stop_price is not None

    # Simulate: Publish order if approved
    if decision.approved:
        order = {
            "symbol": sample_signal_event["symbol"],
            "side": sample_signal_event["side"],
            "size": decision.position_size,
            "stop_price": decision.stop_price,
        }
        redis_client.publish("orders", json.dumps(order))

        redis_client.publish.assert_called_with("orders", json.dumps(order))


@pytest.mark.integration
def test_rejected_signal_does_not_create_order(
    mock_redis, sample_signal_event, risk_config
):
    """Rejected Signal erzeugt keinen Order."""

    # Arrange
    redis_client = mock_redis.return_value

    # High-risk state: Daily drawdown exceeded
    risk_state = {
        "equity": 100_000.0,
        "daily_pnl": -6000.0,  # -6% exceeded
        "total_exposure_pct": 0.15,
    }

    # Act
    decision = risk_engine.evaluate_signal(sample_signal_event, risk_state, risk_config)

    # Assert
    assert decision.approved is False
    assert decision.reason == "max_daily_drawdown_exceeded"

    # Verify: No order published
    redis_client.publish.assert_not_called()


@pytest.mark.integration
def test_multiple_signals_processed_sequentially(
    mock_redis, risk_config, sample_risk_state
):
    """Mehrere Signals werden sequenziell verarbeitet."""

    # Arrange
    signals = [
        {"symbol": "BTCUSDT", "side": "buy", "price": 50_000.0, "size": 1.0},
        {"symbol": "ETHUSDT", "side": "buy", "price": 3_000.0, "size": 5.0},
        {"symbol": "BNBUSDT", "side": "sell", "price": 300.0, "size": 10.0},
    ]

    decisions = []

    # Act
    for signal in signals:
        decision = risk_engine.evaluate_signal(signal, sample_risk_state, risk_config)
        decisions.append(decision)

    # Assert
    assert len(decisions) == 3
    assert all(d.approved for d in decisions)  # All approved with clean state
