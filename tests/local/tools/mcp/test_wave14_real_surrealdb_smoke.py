"""Opt-in local-only surrealdb-local proof for all six Wave-14 MCP tools.

Runs only when:
- ``CDB_RUN_REAL_SURREALDB_SMOKE=1``
- ``infrastructure/config/surrealdb/context_query.local.yaml`` exists
- secrets path resolves (CDB canon, overridable via env)
- local SurrealDB answers on ``127.0.0.1:8010``

Each pytest invocation uses a unique run-scoped record ID set, pre-import
absence checks, and post-run cleanup of DB rows plus ``.tmp`` artifacts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

import pytest

from tests.local.tools.mcp.wave14_smoke_helpers import (
    Wave14SmokeRecordPlan,
    Wave14SmokeSqlClient,
    assert_run_records_absent,
    assert_tmp_root_absent,
    build_record_plan,
    cleanup_run_records,
    cleanup_tmp_root,
    materialize_fixture_records,
    resolve_smoke_run_id,
    smoke_tmp_root,
)
from tools.mcp.context_decision_tools import (
    TOOL_CDB_CONTEXT_DECISION_HISTORY,
    TOOL_CDB_CONTEXT_DECISION_REPLAY,
    handle_cdb_context_decision_history,
    handle_cdb_context_decision_replay,
)
from tools.mcp.context_evidence_memory_tools import (
    TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
    TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
    TOOL_CDB_CONTEXT_MEMORY_GET,
    TOOL_CDB_CONTEXT_TRUST_SUMMARY,
    handle_cdb_context_claim_resolve,
    handle_cdb_context_evidence_resolve,
    handle_cdb_context_memory_get,
    handle_cdb_context_trust_summary,
)
from tools.surrealdb.context_importer import EXPECTED_JSONL_FILES, main as importer_main

pytestmark = pytest.mark.local_only

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "surrealdb" / "wave14_real_smoke"
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
_SEEDED_FILENAMES = frozenset(
    {
        "evidence_refs.jsonl",
        "claims.jsonl",
        "agent_memories.jsonl",
        "decision_events.jsonl",
    }
)
_LOCAL_SURR_URLS = (
    "http://127.0.0.1:8010/health",
    "http://127.0.0.1:8010/version",
)


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
    if os.environ.get("CDB_RUN_REAL_SURREALDB_SMOKE") != "1":
        pytest.skip(
            "real surrealdb-local smoke disabled; set CDB_RUN_REAL_SURREALDB_SMOKE=1"
        )

    if not _QUERY_CONFIG_PATH.exists():
        pytest.skip(
            "missing local query config: infrastructure/config/surrealdb/context_query.local.yaml"
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


def _materialize_input_bundle(
    tmp_path: Path,
    *,
    run_id: str,
    plan: Wave14SmokeRecordPlan,
) -> Path:
    bundle_dir = tmp_path / "wave14-real-smoke-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    for filename in EXPECTED_JSONL_FILES.values():
        target = bundle_dir / filename
        if filename in _SEEDED_FILENAMES:
            target.write_text(
                materialize_fixture_records(filename, run_id=run_id, plan=plan),
                encoding="utf-8",
            )
        else:
            target.write_text("", encoding="utf-8")

    return bundle_dir


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


def _common_parameters(secrets_path: Path) -> dict[str, Any]:
    return {
        "adapter_config_path": str(_QUERY_CONFIG_PATH),
        "secrets_path": str(secrets_path),
        "limit": 25,
    }


def _assert_no_secret_leak(payload: dict[str, Any], *, secrets_path: Path) -> None:
    rendered = json.dumps(payload, sort_keys=True, default=str)
    assert "Authorization" not in rendered, "secret-like token leaked in payload"
    assert "Basic " not in rendered, "secret-like token leaked in payload"
    assert "SURREAL_PASS" not in rendered, "secret-like token leaked in payload"
    assert "SURREAL_USER" not in rendered, "secret-like token leaked in payload"
    assert str(secrets_path) not in rendered, "secret-like token leaked in payload"


def _assert_ok_source(payload: dict[str, Any], tool_name: str) -> None:
    assert payload["status"] == "ok", payload
    assert payload["tool"] == tool_name
    assert payload["metadata"]["source"] == "surrealdb-local", payload
    assert payload["metadata"]["read_only"] is True, payload


def _run_handler_smoke_checks(seeded_bundle: dict[str, Any]) -> None:
    secrets_path = Path(seeded_bundle["secrets_path"])
    common = _common_parameters(secrets_path)

    evidence = handle_cdb_context_evidence_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                **common,
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )
    _assert_ok_source(evidence, TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE)
    _assert_no_secret_leak(evidence, secrets_path=secrets_path)
    assert evidence["result"]["matched_evidence"], evidence

    claim = handle_cdb_context_claim_resolve(
        {
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {**common, "mode": "by_scope", "scope": "wave14"},
        }
    )
    _assert_ok_source(claim, TOOL_CDB_CONTEXT_CLAIM_RESOLVE)
    _assert_no_secret_leak(claim, secrets_path=secrets_path)
    assert claim["result"]["matched_claims"], claim

    memory = handle_cdb_context_memory_get(
        {
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {**common, "mode": "by_scope", "scope": "wave14"},
        }
    )
    _assert_ok_source(memory, TOOL_CDB_CONTEXT_MEMORY_GET)
    _assert_no_secret_leak(memory, secrets_path=secrets_path)
    assert memory["result"]["matched_memory"], memory

    history = handle_cdb_context_decision_history(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_HISTORY,
            "parameters": {**common, "mode": "by_scope", "scope": "wave14"},
        }
    )
    _assert_ok_source(history, TOOL_CDB_CONTEXT_DECISION_HISTORY)
    _assert_no_secret_leak(history, secrets_path=secrets_path)
    assert history["result"]["matched_decisions"], history

    replay = handle_cdb_context_decision_replay(
        {
            "tool": TOOL_CDB_CONTEXT_DECISION_REPLAY,
            "parameters": {**common, "mode": "replay_by_scope", "scope": "wave14"},
        }
    )
    _assert_ok_source(replay, TOOL_CDB_CONTEXT_DECISION_REPLAY)
    _assert_no_secret_leak(replay, secrets_path=secrets_path)
    assert replay["result"]["current_decisions"], replay

    trust = handle_cdb_context_trust_summary(
        {
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {
                **common,
                "scope": "wave14",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )
    _assert_ok_source(trust, TOOL_CDB_CONTEXT_TRUST_SUMMARY)
    _assert_no_secret_leak(trust, secrets_path=secrets_path)
    assert trust["result"]["evidence_strength"] != "none", trust


@pytest.fixture(scope="module")
def seeded_bundle() -> dict[str, Any]:
    secrets_dir = _require_local_opt_in()
    run_id = resolve_smoke_run_id()
    plan = build_record_plan(run_id)
    tmp_root = smoke_tmp_root(run_id)
    sql_client = Wave14SmokeSqlClient.from_secrets_dir(secrets_dir)

    assert_tmp_root_absent(tmp_root)
    assert_run_records_absent(sql_client, plan)

    tmp_root.mkdir(parents=True, exist_ok=True)
    input_dir = _materialize_input_bundle(tmp_root, run_id=run_id, plan=plan)
    _seed_local_surrealdb(input_dir, run_id=run_id, secrets_path=secrets_dir)

    bundle = {
        "secrets_path": str(secrets_dir),
        "run_id": run_id,
        "plan": plan,
        "tmp_root": str(tmp_root),
        "sql_client": sql_client,
    }

    yield bundle

    cleanup_run_records(sql_client, plan)
    cleanup_tmp_root(tmp_root)


@pytest.mark.parametrize(
    ("tool_name", "handler", "parameters", "result_key"),
    [
        pytest.param(
            TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            handle_cdb_context_evidence_resolve,
            {
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
            "matched_evidence",
            id="cdb_context_evidence_resolve",
        ),
        pytest.param(
            TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            handle_cdb_context_claim_resolve,
            {
                "mode": "by_scope",
                "scope": "wave14",
            },
            "matched_claims",
            id="cdb_context_claim_resolve",
        ),
        pytest.param(
            TOOL_CDB_CONTEXT_MEMORY_GET,
            handle_cdb_context_memory_get,
            {
                "mode": "by_scope",
                "scope": "wave14",
            },
            "matched_memory",
            id="cdb_context_memory_get",
        ),
        pytest.param(
            TOOL_CDB_CONTEXT_DECISION_HISTORY,
            handle_cdb_context_decision_history,
            {
                "mode": "by_scope",
                "scope": "wave14",
            },
            "matched_decisions",
            id="cdb_context_decision_history",
        ),
        pytest.param(
            TOOL_CDB_CONTEXT_DECISION_REPLAY,
            handle_cdb_context_decision_replay,
            {
                "mode": "replay_by_scope",
                "scope": "wave14",
            },
            "current_decisions",
            id="cdb_context_decision_replay",
        ),
    ],
)
def test_wave14_real_surrealdb_local_handlers_ok(
    seeded_bundle: dict[str, Any],
    tool_name: str,
    handler,
    parameters: dict[str, Any],
    result_key: str,
) -> None:
    request = {
        "tool": tool_name,
        "parameters": {
            **_common_parameters(Path(seeded_bundle["secrets_path"])),
            **parameters,
        },
    }

    result = handler(request)

    _assert_ok_source(result, tool_name)
    _assert_no_secret_leak(result, secrets_path=Path(seeded_bundle["secrets_path"]))
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    assert result["result"][result_key], result


def test_wave14_real_surrealdb_local_trust_summary_ok(
    seeded_bundle: dict[str, Any],
) -> None:
    result = handle_cdb_context_trust_summary(
        {
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {
                **_common_parameters(Path(seeded_bundle["secrets_path"])),
                "scope": "wave14",
                "artifact": "tools/surrealdb/evidence_lookup.py",
            },
        }
    )

    _assert_ok_source(result, TOOL_CDB_CONTEXT_TRUST_SUMMARY)
    _assert_no_secret_leak(result, secrets_path=Path(seeded_bundle["secrets_path"]))
    assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
    assert result["result"]["evidence_strength"] != "none", result
    assert result["result"]["claim_status_summary"].get("supported", 0) >= 1, result
    assert result["result"]["memory_trust_summary"]["total"] >= 1, result
    assert result["result"]["decision_currentness"]["total"] >= 1, result


def test_wave14_real_smoke_cleanup_proof(seeded_bundle: dict[str, Any]) -> None:
    """Post-cleanup assertions run in the module fixture finalizer."""
    plan: Wave14SmokeRecordPlan = seeded_bundle["plan"]
    sql_client: Wave14SmokeSqlClient = seeded_bundle["sql_client"]
    for table, raw_id in plan.records_by_table:
        assert sql_client.record_exists(
            table, raw_id
        ), f"expected seeded record before cleanup: {table}:{raw_id}"


def test_wave14_real_smoke_idempotent_cycle() -> None:
    """Two isolated seed/query/cleanup cycles in one opt-in run."""
    secrets_dir = _require_local_opt_in()

    for _ in range(2):
        run_id = resolve_smoke_run_id()
        plan = build_record_plan(run_id)
        tmp_root = smoke_tmp_root(run_id)
        sql_client = Wave14SmokeSqlClient.from_secrets_dir(secrets_dir)

        assert_tmp_root_absent(tmp_root)
        assert_run_records_absent(sql_client, plan)

        tmp_root.mkdir(parents=True, exist_ok=True)
        input_dir = _materialize_input_bundle(tmp_root, run_id=run_id, plan=plan)
        _seed_local_surrealdb(input_dir, run_id=run_id, secrets_path=secrets_dir)

        bundle = {"secrets_path": str(secrets_dir)}
        _run_handler_smoke_checks(bundle)

        cleanup_run_records(sql_client, plan)
        cleanup_tmp_root(tmp_root)
