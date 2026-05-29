"""Claim evidence at rest — DB-layer enforcement v1 (#2719).

Fail-closed validation that ``claim`` rows reference persisted ``evidence_ref``
records. Caller-supplied metadata cannot substitute for at-rest evidence.

No productive writes. No MCP mutation. LR: NO-GO.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Protocol

from tools.mcp.surrealdb_adapter_factory import adapter_source
from tools.surrealdb.claim_resolver import (
    ClaimResolveRequest,
    ClaimResolverError,
    resolve_claims_v1,
)

SCHEMA_VERSION = "claim-evidence-at-rest/v1"

CLAIM_STATUSES = frozenset(
    {
        "proposed",
        "supported",
        "weakly_supported",
        "disputed",
        "superseded",
        "stale",
        "invalidated",
    }
)

_STATUSES_REQUIRING_EVIDENCE = frozenset({"supported", "weakly_supported"})

_SURQL_SAFE_RE = re.compile(r"^[a-zA-Z0-9/_.@:#+ \-]+$")

_DB_STRIP_FIELDS = frozenset(
    {
        "run_id",
        "schema_version",
        "id",
        "sensitivity",
    }
)

_CALLER_EVIDENCE_METADATA_KEYS = frozenset(
    {
        "brain_source",
        "metadata_source",
        "adapter_status",
        "evidence_id",
        "evidence_ref",
        "source",
    }
)

_SECRET_SUBSTRINGS = frozenset(
    {
        "SURREAL_PASS",
        "SURREAL_USER",
        "Authorization",
        "Basic ",
    }
)


class ClaimEvidenceAtRestError(ValueError):
    """Raised when a claim fails at-rest evidence enforcement."""


class ClaimEvidenceProofAdapter(Protocol):
    """Minimal adapter surface for claim/evidence SELECT proof."""

    status: str

    def execute(self, query: str) -> list[dict[str, Any]]: ...


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return str(value).strip() or None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_surql_str(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    return text if (text and _SURQL_SAFE_RE.match(text)) else None


def _strip_db_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in dict(row).items() if key not in _DB_STRIP_FIELDS
    }


def reject_caller_metadata_as_evidence(
    metadata: Mapping[str, Any] | None,
    *,
    known_evidence_ids: set[str] | frozenset[str],
) -> None:
    """Block treating caller metadata as persisted evidence without a DB row."""
    if metadata is None:
        return
    if not isinstance(metadata, Mapping):
        raise ClaimEvidenceAtRestError("metadata must be a mapping when provided")

    known = {
        item.strip()
        for item in known_evidence_ids
        if isinstance(item, str) and item.strip()
    }

    for key in _CALLER_EVIDENCE_METADATA_KEYS:
        if key not in metadata:
            continue
        raw = metadata.get(key)
        if raw is None:
            continue
        if key in {"evidence_id", "evidence_ref"}:
            ref = _as_str(raw)
            if ref and ref not in known:
                raise ClaimEvidenceAtRestError(
                    "caller-supplied evidence id is not backed by a "
                    "persisted evidence_ref row"
                )
            continue
        if key in {"brain_source", "metadata_source", "adapter_status", "source"}:
            if not known:
                raise ClaimEvidenceAtRestError(
                    "caller metadata cannot substitute for at-rest evidence "
                    "without known_evidence_ids"
                )
            if key == "source" and _as_str(raw) in {
                "surrealdb-local",
                "db",
                "persisted",
            }:
                raise ClaimEvidenceAtRestError(
                    "caller metadata.source cannot assert DB-backed evidence "
                    "without resolver proof"
                )


def validate_claim_record_structure(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate claim row structure; hard-fail (not warning-only)."""
    claim_id = _as_str(raw.get("claim_id"))
    if not claim_id:
        raise ClaimEvidenceAtRestError("claim record missing claim_id")

    scope = _as_str(raw.get("scope"))
    if not scope:
        raise ClaimEvidenceAtRestError(f"claim {claim_id}: scope is required")

    status = (_as_str(raw.get("status")) or "proposed").lower()
    if status not in CLAIM_STATUSES:
        raise ClaimEvidenceAtRestError(f"claim {claim_id}: unknown status {status!r}")

    evidence_refs = [
        str(x).strip() for x in _as_list(raw.get("evidence_refs")) if _as_str(x)
    ]
    if status in _STATUSES_REQUIRING_EVIDENCE and not evidence_refs:
        raise ClaimEvidenceAtRestError(
            f"claim {claim_id}: evidence_refs required for status {status}"
        )

    for ref in evidence_refs:
        if not ref:
            raise ClaimEvidenceAtRestError(
                f"claim {claim_id}: empty evidence_refs entry"
            )

    return {
        "claim_id": claim_id,
        "scope": scope,
        "status": status,
        "evidence_refs": sorted(set(evidence_refs)),
        "title": _as_str(raw.get("title")) or "",
        "statement": _as_str(raw.get("statement")) or "",
    }


def index_evidence_records(
    evidence_records: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw in evidence_records:
        if not isinstance(raw, Mapping):
            continue
        row = _strip_db_metadata(raw)
        evidence_id = _as_str(row.get("evidence_id"))
        if not evidence_id:
            continue
        evidence_type = _as_str(row.get("evidence_type"))
        if not evidence_type:
            raise ClaimEvidenceAtRestError(
                f"evidence_ref {evidence_id}: evidence_type is required at rest"
            )
        index[evidence_id] = row
    return index


def validate_evidence_refs_resolve(
    claim: Mapping[str, Any],
    evidence_index: Mapping[str, Mapping[str, Any]],
    *,
    require_scope_match: bool = True,
) -> list[str]:
    """Validate each evidence_ref resolves in *evidence_index*. Returns resolved ids."""
    claim_id = _as_str(claim.get("claim_id")) or "<unknown>"
    claim_scope = _as_str(claim.get("scope")) or ""
    resolved: list[str] = []

    for ref in _as_list(claim.get("evidence_refs")):
        evidence_id = _as_str(ref)
        if not evidence_id:
            raise ClaimEvidenceAtRestError(
                f"claim {claim_id}: empty evidence_ref entry"
            )
        row = evidence_index.get(evidence_id)
        if row is None:
            raise ClaimEvidenceAtRestError(
                f"claim {claim_id}: evidence_ref {evidence_id!r} not found at rest"
            )
        row_scope = _as_str(row.get("scope"))
        if require_scope_match and row_scope and row_scope != claim_scope:
            raise ClaimEvidenceAtRestError(
                f"claim {claim_id}: evidence_ref {evidence_id!r} scope mismatch"
            )
        evidence_type = _as_str(row.get("evidence_type"))
        if not evidence_type:
            raise ClaimEvidenceAtRestError(
                f"claim {claim_id}: evidence_ref {evidence_id!r} missing evidence_type"
            )
        resolved.append(evidence_id)
    return resolved


def enforce_claim_records_at_rest(
    claim_records: Iterable[Mapping[str, Any]],
    evidence_records: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate in-memory claim rows against an evidence index (unit/local use)."""
    evidence_index = index_evidence_records(evidence_records)
    known_ids = frozenset(evidence_index.keys())
    reject_caller_metadata_as_evidence(metadata, known_evidence_ids=known_ids)

    valid_claims: list[dict[str, Any]] = []
    for raw in claim_records:
        if not isinstance(raw, Mapping):
            continue
        claim = validate_claim_record_structure(raw)
        validate_evidence_refs_resolve(
            claim,
            evidence_index,
            require_scope_match=False,
        )
        valid_claims.append(claim)

    if not valid_claims:
        raise ClaimEvidenceAtRestError("no valid claims after at-rest enforcement")

    resolver = resolve_claims_v1(
        valid_claims,
        ClaimResolveRequest(mode="by_scope", scope=valid_claims[0]["scope"]),
        known_evidence_ids=set(known_ids),
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "valid_claim_count": len(valid_claims),
        "known_evidence_ids": sorted(known_ids),
        "claim_resolution": resolver,
        "approval_semantics": _approval_semantics(),
        "limitations": _limitations(),
    }


def prove_claim_evidence_at_rest_db_v1(
    adapter: ClaimEvidenceProofAdapter,
    *,
    scope: str,
    limit: int = 200,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """SELECT claims + evidence_ref rows from DB and enforce at-rest linkage."""
    safe_scope = _safe_surql_str(scope)
    if not safe_scope:
        raise ClaimEvidenceAtRestError(f"scope is not safe for SurrealQL: {scope!r}")
    if limit < 1 or limit > 10_000:
        raise ClaimEvidenceAtRestError("limit must be within 1..10000")

    source = adapter_source(adapter)
    claim_query = f"SELECT * FROM claim WHERE scope = '{safe_scope}' LIMIT {limit}"
    evidence_query = f"SELECT * FROM evidence_ref LIMIT {limit * 4}"

    raw_claim_rows = adapter.execute(claim_query)
    raw_evidence_rows = adapter.execute(evidence_query)

    evidence_index = index_evidence_records(
        _strip_db_metadata(row) for row in raw_evidence_rows if isinstance(row, Mapping)
    )
    known_ids = frozenset(evidence_index.keys())
    reject_caller_metadata_as_evidence(metadata, known_evidence_ids=known_ids)

    valid_claims: list[dict[str, Any]] = []
    blocked: list[dict[str, str]] = []

    for raw_row in raw_claim_rows:
        if not isinstance(raw_row, Mapping):
            continue
        stripped = _strip_db_metadata(raw_row)
        claim_id = _as_str(stripped.get("claim_id")) or "<unknown>"
        try:
            claim = validate_claim_record_structure(stripped)
            validate_evidence_refs_resolve(
                claim,
                evidence_index,
                require_scope_match=False,
            )
            valid_claims.append(claim)
        except ClaimEvidenceAtRestError as exc:
            blocked.append(
                {
                    "claim_id": claim_id,
                    "reason_code": "claim_evidence_at_rest_violation",
                    "message": str(exc),
                }
            )

    if blocked:
        raise ClaimEvidenceAtRestError(
            f"claim evidence at rest proof failed: {len(blocked)} blocked row(s)"
        )

    if not valid_claims:
        raise ClaimEvidenceAtRestError("no claims found for scope at rest proof")

    try:
        resolver = resolve_claims_v1(
            valid_claims,
            ClaimResolveRequest(mode="by_scope", scope=safe_scope, limit=limit),
            known_evidence_ids=set(known_ids),
        )
    except ClaimResolverError as exc:
        raise ClaimEvidenceAtRestError(f"claim resolver failed: {exc}") from exc

    if resolver.get("unresolved_evidence_refs"):
        raise ClaimEvidenceAtRestError(
            "unresolved evidence_refs after at-rest enforcement: "
            + ", ".join(resolver["unresolved_evidence_refs"])
        )

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "adapter_status": adapter.status,
        "scope": safe_scope,
        "claim_count": len(valid_claims),
        "claim_ids": [c["claim_id"] for c in valid_claims],
        "known_evidence_ids": sorted(known_ids),
        "claim_resolution": resolver,
        "blocked_claims": blocked,
        "limitations": _limitations(),
        "approval_semantics": _approval_semantics(),
    }
    _assert_no_secrets(envelope)
    return envelope


def _limitations() -> list[str]:
    return [
        "read_only_proof_no_writes",
        "python_contract_enforcement_v1_no_live_db_assert",
        "caller_metadata_cannot_substitute_for_persisted_evidence_ref",
        "lr_no_go",
    ]


def _approval_semantics() -> dict[str, Any]:
    return {
        "read_only": True,
        "no_write": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Claim evidence at rest proof only. Claims without persisted "
            "evidence_refs are blocked. This does not grant Human-GO or "
            "productive memory write."
        ),
    }


def _assert_no_secrets(payload: Mapping[str, Any]) -> None:
    rendered = str(payload)
    for needle in _SECRET_SUBSTRINGS:
        if needle in rendered:
            raise ClaimEvidenceAtRestError(
                "envelope contains forbidden secret-like substring"
            )
