"""Evidence Lookup v1 — side-effect-free domain component.

Issues:
    #2116 — [SURREALDB][CONTEXT][EVIDENCE] Implement evidence lookup v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Scope:
    Implements a minimal, deterministic evidence-lookup slice that works
    purely on in-memory evidence records. No DB access. No SurrealDB SDK.
    No MCP. No networking. No writes.

Guardrails:
    - Retrieval/explanation only: never implies approval, live-go, or authority.
    - Evidence Strength is computed but does not grant any decision authority.
    - No write, no mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "evidence-lookup/v1"

SUPPORTED_MODES = frozenset(
    {
        "by_artifact",
        "by_claim",
        "by_decision",
        "by_source_path",
        "by_run_id",
        "by_evidence_type",
        "by_freshness",
        "by_confidence",
    }
)

# Evidence strength levels (ascending)
EVIDENCE_STRENGTH_LEVELS = ("none", "weak", "moderate", "strong", "blocking_missing")


class EvidenceLookupError(ValueError):
    """Raised when evidence lookup inputs are invalid or unsafe."""


@dataclass(frozen=True)
class EvidenceLookupRequest:
    """Query request for evidence lookup v1."""

    mode: str
    artifact: str | None = None
    claim: str | None = None
    decision: str | None = None
    source_path: str | None = None
    run_id: str | None = None
    evidence_type: str | None = None
    freshness_days: int | None = None
    min_confidence: float | None = None
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


def _compute_strength(evidence: Mapping[str, Any]) -> str:
    """Classify evidence strength from record fields."""
    confidence = _as_float(evidence.get("confidence"))
    ev_type = _as_str(evidence.get("evidence_type")) or ""
    missing = bool(evidence.get("blocking_missing", False))
    stale = bool(evidence.get("stale", False))
    source_refs = _as_list(evidence.get("source_refs"))

    if missing:
        return "blocking_missing"
    if stale or ev_type.lower() in {"assumed", "placeholder"}:
        return "weak"
    if confidence is None:
        # Presence of source_refs upgrades to moderate
        return "moderate" if source_refs else "weak"
    if confidence >= 0.85:
        return "strong"
    if confidence >= 0.5:
        return "moderate"
    return "weak"


def _normalize_evidence(raw: Mapping[str, Any]) -> dict[str, Any]:
    evidence_id = _as_str(raw.get("evidence_id"))
    if not evidence_id:
        raise EvidenceLookupError("evidence record missing evidence_id")

    created_at = _parse_datetime(raw.get("created_at"))
    evidence_type = _as_str(raw.get("evidence_type")) or "unknown"
    confidence = _as_float(raw.get("confidence"))
    stale = bool(raw.get("stale", False))
    blocking_missing = bool(raw.get("blocking_missing", False))

    artifact_refs = [str(x) for x in _as_list(raw.get("artifact_refs")) if _as_str(x)]
    claim_refs = [str(x) for x in _as_list(raw.get("claim_refs")) if _as_str(x)]
    decision_refs = [str(x) for x in _as_list(raw.get("decision_refs")) if _as_str(x)]
    source_refs = [str(x) for x in _as_list(raw.get("source_refs")) if _as_str(x)]
    source_hashes = {k: str(v) for k, v in dict(raw.get("source_hashes") or {}).items()}
    run_id = _as_str(raw.get("run_id"))
    scope = _as_str(raw.get("scope")) or ""

    entry: dict[str, Any] = {
        "evidence_id": evidence_id,
        "title": _as_str(raw.get("title")) or "",
        "description": _as_str(raw.get("description")) or "",
        "evidence_type": evidence_type,
        "confidence": confidence,
        "stale": stale,
        "blocking_missing": blocking_missing,
        "scope": scope,
        "artifact_refs": sorted(set(artifact_refs)),
        "claim_refs": sorted(set(claim_refs)),
        "decision_refs": sorted(set(decision_refs)),
        "source_refs": sorted(set(source_refs)),
        "source_hashes": source_hashes,
        "run_id": run_id,
        "created_at": created_at.isoformat() if created_at else None,
        "_created_at_dt": created_at,
    }
    entry["strength"] = _compute_strength(entry)
    return entry


def _evidence_sort_key(ev: Mapping[str, Any]) -> tuple[int, str, str]:
    dt: datetime | None = ev.get("_created_at_dt")
    if dt is None:
        return (1, "", str(ev.get("evidence_id", "")))
    return (0, dt.isoformat(), str(ev.get("evidence_id", "")))


def _validate_request(req: EvidenceLookupRequest) -> None:
    if req.mode not in SUPPORTED_MODES:
        raise EvidenceLookupError(f"unsupported mode: {req.mode}")
    if req.limit < 1 or req.limit > 10_000:
        raise EvidenceLookupError("limit must be within 1..10000")
    if req.min_confidence is not None and not (0.0 <= req.min_confidence <= 1.0):
        raise EvidenceLookupError("min_confidence must be in [0.0, 1.0]")

    required: dict[str, str] = {
        "by_artifact": "artifact",
        "by_claim": "claim",
        "by_decision": "decision",
        "by_source_path": "source_path",
        "by_run_id": "run_id",
        "by_evidence_type": "evidence_type",
    }
    required_field = required.get(req.mode)
    if required_field and not _as_str(getattr(req, required_field)):
        raise EvidenceLookupError(f"{req.mode} requires {required_field}")


def _match(evidence: Mapping[str, Any], req: EvidenceLookupRequest) -> bool:
    if req.mode == "by_artifact":
        return (req.artifact or "").strip() in set(evidence.get("artifact_refs", []))
    if req.mode == "by_claim":
        return (req.claim or "").strip() in set(evidence.get("claim_refs", []))
    if req.mode == "by_decision":
        return (req.decision or "").strip() in set(evidence.get("decision_refs", []))
    if req.mode == "by_source_path":
        needle = (req.source_path or "").strip()
        return any(needle in str(s) for s in evidence.get("source_refs", []))
    if req.mode == "by_run_id":
        return _as_str(evidence.get("run_id")) == (req.run_id or "").strip()
    if req.mode == "by_evidence_type":
        return str(evidence.get("evidence_type", "")).strip().lower() == (req.evidence_type or "").strip().lower()
    if req.mode == "by_freshness":
        if req.freshness_days is None:
            return False
        dt: datetime | None = evidence.get("_created_at_dt")
        if dt is None:
            return False
        now = cdb_utcnow().replace(tzinfo=timezone.utc)
        age_days = (now - dt).days
        return age_days <= req.freshness_days
    if req.mode == "by_confidence":
        conf = _as_float(evidence.get("confidence"))
        if conf is None or req.min_confidence is None:
            return False
        return conf >= req.min_confidence
    return False


def lookup_evidence_v1(
    evidence_records: Iterable[Mapping[str, Any]],
    request: EvidenceLookupRequest,
) -> dict[str, Any]:
    """Look up evidence over in-memory evidence records.

    Deterministic and side-effect-free.
    """
    _validate_request(request)

    warnings: list[str] = []

    normalized: list[dict[str, Any]] = []
    for raw in evidence_records:
        if not isinstance(raw, Mapping):
            continue
        normalized.append(_normalize_evidence(raw))

    normalized_sorted = sorted(normalized, key=_evidence_sort_key)
    matched = [e for e in normalized_sorted if _match(e, request)]

    if not matched:
        warnings.append("no_evidence_matched")

    matched = matched[: request.limit]

    # Strength buckets
    by_strength: dict[str, list[str]] = {s: [] for s in EVIDENCE_STRENGTH_LEVELS}
    for ev in matched:
        strength = str(ev.get("strength", "weak"))
        if strength in by_strength:
            by_strength[strength].append(ev["evidence_id"])

    stale_ids = [ev["evidence_id"] for ev in matched if ev.get("stale")]
    blocking_missing_ids = [ev["evidence_id"] for ev in matched if ev.get("blocking_missing")]

    if stale_ids:
        warnings.append("stale_evidence_present")
    if blocking_missing_ids:
        warnings.append("blocking_missing_evidence_present")

    # Summary
    total = len(matched)
    strong_count = len(by_strength["strong"])
    moderate_count = len(by_strength["moderate"])
    weak_count = len(by_strength["weak"])
    none_count = len(by_strength["none"])

    if total == 0:
        overall_strength = "none"
    elif blocking_missing_ids:
        overall_strength = "blocking_missing"
    elif strong_count >= total * 0.7:
        overall_strength = "strong"
    elif (strong_count + moderate_count) >= total * 0.5:
        overall_strength = "moderate"
    else:
        overall_strength = "weak"

    evidence_summary = {
        "total": total,
        "strong": strong_count,
        "moderate": moderate_count,
        "weak": weak_count,
        "none": none_count,
        "stale": len(stale_ids),
        "blocking_missing": len(blocking_missing_ids),
        "overall_strength": overall_strength,
    }

    # Strip internal dt field before returning
    clean_matched = [{k: v for k, v in ev.items() if k != "_created_at_dt"} for ev in matched]

    approval_semantics = {
        "lookup_only": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Evidence lookup only. This output does not grant approval, "
            "does not authorize live trading, and must not be interpreted as Human-GO."
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "mode": request.mode,
            "artifact": request.artifact,
            "claim": request.claim,
            "decision": request.decision,
            "source_path": request.source_path,
            "run_id": request.run_id,
            "evidence_type": request.evidence_type,
            "freshness_days": request.freshness_days,
            "min_confidence": request.min_confidence,
            "limit": request.limit,
        },
        "mode": request.mode,
        "matched_evidence": clean_matched,
        "evidence_by_strength": by_strength,
        "stale_evidence_ids": stale_ids,
        "blocking_missing_ids": blocking_missing_ids,
        "evidence_summary": evidence_summary,
        "warnings": sorted(set(warnings)),
        "approval_semantics": approval_semantics,
    }
