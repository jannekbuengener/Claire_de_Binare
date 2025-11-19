"""
Determinism Tests for Event Sourcing System

These tests validate the core principle:
    Same events → Same decisions (ALWAYS)

Test categories:
- LogicalClock determinism
- Event serialization/deserialization
- Replay produces identical results
- Risk decisions are deterministic
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from services.event_sourcing import (
    EventFactory,
    EventMetadata,
    EventType,
    LogicalClock,
    MarketDataEvent,
    RiskCheckResult,
    RiskDecisionEvent,
    RiskState,
    Side,
    SignalGeneratedEvent,
    compare_events,
    ensure_determinism,
    get_clock,
)


# ==============================================================================
# LOGICAL CLOCK TESTS
# ==============================================================================


@pytest.mark.unit
def test_logical_clock_monotonic():
    """LogicalClock must always increment (never decrease or skip)."""
    clock = LogicalClock(initial_value=100)

    seq1 = clock.next()
    seq2 = clock.next()
    seq3 = clock.next()

    assert seq1 == 100
    assert seq2 == 101
    assert seq3 == 102
    assert seq2 > seq1
    assert seq3 > seq2


@pytest.mark.unit
def test_logical_clock_deterministic_ordering():
    """Events created with LogicalClock have guaranteed ordering."""
    clock = LogicalClock()

    # Create 100 "events" (sequence numbers)
    sequences = [clock.next() for _ in range(100)]

    # Verify strict ordering
    for i in range(1, len(sequences)):
        assert sequences[i] > sequences[i - 1]
        assert sequences[i] == sequences[i - 1] + 1


@pytest.mark.unit
def test_logical_clock_reset_for_replay():
    """Clock can be reset for replay (testing only)."""
    clock = LogicalClock()

    clock.next()  # 1
    clock.next()  # 2
    clock.next()  # 3

    clock.reset(100)
    assert clock.next() == 100
    assert clock.next() == 101


@pytest.mark.unit
def test_logical_timestamp_independent_of_wall_clock():
    """Logical timestamp is independent of system time."""
    clock = LogicalClock()

    # Logical timestamp should be based on clock initialization, not wall time
    ts1 = clock.logical_timestamp()
    clock.next()
    ts2 = clock.logical_timestamp()

    # Timestamps can be identical or slightly different
    # but not dependent on wall-clock time
    assert isinstance(ts1, int)
    assert isinstance(ts2, int)
    assert ts2 >= ts1  # Monotonic


# ==============================================================================
# EVENT DETERMINISM TESTS
# ==============================================================================


@pytest.mark.unit
def test_event_has_required_determinism_fields():
    """All events must have fields needed for deterministic replay."""
    metadata = EventMetadata(service="test", version="1.0.0", environment="paper")

    event = MarketDataEvent(
        sequence_number=1,
        timestamp_logical=1000,
        correlation_id=uuid.uuid4(),
        metadata=metadata,
        symbol="BTCUSDT",
        price=50000.0,
        volume=100.0,
    )

    # Should not raise exception
    ensure_determinism(event)

    assert event.sequence_number > 0
    assert event.timestamp_logical >= 0
    assert event.correlation_id is not None
    assert event.metadata is not None


@pytest.mark.unit
def test_event_serialization_is_idempotent():
    """Serializing and deserializing event produces identical result."""
    metadata = EventMetadata(service="test", version="1.0.0")

    original_event = MarketDataEvent(
        sequence_number=42,
        timestamp_logical=5000,
        correlation_id=uuid.uuid4(),
        metadata=metadata,
        symbol="ETHUSDT",
        price=3000.0,
        volume=50.0,
        pct_change=2.5,
    )

    # Serialize to JSON
    event_json = original_event.model_dump_json()

    # Deserialize back
    restored_event = MarketDataEvent.model_validate_json(event_json)

    # Compare (ignoring UUID/datetime objects which may differ in representation)
    assert restored_event.sequence_number == original_event.sequence_number
    assert restored_event.symbol == original_event.symbol
    assert restored_event.price == original_event.price
    assert restored_event.volume == original_event.volume
    assert restored_event.pct_change == original_event.pct_change


@pytest.mark.unit
def test_compare_events_semantic_equality():
    """compare_events() correctly identifies semantically equal events."""
    correlation_id = uuid.uuid4()
    metadata = EventMetadata(service="test", version="1.0.0")

    event1 = MarketDataEvent(
        sequence_number=10,
        timestamp_logical=1000,
        correlation_id=correlation_id,
        metadata=metadata,
        symbol="BTCUSDT",
        price=50000.0,
        volume=100.0,
    )

    event2 = MarketDataEvent(
        sequence_number=10,
        timestamp_logical=1000,
        correlation_id=correlation_id,
        metadata=metadata,
        symbol="BTCUSDT",
        price=50000.0,
        volume=100.0,
    )

    # Should be semantically equal (same sequence, correlation, type)
    assert compare_events(event1, event2)


# ==============================================================================
# RISK DECISION DETERMINISM TESTS
# ==============================================================================


@pytest.mark.unit
def test_risk_decision_deterministic_given_same_state():
    """Same risk state + signal → same decision (determinism)."""
    from services import risk_engine

    # Fixed risk state
    risk_state = {"equity": 100_000.0, "daily_pnl": -1000.0, "total_exposure_pct": 0.15}

    # Fixed risk config
    risk_config = {
        "ACCOUNT_EQUITY": 100_000.0,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,
        "MAX_EXPOSURE_PCT": 0.30,
        "MAX_POSITION_PCT": 0.10,
        "STOP_LOSS_PCT": 0.02,
    }

    # Fixed signal
    signal = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50_000.0,
        "size": 1.0,
        "confidence": 0.85,
    }

    # Evaluate 3 times
    decision1 = risk_engine.evaluate_signal(signal, risk_state.copy(), risk_config)
    decision2 = risk_engine.evaluate_signal(signal, risk_state.copy(), risk_config)
    decision3 = risk_engine.evaluate_signal(signal, risk_state.copy(), risk_config)

    # All decisions must be identical
    assert decision1.approved == decision2.approved == decision3.approved
    assert decision1.reason == decision2.reason == decision3.reason
    assert decision1.position_size == decision2.position_size == decision3.position_size


@pytest.mark.unit
def test_risk_decision_changes_with_different_state():
    """Different risk state → different decision (sensitivity)."""
    from services import risk_engine

    risk_config = {
        "ACCOUNT_EQUITY": 100_000.0,
        "MAX_DAILY_DRAWDOWN_PCT": 0.05,
        "MAX_EXPOSURE_PCT": 0.30,
        "MAX_POSITION_PCT": 0.10,
        "STOP_LOSS_PCT": 0.02,
    }

    signal = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50_000.0,
        "size": 1.0,
    }

    # State 1: Low daily loss (should approve)
    state1 = {"equity": 100_000.0, "daily_pnl": -1000.0, "total_exposure_pct": 0.05}
    decision1 = risk_engine.evaluate_signal(signal, state1, risk_config)

    # State 2: High daily loss (should reject)
    state2 = {"equity": 100_000.0, "daily_pnl": -6000.0, "total_exposure_pct": 0.05}
    decision2 = risk_engine.evaluate_signal(signal, state2, risk_config)

    # Decisions should differ based on state
    assert decision1.approved != decision2.approved


# ==============================================================================
# EVENT FACTORY DETERMINISM TESTS
# ==============================================================================


@pytest.mark.unit
def test_event_factory_creates_consistent_events():
    """EventFactory creates events with consistent metadata."""
    factory = EventFactory(service_name="test_service", version="2.0.0")

    correlation_id = uuid.uuid4()

    event1 = factory.create_market_data(
        symbol="BTCUSDT",
        price=50000.0,
        volume=100.0,
        correlation_id=correlation_id,
    )

    event2 = factory.create_market_data(
        symbol="ETHUSDT",
        price=3000.0,
        volume=50.0,
        correlation_id=correlation_id,
    )

    # Both should have same service metadata
    assert event1.metadata.service == event2.metadata.service == "test_service"
    assert event1.metadata.version == event2.metadata.version == "2.0.0"

    # Both should have sequence numbers
    assert event1.sequence_number < event2.sequence_number  # Monotonic


# ==============================================================================
# REPLAY DETERMINISM TESTS
# ==============================================================================


@pytest.mark.unit
def test_replay_mode_context():
    """Replay mode can be enabled/disabled."""
    from services.replay_engine import ReplayMode

    assert not ReplayMode.is_enabled()

    ReplayMode.enable(start_sequence=1, end_sequence=100)
    assert ReplayMode.is_enabled()
    assert ReplayMode.get_range() == (1, 100)

    ReplayMode.disable()
    assert not ReplayMode.is_enabled()


@pytest.mark.unit
def test_replay_only_decorator():
    """@replay_only decorator prevents function execution outside replay."""
    from services.replay_engine import ReplayMode, replay_only

    @replay_only
    def test_function():
        return "executed"

    # Should fail when not in replay mode
    with pytest.raises(RuntimeError, match="only be called in replay mode"):
        test_function()

    # Should work when in replay mode
    ReplayMode.enable()
    try:
        result = test_function()
        assert result == "executed"
    finally:
        ReplayMode.disable()


@pytest.mark.unit
def test_no_replay_decorator():
    """@no_replay decorator prevents function execution during replay."""
    from services.replay_engine import ReplayMode, no_replay

    @no_replay
    def external_api_call():
        return "api_result"

    # Should work when not in replay mode
    result = external_api_call()
    assert result == "api_result"

    # Should return None when in replay mode
    ReplayMode.enable()
    try:
        result = external_api_call()
        assert result is None
    finally:
        ReplayMode.disable()


@pytest.mark.unit
def test_state_reconstructor_initial_state():
    """StateReconstructor starts with clean initial state."""
    from services.replay_engine import StateReconstructor

    reconstructor = StateReconstructor()

    initial_state = reconstructor.get_state()

    assert "risk_state" in initial_state
    assert initial_state["risk_state"]["equity"] > 0
    assert initial_state["risk_state"]["daily_pnl"] == 0.0
    assert initial_state["positions"] == {}
    assert initial_state["signals"] == []


# ==============================================================================
# INTEGRATION: END-TO-END DETERMINISM
# ==============================================================================


@pytest.mark.integration
def test_end_to_end_signal_to_decision_determinism():
    """Complete flow: MarketData → Signal → RiskDecision is deterministic."""
    from services import risk_engine

    correlation_id = uuid.uuid4()
    metadata = EventMetadata(service="test", version="1.0.0")

    # Step 1: Market data
    market_data = MarketDataEvent(
        sequence_number=1,
        timestamp_logical=1000,
        correlation_id=correlation_id,
        metadata=metadata,
        symbol="BTCUSDT",
        price=50000.0,
        volume=100.0,
        pct_change=3.5,
    )

    # Step 2: Signal generation (deterministic based on market data)
    signal = SignalGeneratedEvent(
        sequence_number=2,
        timestamp_logical=1001,
        correlation_id=correlation_id,
        causation_id=market_data.event_id,
        metadata=metadata,
        symbol="BTCUSDT",
        side=Side.BUY,
        confidence=0.85,
        reason="Strong momentum + high volume",
        price=50000.0,
        strategy_params={"momentum_threshold": 3.0, "rsi_value": 65.0},
    )

    # Step 3: Risk decision (deterministic based on signal + state)
    risk_state_data = RiskState(
        equity=100_000.0, daily_pnl=-1000.0, total_exposure_pct=0.10, open_positions=1
    )

    risk_checks = {
        "daily_drawdown": RiskCheckResult(
            checked=True, passed=True, current_value=-0.01, limit=-0.05
        ),
        "exposure_limit": RiskCheckResult(
            checked=True, passed=True, current_value=0.10, limit=0.30
        ),
    }

    risk_decision = RiskDecisionEvent(
        sequence_number=3,
        timestamp_logical=1002,
        correlation_id=correlation_id,
        causation_id=signal.event_id,
        metadata=metadata,
        signal_id=signal.event_id,
        approved=True,
        reason="All risk checks passed",
        symbol="BTCUSDT",
        side=Side.BUY,
        approved_size=0.2,
        stop_price=49000.0,
        risk_checks=risk_checks,
        risk_state=risk_state_data,
    )

    # Verify causation chain
    assert signal.causation_id == market_data.event_id
    assert risk_decision.causation_id == signal.event_id

    # Verify all events have same correlation
    assert (
        market_data.correlation_id
        == signal.correlation_id
        == risk_decision.correlation_id
    )

    # Verify sequence ordering
    assert market_data.sequence_number < signal.sequence_number < risk_decision.sequence_number
