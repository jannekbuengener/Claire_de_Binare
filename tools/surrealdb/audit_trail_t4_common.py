"""Shared helpers for T4 governed agent_memory operator tooling (#2758)."""
from __future__ import annotations

import hashlib

from tools.surrealdb.audit_trail_t3_common import (  # noqa: F401 — re-export
    CONTAINER_NAME,
    DEFAULT_DB,
    DEFAULT_NS,
    AuditTrailEnv,
    build_ssl_context,
    check_statement_results,
    container_network_names,
    endpoint_fingerprint as t3_endpoint_fingerprint,
    guard_non_localhost,
    health_check,
    load_env_file,
    redact_output,
    resolve_env_file,
    resolve_secrets_path,
    sql_request,
)

T4_ENDPOINT_CLASS = "governed_non_localhost_T4"
T4_PRODUCTIVE_ENV_VAR = "CDB_PERSIST_PRODUCTIVE_AGENT_MEMORY"
T4_WRITE_PROOF_BLOCKED_CODE = "g3_track_required"
T4_WRITE_PROOF_BLOCKED_MESSAGE = (
    "T4 write-proof-row refused: G3 PERSIST_ALLOWED flip and HG-W operator track "
    "required before productive agent_memory proof writes."
)
T4_PROOF_SCOPE = "g4-hgw-proof-2758"
T4_WRITER_SCOPE = "audit_observation_then_agent_memory"


def endpoint_fingerprint(*, ns: str, db: str, mtls_policy: str = "optional") -> str:
    payload = (
        f"endpoint_class={T4_ENDPOINT_CLASS}|ns={ns}|db={db}|tls=1|mtls={mtls_policy}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
