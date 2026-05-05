"""Scoped Memory Read v1 — side-effect-free domain component.

Issues:
    #2120 — [SURREALDB][CONTEXT][MEMORY-READ] Implement scoped memory read v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Scope:
    Implements a minimal, deterministic scoped-memory-read slice that works
    purely on in-memory agent-memory records. No DB access. No SurrealDB SDK.
    No MCP. No networking. No writes.

Guardrails:
    - Read-only. No memory write, no mutation.
    - stale/superseded memory is explicitly flagged and never presented as truth.
    - scope is required to prevent unscoped global memory reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "memory-read/v1"

SUPPORTED_MODES = frozenset(
    {
        "by_scope",
        "by_topic",
        "by_artifact",
        "by_decision",
        "by_agent",
        "by_freshness",
        "by_memory_type",
    }
)

# Memory trust levels (ascending)
MEMORY_TRUST_LEVELS = ("stale", "superseded", "weak", "evidence_backed", "source_backed")

# Modes that REQUIRE scope for safety
_SCOPE_REQUIRED_MODES = frozenset({"by_scope"})


class MemoryReadError(ValueError):
    """Raised when memory read inputs are invalid or unsafe."""


@dataclass(frozen=True)
class MemoryReadRequest:
    """Query request for scoped memory read v1."""

    mode: str
    scope: str | None = None
    topic: str | None = None
    artifact: str | None = None
    decision: str | None = None
    agent: str | None = None
    freshness_days: int | None = None
    memory_type: str | None = None
    limit: int = 200


def _parse_datetime(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc) if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return str(value).strip() or None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compute_trust(memory: Mapping[str, Any]) -> str:
    """Classify memory trust level from record fields."""
    stale = bool(memory.get("stale", False))
    superseded = bool(memory.get("superseded", False)) or bool(memory.get("superseded_by"))
    evidence_backed = bool(memory.get("evidence_backed", False)) or bool(
        _as_list(memory.get("evidence_refs"))
    )
    source_backed = bool(memory.get("source_backed", False)) or bool(
        _as_list(memory.get("source_refs"))
    )

    if superseded:
        return "superseded"
    if stale:
        return "stale"
    if source_backed:
        return "source_backed"
    if evidence_backed:
        return "evidence_backed"
    return "weak"


def _is_stale_by_ttl(memory: Mapping[str, Any]) -> bool:
    """Return True if TTL has elapsed."""
    ttl_days = _as_int(memory.get("ttl_days"))
    if ttl_days is None:
        return False
    created_at: datetime | None = memory.get("_created_at_dt")
    if created_at is None:
        return False
    age_days = (cdb_utcnow().replace(tzinfo=timezone.utc) - created_at).days
    return age_days > ttl_days


def _normalize_memory(raw: Mapping[str, Any]) -> dict[str, Any]:
    memory_id = _as_str(raw.get("memory_id"))
    if not memory_id:
        raise MemoryReadError("memory record missing memory_id")

    created_at = _parse_datetime(raw.get("created_at"))
    memory_type = _as_str(raw.get("memory_type")) or "unknown"
    scope = _as_str(raw.get("scope")) or ""
    agent = _as_str(raw.get("agent")) or ""
    superseded_by = _as_str(raw.get("superseded_by"))
    ttl_days = _as_int(raw.get("ttl_days"))

    topics: list[str] = []
    if _as_str(raw.get("topic")):
        topics.append(str(raw["topic"]).strip())
    topics.extend([str(x) for x in _as_list(raw.get("topics")) if _as_str(x)])

    artifact_refs = [str(x) for x in _as_list(raw.get("artifact_refs")) if _as_str(x)]
    decision_refs = [str(x) for x in _as_list(raw.get("decision_refs")) if _as_str(x)]
    evidence_refs = [str(x) for x in _as_list(raw.get("evidence_refs")) if _as_str(x)]
    source_refs = [str(x) for x in _as_list(raw.get("source_refs")) if _as_str(x)]

    stale_flag = bool(raw.get("stale", False))

    entry: dict[str, Any] = {
        "memory_id": memory_id,
        "title": _as_str(raw.get("title")) or "",
        "content": _as_str(raw.get("content")) or "",
        "memory_type": memory_type,
        "scope": scope,
        "agent": agent,
        "topics": sorted(set(t for t in topics if t)),
        "artifact_refs": sorted(set(artifact_refs)),
        "decision_refs": sorted(set(decision_refs)),
        "evidence_refs": sorted(set(evidence_refs)),
        "source_refs": sorted(set(source_refs)),
        "superseded_by": superseded_by,
        "ttl_days": ttl_days,
        "stale": stale_flag,
        "superseded": bool(superseded_by),
        "evidence_backed": bool(evidence_refs),
        "source_backed": bool(source_refs),
        "created_at": created_at.isoformat() if created_at else None,
        "_created_at_dt": created_at,
    }
    # TTL-based stale detection
    if not stale_flag and _is_stale_by_ttl(entry):
        entry["stale"] = True

    entry["trust_level"] = _compute_trust(entry)
    return entry


def _memory_sort_key(mem: Mapping[str, Any]) -> tuple[int, str, str]:
    dt: datetime | None = mem.get("_created_at_dt")
    if dt is None:
        return (1, "", str(mem.get("memory_id", "")))
    return (0, dt.isoformat(), str(mem.get("memory_id", "")))


def _validate_request(req: MemoryReadRequest) -> None:
    if req.mode not in SUPPORTED_MODES:
        raise MemoryReadError(f"unsupported mode: {req.mode}")
    if req.limit < 1 or req.limit > 10_000:
        raise MemoryReadError("limit must be within 1..10000")

    required: dict[str, str] = {
        "by_scope": "scope",
        "by_topic": "topic",
        "by_artifact": "artifact",
        "by_decision": "decision",
        "by_agent": "agent",
        "by_memory_type": "memory_type",
    }
    required_field = required.get(req.mode)
    if required_field and not _as_str(getattr(req, required_field)):
        raise MemoryReadError(f"{req.mode} requires {required_field}")


def _match(memory: Mapping[str, Any], req: MemoryReadRequest) -> bool:
    if req.mode == "by_scope":
        scope = (req.scope or "").strip()
        return scope == str(memory.get("scope", "")).strip()
    if req.mode == "by_topic":
        topic = (req.topic or "").strip()
        return topic in set(memory.get("topics", []))
    if req.mode == "by_artifact":
        return (req.artifact or "").strip() in set(memory.get("artifact_refs", []))
    if req.mode == "by_decision":
        return (req.decision or "").strip() in set(memory.get("decision_refs", []))
    if req.mode == "by_agent":
        return str(memory.get("agent", "")).strip() == (req.agent or "").strip()
    if req.mode == "by_freshness":
        if req.freshness_days is None:
            return False
        dt: datetime | None = memory.get("_created_at_dt")
        if dt is None:
            return False
        age_days = (cdb_utcnow().replace(tzinfo=timezone.utc) - dt).days
        return age_days <= req.freshness_days
    if req.mode == "by_memory_type":
        return str(memory.get("memory_type", "")).strip().lower() == (req.memory_type or "").strip().lower()
    return False


def read_memory_v1(
    memory_records: Iterable[Mapping[str, Any]],
    request: MemoryReadRequest,
) -> dict[str, Any]:
    """Read scoped agent memory over in-memory records.

    Deterministic and side-effect-free. No writes.
    """
    _validate_request(request)

    warnings: list[str] = []

    normalized: list[dict[str, Any]] = []
    for raw in memory_records:
        if not isinstance(raw, Mapping):
            continue
        normalized.append(_normalize_memory(raw))

    normalized_sorted = sorted(normalized, key=_memory_sort_key)
    matched = [m for m in normalized_sorted if _match(m, request)]

    if not matched:
        warnings.append("no_memory_matched")

    matched = matched[: request.limit]

    stale_ids = [m["memory_id"] for m in matched if m.get("stale")]
    superseded_ids = [m["memory_id"] for m in matched if m.get("superseded")]

    if stale_ids:
        warnings.append("stale_memory_present")
    if superseded_ids:
        warnings.append("superseded_memory_present")

    # Trust level summary
    trust_counts: dict[str, int] = {}
    for m in matched:
        tl = str(m.get("trust_level", "weak"))
        trust_counts[tl] = trust_counts.get(tl, 0) + 1

    total = len(matched)
    source_backed = trust_counts.get("source_backed", 0)
    evidence_backed = trust_counts.get("evidence_backed", 0)
    weak_count = trust_counts.get("weak", 0)

    if total == 0:
        overall_trust = "none"
    elif (source_backed + evidence_backed) >= total * 0.7:
        overall_trust = "source_backed"
    elif (source_backed + evidence_backed) >= total * 0.4:
        overall_trust = "evidence_backed"
    elif weak_count >= total * 0.5:
        overall_trust = "weak"
    else:
        overall_trust = "weak"

    memory_summary = {
        "total": total,
        "stale": len(stale_ids),
        "superseded": len(superseded_ids),
        "trust_counts": trust_counts,
        "overall_trust": overall_trust,
    }

    # Strip internal dt field before returning
    clean_matched = [{k: v for k, v in m.items() if k != "_created_at_dt"} for m in matched]

    approval_semantics = {
        "read_only": True,
        "no_write": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Scoped memory read only. Memory is provided as context, not as authoritative truth. "
            "stale/superseded memory is explicitly flagged. No write. No Human-GO."
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "mode": request.mode,
            "scope": request.scope,
            "topic": request.topic,
            "artifact": request.artifact,
            "decision": request.decision,
            "agent": request.agent,
            "freshness_days": request.freshness_days,
            "memory_type": request.memory_type,
            "limit": request.limit,
        },
        "mode": request.mode,
        "matched_memory": clean_matched,
        "stale_memory_ids": stale_ids,
        "superseded_memory_ids": superseded_ids,
        "trust_counts": trust_counts,
        "memory_summary": memory_summary,
        "warnings": sorted(set(warnings)),
        "approval_semantics": approval_semantics,
    }
