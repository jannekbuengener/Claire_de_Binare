"""Characterization tests for memory read contract and schema normalizer drift.

Issue #2606 — Memory Reality Slice 1 (audit only; no behavior change).

These tests PIN current behavior so a future TTL-unit fix (Slice 3) must be
an explicit, reviewed change. See docs/surrealdb/memory-reality-slice1-audit.md
(Reconcile R4).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tools.mcp.context_evidence_memory_tools import _normalize_memory_row
from tools.surrealdb.memory_read import MemoryReadRequest, read_memory_v1


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.mark.unit
def test_memory_read_ttl_days_marks_old_record_stale() -> None:
    """Reader TTL path uses ttl_days as whole days (fixture contract)."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    records = [
        {
            "memory_id": "mem-char-ttl-days",
            "scope": "wave14",
            "memory_type": "working_memory",
            "content": "pinned",
            "created_at": _utc_iso(old),
            "ttl_days": 1,
            "source_refs": ["docs/AGENTS.md"],
            "evidence_refs": ["ev-pin-001"],
        }
    ]
    result = read_memory_v1(
        records, MemoryReadRequest(mode="by_scope", scope="wave14")
    )
    matched = {m["memory_id"]: m for m in result["matched_memory"]}
    assert matched["mem-char-ttl-days"]["stale"] is True
    assert "mem-char-ttl-days" in result["stale_memory_ids"]


@pytest.mark.unit
def test_normalize_memory_row_maps_created_by_to_agent() -> None:
    """MCP DB path: schema created_by becomes reader contract field agent."""
    row = _normalize_memory_row(
        {
            "memory_id": "mem-schema-pin",
            "scope": "agent:OPENCODE/copilot",
            "namespace": "session",
            "memory_type": "semantic_memory",
            "content": "test",
            "created_by": "agent-test-001",
            "ttl": 3600,
            "source_refs": ["docs/AGENTS.md@abc123"],
            "evidence_refs": ["ev-001"],
        }
    )
    assert row["agent"] == "agent-test-001"
    assert row["ttl_days"] == 3600


@pytest.mark.unit
def test_normalize_memory_row_ttl_copied_to_ttl_days_without_unit_conversion() -> None:
    """KNOWN GAP (R4): schema ttl (seconds) is copied 1:1 to ttl_days.

    One second of schema ttl is treated as one day of reader TTL until Slice 3.
    This test must fail if someone 'fixes' normalization without updating reader.
    """
    recent = datetime.now(timezone.utc) - timedelta(seconds=30)
    row = _normalize_memory_row(
        {
            "memory_id": "mem-ttl-unit-gap",
            "scope": "wave14",
            "namespace": "session",
            "memory_type": "working_memory",
            "content": "ttl gap pin",
            "created_by": "codex",
            "ttl": 1,
            "source_refs": ["docs/AGENTS.md"],
            "evidence_refs": ["ev-001"],
            "created_at": _utc_iso(recent),
        }
    )
    assert row["ttl_days"] == 1

    result = read_memory_v1(
        [row], MemoryReadRequest(mode="by_scope", scope="wave14")
    )
    matched = result["matched_memory"][0]
    assert matched["memory_id"] == "mem-ttl-unit-gap"
    assert matched["stale"] is False
    assert "mem-ttl-unit-gap" not in result["stale_memory_ids"]


@pytest.mark.unit
def test_memory_read_superseded_by_sets_superseded_trust() -> None:
    """Pins superseded_by handling in read path (no chain resolution)."""
    records = [
        {
            "memory_id": "mem-superseded-pin",
            "scope": "wave14",
            "memory_type": "episodic_memory",
            "content": "old fact",
            "created_at": _utc_iso(datetime.now(timezone.utc)),
            "superseded_by": "mem-newer",
            "source_refs": ["issue:#1"],
            "evidence_refs": ["ev-001"],
        }
    ]
    result = read_memory_v1(
        records, MemoryReadRequest(mode="by_scope", scope="wave14")
    )
    entry = result["matched_memory"][0]
    assert entry["trust_level"] == "superseded"
    assert "mem-superseded-pin" in result["superseded_memory_ids"]
