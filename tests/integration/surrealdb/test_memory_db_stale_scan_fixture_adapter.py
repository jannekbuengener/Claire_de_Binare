"""Integration: DB stale scan against committed fixture-backed adapter rows (#2606 DoD reconcile)."""

from __future__ import annotations

import pytest

from tests.integration.surrealdb.memory_db_proof_fixture_helpers import (
    FixtureBackedMemoryAdapter,
    _NOW,
    _SCOPE,
    assert_stale_scan_invariants,
    fixture_memory_ids,
    load_agent_memory_fixture_rows,
)
from tools.surrealdb.memory_db_stale_scan import scan_agent_memory_stale_v1

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_stale_scan_fixture_adapter_matches_runtime_invariants() -> None:
    rows = load_agent_memory_fixture_rows()
    _fresh_id, expired_id = fixture_memory_ids(rows)
    adapter = FixtureBackedMemoryAdapter(rows)

    result = scan_agent_memory_stale_v1(
        adapter=adapter,
        scope=_SCOPE,
        limit=25,
        now=_NOW,
    )

    assert_stale_scan_invariants(result, expired_id=expired_id)
    assert adapter.last_query == f"SELECT * FROM agent_memory WHERE scope = '{_SCOPE}' LIMIT 25"
    assert result["approval_semantics"]["read_only"] is True
