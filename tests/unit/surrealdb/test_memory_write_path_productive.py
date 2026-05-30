"""Unit tests for memory_write_path_productive — G3b #2744."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_write_gate import PERSIST_ALLOWED
from tools.surrealdb.memory_write_path_productive import (
    PRODUCTIVE_ACTIVATED,
    PRODUCTIVE_ENV_VAR,
    ProductiveWriteAuthorization,
    run_memory_write_path_productive,
)

FIXED_NOW = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "memory_write_path_productive:g3b001",
        "namespace": "memory_write_path_productive:g3b001",
        "memory_type": "semantic_memory",
        "content": "G3b productive path unit test record.",
        "source_refs": ["docs/surrealdb/productive-memory-audit-trail-endpoint-design-v1.md"],
        "evidence_refs": ["ev-g3b-001"],
        "confidence": 0.9,
        "ttl": 86400,
        "expires_at": "2026-05-31T10:00:00Z",
        "created_by": "cdb-test-g3b",
        "created_at": "2026-05-30T10:00:00Z",
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


def _valid_auth(**overrides) -> ProductiveWriteAuthorization:
    base = dict(
        human_go_token="GO-2026-05-30-g3b",
        human_go_tier="HG-P",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-30T12:00:00+00:00",
        scope="memory_write_path_productive:g3b001",
        target_issue="2744",
        evidence_refs=("github:issue/2744",),
        operation="create",
    )
    base.update(overrides)
    return ProductiveWriteAuthorization(**base)


class _MockSink:
    def __init__(self, *, mode: str = "mock") -> None:
        self._mode = mode
        self._rows: dict[str, dict[str, Any]] = {}

    def mode(self) -> str:
        return self._mode

    def upsert_audit_observation(
        self, observation_id: str, payload: Mapping[str, Any]
    ) -> None:
        self._rows[observation_id] = dict(payload)

    def observation_exists(self, observation_id: str) -> bool:
        return observation_id in self._rows


@pytest.mark.unit
def test_productive_defaults_fail_closed() -> None:
    assert PRODUCTIVE_ACTIVATED is False
    assert PERSIST_ALLOWED is False
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="dry_run",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["path_status"] == "evaluated_only"
    assert result["tables_written"] == []
    assert not sink._rows


@pytest.mark.unit
def test_dry_run_evaluates_gate_only() -> None:
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="dry_run",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["path_status"] == "evaluated_only"
    assert result["gate_status"] == "approved_dry_run"
    assert result["operation_mode_resolved"] == "dry_run"
    assert not sink._rows


@pytest.mark.unit
def test_productive_mode_refused_without_authorization() -> None:
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        None,
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "no_authorization"
    assert not sink._rows


@pytest.mark.unit
def test_productive_mode_refused_hg_l() -> None:
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(human_go_tier="HG-L"),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "hg_p_required"


@pytest.mark.unit
def test_productive_mode_refused_invalid_tier() -> None:
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(human_go_tier="HG-W"),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "hg_p_required"


@pytest.mark.unit
def test_productive_mode_refused_when_gate_blocked() -> None:
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(scope="wrong-scope"),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "gate_blocked"


@pytest.mark.unit
def test_productive_mode_refused_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(PRODUCTIVE_ENV_VAR, raising=False)
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "productive_env_missing"


@pytest.mark.unit
def test_productive_mode_refused_without_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_productive",
        sink=None,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "mock_sink_required"


@pytest.mark.unit
def test_productive_mode_refused_non_mock_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink(mode="real")
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "refused"
    assert result["code"] == "mock_sink_invalid_mode"


@pytest.mark.unit
def test_productive_mode_mock_persist_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink()
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert result["status"] == "ok"
    assert result["path_status"] == "mock_persisted_productive_audit"
    assert result["tables_written"] == ["audit_observation"]
    assert result["sink_mode"] == "mock"
    assert result["productive_audit_status"] == "mock_persisted"
    assert len(sink._rows) == 1
    assert result["audit_observation"]["observation_type"] == (
        "memory_write_gate_evaluation"
    )


@pytest.mark.unit
def test_productive_mode_refuses_duplicate_observation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRODUCTIVE_ENV_VAR, "1")
    sink = _MockSink()
    first = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert first["status"] == "ok"
    second = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_productive",
        sink=sink,
        now=FIXED_NOW,
    )
    assert second["status"] == "refused"
    assert second["code"] == "duplicate_observation_id"
    assert len(sink._rows) == 1


@pytest.mark.unit
def test_response_never_contains_raw_human_go_token() -> None:
    token = "GO-2026-05-30-g3b-secret"
    result = run_memory_write_path_productive(
        _valid_record(),
        _valid_auth(human_go_token=token),
        mode="dry_run",
        now=FIXED_NOW,
    )
    serialized = json.dumps(result)
    assert token not in serialized
    assert "human_go_token" not in serialized


@pytest.mark.unit
def test_forbidden_keys_in_audit_payload_blocked(
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

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(PRODUCTIVE_ENV_VAR, "1")
        original_eval = evaluate_memory_write_gate

        def patched_eval(*args, **kwargs):
            if kwargs.get("now") == FIXED_NOW and args[0] is record:
                return gate_envelope
            return original_eval(*args, **kwargs)

        mp.setattr(
            "tools.surrealdb.memory_write_path_productive.evaluate_memory_write_gate",
            patched_eval,
        )
        result = run_memory_write_path_productive(
            record,
            auth,
            mode="audit_persist_productive",
            sink=sink,
            now=FIXED_NOW,
        )
    assert result["status"] == "refused"
    assert result["code"] == "forbidden_key_present"


@pytest.mark.unit
def test_deterministic_envelope_for_same_inputs() -> None:
    record = _valid_record()
    auth = _valid_auth()
    first = run_memory_write_path_productive(
        record,
        auth,
        mode="dry_run",
        now=FIXED_NOW,
    )
    second = run_memory_write_path_productive(
        record,
        auth,
        mode="dry_run",
        now=FIXED_NOW,
    )
    assert first["gate"]["audit"]["observation_id"] == (
        second["gate"]["audit"]["observation_id"]
    )
    assert first["memory_id"] == second["memory_id"]
    assert first["gate_status"] == second["gate_status"]
