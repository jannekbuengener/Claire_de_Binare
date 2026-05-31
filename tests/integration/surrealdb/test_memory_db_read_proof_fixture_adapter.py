"""Integration: DB read proof against committed fixture-backed adapter rows (#2606 DoD reconcile)."""

from __future__ import annotations

import pytest

from tests.integration.surrealdb.memory_db_proof_fixture_helpers import (
    FixtureBackedMemoryAdapter,
    _NOW,
    _SCOPE,
    assert_read_proof_invariants,
    fixture_memory_ids,
    load_agent_memory_fixture_rows,
)
from tools.surrealdb.memory_db_read_proof import prove_agent_memory_db_read_v1

pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_read_proof_fixture_adapter_matches_runtime_invariants() -> None:
    rows = load_agent_memory_fixture_rows()
    fresh_id, expired_id = fixture_memory_ids(rows)
    adapter = FixtureBackedMemoryAdapter(rows)

    proof = prove_agent_memory_db_read_v1(
        adapter=adapter,
        scope=_SCOPE,
        limit=25,
        now=_NOW,
    )

    assert_read_proof_invariants(proof, fresh_id=fresh_id, expired_id=expired_id)
    assert adapter.last_query == f"SELECT * FROM agent_memory WHERE scope = '{_SCOPE}' LIMIT 25"
    assert proof["approval_semantics"]["read_only"] is True
    assert set(proof["evidence_refs"]) == {
        "ev-mdbproof-base-001",
        "ev-mdbproof-base-002",
    }
