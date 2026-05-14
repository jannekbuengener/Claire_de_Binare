"""Context Trust Summary Builder v1 — side-effect-free domain component.

Issues:
    #2121 — [SURREALDB][CONTEXT][TRUST] Implement context trust summary builder v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Scope:
    Implements a minimal, deterministic trust summary builder that combines
    evidence, claim, decision, and memory lookup results into a unified
    trust assessment. No DB access. No SurrealDB SDK. No MCP. No networking.
    No writes.

Guardrails:
    - Assessment only: never implies approval, live-go, or authority.
    - Blocking findings are surfaced explicitly.
    - Trust level 'blocked' does NOT mean hard-blocked by human gate.
      It means the context quality is insufficient to proceed without review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA_VERSION = "trust-summary/v1"

# Trust levels (ascending quality)
TRUST_LEVELS = ("blocked", "weak", "acceptable", "strong")


class TrustSummaryError(ValueError):
    """Raised when trust summary inputs are invalid."""


@dataclass(frozen=True)
class TrustSummaryRequest:
    """Input for the trust summary builder."""

    scope: str
    topic: str | None = None
    artifact: str | None = None


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


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evidence_strength_score(strength: str | None) -> float:
    """Map evidence strength string to a numeric score in [0, 1]."""
    mapping = {
        "none": 0.0,
        "weak": 0.25,
        "moderate": 0.55,
        "strong": 0.90,
        "blocking_missing": 0.0,
    }
    return mapping.get((strength or "none").lower(), 0.0)


def _claim_status_score(status_counts: Mapping[str, int]) -> float:
    """Score claim status distribution in [0, 1]."""
    weights = {
        "supported": 1.0,
        "weakly_supported": 0.5,
        "proposed": 0.3,
        "disputed": 0.1,
        "superseded": 0.2,
        "stale": 0.15,
        "invalidated": 0.0,
    }
    total = sum(status_counts.values())
    if total == 0:
        return 0.5  # neutral when no claims
    score = sum(weights.get(s, 0.0) * count for s, count in status_counts.items())
    return min(score / total, 1.0)


def _decision_currentness_score(result: Mapping[str, Any]) -> float:
    """Score decision currentness in [0, 1]."""
    matched = _as_list(result.get("matched_decisions", []))
    current = _as_list(result.get("current_decisions", []))
    superseded = _as_list(result.get("superseded_decisions", []))
    invalidated = _as_list(result.get("invalidated_decisions", []))

    total = len(matched)
    if total == 0:
        return 0.5  # neutral when no decisions
    current_ratio = len(current) / total
    penalty = (len(superseded) * 0.3 + len(invalidated) * 0.5) / total
    return max(0.0, min(1.0, current_ratio - penalty))


def _memory_trust_score(result: Mapping[str, Any]) -> float:
    """Score memory trust in [0, 1]."""
    trust_counts: dict[str, int] = dict(result.get("trust_counts") or {})
    weights = {
        "source_backed": 1.0,
        "evidence_backed": 0.75,
        "weak": 0.3,
        "superseded": 0.1,
        "stale": 0.05,
    }
    total = sum(trust_counts.values())
    if total == 0:
        return 0.5  # neutral when no memory
    score = sum(weights.get(level, 0.0) * count for level, count in trust_counts.items())
    return min(score / total, 1.0)


def _derive_trust_level(
    composite_score: float,
    blocking_findings: list[str],
) -> str:
    if blocking_findings:
        return "blocked"
    if composite_score >= 0.80:
        return "strong"
    if composite_score >= 0.55:
        return "acceptable"
    if composite_score >= 0.30:
        return "weak"
    return "blocked"


def _collect_stale_flags(
    evidence_result: Mapping[str, Any] | None,
    claim_result: Mapping[str, Any] | None,
    memory_result: Mapping[str, Any] | None,
) -> list[str]:
    flags: list[str] = []
    if evidence_result:
        stale_ids = _as_list(evidence_result.get("stale_evidence_ids"))
        if stale_ids:
            flags.append(f"stale_evidence: {len(stale_ids)} records")
    if claim_result:
        stale_ids = _as_list(claim_result.get("stale_claim_ids"))
        if stale_ids:
            flags.append(f"stale_claims: {len(stale_ids)} records")
    if memory_result:
        stale_ids = _as_list(memory_result.get("stale_memory_ids"))
        if stale_ids:
            flags.append(f"stale_memory: {len(stale_ids)} records")
    return flags


def _collect_disputed_flags(
    claim_result: Mapping[str, Any] | None,
) -> list[str]:
    flags: list[str] = []
    if claim_result:
        disputed = _as_list(claim_result.get("disputed_claim_ids"))
        if disputed:
            flags.append(f"disputed_claims: {len(disputed)} records")
    return flags


def _collect_blocking_findings(
    evidence_result: Mapping[str, Any] | None,
    claim_result: Mapping[str, Any] | None,
    decision_result: Mapping[str, Any] | None,
    memory_result: Mapping[str, Any] | None,
) -> list[str]:
    findings: list[str] = []
    if evidence_result:
        if _as_list(evidence_result.get("blocking_missing_ids")):
            findings.append("blocking_missing_evidence")
    if claim_result:
        disputed = _as_list(claim_result.get("disputed_claim_ids"))
        if disputed:
            findings.append(f"disputed_claims_present ({len(disputed)})")
        missing_ev = _as_list(claim_result.get("missing_evidence_claim_ids"))
        if missing_ev:
            findings.append(f"claims_with_missing_evidence ({len(missing_ev)})")
    if decision_result:
        unresolved = _as_list(decision_result.get("unresolved_evidence_refs"))
        if unresolved:
            findings.append(f"unresolved_evidence_refs_in_decisions ({len(unresolved)})")
    return findings


def _build_recommended_next_reads(
    evidence_result: Mapping[str, Any] | None,
    claim_result: Mapping[str, Any] | None,
    decision_result: Mapping[str, Any] | None,
    memory_result: Mapping[str, Any] | None,
) -> list[str]:
    reads: list[str] = []
    if evidence_result and _as_list(evidence_result.get("blocking_missing_ids")):
        reads.append("resolve_blocking_missing_evidence")
    if claim_result and _as_list(claim_result.get("disputed_claim_ids")):
        reads.append("review_disputed_claims")
    if decision_result and _as_list(decision_result.get("superseded_decisions")):
        reads.append("review_superseded_decisions")
    if memory_result and _as_list(memory_result.get("stale_memory_ids")):
        reads.append("refresh_stale_memory")
    if claim_result and _as_list(claim_result.get("unresolved_evidence_refs")):
        reads.append("fill_missing_evidence_for_claims")
    return reads


def build_trust_summary_v1(
    request: TrustSummaryRequest,
    *,
    evidence_result: Mapping[str, Any] | None = None,
    claim_result: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    memory_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a trust summary over evidence, claim, decision, and memory results.

    Deterministic and side-effect-free.
    """
    if not _as_str(request.scope):
        raise TrustSummaryError("scope is required for trust summary")

    warnings: list[str] = []

    # ── Score each dimension ────────────────────────────────────────────────
    ev_summary = dict(evidence_result.get("evidence_summary") or {}) if evidence_result else {}
    ev_strength = _as_str(ev_summary.get("overall_strength")) or "none"
    evidence_strength_score = _evidence_strength_score(ev_strength)

    claim_status_counts: dict[str, int] = {}
    if claim_result:
        raw_counts = claim_result.get("status_counts") or {}
        claim_status_counts = {k: int(v) for k, v in raw_counts.items()}
    claim_score = _claim_status_score(claim_status_counts)

    decision_score = _decision_currentness_score(decision_result or {})
    memory_score = _memory_trust_score(memory_result or {})

    # ── Composite score (weighted average) ──────────────────────────────────
    weights = [0.30, 0.25, 0.25, 0.20]  # evidence, claim, decision, memory
    scores = [evidence_strength_score, claim_score, decision_score, memory_score]
    composite_score = round(sum(w * s for w, s in zip(weights, scores)), 4)

    # ── Blocking findings ───────────────────────────────────────────────────
    blocking_findings = _collect_blocking_findings(
        evidence_result, claim_result, decision_result, memory_result
    )

    # ── Stale / disputed flags ──────────────────────────────────────────────
    stale_flags: list[str] = []
    if evidence_result:
        stale_ev = _as_list(evidence_result.get("stale_evidence_ids"))
        if stale_ev:
            stale_flags.append(f"stale_evidence: {len(stale_ev)} records")
    if claim_result:
        stale_cl = _as_list(claim_result.get("stale_claim_ids"))
        if stale_cl:
            stale_flags.append(f"stale_claims: {len(stale_cl)} records")
    if memory_result:
        stale_mem = _as_list(memory_result.get("stale_memory_ids"))
        if stale_mem:
            stale_flags.append(f"stale_memory: {len(stale_mem)} records")

    disputed_flags = _collect_disputed_flags(claim_result)

    if stale_flags:
        warnings.append("stale_context_present")
    if disputed_flags:
        warnings.append("disputed_claims_present")

    # ── Missing evidence ────────────────────────────────────────────────────
    missing_evidence: list[str] = []
    if evidence_result:
        missing_evidence.extend(_as_list(evidence_result.get("blocking_missing_ids")))
    if claim_result:
        for cid in _as_list(claim_result.get("missing_evidence_claim_ids")):
            missing_evidence.append(f"claim:{cid}")

    if missing_evidence:
        warnings.append("missing_evidence_detected")

    # ── Trust level ─────────────────────────────────────────────────────────
    trust_level = _derive_trust_level(composite_score, blocking_findings)

    # ── Recommended next reads ──────────────────────────────────────────────
    recommended_next_reads = _build_recommended_next_reads(
        evidence_result, claim_result, decision_result, memory_result
    )

    # ── Decision currentness summary ────────────────────────────────────────
    decision_currentness: dict[str, Any] = {}
    if decision_result:
        decision_currentness = {
            "current": len(_as_list(decision_result.get("current_decisions"))),
            "superseded": len(_as_list(decision_result.get("superseded_decisions"))),
            "invalidated": len(_as_list(decision_result.get("invalidated_decisions"))),
            "total": len(_as_list(decision_result.get("matched_decisions"))),
        }

    # ── Memory trust summary ────────────────────────────────────────────────
    memory_trust_summary: dict[str, Any] = {}
    if memory_result:
        memory_trust_summary = dict(memory_result.get("memory_summary") or {})

    approval_semantics = {
        "assessment_only": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Trust summary is a contextual assessment only. "
            "trust_level='blocked' means insufficient context quality — "
            "it is NOT a human gate block. No approval, no live-go, no Echtgeld-GO."
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "scope": request.scope,
        "topic": request.topic,
        "artifact": request.artifact,
        "trust_level": trust_level,
        "composite_score": composite_score,
        "evidence_strength": ev_strength,
        "evidence_strength_score": round(evidence_strength_score, 4),
        "claim_status_summary": claim_status_counts,
        "claim_score": round(claim_score, 4),
        "decision_currentness": decision_currentness,
        "decision_score": round(decision_score, 4),
        "memory_trust_summary": memory_trust_summary,
        "memory_score": round(memory_score, 4),
        "stale_flags": stale_flags,
        "disputed_flags": disputed_flags,
        "missing_evidence": missing_evidence,
        "blocking_trust_findings": blocking_findings,
        "recommended_next_reads": recommended_next_reads,
        "confidence_summary": {
            "composite_score": composite_score,
            "trust_level": trust_level,
            "dimensions": {
                "evidence": round(evidence_strength_score, 4),
                "claims": round(claim_score, 4),
                "decisions": round(decision_score, 4),
                "memory": round(memory_score, 4),
            },
        },
        "warnings": sorted(set(warnings)),
        "approval_semantics": approval_semantics,
    }
