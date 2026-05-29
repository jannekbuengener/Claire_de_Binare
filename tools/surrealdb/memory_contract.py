"""Deterministic memory_id generation and fail-closed record validation.

Issues:
    #2606 — [EPIC][AGENT-MEMORY] Langzeitgedaechtnis / Persistent Agent Memory
    Slice: Memory Reality Slice 2 — deterministic memory_id + contracts

Scope:
    Generates a stable UUIDv5 memory_id from canonical identity fields.
    Validates agent_memory records against the v1 field contract.
    No DB access. No MCP changes. No writes. No side effects.

Guardrails:
    - Read/compute-only. No memory write, no mutation.
    - LR remains NO-GO. Board stage 'trade-capable' is not live-go.
    - Deterministic: same inputs always produce the same memory_id.
    - Fail-closed: invalid records raise MemoryContractError.

Relations:
    role: memory_id_generator_and_validator
    domain: agent_memory
    upstream:
        - core/replay/canonical_json.py  (canonical_hash for source_refs fingerprint)
    downstream:
        - Slice 3 DB read proof
        - Slice 4 Human-GO write gate
    see_also:
        - docs/surrealdb/memory-reality-slice1-audit.md  (R5 finalized here)
        - docs/surrealdb/scoped-agent-memory-model-v1.md
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from core.replay.canonical_json import canonical_hash

SCHEMA_VERSION = "memory-contract/v1"

CANONICAL_MEMORY_TYPES: frozenset[str] = frozenset(
    {
        "working_memory",
        "semantic_memory",
        "episodic_memory",
        "procedural_memory",
        "preference_memory",
        "risk_memory",
    }
)

# UUIDv5 namespace dedicated exclusively to memory_id generation.
# Must never be reused for other ID domains (decision_pk, event_pk, etc.).
MEMORY_ID_NAMESPACE = uuid.UUID("b4e1d2c3-a5f6-4780-9bcd-ef0123456789")

# All valid top-level fields in a v1 memory record.
_KNOWN_FIELDS: frozenset[str] = frozenset(
    {
        "memory_id",
        "scope",
        "namespace",
        "memory_type",
        "content",
        "source_refs",
        "evidence_refs",
        "confidence",
        "ttl",
        "expires_at",
        "created_by",
        "created_at",
        "superseded_by",
        "stale_after",
        "comment",
    }
)

_REQUIRED_FIELDS: tuple[str, ...] = (
    "scope",
    "namespace",
    "memory_type",
    "content",
    "source_refs",
    "evidence_refs",
    "confidence",
    "ttl",
    "created_by",
    "created_at",
)


class MemoryContractError(ValueError):
    """Raised when a memory record or memory_id contract is violated."""


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hex digest of stripped UTF-8 content.

    Args:
        content: Raw memory content string.

    Returns:
        64-character lowercase hex SHA256 digest.
    """
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def compute_source_refs_fingerprint(source_refs: list[str]) -> str:
    """Compute canonical hash of sorted unique source reference strings.

    Uses canonical_hash (sorted-key JSON + SHA256) from core.replay.canonical_json
    so the fingerprint is stable regardless of list ordering or duplicates.

    Args:
        source_refs: List of source reference strings.

    Returns:
        64-character lowercase hex SHA256 digest.
    """
    return canonical_hash(sorted(set(source_refs)))


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def generate_memory_id(
    scope: str,
    namespace: str,
    memory_type: str,
    created_by: str,
    content: str,
    source_refs: list[str],
) -> str:
    """Generate a deterministic UUIDv5 memory_id.

    Name string (pipe-delimited):
        ``{scope}|{namespace}|{memory_type}|{created_by}|{content_hash}|{source_refs_fingerprint}``

    Fields deliberately NOT in the ID: created_at, ttl, confidence,
    evidence_refs.  These are mutable metadata; the ID must be stable
    across updates to those fields.

    Args:
        scope: Memory scope identifier (required, non-empty).
        namespace: Memory namespace (required, non-empty).
        memory_type: Must be a member of CANONICAL_MEMORY_TYPES; lowercased.
        created_by: Identity string of the creating agent (required, non-empty).
        content: Memory content string.
        source_refs: Source reference strings list.

    Returns:
        UUIDv5 string (36 characters, lowercase hyphenated).

    Raises:
        MemoryContractError: If any required input is invalid or memory_type
            is not in CANONICAL_MEMORY_TYPES.
    """
    if not isinstance(scope, str) or not scope.strip():
        raise MemoryContractError("scope is required for memory_id generation")
    if not isinstance(namespace, str) or not namespace.strip():
        raise MemoryContractError("namespace is required for memory_id generation")
    if not isinstance(created_by, str) or not created_by.strip():
        raise MemoryContractError("created_by is required for memory_id generation")

    mt = memory_type.lower() if isinstance(memory_type, str) else ""
    if mt not in CANONICAL_MEMORY_TYPES:
        raise MemoryContractError(
            f"unknown memory_type {memory_type!r}; must be one of {sorted(CANONICAL_MEMORY_TYPES)}"
        )

    content_hash = compute_content_hash(content)
    source_refs_fingerprint = compute_source_refs_fingerprint(source_refs)

    name = (
        f"{scope.strip()}|{namespace.strip()}|{mt}|{created_by.strip()}"
        f"|{content_hash}|{source_refs_fingerprint}"
    )
    return str(uuid.uuid5(MEMORY_ID_NAMESPACE, name))


# ---------------------------------------------------------------------------
# Validation internals
# ---------------------------------------------------------------------------


def _parse_datetime_strict(value: Any, field: str) -> datetime:
    """Parse an ISO 8601 datetime; fail-closed on any error."""
    if isinstance(value, datetime):
        return (
            value.astimezone(timezone.utc)
            if value.tzinfo
            else value.replace(tzinfo=timezone.utc)
        )
    if not isinstance(value, str) or not value.strip():
        raise MemoryContractError(f"{field} must be a non-empty ISO datetime string")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MemoryContractError(
            f"{field} is not a valid ISO datetime: {value!r}"
        ) from exc
    return (
        parsed.astimezone(timezone.utc)
        if parsed.tzinfo
        else parsed.replace(tzinfo=timezone.utc)
    )


# ---------------------------------------------------------------------------
# Public validation API
# ---------------------------------------------------------------------------


def validate_memory_record(raw: Any, *, strict: bool = True) -> dict[str, Any]:
    """Validate a raw agent_memory record against the v1 contract.

    Fail-closed: raises MemoryContractError for any violation.

    Contract rules:
    - Required: scope, namespace, memory_type, content, source_refs,
      evidence_refs, confidence, ttl, created_by, created_at.
    - memory_type must be in CANONICAL_MEMORY_TYPES.
    - source_refs: non-empty list of non-empty strings.
    - evidence_refs: non-empty list of non-empty strings.
    - confidence: numeric value in [0.0, 1.0].
    - ttl: integer >= 0 (seconds).
    - If ttl > 0: expires_at required, and must be strictly after created_at.
    - Optional superseded_by: non-empty string if present.
    - Optional stale_after: integer >= 0 if present.
    - Optional comment: any string.
    - If memory_id is present: must equal the computed UUIDv5.
    - If memory_id is absent: validator computes and attaches it.
    - strict=True: rejects any fields not in _KNOWN_FIELDS.

    Canon field names (not aliases):
    - created_by (NOT agent_id)
    - source_refs (NOT source_ref)
    - superseded_by (NOT supersedes)

    Args:
        raw: Dict representing a raw memory record.
        strict: If True (default), reject records with unknown fields.

    Returns:
        Validated and normalized record dict with memory_id set and
        memory_type lowercased.

    Raises:
        MemoryContractError: On any contract violation.
    """
    if not isinstance(raw, dict):
        raise MemoryContractError("memory record must be a dict")

    if strict:
        unknown = set(raw.keys()) - _KNOWN_FIELDS
        if unknown:
            raise MemoryContractError(
                f"unknown fields in memory record (strict=True): {sorted(unknown)}"
            )

    # Required field presence
    for field in _REQUIRED_FIELDS:
        if field not in raw:
            raise MemoryContractError(f"missing required field: {field!r}")

    # scope
    scope = raw["scope"]
    if not isinstance(scope, str) or not scope.strip():
        raise MemoryContractError("scope must be a non-empty string")

    # namespace
    namespace = raw["namespace"]
    if not isinstance(namespace, str) or not namespace.strip():
        raise MemoryContractError("namespace must be a non-empty string")

    # memory_type
    memory_type = raw["memory_type"]
    if not isinstance(memory_type, str):
        raise MemoryContractError("memory_type must be a string")
    mt = memory_type.lower()
    if mt not in CANONICAL_MEMORY_TYPES:
        raise MemoryContractError(
            f"unknown memory_type {memory_type!r}; must be one of {sorted(CANONICAL_MEMORY_TYPES)}"
        )

    # content
    content = raw["content"]
    if not isinstance(content, str) or not content.strip():
        raise MemoryContractError("content must be a non-empty string")

    # source_refs
    source_refs = raw["source_refs"]
    if not isinstance(source_refs, list) or not source_refs:
        raise MemoryContractError("source_refs must be a non-empty list")
    if not all(isinstance(r, str) and r.strip() for r in source_refs):
        raise MemoryContractError("source_refs must be a list of non-empty strings")

    # evidence_refs
    evidence_refs = raw["evidence_refs"]
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise MemoryContractError("evidence_refs must be a non-empty list")
    if not all(isinstance(r, str) and r.strip() for r in evidence_refs):
        raise MemoryContractError("evidence_refs must be a list of non-empty strings")

    # confidence
    confidence = raw["confidence"]
    try:
        confidence_f = float(confidence)
    except (TypeError, ValueError) as exc:
        raise MemoryContractError(
            f"confidence must be a float in [0.0, 1.0]; got {confidence!r}"
        ) from exc
    if not (0.0 <= confidence_f <= 1.0):
        raise MemoryContractError(
            f"confidence must be in [0.0, 1.0]; got {confidence_f}"
        )

    # ttl
    ttl = raw["ttl"]
    try:
        ttl_int = int(ttl)
    except (TypeError, ValueError) as exc:
        raise MemoryContractError(
            f"ttl must be an integer >= 0 (seconds); got {ttl!r}"
        ) from exc
    if ttl_int < 0:
        raise MemoryContractError(f"ttl must be >= 0; got {ttl_int}")

    # created_by
    created_by = raw["created_by"]
    if not isinstance(created_by, str) or not created_by.strip():
        raise MemoryContractError("created_by must be a non-empty string")

    # created_at
    created_at_dt = _parse_datetime_strict(raw["created_at"], "created_at")

    # expires_at: required when ttl > 0
    if ttl_int > 0:
        if "expires_at" not in raw:
            raise MemoryContractError("expires_at is required when ttl > 0")
        expires_at_dt = _parse_datetime_strict(raw["expires_at"], "expires_at")
        if expires_at_dt <= created_at_dt:
            raise MemoryContractError(
                f"expires_at must be strictly after created_at; "
                f"got expires_at={raw['expires_at']!r}, created_at={raw['created_at']!r}"
            )

    # superseded_by (optional, non-empty if present)
    if "superseded_by" in raw:
        sv = raw["superseded_by"]
        if not isinstance(sv, str) or not sv.strip():
            raise MemoryContractError(
                "superseded_by must be a non-empty string if present"
            )

    # stale_after (optional, int >= 0)
    if "stale_after" in raw:
        sa = raw["stale_after"]
        try:
            sa_int = int(sa)
        except (TypeError, ValueError) as exc:
            raise MemoryContractError(
                f"stale_after must be an integer >= 0; got {sa!r}"
            ) from exc
        if sa_int < 0:
            raise MemoryContractError(f"stale_after must be >= 0; got {sa_int}")

    # Compute canonical memory_id
    computed_id = generate_memory_id(
        scope=scope.strip(),
        namespace=namespace.strip(),
        memory_type=mt,
        created_by=created_by.strip(),
        content=content,
        source_refs=source_refs,
    )

    # memory_id check: if present must match; if absent attach computed value
    if "memory_id" in raw:
        existing_id = raw["memory_id"]
        if existing_id != computed_id:
            raise MemoryContractError(
                f"memory_id mismatch: record has {existing_id!r}, "
                f"computed {computed_id!r}"
            )

    # Build normalized output (shallow copy, override computed fields)
    record: dict[str, Any] = dict(raw)
    record["memory_type"] = mt  # lowercased canonical form
    record["memory_id"] = computed_id  # attach (or confirm)

    return record


def validate_memory_id_matches_record(record: dict[str, Any]) -> None:
    """Verify that record['memory_id'] matches the value computed from the record.

    Args:
        record: Memory record dict. Must have memory_id and all fields
            required for ID computation (scope, namespace, memory_type,
            created_by, content, source_refs).

    Raises:
        MemoryContractError: If memory_id is absent or does not match the
            computed UUIDv5.
    """
    if "memory_id" not in record:
        raise MemoryContractError("record is missing memory_id field")

    _required_for_id = (
        "scope",
        "namespace",
        "memory_type",
        "created_by",
        "content",
        "source_refs",
    )
    for field in _required_for_id:
        if field not in record:
            raise MemoryContractError(
                f"record is missing field required for ID computation: {field!r}"
            )

    computed = generate_memory_id(
        scope=str(record["scope"]).strip(),
        namespace=str(record["namespace"]).strip(),
        memory_type=str(record["memory_type"]).lower(),
        created_by=str(record["created_by"]).strip(),
        content=record["content"],
        source_refs=record["source_refs"],
    )

    if record["memory_id"] != computed:
        raise MemoryContractError(
            f"memory_id mismatch: record has {record['memory_id']!r}, "
            f"computed {computed!r}"
        )
