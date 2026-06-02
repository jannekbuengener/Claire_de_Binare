"""Hybrid retrieval ranking v1 — side-effect-free domain component.

Issues:
    #2799 — [PHASE-2][SURREALDB][SLICE-3] Hybrid retrieval and ranking v1
    Parent: #2778 (Phase-2 epic)
    Contract: docs/surrealdb/context-hybrid-retrieval-strategy-v1.md (#2015)

Scope:
    Deterministic weighted ranking and explainability for hybrid retrieval
    candidates. No DB access. No SurrealDB SDK. No MCP. No networking.
    No writes. Vector search is optional/deferred (not weighted in v1).

Guardrails:
    - Retrieval results are context, not truth.
    - No retrieval result implies Live-Go or Echtgeld-Go.
    - LR remains NO-GO for live trading.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "hybrid-retrieval-ranking/v1"

RANKING_FACTORS = (
    "source_match",
    "graph_distance",
    "evidence_strength",
    "freshness",
    "confidence",
    "scope_match",
    "memory_trust",
)

DEFAULT_RANKING_WEIGHTS: dict[str, float] = {
    "source_match": 0.20,
    "graph_distance": 0.15,
    "evidence_strength": 0.15,
    "freshness": 0.15,
    "confidence": 0.20,
    "scope_match": 0.10,
    "memory_trust": 0.05,
}

MISSING_FACTOR_DEFAULT = 0.35
WEAK_CONFIDENCE_THRESHOLD = 0.30
GRAPH_DISTANCE_MAX_HOPS = 10.0
FRESHNESS_DECAY_PER_DAY = 0.05
FRESHNESS_NO_TIMESTAMP_DEFAULT = 0.5
FRESHNESS_MAX_SCORE = 1.0
FRESHNESS_MIN_SCORE = 0.1
FRESHNESS_FULL_SCORE_MAX_AGE_DAYS = 1.0
FRESHNESS_MIN_SCORE_AGE_DAYS = 18.0

GUARDRAILS: tuple[str, ...] = (
    "Retrieval results are context, not truth.",
    "No retrieval result implies Live-Go.",
    "No retrieval result implies Echtgeld-Go.",
    "LR status remains NO-GO for live trading.",
    "Human-GO required for any live capital action.",
)

_EVIDENCE_STRENGTH_MAP: dict[str, float] = {
    "none": 0.0,
    "weak": 0.25,
    "moderate": 0.55,
    "strong": 0.90,
    "blocking_missing": 0.0,
}


class HybridRetrievalRankingError(ValueError):
    """Raised when ranking inputs or weights are invalid."""


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_finite_float(value: Any) -> float | None:
    """Parse a float and reject non-finite values (NaN, +/-inf)."""
    parsed = _as_float(value)
    if parsed is None or not math.isfinite(parsed):
        return None
    return parsed


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return str(value).strip() or None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def normalize_factor(value: Any, *, missing_default: float = MISSING_FACTOR_DEFAULT) -> float:
    """Clamp a finite factor to [0, 1]; missing/invalid values use a conservative default."""
    numeric = _as_finite_float(value)
    if numeric is None:
        return missing_default
    return max(0.0, min(1.0, numeric))


def _score_numeric_field(
    raw: Any,
    *,
    missing_default: float = MISSING_FACTOR_DEFAULT,
) -> tuple[float, bool, bool]:
    """Return (score, is_missing, is_invalid)."""
    if raw is None:
        return missing_default, True, False
    numeric = _as_finite_float(raw)
    if numeric is None:
        return missing_default, False, True
    return max(0.0, min(1.0, numeric)), False, False


def _parse_datetime(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return (
            raw.astimezone(timezone.utc)
            if raw.tzinfo
            else raw.replace(tzinfo=timezone.utc)
        )
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
    return (
        parsed.astimezone(timezone.utc)
        if parsed.tzinfo
        else parsed.replace(tzinfo=timezone.utc)
    )


def _resolve_reference_time(
    candidate: Mapping[str, Any],
    query_context: Mapping[str, Any] | None,
) -> datetime:
    for source in (query_context, candidate):
        if not source:
            continue
        for key in ("as_of", "reference_time", "reference_at", "now"):
            parsed = _parse_datetime(source.get(key))
            if parsed is not None:
                return parsed
    parsed_now = _parse_datetime(cdb_utcnow())
    if parsed_now is None:
        raise HybridRetrievalRankingError("reference time from clock is invalid")
    return parsed_now


def created_at_to_freshness_score(
    created_at: datetime,
    *,
    reference: datetime,
) -> float:
    """Map created_at to freshness per strategy v1 (5% decay/day, clamped)."""
    ref = (
        reference.astimezone(timezone.utc)
        if reference.tzinfo
        else reference.replace(tzinfo=timezone.utc)
    )
    created = (
        created_at.astimezone(timezone.utc)
        if created_at.tzinfo
        else created_at.replace(tzinfo=timezone.utc)
    )
    age_days = max(0.0, (ref - created).total_seconds()) / 86400.0
    if age_days < FRESHNESS_FULL_SCORE_MAX_AGE_DAYS:
        return FRESHNESS_MAX_SCORE
    score = FRESHNESS_MAX_SCORE - (FRESHNESS_DECAY_PER_DAY * age_days)
    return max(FRESHNESS_MIN_SCORE, min(FRESHNESS_MAX_SCORE, score))


def graph_distance_to_score(distance: Any, *, max_hops: float = GRAPH_DISTANCE_MAX_HOPS) -> float:
    """Map raw graph hop count to a score in [0, 1]; closer nodes score higher.

    Pre-normalized scores belong in ``graph_distance_score``, not ``graph_distance``.
    """
    numeric = _as_finite_float(distance)
    if numeric is None:
        return MISSING_FACTOR_DEFAULT
    if numeric < 0:
        return 0.0
    capped = min(numeric, max_hops)
    return max(0.0, 1.0 - (capped / max_hops))


def _evidence_strength_to_score(value: Any) -> tuple[float, bool]:
    """Return (score, was_missing). Accepts float 0-1 or contract strength strings."""
    if value is None:
        return MISSING_FACTOR_DEFAULT, True
    numeric = _as_finite_float(value)
    if numeric is not None:
        return normalize_factor(numeric), False
    text = _as_str(value)
    if text is None:
        return MISSING_FACTOR_DEFAULT, True
    mapped = _EVIDENCE_STRENGTH_MAP.get(text.lower())
    if mapped is None:
        return MISSING_FACTOR_DEFAULT, True
    return mapped, False


def _resolve_factor_scores(
    candidate: Mapping[str, Any],
    *,
    reference: datetime | None = None,
) -> tuple[dict[str, float], list[str], list[str]]:
    """Extract normalized factor scores, warnings, and caveats for one candidate."""
    warnings: list[str] = list(candidate.get("warnings") or [])
    caveats: list[str] = []

    scores: dict[str, float] = {}
    missing_flags: list[str] = []

    # source_match
    raw = candidate.get("source_match")
    score, is_missing, is_invalid = _score_numeric_field(raw)
    scores["source_match"] = score
    if is_missing:
        missing_flags.append("source_match")
    elif is_invalid:
        warnings.append("invalid_factor:source_match")

    # graph_distance — prefer graph_distance_score if pre-normalized
    gds_raw = candidate.get("graph_distance_score")
    gd_raw = candidate.get("graph_distance")
    if gds_raw is not None:
        score, is_missing, is_invalid = _score_numeric_field(gds_raw)
        scores["graph_distance"] = score
        if is_missing:
            missing_flags.append("graph_distance")
        elif is_invalid:
            warnings.append("invalid_factor:graph_distance")
    elif gd_raw is not None:
        numeric = _as_finite_float(gd_raw)
        if numeric is None:
            scores["graph_distance"] = MISSING_FACTOR_DEFAULT
            warnings.append("invalid_factor:graph_distance")
        else:
            scores["graph_distance"] = graph_distance_to_score(numeric)
    else:
        scores["graph_distance"] = MISSING_FACTOR_DEFAULT
        missing_flags.append("graph_distance")

    # evidence_strength
    ev_score, ev_missing = _evidence_strength_to_score(candidate.get("evidence_strength"))
    scores["evidence_strength"] = ev_score
    if ev_missing:
        missing_flags.append("evidence_strength")

    # freshness — explicit score, else derive from created_at, else contract default
    fresh_raw = candidate.get("freshness")
    if fresh_raw is None and candidate.get("freshness_score") is not None:
        fresh_raw = candidate.get("freshness_score")
    if fresh_raw is not None:
        score, is_missing, is_invalid = _score_numeric_field(fresh_raw)
        scores["freshness"] = score
        if is_missing:
            missing_flags.append("freshness")
        elif is_invalid:
            warnings.append("invalid_factor:freshness")
    else:
        created_at = _parse_datetime(candidate.get("created_at"))
        if created_at is not None:
            ref = reference
            if ref is None:
                parsed_now = _parse_datetime(cdb_utcnow())
                if parsed_now is None:
                    raise HybridRetrievalRankingError(
                        "reference time required for created_at freshness"
                    )
                ref = parsed_now
            scores["freshness"] = created_at_to_freshness_score(
                created_at, reference=ref
            )
        else:
            scores["freshness"] = FRESHNESS_NO_TIMESTAMP_DEFAULT
            missing_flags.append("freshness")

    # confidence
    conf_raw = candidate.get("confidence")
    score, is_missing, is_invalid = _score_numeric_field(conf_raw)
    scores["confidence"] = score
    if is_missing:
        missing_flags.append("confidence")
    elif is_invalid:
        warnings.append("invalid_factor:confidence")

    # scope_match
    scope_raw = candidate.get("scope_match")
    score, is_missing, is_invalid = _score_numeric_field(scope_raw)
    scores["scope_match"] = score
    if is_missing:
        missing_flags.append("scope_match")
    elif is_invalid:
        warnings.append("invalid_factor:scope_match")

    # memory_trust
    mem_raw = candidate.get("memory_trust")
    if mem_raw is None:
        scores["memory_trust"] = MISSING_FACTOR_DEFAULT
        missing_flags.append("memory_trust")
    else:
        mem_score, mem_missing = _evidence_strength_to_score(mem_raw)
        scores["memory_trust"] = mem_score
        if mem_missing:
            missing_flags.append("memory_trust")

    for name in missing_flags:
        warnings.append(f"missing_factor:{name}")

    if scores["confidence"] < WEAK_CONFIDENCE_THRESHOLD:
        warnings.append("weak_match:low_confidence")
    if _as_bool(candidate.get("inferred")):
        warnings.append("weak_match:inferred_result")
        caveats.append("Result is inferred; verify against repo or live evidence.")

    if candidate.get("vector_score") is not None:
        caveats.append(
            "vector_score present but optional_vector_search is deferred in ranking v1"
        )

    return scores, sorted(set(warnings)), caveats


def _validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    unknown = set(weights) - set(RANKING_FACTORS)
    if unknown:
        raise HybridRetrievalRankingError(
            f"unknown ranking factors: {sorted(unknown)}"
        )
    missing = [f for f in RANKING_FACTORS if f not in weights]
    if missing:
        raise HybridRetrievalRankingError(f"missing ranking factors: {missing}")
    resolved: dict[str, float] = {}
    for factor in RANKING_FACTORS:
        value = _as_finite_float(weights[factor])
        if value is None:
            raise HybridRetrievalRankingError(
                f"ranking weight for {factor} must be a finite number"
            )
        if value < 0:
            raise HybridRetrievalRankingError(
                f"ranking weight for {factor} must be non-negative, got {value}"
            )
        resolved[factor] = value
    total = sum(resolved[f] for f in RANKING_FACTORS)
    if not math.isfinite(total) or abs(total - 1.0) > 1e-6:
        raise HybridRetrievalRankingError(
            f"ranking weights must sum to 1.0, got {total:.6f}"
        )
    return resolved


def _coalesce_weights(weights: Mapping[str, float] | None) -> dict[str, float]:
    """Use defaults only when weights is None; explicit mappings must validate."""
    if weights is None:
        return _validate_weights(DEFAULT_RANKING_WEIGHTS)
    return _validate_weights(weights)


def compute_ranking_explanation(
    candidate: Mapping[str, Any],
    weights: Mapping[str, float] | None = None,
    *,
    query_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute factor scores, weighted contributions, and final score for one candidate."""
    resolved_weights = _coalesce_weights(weights)
    reference = _resolve_reference_time(candidate, query_context)
    factor_scores, warnings, caveats = _resolve_factor_scores(
        candidate, reference=reference
    )

    contributions: dict[str, float] = {
        factor: round(factor_scores[factor] * resolved_weights[factor], 6)
        for factor in RANKING_FACTORS
    }
    final_score = round(sum(contributions.values()), 6)

    explanation: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "factor_scores": {k: round(v, 6) for k, v in factor_scores.items()},
        "weights": dict(resolved_weights),
        "weighted_contributions": contributions,
        "final_score": final_score,
        "warnings": warnings,
        "caveats": caveats,
        "guardrails": list(GUARDRAILS),
    }
    if query_context:
        explanation["query_context"] = dict(query_context)
    return explanation


def _tie_break_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    explanation = item.get("ranking_explanation") or {}
    final_score = explanation.get("final_score", item.get("score", 0.0))
    confidence = (explanation.get("factor_scores") or {}).get(
        "confidence", item.get("confidence", 0.0)
    )
    freshness = (explanation.get("factor_scores") or {}).get(
        "freshness", item.get("freshness", 0.0)
    )
    stable_id = _as_str(item.get("source_ref")) or _as_str(item.get("result_id")) or ""
    return (
        -float(final_score),
        -float(confidence),
        -float(freshness),
        stable_id,
    )


def rank_retrieval_results(
    candidates: Sequence[Mapping[str, Any]],
    *,
    weights: Mapping[str, float] | None = None,
    limit: int | None = None,
    query_context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Rank retrieval candidates with explainable weighted scores (deterministic)."""
    resolved_weights = _coalesce_weights(weights)
    ranked: list[dict[str, Any]] = []

    for candidate in candidates:
        row = dict(candidate)
        explanation = compute_ranking_explanation(
            candidate,
            resolved_weights,
            query_context=query_context,
        )
        row["ranking_explanation"] = explanation
        row["score"] = explanation["final_score"]
        existing_warnings = list(row.get("warnings") or [])
        row["warnings"] = sorted(
            set(existing_warnings) | set(explanation.get("warnings") or [])
        )
        ranked.append(row)

    ranked.sort(key=_tie_break_key)
    if limit is None:
        return ranked
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise HybridRetrievalRankingError("limit must be a non-negative integer or None")
    if limit < 0:
        raise HybridRetrievalRankingError("limit must be non-negative")
    if limit == 0:
        return []
    return ranked[:limit]
