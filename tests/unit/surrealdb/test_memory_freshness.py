"""Unit tests for memory TTL/freshness/stale classification (Slice 3).

Issue #2606 — Memory Reality Slice 3: TTL / Freshness / Stale Proof.

Deterministic in-memory tests only; no DB, no writes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.surrealdb.memory_contract import (
    MemoryFreshness,
    classify_memory_freshness,
)
from tools.surrealdb.memory_read import MemoryReadRequest, read_memory_v1
from tools.mcp.context_evidence_memory_tools import _normalize_memory_row

_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
_CREATED = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.mark.unit
def test_classify_no_ttl_or_expiry_is_fresh() -> None:
    result = classify_memory_freshness(
        {"created_at": _iso(_CREATED), "stale": False},
        now=_NOW,
    )
    assert result == MemoryFreshness(
        is_fresh=True, is_stale=False, is_expired=False, reasons=()
    )


@pytest.mark.unit
def test_classify_expires_at_in_future_is_fresh() -> None:
    expires = _NOW + timedelta(hours=1)
    result = classify_memory_freshness(
        {
            "created_at": _iso(_CREATED),
            "ttl": 7200,
            "expires_at": _iso(expires),
        },
        now=_NOW,
    )
    assert result.is_fresh is True
    assert result.is_stale is False
    assert result.is_expired is False


@pytest.mark.unit
def test_classify_expires_at_elapsed_is_expired_and_stale() -> None:
    expires = _NOW - timedelta(seconds=1)
    result = classify_memory_freshness(
        {
            "created_at": _iso(_CREATED),
            "ttl": 3600,
            "expires_at": _iso(expires),
        },
        now=_NOW,
    )
    assert result.is_fresh is False
    assert result.is_stale is True
    assert result.is_expired is True
    assert "expires_at_elapsed" in result.reasons


@pytest.mark.unit
def test_classify_stale_after_elapsed_not_expired() -> None:
    expires = _NOW + timedelta(hours=2)
    result = classify_memory_freshness(
        {
            "created_at": _iso(_CREATED),
            "ttl": 86400,
            "expires_at": _iso(expires),
            "stale_after": 3600,
        },
        now=_NOW,
    )
    assert result.is_stale is True
    assert result.is_expired is False
    assert "stale_after_elapsed" in result.reasons
    assert "expires_at_elapsed" not in result.reasons


@pytest.mark.unit
def test_classify_ttl_zero_without_expires_at_is_fresh() -> None:
    result = classify_memory_freshness(
        {"created_at": _iso(_CREATED), "ttl": 0},
        now=_NOW,
    )
    assert result.is_fresh is True
    assert result.is_expired is False


@pytest.mark.unit
def test_classify_superseded_by_is_stale_not_expired() -> None:
    expires = _NOW - timedelta(hours=1)
    result = classify_memory_freshness(
        {
            "created_at": _iso(_CREATED),
            "expires_at": _iso(expires),
            "superseded_by": "mem-newer",
        },
        now=_NOW,
    )
    assert result.is_stale is True
    assert result.is_expired is False
    assert result.reasons == ("superseded_by",)


@pytest.mark.unit
def test_classify_explicit_stale_flag() -> None:
    result = classify_memory_freshness(
        {"created_at": _iso(_CREATED), "stale": True},
        now=_NOW,
    )
    assert result.is_stale is True
    assert result.reasons == ("explicit_stale",)


@pytest.mark.unit
def test_classify_legacy_ttl_days_only() -> None:
    old_created = _NOW - timedelta(days=10)
    result = classify_memory_freshness(
        {"created_at": _iso(old_created), "ttl_days": 1},
        now=_NOW,
    )
    assert result.is_stale is True
    assert "legacy_ttl_days" in result.reasons


@pytest.mark.unit
def test_classify_derives_expiry_from_ttl_seconds() -> None:
    created = _NOW - timedelta(seconds=7200)
    result = classify_memory_freshness(
        {"created_at": _iso(created), "ttl": 3600},
        now=_NOW,
    )
    assert result.is_expired is True
    assert "expires_at_elapsed" in result.reasons


@pytest.mark.unit
def test_read_memory_expired_record_marked_stale_not_filtered() -> None:
    created = _NOW - timedelta(hours=2)
    expires = _NOW - timedelta(minutes=30)
    records = [
        {
            "memory_id": "mem-expired-001",
            "scope": "wave14",
            "memory_type": "working_memory",
            "content": "old",
            "created_at": _iso(created),
            "ttl": 3600,
            "expires_at": _iso(expires),
            "source_refs": ["docs/AGENTS.md"],
            "evidence_refs": ["ev-001"],
        }
    ]
    result = read_memory_v1(
        records,
        MemoryReadRequest(mode="by_scope", scope="wave14"),
        now=_NOW,
    )
    assert len(result["matched_memory"]) == 1
    row = result["matched_memory"][0]
    assert row["stale"] is True
    assert row["expired"] is True
    assert "expires_at_elapsed" in row["freshness_reasons"]
    assert "mem-expired-001" in result["stale_memory_ids"]


@pytest.mark.unit
def test_read_memory_fresh_with_canonical_ttl() -> None:
    created = _NOW - timedelta(seconds=30)
    expires = _NOW + timedelta(hours=1)
    records = [
        {
            "memory_id": "mem-fresh-001",
            "scope": "wave14",
            "memory_type": "working_memory",
            "content": "current",
            "created_at": _iso(created),
            "ttl": 3600,
            "expires_at": _iso(expires),
            "source_refs": ["docs/AGENTS.md"],
            "evidence_refs": ["ev-001"],
        }
    ]
    result = read_memory_v1(
        records,
        MemoryReadRequest(mode="by_scope", scope="wave14"),
        now=_NOW,
    )
    row = result["matched_memory"][0]
    assert row["stale"] is False
    assert row.get("expired") is False
    assert row["ttl"] == 3600
    assert "mem-fresh-001" not in result["stale_memory_ids"]


@pytest.mark.unit
def test_read_memory_legacy_ttl_days_fixture_still_stale() -> None:
    old = _NOW - timedelta(days=10)
    records = [
        {
            "memory_id": "mem-char-ttl-days",
            "scope": "wave14",
            "memory_type": "working_memory",
            "content": "pinned",
            "created_at": _iso(old),
            "ttl_days": 1,
            "source_refs": ["docs/AGENTS.md"],
            "evidence_refs": ["ev-pin-001"],
        }
    ]
    result = read_memory_v1(
        records,
        MemoryReadRequest(mode="by_scope", scope="wave14"),
        now=_NOW,
    )
    matched = {m["memory_id"]: m for m in result["matched_memory"]}
    assert matched["mem-char-ttl-days"]["stale"] is True
    assert "legacy_ttl_days" in matched["mem-char-ttl-days"]["freshness_reasons"]


@pytest.mark.unit
def test_normalize_memory_row_preserves_ttl_seconds() -> None:
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
def test_normalize_memory_row_one_second_ttl_not_mapped_to_days() -> None:
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
            "created_at": _iso(recent),
            "expires_at": _iso(expires),
        }
    )
    assert row["ttl"] == 60
    assert "ttl_days" not in row

    result = read_memory_v1(
        [row],
        MemoryReadRequest(mode="by_scope", scope="wave14"),
        now=_NOW,
    )
    matched = result["matched_memory"][0]
    assert matched["memory_id"] == "mem-ttl-unit-gap"
    assert matched["stale"] is False
    assert "mem-ttl-unit-gap" not in result["stale_memory_ids"]


@pytest.mark.unit
def test_memory_read_no_datetime_now_in_source() -> None:
    """Guardrail: memory_read must use injectable clock, not datetime.now()."""
    source = Path("tools/surrealdb/memory_read.py").read_text(encoding="utf-8")
    assert "datetime.now(" not in source
    assert "datetime.utcnow(" not in source
