"""Unit tests for memory_write_gate — #2606 Memory Reality Slice 5.

No DB. No MCP. No persistence. Harness must not invoke write executors.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_write_gate import (
    GATE_SCHEMA_VERSION,
    PERSIST_ALLOWED,
    PERSIST_ENV_VAR,
    PROOF_SCOPE_HGW_2759,
    MemoryWriteAuthorization,
    approved_for_persist,
    evaluate_memory_write_gate,
    persist_env_enabled,
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


@pytest.mark.unit
def test_envelope_never_contains_raw_human_go_token() -> None:
    token = "GO-2026-05-29-slice5-secret"
    auth = _valid_auth(human_go_token=token)
    result = evaluate_memory_write_gate(_valid_record(), auth, now=FIXED_NOW)
    serialized = json.dumps(result, default=str)
    assert token not in serialized
    assert '"human_go_token"' not in serialized


def _hgw_auth(**overrides) -> MemoryWriteAuthorization:
    base = dict(
        human_go_token="GO-2026-05-31-hgw",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-31T12:00:00+00:00",
        scope=f"memory_write_path_t4:{PROOF_SCOPE_HGW_2759}",
        target_issue="2759",
        evidence_refs=("github:issue/2759",),
        operation="create",
    )
    base.update(overrides)
    return MemoryWriteAuthorization(**base)


@pytest.mark.unit
def test_persist_env_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PERSIST_ENV_VAR, raising=False)
    assert persist_env_enabled() is False


@pytest.mark.unit
def test_approved_for_persist_false_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(PERSIST_ENV_VAR, raising=False)
    assert (
        approved_for_persist(_hgw_auth(), human_go_tier="HG-W") is False
    )


@pytest.mark.unit
def test_approved_for_persist_false_without_hgw_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    for tier in ("HG-P", "HG-L", ""):
        assert (
            approved_for_persist(_hgw_auth(), human_go_tier=tier) is False
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "target_issue",
    ["12759", "27590", "not-2759", "issue/27590"],
)
def test_approved_for_persist_false_for_non_exact_target_issue(
    monkeypatch: pytest.MonkeyPatch,
    target_issue: str,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    assert (
        approved_for_persist(
            _hgw_auth(target_issue=target_issue),
            human_go_tier="HG-W",
        )
        is False
    )


@pytest.mark.unit
def test_approved_for_persist_true_for_github_issue_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    assert (
        approved_for_persist(
            _hgw_auth(target_issue="github:issue/2759"),
            human_go_tier="HG-W",
        )
        is True
    )


@pytest.mark.unit
def test_approved_for_persist_false_without_target_issue_2759(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    assert (
        approved_for_persist(
            _hgw_auth(target_issue="2758"),
            human_go_tier="HG-W",
        )
        is False
    )


@pytest.mark.unit
def test_approved_for_persist_false_without_valid_go_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    assert (
        approved_for_persist(
            _hgw_auth(human_go_token="invalid-token"),
            human_go_tier="HG-W",
        )
        is False
    )


@pytest.mark.unit
def test_approved_for_persist_false_wrong_proof_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    assert (
        approved_for_persist(
            _hgw_auth(scope="memory_write_path_t4:wrong-scope"),
            human_go_tier="HG-W",
        )
        is False
    )


@pytest.mark.unit
def test_approved_for_persist_true_under_full_hgw_conditions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PERSIST_ENV_VAR, "1")
    assert PERSIST_ALLOWED is False
    assert approved_for_persist(_hgw_auth(), human_go_tier="HG-W") is True
