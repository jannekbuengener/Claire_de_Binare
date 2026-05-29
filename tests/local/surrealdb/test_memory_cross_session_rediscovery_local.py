"""Opt-in local cross-session memory rediscovery — #2720."""

from __future__ import annotations

import os

import pytest

from tools.surrealdb.memory_rediscovery_proof_runtime import (
    run_memory_rediscovery_proof_cycle,
)

pytestmark = pytest.mark.local_only

_ENV = "CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE"


def _enabled() -> bool:
    return os.environ.get(_ENV) == "1"


@pytest.mark.skipif(
    not _enabled(),
    reason=f"set {_ENV}=1 for local SurrealDB rediscovery proof",
)
def test_cross_session_rediscovery_local_cycle() -> None:
    result = run_memory_rediscovery_proof_cycle(confirm=True)
    assert result["status"] == "ok"
    prove = result["prove_envelope"]
    assert prove["schema_version"] == "memory-cross-session-rediscovery/v1"
    assert prove["seed_process"] != prove["prove_process"]
    assert prove["memory_ids_found"]
    assert "SURREAL_PASS" not in str(result)
