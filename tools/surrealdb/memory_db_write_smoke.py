"""Local-only gated memory write smoke — #2606 Memory Reality Slice 6.

Executes a minimal SurrealDB write only after Human-GO gate pass and explicit
env opt-in. No MCP writes. No productive memory path.

Guardrails:
    - Module-level PERSIST_ALLOWED in memory_write_gate stays False.
    - Runtime permission requires CDB_RUN_REAL_SURREALDB_MEMORY_WRITE=1.
    - Gate must return approved_dry_run before any SQL UPSERT.
    - LR remains NO-GO.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.memory_write_gate import (
    GATE_SCHEMA_VERSION,
    MemoryWriteAuthorization,
    evaluate_memory_write_gate,
)

WRITE_SMOKE_SCHEMA_VERSION = "memory-db-write-smoke/v1"
WRITE_SMOKE_ENV_VAR = "CDB_RUN_REAL_SURREALDB_MEMORY_WRITE"
OBSERVED_BY = "memory_db_write_smoke/v1"


class MemoryWriteSmokeError(RuntimeError):
    """Raised when gated local write smoke preconditions are not met."""


class MemoryWriteSqlClient(Protocol):
    """Minimal SQL client surface for local write smoke."""

    def upsert_create(self, table: str, record_id: str, payload: dict[str, Any]) -> None: ...

    def record_exists(self, table: str, raw_id: str, *, id_field: str) -> bool: ...


def write_smoke_env_enabled() -> bool:
    return os.environ.get(WRITE_SMOKE_ENV_VAR) == "1"


def local_write_smoke_enabled(envelope: Mapping[str, Any]) -> bool:
    return (
        write_smoke_env_enabled()
        and envelope.get("gate_status") == "approved_dry_run"
        and envelope.get("persist_allowed") is False
    )


def _parse_observed_at(value: datetime | None) -> datetime:
    effective = value if value is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def _audit_safe_envelope(
    envelope: dict[str, Any],
    *,
    write_status: str,
    tables_written: tuple[str, ...],
    memory_id: str,
    evidence_id: str,
) -> dict[str, Any]:
    audit = dict(envelope.get("audit") or {})
    audit["observation_type"] = "memory_write_smoke_execution"
    audit["observed_by"] = OBSERVED_BY
    audit["subject_ref"] = memory_id
    audit["gate_status"] = envelope.get("gate_status")
    audit["write_status"] = write_status
    audit["tables_written"] = list(tables_written)
    audit["related_memory"] = [memory_id]
    audit["evidence_refs"] = [evidence_id]
    return {
        "schema_version": WRITE_SMOKE_SCHEMA_VERSION,
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "write_status": write_status,
        "gate_status": envelope.get("gate_status"),
        "persist_allowed": False,
        "memory_id": memory_id,
        "evidence_id": evidence_id,
        "tables_written": list(tables_written),
        "audit": audit,
        "limitations": [
            "local_only",
            "run_scoped_cleanup_required",
            "lr_no_go",
            "persist_allowed_false",
            "slice_6_smoke_only",
        ],
        "approval_semantics": envelope.get("approval_semantics"),
    }


def execute_gated_local_memory_write_v1(
    *,
    record: Mapping[str, Any],
    authorization: MemoryWriteAuthorization,
    sql_client: MemoryWriteSqlClient,
    evidence_record: Mapping[str, Any],
    evidence_id: str,
    strict: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate gate, then UPSERT evidence_ref and agent_memory on localhost only.

    Fail-closed: raises MemoryWriteSmokeError when gate blocks or env is unset.
    Never logs raw human_go_token.
    """
    observed_at = _parse_observed_at(now)
    envelope = evaluate_memory_write_gate(
        record,
        authorization,
        strict=strict,
        now=observed_at,
    )
    gate_status = envelope.get("gate_status")
    if gate_status != "approved_dry_run":
        raise MemoryWriteSmokeError(
            f"memory write smoke blocked: gate_status={gate_status!r}"
        )
    if not local_write_smoke_enabled(envelope):
        raise MemoryWriteSmokeError(
            "memory write smoke blocked: "
            f"{WRITE_SMOKE_ENV_VAR} must be '1' and gate must approve dry-run only"
        )

    validated = envelope.get("validated_record")
    if not isinstance(validated, dict):
        raise MemoryWriteSmokeError(
            "memory write smoke blocked: gate envelope missing validated_record"
        )
    memory_id = str(validated["memory_id"])
    if not evidence_id.strip():
        raise MemoryWriteSmokeError("memory write smoke blocked: evidence_id is required")

    if sql_client.record_exists("agent_memory", memory_id, id_field="memory_id"):
        raise MemoryWriteSmokeError(
            f"memory write smoke blocked: agent_memory already exists: {memory_id}"
        )
    if sql_client.record_exists("evidence_ref", evidence_id, id_field="evidence_id"):
        raise MemoryWriteSmokeError(
            f"memory write smoke blocked: evidence_ref already exists: {evidence_id}"
        )

    evidence_payload = dict(evidence_record)
    memory_payload = dict(validated)

    sql_client.upsert_create("evidence_ref", evidence_id, evidence_payload)
    sql_client.upsert_create("agent_memory", memory_id, memory_payload)

    if not sql_client.record_exists("evidence_ref", evidence_id, id_field="evidence_id"):
        raise MemoryWriteSmokeError(
            f"memory write smoke failed: evidence_ref not found after write: {evidence_id}"
        )
    if not sql_client.record_exists("agent_memory", memory_id, id_field="memory_id"):
        raise MemoryWriteSmokeError(
            f"memory write smoke failed: agent_memory not found after write: {memory_id}"
        )

    return _audit_safe_envelope(
        envelope,
        write_status="written_local_only",
        tables_written=("evidence_ref", "agent_memory"),
        memory_id=memory_id,
        evidence_id=evidence_id,
    )
