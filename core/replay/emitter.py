"""
Toggle-gated envelope emitter for LR-021 Slice 2.

Emits DecisionEnvelopeV1 / OrderEnvelopeV1 / FillEnvelopeV1 as structured
JSONL to a configured publisher. Toggle default OFF.

Toggle is read from ``os.environ`` on **every call** — no module-level cache.
  - Primary: ``CDB_ENVELOPE_EMISSION=0|1`` (takes precedence when set)
  - Legacy:  ``LR021_ENVELOPE_EMIT_ENABLED=0|1`` (fallback, default ``"0"``)
  - Any read error ⇒ treated as OFF.

When OFF: all emit functions are strict no-ops (zero side effects, zero I/O,
no exceptions).

``configure_envelope_emission()`` injects the publisher only; the ``enabled``
parameter is kept for backward compatibility but ignored.

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
from core.replay.publisher import EnvelopePublisher
from core.utils.uuid_gen import compute_correlation_id, compute_event_pk
from core.replay.time import created_at_from_ts_ms

logger = logging.getLogger("lr021.emitter")

_envelope_publisher: EnvelopePublisher | None = None


def configure_envelope_emission(
    enabled: bool = False, publisher: EnvelopePublisher | None = None
) -> None:
    """Inject publisher for emission.

    The *enabled* parameter is retained for backward compatibility but
    ignored — the toggle is read from ``os.environ`` on every call.
    """
    global _envelope_publisher
    _envelope_publisher = publisher


def is_envelope_emission_enabled() -> bool:
    """Return the current emission toggle state (reads env per call)."""
    return _should_emit()


def _publish_line(line: str) -> None:
    if _envelope_publisher is None:
        raise RuntimeError("Envelope emission enabled but no publisher configured")
    _envelope_publisher.publish(line)


def _should_emit() -> bool:
    """Read env on every call — no module-level cache."""
    try:
        primary = os.environ.get("CDB_ENVELOPE_EMISSION")
        if primary is not None:
            return primary == "1"
        return os.environ.get("LR021_ENVELOPE_EMIT_ENABLED", "0") == "1"
    except Exception:
        return False


def _compute_event_hash(envelope_dict: dict) -> str:
    """Compute canonical SHA-256 hash of an envelope dict."""
    canonical = canonical_json_dumps(envelope_dict)
    return sha256_hex(canonical.encode("utf-8"))


def _derive_correlation_id(signal_id: Optional[str]) -> Optional[str]:
    """Compute deterministic correlation_id when signal_id is available."""
    if not signal_id:
        return None
    try:
        return compute_correlation_id(signal_id)
    except ValueError:
        return None


def _derive_event_id(
    *,
    event_type: str,
    fallback_event_id: str,
    signal_id: Optional[str] = None,
    order_id: Optional[str] = None,
    fill_id: Optional[str] = None,
) -> str:
    """Prefer deterministic event ids when correlation inputs are available."""
    if not signal_id:
        return fallback_event_id
    try:
        if event_type == "DECISION":
            return compute_event_pk(signal_id, event_type)
        if event_type == "ORDER" and order_id:
            return compute_event_pk(signal_id, event_type, order_id=order_id)
        if event_type == "FILL" and order_id and fill_id:
            return compute_event_pk(
                signal_id, event_type, order_id=order_id, fill_id=fill_id
            )
    except ValueError:
        return fallback_event_id
    return fallback_event_id


def _build_envelope(
    *,
    event_type: str,
    event_id: str,
    ts_ms: int,
    payload: Dict[str, Any],
    signal_id: Optional[str] = None,
    order_id: Optional[str] = None,
    fill_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    decision_context: Optional[Dict[str, Any]] = None,
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> dict:
    """Build envelope dict with optional fields omitted when None."""
    deterministic_event_id = _derive_event_id(
        event_type=event_type,
        fallback_event_id=event_id,
        signal_id=signal_id,
        order_id=order_id,
        fill_id=fill_id,
    )
    envelope: dict[str, Any] = {
        "schema_version": "envelope.v1",
        "event_type": event_type,
        "event_id": deterministic_event_id,
        "ts_ms": ts_ms,
        "created_at": created_at_from_ts_ms(ts_ms),
        "payload": payload,
    }
    correlation_id = _derive_correlation_id(signal_id)
    if correlation_id is not None:
        envelope["correlation_id"] = correlation_id
    if trace_id is not None:
        envelope["trace_id"] = trace_id
    if policy_id is not None:
        envelope["policy_id"] = policy_id
    if policy_hash is not None:
        envelope["policy_hash"] = policy_hash
    if input_hash is not None:
        envelope["input_hash"] = input_hash
    if output_hash is not None:
        envelope["output_hash"] = output_hash
    if decision_context is not None:
        envelope["decision_context"] = decision_context
    if policy_snapshot is not None:
        envelope["policy_snapshot"] = policy_snapshot
    return envelope


def emit_envelope(envelope: dict) -> None:
    """Emit a single envelope as compact JSON to the lr021.emitter logger.

    No-op when toggle OFF. When ON, computes event_hash and logs one
    JSONL line at INFO level, then publishes via the configured publisher.
    """
    if not _should_emit():
        return

    event_hash = _compute_event_hash(envelope)
    output = {**envelope, "event_hash": event_hash}
    line = canonical_json_dumps(output)
    logger.info(line)
    _publish_line(line)


def emit_decision_envelope(
    *,
    event_id: str,
    ts_ms: int,
    decision: str,
    reason_code: Optional[str],
    symbol: str,
    evidence: Dict[str, Any],
    signal_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    decision_context: Optional[Dict[str, Any]] = None,
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a DECISION envelope. No-op when toggle OFF."""
    if not _should_emit():
        return

    payload: dict[str, Any] = {
        "decision": decision,
        "symbol": symbol,
        "decision_id": event_id,
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
        signal_id=signal_id,
        trace_id=trace_id,
        decision_context=decision_context,
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
    order_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    decision_context: Optional[Dict[str, Any]] = None,
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit an ORDER envelope. No-op when toggle OFF."""
    if not _should_emit():
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
    if order_id is not None:
        payload["order_id"] = order_id

    envelope = _build_envelope(
        event_type="ORDER",
        event_id=event_id,
        ts_ms=ts_ms,
        payload=payload,
        signal_id=signal_id,
        order_id=order_id,
        trace_id=trace_id,
        decision_context=decision_context,
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
    signal_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    decision_context: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    policy_id: Optional[str] = None,
    policy_hash: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a FILL envelope. No-op when toggle OFF."""
    if not _should_emit():
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
    if status is not None:
        payload["status"] = status

    envelope = _build_envelope(
        event_type="FILL",
        event_id=event_id,
        ts_ms=ts_ms,
        payload=payload,
        signal_id=signal_id,
        order_id=order_id,
        fill_id=fill_id,
        trace_id=trace_id,
        decision_context=decision_context,
        policy_id=policy_id,
        policy_hash=policy_hash,
        input_hash=input_hash,
        output_hash=output_hash,
        policy_snapshot=policy_snapshot,
    )
    emit_envelope(envelope)
