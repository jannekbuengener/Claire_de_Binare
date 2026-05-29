"""Unit tests for memory_write_path_v1 — #2703."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_write_gate import (
    PERSIST_ALLOWED,
    MemoryWriteAuthorization,
)
from tools.surrealdb.memory_write_path_v1 import (
    AUDIT_PERSIST_ENV_VAR,
    MemoryWritePathError,
    audit_persist_env_enabled,
    run_memory_write_path_v1,
)

FIXED_NOW = datetime(2026, 5, 29, 15, 30, 0, tzinfo=timezone.utc)


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "memory_write_path:abc123",
        "namespace": "memory_write_path:abc123",
        "memory_type": "semantic_memory",
        "content": "Path v1 unit test record.",
        "source_refs": ["docs/surrealdb/memory-write-path-v1-runbook.md"],
        "evidence_refs": ["ev-path-001"],
        "confidence": 0.9,
        "ttl": 86400,
        "expires_at": "2026-05-30T10:00:00Z",
        "created_by": "cdb-test-001",
        "created_at": "2026-05-29T10:00:00Z",
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


def _valid_auth(**overrides) -> MemoryWriteAuthorization:
    base = dict(
        human_go_token="GO-2026-05-29-pathv1",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-29T15:30:00+00:00",
        scope="memory_write_path:abc123",
        target_issue="2703",
        evidence_refs=("github:issue/2703",),
        operation="create",
    )
    base.update(overrides)
    return MemoryWriteAuthorization(**base)


def _mock_sql() -> MagicMock:
    client = MagicMock()
    client.record_exists.return_value = False
    return client


@pytest.mark.unit
def test_persist_allowed_unchanged() -> None:
    assert PERSIST_ALLOWED is False


@pytest.mark.unit
def test_dry_run_no_sql_calls() -> None:
    sql = _mock_sql()
    result = run_memory_write_path_v1(
        _valid_record(),
        _valid_auth(),
        mode="dry_run",
        sql_client=sql,
        now=FIXED_NOW,
    )
    assert result["path_status"] == "evaluated_only"
    assert result["gate_status"] == "approved_dry_run"
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_blocked_without_authorization() -> None:
    sql = _mock_sql()
    result = run_memory_write_path_v1(
        _valid_record(),
        None,
        mode="dry_run",
        sql_client=sql,
        now=FIXED_NOW,
    )
    assert result["gate_status"] == "blocked_no_authorization"
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_audit_persist_blocked_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(AUDIT_PERSIST_ENV_VAR, raising=False)
    sql = _mock_sql()
    with pytest.raises(MemoryWritePathError, match=AUDIT_PERSIST_ENV_VAR):
        run_memory_write_path_v1(
            _valid_record(),
            _valid_auth(),
            mode="audit_persist_local",
            sql_client=sql,
            now=FIXED_NOW,
        )
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_audit_persist_blocked_when_gate_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(AUDIT_PERSIST_ENV_VAR, "1")
    sql = _mock_sql()
    with pytest.raises(MemoryWritePathError, match="gate_status"):
        run_memory_write_path_v1(
            _valid_record(),
            None,
            mode="audit_persist_local",
            sql_client=sql,
            now=FIXED_NOW,
        )
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_audit_persist_writes_one_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(AUDIT_PERSIST_ENV_VAR, "1")
    sql = _mock_sql()
    seen: set[str] = set()

    def record_exists(table: str, raw_id: str, *, id_field: str) -> bool:
        return raw_id in seen

    def upsert_create(table: str, record_id: str, payload: dict) -> None:
        seen.add(record_id)

    sql.record_exists.side_effect = record_exists
    sql.upsert_create.side_effect = upsert_create
    result = run_memory_write_path_v1(
        _valid_record(),
        _valid_auth(),
        mode="audit_persist_local",
        sql_client=sql,
        now=FIXED_NOW,
    )
    assert result["path_status"] == "audit_persisted_local"
    assert result["tables_written"] == ["audit_observation"]
    assert result["audit_observation"]["observation_type"] == (
        "memory_write_gate_evaluation"
    )
    sql.upsert_create.assert_called_once()
    assert sql.upsert_create.call_args.args[0] == "audit_observation"


@pytest.mark.unit
def test_audit_persist_env_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(AUDIT_PERSIST_ENV_VAR, raising=False)
    assert audit_persist_env_enabled() is False
