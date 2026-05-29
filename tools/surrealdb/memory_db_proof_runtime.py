"""Operator runtime for #2603 memory DB read + stale proof against surrealdb-local."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils.clock import utcnow as cdb_utcnow
from tools.mcp.context_evidence_memory_tools import TOOL_CDB_CONTEXT_MEMORY_GET
from tools.mcp.surrealdb_adapter_factory import build_adapter_from_params
from tools.surrealdb.memory_contract import validate_memory_id_matches_record
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
    MemoryDbProofSqlClient,
    repo_root,
    resolve_memory_proof_run_id,
    resolve_secrets_path,
    seed_memory_proof_bundle,
)
from tools.surrealdb.memory_db_read_proof import prove_agent_memory_db_read_v1
from tools.surrealdb.memory_db_stale_scan import scan_agent_memory_stale_v1

RUNTIME_SCHEMA_VERSION = "memory-db-proof-runtime/v1"
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


def check_memory_db_proof_preconditions(
    *,
    confirm: bool = False,
) -> dict[str, Any]:
    """Fail-closed preflight without pytest (returns structured status)."""
    errors: list[str] = []
    if os.environ.get(ENV_REAL_SURREALDB_MEMORY_SMOKE) != "1" and not confirm:
        errors.append(
            f"set {ENV_REAL_SURREALDB_MEMORY_SMOKE}=1 or pass --confirm on CLI/Makefile"
        )

    root = repo_root()
    query_config = root / QUERY_CONFIG_REL
    if not query_config.is_file():
        errors.append(f"missing local query config: {QUERY_CONFIG_REL}")

    secrets_path = resolve_secrets_path()
    if secrets_path is None:
        errors.append(
            "missing secrets dir (CDB_CONTEXT_SECRETS_PATH, SECRETS_PATH, or canon store)"
        )
    elif not (secrets_path / "SURREALDB_ENV").is_file():
        errors.append("missing SURREALDB_ENV in secrets dir")

    for url in _LOCAL_HEALTH_URLS:
        status = http_status(url)
        if status != 200:
            errors.append(
                f"local SurrealDB preflight failed for {url} (status={status})"
            )

    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "ok": not errors,
        "errors": errors,
        "query_config_path": str(query_config) if query_config.is_file() else None,
        "secrets_path_configured": secrets_path is not None,
        "limitations": [
            "local_dev_only_127.0.0.1:8010",
            "run_scoped_fixture_seed_via_context_importer_local_dev",
            "no_productive_memory_write",
            "lr_no_go",
        ],
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


def run_memory_db_proof_cycle(
    *,
    confirm: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Seed run-scoped fixtures, prove read + stale scan, cleanup (read-focused path)."""
    preflight = check_memory_db_proof_preconditions(confirm=confirm)
    if not preflight["ok"]:
        raise RuntimeError("; ".join(preflight["errors"]))

    secrets_path = resolve_secrets_path()
    if secrets_path is None:
        raise RuntimeError("secrets path missing after preflight")

    ref_now = now or cdb_utcnow()
    run_id = resolve_memory_proof_run_id()
    plan = build_memory_proof_record_plan(run_id)
    tmp_root = memory_proof_tmp_root(run_id)
    assert_memory_proof_tmp_absent(tmp_root)
    sql_client = MemoryDbProofSqlClient.from_secrets_dir(secrets_path)
    assert_memory_proof_records_absent(sql_client, plan)

    try:
        bundle_dir = materialize_memory_proof_bundle(tmp_root, run_id=run_id, plan=plan)
        seed_memory_proof_bundle(bundle_dir, run_id=run_id, secrets_path=secrets_path)
        adapter = _build_adapter(secrets_path)

        read_proof = prove_agent_memory_db_read_v1(
            adapter=adapter,
            scope=plan.scope,
            limit=25,
            now=ref_now,
        )
        stale_scan = scan_agent_memory_stale_v1(
            adapter=adapter,
            scope=plan.scope,
            limit=25,
            now=ref_now,
        )

        _validate_read_proof(plan, read_proof)
        _validate_stale_scan(plan, stale_scan)

        envelope = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "status": "ok",
            "run_id": run_id,
            "scope": plan.scope,
            "read_proof": read_proof,
            "stale_scan": stale_scan,
            "approval_semantics": read_proof.get("approval_semantics", {}),
            "limitations": list(
                dict.fromkeys(
                    (read_proof.get("limitations") or [])
                    + (stale_scan.get("limitations") or [])
                    + preflight["limitations"]
                )
            ),
        }
        return _redact_for_output(envelope, secrets_path=secrets_path)
    finally:
        cleanup_memory_proof_records(sql_client, plan)
        cleanup_memory_proof_tmp(tmp_root)


def _validate_read_proof(plan: MemoryDbProofRecordPlan, proof: dict[str, Any]) -> None:
    if proof["source"] != "surrealdb-local":
        raise RuntimeError(f"read proof source mismatch: {proof['source']!r}")
    if proof["record_count"] != 2:
        raise RuntimeError(f"read proof record_count: {proof['record_count']}")
    if set(proof["memory_ids"]) != set(plan.memory_ids):
        raise RuntimeError("read proof memory_ids mismatch")
    fresh_id, expired_id = plan.memory_ids
    by_id = {item["record"]["memory_id"]: item for item in proof["records"]}
    if not by_id[fresh_id]["freshness"]["is_fresh"]:
        raise RuntimeError("expected fresh row")
    if not by_id[expired_id]["freshness"]["is_expired"]:
        raise RuntimeError("expected expired row")
    for item in proof["records"]:
        validate_memory_id_matches_record(item["record"])


def _validate_stale_scan(plan: MemoryDbProofRecordPlan, result: dict[str, Any]) -> None:
    if result["source"] != "surrealdb-local":
        raise RuntimeError(f"stale scan source mismatch: {result['source']!r}")
    if result["record_count"] != 2:
        raise RuntimeError(f"stale scan record_count: {result['record_count']}")
    if result["fresh_count"] != 1 or result["expired_count"] != 1:
        raise RuntimeError("stale scan fresh/expired counts unexpected")
    if set(result["expired_memory_ids"]) != {plan.memory_ids[1]}:
        raise RuntimeError("stale scan expired_memory_ids mismatch")
    wave16 = result["wave16_memory_ttl"]
    if wave16["finding_count"] != 1:
        raise RuntimeError("wave16_memory_ttl finding_count expected 1")
