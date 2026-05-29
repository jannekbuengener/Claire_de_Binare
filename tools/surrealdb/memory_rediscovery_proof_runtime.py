"""Operator runtime for #2720 cross-session memory rediscovery proof."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.utils.clock import utcnow as cdb_utcnow
from tools.mcp.context_evidence_memory_tools import TOOL_CDB_CONTEXT_MEMORY_GET
from tools.mcp.surrealdb_adapter_factory import build_adapter_from_params
from tools.surrealdb.memory_cross_session_rediscovery import (
    SCHEMA_VERSION,
    build_manifest_from_plan,
    cleanup_rediscovery_manifest,
    load_rediscovery_manifest,
    manifest_path_for_run,
    prove_cross_session_rediscovery_from_manifest,
    write_rediscovery_manifest,
)
from tools.surrealdb.memory_db_proof_local_dev import (
    QUERY_CONFIG_REL,
    MemoryDbProofRecordPlan,
    MemoryDbProofSqlClient,
    assert_memory_proof_records_absent,
    assert_memory_proof_tmp_absent,
    build_memory_proof_record_plan,
    cleanup_memory_proof_records,
    cleanup_memory_proof_tmp,
    materialize_memory_proof_bundle,
    memory_proof_tmp_root,
    repo_root,
    resolve_memory_proof_run_id,
    resolve_secrets_path,
    seed_memory_proof_bundle,
)
from tools.surrealdb.memory_db_proof_runtime import check_memory_db_proof_preconditions

REDISCOVERY_RUNTIME_SCHEMA = "memory-rediscovery-proof-runtime/v1"
_PROVE_CLI_MODULE = "tools.surrealdb.memory_rediscovery_proof_cli"


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


def check_memory_rediscovery_proof_preconditions(
    *, confirm: bool = False
) -> dict[str, Any]:
    base = check_memory_db_proof_preconditions(confirm=confirm)
    return {
        **base,
        "schema_version": REDISCOVERY_RUNTIME_SCHEMA,
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


def run_prove_phase_subprocess(
    *,
    manifest_path: Path,
    confirm: bool,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        _PROVE_CLI_MODULE,
        "prove-phase",
        "--manifest",
        str(manifest_path),
    ]
    if confirm:
        cmd.append("--confirm")
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()[:500]
        raise RuntimeError(
            f"prove-phase subprocess failed (exit={completed.returncode}): {stderr}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("prove-phase subprocess returned invalid JSON") from exc


def run_memory_rediscovery_proof_cycle(*, confirm: bool = False) -> dict[str, Any]:
    preflight = check_memory_rediscovery_proof_preconditions(confirm=confirm)
    if not preflight["ok"]:
        raise RuntimeError("; ".join(preflight["errors"]))

    secrets_path = resolve_secrets_path()
    if secrets_path is None:
        raise RuntimeError("secrets path missing after preflight")

    root = repo_root()
    run_id = resolve_memory_proof_run_id()
    plan = build_memory_proof_record_plan(run_id)
    tmp_root = memory_proof_tmp_root(run_id)
    manifest_path = manifest_path_for_run(root, run_id)

    assert_memory_proof_tmp_absent(tmp_root)
    sql_client = MemoryDbProofSqlClient.from_secrets_dir(secrets_path)
    assert_memory_proof_records_absent(sql_client, plan)

    try:
        bundle_dir = materialize_memory_proof_bundle(tmp_root, run_id=run_id, plan=plan)
        seed_memory_proof_bundle(bundle_dir, run_id=run_id, secrets_path=secrets_path)

        manifest = build_manifest_from_plan(
            run_id=run_id,
            scope=plan.scope,
            memory_ids=plan.memory_ids,
            evidence_ids=plan.evidence_ids,
            seed_process_id=os.getpid(),
        )
        write_rediscovery_manifest(manifest, manifest_path)

        prove_envelope = run_prove_phase_subprocess(
            manifest_path=manifest_path,
            confirm=confirm,
        )
        _validate_prove_envelope(plan, prove_envelope)

        envelope = {
            "schema_version": REDISCOVERY_RUNTIME_SCHEMA,
            "status": "ok",
            "run_id": run_id,
            "scope": plan.scope,
            "manifest_path": str(manifest_path.relative_to(root)),
            "seed_process": manifest.seed_process_id,
            "prove_envelope": prove_envelope,
            "approval_semantics": prove_envelope.get("approval_semantics", {}),
            "limitations": list(
                dict.fromkeys(
                    (prove_envelope.get("limitations") or [])
                    + (preflight.get("limitations") or [])
                )
            ),
        }
        return _redact_for_output(envelope, secrets_path=secrets_path)
    finally:
        cleanup_memory_proof_records(sql_client, plan)
        cleanup_memory_proof_tmp(tmp_root)
        cleanup_rediscovery_manifest(manifest_path)


def run_prove_phase_only(
    *,
    manifest_path: Path,
    confirm: bool = False,
) -> dict[str, Any]:
    """Subprocess entry: load manifest + DB proof only."""
    preflight = check_memory_rediscovery_proof_preconditions(confirm=confirm)
    if not preflight["ok"]:
        raise RuntimeError("; ".join(preflight["errors"]))

    secrets_path = resolve_secrets_path()
    if secrets_path is None:
        raise RuntimeError("secrets path missing after preflight")

    manifest = load_rediscovery_manifest(manifest_path)
    adapter = _build_adapter(secrets_path)
    return prove_cross_session_rediscovery_from_manifest(
        adapter,
        manifest,
        prove_process_id=os.getpid(),
        now=cdb_utcnow(),
    )


def _validate_prove_envelope(
    plan: MemoryDbProofRecordPlan, prove: dict[str, Any]
) -> None:
    if prove.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("prove envelope schema mismatch")
    if set(prove.get("memory_ids_found", [])) != set(plan.memory_ids):
        raise RuntimeError("memory_ids_found mismatch")
    if prove.get("scope") != plan.scope:
        raise RuntimeError("prove scope mismatch")
