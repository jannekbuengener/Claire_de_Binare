"""Unit tests for memory_write_gate — #2606 Memory Reality Slice 5.

No DB. No MCP. No persistence. Harness must not invoke write executors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_write_gate import (
    GATE_SCHEMA_VERSION,
    PERSIST_ALLOWED,
    MemoryWriteAuthorization,
    evaluate_memory_write_gate,
    run_memory_write_gate_harness,
)

FIXED_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "agent:TEST/cursor",
        "namespace": "session",
        "memory_type": "working_memory",
        "content": "Test memory content for slice 5 gate",
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
        human_go_token="GO-2026-05-29-slice5",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-29T11:00:00+00:00",
        scope="agent:TEST/cursor",
        target_issue="2606",
        evidence_refs=("github:issue/2606",),
        operation="create",
    )
    base.update(overrides)
    return MemoryWriteAuthorization(**base)


@pytest.mark.unit
def test_persist_allowed_is_false() -> None:
    assert PERSIST_ALLOWED is False


@pytest.mark.unit
def test_blocked_without_authorization() -> None:
    result = evaluate_memory_write_gate(_valid_record(), None, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_no_authorization"
    assert result["persist_allowed"] is False
    assert result["approval_semantics"]["no_write"] is True


@pytest.mark.unit
def test_blocked_empty_human_go_token() -> None:
    auth = _valid_auth(human_go_token="")
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_no_human_go"


@pytest.mark.unit
def test_blocked_invalid_human_go_token_shape() -> None:
    auth = _valid_auth(human_go_token="approved-by-agent")
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_no_human_go"


@pytest.mark.unit
def test_blocked_scope_mismatch() -> None:
    auth = _valid_auth(scope="agent:OTHER/scope")
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_scope_mismatch"
    assert result["memory_id"] is not None


@pytest.mark.unit
def test_blocked_missing_authorization_evidence_refs() -> None:
    auth = _valid_auth(evidence_refs=())
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_missing_evidence"


@pytest.mark.unit
def test_blocked_missing_target_issue() -> None:
    auth = _valid_auth(target_issue="  ")
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_missing_evidence"


@pytest.mark.unit
def test_blocked_contract_violation() -> None:
    record = _valid_record(evidence_refs=[])
    auth = _valid_auth()
    result = evaluate_memory_write_gate(record, auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_contract_violation"


@pytest.mark.unit
def test_blocked_agent_self_asserted_go_field() -> None:
    record = _valid_record(human_go=True)
    auth = _valid_auth()
    result = evaluate_memory_write_gate(record, auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_agent_self_asserted_go"


@pytest.mark.unit
def test_blocked_supersede_without_target() -> None:
    auth = _valid_auth(operation="supersede")
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "blocked_supersede_requires_target"


@pytest.mark.unit
def test_approved_dry_run_with_valid_inputs() -> None:
    auth = _valid_auth()
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    assert result["gate_status"] == "approved_dry_run"
    assert result["persist_allowed"] is False
    assert result["dry_run_only"] is True
    assert result["schema_version"] == GATE_SCHEMA_VERSION
    assert result["validated_record"]["memory_id"] == result["memory_id"]
    assert result["audit"]["human_go_token_present"] is True
    assert result["audit"]["severity"] == "info"
    assert "gate_pass_does_not_persist" in result["limitations"]


@pytest.mark.unit
def test_supersede_passes_with_superseded_by() -> None:
    record = _valid_record(superseded_by="previous-memory-id")
    auth = _valid_auth(operation="supersede")
    result = evaluate_memory_write_gate(record, auth, now=FIXED_NOW)
    assert result["gate_status"] == "approved_dry_run"


@pytest.mark.unit
def test_observation_id_deterministic() -> None:
    auth = _valid_auth()
    record = _valid_record()
    first = evaluate_memory_write_gate(record, auth, now=FIXED_NOW)
    second = evaluate_memory_write_gate(record, auth, now=FIXED_NOW)
    assert first["audit"]["observation_id"] == second["audit"]["observation_id"]


@pytest.mark.unit
def test_harness_does_not_call_write_executor_on_block() -> None:
    executor = MagicMock()
    run_memory_write_gate_harness(_valid_record(), None, executor, now=FIXED_NOW)
    executor.assert_not_called()


@pytest.mark.unit
def test_harness_does_not_call_write_executor_on_pass() -> None:
    executor = MagicMock()
    run_memory_write_gate_harness(
        _valid_record(),
        _valid_auth(),
        executor,
        now=FIXED_NOW,
    )
    executor.assert_not_called()
