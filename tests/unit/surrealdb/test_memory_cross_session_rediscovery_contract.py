"""Unit tests for cross-session memory rediscovery contracts — #2720."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.memory_cross_session_rediscovery import (
    MemoryRediscoveryError,
    build_manifest_from_plan,
    load_rediscovery_manifest,
    prove_cross_session_rediscovery_from_manifest,
    write_rediscovery_manifest,
)

_SCOPE = "memory_db_proof:unittest"


def _mock_adapter(rows_by_query: dict[str, list[dict[str, Any]]]) -> MagicMock:
    adapter = MagicMock()
    adapter.status = "surrealdb-local"

    def _execute(query: str) -> list[dict[str, Any]]:
        for key, rows in rows_by_query.items():
            if key in query:
                return rows
        return []

    adapter.execute.side_effect = _execute
    return adapter


def _memory_row(memory_id: str) -> dict[str, Any]:
    return {
        "memory_id": memory_id,
        "scope": _SCOPE,
        "namespace": _SCOPE,
        "memory_type": "semantic_memory",
        "content": "cross-session proof memory",
        "source_refs": ["docs/surrealdb/memory-reality-slice1-audit.md"],
        "evidence_refs": ["ev-unit-001"],
        "confidence": 0.9,
        "ttl": 86400,
        "created_by": "cdb-test-001",
        "created_at": "2026-05-29T10:00:00Z",
        "expires_at": "2026-05-30T10:00:00Z",
    }


@pytest.mark.unit
def test_manifest_round_trip(tmp_path: Path) -> None:
    manifest = build_manifest_from_plan(
        run_id="run-test-001",
        scope=_SCOPE,
        memory_ids=("mid-a", "mid-b"),
        evidence_ids=("ev-unit-001",),
        seed_process_id=1000,
    )
    path = tmp_path / "manifest.json"
    write_rediscovery_manifest(manifest, path)
    loaded = load_rediscovery_manifest(path)
    assert loaded.run_id == "run-test-001"
    assert len(loaded.entries) == 2
    assert loaded.entries[0].memory_id == "mid-a"


@pytest.mark.unit
def test_prove_without_manifest_file_raises(tmp_path: Path) -> None:
    with pytest.raises(MemoryRediscoveryError, match="manifest missing"):
        load_rediscovery_manifest(tmp_path / "missing.json")


@pytest.mark.unit
def test_scope_mismatch_in_manifest_entries_blocks_prove() -> None:
    from tools.surrealdb.memory_cross_session_rediscovery import (
        RediscoveryManifest,
        RediscoveryManifestEntry,
    )

    manifest = RediscoveryManifest(
        schema_version="memory-cross-session-rediscovery-manifest/v1",
        run_id="r1",
        seed_process_id=1,
        entries=(
            RediscoveryManifestEntry("m1", "scope-a", ("ev-1",)),
            RediscoveryManifestEntry("m2", "scope-b", ("ev-1",)),
        ),
    )
    adapter = _mock_adapter({})
    with pytest.raises(MemoryRediscoveryError, match="single scope"):
        prove_cross_session_rediscovery_from_manifest(
            adapter,
            manifest,
            prove_process_id=2,
        )


@pytest.mark.unit
def test_memory_id_and_scope_lookup_required() -> None:
    manifest = build_manifest_from_plan(
        run_id="r2",
        scope=_SCOPE,
        memory_ids=("mid-lookup",),
        evidence_ids=("ev-unit-001",),
        seed_process_id=10,
    )
    adapter = _mock_adapter({})
    with pytest.raises(MemoryRediscoveryError, match="expected exactly one"):
        prove_cross_session_rediscovery_from_manifest(
            adapter,
            manifest,
            prove_process_id=20,
        )


@pytest.mark.unit
def test_prove_envelope_has_source_trust_limitations() -> None:
    memory_id = "988581e3-7003-5e93-a847-9dcfe2d4633f"
    row = _memory_row(memory_id)
    from tools.surrealdb.memory_contract import generate_memory_id

    row["memory_id"] = generate_memory_id(
        scope=row["scope"],
        namespace=row["namespace"],
        memory_type=row["memory_type"],
        created_by=row["created_by"],
        content=row["content"],
        source_refs=row["source_refs"],
    )
    mid = row["memory_id"]
    manifest = build_manifest_from_plan(
        run_id="r3",
        scope=_SCOPE,
        memory_ids=(mid,),
        evidence_ids=("ev-unit-001",),
        seed_process_id=30,
    )

    claim_row = {
        "claim_id": "claim-unit",
        "scope": _SCOPE,
        "status": "supported",
        "evidence_refs": ["ev-unit-001"],
    }
    evidence_row = {"evidence_id": "ev-unit-001", "evidence_type": "test_run"}

    adapter = _mock_adapter(
        {
            "agent_memory": [row],
            f"memory_id = '{mid}'": [row],
            "FROM claim": [claim_row],
            "FROM evidence_ref": [evidence_row],
        }
    )

    prove = prove_cross_session_rediscovery_from_manifest(
        adapter,
        manifest,
        prove_process_id=40,
    )
    assert prove["schema_version"] == "memory-cross-session-rediscovery/v1"
    assert prove["source"] == "surrealdb-local"
    assert prove["trust"]["lookup_keys"] == ["memory_id", "scope"]
    assert prove["limitations"]
    assert prove["approval_semantics"]["no_live_go"] is True
    assert prove["claim_evidence_at_rest"]["claim_count"] >= 1
    rendered = json.dumps(prove)
    assert "SURREAL_PASS" not in rendered
