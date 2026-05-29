"""Characterization tests for memory read contract and schema normalizer drift.

Issue #2606 — Memory Reality Slice 3 (TTL/freshness/stale proof).

See docs/surrealdb/memory-reality-slice1-audit.md (Reconcile R4, Slice 3 addendum).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tools.mcp.context_evidence_memory_tools import _normalize_memory_row
from tools.surrealdb.memory_read import MemoryReadRequest, read_memory_v1

_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.mark.unit
def test_memory_read_legacy_ttl_days_marks_old_record_stale() -> None:
    """Legacy reader fixtures: ttl_days (whole days) when no schema ttl/expires_at."""
    old = _NOW - timedelta(days=10)
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
        records, MemoryReadRequest(mode="by_scope", scope="wave14"), now=_NOW
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
    assert row["ttl"] == 3600
    assert "ttl_days" not in row


@pytest.mark.unit
def test_normalize_memory_row_ttl_seconds_not_copied_to_ttl_days() -> None:
    """R4 fix: schema ttl (seconds) stays ttl; reader uses expires_at / ttl seconds."""
    recent = _NOW - timedelta(seconds=30)
    expires = _NOW + timedelta(seconds=30)
    row = _normalize_memory_row(
        {
            "memory_id": "mem-ttl-unit-gap",
            "scope": "wave14",
            "namespace": "session",
            "memory_type": "working_memory",
            "content": "ttl gap pin",
            "created_by": "codex",
            "ttl": 60,
            "source_refs": ["docs/AGENTS.md"],
            "evidence_refs": ["ev-001"],
            "created_at": _utc_iso(recent),
            "expires_at": _utc_iso(expires),
        }
    )
    assert row["ttl"] == 60
    assert "ttl_days" not in row

    result = read_memory_v1(
        [row], MemoryReadRequest(mode="by_scope", scope="wave14"), now=_NOW
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
            "created_at": _utc_iso(_NOW),
            "superseded_by": "mem-newer",
            "source_refs": ["issue:#1"],
            "evidence_refs": ["ev-001"],
        }
    ]
    result = read_memory_v1(
        records, MemoryReadRequest(mode="by_scope", scope="wave14"), now=_NOW
    )
    entry = result["matched_memory"][0]
    assert entry["trust_level"] == "superseded"
    assert entry["superseded"] is True
