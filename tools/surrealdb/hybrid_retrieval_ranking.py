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

from typing import Any, Mapping, Sequence

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


def normalize_factor(value: float | None, *, missing_default: float = MISSING_FACTOR_DEFAULT) -> float:
    """Clamp a factor to [0, 1]; missing values use a conservative default."""
    if value is None:
        return missing_default
    return max(0.0, min(1.0, value))


def graph_distance_to_score(distance: float | None, *, max_hops: float = GRAPH_DISTANCE_MAX_HOPS) -> float:
    """Map graph distance (hops) to a score in [0, 1]; closer nodes score higher."""
    if distance is None:
        return MISSING_FACTOR_DEFAULT
    if distance < 0:
        return 0.0
    if distance <= 1.0:
        return normalize_factor(distance)
    capped = min(distance, max_hops)
    return max(0.0, 1.0 - (capped / max_hops))


def _evidence_strength_to_score(value: Any) -> tuple[float, bool]:
    """Return (score, was_missing). Accepts float 0-1 or contract strength strings."""
    if value is None:
        return MISSING_FACTOR_DEFAULT, True
    numeric = _as_float(value)
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
) -> tuple[dict[str, float], list[str], list[str]]:
    """Extract normalized factor scores, warnings, and caveats for one candidate."""
    warnings: list[str] = list(candidate.get("warnings") or [])
    caveats: list[str] = []

    scores: dict[str, float] = {}
    missing_flags: list[str] = []

    # source_match
    raw = candidate.get("source_match")
    if raw is None:
        scores["source_match"] = MISSING_FACTOR_DEFAULT
        missing_flags.append("source_match")
    else:
        scores["source_match"] = normalize_factor(_as_float(raw))

    # graph_distance — prefer graph_distance_score if pre-normalized
    if candidate.get("graph_distance_score") is not None:
        scores["graph_distance"] = normalize_factor(
            _as_float(candidate.get("graph_distance_score"))
        )
    else:
        scores["graph_distance"] = graph_distance_to_score(_as_float(candidate.get("graph_distance")))

    # evidence_strength
    ev_score, ev_missing = _evidence_strength_to_score(candidate.get("evidence_strength"))
    scores["evidence_strength"] = ev_score
    if ev_missing:
        missing_flags.append("evidence_strength")

    # freshness — use freshness field or freshness_score
    fresh_raw = candidate.get("freshness")
    if fresh_raw is None and candidate.get("freshness_score") is not None:
        fresh_raw = candidate.get("freshness_score")
    if fresh_raw is None:
        scores["freshness"] = MISSING_FACTOR_DEFAULT
        missing_flags.append("freshness")
    else:
        scores["freshness"] = normalize_factor(_as_float(fresh_raw))

    # confidence
    conf_raw = candidate.get("confidence")
    if conf_raw is None:
        scores["confidence"] = MISSING_FACTOR_DEFAULT
        missing_flags.append("confidence")
    else:
        scores["confidence"] = normalize_factor(_as_float(conf_raw))

    # scope_match
    scope_raw = candidate.get("scope_match")
    if scope_raw is None:
        scores["scope_match"] = MISSING_FACTOR_DEFAULT
        missing_flags.append("scope_match")
    else:
        scores["scope_match"] = normalize_factor(_as_float(scope_raw))

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
    total = sum(float(weights[f]) for f in RANKING_FACTORS)
    if abs(total - 1.0) > 1e-6:
        raise HybridRetrievalRankingError(
            f"ranking weights must sum to 1.0, got {total:.6f}"
        )
    return {f: float(weights[f]) for f in RANKING_FACTORS}


def compute_ranking_explanation(
    candidate: Mapping[str, Any],
    weights: Mapping[str, float] | None = None,
    *,
    query_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute factor scores, weighted contributions, and final score for one candidate."""
    resolved_weights = _validate_weights(weights or DEFAULT_RANKING_WEIGHTS)
    factor_scores, warnings, caveats = _resolve_factor_scores(candidate)

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
    resolved_weights = _validate_weights(weights or DEFAULT_RANKING_WEIGHTS)
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
    if limit is not None and limit > 0:
        return ranked[:limit]
    return ranked
