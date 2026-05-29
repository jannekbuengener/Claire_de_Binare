"""Unit tests for DB-backed memory read proof helper — #2606 Slice 4."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_contract import (
    MemoryContractError,
    generate_memory_id,
    validate_memory_id_matches_record,
)
from tools.surrealdb.memory_db_read_proof import prove_agent_memory_db_read_v1

_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
_SCOPE = "memory_db_proof"


def _fresh_record(**overrides: Any) -> dict[str, Any]:
    base = {
        "memory_id": "988581e3-7003-5e93-a847-9dcfe2d4633f",
        "scope": _SCOPE,
        "namespace": _SCOPE,
        "memory_type": "semantic_memory",
        "content": "Fresh memory for DB read proof slice 4.",
        "source_refs": ["docs/surrealdb/memory-reality-slice1-audit.md"],
        "evidence_refs": ["ev-mdbproof-base-001"],
        "confidence": 0.9,
        "ttl": 86400,
        "created_by": "cdb-test-001",
        "created_at": "2026-05-29T10:00:00Z",
        "expires_at": "2026-05-30T10:00:00Z",
        "run_id": "seed-run",
        "schema_version": "context-indexer/v0",
        "id": "agent_memory:seed",
        "sensitivity": "internal",
    }
    base.update(overrides)
    base["memory_id"] = generate_memory_id(
        scope=base["scope"],
        namespace=base["namespace"],
        memory_type=base["memory_type"],
        created_by=base["created_by"],
        content=base["content"],
        source_refs=base["source_refs"],
    )
    return base


def _expired_record(**overrides: Any) -> dict[str, Any]:
    base = {
        "scope": _SCOPE,
        "namespace": _SCOPE,
        "memory_type": "semantic_memory",
        "content": "Expired memory for DB read proof slice 4.",
        "source_refs": ["docs/surrealdb/memory-reality-slice1-audit.md"],
        "evidence_refs": ["ev-mdbproof-base-002"],
        "confidence": 0.85,
        "ttl": 3600,
        "created_by": "cdb-test-001",
        "created_at": "2026-05-01T10:00:00Z",
        "expires_at": "2026-05-01T11:00:00Z",
    }
    base.update(overrides)
    base["memory_id"] = generate_memory_id(
        scope=base["scope"],
        namespace=base["namespace"],
        memory_type=base["memory_type"],
        created_by=base["created_by"],
        content=base["content"],
        source_refs=base["source_refs"],
    )
    return base


def _mock_adapter(rows: list[dict[str, Any]]) -> MagicMock:
    adapter = MagicMock()
    adapter.status = "surrealdb-local"
    adapter.execute.return_value = rows
    return adapter


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_validates_and_classifies() -> None:
    adapter = _mock_adapter([_fresh_record(), _expired_record()])
    proof = prove_agent_memory_db_read_v1(
        adapter=adapter, scope=_SCOPE, limit=10, now=_NOW
    )

    assert proof["source"] == "surrealdb-local"
    assert proof["adapter_status"] == "surrealdb-local"
    assert proof["record_count"] == 2
    assert proof["approval_semantics"]["read_only"] is True

    by_id = {item["record"]["memory_id"]: item for item in proof["records"]}
    fresh = by_id[
        generate_memory_id(
            scope=_SCOPE,
            namespace=_SCOPE,
            memory_type="semantic_memory",
            created_by="cdb-test-001",
            content="Fresh memory for DB read proof slice 4.",
            source_refs=["docs/surrealdb/memory-reality-slice1-audit.md"],
        )
    ]
    expired = by_id[
        generate_memory_id(
            scope=_SCOPE,
            namespace=_SCOPE,
            memory_type="semantic_memory",
            created_by="cdb-test-001",
            content="Expired memory for DB read proof slice 4.",
            source_refs=["docs/surrealdb/memory-reality-slice1-audit.md"],
        )
    ]

    assert fresh["freshness"]["is_fresh"] is True
    assert fresh["freshness"]["is_expired"] is False
    assert expired["freshness"]["is_expired"] is True
    assert expired["freshness"]["is_fresh"] is False


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_strips_db_metadata() -> None:
    adapter = _mock_adapter([_fresh_record()])
    proof = prove_agent_memory_db_read_v1(
        adapter=adapter, scope=_SCOPE, limit=5, now=_NOW
    )
    record = proof["records"][0]["record"]
    assert "run_id" not in record
    assert "schema_version" not in record
    assert "id" not in record
    assert "sensitivity" not in record
    validate_memory_id_matches_record(record)


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_aggregates_evidence_refs() -> None:
    adapter = _mock_adapter([_fresh_record(), _expired_record()])
    proof = prove_agent_memory_db_read_v1(
        adapter=adapter, scope=_SCOPE, limit=10, now=_NOW
    )
    assert set(proof["evidence_refs"]) == {
        "ev-mdbproof-base-001",
        "ev-mdbproof-base-002",
    }


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_read_memory_crosscheck() -> None:
    adapter = _mock_adapter([_fresh_record(), _expired_record()])
    proof = prove_agent_memory_db_read_v1(
        adapter=adapter, scope=_SCOPE, limit=10, now=_NOW
    )
    assert proof["read_memory_crosscheck"]["matched_count"] == 2
    assert set(proof["read_memory_crosscheck"]["memory_ids"]) == set(
        proof["memory_ids"]
    )


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_unsafe_scope_rejected() -> None:
    adapter = _mock_adapter([])
    with pytest.raises(ValueError, match="not safe for SurrealQL"):
        prove_agent_memory_db_read_v1(
            adapter=adapter, scope="scope'; DROP TABLE agent_memory; --", now=_NOW
        )


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_contract_violation_fail_closed() -> None:
    bad = _fresh_record()
    bad["memory_id"] = "00000000-0000-0000-0000-000000000001"
    adapter = _mock_adapter([bad])
    with pytest.raises(MemoryContractError, match="memory_id mismatch"):
        prove_agent_memory_db_read_v1(adapter=adapter, scope=_SCOPE, now=_NOW)


@pytest.mark.unit
def test_prove_agent_memory_db_read_v1_builds_scope_filter_query() -> None:
    adapter = _mock_adapter([])
    prove_agent_memory_db_read_v1(adapter=adapter, scope=_SCOPE, limit=3, now=_NOW)
    adapter.execute.assert_called_once_with(
        f"SELECT * FROM agent_memory WHERE scope = '{_SCOPE}' LIMIT 3"
    )
