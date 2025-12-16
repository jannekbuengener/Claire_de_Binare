"""
Event Base Class für Event-Sourcing.
Governance: CDB_PSM_POLICY.md (Append-Only Events, Replay-fähig)

relations:
  role: event_definition
  domain: datamodel
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - services/db_writer/db_writer.py
    - services/execution/service.py
    - services/risk/service.py
    - services/signal/service.py
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from enum import StrEnum
import hashlib
import json
import uuid


class EventType(StrEnum):
    """Supported event types for the system."""

    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PLACED = "ORDER_PLACED"
    POSITION_OPENED = "POSITION_OPENED"


@dataclass
class Event:
    """
    Base Class für alle Events im System.

    Governance:
    - CDB_PSM_POLICY.md: Event-Sourcing Kern (Immutable, Append-Only)
    - Deterministisch replay-bar
    - Hash-Validierung für Tamper-Erkennung
    """

    event_id: str
    event_type: EventType | str
    timestamp: datetime
    payload: Dict[str, Any]
    stream_id: str = ""
    sequence_number: int = 0
    schema_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """
        Berechnet Hash des Events (Payload + Metadata).

        Für Tamper-Erkennung und Replay-Validierung.
        """
        # Sortiere dict für deterministische Hashes
        payload_json = json.dumps(self.payload, sort_keys=True)
        metadata_json = json.dumps(self.metadata, sort_keys=True)

        hash_input = f"{self.event_id}{self.event_type}{self.timestamp.isoformat()}{payload_json}{metadata_json}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def validate_hash(self, expected_hash: str) -> bool:
        """Validiert Event-Hash."""
        return self.compute_hash() == expected_hash

    @classmethod
    def create(
        cls,
        event_type: EventType | str,
        payload: Dict[str, Any],
        timestamp: datetime,
        stream_id: str = "",
        sequence_number: int = 0,
        event_id: str | None = None,
    ) -> "Event":
        """Factory Method für Event-Erstellung."""
        if event_id is None:
            event_id = str(uuid.uuid4())

        return cls(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            payload=payload,
            stream_id=stream_id,
            sequence_number=sequence_number,
        )
