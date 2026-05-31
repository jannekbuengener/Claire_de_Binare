"""Unit tests for memory_write_path_t4 — G4 #2758."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_write_gate import PERSIST_ALLOWED
from tools.surrealdb import memory_write_path_t4 as t4_module
from tools.surrealdb.memory_write_path_t4 import (
    PRODUCTIVE_ACTIVATED,
    PRODUCTIVE_ENV_VAR,
    PROOF_SCOPE,
    T4WriteAuthorization,
    run_memory_write_path_t4,
)

FIXED_NOW = datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc)


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": f"memory_write_path_t4:{PROOF_SCOPE}",
        "namespace": f"memory_write_path_t4:{PROOF_SCOPE}",
        "memory_type": "semantic_memory",
        "content": "G4 T4 agent_memory path unit test record.",
        "source_refs": ["docs/surrealdb/memory-write-path-t4-runbook-v1.md"],
        "evidence_refs": ["ev-g4-t4-001"],
        "confidence": 0.9,
        "ttl": 86400,
        "expires_at": "2026-06-01T10:00:00Z",
        "created_by": "cdb-test-g4-t4",
        "created_at": "2026-05-31T10:00:00Z",
    }
    base.update(overrides)
    from tools.surrealdb.memory_contract import generate_memory_id

    base["memory_id"] = generate_memory_id(
        scope=base["scope"],
        namespace=base["namespace"],
        memory_type=base["memory_type"],
        created_by=base["created_by"],
        content=base["content"],
        source_refs=base["source_refs"],
    )
    return base


def _valid_auth(**overrides) -> T4WriteAuthorization:
    base = dict(
        human_go_token="GO-2026-05-31-hgw",
        human_go_tier="HG-W",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-31T12:00:00+00:00",
        scope=f"memory_write_path_t4:{PROOF_SCOPE}",
        target_issue="2758",
        evidence_refs=("github:issue/2758",),
        operation="create",
    )
    base.update(overrides)
    return T4WriteAuthorization(**base)


class _MockSink:
    def __init__(self, *, mode: str = "mock") -> None:
        self._mode = mode
        self._audit_rows: dict[str, dict[str, Any]] = {}
        self._memory_rows: dict[str, dict[str, Any]] = {}
        self.call_order: list[str] = []

    def mode(self) -> str:
        return self._mode

    def upsert_audit_observation(
        self, observation_id: str, payload: Mapping[str, Any]
    ) -> None:
        self.call_order.append("upsert_audit_observation")
        self._audit_rows[observation_id] = dict(payload)

    def observation_exists(self, observation_id: str) -> bool:
        return observation_id in self._audit_rows

    def upsert_agent_memory(self, memory_id: str, payload: Mapping[str, Any]) -> None:
        self.call_order.append("upsert_agent_memory")
        self._memory_rows[memory_id] = dict(payload)

    def memory_exists(self, memory_id: str) -> bool:
        return memory_id in self._memory_rows


@pytest.mark.unit
def test_defaults_fail_closed() -> None:
    assert PRODUCTIVE_ACTIVATED is False
    assert PERSIST_ALLOWED is False
    sink = _MockSink()
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(),
        mode="dry_run",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["path_status"] == "evaluated_only"
    assert result["tables_written"] == []
    assert result["agent_memory_written"] is False
    assert not sink._audit_rows
    assert not sink._memory_rows


@pytest.mark.unit
def test_no_write_without_hgw() -> None:
    sink = _MockSink()
    for tier in ("HG-L", "HG-P"):
        result = run_memory_write_path_t4(
            _valid_record(),
            _valid_auth(human_go_tier=tier),
            mode="agent_memory_persist_productive",
            sink=sink,
            now=FIXED_NOW,
        )
        assert result["status"] == "refused"
        assert result["code"] == "hg_w_required"
    assert not sink._audit_rows


@pytest.mark.unit
def test_no_write_when_persist_allowed_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink()
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "ok"
    assert result["path_status"] == "mock_persisted_audit_only"
    assert result["agent_memory_written"] is False
    assert "agent_memory" not in result["tables_written"]
    assert result["tables_written"] == ["audit_observation"]
    assert len(sink._audit_rows) == 1
    assert not sink._memory_rows


@pytest.mark.unit
def test_exactly_one_scoped_proof_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    monkeypatch.setattr(t4_module, "PERSIST_ALLOWED", True)
    sink = _MockSink()
    record = _valid_record()
    auth = _valid_auth()
    first = run_memory_write_path_t4(
        record,
        auth,
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert first["status"] == "ok"
    assert first["agent_memory_written"] is True
    assert set(first["tables_written"]) == {"audit_observation", "agent_memory"}

    second = run_memory_write_path_t4(
        record,
        auth,
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert second["status"] == "refused"
    assert second["code"] == "duplicate_observation_id"
    assert len(sink._audit_rows) == 1
    assert len(sink._memory_rows) == 1


@pytest.mark.unit
def test_duplicate_memory_id_when_persist_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    monkeypatch.setattr(t4_module, "PERSIST_ALLOWED", True)
    sink = _MockSink()
    record = _valid_record()
    memory_id = record["memory_id"]
    sink._memory_rows[memory_id] = {"memory_id": memory_id}

    result = run_memory_write_path_t4(
        record,
        _valid_auth(),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "duplicate_memory_id"
    assert result["tables_written"] == ["audit_observation"]
    assert len(sink._audit_rows) == 1
    assert len(sink._memory_rows) == 1


@pytest.mark.unit
def test_audit_observation_emitted_before_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    monkeypatch.setattr(t4_module, "PERSIST_ALLOWED", True)
    sink = _MockSink()
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "ok"
    assert sink.call_order == ["upsert_audit_observation", "upsert_agent_memory"]
    assert result["audit_observation"] is not None
    assert result["audit_observation"]["observation_type"] == (
        "memory_write_gate_evaluation"
    )


@pytest.mark.unit
def test_no_secrets_raw_token_persisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "GO-2026-05-31-hgw-secret"
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(human_go_token=token),
        mode="dry_run",
        now=FIXED_NOW,
    )
    serialized = json.dumps(result)
    assert token not in serialized
    assert "human_go_token" not in serialized

    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink()
    persist_result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(human_go_token=token),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    persist_serialized = json.dumps(persist_result)
    assert token not in persist_serialized
    for row in sink._audit_rows.values():
        assert token not in json.dumps(row)


@pytest.mark.unit
def test_gate_blocked_no_sql() -> None:
    sink = _MockSink()
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(scope="wrong-scope"),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "gate_blocked"
    assert not sink._audit_rows
    assert sink.call_order == []


@pytest.mark.unit
def test_localhost_endpoint_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink()
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
        endpoint_url="https://127.0.0.1:8011",
    )
    assert result["status"] == "refused"
    assert result["code"] == "localhost_endpoint_refused"
    assert not sink._audit_rows


@pytest.mark.unit
def test_forbidden_keys_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink()
    record = _valid_record()
    auth = _valid_auth()
    from tools.surrealdb.memory_write_gate import (
        MemoryWriteAuthorization,
        evaluate_memory_write_gate,
    )

    gate_envelope = evaluate_memory_write_gate(
        record,
        MemoryWriteAuthorization(
            human_go_token=auth.human_go_token,
            authorized_by=auth.authorized_by,
            authorized_at=auth.authorized_at,
            scope=auth.scope,
            target_issue=auth.target_issue,
            evidence_refs=auth.evidence_refs,
            operation=auth.operation,
        ),
        now=FIXED_NOW,
    )
    gate_envelope = dict(gate_envelope)
    audit = dict(gate_envelope["audit"])
    audit["human_go_token"] = "LEAK"
    gate_envelope["audit"] = audit

    original_eval = evaluate_memory_write_gate

    def patched_eval(*args, **kwargs):
        if kwargs.get("now") == FIXED_NOW and args[0] is record:
            return gate_envelope
        return original_eval(*args, **kwargs)

    monkeypatch.setattr(
        "tools.surrealdb.memory_write_path_t4.evaluate_memory_write_gate",
        patched_eval,
    )
    result = run_memory_write_path_t4(
        record,
        auth,
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "forbidden_key_present"


@pytest.mark.unit
def test_mcp_still_blocks_agent_memory_write() -> None:
    from tools.mcp.memory_write_intent_tools import (
        MUTATION_ALLOWED,
        handle_cdb_context_memory_write_intent,
    )

    assert MUTATION_ALLOWED is False
    response = handle_cdb_context_memory_write_intent(
        {
            "tool": "cdb_context_memory_write_intent",
            "parameters": {
                "record": _valid_record(),
                "authorization": {
                    "human_go_token": "GO-2026-05-31-hgw",
                    "authorized_by": "jannekbuengener",
                    "authorized_at": "2026-05-31T12:00:00+00:00",
                    "scope": _valid_record()["scope"],
                    "target_issue": "2758",
                    "evidence_refs": ["github:issue/2758"],
                    "operation": "create",
                },
                "operation_mode": "agent_memory_write",
            },
        }
    )
    assert response["status"] == "refused"
    assert response["code"] == "agent_memory_write_not_activated"


@pytest.mark.unit
def test_agent_memory_row_uses_validated_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    monkeypatch.setattr(t4_module, "PERSIST_ALLOWED", True)
    sink = _MockSink()
    record = _valid_record()
    result = run_memory_write_path_t4(
        record,
        _valid_auth(),
        mode="agent_memory_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "ok"
    memory_row = sink._memory_rows[record["memory_id"]]
    assert memory_row["scope"] == record["scope"]
    assert memory_row["content"] == record["content"]
    assert memory_row["namespace"] == record["namespace"]


@pytest.mark.unit
def test_dry_run_evaluates_gate_only() -> None:
    sink = _MockSink()
    result = run_memory_write_path_t4(
        _valid_record(),
        _valid_auth(),
        mode="dry_run",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["path_status"] == "evaluated_only"
    assert result["gate_status"] == "approved_dry_run"
    assert not sink._audit_rows
