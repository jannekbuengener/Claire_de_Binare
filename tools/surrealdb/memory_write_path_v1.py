"""Memory Write Path v1 — gated operator surface with audit_observation — #2703.

Orchestrates Human-GO gate evaluation and optional localhost audit_observation
persistence. Never performs productive agent_memory writes.

Guardrails:
    - PERSIST_ALLOWED in memory_write_gate remains False (not flipped here).
    - Default mode is dry_run (zero SQL).
    - audit_persist_local requires env CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT=1.
    - LR remains NO-GO.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Protocol

from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.audit_observation_from_gate import (
    materialize_audit_observation_from_gate,
)
from tools.surrealdb.memory_write_gate import (
    GATE_SCHEMA_VERSION,
    MemoryWriteAuthorization,
    PERSIST_ALLOWED,
    evaluate_memory_write_gate,
)

WRITE_PATH_SCHEMA_VERSION = "memory-write-path/v1"
AUDIT_PERSIST_ENV_VAR = "CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT"

MemoryWritePathMode = Literal["dry_run", "audit_persist_local"]


class MemoryWritePathError(RuntimeError):
    """Raised when write path preconditions are not met."""


class MemoryWritePathSqlClient(Protocol):
    """Minimal SQL client for localhost audit_observation UPSERT."""

    def upsert_create(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None: ...

    def record_exists(self, table: str, raw_id: str, *, id_field: str) -> bool: ...


def audit_persist_env_enabled() -> bool:
    return os.environ.get(AUDIT_PERSIST_ENV_VAR) == "1"


def _parse_now(value: datetime | None) -> datetime:
    effective = value if value is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def _path_envelope(
    gate_envelope: dict[str, Any],
    *,
    path_status: str,
    audit_observation: dict[str, Any] | None = None,
    tables_written: tuple[str, ...] = (),
) -> dict[str, Any]:
    limitations = list(gate_envelope.get("limitations") or [])
    limitations.extend(
        [
            "memory_write_path_v1",
            "persist_allowed_false",
            "lr_no_go",
            "no_agent_memory_write_in_path_v1",
        ]
    )
    if path_status == "evaluated_only":
        limitations.append("path_dry_run_only")
    if path_status == "audit_persisted_local":
        limitations.extend(["audit_persist_local_only", "run_scoped_cleanup_required"])

    return {
        "schema_version": WRITE_PATH_SCHEMA_VERSION,
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "path_status": path_status,
        "gate_status": gate_envelope.get("gate_status"),
        "persist_allowed": PERSIST_ALLOWED,
        "dry_run_only": True,
        "memory_id": gate_envelope.get("memory_id"),
        "gate": gate_envelope,
        "audit_observation": audit_observation,
        "tables_written": list(tables_written),
        "limitations": limitations,
        "approval_semantics": gate_envelope.get("approval_semantics"),
    }


def run_memory_write_path_v1(
    record: Mapping[str, Any],
    authorization: MemoryWriteAuthorization | None,
    *,
    mode: MemoryWritePathMode = "dry_run",
    sql_client: MemoryWritePathSqlClient | None = None,
    strict: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate gate and optionally persist audit_observation on localhost.

    Fail-closed: blocked gate never writes. audit_persist_local never writes
    agent_memory.
    """
    ref_now = _parse_now(now)
    gate_envelope = evaluate_memory_write_gate(
        record,
        authorization,
        strict=strict,
        now=ref_now,
    )

    if mode == "dry_run":
        return _path_envelope(gate_envelope, path_status="evaluated_only")

    if mode != "audit_persist_local":
        raise MemoryWritePathError(f"unsupported write path mode: {mode!r}")

    gate_status = gate_envelope.get("gate_status")
    if gate_status != "approved_dry_run":
        raise MemoryWritePathError(
            f"audit persist blocked: gate_status={gate_status!r}"
        )
    if not audit_persist_env_enabled():
        raise MemoryWritePathError(
            f"audit persist blocked: {AUDIT_PERSIST_ENV_VAR} must be '1'"
        )
    if sql_client is None:
        raise MemoryWritePathError("audit persist blocked: sql_client is required")

    audit_row = materialize_audit_observation_from_gate(gate_envelope, now=ref_now)
    observation_id = str(audit_row["observation_id"])

    if sql_client.record_exists(
        "audit_observation", observation_id, id_field="observation_id"
    ):
        raise MemoryWritePathError(
            f"audit persist blocked: audit_observation already exists: {observation_id}"
        )

    sql_client.upsert_create("audit_observation", observation_id, audit_row)

    if not sql_client.record_exists(
        "audit_observation", observation_id, id_field="observation_id"
    ):
        raise MemoryWritePathError(
            f"audit persist failed: audit_observation not found after write: "
            f"{observation_id}"
        )

    return _path_envelope(
        gate_envelope,
        path_status="audit_persisted_local",
        audit_observation=audit_row,
        tables_written=("audit_observation",),
    )
