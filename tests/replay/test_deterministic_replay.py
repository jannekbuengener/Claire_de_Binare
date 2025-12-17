"""
Replay-Tests für deterministische Event-Sourcing.
Governance: CDB_PSM_POLICY.md (Deterministische Replays)
"""

import pytest
from datetime import datetime, timezone

from core.utils.clock import FixedClock
from core.utils.seed import SeedManager
from core.utils.uuid_gen import UUIDGenerator
from core.domain.event import Event


@pytest.mark.unit
def test_fixed_clock_determinism():
    """Test: FixedClock liefert immer dieselbe Zeit."""
    fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    clock = FixedClock(fixed_time)

    # Mehrfache Calls liefern identische Zeit
    time1 = clock.now()
    time2 = clock.now()
    time3 = clock.now()

    assert time1 == time2 == time3 == fixed_time


@pytest.mark.unit
def test_seed_manager_determinism():
    """Test: Gleicher Seed → Identische Zufallszahlen."""
    seed = 42

    manager1 = SeedManager(seed)
    manager2 = SeedManager(seed)

    # Gleiche Sequenz von Zufallszahlen
    seq1 = [manager1.random_int() for _ in range(10)]
    seq2 = [manager2.random_int() for _ in range(10)]

    assert seq1 == seq2


@pytest.mark.unit
def test_uuid_generator_determinism():
    """Test: Gleicher Seed → Identische UUIDs."""
    seed = 42

    gen1 = UUIDGenerator(seed)
    gen2 = UUIDGenerator(seed)

    # Generiere UUIDs
    uuids1 = [gen1.generate() for _ in range(5)]
    uuids2 = [gen2.generate() for _ in range(5)]

    assert uuids1 == uuids2


@pytest.mark.unit
def test_event_hash_consistency():
    """Test: Gleiche Events → Gleiche Hashes."""
    timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    payload = {"symbol": "BTCUSDT", "price": "50000.00"}

    event1 = Event.create("TradeExecuted", payload, timestamp, event_id="test-123")
    event2 = Event.create("TradeExecuted", payload, timestamp, event_id="test-123")

    assert event1.compute_hash() == event2.compute_hash()


@pytest.mark.unit
def test_event_replay_determinism():
    """
    Test: Event-Replay mit FixedClock + Deterministic UUID → Identischer State.

    Governance: CDB_PSM_POLICY.md (Deterministische Replays)
    """
    # Setup: Fixed Clock + UUID Generator
    fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    clock = FixedClock(fixed_time)
    uuid_gen = UUIDGenerator(seed=42)

    # Erstelle Events
    events_run1 = []
    for i in range(3):
        event = Event.create(
            event_type="TradeExecuted",
            payload={"symbol": "BTCUSDT", "price": f"{50000 + i * 100}"},
            timestamp=clock.now(),
            event_id=str(uuid_gen.generate()),
            sequence_number=i,
        )
        events_run1.append(event)

    # Replay: Gleiche Clock + UUID Generator
    clock2 = FixedClock(fixed_time)
    uuid_gen2 = UUIDGenerator(seed=42)

    events_run2 = []
    for i in range(3):
        event = Event.create(
            event_type="TradeExecuted",
            payload={"symbol": "BTCUSDT", "price": f"{50000 + i * 100}"},
            timestamp=clock2.now(),
            event_id=str(uuid_gen2.generate()),
            sequence_number=i,
        )
        events_run2.append(event)

    # Assert: Identische Events
    assert len(events_run1) == len(events_run2)
    for e1, e2 in zip(events_run1, events_run2):
        assert e1.event_id == e2.event_id
        assert e1.event_type == e2.event_type
        assert e1.timestamp == e2.timestamp
        assert e1.payload == e2.payload
        assert e1.compute_hash() == e2.compute_hash()
