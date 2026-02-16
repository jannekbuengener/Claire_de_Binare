"""
Deterministic UUID Generator for Event-Sourcing Replay.
Governance: CDB_PSM_POLICY.md (Event-Sourcing, Determinismus)

relations:
  role: uuid_generator
  domain: utility
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - core/domain/event.py
    - tests/replay/test_deterministic_replay.py
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional


DEFAULT_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000000")


class DeterministicUUIDGenerator:
    """Generates deterministic UUIDs for replay scenarios."""

    def __init__(self, seed: int = 0, namespace: uuid.UUID = DEFAULT_NAMESPACE):
        self._seed = seed
        self._counter = 0
        self._namespace = namespace

    def generate(self, name: Optional[str] = None) -> uuid.UUID:
        """Generate a deterministic UUID from a name or seed/counter."""
        if name is None:
            name = f"{self._seed}-{self._counter}"
            self._counter += 1
        return uuid.uuid5(self._namespace, name)

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset the generator counter and optionally update the seed."""
        if seed is not None:
            self._seed = seed
        self._counter = 0


_DEFAULT_GENERATOR = DeterministicUUIDGenerator()


def generate_uuid(name: Optional[str] = None, seed: Optional[int] = None) -> str:
    """Generate a deterministic UUID string."""
    if seed is not None:
        generator = DeterministicUUIDGenerator(seed)
        return str(generator.generate(name))
    return str(_DEFAULT_GENERATOR.generate(name))


def generate_uuid_hex(
    name: Optional[str] = None, seed: Optional[int] = None, length: int = 8
) -> str:
    """Generate a deterministic UUID hex string with a specific length."""
    value = generate_uuid(name=name, seed=seed)
    return uuid.UUID(value).hex[:length]


# Namespace for decision_pk (Phase 8B)
DECISION_PK_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Fields included in input snapshot hash (deterministic, immutable)
DECISION_HASH_FIELDS = (
    "symbol",
    "timestamp_ms",
    "regime_id",
    "return_1m",
    "return_5m",
    "price_change_5m",
    "pct_change_15m",
    "volume_15m",
    "daily_drawdown_pct",
    "total_exposure_pct",
    "slippage_pct",
    "staleness_s",
    "data_silence_s",
    "thresholds",
)


def _sanitize_float(value: Any) -> Any:
    """Sanitize float values for deterministic JSON serialization."""
    if isinstance(value, float):
        if value != value or value == float("inf") or value == float("-inf"):
            return None
        return round(value, 10)
    if isinstance(value, dict):
        return {k: _sanitize_float(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_float(v) for v in value]
    return value


def compute_input_snapshot_hash(evidence: dict) -> str:
    """Compute SHA256 hash of deterministic evidence fields."""
    snapshot = {}
    for field in DECISION_HASH_FIELDS:
        if field in evidence:
            snapshot[field] = _sanitize_float(evidence[field])
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_decision_pk(symbol: str, ts_ms: int, evidence: dict) -> str:
    """Generate deterministic decision_pk (UUIDv5) for idempotent persistence."""
    input_hash = compute_input_snapshot_hash(evidence)
    name = f"{symbol}:{ts_ms}:{input_hash}"
    return str(uuid.uuid5(DECISION_PK_NAMESPACE, name))


# =============================================================================
# Phase 8C: Correlation IDs End-to-End
# =============================================================================

# Namespace for correlation_id (root of correlation chain)
CORRELATION_ROOT_NAMESPACE = uuid.UUID("c0ffe100-cafe-4000-babe-000000000001")

# Namespace for event_pk (per-event idempotency key)
CORRELATION_EVENT_NAMESPACE = uuid.UUID("c0ffe100-cafe-4000-babe-000000000002")


def compute_correlation_id(signal_id: str) -> str:
    """
    Compute correlation_id (root of chain) from signal_id.

    Args:
        signal_id: The signal_id from Signal Service (e.g., "sig-abc123...")

    Returns:
        UUIDv5 string (36 chars) as correlation chain root.

    Raises:
        ValueError: If signal_id is empty/None (fail-closed).
    """
    if not signal_id:
        raise ValueError("signal_id is required for correlation_id (fail-closed)")
    return str(uuid.uuid5(CORRELATION_ROOT_NAMESPACE, signal_id))


def compute_event_pk(
    signal_id: str,
    event_type: str,
    order_id: str | None = None,
    fill_id: str | None = None,
) -> str:
    """
    Compute deterministic event_pk for idempotent correlation_ledger writes.

    STRICT CANONICALIZATION:
    - event_type: UPPERCASE (SIGNAL, DECISION, ORDER, FILL)
    - signal_id: exact string (required, fail-closed)
    - order_id: "-" if empty/None
    - fill_id: "-" if empty/None

    Args:
        signal_id: The signal_id from Signal Service (required).
        event_type: Event type (SIGNAL, DECISION, ORDER, FILL).
        order_id: Optional order_id (for ORDER/FILL events).
        fill_id: Optional fill_id (for FILL events).

    Returns:
        UUIDv5 string (36 chars) as event idempotency key.

    Raises:
        ValueError: If signal_id is empty/None (fail-closed).
    """
    if not signal_id:
        raise ValueError("signal_id is required for event_pk (fail-closed)")

    canonical_event_type = event_type.upper()
    canonical_order_id = order_id if order_id else "-"
    canonical_fill_id = fill_id if fill_id else "-"

    input_str = (
        f"{signal_id}|{canonical_event_type}|{canonical_order_id}|{canonical_fill_id}"
    )
    return str(uuid.uuid5(CORRELATION_EVENT_NAMESPACE, input_str))


# =============================================================================
# Phase 9: Trace Contract v1 - Policy Governance
# =============================================================================

POLICY_ID = "risk_policy_v1"


def compute_policy_hash(thresholds: dict) -> str:
    """Compute SHA256 hash of policy/threshold bundle.

    Args:
        thresholds: The DECISION_THRESHOLDS dict used for risk decision.

    Returns:
        64-char hex SHA256 hash.
    """
    canonical = json.dumps(thresholds, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_output_hash(
    decision: str,
    reason_code: str | None,
    decision_pk: str,
    decision_id: str,
    contract_version: str,
    input_hash: str,
    policy_hash: str,
) -> str:
    """Compute SHA256 hash of deterministic decision output object.

    Fingerprints the complete decision output so changes in any
    deterministic field will produce a different hash.

    Args:
        decision: "ALLOW" or "BLOCK"
        reason_code: RC_XXX or None
        decision_pk: Deterministic decision primary key
        decision_id: UUIDv5 decision identifier
        contract_version: e.g., "decision_contract_v1"
        input_hash: SHA256 of input snapshot
        policy_hash: SHA256 of thresholds used

    Returns:
        64-char hex SHA256 hash.
    """
    output = {
        "decision": decision,
        "reason_code": reason_code,
        "decision_pk": decision_pk,
        "decision_id": decision_id,
        "contract_version": contract_version,
        "input_hash": input_hash,
        "policy_hash": policy_hash,
    }
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
