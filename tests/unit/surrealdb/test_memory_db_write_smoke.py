"""Unit tests for memory_db_write_smoke — #2606 Slice 6.

No DB. Mock SQL client. Gate-blocked paths must not call upsert_create.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_db_write_smoke import (
    WRITE_SMOKE_ENV_VAR,
    MemoryWriteSmokeError,
    execute_gated_local_memory_write_v1,
    local_write_smoke_enabled,
    write_smoke_env_enabled,
)
from tools.surrealdb.memory_write_gate import MemoryWriteAuthorization

FIXED_NOW = datetime(2026, 5, 29, 14, 0, 0, tzinfo=timezone.utc)


def _valid_record(**overrides) -> dict:
    base: dict = {
        "scope": "memory_db_write_smoke:abc123",
        "namespace": "memory_db_write_smoke:abc123",
        "memory_type": "semantic_memory",
        "content": "Slice 6 unit test memory record.",
        "source_refs": ["docs/surrealdb/memory-write-gate-v1.md"],
        "evidence_refs": ["ev-mdbwrite-base-001"],
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
        human_go_token="GO-2026-05-29-slice6",
        authorized_by="jannekbuengener",
        authorized_at="2026-05-29T14:00:00+00:00",
        scope="memory_db_write_smoke:abc123",
        target_issue="2694",
        evidence_refs=("github:issue/2694",),
        operation="create",
    )
    base.update(overrides)
    return MemoryWriteAuthorization(**base)


def _mock_sql() -> MagicMock:
    client = MagicMock()
    client.record_exists.return_value = False
    return client


@pytest.mark.unit
def test_write_smoke_env_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(WRITE_SMOKE_ENV_VAR, raising=False)
    assert write_smoke_env_enabled() is False


@pytest.mark.unit
def test_local_write_smoke_enabled_requires_env_and_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(WRITE_SMOKE_ENV_VAR, "1")
    assert local_write_smoke_enabled(
        {"gate_status": "approved_dry_run", "persist_allowed": False}
    )
    assert not local_write_smoke_enabled(
        {"gate_status": "blocked_no_human_go", "persist_allowed": False}
    )
    monkeypatch.delenv(WRITE_SMOKE_ENV_VAR, raising=False)
    assert not local_write_smoke_enabled(
        {"gate_status": "approved_dry_run", "persist_allowed": False}
    )


@pytest.mark.unit
def test_execute_blocked_without_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(WRITE_SMOKE_ENV_VAR, "1")
    sql = _mock_sql()
    with pytest.raises(MemoryWriteSmokeError, match="blocked"):
        execute_gated_local_memory_write_v1(
            record=_valid_record(),
            authorization=None,  # type: ignore[arg-type]
            sql_client=sql,
            evidence_record={"evidence_id": "ev-1"},
            evidence_id="ev-1",
            now=FIXED_NOW,
        )
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_execute_blocked_invalid_go_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(WRITE_SMOKE_ENV_VAR, "1")
    sql = _mock_sql()
    auth = _valid_auth(human_go_token="not-a-go-token")
    with pytest.raises(MemoryWriteSmokeError, match="blocked"):
        execute_gated_local_memory_write_v1(
            record=_valid_record(),
            authorization=auth,
            sql_client=sql,
            evidence_record={"evidence_id": "ev-1"},
            evidence_id="ev-1",
            now=FIXED_NOW,
        )
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_execute_blocked_without_env_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(WRITE_SMOKE_ENV_VAR, raising=False)
    sql = _mock_sql()
    record = _valid_record()
    auth = _valid_auth(scope=record["scope"])
    with pytest.raises(MemoryWriteSmokeError, match=WRITE_SMOKE_ENV_VAR):
        execute_gated_local_memory_write_v1(
            record=record,
            authorization=auth,
            sql_client=sql,
            evidence_record={"evidence_id": "ev-1", "comment": "test"},
            evidence_id="ev-1",
            now=FIXED_NOW,
        )
    sql.upsert_create.assert_not_called()


@pytest.mark.unit
def test_execute_writes_when_gate_and_env_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(WRITE_SMOKE_ENV_VAR, "1")
    sql = _mock_sql()

    def exists_side_effect(table: str, raw_id: str, *, id_field: str) -> bool:
        if sql.upsert_create.call_count == 0:
            return False
        return True

    sql.record_exists.side_effect = exists_side_effect

    record = _valid_record()
    auth = _valid_auth(scope=record["scope"])
    evidence_id = "ev-mdbwrite-unit-001"
    result = execute_gated_local_memory_write_v1(
        record=record,
        authorization=auth,
        sql_client=sql,
        evidence_record={
            "evidence_id": evidence_id,
            "comment": "unit test evidence",
        },
        evidence_id=evidence_id,
        now=FIXED_NOW,
    )
    assert result["write_status"] == "written_local_only"
    assert sql.upsert_create.call_count == 2
    calls = [c.args[0] for c in sql.upsert_create.call_args_list]
    assert calls == ["evidence_ref", "agent_memory"]
    rendered = str(result)
    assert auth.human_go_token not in rendered
