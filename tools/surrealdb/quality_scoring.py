"""Knowledge Quality Scoring Service v1 — side-effect-free domain component.

Issues:
    #2171 — [SURREALDB][CONTEXT][QUALITY-RUNTIME] Implement knowledge quality scoring service v1
    Parent: #2170 (Wave-18 anchor)
    Epic: #1976

Scope:
    Pure, deterministic knowledge quality scoring service. No DB access. No
    SurrealDB SDK. No MCP. No networking. No writes. No auto-fix. No live-go.

    Computes 8 quality scores:
        coverage_score          — breadth of source/doc/test coverage
        freshness_score         — how current sources and decisions are
        evidence_score          — strength and completeness of evidence
        contradiction_score     — inverse: how free of contradictions
        dependency_confidence_score — confidence of dependency edges
        memory_trust_score      — trust level of memory items
        decision_validity_score — how many decisions are current vs. superseded
        scope_risk_score        — inverse: how free of scope drift findings

    And an aggregated overall_score with grade: blocking/watch/weak/good.

Guardrails:
    - Score is signal, not authorization.
    - Scores do not imply live-go, echtgeld-go, or action authority.
    - No auto-fix. No auto-write.
    - LR status remains NO-GO for live trading.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "quality-scoring/v1"
DETECTED_BY = "quality-scoring/v1"

SCORE_DIMENSIONS = (
    "coverage_score",
    "freshness_score",
    "evidence_score",
    "contradiction_score",
    "dependency_confidence_score",
    "memory_trust_score",
    "decision_validity_score",
    "scope_risk_score",
)

GRADE_BLOCKING = "blocking"
GRADE_WATCH = "watch"
GRADE_WEAK = "weak"
GRADE_GOOD = "good"

GRADES = (GRADE_BLOCKING, GRADE_WATCH, GRADE_WEAK, GRADE_GOOD)

# Inclusive lower bound, exclusive upper bound (except GOOD which is fully inclusive at 1.0)
_GRADE_BANDS: tuple[tuple[str, float, float], ...] = (
    (GRADE_BLOCKING, 0.0, 0.30),
    (GRADE_WATCH, 0.30, 0.50),
    (GRADE_WEAK, 0.50, 0.70),
    (GRADE_GOOD, 0.70, 1.01),
)

GUARDRAILS: tuple[str, ...] = (
    "Quality Score is signal, not authorization.",
    "No auto-fix. No auto-write.",
    "No Live-Readiness-Go.",
    "No Echtgeld-Go.",
    "Human-GO required for any action after blocking quality score.",
)

# Stale finding statuses that are terminal/remediated and should not penalise
# freshness. Mirrors the non-penalised sets used in contradiction and scope-risk
# scoring.
_STALE_EXEMPT_STATUSES: frozenset[str] = frozenset(
    {"refreshed", "accepted_risk", "false_positive"}
)


class QualityScoringError(ValueError):
    """Raised when quality scoring inputs are invalid or unsafe."""


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DimensionScore:
    """Score result for a single quality dimension."""

    dimension: str
    score: float          # 0.0 – 1.0
    grade: str            # blocking / watch / weak / good
    explanation: str
    inputs_used: int
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 4),
            "grade": self.grade,
            "explanation": self.explanation,
            "inputs_used": self.inputs_used,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class QualityScoreResult:
    """Full quality scoring result for a bundle."""

    scope_id: str
    level: str                              # artifact | domain | issue | system
    overall_score: float
    overall_grade: str
    dimensions: tuple[DimensionScore, ...]
    blocking_dimensions: tuple[str, ...]    # dimension names graded blocking
    watch_dimensions: tuple[str, ...]       # dimension names graded watch
    recommended_next_reads: tuple[str, ...]
    guardrails: tuple[str, ...] = field(default_factory=lambda: GUARDRAILS)
    scored_at: str = field(default_factory=lambda: cdb_utcnow().isoformat())
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scope_id": self.scope_id,
            "level": self.level,
            "scored_at": self.scored_at,
            "overall_score": round(self.overall_score, 4),
            "overall_grade": self.overall_grade,
            "blocking_dimensions": list(self.blocking_dimensions),
            "watch_dimensions": list(self.watch_dimensions),
            "recommended_next_reads": list(self.recommended_next_reads),
            "guardrails": list(self.guardrails),
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _grade(score: float) -> str:
    for grade, lo, hi in _GRADE_BANDS:
        if lo <= score < hi:
            return grade
    return GRADE_GOOD


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _as_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return str(value).strip() if value is not None else ""


def _deterministic_id(parts: Sequence[str]) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _validate_bundle(bundle: Any) -> Mapping[str, Any]:
    if not isinstance(bundle, Mapping):
        raise QualityScoringError("bundle must be a mapping")
    meta = bundle.get("meta")
    if not isinstance(meta, Mapping):
        raise QualityScoringError("bundle.meta must be a mapping")
    return bundle


# ── Score computation ─────────────────────────────────────────────────────────


def _score_coverage(sources: list[Any]) -> DimensionScore:
    """Coverage: what fraction of sources have docs + tests + evidence."""
    if not sources:
        return DimensionScore(
            dimension="coverage_score",
            score=0.0,
            grade=GRADE_BLOCKING,
            explanation="No sources provided — coverage cannot be assessed.",
            inputs_used=0,
            warnings=("no sources in bundle",),
        )
    total = len(sources)
    covered = sum(
        1
        for s in sources
        if (
            isinstance(s, Mapping)
            and s.get("has_documentation") is True
            and s.get("has_tests") is True
        )
    )
    score = covered / total
    warnings: list[str] = []
    if score < 0.30:
        warnings.append(
            f"only {covered}/{total} sources have both docs and tests"
        )
    return DimensionScore(
        dimension="coverage_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"{covered}/{total} sources have documentation and test coverage."
        ),
        inputs_used=total,
        warnings=tuple(warnings),
    )


def _score_freshness(
    sources: list[Any],
    decisions: list[Any],
    stale_findings: list[Any] | None = None,
) -> DimensionScore:
    """Freshness: fraction of sources + decisions that are current.

    Bundle-level ``stale_findings`` are each counted as an additional
    non-fresh item so that a bundle with all-current sources but open
    stale findings cannot score perfect 1.0 freshness.
    """
    stale_findings = stale_findings or []
    items: list[Any] = list(sources) + list(decisions)
    # Only count active (non-exempt) stale findings against freshness.
    # Terminal/remediated statuses (refreshed, accepted_risk, false_positive)
    # are excluded to mirror the behaviour of contradiction and scope-risk
    # scoring which skip their own non-penalised statuses.
    active_stale = [
        f for f in stale_findings
        if not isinstance(f, Mapping)
        or _as_str(f.get("status", "open")).lower() not in _STALE_EXEMPT_STATUSES
    ]
    extra_stale = len(active_stale)
    if not items and extra_stale == 0:
        return DimensionScore(
            dimension="freshness_score",
            score=0.5,
            grade=GRADE_WATCH,
            explanation="No sources or decisions provided — freshness defaulted to 0.5 (watch).",
            inputs_used=0,
        )
    total = len(items) + extra_stale
    fresh = 0
    for item in items:
        if not isinstance(item, Mapping):
            continue
        status = _as_str(item.get("status", "")).lower()
        stale_flag = item.get("stale") is True
        deleted_flag = item.get("deleted") is True
        if not stale_flag and not deleted_flag and status not in (
            "superseded", "invalidated", "deleted", "stale"
        ):
            fresh += 1
    score = fresh / total
    explanation = (
        f"{fresh}/{total} sources/decisions are current "
        f"(not stale, superseded, or deleted)."
    )
    if extra_stale:
        explanation += f" {extra_stale} active stale finding(s) counted against freshness."
    return DimensionScore(
        dimension="freshness_score",
        score=score,
        grade=_grade(score),
        explanation=explanation,
        inputs_used=total,
    )


def _score_evidence(evidence_items: list[Any]) -> DimensionScore:
    """Evidence: average strength of evidence items."""
    _strength_map = {
        "strong": 1.0,
        "moderate": 0.6,
        "weak": 0.25,
        "none": 0.0,
        "blocking_missing": 0.0,
    }
    if not evidence_items:
        return DimensionScore(
            dimension="evidence_score",
            score=0.0,
            grade=GRADE_BLOCKING,
            explanation="No evidence items provided — evidence quality is unknown.",
            inputs_used=0,
            warnings=("no evidence in bundle",),
        )
    total = len(evidence_items)
    score_sum = 0.0
    expired_count = 0
    for item in evidence_items:
        if not isinstance(item, Mapping):
            continue
        strength = _as_str(item.get("strength", "none")).lower()
        s = _strength_map.get(strength, 0.0)
        if item.get("expired") is True:
            s *= 0.25
            expired_count += 1
        score_sum += s
    score = score_sum / total
    warnings: list[str] = []
    if expired_count > 0:
        warnings.append(f"{expired_count} expired evidence item(s) penalised")
    return DimensionScore(
        dimension="evidence_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"Average evidence strength across {total} items: {score:.2f}."
        ),
        inputs_used=total,
        warnings=tuple(warnings),
    )


def _score_contradiction(contradiction_findings: list[Any]) -> DimensionScore:
    """Contradiction: inverse score — fewer open/blocking contradictions is better."""
    if not contradiction_findings:
        return DimensionScore(
            dimension="contradiction_score",
            score=1.0,
            grade=GRADE_GOOD,
            explanation="No contradiction findings — contradiction score is perfect.",
            inputs_used=0,
        )
    _non_penalised = frozenset(
        {"false_positive", "accepted_risk", "resolved", "superseded"}
    )
    total = len(contradiction_findings)
    blocking_open = 0
    warning_open = 0
    for f in contradiction_findings:
        if not isinstance(f, Mapping):
            continue
        status = _as_str(f.get("status", "open")).lower()
        if status in _non_penalised:
            continue
        severity = _as_str(f.get("severity", "info")).lower()
        if severity == "blocking":
            blocking_open += 1
        elif severity == "warning":
            warning_open += 1
    # Penalty: blocking findings reduce score by 0.35 each, warnings by 0.10 each
    penalty = min(blocking_open * 0.35 + warning_open * 0.10, 1.0)
    score = max(1.0 - penalty, 0.0)
    warnings: list[str] = []
    if blocking_open > 0:
        warnings.append(f"{blocking_open} open blocking contradiction(s)")
    return DimensionScore(
        dimension="contradiction_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"Contradiction check across {total} findings: "
            f"{blocking_open} blocking open, {warning_open} warning open."
        ),
        inputs_used=total,
        warnings=tuple(warnings),
    )


def _score_dependency_confidence(dependency_edges: list[Any]) -> DimensionScore:
    """Dependency confidence: fraction of edges with high/medium confidence."""
    _conf_map = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.1}
    if not dependency_edges:
        return DimensionScore(
            dimension="dependency_confidence_score",
            score=0.5,
            grade=GRADE_WATCH,
            explanation="No dependency edges — confidence defaulted to 0.5 (watch).",
            inputs_used=0,
        )
    total = len(dependency_edges)
    score_sum = 0.0
    for edge in dependency_edges:
        if not isinstance(edge, Mapping):
            continue
        conf = _as_str(edge.get("confidence", "unknown")).lower()
        score_sum += _conf_map.get(conf, 0.1)
    score = score_sum / total
    return DimensionScore(
        dimension="dependency_confidence_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"Average dependency edge confidence across {total} edges: {score:.2f}."
        ),
        inputs_used=total,
    )


def _score_memory_trust(memory_items: list[Any]) -> DimensionScore:
    """Memory trust: fraction of memory items at acceptable or strong trust."""
    _trust_map = {"strong": 1.0, "acceptable": 0.7, "weak": 0.3, "blocked": 0.0}
    if not memory_items:
        return DimensionScore(
            dimension="memory_trust_score",
            score=0.5,
            grade=GRADE_WATCH,
            explanation="No memory items — trust defaulted to 0.5 (watch).",
            inputs_used=0,
        )
    total = len(memory_items)
    score_sum = 0.0
    for item in memory_items:
        if not isinstance(item, Mapping):
            continue
        trust = _as_str(item.get("trust_level", "weak")).lower()
        score_sum += _trust_map.get(trust, 0.3)
    score = score_sum / total
    return DimensionScore(
        dimension="memory_trust_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"Average memory trust across {total} items: {score:.2f}."
        ),
        inputs_used=total,
    )


def _score_decision_validity(decisions: list[Any]) -> DimensionScore:
    """Decision validity: fraction of decisions that are current (not superseded/invalidated)."""
    if not decisions:
        return DimensionScore(
            dimension="decision_validity_score",
            score=0.5,
            grade=GRADE_WATCH,
            explanation="No decisions provided — validity defaulted to 0.5 (watch).",
            inputs_used=0,
        )
    total = len(decisions)
    current = sum(
        1
        for d in decisions
        if isinstance(d, Mapping)
        and _as_str(d.get("status", "current")).lower()
        not in ("superseded", "invalidated", "stale")
    )
    score = current / total
    return DimensionScore(
        dimension="decision_validity_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"{current}/{total} decisions are current "
            f"(not superseded or invalidated)."
        ),
        inputs_used=total,
    )


def _score_scope_risk(scope_drift_findings: list[Any]) -> DimensionScore:
    """Scope risk: inverse score — fewer open/blocking scope drift findings is better."""
    if not scope_drift_findings:
        return DimensionScore(
            dimension="scope_risk_score",
            score=1.0,
            grade=GRADE_GOOD,
            explanation="No scope drift findings — scope risk score is perfect.",
            inputs_used=0,
        )
    _non_penalised = frozenset({"false_positive", "accepted_risk", "resolved"})
    total = len(scope_drift_findings)
    blocking_open = 0
    warning_open = 0
    for f in scope_drift_findings:
        if not isinstance(f, Mapping):
            continue
        status = _as_str(f.get("status", "open")).lower()
        if status in _non_penalised:
            continue
        severity = _as_str(f.get("severity", "info")).lower()
        if severity == "blocking":
            blocking_open += 1
        elif severity == "warning":
            warning_open += 1
    penalty = min(blocking_open * 0.40 + warning_open * 0.12, 1.0)
    score = max(1.0 - penalty, 0.0)
    warnings: list[str] = []
    if blocking_open > 0:
        warnings.append(f"{blocking_open} open blocking scope drift finding(s)")
    return DimensionScore(
        dimension="scope_risk_score",
        score=score,
        grade=_grade(score),
        explanation=(
            f"Scope drift check across {total} findings: "
            f"{blocking_open} blocking open, {warning_open} warning open."
        ),
        inputs_used=total,
        warnings=tuple(warnings),
    )


# ── Public API ────────────────────────────────────────────────────────────────


def score_knowledge_quality_v1(
    bundle: Mapping[str, Any],
    as_of: str | None = None,
) -> QualityScoreResult:
    """Compute knowledge quality scores for the given bundle.

    The bundle is a plain mapping describing the current context state:

    .. code-block:: json

        {
          "meta": {
            "scope_id": "my-scope",
            "level": "artifact|domain|issue|system"
          },
          "sources": [...],
          "decisions": [...],
          "evidence_items": [...],
          "contradiction_findings": [...],
          "stale_findings": [...],
          "dependency_edges": [...],
          "memory_items": [...],
          "scope_drift_findings": [...]
        }

    Returns a :class:`QualityScoreResult` with per-dimension scores and an
    aggregated overall grade.

    Raises:
        QualityScoringError: if the bundle is structurally invalid.
    """
    _validate_bundle(bundle)
    meta = bundle.get("meta", {})
    scope_id = _as_str(meta.get("scope_id", "")) or _deterministic_id(
        [str(bundle)]
    )
    level = _as_str(meta.get("level", "system")).lower()
    if level not in ("artifact", "domain", "issue", "system"):
        level = "system"

    sources = _as_list(bundle.get("sources"))
    decisions = _as_list(bundle.get("decisions"))
    evidence_items = _as_list(bundle.get("evidence_items"))
    contradiction_findings = _as_list(bundle.get("contradiction_findings"))
    stale_findings = _as_list(bundle.get("stale_findings"))
    dependency_edges = _as_list(bundle.get("dependency_edges"))
    memory_items = _as_list(bundle.get("memory_items"))
    scope_drift_findings = _as_list(bundle.get("scope_drift_findings"))

    dims = (
        _score_coverage(sources),
        _score_freshness(sources, decisions, stale_findings),
        _score_evidence(evidence_items),
        _score_contradiction(contradiction_findings),
        _score_dependency_confidence(dependency_edges),
        _score_memory_trust(memory_items),
        _score_decision_validity(decisions),
        _score_scope_risk(scope_drift_findings),
    )

    # Overall score: weighted average
    # Blocking findings in contradiction/scope_risk have higher weight.
    weights = {
        "coverage_score": 1.0,
        "freshness_score": 1.0,
        "evidence_score": 1.5,
        "contradiction_score": 1.5,
        "dependency_confidence_score": 0.8,
        "memory_trust_score": 0.8,
        "decision_validity_score": 1.2,
        "scope_risk_score": 1.2,
    }
    total_weight = sum(weights[d.dimension] for d in dims)
    weighted_sum = sum(weights[d.dimension] * d.score for d in dims)
    overall_score = weighted_sum / total_weight

    # If any single dimension is blocking → overall is at most watch
    blocking_dims = tuple(d.dimension for d in dims if d.grade == GRADE_BLOCKING)
    watch_dims = tuple(d.dimension for d in dims if d.grade == GRADE_WATCH)

    # Force downgrade if blocking dimensions exist
    overall_grade = _grade(overall_score)
    if blocking_dims and overall_grade in (GRADE_WEAK, GRADE_GOOD):
        overall_grade = GRADE_WATCH

    next_reads = ["AGENTS.md", "docs/runbooks/CONTROL_REGISTER.md"]
    if blocking_dims:
        next_reads.append("docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md")

    return QualityScoreResult(
        scope_id=scope_id,
        level=level,
        overall_score=overall_score,
        overall_grade=overall_grade,
        dimensions=dims,
        blocking_dimensions=blocking_dims,
        watch_dimensions=watch_dims,
        recommended_next_reads=tuple(next_reads),
        scored_at=(as_of or cdb_utcnow().isoformat()),
    )
