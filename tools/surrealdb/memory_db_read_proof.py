"""DB-backed agent_memory read proof helper — #2606 Memory Reality Slice 4.

Read-only proof that rows loaded from a local SurrealDB adapter satisfy the
memory contract (memory_id, required fields, TTL/freshness) and align with the
in-memory ``read_memory_v1`` path after MCP normalization.

No writes. No MCP registry changes. No live trading scope.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from core.utils.clock import utcnow as cdb_utcnow
from tools.mcp.context_evidence_memory_tools import _normalize_memory_row
from tools.mcp.surrealdb_adapter_factory import adapter_source
from tools.surrealdb.memory_contract import (
    MemoryContractError,
    MemoryFreshness,
    SCHEMA_VERSION as MEMORY_CONTRACT_SCHEMA_VERSION,
    classify_memory_freshness,
    validate_memory_record,
)
from tools.surrealdb.memory_read import MemoryReadRequest, read_memory_v1

PROOF_SCHEMA_VERSION = "memory-db-read-proof/v1"

_SURQL_SAFE_RE = re.compile(r"^[a-zA-Z0-9/_.@:#+ \-]+$")

_DB_STRIP_FIELDS = frozenset(
    {
        "run_id",
        "schema_version",
        "id",
        "sensitivity",
    }
)


class MemoryProofAdapter(Protocol):
    """Minimal adapter surface required for DB read proof."""

    status: str

    def execute(self, query: str) -> list[dict[str, Any]]: ...


def _safe_surql_str(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    return text if (text and _SURQL_SAFE_RE.match(text)) else None


def _strip_db_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in dict(row).items() if key not in _DB_STRIP_FIELDS
    }


def _serialize_freshness(freshness: MemoryFreshness) -> dict[str, Any]:
    return {
        "is_fresh": freshness.is_fresh,
        "is_stale": freshness.is_stale,
        "is_expired": freshness.is_expired,
        "reasons": list(freshness.reasons),
    }


def _resolve_now(now: datetime | None) -> datetime:
    effective = now if now is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def prove_agent_memory_db_read_v1(
    *,
    adapter: MemoryProofAdapter,
    scope: str,
    limit: int = 200,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prove DB-backed agent_memory rows satisfy the v1 memory contract.

    Args:
        adapter: Read-only query adapter (typically ``SurrealDBLocalQueryAdapter``).
        scope: Exact scope filter for ``SELECT * FROM agent_memory``.
        limit: Maximum rows to load (1..10000).
        now: Reference instant for freshness classification (UTC).

    Returns:
        Structured proof bundle with validated records, freshness, and evidence refs.

    Raises:
        MemoryContractError: Invalid scope/limit or contract violation on any row.
        ValueError: When scope cannot be safely embedded in SurrealQL.
    """
    safe_scope = _safe_surql_str(scope)
    if not safe_scope:
        raise ValueError(f"scope is not safe for SurrealQL embedding: {scope!r}")

    if limit < 1 or limit > 10_000:
        raise MemoryContractError("limit must be within 1..10000")

    ref_now = _resolve_now(now)
    source = adapter_source(adapter)

    query = f"SELECT * FROM agent_memory WHERE scope = '{safe_scope}' LIMIT {limit}"
    raw_rows = adapter.execute(query)

    validated_records: list[dict[str, Any]] = []
    memory_ids: list[str] = []
    evidence_ref_set: set[str] = set()

    for raw_row in raw_rows:
        if not isinstance(raw_row, Mapping):
            continue
        stripped = _strip_db_metadata(raw_row)
        validated = validate_memory_record(stripped, strict=False)
        freshness = classify_memory_freshness(validated, now=ref_now)
        memory_ids.append(validated["memory_id"])
        for ref in validated.get("evidence_refs") or []:
            if isinstance(ref, str) and ref.strip():
                evidence_ref_set.add(ref.strip())
        validated_records.append(
            {
                "record": validated,
                "freshness": _serialize_freshness(freshness),
            }
        )

    normalized_for_reader = [
        _normalize_memory_row(item["record"]) for item in validated_records
    ]
    crosscheck = read_memory_v1(
        normalized_for_reader,
        MemoryReadRequest(mode="by_scope", scope=safe_scope, limit=limit),
        now=ref_now,
    )
    crosscheck_ids = [
        str(item.get("memory_id"))
        for item in crosscheck.get("matched_memory") or []
        if item.get("memory_id")
    ]

    limitations = [
        "read_only_proof_no_writes",
        "db_metadata_fields_stripped_before_validation",
        "strict_false_allows_importer_only_fields_when_present",
    ]
    if len(crosscheck_ids) != len(memory_ids):
        limitations.append("read_memory_v1_crosscheck_count_mismatch")

    return {
        "schema_version": PROOF_SCHEMA_VERSION,
        "memory_contract_schema_version": MEMORY_CONTRACT_SCHEMA_VERSION,
        "source": source,
        "adapter_status": adapter.status,
        "scope": safe_scope,
        "record_count": len(validated_records),
        "memory_ids": memory_ids,
        "evidence_refs": sorted(evidence_ref_set),
        "records": validated_records,
        "read_memory_crosscheck": {
            "matched_count": len(crosscheck_ids),
            "memory_ids": crosscheck_ids,
        },
        "limitations": limitations,
        "approval_semantics": {
            "read_only": True,
            "no_write": True,
            "no_approval": True,
            "no_live_go": True,
            "no_echtgeld_go": True,
            "note": (
                "DB-backed memory read proof only. Memory is context, not authoritative "
                "truth. No write. No Human-GO."
            ),
        },
    }
