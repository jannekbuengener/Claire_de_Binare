"""Unit tests for audit_observation_from_gate — #2703."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tools.surrealdb.audit_observation_from_gate import (
    AuditObservationMaterializeError,
    audit_observation_row_is_redacted,
    materialize_audit_observation_from_gate,
)
from tools.surrealdb.memory_write_gate import (
    MemoryWriteAuthorization,
    evaluate_memory_write_gate,
)

FIXED_NOW = datetime(2026, 5, 29, 15, 0, 0, tzinfo=timezone.utc)


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "agent:TEST/cursor",
        "namespace": "session",
        "memory_type": "working_memory",
        "content": "Test memory content for path v1",
        "source_refs": ["docs/AGENTS.md@abc123"],
        "evidence_refs": ["ev-001"],
        "confidence": 0.9,
        "ttl": 3600,
        "expires_at": "2026-05-30T00:00:00+00:00",
        "created_by": "cursor-agent-v1",
        "created_at": "2026-05-29T04:00:00+00:00",
    }
    base.update(overrides)
    return base


def _valid_auth(**overrides) -> MemoryWriteAuthorization:
    base = dict(
        human_go_token="GO-2026-05-29-pathv1",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-29T15:00:00+00:00",
        scope="agent:TEST/cursor",
        target_issue="2703",
        evidence_refs=("github:issue/2703",),
        operation="create",
    )
    base.update(overrides)
    return MemoryWriteAuthorization(**base)


@pytest.mark.unit
def test_materialize_maps_required_fields() -> None:
    envelope = evaluate_memory_write_gate(_valid_record(), _valid_auth(), now=FIXED_NOW)
    row = materialize_audit_observation_from_gate(envelope, now=FIXED_NOW)
    assert row["observation_type"] == "memory_write_gate_evaluation"
    assert row["status"] == "open"
    assert row["severity"] == "info"
    assert row["observation_id"] == envelope["audit"]["observation_id"]
    assert row["subject_ref"].startswith("agent_memory:")
    assert audit_observation_row_is_redacted(row)


@pytest.mark.unit
def test_materialize_blocked_gate() -> None:
    envelope = evaluate_memory_write_gate(_valid_record(), None, now=FIXED_NOW)
    row = materialize_audit_observation_from_gate(envelope, now=FIXED_NOW)
    assert row["severity"] == "blocking"
    assert row["subject_ref"] == "audit_observation:unknown_subject"


@pytest.mark.unit
def test_materialize_rejects_forbidden_audit_key() -> None:
    envelope = evaluate_memory_write_gate(_valid_record(), _valid_auth(), now=FIXED_NOW)
    bad = dict(envelope)
    audit = dict(bad["audit"])
    audit["human_go_token"] = "GO-2026-05-29-secret"
    bad["audit"] = audit
    with pytest.raises(AuditObservationMaterializeError, match="forbidden"):
        materialize_audit_observation_from_gate(bad, now=FIXED_NOW)
