"""
Toggle-gated envelope emitter for LR-021 Slice 2.

Emits DecisionEnvelopeV1 / OrderEnvelopeV1 / FillEnvelopeV1 as structured
JSONL to a configured output (default: stdout logger). Toggle default OFF.

Toggle: CDB_ENVELOPE_EMISSION=0|1 (primary) | LR021_ENVELOPE_EMIT_ENABLED=0|1 (legacy alias).
Read per call, no cache. CDB_ takes precedence when set.
When OFF: all emit functions are no-ops (zero side effects, zero I/O).

Governance: LR-021 Slice 2 Evidence (docs/live-readiness/LR-021-EVIDENCE-SLICE2.md)

relations:
  role: envelope_emitter
  domain: replay
  upstream:
    - core/replay/canonical_json.py
    - core/replay/envelopes.py
  downstream:
    - services/risk/service.py
    - services/execution/service.py
    - tests/unit/replay/test_emitter.py
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from core.replay.canonical_json import canonical_json_dumps, sha256_hex

logger = logging.getLogger("lr021.emitter")


def envelope_emit_enabled() -> bool:
    """True only when envelope emission toggle is '1'.

    Precedence: CDB_ENVELOPE_EMISSION (primary) > LR021_ENVELOPE_EMIT_ENABLED (legacy alias).
    If CDB_ENVELOPE_EMISSION is set (any value including '0'), it wins.
    Otherwise falls back to LR021_ENVELOPE_EMIT_ENABLED.
    Default: '0' (OFF).

    Reads os.getenv on every call (no module-level cache) so tests
    can toggle via monkeypatch.setenv.
    """
    primary = os.getenv("CDB_ENVELOPE_EMISSION")
    if primary is not None:
        return primary == "1"
    return os.getenv("LR021_ENVELOPE_EMIT_ENABLED", "0") == "1"


def _compute_event_hash(envelope_dict: dict) -> str:
    """Compute canonical SHA-256 hash of an envelope dict."""
    canonical = canonical_json_dumps(envelope_dict)
    return sha256_hex(canonical.encode("utf-8"))


def _build_envelope(
    *,
    event_type: str,
    event_id: str,
    ts_ms: int,
    payload: Dict[str, Any],
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> dict:
    """Build envelope dict with optional fields omitted when None."""
    envelope: dict[str, Any] = {
        "schema_version": "envelope.v1",
        "event_type": event_type,
        "event_id": event_id,
        "ts_ms": ts_ms,
        "payload": payload,
    }
    if policy_id is not None:
        envelope["policy_id"] = policy_id
    if policy_hash is not None:
        envelope["policy_hash"] = policy_hash
    if input_hash is not None:
        envelope["input_hash"] = input_hash
    if output_hash is not None:
        envelope["output_hash"] = output_hash
    if policy_snapshot is not None:
        envelope["policy_snapshot"] = policy_snapshot
    return envelope


def emit_envelope(envelope: dict) -> None:
    """Emit a single envelope as compact JSON to the lr021.emitter logger.

    No-op when toggle OFF. When ON, computes event_hash and logs one
    JSONL line at INFO level.
    """
    if not envelope_emit_enabled():
        return

    event_hash = _compute_event_hash(envelope)
    output = {**envelope, "event_hash": event_hash}
    line = canonical_json_dumps(output)
    logger.info(line)


def emit_decision_envelope(
    *,
    event_id: str,
    ts_ms: int,
    decision: str,
    reason_code: Optional[str],
    symbol: str,
    evidence: Dict[str, Any],
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a DECISION envelope. No-op when toggle OFF."""
    if not envelope_emit_enabled():
        return

    payload: dict[str, Any] = {
        "decision": decision,
        "symbol": symbol,
    }
    if reason_code is not None:
        payload["reason_code"] = reason_code
    # Audit-useful without leaking values: sorted key names only
    if evidence:
        payload["evidence_keys"] = sorted(str(k) for k in evidence.keys())

    envelope = _build_envelope(
        event_type="DECISION",
        event_id=event_id,
        ts_ms=ts_ms,
        payload=payload,
        policy_id=policy_id,
        policy_hash=policy_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        policy_snapshot=policy_snapshot,
    )
    emit_envelope(envelope)


def emit_order_envelope(
    *,
    event_id: str,
    ts_ms: int,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    signal_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit an ORDER envelope. No-op when toggle OFF."""
    if not envelope_emit_enabled():
        return

    payload: dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
    }
    if signal_id is not None:
        payload["signal_id"] = signal_id
    if decision_id is not None:
        payload["decision_id"] = decision_id

    envelope = _build_envelope(
        event_type="ORDER",
        event_id=event_id,
        ts_ms=ts_ms,
        payload=payload,
        policy_id=policy_id,
        policy_hash=policy_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        policy_snapshot=policy_snapshot,
    )
    emit_envelope(envelope)


def emit_fill_envelope(
    *,
    event_id: str,
    ts_ms: int,
    order_id: str,
    fill_id: str,
    symbol: str,
    side: str,
    filled_quantity: float,
    price: Optional[float],
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a FILL envelope. No-op when toggle OFF."""
    if not envelope_emit_enabled():
        return

    payload: dict[str, Any] = {
        "order_id": order_id,
        "fill_id": fill_id,
        "symbol": symbol,
        "side": side,
        "filled_quantity": filled_quantity,
    }
    if price is not None:
        payload["price"] = price

    envelope = _build_envelope(
        event_type="FILL",
        event_id=event_id,
        ts_ms=ts_ms,
        payload=payload,
        policy_id=policy_id,
        policy_hash=policy_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        policy_snapshot=policy_snapshot,
    )
    emit_envelope(envelope)
