"""
Event Sourcing Infrastructure for Claire de Binaire

Provides:
- LogicalClock: Monotone sequence numbers for deterministic ordering
- BaseEvent: Common structure for all events
- Specific event types: MarketDataEvent, SignalEvent, RiskDecisionEvent, etc.
- Event validation and serialization
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# LOGICAL CLOCK
# ==============================================================================


class LogicalClock:
    """
    Monotonically increasing sequence number generator.

    Guarantees:
    - Event N always comes before Event N+1
    - No dependency on wall-clock time
    - Deterministic ordering across replay
    - Thread-safe (for multi-threaded environments)

    Implementation:
    - In-memory counter for single-process
    - Redis INCR for distributed systems
    - PostgreSQL sequence for persistence
    """

    def __init__(self, initial_value: int = 1):
        """
        Initialize logical clock.

        Args:
            initial_value: Starting sequence number (default: 1)
        """
        self._sequence: int = initial_value
        self._start_time_ms: int = int(time.time() * 1000)

    def next(self) -> int:
        """
        Get next sequence number.

        Returns:
            int: Monotonically increasing sequence number
        """
        current = self._sequence
        self._sequence += 1
        return current

    def current(self) -> int:
        """Get current sequence number without incrementing."""
        return self._sequence

    def logical_timestamp(self) -> int:
        """
        Get logical timestamp (milliseconds since clock start).

        This is independent of system time and only advances when
        events are created.

        Returns:
            int: Milliseconds since clock initialization
        """
        return int(time.time() * 1000) - self._start_time_ms

    def reset(self, value: int = 1) -> None:
        """
        Reset clock to specific value.

        WARNING: Only use for testing or replay initialization.

        Args:
            value: New sequence number
        """
        self._sequence = value
        self._start_time_ms = int(time.time() * 1000)


# Global logical clock instance
# In production: replace with Redis-backed implementation
_global_clock = LogicalClock()


def get_clock() -> LogicalClock:
    """Get global logical clock instance."""
    return _global_clock


# ==============================================================================
# ENUMS
# ==============================================================================


class EventType(str, Enum):
    """Event type enumeration."""

    MARKET_DATA = "market_data"
    SIGNAL_GENERATED = "signal_generated"
    RISK_DECISION = "risk_decision"
    ORDER_REQUEST = "order_request"
    ORDER_RESULT = "order_result"
    POSITION_UPDATE = "position_update"
    ALERT = "alert"
    STATE_SNAPSHOT = "state_snapshot"
    SYSTEM_EVENT = "system_event"


class Side(str, Enum):
    """Trading side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Order execution status."""

    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


class AlertLevel(str, Enum):
    """Alert severity level."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class PositionAction(str, Enum):
    """Position lifecycle action."""

    OPENED = "OPENED"
    MODIFIED = "MODIFIED"
    CLOSED = "CLOSED"


# ==============================================================================
# BASE EVENT
# ==============================================================================


class EventMetadata(BaseModel):
    """Metadata for audit trail."""

    service: str = Field(..., description="Service that generated this event")
    version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(
        default="paper", description="Environment: paper or live"
    )


class BaseEvent(BaseModel):
    """
    Base structure for all events.

    All events must inherit from this class to ensure
    consistent audit trail and deterministic replay.
    """

    event_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique event identifier"
    )
    event_type: EventType = Field(..., description="Type of event")
    sequence_number: int = Field(..., description="Monotonic logical clock value")
    timestamp_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Wall-clock time (for humans)",
    )
    timestamp_logical: int = Field(
        ..., description="Bot-internal logical timestamp (ms since start)"
    )
    causation_id: Optional[uuid.UUID] = Field(
        default=None, description="Event ID that caused this event"
    )
    correlation_id: uuid.UUID = Field(
        ..., description="Session/Trade ID to group related events"
    )
    metadata: EventMetadata = Field(..., description="Audit trail metadata")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v),
        }

    @classmethod
    def create(
        cls,
        event_type: EventType,
        correlation_id: uuid.UUID,
        metadata: EventMetadata,
        causation_id: Optional[uuid.UUID] = None,
        **payload: Any,
    ) -> BaseEvent:
        """
        Create new event with automatic sequence numbering.

        Args:
            event_type: Type of event
            correlation_id: Session/Trade ID
            metadata: Audit metadata
            causation_id: Optional causation event ID
            **payload: Event-specific payload fields

        Returns:
            BaseEvent: New event instance
        """
        clock = get_clock()
        return cls(
            event_type=event_type,
            sequence_number=clock.next(),
            timestamp_logical=clock.logical_timestamp(),
            causation_id=causation_id,
            correlation_id=correlation_id,
            metadata=metadata,
            **payload,
        )


# ==============================================================================
# SPECIFIC EVENT TYPES
# ==============================================================================


class MarketDataEvent(BaseEvent):
    """Market data received from exchange."""

    event_type: EventType = Field(default=EventType.MARKET_DATA, frozen=True)
    symbol: str
    price: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    pct_change: Optional[float] = None
    interval: str = "1m"

    @field_validator("price", "volume")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Validate price and volume are positive."""
        if v <= 0:
            raise ValueError("Price and volume must be positive")
        return v


class SignalGeneratedEvent(BaseEvent):
    """Trading signal generated by strategy."""

    event_type: EventType = Field(default=EventType.SIGNAL_GENERATED, frozen=True)
    symbol: str
    side: Side
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    requested_size: Optional[float] = None
    price: float
    strategy_params: Dict[str, Any]


class RiskCheckResult(BaseModel):
    """Result of individual risk check."""

    checked: bool
    passed: bool
    current_value: Optional[float] = None
    limit: Optional[float] = None
    details: Optional[str] = None


class RiskState(BaseModel):
    """Complete risk state at decision time."""

    equity: float
    daily_pnl: float
    total_exposure_pct: float
    open_positions: int


class RiskDecisionEvent(BaseEvent):
    """Risk manager decision on signal."""

    event_type: EventType = Field(default=EventType.RISK_DECISION, frozen=True)
    signal_id: uuid.UUID
    approved: bool
    reason: str
    symbol: str
    side: Side
    approved_size: Optional[float] = None
    stop_price: Optional[float] = None
    risk_checks: Dict[str, RiskCheckResult]
    risk_state: RiskState


class OrderRequestEvent(BaseEvent):
    """Order request sent to execution service."""

    event_type: EventType = Field(default=EventType.ORDER_REQUEST, frozen=True)
    risk_decision_id: uuid.UUID
    symbol: str
    side: Side
    size: float
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None
    order_type: str = "MARKET"


class OrderResultEvent(BaseEvent):
    """Result of order execution."""

    event_type: EventType = Field(default=EventType.ORDER_RESULT, frozen=True)
    order_request_id: uuid.UUID
    order_id: str
    status: OrderStatus
    filled_quantity: Optional[float] = None
    fill_price: Optional[float] = None
    fees: Optional[float] = None
    slippage: Optional[float] = None
    error_message: Optional[str] = None


class PositionUpdateEvent(BaseEvent):
    """Position opened, modified, or closed."""

    event_type: EventType = Field(default=EventType.POSITION_UPDATE, frozen=True)
    position_id: uuid.UUID
    symbol: str
    action: PositionAction
    side: Side
    quantity: float
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None


class AlertEvent(BaseEvent):
    """System alert (risk limit, error, warning)."""

    event_type: EventType = Field(default=EventType.ALERT, frozen=True)
    code: str
    level: AlertLevel
    message: str
    context: Optional[Dict[str, Any]] = None


class StateSnapshotEvent(BaseEvent):
    """Periodic snapshot of system state for faster replay."""

    event_type: EventType = Field(default=EventType.STATE_SNAPSHOT, frozen=True)
    snapshot_type: str
    state_data: Dict[str, Any]
    checksum: str


class SystemEvent(BaseEvent):
    """System lifecycle events (start, stop, error)."""

    event_type: EventType = Field(default=EventType.SYSTEM_EVENT, frozen=True)
    event_name: str
    details: Optional[Dict[str, Any]] = None


# ==============================================================================
# EVENT FACTORY
# ==============================================================================


class EventFactory:
    """Factory for creating events with consistent metadata."""

    def __init__(self, service_name: str, version: str = "1.0.0"):
        """
        Initialize event factory.

        Args:
            service_name: Name of service creating events
            version: Service version
        """
        self.service_name = service_name
        self.version = version
        self.environment = os.getenv("ENVIRONMENT", "paper")

    def _create_metadata(self) -> EventMetadata:
        """Create standard metadata."""
        return EventMetadata(
            service=self.service_name,
            version=self.version,
            environment=self.environment,
        )

    def create_market_data(
        self,
        symbol: str,
        price: float,
        volume: float,
        correlation_id: uuid.UUID,
        **kwargs: Any,
    ) -> MarketDataEvent:
        """Create market data event."""
        return MarketDataEvent(
            sequence_number=get_clock().next(),
            timestamp_logical=get_clock().logical_timestamp(),
            correlation_id=correlation_id,
            metadata=self._create_metadata(),
            symbol=symbol,
            price=price,
            volume=volume,
            **kwargs,
        )

    def create_signal(
        self,
        symbol: str,
        side: Side,
        confidence: float,
        reason: str,
        price: float,
        strategy_params: Dict[str, Any],
        correlation_id: uuid.UUID,
        causation_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> SignalGeneratedEvent:
        """Create signal generated event."""
        return SignalGeneratedEvent(
            sequence_number=get_clock().next(),
            timestamp_logical=get_clock().logical_timestamp(),
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=self._create_metadata(),
            symbol=symbol,
            side=side,
            confidence=confidence,
            reason=reason,
            price=price,
            strategy_params=strategy_params,
            **kwargs,
        )

    def create_risk_decision(
        self,
        signal_id: uuid.UUID,
        approved: bool,
        reason: str,
        symbol: str,
        side: Side,
        risk_checks: Dict[str, RiskCheckResult],
        risk_state: RiskState,
        correlation_id: uuid.UUID,
        causation_id: Optional[uuid.UUID] = None,
        **kwargs: Any,
    ) -> RiskDecisionEvent:
        """Create risk decision event."""
        return RiskDecisionEvent(
            sequence_number=get_clock().next(),
            timestamp_logical=get_clock().logical_timestamp(),
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=self._create_metadata(),
            signal_id=signal_id,
            approved=approved,
            reason=reason,
            symbol=symbol,
            side=side,
            risk_checks=risk_checks,
            risk_state=risk_state,
            **kwargs,
        )

    # Add similar factory methods for other event types...


# ==============================================================================
# DETERMINISM HELPERS
# ==============================================================================


def ensure_determinism(event: BaseEvent) -> None:
    """
    Validate event contains all fields needed for deterministic replay.

    Raises:
        ValueError: If event missing required fields for determinism
    """
    if not event.sequence_number:
        raise ValueError("Event missing sequence_number")
    if not event.timestamp_logical:
        raise ValueError("Event missing timestamp_logical")
    if not event.correlation_id:
        raise ValueError("Event missing correlation_id")
    if not event.metadata:
        raise ValueError("Event missing metadata")


def compare_events(event1: BaseEvent, event2: BaseEvent) -> bool:
    """
    Compare two events for equality (excluding timestamps).

    Used in determinism tests to verify replay produces same events.

    Args:
        event1: First event
        event2: Second event

    Returns:
        bool: True if events are semantically equal
    """
    # Compare everything except wall-clock timestamps
    return (
        event1.event_type == event2.event_type
        and event1.sequence_number == event2.sequence_number
        and event1.correlation_id == event2.correlation_id
    )
