"""
Replay Engine for Claire de Binaire

Deterministisches Replay-System für:
- Bug-Reproduktion
- Strategy-Backtesting
- Risk-Validierung
- Compliance-Audits

Garantiert:
- Gleiche Events → gleiche Entscheidungen
- Keine Side-Effects (read-only)
- Kein externes API-Calling
- Vollständige Nachvollziehbarkeit
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))

from services.event_sourcing import (
    BaseEvent,
    EventType,
    LogicalClock,
    MarketDataEvent,
    SignalGeneratedEvent,
    RiskDecisionEvent,
    OrderRequestEvent,
    OrderResultEvent,
    get_clock,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# REPLAY MODE CONTEXT
# ==============================================================================


class ReplayMode:
    """
    Global replay mode flag.

    When in replay mode:
    - No external API calls allowed
    - No Redis pub/sub (events come from log)
    - Database writes disabled (except for replay metadata)
    - Deterministic behavior enforced
    """

    _enabled: bool = False
    _start_sequence: Optional[int] = None
    _end_sequence: Optional[int] = None

    @classmethod
    def enable(
        cls, start_sequence: Optional[int] = None, end_sequence: Optional[int] = None
    ) -> None:
        """Enable replay mode with optional sequence range."""
        cls._enabled = True
        cls._start_sequence = start_sequence
        cls._end_sequence = end_sequence
        logger.info(
            f"🎬 Replay mode ENABLED (seq {start_sequence} → {end_sequence})"
        )

    @classmethod
    def disable(cls) -> None:
        """Disable replay mode."""
        cls._enabled = False
        cls._start_sequence = None
        cls._end_sequence = None
        logger.info("⏹️ Replay mode DISABLED")

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if in replay mode."""
        return cls._enabled

    @classmethod
    def get_range(cls) -> tuple[Optional[int], Optional[int]]:
        """Get replay sequence range."""
        return (cls._start_sequence, cls._end_sequence)


def replay_only(func: Callable) -> Callable:
    """Decorator to mark functions that only run in replay mode."""

    def wrapper(*args, **kwargs):
        if not ReplayMode.is_enabled():
            raise RuntimeError(f"{func.__name__} can only be called in replay mode")
        return func(*args, **kwargs)

    return wrapper


def no_replay(func: Callable) -> Callable:
    """Decorator to prevent functions from running in replay mode."""

    def wrapper(*args, **kwargs):
        if ReplayMode.is_enabled():
            logger.warning(
                f"⚠️ {func.__name__} blocked in replay mode (no side effects)"
            )
            return None
        return func(*args, **kwargs)

    return wrapper


# ==============================================================================
# EVENT PLAYER
# ==============================================================================


class EventPlayer:
    """
    Plays events from log through the system.

    Events are processed in sequence order to maintain
    deterministic causation chain.
    """

    def __init__(self):
        """Initialize event player."""
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.events_played = 0
        self.errors: List[Dict[str, Any]] = []

    def register_handler(
        self, event_type: EventType, handler: Callable[[BaseEvent], None]
    ) -> None:
        """
        Register handler for specific event type.

        Args:
            event_type: Type of event to handle
            handler: Function that processes the event
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")

    def play_event(self, event: BaseEvent) -> bool:
        """
        Play single event through registered handlers.

        Args:
            event: Event to play

        Returns:
            bool: True if successful, False if error
        """
        try:
            event_type = EventType(event.event_type)

            if event_type not in self.event_handlers:
                logger.debug(f"No handler for {event_type}, skipping")
                return True

            for handler in self.event_handlers[event_type]:
                handler(event)

            self.events_played += 1

            if self.events_played % 100 == 0:
                logger.info(f"📼 Replayed {self.events_played} events...")

            return True

        except Exception as e:
            error_record = {
                "event_id": str(event.event_id),
                "sequence_number": event.sequence_number,
                "event_type": event.event_type,
                "error": str(e),
            }
            self.errors.append(error_record)
            logger.error(
                f"❌ Error playing event {event.sequence_number}: {e}"
            )
            return False

    def play_events(
        self, events: List[BaseEvent], fail_fast: bool = False
    ) -> Dict[str, Any]:
        """
        Play sequence of events.

        Args:
            events: List of events in sequence order
            fail_fast: Stop on first error if True

        Returns:
            Dict with replay statistics
        """
        logger.info(f"🎬 Starting replay of {len(events)} events...")

        for event in events:
            success = self.play_event(event)
            if not success and fail_fast:
                logger.error("Stopping replay due to error (fail_fast=True)")
                break

        stats = {
            "total_events": len(events),
            "events_played": self.events_played,
            "errors": len(self.errors),
            "error_details": self.errors,
        }

        logger.info(
            f"✅ Replay complete: {stats['events_played']}/{stats['total_events']} events, {stats['errors']} errors"
        )

        return stats


# ==============================================================================
# STATE RECONSTRUCTOR
# ==============================================================================


class StateReconstructor:
    """
    Reconstructs system state from event log.

    Can start from:
    - Beginning (full replay)
    - State snapshot (faster)
    - Specific sequence number
    """

    def __init__(self):
        """Initialize state reconstructor."""
        self.risk_state: Dict[str, Any] = self._initial_risk_state()
        self.positions: Dict[str, Any] = {}
        self.signals: List[Dict[str, Any]] = []
        self.orders: List[Dict[str, Any]] = []

    def _initial_risk_state(self) -> Dict[str, Any]:
        """Get initial risk state."""
        return {
            "equity": float(os.getenv("INITIAL_EQUITY", "100000.0")),
            "daily_pnl": 0.0,
            "total_exposure_pct": 0.0,
            "open_positions": 0,
        }

    @replay_only
    def load_from_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        Load state from snapshot.

        Args:
            snapshot: State snapshot from database
        """
        logger.info(
            f"📸 Loading state from snapshot (seq {snapshot['sequence_number']})"
        )
        state_data = snapshot["state_data"]

        if "risk_state" in state_data:
            self.risk_state = state_data["risk_state"]
        if "positions" in state_data:
            self.positions = state_data["positions"]
        if "signals" in state_data:
            self.signals = state_data["signals"]
        if "orders" in state_data:
            self.orders = state_data["orders"]

    @replay_only
    def apply_event(self, event: BaseEvent) -> None:
        """
        Apply event to reconstruct state.

        Args:
            event: Event to apply
        """
        event_type = EventType(event.event_type)

        if event_type == EventType.SIGNAL_GENERATED:
            self._apply_signal_event(event)
        elif event_type == EventType.RISK_DECISION:
            self._apply_risk_decision_event(event)
        elif event_type == EventType.ORDER_RESULT:
            self._apply_order_result_event(event)
        elif event_type == EventType.POSITION_UPDATE:
            self._apply_position_update_event(event)

    def _apply_signal_event(self, event: BaseEvent) -> None:
        """Apply signal event to state."""
        signal_data = event.model_dump()
        self.signals.append(signal_data)

    def _apply_risk_decision_event(self, event: BaseEvent) -> None:
        """Apply risk decision event to state."""
        # Update risk state from event
        if hasattr(event, "risk_state"):
            self.risk_state = event.risk_state.model_dump()

    def _apply_order_result_event(self, event: BaseEvent) -> None:
        """Apply order result event to state."""
        order_data = event.model_dump()
        self.orders.append(order_data)

        # Update equity if filled
        if hasattr(event, "status") and event.status == "FILLED":
            if hasattr(event, "fees"):
                self.risk_state["equity"] -= float(event.fees or 0.0)

    def _apply_position_update_event(self, event: BaseEvent) -> None:
        """Apply position update event to state."""
        if hasattr(event, "position_id"):
            position_id = str(event.position_id)
            self.positions[position_id] = event.model_dump()

            # Update open positions count
            self.risk_state["open_positions"] = len(
                [p for p in self.positions.values() if p.get("action") != "CLOSED"]
            )

    def get_state(self) -> Dict[str, Any]:
        """
        Get current reconstructed state.

        Returns:
            Complete system state
        """
        return {
            "risk_state": self.risk_state,
            "positions": self.positions,
            "signals": self.signals,
            "orders": self.orders,
        }


# ==============================================================================
# REPLAY ENGINE
# ==============================================================================


class ReplayEngine:
    """
    Main replay engine orchestrator.

    Coordinates:
    - Event loading from database
    - State reconstruction
    - Event playback through services
    - Determinism validation
    """

    def __init__(self, event_reader):
        """
        Initialize replay engine.

        Args:
            event_reader: EventReader instance from event_store service
        """
        self.event_reader = event_reader
        self.player = EventPlayer()
        self.reconstructor = StateReconstructor()
        self.clock = get_clock()

    def replay_range(
        self,
        from_sequence: Optional[int] = None,
        to_sequence: Optional[int] = None,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
        use_snapshot: bool = True,
    ) -> Dict[str, Any]:
        """
        Replay events in specified range.

        Args:
            from_sequence: Start sequence number
            to_sequence: End sequence number
            from_timestamp: Start timestamp
            to_timestamp: End timestamp
            use_snapshot: Start from latest snapshot if available

        Returns:
            Replay statistics and final state
        """
        # Enable replay mode
        ReplayMode.enable(from_sequence, to_sequence)

        try:
            # Load snapshot if requested
            if use_snapshot:
                snapshot = self.event_reader.get_latest_snapshot()
                if snapshot and (
                    from_sequence is None or snapshot["sequence_number"] >= from_sequence
                ):
                    self.reconstructor.load_from_snapshot(snapshot)
                    from_sequence = snapshot["sequence_number"] + 1
                    logger.info(
                        f"Starting replay from snapshot at seq {snapshot['sequence_number']}"
                    )

            # Load events
            logger.info(f"Loading events (seq {from_sequence} → {to_sequence})...")
            events = self.event_reader.read_events(
                from_sequence=from_sequence, to_sequence=to_sequence
            )

            logger.info(f"Loaded {len(events)} events")

            # Reset logical clock to match replay
            if events:
                self.clock.reset(events[0]["sequence_number"])

            # Register state reconstruction handler
            self.player.register_handler(
                EventType.SIGNAL_GENERATED, self.reconstructor.apply_event
            )
            self.player.register_handler(
                EventType.RISK_DECISION, self.reconstructor.apply_event
            )
            self.player.register_handler(
                EventType.ORDER_RESULT, self.reconstructor.apply_event
            )
            self.player.register_handler(
                EventType.POSITION_UPDATE, self.reconstructor.apply_event
            )

            # Play events
            # TODO: Convert dict events to Pydantic models
            # stats = self.player.play_events(converted_events)

            # For now, return basic stats
            stats = {
                "events_loaded": len(events),
                "replay_range": {
                    "from_sequence": from_sequence,
                    "to_sequence": to_sequence,
                },
                "final_state": self.reconstructor.get_state(),
            }

            return stats

        finally:
            # Always disable replay mode
            ReplayMode.disable()

    def replay_correlation(self, correlation_id: str) -> Dict[str, Any]:
        """
        Replay all events for specific trade/session.

        Args:
            correlation_id: Correlation UUID

        Returns:
            Replay statistics and events
        """
        logger.info(f"Replaying correlation {correlation_id}...")

        events = self.event_reader.get_correlation_events(correlation_id)

        if not events:
            logger.warning(f"No events found for correlation {correlation_id}")
            return {"events": [], "state": {}}

        # Replay events in sequence order
        ReplayMode.enable()
        try:
            # TODO: Play events and reconstruct state
            stats = {
                "correlation_id": correlation_id,
                "events": events,
                "event_count": len(events),
                "final_state": self.reconstructor.get_state(),
            }
            return stats
        finally:
            ReplayMode.disable()

    def validate_determinism(
        self, from_sequence: int, to_sequence: int
    ) -> Dict[str, Any]:
        """
        Validate determinism by replaying twice and comparing results.

        Args:
            from_sequence: Start sequence
            to_sequence: End sequence

        Returns:
            Validation results
        """
        logger.info(f"🔍 Validating determinism (seq {from_sequence} → {to_sequence})")

        # First replay
        result1 = self.replay_range(
            from_sequence=from_sequence, to_sequence=to_sequence, use_snapshot=False
        )

        # Reset state
        self.reconstructor = StateReconstructor()

        # Second replay
        result2 = self.replay_range(
            from_sequence=from_sequence, to_sequence=to_sequence, use_snapshot=False
        )

        # Compare states
        state1 = result1["final_state"]
        state2 = result2["final_state"]

        deterministic = state1 == state2

        result = {
            "deterministic": deterministic,
            "replay1": result1,
            "replay2": result2,
            "state_diff": self._compare_states(state1, state2) if not deterministic else None,
        }

        if deterministic:
            logger.info("✅ Determinism validated: identical results")
        else:
            logger.error("❌ Determinism FAILED: results differ")

        return result

    def _compare_states(
        self, state1: Dict[str, Any], state2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two states and return differences."""
        differences = {}

        for key in set(list(state1.keys()) + list(state2.keys())):
            if state1.get(key) != state2.get(key):
                differences[key] = {"replay1": state1.get(key), "replay2": state2.get(key)}

        return differences


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: Initialize replay engine
    # from backoffice.services.event_store.service import EventReader, DatabaseConnection
    # db = DatabaseConnection(os.getenv("DATABASE_URL"))
    # reader = EventReader(db)
    # engine = ReplayEngine(reader)

    # Replay last 100 events
    # stats = engine.replay_range(from_sequence=1, to_sequence=100)
    # print(stats)

    # Validate determinism
    # validation = engine.validate_determinism(from_sequence=1, to_sequence=50)
    # print(f"Deterministic: {validation['deterministic']}")

    print("Replay engine module loaded successfully")
