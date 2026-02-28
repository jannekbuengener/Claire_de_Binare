"""
Envelope dataclasses for LR-021 deterministic replay.

Three envelope types represent the trading pipeline stages:
  - DecisionEnvelopeV1: Risk decision (ALLOW/BLOCK)
  - OrderEnvelopeV1: Order placed by execution service
  - FillEnvelopeV1: Fill/execution result

All envelopes share:
  - schema_version (str): "envelope.v1" for V1 envelopes
  - event_type (str): DECISION / ORDER / FILL
  - event_id (str): Unique event identifier
  - ts_ms (int): Event timestamp in milliseconds
  - payload (dict): Event-specific data

Optional fields (set to None when not applicable):
  - policy_id, policy_hash, input_hash, output_hash
  - policy_snapshot (dict): nested policy metadata (#748, Slice 1)

relations:
  role: envelope_definition
  domain: replay
  upstream:
    - core/replay/canonical_json.py
  downstream:
    - scripts/replay/lr021_replay.py
    - tests/unit/replay/test_envelopes.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DecisionEnvelopeV1:
    """Risk decision envelope (ALLOW or BLOCK)."""

    schema_version: str  # "envelope.v1"
    event_type: str  # "DECISION"
    event_id: str
    ts_ms: int
    payload: Dict[str, Any]
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    policy_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts_ms": self.ts_ms,
            "payload": self.payload,
        }
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        if self.policy_hash is not None:
            result["policy_hash"] = self.policy_hash
        if self.input_hash is not None:
            result["input_hash"] = self.input_hash
        if self.output_hash is not None:
            result["output_hash"] = self.output_hash
        if self.policy_snapshot is not None:
            result["policy_snapshot"] = self.policy_snapshot
        return result


@dataclass
class OrderEnvelopeV1:
    """Order placement envelope."""

    schema_version: str  # "envelope.v1"
    event_type: str  # "ORDER"
    event_id: str
    ts_ms: int
    payload: Dict[str, Any]
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    policy_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts_ms": self.ts_ms,
            "payload": self.payload,
        }
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        if self.policy_hash is not None:
            result["policy_hash"] = self.policy_hash
        if self.input_hash is not None:
            result["input_hash"] = self.input_hash
        if self.output_hash is not None:
            result["output_hash"] = self.output_hash
        if self.policy_snapshot is not None:
            result["policy_snapshot"] = self.policy_snapshot
        return result


@dataclass
class FillEnvelopeV1:
    """Execution fill/result envelope."""

    schema_version: str  # "envelope.v1"
    event_type: str  # "FILL"
    event_id: str
    ts_ms: int
    payload: Dict[str, Any]
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    policy_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts_ms": self.ts_ms,
            "payload": self.payload,
        }
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        if self.policy_hash is not None:
            result["policy_hash"] = self.policy_hash
        if self.input_hash is not None:
            result["input_hash"] = self.input_hash
        if self.output_hash is not None:
            result["output_hash"] = self.output_hash
        if self.policy_snapshot is not None:
            result["policy_snapshot"] = self.policy_snapshot
        return result
