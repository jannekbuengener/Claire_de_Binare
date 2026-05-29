"""DB-backed agent_memory stale/expired scan — #2702 Wave-16 runtime gap.

Read-only scan that loads ``agent_memory`` rows from a local SurrealDB adapter,
classifies freshness via ``classify_memory_freshness``, and surfaces stale/expired
memory IDs with optional Wave-16 ``memory_ttl_expired`` findings.

No writes. No MCP registry changes. No live trading scope.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from core.utils.clock import utcnow as cdb_utcnow
from tools.mcp.surrealdb_adapter_factory import adapter_source
from tools.surrealdb.memory_contract import (
    MemoryContractError,
    MemoryFreshness,
    SCHEMA_VERSION as MEMORY_CONTRACT_SCHEMA_VERSION,
    classify_memory_freshness,
    validate_memory_record,
)
from tools.surrealdb.stale_knowledge_scan import scan_stale_knowledge_v1

SCAN_SCHEMA_VERSION = "memory-db-stale-scan/v1"

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
    """Minimal adapter surface required for DB stale scan."""

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


def _wave16_memory_ttl_findings(
    *,
    expired_records: list[dict[str, Any]],
    as_of: str,
) -> dict[str, Any]:
    """Bridge expired DB rows into Wave-16 memory_ttl_expired findings (read-only)."""
    memory_records = [
        {
            "memory_id": item["record"]["memory_id"],
            "expires_at": item["record"].get("expires_at"),
            "scope": item["record"].get("scope"),
        }
        for item in expired_records
        if item["record"].get("expires_at")
    ]
    if not memory_records:
        return {
            "finding_count": 0,
            "stale_ids": [],
            "stale_types": [],
        }

    scan_result = scan_stale_knowledge_v1(
        {"memory_records": memory_records},
        as_of=as_of,
    )
    memory_findings = [
        f for f in scan_result.findings if f.stale_type == "memory_ttl_expired"
    ]
    return {
        "finding_count": len(memory_findings),
        "stale_ids": [f.stale_id for f in memory_findings],
        "stale_types": sorted({f.stale_type for f in memory_findings}),
    }


def scan_agent_memory_stale_v1(
    *,
    adapter: MemoryProofAdapter,
    scope: str,
    limit: int = 200,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Scan DB-backed agent_memory rows for stale/expired state (read-only).

    Args:
        adapter: Read-only query adapter (typically ``SurrealDBLocalQueryAdapter``).
        scope: Exact scope filter for ``SELECT * FROM agent_memory``.
        limit: Maximum rows to load (1..10000).
        now: Reference instant for freshness classification (UTC).

    Returns:
        Structured scan bundle with stale/expired counts, memory IDs, and optional
        Wave-16 ``memory_ttl_expired`` bridge findings.

    Raises:
        MemoryContractError: Invalid limit or contract violation on any row.
        ValueError: When scope cannot be safely embedded in SurrealQL.
    """
    safe_scope = _safe_surql_str(scope)
    if not safe_scope:
        raise ValueError(f"scope is not safe for SurrealQL embedding: {scope!r}")

    if limit < 1 or limit > 10_000:
        raise MemoryContractError("limit must be within 1..10000")

    ref_now = _resolve_now(now)
    as_of = ref_now.isoformat()
    source = adapter_source(adapter)

    query = f"SELECT * FROM agent_memory WHERE scope = '{safe_scope}' LIMIT {limit}"
    raw_rows = adapter.execute(query)

    all_records: list[dict[str, Any]] = []
    stale_records: list[dict[str, Any]] = []
    expired_records: list[dict[str, Any]] = []
    stale_memory_ids: list[str] = []
    expired_memory_ids: list[str] = []

    for raw_row in raw_rows:
        if not isinstance(raw_row, Mapping):
            continue
        stripped = _strip_db_metadata(raw_row)
        validated = validate_memory_record(stripped, strict=False)
        freshness = classify_memory_freshness(validated, now=ref_now)
        entry = {
            "record": validated,
            "freshness": _serialize_freshness(freshness),
        }
        all_records.append(entry)
        if freshness.is_stale:
            stale_records.append(entry)
            stale_memory_ids.append(validated["memory_id"])
        if freshness.is_expired:
            expired_records.append(entry)
            expired_memory_ids.append(validated["memory_id"])

    fresh_count = len(all_records) - len(stale_records)
    wave16 = _wave16_memory_ttl_findings(
        expired_records=expired_records,
        as_of=as_of,
    )

    limitations = [
        "read_only_scan_no_writes",
        "db_metadata_fields_stripped_before_validation",
        "strict_false_allows_importer_only_fields_when_present",
        "wave16_bridge_uses_memory_ttl_expired_only_for_expired_rows_with_expires_at",
    ]

    return {
        "schema_version": SCAN_SCHEMA_VERSION,
        "memory_contract_schema_version": MEMORY_CONTRACT_SCHEMA_VERSION,
        "source": source,
        "adapter_status": adapter.status,
        "scope": safe_scope,
        "as_of": as_of,
        "record_count": len(all_records),
        "fresh_count": fresh_count,
        "stale_count": len(stale_records),
        "expired_count": len(expired_records),
        "stale_memory_ids": stale_memory_ids,
        "expired_memory_ids": expired_memory_ids,
        "stale_records": stale_records,
        "expired_records": expired_records,
        "wave16_memory_ttl": wave16,
        "limitations": limitations,
        "approval_semantics": {
            "read_only": True,
            "no_write": True,
            "no_approval": True,
            "no_live_go": True,
            "no_echtgeld_go": True,
            "note": (
                "DB-backed stale/expired memory scan only. Stale detection is signal, "
                "not authorization. No write. No Human-GO."
            ),
        },
    }
