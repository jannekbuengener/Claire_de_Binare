"""Unit tests for core.domain.event module."""
import pytest
from core.domain.event import Event, EventType


def test_event_creation():
    """Test Event model creation."""
    event = Event(
        event_id="evt_001",
        event_type=EventType.SIGNAL_GENERATED,
        payload={"signal_id": "sig_001"},
        timestamp=1000.0
    )
    assert event.event_id == "evt_001"
    assert event.event_type == EventType.SIGNAL_GENERATED
    assert event.payload["signal_id"] == "sig_001"


def test_event_type_enum():
    """Test EventType enum values."""
    assert hasattr(EventType, "SIGNAL_GENERATED")
    assert hasattr(EventType, "ORDER_PLACED")
    assert hasattr(EventType, "POSITION_OPENED")
