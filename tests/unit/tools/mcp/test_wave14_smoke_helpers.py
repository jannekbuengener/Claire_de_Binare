from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.local.tools.mcp.wave14_smoke_helpers import (
    _FRESH_MEMORY_STALE_AFTER_SECONDS,
    _FRESH_MEMORY_TTL_SECONDS,
    build_record_plan,
    materialize_fixture_records,
)

pytestmark = pytest.mark.unit


def _load_single_record(text: str) -> dict[str, object]:
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    assert len(records) == 1
    return records[0]


def test_materialize_fixture_records_refreshes_evidence_hash_and_timestamps() -> None:
    fixed_now = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)
    plan = build_record_plan("wave14-real-smoke-unit")

    record = _load_single_record(
        materialize_fixture_records(
            "evidence_refs.jsonl",
            run_id=plan.run_id,
            plan=plan,
            materialized_at=fixed_now,
        )
    )

    source_path = Path(str(record["source_path"]))
    expected_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    assert record["run_id"] == plan.run_id
    assert record["evidence_id"] == plan.evidence_ids[0]
    assert record["source_hash"] == expected_hash
    assert record["created_at"] == "2026-06-29T11:56:00Z"
    assert record["collected_at"] == "2026-06-29T11:56:00Z"
    assert record["freshness"] == "fresh"


def test_materialize_fixture_records_keeps_memory_fresh_for_local_proof() -> None:
    fixed_now = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)
    plan = build_record_plan("wave14-real-smoke-unit")

    record = _load_single_record(
        materialize_fixture_records(
            "agent_memories.jsonl",
            run_id=plan.run_id,
            plan=plan,
            materialized_at=fixed_now,
        )
    )

    assert record["run_id"] == plan.run_id
    assert record["memory_id"] == plan.memory_ids[0]
    assert record["created_at"] == "2026-06-29T11:59:30Z"
    assert record["ttl"] == _FRESH_MEMORY_TTL_SECONDS
    assert record["stale_after"] == _FRESH_MEMORY_STALE_AFTER_SECONDS
    assert record["expires_at"] == (
        fixed_now + timedelta(seconds=_FRESH_MEMORY_TTL_SECONDS)
    ).isoformat().replace("+00:00", "Z")
