"""Map memory write gate audit blocks to audit_observation records — #2703.

Fail-closed materialization only. No persistence in this module.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from core.utils.clock import utcnow as cdb_utcnow

OBSERVATION_TYPE_MEMORY_WRITE_GATE = "memory_write_gate_evaluation"
AUDIT_OBSERVATION_SCHEMA_VERSION = "audit-observation-from-gate/v1"

_FORBIDDEN_KEYS = frozenset({"human_go_token", "human_go"})
_SUBJECT_REF_RE = re.compile(r"^agent_memory:[a-zA-Z0-9/_\-.]+$")


class AuditObservationMaterializeError(ValueError):
    """Raised when a gate audit block cannot be materialized safely."""


def _parse_observed_at(value: str | None, fallback: datetime | None) -> datetime:
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    effective = fallback if fallback is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def _subject_ref_from_memory_id(memory_id: str | None) -> str | None:
    if not memory_id or not str(memory_id).strip():
        return None
    cleaned = str(memory_id).strip()
    subject = f"agent_memory:{cleaned}"
    if not _SUBJECT_REF_RE.match(subject):
        raise AuditObservationMaterializeError(
            f"memory_id is not safe for subject_ref: {memory_id!r}"
        )
    return subject


def materialize_audit_observation_from_gate(
    gate_envelope: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build an audit_observation row dict from a memory write gate envelope.

    Never includes raw human_go_token. Raises on forbidden keys in audit block.
    """
    audit = gate_envelope.get("audit")
    if not isinstance(audit, Mapping):
        raise AuditObservationMaterializeError("gate envelope missing audit block")

    for key in _FORBIDDEN_KEYS:
        if key in audit:
            raise AuditObservationMaterializeError(
                f"audit block must not contain forbidden key: {key}"
            )

    observation_id = audit.get("observation_id")
    if not isinstance(observation_id, str) or not observation_id.strip():
        raise AuditObservationMaterializeError("audit.observation_id is required")

    observation_type = audit.get("observation_type")
    if observation_type != OBSERVATION_TYPE_MEMORY_WRITE_GATE:
        raise AuditObservationMaterializeError(
            "audit.observation_type must be memory_write_gate_evaluation"
        )

    severity = audit.get("severity")
    if severity not in {"info", "warning", "blocking"}:
        raise AuditObservationMaterializeError(
            f"audit.severity invalid for audit_observation: {severity!r}"
        )

    message = audit.get("message")
    if not isinstance(message, str) or not message.strip():
        raise AuditObservationMaterializeError("audit.message is required")

    observed_by = audit.get("observed_by")
    if not isinstance(observed_by, str) or not observed_by.strip():
        raise AuditObservationMaterializeError("audit.observed_by is required")

    observed_at = _parse_observed_at(
        audit.get("observed_at") if isinstance(audit.get("observed_at"), str) else None,
        now,
    )

    memory_id = gate_envelope.get("memory_id")
    if memory_id is None:
        subject_ref = audit.get("subject_ref")
    else:
        subject_ref = _subject_ref_from_memory_id(str(memory_id))

    if subject_ref is None:
        subject_ref = "audit_observation:unknown_subject"

    evidence_refs = audit.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        evidence_refs = []

    related_memory = audit.get("related_memory")
    if not isinstance(related_memory, list):
        related_memory = []

    row: dict[str, Any] = {
        "schema_version": AUDIT_OBSERVATION_SCHEMA_VERSION,
        "observation_id": observation_id.strip(),
        "observation_type": OBSERVATION_TYPE_MEMORY_WRITE_GATE,
        "subject_ref": subject_ref,
        "severity": severity,
        "message": message.strip(),
        "evidence_refs": list(evidence_refs),
        "related_memory": list(related_memory),
        "observed_by": observed_by.strip(),
        "observed_at": observed_at.isoformat(),
        "status": "open",
        "created_at": observed_at.isoformat(),
        "gate_status": gate_envelope.get("gate_status"),
        "human_go_token_present": bool(audit.get("human_go_token_present")),
    }
    return row


def audit_observation_row_is_redacted(row: Mapping[str, Any]) -> bool:
    """Return True when serialized row contains no raw GO token keys or values."""
    if _FORBIDDEN_KEYS.intersection(row.keys()):
        return False
    serialized = json.dumps(dict(row), default=str)
    if '"human_go_token"' in serialized:
        return False
    return True
