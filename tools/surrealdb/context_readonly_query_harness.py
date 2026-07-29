"""Read-only SurrealDB context query integration harness (#3776).

Local-only test surface for read-only context queries against surrealdb-local.
No productive writes, no MCP mutation, no trading-state tables.

LR remains NO-GO.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from tools.mcp.memory_write_intent_tools import MUTATION_ALLOWED
from tools.surrealdb.context_query import (
    QueryAdapter,
    SurrealDBLocalQueryAdapter,
    WriteDeniedError,
    classify_statement,
    load_config,
)
from tools.surrealdb.memory_db_proof_local_dev import (
    LOCAL_DB,
    LOCAL_NS,
    LOCAL_SURR_URL,
    QUERY_CONFIG_REL,
    http_status,
    repo_root,
    resolve_secrets_path,
)
from tools.surrealdb.context_query import _load_query_credentials

SCHEMA_VERSION = "context-readonly-query-harness/v1"
ENV_REAL_SURREALDB_READONLY_QUERY = "CDB_RUN_REAL_SURREALDB_READONLY_QUERY"

HARNESS_NAMESPACE = LOCAL_NS
HARNESS_DATABASE = LOCAL_DB
HARNESS_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_LOCAL_HEALTH_URLS = (
    f"{LOCAL_SURR_URL}/health",
    f"{LOCAL_SURR_URL}/version",
)

HARNESS_PROBE_QUERY = "SELECT * FROM repo_artifact LIMIT 0"
HARNESS_WRITE_PROBE = "CREATE agent_memory:test SET content = 'denied'"

TestMode = Literal["embedded", "file", "mem", "live"]

_FORBIDDEN_WRITE_IMPORTS = frozenset(
    {
        "context_importer",
        "memory_write_gate",
        "memory_write_path_v1",
        "memory_write_path_t4",
        "memory_db_write_smoke",
    }
)


@dataclass(frozen=True)
class HarnessIsolation:
    """Namespace/database isolation contract for local read-only probes."""

    namespace: str
    database: str
    surreal_url: str
    run_tag: str | None = None

    def as_headers(self) -> dict[str, str]:
        return {
            "surreal-ns": self.namespace,
            "surreal-db": self.database,
            "surreal-url": self.surreal_url.rstrip("/"),
        }


class MemQueryAdapter(QueryAdapter):
    """In-memory read-only adapter for harness unit tests (no network)."""

    status = "mem-readonly"

    def __init__(
        self,
        rows: list[dict[str, Any]] | None = None,
        *,
        namespace: str = HARNESS_NAMESPACE,
        database: str = HARNESS_DATABASE,
    ) -> None:
        super().__init__(config=None)
        self._rows = list(rows or [])
        self.namespace = namespace
        self.database = database

    def execute(self, query: str) -> list[dict[str, Any]]:
        classification = self.classify(query)
        if not classification.allowed:
            raise WriteDeniedError(classification.reason)
        if "LIMIT 0" in query.upper():
            return []
        return list(self._rows)


def harness_safety_flags() -> dict[str, bool]:
    return {
        "MUTATION_ALLOWED": bool(MUTATION_ALLOWED),
        "read_only_default": True,
        "productive_write_path": False,
    }


def build_isolation(*, run_tag: str | None = None) -> HarnessIsolation:
    """Return the canonical local read-only isolation envelope."""

    return HarnessIsolation(
        namespace=HARNESS_NAMESPACE,
        database=HARNESS_DATABASE,
        surreal_url=LOCAL_SURR_URL,
        run_tag=run_tag,
    )


def classify_db_evidence_posture(
    *,
    db_reachable: bool,
    record_source: str | None = None,
    record_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Fail-closed posture for DB-backed claims (#3776)."""

    has_records = bool(record_ids)
    if db_reachable and record_source == "surrealdb-local" and has_records:
        return {
            "evidence_posture": "db_backed",
            "brain_source": "surrealdb-local",
            "brain_status": "partial",
            "db_claims_allowed": True,
            "repo_fallback_used": False,
            "repo_fallback_reason": "none",
            "record_ids": list(record_ids or ()),
        }
    return {
        "evidence_posture": "repo_only",
        "brain_source": "repo-only",
        "brain_status": "not-used",
        "db_claims_allowed": False,
        "repo_fallback_used": True,
        "repo_fallback_reason": "unavailable" if not db_reachable else "insufficient_evidence",
        "record_ids": [],
    }


def assert_repo_only_db_claim_blocked(
    *,
    db_reachable: bool,
    record_source: str | None,
    claimed_brain_source: str,
) -> bool:
    posture = classify_db_evidence_posture(
        db_reachable=db_reachable,
        record_source=record_source,
        record_ids=["placeholder"] if record_source == "surrealdb-local" else None,
    )
    if posture["db_claims_allowed"]:
        return False
    return claimed_brain_source in {"surrealdb-local", "used", "db_backed"}


def check_readonly_query_preconditions(*, confirm: bool = False) -> dict[str, Any]:
    """Fail-closed preflight for local read-only query harness (no pytest)."""

    errors: list[str] = []
    if os.environ.get(ENV_REAL_SURREALDB_READONLY_QUERY) != "1" and not confirm:
        errors.append(
            f"set {ENV_REAL_SURREALDB_READONLY_QUERY}=1 or pass --confirm on CLI/Makefile"
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

    db_reachable = True
    for url in _LOCAL_HEALTH_URLS:
        status = http_status(url)
        if status != 200:
            db_reachable = False
            errors.append(
                f"local SurrealDB preflight failed for {url} (status={status})"
            )

    isolation = build_isolation()
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not errors,
        "errors": errors,
        "db_reachable": db_reachable and not errors,
        "query_config_path": str(query_config) if query_config.is_file() else None,
        "secrets_path_configured": secrets_path is not None,
        "isolation": isolation.as_headers(),
        "safety_flags": harness_safety_flags(),
        "limitations": [
            "local_dev_only_127.0.0.1:8010",
            "read_only_queries_only",
            "no_productive_write_path",
            "standard_ci_excludes_local_only",
            "lr_no_go",
        ],
    }


def build_live_adapter(
    *,
    config_path: Path,
    secrets_path: Path,
    hard_mode: bool = False,
) -> SurrealDBLocalQueryAdapter:
    config = load_config(config_path)
    user, password = _load_query_credentials(config, secrets_path)
    return SurrealDBLocalQueryAdapter(
        surreal_url=config.surreal_url,
        namespace=config.namespace,
        database=config.database,
        user=user,
        password=password,
        timeout=config.timeout,
        hard_mode=hard_mode,
        config=config,
    )


def build_adapter_for_mode(
    mode: TestMode,
    *,
    config_path: Path | None = None,
    secrets_path: Path | None = None,
    mem_rows: list[dict[str, Any]] | None = None,
) -> QueryAdapter:
    if mode == "embedded":
        from tools.surrealdb.context_query import NoopQueryAdapter

        return NoopQueryAdapter()
    if mode == "mem":
        return MemQueryAdapter(mem_rows)
    if mode == "file":
        if config_path is None:
            raise ValueError("file mode requires config_path")
        config = load_config(config_path)
        return MemQueryAdapter(
            [{"config_namespace": config.namespace, "config_database": config.database}],
            namespace=config.namespace,
            database=config.database,
        )
    if mode == "live":
        if config_path is None or secrets_path is None:
            raise ValueError("live mode requires config_path and secrets_path")
        return build_live_adapter(config_path=config_path, secrets_path=secrets_path)
    raise ValueError(f"unsupported harness mode: {mode}")


def run_readonly_probe(adapter: QueryAdapter, *, query: str = HARNESS_PROBE_QUERY) -> dict[str, Any]:
    """Execute a read-only probe and return structured harness evidence."""

    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(classification.reason)
    rows = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "query": query,
        "classification": classification.to_payload(),
        "row_count": len(rows),
        "adapter_status": getattr(adapter, "status", "unknown"),
        "read_only": True,
    }


def assert_harness_has_no_productive_write_path() -> list[str]:
    """Static contract: harness module must not import productive write executors."""

    module_path = Path(__file__)
    source = module_path.read_text(encoding="utf-8")
    violations: list[str] = []
    for token in _FORBIDDEN_WRITE_IMPORTS:
        if f"import {token}" in source or f"from tools.surrealdb.{token}" in source:
            violations.append(token)
    return violations


def standard_ci_excludes_local_only() -> dict[str, Any]:
    """Repo-backed evidence that standard CI skips local_only tests."""

    root = repo_root()
    ci_yaml = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    unit_stage = (root / "ci" / "stages" / "unit.py").read_text(encoding="utf-8")
    pytest_ini = (root / "pytest.ini").read_text(encoding="utf-8")
    marker_present = "local_only:" in pytest_ini
    # #4163: thin ci.yml delegates to run.py; unit stage owns the pytest filter.
    delegates = "ci/scripts/run.py" in ci_yaml and "--profile fast" in ci_yaml
    unit_filter = "pytest" in unit_stage and "not test_mcp_time_server_runtime" in unit_stage
    ci_excludes = (
        delegates
        and unit_filter
        and "norecursedirs = local" in pytest_ini
    )
    return {
        "pytest_marker_registered": marker_present,
        "ci_excludes_local_only": ci_excludes,
        "ok": marker_present and ci_excludes,
    }
