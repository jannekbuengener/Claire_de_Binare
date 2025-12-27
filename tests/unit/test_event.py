"""Unit tests for core.domain.event module."""

import pytest
from datetime import datetime, timezone

from core.domain.event import Event, EventType


@pytest.mark.unit
def test_event_creation():
    """Test Event model creation."""
    event = Event(
        event_id="evt_001",
        event_type=EventType.SIGNAL_GENERATED,
        payload={"signal_id": "sig_001"},
        timestamp=1000.0,
    )
    assert event.event_id == "evt_001"
    assert event.event_type == EventType.SIGNAL_GENERATED
    assert event.payload["signal_id"] == "sig_001"


@pytest.mark.unit
def test_event_type_enum():
    """Test EventType enum values."""
    assert hasattr(EventType, "SIGNAL_GENERATED")
    assert hasattr(EventType, "ORDER_PLACED")
    assert hasattr(EventType, "POSITION_OPENED")


@pytest.mark.unit
def test_event_id_deterministic_for_same_payload():
    """Event IDs should be deterministic for identical payloads."""
    timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    payload = {"price": "50000.00", "symbol": "BTCUSDT"}

    event1 = Event.create(
        event_type="TradeExecuted",
        payload=payload,
        timestamp=timestamp,
        stream_id="stream-1",
        sequence_number=1,
    )
    event2 = Event.create(
        event_type="TradeExecuted",
        payload=payload,
        timestamp=timestamp,
        stream_id="stream-1",
        sequence_number=1,
    )

    assert event1.event_id == event2.event_id


@pytest.mark.unit
def test_event_id_changes_on_payload_change():
    """Event IDs should change when payload content changes."""
    timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    payload_a = {"price": "50000.00", "symbol": "BTCUSDT"}
    payload_b = {"price": "50100.00", "symbol": "BTCUSDT"}

    event_a = Event.create(
        event_type="TradeExecuted",
        payload=payload_a,
        timestamp=timestamp,
        stream_id="stream-1",
        sequence_number=1,
    )
    event_b = Event.create(
        event_type="TradeExecuted",
        payload=payload_b,
        timestamp=timestamp,
        stream_id="stream-1",
        sequence_number=1,
    )

    assert event_a.event_id != event_b.event_id
