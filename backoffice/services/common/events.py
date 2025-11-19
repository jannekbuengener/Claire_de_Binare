"""
Common Event Base Classes for Claire de Binaire
Event Sourcing v2 - Deterministisches Event-Schema

Basierend auf Research: backoffice/docs/architecture/EVENT_SOURCING_RESEARCH.md
"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any
from datetime import datetime


@dataclass
class BaseEvent:
    """
    Base-Klasse für alle Events im System.

    Pflichtfelder für Event Sourcing v2:
    - event_id: Unique ID für das Event (UUID)
    - event_type: Type des Events (z.B. "market_data", "signal", "order")
    - timestamp: Wann wurde das Event erzeugt (Unix-Timestamp in ms)
    - version: Schema-Version (für Backward-Kompatibilität)
    - source: Welcher Service hat das Event erzeugt

    Optional (für End-to-End Tracing):
    - sequence_id: Monoton steigende Sequenz-Nummer (pro Service)
    - correlation_id: Bleibt gleich über gesamten Flow (MarketData → Signal → Order → Fill)
    - causation_id: ID des direkten Parent-Events (Fill.causation_id = Order.event_id)
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "base_event"
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))  # ms
    version: str = "2.0"
    source: str = "unknown"

    # Optional (für Tracing)
    sequence_id: Optional[int] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert Event zu Dictionary (für Redis/PostgreSQL).

        Returns:
            Dictionary mit allen Feldern (None-Werte werden gefiltert)
        """
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "version": self.version,
            "source": self.source,
        }

        # Optional fields (nur wenn gesetzt)
        if self.sequence_id is not None:
            result["sequence_id"] = self.sequence_id
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        if self.causation_id is not None:
            result["causation_id"] = self.causation_id

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "BaseEvent":
        """
        Erstellt Event aus Dictionary.

        Args:
            data: Dictionary mit Event-Daten

        Returns:
            BaseEvent-Instanz
        """
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=data.get("event_type", "base_event"),
            timestamp=int(data.get("timestamp", time.time() * 1000)),
            version=data.get("version", "2.0"),
            source=data.get("source", "unknown"),
            sequence_id=data.get("sequence_id"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
        )


@dataclass
class ClockEvent(BaseEvent):
    """
    Clock-Event für deterministische Zeit.

    Statt datetime.now() zu nutzen, wird die Zeit als Event ins System eingespeist.
    Dies ermöglicht deterministische Replays und Backtests.

    Usage:
        # Produktion: Echte Zeit
        clock_event = ClockEvent(
            current_time=int(time.time() * 1000),
            source="system_clock"
        )

        # Backtest: Simulierte Zeit
        clock_event = ClockEvent(
            current_time=backtest_timestamp,
            source="backtest_simulator"
        )
    """

    current_time: int = field(default_factory=lambda: int(time.time() * 1000))  # ms
    event_type: Literal["clock"] = "clock"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["current_time"] = self.current_time
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ClockEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            current_time=int(data.get("current_time", time.time() * 1000)),
        )

    @staticmethod
    def now() -> int:
        """Gibt aktuelle Zeit in ms zurück (für Live-Systeme)"""
        return int(time.time() * 1000)

    @staticmethod
    def from_timestamp(ts: int) -> "ClockEvent":
        """Erstellt ClockEvent aus Unix-Timestamp (für Backtests)"""
        return ClockEvent(current_time=ts, source="backtest")


@dataclass
class RiskDecisionEvent(BaseEvent):
    """
    Risk-Decision Event vom Risk Manager.

    Dieses Event loggt jede Risk-Entscheidung (approved/rejected) für Audit-Zwecke.
    Es ermöglicht später Replay und Analyse von Risk-Decisions.

    Usage:
        # Signal wurde approved
        decision = RiskDecisionEvent(
            signal_id="uuid-of-signal",
            approved=True,
            reason=None,
            position_size=0.5,
            stop_price=48000.0,
            source="cdb_risk",
            correlation_id=signal.correlation_id,
            causation_id=signal.event_id
        )

        # Signal wurde rejected
        decision = RiskDecisionEvent(
            signal_id="uuid-of-signal",
            approved=False,
            reason="max_daily_drawdown_exceeded",
            position_size=0.0,
            stop_price=None,
            source="cdb_risk",
            correlation_id=signal.correlation_id,
            causation_id=signal.event_id
        )
    """

    # Required fields (vor default fields wegen dataclass-Reihenfolge)
    signal_id: str = field(default="")  # ID des Signals, das evaluiert wurde
    approved: bool = field(default=False)  # Wurde das Signal genehmigt?

    # Optional fields
    reason: Optional[str] = None  # Grund für Rejection (bei approved=False)
    position_size: float = 0.0  # Genehmigte Position-Size
    stop_price: Optional[float] = None  # Berechneter Stop-Loss

    event_type: Literal["risk_decision"] = "risk_decision"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "signal_id": self.signal_id,
            "approved": self.approved,
            "position_size": self.position_size,
        })

        if self.reason is not None:
            result["reason"] = self.reason
        if self.stop_price is not None:
            result["stop_price"] = self.stop_price

        return result

    @classmethod
    def from_dict(cls, data: dict) -> "RiskDecisionEvent":
        base = super().from_dict(data)
        return cls(
            event_id=base.event_id,
            timestamp=base.timestamp,
            version=base.version,
            source=base.source,
            sequence_id=base.sequence_id,
            correlation_id=base.correlation_id,
            causation_id=base.causation_id,
            signal_id=data["signal_id"],
            approved=bool(data["approved"]),
            reason=data.get("reason"),
            position_size=float(data.get("position_size", 0.0)),
            stop_price=(
                float(data["stop_price"]) if data.get("stop_price") is not None else None
            ),
        )


# Sequence Counter für Services (Thread-Safe)
class SequenceCounter:
    """
    Thread-Safe Sequence Counter für Event-IDs.

    Jeder Service sollte seinen eigenen Counter haben:

    Usage:
        signal_counter = SequenceCounter("cdb_signal")

        event = Signal(
            sequence_id=signal_counter.next(),
            source="cdb_signal",
            ...
        )
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._counter = 0
        self._lock = None  # Optional: threading.Lock() für Multi-Threading

    def next(self) -> int:
        """Gibt nächste Sequence-ID zurück (monoton steigend)"""
        self._counter += 1
        return self._counter

    def current(self) -> int:
        """Gibt aktuelle Sequence-ID zurück (ohne Increment)"""
        return self._counter

    def reset(self) -> None:
        """Reset Counter (nur für Tests!)"""
        self._counter = 0
