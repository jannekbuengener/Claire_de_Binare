"""
Envelope dataclasses for LR-021 deterministic replay.

Three envelope types represent the trading pipeline stages:
  - DecisionEnvelopeV1: Risk decision (ALLOW/BLOCK)
  - OrderEnvelopeV1: Order placed by execution service
  - FillEnvelopeV1: Fill/execution result

All envelopes share:
  - schema_version (str): "envelope.v1" for V1 envelopes
  - event_type (str): DECISION / ORDER / FILL
  - event_id (str): Deterministic envelope identifier when correlation inputs exist
  - ts_ms (int): Event timestamp in milliseconds
  - created_at (str): UTC ISO-8601 derived from ts_ms
  - payload (dict): Event-specific data

Optional fields (set to None when not applicable):
  - correlation_id, trace_id
  - policy_id, policy_hash, input_hash, output_hash
  - decision_context (dict): immutable decision inputs/thresholds snapshot
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

from core.replay.time import created_at_from_ts_ms


@dataclass
class DecisionEnvelopeV1:
    """Risk decision envelope (ALLOW or BLOCK)."""

    schema_version: str  # "envelope.v1"
    event_type: str  # "DECISION"
    event_id: str
    ts_ms: int
    payload: Dict[str, Any]
    created_at: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    decision_context: Optional[Dict[str, Any]] = None
    policy_snapshot: Optional[Dict[str, Any]] = None
    replay_run_id: Optional[str] = None
    replay_envelope_index: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts_ms": self.ts_ms,
            "created_at": (
                self.created_at
                if self.created_at is not None
                else created_at_from_ts_ms(self.ts_ms)
            ),
            "payload": self.payload,
        }
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        if self.trace_id is not None:
            result["trace_id"] = self.trace_id
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        if self.policy_hash is not None:
            result["policy_hash"] = self.policy_hash
        if self.input_hash is not None:
            result["input_hash"] = self.input_hash
        if self.output_hash is not None:
            result["output_hash"] = self.output_hash
        if self.decision_context is not None:
            result["decision_context"] = self.decision_context
        if self.policy_snapshot is not None:
            result["policy_snapshot"] = self.policy_snapshot
        if self.replay_run_id is not None:
            result["replay_run_id"] = self.replay_run_id
        if self.replay_envelope_index is not None:
            result["replay_envelope_index"] = self.replay_envelope_index
        return result


@dataclass
class OrderEnvelopeV1:
    """Order placement envelope."""

    schema_version: str  # "envelope.v1"
    event_type: str  # "ORDER"
    event_id: str
    ts_ms: int
    payload: Dict[str, Any]
    created_at: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    decision_context: Optional[Dict[str, Any]] = None
    policy_snapshot: Optional[Dict[str, Any]] = None
    replay_run_id: Optional[str] = None
    replay_envelope_index: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts_ms": self.ts_ms,
            "created_at": (
                self.created_at
                if self.created_at is not None
                else created_at_from_ts_ms(self.ts_ms)
            ),
            "payload": self.payload,
        }
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        if self.trace_id is not None:
            result["trace_id"] = self.trace_id
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        if self.policy_hash is not None:
            result["policy_hash"] = self.policy_hash
        if self.input_hash is not None:
            result["input_hash"] = self.input_hash
        if self.output_hash is not None:
            result["output_hash"] = self.output_hash
        if self.decision_context is not None:
            result["decision_context"] = self.decision_context
        if self.policy_snapshot is not None:
            result["policy_snapshot"] = self.policy_snapshot
        if self.replay_run_id is not None:
            result["replay_run_id"] = self.replay_run_id
        if self.replay_envelope_index is not None:
            result["replay_envelope_index"] = self.replay_envelope_index
        return result


@dataclass
class FillEnvelopeV1:
    """Execution fill/result envelope."""

    schema_version: str  # "envelope.v1"
    event_type: str  # "FILL"
    event_id: str
    ts_ms: int
    payload: Dict[str, Any]
    created_at: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_hash: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    decision_context: Optional[Dict[str, Any]] = None
    policy_snapshot: Optional[Dict[str, Any]] = None
    replay_run_id: Optional[str] = None
    replay_envelope_index: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "ts_ms": self.ts_ms,
            "created_at": (
                self.created_at
                if self.created_at is not None
                else created_at_from_ts_ms(self.ts_ms)
            ),
            "payload": self.payload,
        }
        if self.correlation_id is not None:
            result["correlation_id"] = self.correlation_id
        if self.trace_id is not None:
            result["trace_id"] = self.trace_id
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        if self.policy_hash is not None:
            result["policy_hash"] = self.policy_hash
        if self.input_hash is not None:
            result["input_hash"] = self.input_hash
        if self.output_hash is not None:
            result["output_hash"] = self.output_hash
        if self.decision_context is not None:
            result["decision_context"] = self.decision_context
        if self.policy_snapshot is not None:
            result["policy_snapshot"] = self.policy_snapshot
        if self.replay_run_id is not None:
            result["replay_run_id"] = self.replay_run_id
        if self.replay_envelope_index is not None:
            result["replay_envelope_index"] = self.replay_envelope_index
        return result
