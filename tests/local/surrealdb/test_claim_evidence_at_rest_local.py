"""Opt-in local-only claim evidence at rest proof — #2719.

Requires ``CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1`` or pytest ``--confirm`` via
operator CLI; same gates as #2603 memory DB proof.
"""

from __future__ import annotations

import os

import pytest

from tools.surrealdb.claim_evidence_proof_runtime import run_claim_evidence_proof_cycle

pytestmark = pytest.mark.local_only

_ENV = "CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE"


def _local_proof_enabled() -> bool:
    return os.environ.get(_ENV) == "1"


@pytest.mark.skipif(
    not _local_proof_enabled(),
    reason=f"set {_ENV}=1 for local SurrealDB claim evidence proof",
)
def test_claim_evidence_at_rest_local_cycle() -> None:
    result = run_claim_evidence_proof_cycle(confirm=True)
    assert result["status"] == "ok"
    proof = result["claim_evidence_proof"]
    assert proof["schema_version"] == "claim-evidence-at-rest/v1"
    assert proof["claim_count"] >= 1
    assert "SURREAL_PASS" not in str(result)
    assert proof["approval_semantics"]["read_only"] is True
