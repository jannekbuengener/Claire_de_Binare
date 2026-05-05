"""Claim Resolution v1 — side-effect-free domain component.

Issues:
    #2117 — [SURREALDB][CONTEXT][CLAIMS] Implement claim resolution v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Scope:
    Implements a minimal, deterministic claim-resolution slice that works
    purely on in-memory claim records. No DB access. No SurrealDB SDK.
    No MCP. No networking. No writes.

Guardrails:
    - Retrieval/explanation only: never implies approval, live-go, or authority.
    - Claims without evidence are never presented as hard truth.
    - disputed/stale/invalidated claims are explicitly surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "claim-resolver/v1"

SUPPORTED_MODES = frozenset(
    {
        "by_claim_id",
        "by_topic",
        "by_scope",
        "by_status",
        "by_artifact",
        "by_evidence_ref",
        "by_decision_ref",
    }
)

# Claim status values
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

# Statuses that indicate a claim needs human attention
_ATTENTION_STATUSES = frozenset({"disputed", "stale", "invalidated"})
# Statuses that indicate a claim is weak
_WEAK_STATUSES = frozenset({"proposed", "weakly_supported"})


class ClaimResolverError(ValueError):
    """Raised when claim resolution inputs are invalid or unsafe."""


@dataclass(frozen=True)
class ClaimResolveRequest:
    """Query request for claim resolution v1."""

    mode: str
    claim_id: str | None = None
    topic: str | None = None
    scope: str | None = None
    status: str | None = None
    artifact: str | None = None
    evidence_ref: str | None = None
    decision_ref: str | None = None
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


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_claim(raw: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = _as_str(raw.get("claim_id"))
    if not claim_id:
        raise ClaimResolverError("claim record missing claim_id")

    created_at = _parse_datetime(raw.get("created_at"))
    status = _as_str(raw.get("status")) or "proposed"
    scope = _as_str(raw.get("scope")) or ""

    topics: list[str] = []
    if _as_str(raw.get("topic")):
        topics.append(str(raw["topic"]).strip())
    topics.extend([str(x) for x in _as_list(raw.get("topics")) if _as_str(x)])

    evidence_refs = [str(x) for x in _as_list(raw.get("evidence_refs")) if _as_str(x)]
    decision_refs = [str(x) for x in _as_list(raw.get("decision_refs")) if _as_str(x)]
    artifact_refs = [str(x) for x in _as_list(raw.get("artifact_refs")) if _as_str(x)]

    superseded_by = _as_str(raw.get("superseded_by"))
    invalidated_by = _as_str(raw.get("invalidated_by"))
    confidence = _as_float(raw.get("confidence"))
    uncertainty = _as_str(raw.get("uncertainty"))

    no_evidence = len(evidence_refs) == 0
    missing_evidence_blocker = bool(raw.get("missing_evidence_blocker", False)) or (
        status in ("supported", "weakly_supported") and no_evidence
    )

    return {
        "claim_id": claim_id,
        "title": _as_str(raw.get("title")) or "",
        "statement": _as_str(raw.get("statement")) or "",
        "status": status,
        "scope": scope,
        "topics": sorted(set(t for t in topics if t)),
        "evidence_refs": sorted(set(evidence_refs)),
        "decision_refs": sorted(set(decision_refs)),
        "artifact_refs": sorted(set(artifact_refs)),
        "confidence": confidence,
        "uncertainty": uncertainty,
        "superseded_by": superseded_by,
        "invalidated_by": invalidated_by,
        "missing_evidence_blocker": missing_evidence_blocker,
        "created_at": created_at.isoformat() if created_at else None,
        "_created_at_dt": created_at,
    }


def _claim_sort_key(claim: Mapping[str, Any]) -> tuple[int, str, str]:
    dt: datetime | None = claim.get("_created_at_dt")
    if dt is None:
        return (1, "", str(claim.get("claim_id", "")))
    return (0, dt.isoformat(), str(claim.get("claim_id", "")))


def _validate_request(req: ClaimResolveRequest) -> None:
    if req.mode not in SUPPORTED_MODES:
        raise ClaimResolverError(f"unsupported mode: {req.mode}")
    if req.limit < 1 or req.limit > 10_000:
        raise ClaimResolverError("limit must be within 1..10000")

    required: dict[str, str] = {
        "by_claim_id": "claim_id",
        "by_topic": "topic",
        "by_scope": "scope",
        "by_status": "status",
        "by_artifact": "artifact",
        "by_evidence_ref": "evidence_ref",
        "by_decision_ref": "decision_ref",
    }
    required_field = required.get(req.mode)
    if required_field and not _as_str(getattr(req, required_field)):
        raise ClaimResolverError(f"{req.mode} requires {required_field}")

    if req.mode == "by_status" and req.status and req.status.strip() not in CLAIM_STATUSES:
        raise ClaimResolverError(f"unknown claim status: {req.status!r}")


def _match(claim: Mapping[str, Any], req: ClaimResolveRequest) -> bool:
    if req.mode == "by_claim_id":
        return claim.get("claim_id") == req.claim_id
    if req.mode == "by_topic":
        topic = (req.topic or "").strip()
        return topic in set(claim.get("topics", []))
    if req.mode == "by_scope":
        scope = (req.scope or "").strip()
        return scope in str(claim.get("scope", ""))
    if req.mode == "by_status":
        return str(claim.get("status", "")).strip().lower() == (req.status or "").strip().lower()
    if req.mode == "by_artifact":
        return (req.artifact or "").strip() in set(claim.get("artifact_refs", []))
    if req.mode == "by_evidence_ref":
        return (req.evidence_ref or "").strip() in set(claim.get("evidence_refs", []))
    if req.mode == "by_decision_ref":
        return (req.decision_ref or "").strip() in set(claim.get("decision_refs", []))
    return False


def resolve_claims_v1(
    claim_records: Iterable[Mapping[str, Any]],
    request: ClaimResolveRequest,
    *,
    known_evidence_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Resolve claims over in-memory claim records.

    Deterministic and side-effect-free.
    """
    _validate_request(request)

    warnings: list[str] = []

    normalized: list[dict[str, Any]] = []
    for raw in claim_records:
        if not isinstance(raw, Mapping):
            continue
        normalized.append(_normalize_claim(raw))

    normalized_sorted = sorted(normalized, key=_claim_sort_key)
    matched = [c for c in normalized_sorted if _match(c, request)]

    if not matched:
        warnings.append("no_claims_matched")

    matched = matched[: request.limit]

    # Status buckets
    disputed = [c["claim_id"] for c in matched if c.get("status") == "disputed"]
    stale = [c["claim_id"] for c in matched if c.get("status") == "stale"]
    invalidated = [c["claim_id"] for c in matched if c.get("status") == "invalidated"]
    missing_evidence = [c["claim_id"] for c in matched if c.get("missing_evidence_blocker")]

    if disputed:
        warnings.append("disputed_claims_present")
    if stale:
        warnings.append("stale_claims_present")
    if invalidated:
        warnings.append("invalidated_claims_present")
    if missing_evidence:
        warnings.append("missing_evidence_on_claims")

    # Resolve unresolved evidence refs
    all_evidence_refs = sorted({e for c in matched for e in c.get("evidence_refs", [])})
    unresolved_evidence_refs: list[str] = []
    if known_evidence_ids is not None:
        unresolved_evidence_refs = sorted([e for e in all_evidence_refs if e not in known_evidence_ids])
        if unresolved_evidence_refs:
            warnings.append("unresolved_evidence_refs_present")

    # Confidence summary
    confidences = [c["confidence"] for c in matched if c.get("confidence") is not None]
    confidence_summary: dict[str, Any] = {}
    if confidences:
        confidence_summary = {
            "min": min(confidences),
            "max": max(confidences),
            "avg": round(sum(confidences) / len(confidences), 4),
            "count": len(confidences),
        }

    # Status counts
    status_counts: dict[str, int] = {}
    for c in matched:
        s = str(c.get("status", "unknown"))
        status_counts[s] = status_counts.get(s, 0) + 1

    # Strip internal dt field before returning
    clean_matched = [{k: v for k, v in c.items() if k != "_created_at_dt"} for c in matched]

    approval_semantics = {
        "resolution_only": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Claim resolution only. Claims without evidence are not presented as hard truth. "
            "This output does not grant approval and must not be interpreted as Human-GO."
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "mode": request.mode,
            "claim_id": request.claim_id,
            "topic": request.topic,
            "scope": request.scope,
            "status": request.status,
            "artifact": request.artifact,
            "evidence_ref": request.evidence_ref,
            "decision_ref": request.decision_ref,
            "limit": request.limit,
        },
        "mode": request.mode,
        "matched_claims": clean_matched,
        "disputed_claim_ids": disputed,
        "stale_claim_ids": stale,
        "invalidated_claim_ids": invalidated,
        "missing_evidence_claim_ids": missing_evidence,
        "all_evidence_refs": all_evidence_refs,
        "unresolved_evidence_refs": unresolved_evidence_refs,
        "confidence_summary": confidence_summary,
        "status_counts": status_counts,
        "warnings": sorted(set(warnings)),
        "approval_semantics": approval_semantics,
    }
