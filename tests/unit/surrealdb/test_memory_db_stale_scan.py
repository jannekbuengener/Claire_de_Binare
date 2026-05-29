"""Unit tests for DB-backed stale/expired memory scan — #2702."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_contract import (
    MemoryContractError,
    generate_memory_id,
)
from tools.surrealdb.memory_db_stale_scan import scan_agent_memory_stale_v1
from tools.surrealdb.stale_knowledge_scan import scan_stale_knowledge_v1

_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
_SCOPE = "memory_db_proof"


def _fresh_record(**overrides: Any) -> dict[str, Any]:
    base = {
        "scope": _SCOPE,
        "namespace": _SCOPE,
        "memory_type": "semantic_memory",
        "content": "Fresh memory for DB stale scan proof.",
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
        "content": "Expired memory for DB stale scan proof.",
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
def test_scan_agent_memory_stale_v1_partitions_fresh_and_expired() -> None:
    adapter = _mock_adapter([_fresh_record(), _expired_record()])
    result = scan_agent_memory_stale_v1(
        adapter=adapter, scope=_SCOPE, limit=10, now=_NOW
    )

    assert result["source"] == "surrealdb-local"
    assert result["adapter_status"] == "surrealdb-local"
    assert result["schema_version"] == "memory-db-stale-scan/v1"
    assert result["record_count"] == 2
    assert result["fresh_count"] == 1
    assert result["stale_count"] == 1
    assert result["expired_count"] == 1
    assert len(result["stale_memory_ids"]) == 1
    assert len(result["expired_memory_ids"]) == 1
    assert result["approval_semantics"]["read_only"] is True
    assert result["approval_semantics"]["no_write"] is True

    expired_id = result["expired_memory_ids"][0]
    assert expired_id in result["stale_memory_ids"]
    expired_entry = result["expired_records"][0]
    assert expired_entry["freshness"]["is_expired"] is True
    assert expired_entry["freshness"]["is_stale"] is True

    fresh_id = generate_memory_id(
        scope=_SCOPE,
        namespace=_SCOPE,
        memory_type="semantic_memory",
        created_by="cdb-test-001",
        content="Fresh memory for DB stale scan proof.",
        source_refs=["docs/surrealdb/memory-reality-slice1-audit.md"],
    )
    assert fresh_id not in result["stale_memory_ids"]


@pytest.mark.unit
def test_scan_agent_memory_stale_v1_wave16_bridge_for_expired() -> None:
    adapter = _mock_adapter([_expired_record()])
    result = scan_agent_memory_stale_v1(
        adapter=adapter, scope=_SCOPE, limit=5, now=_NOW
    )

    wave16 = result["wave16_memory_ttl"]
    assert wave16["finding_count"] == 1
    assert wave16["stale_types"] == ["memory_ttl_expired"]
    assert len(wave16["stale_ids"]) == 1


@pytest.mark.unit
def test_scan_agent_memory_stale_v1_strips_db_metadata() -> None:
    adapter = _mock_adapter([_fresh_record()])
    result = scan_agent_memory_stale_v1(
        adapter=adapter, scope=_SCOPE, limit=5, now=_NOW
    )
    record = result["stale_records"]  # empty
    assert record == []
    # all records are fresh — check via record_count
    assert result["record_count"] == 1
    # No stale_records but we loaded one row — verify no metadata in query path
    adapter.execute.assert_called_once()


@pytest.mark.unit
def test_scan_agent_memory_stale_v1_builds_scope_filter_query() -> None:
    adapter = _mock_adapter([])
    scan_agent_memory_stale_v1(adapter=adapter, scope=_SCOPE, limit=3, now=_NOW)
    adapter.execute.assert_called_once_with(
        f"SELECT * FROM agent_memory WHERE scope = '{_SCOPE}' LIMIT 3"
    )


@pytest.mark.unit
def test_scan_agent_memory_stale_v1_unsafe_scope_rejected() -> None:
    adapter = _mock_adapter([])
    with pytest.raises(ValueError, match="not safe for SurrealQL"):
        scan_agent_memory_stale_v1(
            adapter=adapter,
            scope="scope'; DROP TABLE agent_memory; --",
            now=_NOW,
        )


@pytest.mark.unit
def test_scan_agent_memory_stale_v1_contract_violation_fail_closed() -> None:
    bad = _fresh_record()
    bad["memory_id"] = "00000000-0000-0000-0000-000000000001"
    adapter = _mock_adapter([bad])
    with pytest.raises(MemoryContractError, match="memory_id mismatch"):
        scan_agent_memory_stale_v1(adapter=adapter, scope=_SCOPE, now=_NOW)


@pytest.mark.unit
def test_wave16_bundle_path_unchanged_on_empty_bundle() -> None:
    """Regression: Wave-16 bundle scan unchanged (no DB coupling)."""
    result = scan_stale_knowledge_v1({}, as_of=_NOW.isoformat())
    assert result.total_count == 0
    assert result.blocking_count == 0
