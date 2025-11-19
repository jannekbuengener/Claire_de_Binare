"""
Golden Run Tests - Proof of Concept
Deterministischer Replay mit State-Hashing

Basierend auf Research: backoffice/docs/architecture/EVENT_SOURCING_RESEARCH.md
"""
import pytest
import hashlib
import json
from typing import List, Dict, Any
from backoffice.services.common import BaseEvent, ClockEvent, RiskDecisionEvent


def hash_state(state: Dict[str, Any]) -> str:
    """
    Hasht einen State deterministisch mit SHA256.

    Args:
        state: Dictionary mit State-Daten

    Returns:
        SHA256-Hash als Hex-String
    """
    # Sortierte Keys für Determinismus
    normalized = json.dumps(state, sort_keys=True)
    return hashlib.sha256(normalized.encode()).hexdigest()


def replay_events(events: List[BaseEvent]) -> Dict[str, Any]:
    """
    Replayed Events und rebuildet den State.

    Args:
        events: Liste von Events

    Returns:
        Finaler State nach Replay
    """
    state = {
        "total_events": 0,
        "approved_signals": 0,
        "rejected_signals": 0,
        "total_position_size": 0.0,
        "event_types": {},
    }

    for event in events:
        state["total_events"] += 1

        # Event-Type zählen
        event_type = event.event_type
        state["event_types"][event_type] = state["event_types"].get(event_type, 0) + 1

        # Spezielle Logik für RiskDecision
        if isinstance(event, RiskDecisionEvent):
            if event.approved:
                state["approved_signals"] += 1
                state["total_position_size"] += event.position_size
            else:
                state["rejected_signals"] += 1

    return state


# ===== TESTS =====


@pytest.mark.unit
def test_hash_state_is_deterministic():
    """Test: State-Hashing ist deterministisch"""
    state = {"a": 1, "b": 2, "c": 3}

    # Mehrfaches Hashen sollte gleiche Hashes ergeben
    hash1 = hash_state(state)
    hash2 = hash_state(state)

    assert hash1 == hash2


@pytest.mark.unit
def test_hash_state_ignores_key_order():
    """Test: State-Hashing ignoriert Key-Reihenfolge"""
    state1 = {"a": 1, "b": 2, "c": 3}
    state2 = {"c": 3, "a": 1, "b": 2}  # Andere Reihenfolge

    hash1 = hash_state(state1)
    hash2 = hash_state(state2)

    assert hash1 == hash2, "Hash sollte unabhängig von Key-Reihenfolge sein"


@pytest.mark.unit
def test_hash_state_detects_changes():
    """Test: State-Hashing erkennt Änderungen"""
    state1 = {"a": 1, "b": 2}
    state2 = {"a": 1, "b": 3}  # b geändert

    hash1 = hash_state(state1)
    hash2 = hash_state(state2)

    assert hash1 != hash2, "Hash sollte sich bei Änderungen unterscheiden"


@pytest.mark.unit
def test_replay_events_rebuilds_state():
    """Test: Replay rebuildet State korrekt"""
    # Arrange: Events erstellen
    events = [
        RiskDecisionEvent(
            signal_id="sig1",
            approved=True,
            position_size=0.5,
            source="cdb_risk",
        ),
        RiskDecisionEvent(
            signal_id="sig2",
            approved=False,
            reason="max_exposure_reached",
            source="cdb_risk",
        ),
        RiskDecisionEvent(
            signal_id="sig3",
            approved=True,
            position_size=0.3,
            source="cdb_risk",
        ),
    ]

    # Act: Replay
    state = replay_events(events)

    # Assert
    assert state["total_events"] == 3
    assert state["approved_signals"] == 2
    assert state["rejected_signals"] == 1
    assert abs(state["total_position_size"] - 0.8) < 0.01


@pytest.mark.unit
def test_golden_run_pattern():
    """
    Test: Golden Run Pattern (Proof-of-Concept)

    Workflow:
    1. Golden Run: Events erstellen, Replay, Hash speichern
    2. Regression Test: Gleiche Events replayed, Hash vergleichen
    """
    # ===== GOLDEN RUN =====
    golden_events = [
        ClockEvent(current_time=1700000000000, source="system_clock"),
        RiskDecisionEvent(
            signal_id="sig1",
            approved=True,
            position_size=0.5,
            stop_price=48000.0,
            source="cdb_risk",
        ),
        ClockEvent(current_time=1700000001000, source="system_clock"),
        RiskDecisionEvent(
            signal_id="sig2",
            approved=False,
            reason="max_daily_drawdown_exceeded",
            source="cdb_risk",
        ),
    ]

    golden_state = replay_events(golden_events)
    golden_hash = hash_state(golden_state)

    # Golden Run speichern (simuliert)
    golden_run = {
        "run_id": "2025-01-15_production",
        "total_events": len(golden_events),
        "final_state_hash": golden_hash,
        "snapshots": {
            "after_event_2": hash_state(replay_events(golden_events[:2])),
            "after_event_4": hash_state(replay_events(golden_events[:4])),
        },
    }

    # ===== REGRESSION TEST =====
    # Replay mit gleichen Events
    replay_state = replay_events(golden_events)
    replay_hash = hash_state(replay_state)

    # Assert: Replay sollte exakt gleichen Hash ergeben
    assert replay_hash == golden_run["final_state_hash"]
    assert replay_hash == golden_hash


@pytest.mark.unit
def test_golden_run_detects_code_changes():
    """Test: Golden Run erkennt Code-Änderungen"""
    # Original Events
    events = [
        RiskDecisionEvent(
            signal_id="sig1",
            approved=True,
            position_size=0.5,
            source="cdb_risk",
        ),
    ]

    # Original Replay
    original_state = replay_events(events)
    original_hash = hash_state(original_state)

    # Simuliere Code-Änderung: State wird anders berechnet
    modified_state = original_state.copy()
    modified_state["total_position_size"] = 1.0  # Bug eingeführt

    modified_hash = hash_state(modified_state)

    # Assert: Hashes sollten sich unterscheiden
    assert original_hash != modified_hash, "Code-Änderung wurde erkannt"


@pytest.mark.unit
def test_clock_event_determinism():
    """Test: ClockEvent ermöglicht deterministisches Timing"""
    # Arrange: Fixe Timestamps (wie in Backtest)
    clock1 = ClockEvent(current_time=1700000000000, source="backtest")
    clock2 = ClockEvent(current_time=1700000001000, source="backtest")

    # Act: Mehrfaches Erstellen sollte gleiche Timestamps geben
    events = [clock1, clock2]
    state = replay_events(events)
    hash1 = hash_state(state)

    # Replay
    events_replay = [clock1, clock2]
    state_replay = replay_events(events_replay)
    hash2 = hash_state(state_replay)

    # Assert: Hashes sollten gleich sein (Determinismus)
    assert hash1 == hash2


@pytest.mark.unit
def test_event_serialization_roundtrip():
    """Test: Events können zu/von Dictionary konvertiert werden"""
    # Arrange
    original = RiskDecisionEvent(
        event_id="test-uuid",
        signal_id="sig1",
        approved=True,
        position_size=0.5,
        stop_price=48000.0,
        source="cdb_risk",
        sequence_id=123,
        correlation_id="corr-123",
        causation_id="cause-456",
    )

    # Act: to_dict → from_dict
    data = original.to_dict()
    restored = RiskDecisionEvent.from_dict(data)

    # Assert: Alle Felder sollten gleich sein
    assert restored.event_id == original.event_id
    assert restored.signal_id == original.signal_id
    assert restored.approved == original.approved
    assert restored.position_size == original.position_size
    assert restored.stop_price == original.stop_price
    assert restored.source == original.source
    assert restored.sequence_id == original.sequence_id
    assert restored.correlation_id == original.correlation_id
    assert restored.causation_id == original.causation_id


@pytest.mark.unit
def test_correlation_id_tracks_end_to_end_flow():
    """Test: correlation_id bleibt über gesamten Flow gleich"""
    correlation_id = "flow-12345"

    # MarketData → Signal → RiskDecision → Order
    # Alle sollten gleiche correlation_id haben

    events = [
        BaseEvent(
            event_type="market_data",
            correlation_id=correlation_id,
            source="cdb_screener",
        ),
        BaseEvent(
            event_type="signal",
            correlation_id=correlation_id,
            causation_id="event-1",
            source="cdb_signal",
        ),
        RiskDecisionEvent(
            signal_id="sig1",
            approved=True,
            position_size=0.5,
            correlation_id=correlation_id,
            causation_id="event-2",
            source="cdb_risk",
        ),
    ]

    # Assert: Alle Events haben gleiche correlation_id
    for event in events:
        assert event.correlation_id == correlation_id
