"""Determinism validation and integrity verification for replay.

This module provides pure, side-effect-free helpers for validating
deterministic replay properties: envelope chain consistency, hash
verification, and report integrity.

Design rules:
  - No wall-clock time (determinism-critical)
  - Canonical JSON serialization via core.replay.canonical_json
  - Fail-closed validation (raise on any inconsistency)
  - Clear docstrings documenting canonical_json requirements
  - Testable without runtime/Redis/Docker

Governance: Issue #1806 (LR-021 Replay Contracts & Determinism)

relations:
  role: determinism_validation_utility
  domain: replay
  upstream:
    - core.replay.canonical_json
    - core.replay.replay_contracts
    - core.replay.envelopes
  downstream:
    - services/validation/ (potential future use)
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from core.replay.canonical_json import canonical_hash
from core.replay.replay_contracts import (
    ReplayIntegrity,
    ReplayReportInput,
    ReplayExecutionResult,
)


class ReplayDeterminismError(ValueError):
    """Raised when deterministic replay validation fails."""


def validate_envelope_determinism(envelope: Any) -> None:
    """Validate that an envelope is determinism-safe for replay.

    Requirements:
      - Must have to_dict() method
      - All required fields must be present and non-None
      - Optional fields present: should have values (not all None)
      - No wall-clock time variation (timestamps explicit, not NOW())

    Args:
        envelope: A DecisionEnvelopeV1, OrderEnvelopeV1, or FillEnvelopeV1.

    Raises:
        ReplayDeterminismError if validation fails.
    """
    if not hasattr(envelope, "to_dict"):
        raise ReplayDeterminismError(f"Envelope must have to_dict() method, got {type(envelope)}")

    if not hasattr(envelope, "schema_version"):
        raise ReplayDeterminismError("Envelope missing required field: schema_version")

    if envelope.schema_version != "envelope.v1":
        raise ReplayDeterminismError(
            f"Expected schema_version='envelope.v1', got {envelope.schema_version!r}"
        )

    if not hasattr(envelope, "event_type"):
        raise ReplayDeterminismError("Envelope missing required field: event_type")

    if envelope.event_type not in ("DECISION", "ORDER", "FILL"):
        raise ReplayDeterminismError(
            f"Expected event_type in (DECISION, ORDER, FILL), got {envelope.event_type!r}"
        )

    if not hasattr(envelope, "event_id"):
        raise ReplayDeterminismError("Envelope missing required field: event_id")

    if not isinstance(envelope.event_id, str) or not envelope.event_id.strip():
        raise ReplayDeterminismError(
            f"event_id must be non-empty string, got {envelope.event_id!r}"
        )

    if not hasattr(envelope, "ts_ms"):
        raise ReplayDeterminismError("Envelope missing required field: ts_ms")

    if not isinstance(envelope.ts_ms, int) or envelope.ts_ms < 0:
        raise ReplayDeterminismError(
            f"ts_ms must be non-negative integer, got {envelope.ts_ms!r}"
        )

    if not hasattr(envelope, "payload"):
        raise ReplayDeterminismError("Envelope missing required field: payload")

    if not isinstance(envelope.payload, dict):
        raise ReplayDeterminismError(
            f"payload must be dict, got {type(envelope.payload)}"
        )


def compute_envelope_hash(envelope: Any) -> str:
    """Compute deterministic SHA256 hash of an envelope.

    Uses canonical JSON serialization (sorted keys, compact, None-omitted).

    Args:
        envelope: A DecisionEnvelopeV1, OrderEnvelopeV1, or FillEnvelopeV1.

    Returns:
        64-character lowercase hex SHA256 hash.

    Raises:
        ReplayDeterminismError if envelope is invalid.
    """
    validate_envelope_determinism(envelope)
    envelope_dict = envelope.to_dict()
    return canonical_hash(envelope_dict)


def verify_envelope_chain_integrity(
    envelopes: Sequence[Any],
    expected_chain_hash: Optional[str] = None,
) -> str:
    """Verify that an ordered sequence of envelopes forms a consistent chain.

    Chain consistency means:
      1. All envelopes are valid (validate_envelope_determinism passes)
      2. Timestamps are non-decreasing
      3. event_ids are unique (no duplicates)
      4. The combined chain hash is deterministic and reproducible

    Args:
        envelopes: Sequence of envelope objects.
        expected_chain_hash: If provided, verify chain hash matches this value.

    Returns:
        Computed chain hash (canonical hash of ordered envelope hashes).

    Raises:
        ReplayDeterminismError if any check fails.
    """
    if not envelopes:
        computed_hash = canonical_hash([])
        if expected_chain_hash is not None and computed_hash != expected_chain_hash:
            raise ReplayDeterminismError(
                f"Empty envelope chain: expected hash {expected_chain_hash!r}, got {computed_hash!r}"
            )
        return computed_hash

    # Validate all envelopes individually
    envelope_hashes: List[str] = []
    seen_event_ids: set = set()
    last_ts_ms: Optional[int] = None

    for i, envelope in enumerate(envelopes):
        try:
            validate_envelope_determinism(envelope)
        except ReplayDeterminismError as e:
            raise ReplayDeterminismError(f"Envelope {i}: {e}") from e

        # Compute individual hash
        h = compute_envelope_hash(envelope)
        envelope_hashes.append(h)

        # Check for duplicate event_ids
        event_id = envelope.event_id
        if event_id in seen_event_ids:
            raise ReplayDeterminismError(
                f"Envelope {i}: duplicate event_id {event_id!r}"
            )
        seen_event_ids.add(event_id)

        # Check timestamp monotonicity
        ts_ms = envelope.ts_ms
        if last_ts_ms is not None and ts_ms < last_ts_ms:
            raise ReplayDeterminismError(
                f"Envelope {i}: timestamp violation (ts_ms={ts_ms} < last_ts_ms={last_ts_ms})"
            )
        last_ts_ms = ts_ms

    # Compute chain hash: hash of ordered individual hashes
    computed_hash = canonical_hash(envelope_hashes)

    if expected_chain_hash is not None and computed_hash != expected_chain_hash:
        raise ReplayDeterminismError(
            f"Envelope chain hash mismatch: expected {expected_chain_hash!r}, got {computed_hash!r}"
        )

    return computed_hash


def verify_replay_execution_result(result: ReplayExecutionResult) -> None:
    """Validate a ReplayExecutionResult for internal consistency.

    Checks:
      - run_id is non-empty string
      - event counts are non-negative
      - envelope_hashes list entries are 64-char hex strings (list itself may be empty)
      - if error_message is set, all event/order/fill counts should be zero

    Args:
        result: ReplayExecutionResult instance.

    Raises:
        ReplayDeterminismError if validation fails.
    """
    if not isinstance(result.run_id, str) or not result.run_id.strip():
        raise ReplayDeterminismError(f"run_id must be non-empty string, got {result.run_id!r}")

    if not isinstance(result.events_processed, int) or result.events_processed < 0:
        raise ReplayDeterminismError(
            f"events_processed must be non-negative int, got {result.events_processed}"
        )

    if not isinstance(result.decisions_made, int) or result.decisions_made < 0:
        raise ReplayDeterminismError(
            f"decisions_made must be non-negative int, got {result.decisions_made}"
        )

    if not isinstance(result.orders_placed, int) or result.orders_placed < 0:
        raise ReplayDeterminismError(
            f"orders_placed must be non-negative int, got {result.orders_placed}"
        )

    if not isinstance(result.fills_recorded, int) or result.fills_recorded < 0:
        raise ReplayDeterminismError(
            f"fills_recorded must be non-negative int, got {result.fills_recorded}"
        )

    if not isinstance(result.envelope_hashes, list):
        raise ReplayDeterminismError(
            f"envelope_hashes must be list, got {type(result.envelope_hashes)}"
        )

    for i, h in enumerate(result.envelope_hashes):
        if not isinstance(h, str) or len(h) != 64:
            raise ReplayDeterminismError(
                f"envelope_hashes[{i}] must be 64-char hex string, got {h!r}"
            )

    if result.error_message is not None and (
        result.events_processed > 0
        or result.decisions_made > 0
        or result.orders_placed > 0
        or result.fills_recorded > 0
    ):
        raise ReplayDeterminismError(
            "Inconsistent result: error_message set but event/order/fill counts > 0"
        )


def compute_replay_report_hash(report_input: ReplayReportInput) -> str:
    """Compute deterministic SHA256 hash of a replay report.

    Uses canonical JSON serialization of the full report_input.to_dict()
    output. This hash serves as the immutable fingerprint of the replay
    execution and its results.

    Args:
        report_input: ReplayReportInput instance.

    Returns:
        64-character lowercase hex SHA256 hash.

    Raises:
        ReplayDeterminismError if report is invalid.
    """
    # Quick validation
    if not isinstance(report_input, ReplayReportInput):
        raise ReplayDeterminismError(
            f"Expected ReplayReportInput, got {type(report_input)}"
        )

    if report_input.schema_version != "replay_report.v1":
        raise ReplayDeterminismError(
            f"Expected schema_version='replay_report.v1', got {report_input.schema_version!r}"
        )

    report_dict = report_input.to_dict()
    return canonical_hash(report_dict)


def verify_replay_integrity_result(integrity: ReplayIntegrity) -> None:
    """Validate a ReplayIntegrity result for internal consistency.

    Checks:
      - run_id is non-empty string
      - envelope_count is non-negative int
      - hashes are 64-char hex strings
      - failed_checks is empty iff integrity_ok is True

    Args:
        integrity: ReplayIntegrity instance.

    Raises:
        ReplayDeterminismError if validation fails.
    """
    if not isinstance(integrity.run_id, str) or not integrity.run_id.strip():
        raise ReplayDeterminismError(
            f"run_id must be non-empty string, got {integrity.run_id!r}"
        )

    if not isinstance(integrity.envelope_count, int) or integrity.envelope_count < 0:
        raise ReplayDeterminismError(
            f"envelope_count must be non-negative int, got {integrity.envelope_count}"
        )

    for hash_name in ("envelope_chain_hash", "event_loop_states_hash"):
        h = getattr(integrity, hash_name)
        if not isinstance(h, str) or len(h) != 64:
            raise ReplayDeterminismError(
                f"{hash_name} must be 64-char hex string, got {h!r}"
            )

    failed_checks = integrity.failed_checks
    if isinstance(failed_checks, (list, tuple)):
        if not all(isinstance(check, str) and check.strip() for check in failed_checks):
            raise ReplayDeterminismError(
                f"failed_checks must be non-empty strings, got {failed_checks}"
            )
    elif failed_checks:
        raise ReplayDeterminismError(
            f"failed_checks must be list/tuple, got {type(failed_checks)}"
        )

    if integrity.integrity_ok and failed_checks:
        raise ReplayDeterminismError(
            "Inconsistent result: integrity_ok=True but failed_checks is non-empty"
        )

    if not integrity.integrity_ok and not failed_checks:
        raise ReplayDeterminismError(
            "Inconsistent result: integrity_ok=False but failed_checks is empty"
        )
