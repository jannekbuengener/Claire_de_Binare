"""Context Trust Summary Builder v1 — side-effect-free domain component.

Issues:
    #2121 — [SURREALDB][CONTEXT][TRUST] Implement context trust summary builder v1
    #2856 — [CONTEXT][TRUST] Operator trust thresholds (HIGH/MEDIUM/LOW/BLOCKED)
    Parent: #2115 (Wave-14)
    Epic: #1976

Contract:
    docs/contracts/context_tooling/CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md

Scope:
    Combines evidence, claim, decision, and memory lookup results into a unified
    trust assessment. No DB access. No SurrealDB SDK. No MCP. No networking.
    No writes.

Guardrails:
    - Assessment only: never implies approval, live-go, or authority.
    - operator_trust_level LOW/BLOCKED is not operational truth.
    - Legacy trust_level 'blocked' is insufficient context quality, not Human-GO.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA_VERSION = "trust-summary/v1"
OPERATOR_TRUST_CONTRACT_VERSION = "context-trust-threshold/v1"

# Wave-14 legacy trust levels (ascending quality)
TRUST_LEVELS = ("blocked", "weak", "acceptable", "strong")

# Operator SSOT (#2856) — ascending quality
OPERATOR_TRUST_LEVELS = ("BLOCKED", "LOW", "MEDIUM", "HIGH")

_OPERATOR_RANK = {"BLOCKED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

_LEGACY_TO_OPERATOR_BASE: dict[str, str] = {
    "blocked": "BLOCKED",
    "weak": "LOW",
    "acceptable": "MEDIUM",
    "strong": "HIGH",
}

_LIMITATION_TRUST_NEVER_AUTHORIZES = (
    "Trust summary is assessment-only; it does not grant Human-GO, Live-GO, "
    "Echtgeld-GO, persist, mutation, or operational truth."
)
_LIMITATION_BELOW_HIGH = (
    "operator_trust_level is below HIGH; do not treat output as operational truth."
)
_LIMITATION_LOW_BLOCKED = (
    "operator_trust_level LOW or BLOCKED: fail-closed for writes, live actions, "
    "merges, and LR decisions — recheck live GitHub and repo canon."
)


class TrustSummaryError(ValueError):
    """Raised when trust summary inputs are invalid."""


@dataclass(frozen=True)
class TrustSummaryRequest:
    """Input for the trust summary builder."""

    scope: str
    topic: str | None = None
    artifact: str | None = None


@dataclass(frozen=True)
class TrustContextSignals:
    """Optional external gates for operator_trust_level (tests/harness; no network)."""

    github_live_mismatch: bool = False
    ledger_stale_vs_live: bool = False
    repo_crosscheck_present: bool = True
    record_source: str | None = None
    caller_supplied_source_only: bool = False
    freshness_ok: bool = True
    required_db_records_missing: bool = False

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> TrustContextSignals | None:
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise TrustSummaryError("context_signals must be a mapping when provided")
        record_source = _as_str(raw.get("record_source"))
        return cls(
            github_live_mismatch=bool(raw.get("github_live_mismatch")),
            ledger_stale_vs_live=bool(raw.get("ledger_stale_vs_live")),
            repo_crosscheck_present=bool(raw.get("repo_crosscheck_present", True)),
            record_source=record_source,
            caller_supplied_source_only=bool(raw.get("caller_supplied_source_only")),
            freshness_ok=bool(raw.get("freshness_ok", True)),
            required_db_records_missing=bool(raw.get("required_db_records_missing")),
        )


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


def _cap_operator_level(level: str, ceiling: str) -> str:
    if _OPERATOR_RANK[level] > _OPERATOR_RANK[ceiling]:
        return ceiling
    return level


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


def _derive_operator_trust_level(
    legacy_level: str,
    *,
    composite_score: float,
    blocking_findings: list[str],
    stale_flags: list[str],
    disputed_flags: list[str],
    context_signals: TrustContextSignals | None,
) -> tuple[str, dict[str, Any], list[str]]:
    """Return operator level, mapping metadata, and applied gate notes."""
    base = _LEGACY_TO_OPERATOR_BASE.get(legacy_level, "BLOCKED")
    gates_applied: list[str] = []
    operator = base

    if blocking_findings:
        return (
            "BLOCKED",
            {
                "legacy_trust_level": legacy_level,
                "base_operator_level": base,
                "composite_score": composite_score,
                "gates_applied": ["blocking_trust_findings"],
                "context_signals_supplied": context_signals is not None,
            },
            ["blocking_trust_findings"],
        )

    if context_signals is None:
        return (
            operator,
            {
                "legacy_trust_level": legacy_level,
                "base_operator_level": base,
                "composite_score": composite_score,
                "gates_applied": [],
                "context_signals_supplied": False,
            },
            [],
        )

    if context_signals.github_live_mismatch:
        gates_applied.append("github_live_mismatch")
        operator = "BLOCKED"
    if context_signals.ledger_stale_vs_live:
        gates_applied.append("ledger_stale_vs_live")
        operator = "BLOCKED"
    if context_signals.required_db_records_missing:
        gates_applied.append("required_db_records_missing")
        operator = "BLOCKED"

    if operator != "BLOCKED":
        if context_signals.caller_supplied_source_only:
            gates_applied.append("caller_supplied_source_only")
            operator = _cap_operator_level(operator, "LOW")
        if not context_signals.freshness_ok:
            gates_applied.append("freshness_not_ok")
            operator = _cap_operator_level(operator, "LOW")
        if not context_signals.repo_crosscheck_present:
            gates_applied.append("repo_crosscheck_missing")
            operator = _cap_operator_level(operator, "MEDIUM")
        record_source = (context_signals.record_source or "").lower()
        if record_source in ("repo-only", "in_memory"):
            gates_applied.append(f"record_source_{record_source.replace('-', '_')}")
            operator = _cap_operator_level(operator, "MEDIUM")
        if stale_flags or disputed_flags:
            gates_applied.append("stale_or_disputed_context")
            operator = _cap_operator_level(operator, "MEDIUM")

        if operator == "HIGH" and legacy_level != "strong":
            gates_applied.append("legacy_not_strong")
            operator = _LEGACY_TO_OPERATOR_BASE.get(legacy_level, "MEDIUM")

    mapping = {
        "legacy_trust_level": legacy_level,
        "base_operator_level": base,
        "composite_score": composite_score,
        "gates_applied": gates_applied,
        "context_signals_supplied": True,
        "context_signals": {
            "github_live_mismatch": context_signals.github_live_mismatch,
            "ledger_stale_vs_live": context_signals.ledger_stale_vs_live,
            "repo_crosscheck_present": context_signals.repo_crosscheck_present,
            "record_source": context_signals.record_source,
            "caller_supplied_source_only": context_signals.caller_supplied_source_only,
            "freshness_ok": context_signals.freshness_ok,
            "required_db_records_missing": context_signals.required_db_records_missing,
        },
    }
    return operator, mapping, gates_applied


def _build_operator_limitations(operator_trust_level: str) -> list[str]:
    limitations = [_LIMITATION_TRUST_NEVER_AUTHORIZES]
    if operator_trust_level != "HIGH":
        limitations.append(_LIMITATION_BELOW_HIGH)
    if operator_trust_level in ("LOW", "BLOCKED"):
        limitations.append(_LIMITATION_LOW_BLOCKED)
    return limitations


def _authorization_semantics(operator_trust_level: str) -> dict[str, Any]:
    return {
        "operational_truth_allowed": False,
        "no_human_go": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "no_persist": True,
        "no_mutation": True,
        "operator_trust_level": operator_trust_level,
        "note": (
            "authorization_semantics is explicit deny-by-default; "
            "trust output never grants Human-GO, Live-GO, persist, or mutation."
        ),
    }


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


def _collect_disputed_flags(
    claim_result: Mapping[str, Any] | None,
) -> list[str]:
    flags: list[str] = []
    if claim_result:
        disputed = _as_list(claim_result.get("disputed_claim_ids"))
        if disputed:
            flags.append(f"disputed_claims: {len(disputed)} records")
    return flags


def build_trust_summary_v1(
    request: TrustSummaryRequest,
    *,
    evidence_result: Mapping[str, Any] | None = None,
    claim_result: Mapping[str, Any] | None = None,
    decision_result: Mapping[str, Any] | None = None,
    memory_result: Mapping[str, Any] | None = None,
    context_signals: TrustContextSignals | None = None,
) -> dict[str, Any]:
    """Build a trust summary over evidence, claim, decision, and memory results.

    Deterministic and side-effect-free.
    """
    if not _as_str(request.scope):
        raise TrustSummaryError("scope is required for trust summary")

    warnings: list[str] = []

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

    weights = [0.30, 0.25, 0.25, 0.20]
    scores = [evidence_strength_score, claim_score, decision_score, memory_score]
    composite_score = round(sum(w * s for w, s in zip(weights, scores)), 4)

    blocking_findings = _collect_blocking_findings(
        evidence_result, claim_result, decision_result, memory_result
    )

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

    missing_evidence: list[str] = []
    if evidence_result:
        missing_evidence.extend(_as_list(evidence_result.get("blocking_missing_ids")))
    if claim_result:
        for cid in _as_list(claim_result.get("missing_evidence_claim_ids")):
            missing_evidence.append(f"claim:{cid}")

    if missing_evidence:
        warnings.append("missing_evidence_detected")

    trust_level = _derive_trust_level(composite_score, blocking_findings)

    operator_trust_level, operator_trust_mapping, gate_notes = _derive_operator_trust_level(
        trust_level,
        composite_score=composite_score,
        blocking_findings=blocking_findings,
        stale_flags=stale_flags,
        disputed_flags=disputed_flags,
        context_signals=context_signals,
    )
    if gate_notes:
        warnings.extend(gate_notes)

    limitations = _build_operator_limitations(operator_trust_level)
    authorization_semantics = _authorization_semantics(operator_trust_level)

    recommended_next_reads = _build_recommended_next_reads(
        evidence_result, claim_result, decision_result, memory_result
    )

    decision_currentness: dict[str, Any] = {}
    if decision_result:
        decision_currentness = {
            "current": len(_as_list(decision_result.get("current_decisions"))),
            "superseded": len(_as_list(decision_result.get("superseded_decisions"))),
            "invalidated": len(_as_list(decision_result.get("invalidated_decisions"))),
            "total": len(_as_list(decision_result.get("matched_decisions"))),
        }

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
            "it is NOT a human gate block. No approval, no live-go, no Echtgeld-GO. "
            "See operator_trust_level and authorization_semantics (#2856)."
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "operator_trust_contract_version": OPERATOR_TRUST_CONTRACT_VERSION,
        "scope": request.scope,
        "topic": request.topic,
        "artifact": request.artifact,
        "trust_level": trust_level,
        "operator_trust_level": operator_trust_level,
        "operator_trust_mapping": operator_trust_mapping,
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
        "limitations": limitations,
        "authorization_semantics": authorization_semantics,
        "confidence_summary": {
            "composite_score": composite_score,
            "trust_level": trust_level,
            "operator_trust_level": operator_trust_level,
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
