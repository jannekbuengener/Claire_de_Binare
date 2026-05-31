"""Shared fixture-backed adapter helpers for #2606 DB read/stale integration tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.surrealdb.memory_contract import generate_memory_id, validate_memory_id_matches_record

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_PATH = (
    _REPO_ROOT / "tests" / "fixtures" / "surrealdb" / "memory_db_proof" / "agent_memories.jsonl"
)
_SCOPE = "memory_db_proof"
_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)


class FixtureBackedMemoryAdapter:
    """Minimal adapter surface returning committed fixture rows as DB SELECT results."""

    status = "surrealdb-local"

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.last_query: str | None = None

    def execute(self, query: str) -> list[dict[str, Any]]:
        self.last_query = query
        return list(self._rows)


def load_agent_memory_fixture_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _FIXTURE_PATH.read_text(encoding="utf-8").strip().splitlines():
        row = json.loads(line)
        memory_id = row.get("memory_id") or generate_memory_id(
            scope=row["scope"],
            namespace=row["namespace"],
            memory_type=row["memory_type"],
            created_by=row["created_by"],
            content=row["content"],
            source_refs=row["source_refs"],
        )
        row["memory_id"] = memory_id
        row.setdefault("run_id", "memory_db_proof_seed")
        row.setdefault("schema_version", "context-indexer/v0")
        row.setdefault("id", f"agent_memory:{memory_id[:8]}")
        row.setdefault("sensitivity", "internal")
        rows.append(row)
    return rows


def fixture_memory_ids(rows: list[dict[str, Any]]) -> tuple[str, str]:
    fresh_id = generate_memory_id(
        scope=_SCOPE,
        namespace=_SCOPE,
        memory_type="semantic_memory",
        created_by="cdb-test-001",
        content="Fresh memory for DB read proof slice 4.",
        source_refs=["docs/surrealdb/memory-reality-slice1-audit.md"],
    )
    expired_id = generate_memory_id(
        scope=_SCOPE,
        namespace=_SCOPE,
        memory_type="semantic_memory",
        created_by="cdb-test-001",
        content="Expired memory for DB read proof slice 4.",
        source_refs=["docs/surrealdb/memory-reality-slice1-audit.md"],
    )
    loaded = {row["memory_id"] for row in rows}
    assert fresh_id in loaded, "fresh fixture memory_id missing"
    assert expired_id in loaded, "expired fixture memory_id missing"
    return fresh_id, expired_id


def assert_read_proof_invariants(proof: dict[str, Any], *, fresh_id: str, expired_id: str) -> None:
    assert proof["source"] == "surrealdb-local"
    assert proof["record_count"] == 2
    assert set(proof["memory_ids"]) == {fresh_id, expired_id}
    by_id = {item["record"]["memory_id"]: item for item in proof["records"]}
    assert by_id[fresh_id]["freshness"]["is_fresh"] is True
    assert by_id[expired_id]["freshness"]["is_expired"] is True
    for item in proof["records"]:
        record = item["record"]
        assert "run_id" not in record
        validate_memory_id_matches_record(record)


def assert_stale_scan_invariants(result: dict[str, Any], *, expired_id: str) -> None:
    assert result["source"] == "surrealdb-local"
    assert result["schema_version"] == "memory-db-stale-scan/v1"
    assert result["record_count"] == 2
    assert result["fresh_count"] == 1
    assert result["expired_count"] == 1
    assert set(result["expired_memory_ids"]) == {expired_id}
    wave16 = result["wave16_memory_ttl"]
    assert wave16["finding_count"] == 1
