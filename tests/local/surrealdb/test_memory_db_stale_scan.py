"""Opt-in local-only DB-backed stale/expired memory scan — #2702.

Runs only when:
- ``CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1``
- ``infrastructure/config/surrealdb/context_query.local.yaml`` exists
- secrets path resolves (CDB canon, overridable via env)
- local SurrealDB answers on ``127.0.0.1:8010``
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

import pytest

from tests.local.surrealdb.memory_db_proof_helpers import (
    MemoryDbProofRecordPlan,
    MemoryDbProofSqlClient,
    assert_memory_proof_records_absent,
    assert_memory_proof_tmp_absent,
    build_memory_proof_record_plan,
    cleanup_memory_proof_records,
    cleanup_memory_proof_tmp,
    materialize_memory_proof_bundle,
    memory_proof_tmp_root,
    resolve_memory_proof_run_id,
)
from tools.mcp.surrealdb_adapter_factory import build_adapter_from_params
from tools.mcp.context_evidence_memory_tools import TOOL_CDB_CONTEXT_MEMORY_GET
from tools.surrealdb.context_importer import main as importer_main
from tools.surrealdb.memory_db_stale_scan import scan_agent_memory_stale_v1

pytestmark = pytest.mark.local_only

_REPO_ROOT = Path(__file__).resolve().parents[3]
_QUERY_CONFIG_PATH = (
    _REPO_ROOT / "infrastructure" / "config" / "surrealdb" / "context_query.local.yaml"
)
_IMPORT_CONFIG_PATH = (
    _REPO_ROOT
    / "infrastructure"
    / "config"
    / "surrealdb"
    / "context_import.local.example.yaml"
)
_LOCAL_SURR_URLS = (
    "http://127.0.0.1:8010/health",
    "http://127.0.0.1:8010/version",
)
_NOW = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)


def _http_status(url: str) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return int(response.status)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _candidate_secrets_paths() -> list[Path]:
    candidates: list[Path] = []
    for env_key in ("CDB_CONTEXT_SECRETS_PATH", "SECRETS_PATH"):
        raw = os.environ.get(env_key, "").strip()
        if raw:
            candidates.append(Path(raw))
    if os.name == "nt":
        userprofile = os.environ.get("USERPROFILE", "").strip()
        if userprofile:
            candidates.append(Path(userprofile) / "Documents" / ".secrets" / ".cdb")
    else:
        candidates.append(Path.home() / "Documents" / ".secrets" / ".cdb")
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _resolve_secrets_path() -> Path | None:
    for candidate in _candidate_secrets_paths():
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue
    return None


def _require_local_opt_in() -> Path:
    if os.environ.get("CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE") != "1":
        pytest.skip(
            "real surrealdb-local memory proof disabled; "
            "set CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1"
        )
    if not _QUERY_CONFIG_PATH.exists():
        pytest.skip(
            "missing local query config: "
            "infrastructure/config/surrealdb/context_query.local.yaml"
        )
    secrets_dir = _resolve_secrets_path()
    if secrets_dir is None:
        pytest.skip(
            "missing secrets dir for surrealdb-local auth "
            "(set CDB_CONTEXT_SECRETS_PATH or SECRETS_PATH, or provide canon secrets store)"
        )
    if not (secrets_dir / "SURREALDB_ENV").is_file():
        pytest.skip("missing required secrets file SURREALDB_ENV in secrets dir")
    for url in _LOCAL_SURR_URLS:
        status = _http_status(url)
        if status != 200:
            pytest.skip(f"local SurrealDB preflight failed for {url} (status={status})")
    return secrets_dir


def _seed_local_surrealdb(
    input_dir: Path,
    *,
    run_id: str,
    secrets_path: Path,
) -> None:
    exit_code = importer_main(
        [
            "apply",
            "--input-dir",
            str(input_dir),
            "--surreal-url",
            "http://127.0.0.1:8010",
            "--namespace",
            "cdb_context_local",
            "--database",
            "cdb_context_intel",
            "--apply",
            "--apply-mode",
            "local-dev",
            "--config",
            str(_IMPORT_CONFIG_PATH),
            "--run-id",
            run_id,
            "--adapter",
            "surrealdb-local",
            "--secrets-path",
            str(secrets_path),
        ]
    )
    assert exit_code == 0, f"context_importer apply failed with exit code {exit_code}"


def _build_adapter(secrets_path: Path) -> Any:
    result = build_adapter_from_params(
        {
            "adapter_config_path": str(_QUERY_CONFIG_PATH),
            "secrets_path": str(secrets_path),
        },
        TOOL_CDB_CONTEXT_MEMORY_GET,
    )
    assert not isinstance(result, dict), result
    adapter, _config = result
    return adapter


def _assert_no_secret_leak(payload: dict[str, Any], *, secrets_path: Path) -> None:
    rendered = json.dumps(payload, sort_keys=True, default=str)
    assert "Authorization" not in rendered
    assert "Basic " not in rendered
    assert "SURREAL_PASS" not in rendered
    assert "SURREAL_USER" not in rendered
    assert str(secrets_path) not in rendered


@pytest.fixture
def memory_db_proof_context() -> (
    tuple[MemoryDbProofRecordPlan, Path, MemoryDbProofSqlClient]
):
    secrets_path = _require_local_opt_in()
    run_id = resolve_memory_proof_run_id()
    plan = build_memory_proof_record_plan(run_id)
    tmp_root = memory_proof_tmp_root(run_id)
    assert_memory_proof_tmp_absent(tmp_root)
    sql_client = MemoryDbProofSqlClient.from_secrets_dir(secrets_path)
    assert_memory_proof_records_absent(sql_client, plan)
    bundle_dir = materialize_memory_proof_bundle(tmp_root, run_id=run_id, plan=plan)
    _seed_local_surrealdb(bundle_dir, run_id=run_id, secrets_path=secrets_path)
    try:
        yield plan, secrets_path, sql_client
    finally:
        cleanup_memory_proof_records(sql_client, plan)
        cleanup_memory_proof_tmp(tmp_root)


def test_memory_db_stale_scan_skips_without_env_flag() -> None:
    if os.environ.get("CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE") == "1":
        pytest.skip("env flag set; covered by seeded stale scan test")
    with pytest.raises(pytest.skip.Exception):
        _require_local_opt_in()


def test_memory_db_stale_scan_finds_fresh_and_expired(
    memory_db_proof_context: tuple[
        MemoryDbProofRecordPlan, Path, MemoryDbProofSqlClient
    ],
) -> None:
    plan, secrets_path, _sql_client = memory_db_proof_context
    adapter = _build_adapter(secrets_path)

    result = scan_agent_memory_stale_v1(
        adapter=adapter,
        scope=plan.scope,
        limit=25,
        now=_NOW,
    )

    assert result["source"] == "surrealdb-local"
    assert result["record_count"] == 2
    assert result["fresh_count"] == 1
    assert result["stale_count"] == 1
    assert result["expired_count"] == 1
    assert set(result["expired_memory_ids"]) == {plan.memory_ids[1]}
    assert plan.memory_ids[0] not in result["stale_memory_ids"]
    assert plan.memory_ids[1] in result["stale_memory_ids"]

    wave16 = result["wave16_memory_ttl"]
    assert wave16["finding_count"] == 1
    assert wave16["stale_types"] == ["memory_ttl_expired"]

    _assert_no_secret_leak(result, secrets_path=secrets_path)
