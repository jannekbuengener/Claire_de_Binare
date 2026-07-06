"""Opt-in local-only read-only SurrealDB context query harness (#3776).

Runs only when:
- ``CDB_RUN_REAL_SURREALDB_READONLY_QUERY=1``
- ``infrastructure/config/surrealdb/context_query.local.yaml`` exists
- secrets path resolves (CDB canon, overridable via env)
- local SurrealDB answers on ``127.0.0.1:8010``

Read-only probes only — no importer, no UPSERT, no MCP write tools.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request

import pytest

from tools.surrealdb import context_readonly_query_harness as harness
from tools.surrealdb.context_query import WriteDeniedError

pytestmark = pytest.mark.local_only

_REPO_ROOT = Path(__file__).resolve().parents[3]
_QUERY_CONFIG_PATH = _REPO_ROOT / harness.QUERY_CONFIG_REL
_LOCAL_SURR_URLS = (
    f"{harness.LOCAL_SURR_URL}/health",
    f"{harness.LOCAL_SURR_URL}/version",
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
    if os.environ.get(harness.ENV_REAL_SURREALDB_READONLY_QUERY) != "1":
        pytest.skip(
            "real surrealdb-local read-only harness disabled; "
            f"set {harness.ENV_REAL_SURREALDB_READONLY_QUERY}=1"
        )
    if not _QUERY_CONFIG_PATH.exists():
        pytest.skip(f"missing local query config: {harness.QUERY_CONFIG_REL}")
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


def _assert_no_secret_leak(payload: dict, *, secrets_path: Path) -> None:
    rendered = json.dumps(payload, sort_keys=True, default=str)
    assert "Authorization" not in rendered
    assert "Basic " not in rendered
    assert "SURREAL_PASS" not in rendered
    assert "SURREAL_USER" not in rendered
    assert str(secrets_path) not in rendered


def test_readonly_harness_skips_without_env_flag() -> None:
    if os.environ.get(harness.ENV_REAL_SURREALDB_READONLY_QUERY) == "1":
        pytest.skip("env flag set; covered by live probe test")
    with pytest.raises(pytest.skip.Exception):
        _require_local_opt_in()


def test_readonly_query_probe_against_local_db() -> None:
    secrets_path = _require_local_opt_in()
    adapter = harness.build_live_adapter(
        config_path=_QUERY_CONFIG_PATH,
        secrets_path=secrets_path,
        hard_mode=True,
    )
    isolation = harness.build_isolation()
    assert adapter._namespace == isolation.namespace
    assert adapter._database == isolation.database

    probe = harness.run_readonly_probe(adapter)
    assert probe["read_only"] is True
    assert probe["classification"]["allowed"] is True
    assert probe["adapter_status"] == "surrealdb-local"

    posture = harness.classify_db_evidence_posture(
        db_reachable=True,
        record_source="surrealdb-local",
        record_ids=[f"probe:{probe['row_count']}"],
    )
    assert posture["db_claims_allowed"] is True
    _assert_no_secret_leak(probe, secrets_path=secrets_path)


def test_write_probe_denied_before_http() -> None:
    secrets_path = _require_local_opt_in()
    adapter = harness.build_live_adapter(
        config_path=_QUERY_CONFIG_PATH,
        secrets_path=secrets_path,
        hard_mode=True,
    )
    with pytest.raises(WriteDeniedError):
        harness.run_readonly_probe(adapter, query=harness.HARNESS_WRITE_PROBE)
