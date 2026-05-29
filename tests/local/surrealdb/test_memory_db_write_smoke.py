"""Opt-in local-only gated memory write smoke — #2606 Slice 6.

Requires:
- ``CDB_RUN_REAL_SURREALDB_MEMORY_WRITE=1``
- Operator-supplied ``CDB_MEMORY_WRITE_HUMAN_GO_TOKEN`` (valid GO-* shape)
- local SurrealDB @ ``127.0.0.1:8010``, secrets, ``context_query.local.yaml``
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

import pytest

from tests.local.surrealdb.memory_db_proof_helpers import (
    MemoryDbProofSqlClient,
    MemoryWriteSmokeRecordPlan,
    assert_memory_write_smoke_records_absent,
    build_memory_write_smoke_plan,
    cleanup_memory_write_smoke_records,
    materialize_memory_write_smoke_evidence,
    materialize_memory_write_smoke_memory_record,
    memory_write_smoke_tmp_root,
    resolve_memory_write_smoke_run_id,
)
from tools.surrealdb.memory_contract import validate_memory_id_matches_record
from tools.surrealdb.memory_db_read_proof import prove_agent_memory_db_read_v1
from tools.surrealdb.memory_db_write_smoke import (
    WRITE_SMOKE_ENV_VAR,
    execute_gated_local_memory_write_v1,
)
from tools.surrealdb.memory_write_gate import MemoryWriteAuthorization
from tools.mcp.context_evidence_memory_tools import TOOL_CDB_CONTEXT_MEMORY_GET
from tools.mcp.surrealdb_adapter_factory import build_adapter_from_params

pytestmark = pytest.mark.local_only

_REPO_ROOT = Path(__file__).resolve().parents[3]
_QUERY_CONFIG_PATH = (
    _REPO_ROOT / "infrastructure" / "config" / "surrealdb" / "context_query.local.yaml"
)
_LOCAL_SURR_URLS = (
    "http://127.0.0.1:8010/health",
    "http://127.0.0.1:8010/version",
)
_NOW = datetime(2026, 5, 29, 14, 0, 0, tzinfo=timezone.utc)


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


def _require_write_smoke_opt_in() -> Path:
    if os.environ.get(WRITE_SMOKE_ENV_VAR) != "1":
        pytest.skip(
            "real surrealdb-local memory write smoke disabled; "
            f"set {WRITE_SMOKE_ENV_VAR}=1"
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
            "(set CDB_CONTEXT_SECRETS_PATH or SECRETS_PATH)"
        )
    if not (secrets_dir / "SURREALDB_ENV").is_file():
        pytest.skip("missing required secrets file SURREALDB_ENV in secrets dir")
    for url in _LOCAL_SURR_URLS:
        status = _http_status(url)
        if status != 200:
            pytest.skip(f"local SurrealDB preflight failed for {url} (status={status})")
    return secrets_dir


def _operator_authorization(plan: MemoryWriteSmokeRecordPlan) -> MemoryWriteAuthorization:
    token = os.environ.get("CDB_MEMORY_WRITE_HUMAN_GO_TOKEN", "").strip()
    if not token:
        pytest.skip(
            "missing operator GO token; set CDB_MEMORY_WRITE_HUMAN_GO_TOKEN "
            "(GO-YYYY-MM-DD[-suffix])"
        )
    return MemoryWriteAuthorization(
        human_go_token=token,
        authorized_by=os.environ.get("CDB_MEMORY_WRITE_AUTHORIZED_BY", "operator").strip()
        or "operator",
        authorized_at=os.environ.get(
            "CDB_MEMORY_WRITE_AUTHORIZED_AT", "2026-05-29T14:00:00+00:00"
        ).strip(),
        scope=plan.scope,
        target_issue=os.environ.get("CDB_MEMORY_WRITE_TARGET_ISSUE", "2694").strip()
        or "2694",
        evidence_refs=tuple(
            part.strip()
            for part in os.environ.get(
                "CDB_MEMORY_WRITE_EVIDENCE_REFS",
                "github:issue/2694",
            ).split(",")
            if part.strip()
        )
        or ("github:issue/2694",),
        operation="create",
    )


def _assert_no_secret_leak(payload: dict[str, Any], *, secrets_path: Path) -> None:
    rendered = json.dumps(payload, sort_keys=True, default=str)
    assert "Authorization" not in rendered
    assert "Basic " not in rendered
    assert "SURREAL_PASS" not in rendered
    assert "SURREAL_USER" not in rendered
    assert str(secrets_path) not in rendered
    token = os.environ.get("CDB_MEMORY_WRITE_HUMAN_GO_TOKEN", "")
    if token:
        assert token not in rendered


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


@pytest.fixture
def memory_write_smoke_context() -> (
    tuple[MemoryWriteSmokeRecordPlan, Path, MemoryDbProofSqlClient]
):
    secrets_path = _require_write_smoke_opt_in()
    run_id = resolve_memory_write_smoke_run_id()
    plan = build_memory_write_smoke_plan(run_id)
    tmp_root = memory_write_smoke_tmp_root(run_id)
    sql_client = MemoryDbProofSqlClient.from_secrets_dir(secrets_path)
    assert_memory_write_smoke_records_absent(sql_client, plan)
    try:
        yield plan, secrets_path, sql_client
    finally:
        cleanup_memory_write_smoke_records(sql_client, plan)
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=False)


def test_memory_db_write_smoke_skips_without_env_flag() -> None:
    if os.environ.get(WRITE_SMOKE_ENV_VAR) == "1":
        pytest.skip("env flag set; covered by gated write smoke test")
    with pytest.raises(pytest.skip.Exception):
        _require_write_smoke_opt_in()


def test_memory_db_write_smoke_gated_upsert_and_read_back(
    memory_write_smoke_context: tuple[
        MemoryWriteSmokeRecordPlan, Path, MemoryDbProofSqlClient
    ],
) -> None:
    plan, secrets_path, sql_client = memory_write_smoke_context
    record = materialize_memory_write_smoke_memory_record(run_id=plan.run_id, plan=plan)
    evidence = materialize_memory_write_smoke_evidence(run_id=plan.run_id, plan=plan)
    auth = _operator_authorization(plan)

    result = execute_gated_local_memory_write_v1(
        record=record,
        authorization=auth,
        sql_client=sql_client,
        evidence_record=evidence,
        evidence_id=plan.evidence_id,
        now=_NOW,
    )
    assert result["write_status"] == "written_local_only"
    assert result["gate_status"] == "approved_dry_run"
    assert result["persist_allowed"] is False
    assert result["memory_id"] == plan.memory_id
    assert result["evidence_id"] == plan.evidence_id

    validate_memory_id_matches_record(record)

    adapter = _build_adapter(secrets_path)
    proof = prove_agent_memory_db_read_v1(
        adapter=adapter,
        scope=plan.scope,
        limit=10,
        now=_NOW,
    )
    assert proof["source"] == "surrealdb-local"
    assert plan.memory_id in proof["memory_ids"]
    _assert_no_secret_leak(result, secrets_path=secrets_path)
    _assert_no_secret_leak(proof, secrets_path=secrets_path)
