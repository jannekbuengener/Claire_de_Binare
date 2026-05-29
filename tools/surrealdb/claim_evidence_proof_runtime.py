"""Operator runtime for #2719 claim evidence at rest proof against surrealdb-local."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools.mcp.context_evidence_memory_tools import TOOL_CDB_CONTEXT_MEMORY_GET
from tools.mcp.surrealdb_adapter_factory import build_adapter_from_params
from tools.surrealdb.claim_evidence_at_rest import prove_claim_evidence_at_rest_db_v1
from tools.surrealdb.memory_db_proof_local_dev import (
    ENV_REAL_SURREALDB_MEMORY_SMOKE,
    LOCAL_SURR_URL,
    QUERY_CONFIG_REL,
    MemoryDbProofRecordPlan,
    assert_memory_proof_records_absent,
    assert_memory_proof_tmp_absent,
    build_memory_proof_record_plan,
    cleanup_memory_proof_records,
    cleanup_memory_proof_tmp,
    http_status,
    materialize_memory_proof_bundle,
    memory_proof_tmp_root,
    repo_root,
    resolve_memory_proof_run_id,
    resolve_secrets_path,
    seed_memory_proof_bundle,
)
from tools.surrealdb.memory_db_proof_runtime import (
    RUNTIME_SCHEMA_VERSION as MEMORY_PROOF_RUNTIME_SCHEMA,
    check_memory_db_proof_preconditions,
)

CLAIM_PROOF_RUNTIME_SCHEMA = "claim-evidence-proof-runtime/v1"
_LOCAL_HEALTH_URLS = (
    f"{LOCAL_SURR_URL}/health",
    f"{LOCAL_SURR_URL}/version",
)


def _redact_for_output(
    payload: dict[str, Any], *, secrets_path: Path | None
) -> dict[str, Any]:
    rendered = json.dumps(payload, sort_keys=True, default=str)
    assert "Authorization" not in rendered
    assert "Basic " not in rendered
    assert "SURREAL_PASS" not in rendered
    assert "SURREAL_USER" not in rendered
    if secrets_path is not None:
        assert str(secrets_path) not in rendered
    return payload


def check_claim_evidence_proof_preconditions(
    *, confirm: bool = False
) -> dict[str, Any]:
    """Reuse #2603 preflight (local SurrealDB + secrets + env gate)."""
    base = check_memory_db_proof_preconditions(confirm=confirm)
    return {
        **base,
        "schema_version": CLAIM_PROOF_RUNTIME_SCHEMA,
        "preflight_reused_from": MEMORY_PROOF_RUNTIME_SCHEMA,
    }


def _build_adapter(secrets_path: Path) -> Any:
    query_config = repo_root() / QUERY_CONFIG_REL
    result = build_adapter_from_params(
        {
            "adapter_config_path": str(query_config),
            "secrets_path": str(secrets_path),
        },
        TOOL_CDB_CONTEXT_MEMORY_GET,
    )
    if isinstance(result, dict):
        raise RuntimeError(f"adapter build failed: {result}")
    adapter, _config = result
    return adapter


def run_claim_evidence_proof_cycle(*, confirm: bool = False) -> dict[str, Any]:
    """Seed run-scoped fixtures (incl. claims), prove at-rest linkage, cleanup."""
    preflight = check_claim_evidence_proof_preconditions(confirm=confirm)
    if not preflight["ok"]:
        raise RuntimeError("; ".join(preflight["errors"]))

    secrets_path = resolve_secrets_path()
    if secrets_path is None:
        raise RuntimeError("secrets path missing after preflight")

    run_id = resolve_memory_proof_run_id()
    plan = build_memory_proof_record_plan(run_id)
    tmp_root = memory_proof_tmp_root(run_id)
    assert_memory_proof_tmp_absent(tmp_root)

    from tools.surrealdb.memory_db_proof_local_dev import MemoryDbProofSqlClient

    sql_client = MemoryDbProofSqlClient.from_secrets_dir(secrets_path)
    assert_memory_proof_records_absent(sql_client, plan)

    try:
        bundle_dir = materialize_memory_proof_bundle(tmp_root, run_id=run_id, plan=plan)
        seed_memory_proof_bundle(bundle_dir, run_id=run_id, secrets_path=secrets_path)
        adapter = _build_adapter(secrets_path)

        claim_proof = prove_claim_evidence_at_rest_db_v1(
            adapter,
            scope=plan.scope,
            limit=50,
        )
        _validate_claim_proof(plan, claim_proof)

        envelope = {
            "schema_version": CLAIM_PROOF_RUNTIME_SCHEMA,
            "status": "ok",
            "run_id": run_id,
            "scope": plan.scope,
            "claim_evidence_proof": claim_proof,
            "approval_semantics": claim_proof.get("approval_semantics", {}),
            "limitations": list(
                dict.fromkeys(
                    (claim_proof.get("limitations") or [])
                    + (preflight["limitations"] or [])
                )
            ),
        }
        return _redact_for_output(envelope, secrets_path=secrets_path)
    finally:
        cleanup_memory_proof_records(sql_client, plan)
        cleanup_memory_proof_tmp(tmp_root)


def _validate_claim_proof(plan: MemoryDbProofRecordPlan, proof: dict[str, Any]) -> None:
    if proof["source"] != "surrealdb-local":
        raise RuntimeError(f"claim proof source mismatch: {proof['source']!r}")
    if proof["claim_count"] < 1:
        raise RuntimeError("claim proof expected at least one claim row")
    if set(proof["claim_ids"]) != set(plan.claim_ids):
        raise RuntimeError("claim proof claim_ids mismatch")
    for evidence_id in plan.evidence_ids:
        if evidence_id not in proof["known_evidence_ids"]:
            raise RuntimeError(f"known evidence missing from proof: {evidence_id}")
