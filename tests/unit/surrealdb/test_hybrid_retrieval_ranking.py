"""Unit tests for hybrid_retrieval_ranking.py — Hybrid Retrieval Ranking v1.

Issues:
    #2799 — [PHASE-2][SURREALDB][SLICE-3] Hybrid retrieval and ranking v1
    Parent: #2778

Scope:
    Fixture-based unit tests. No DB. No MCP. No networking. No writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.surrealdb.hybrid_retrieval_ranking import (
    DEFAULT_RANKING_WEIGHTS,
    FRESHNESS_NO_TIMESTAMP_DEFAULT,
    GUARDRAILS,
    MISSING_FACTOR_DEFAULT,
    RANKING_FACTORS,
    SCHEMA_VERSION,
    HybridRetrievalRankingError,
    compute_ranking_explanation,
    created_at_to_freshness_score,
    graph_distance_to_score,
    normalize_factor,
    rank_retrieval_results,
)

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "surrealdb"
    / "hybrid_retrieval_ranking"
    / "candidates_v1.json"
)


def _load_fixture_candidates() -> list[dict[str, Any]]:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return list(payload["candidates"])


@pytest.mark.unit
def test_default_weights_sum_to_one() -> None:
    total = sum(DEFAULT_RANKING_WEIGHTS[f] for f in RANKING_FACTORS)
    assert abs(total - 1.0) < 1e-9
    assert set(DEFAULT_RANKING_WEIGHTS) == set(RANKING_FACTORS)


@pytest.mark.unit
def test_normalize_factor_clamps_and_missing() -> None:
    assert normalize_factor(1.5) == 1.0
    assert normalize_factor(-0.2) == 0.0
    assert normalize_factor(None) == MISSING_FACTOR_DEFAULT


@pytest.mark.unit
def test_graph_distance_to_score() -> None:
    assert graph_distance_to_score(None) == MISSING_FACTOR_DEFAULT
    assert graph_distance_to_score(0) == 1.0
    assert graph_distance_to_score(1) == 0.9
    assert graph_distance_to_score(3) > graph_distance_to_score(8)


@pytest.mark.unit
def test_zero_hop_graph_distance_ranks_above_one_hop() -> None:
    exact = {
        "result_id": "exact",
        "source_ref": "a:exact",
        "confidence": 0.8,
        "freshness": 0.8,
        "source_match": 0.8,
        "graph_distance": 0,
        "evidence_strength": 0.8,
        "scope_match": 0.8,
        "memory_trust": 0.8,
    }
    one_hop = {**exact, "result_id": "one-hop", "source_ref": "b:one-hop", "graph_distance": 1}
    ranked = rank_retrieval_results([one_hop, exact])
    assert ranked[0]["result_id"] == "exact"


@pytest.mark.unit
def test_limit_zero_returns_empty_list() -> None:
    candidates = _load_fixture_candidates()
    assert rank_retrieval_results(candidates, limit=0) == []


@pytest.mark.unit
def test_limit_none_returns_all_ranked() -> None:
    candidates = _load_fixture_candidates()
    ranked = rank_retrieval_results(candidates, limit=None)
    assert len(ranked) == len(candidates)


@pytest.mark.unit
def test_negative_limit_raises() -> None:
    with pytest.raises(HybridRetrievalRankingError, match="non-negative"):
        rank_retrieval_results([], limit=-1)


@pytest.mark.unit
def test_weighted_ranking_sorts_strong_first() -> None:
    candidates = _load_fixture_candidates()
    ranked = rank_retrieval_results(candidates)
    assert ranked[0]["result_id"] == "res-strong-primary"
    assert ranked[0]["score"] > ranked[1]["score"]


@pytest.mark.unit
def test_evidence_freshness_confidence_influence_score() -> None:
    high = {
        "result_id": "high",
        "source_ref": "a:high",
        "confidence": 0.95,
        "freshness": 0.95,
        "source_match": 0.9,
        "graph_distance": 1,
        "evidence_strength": "strong",
        "scope_match": 0.9,
        "memory_trust": 0.9,
    }
    low = {
        "result_id": "low",
        "source_ref": "b:low",
        "confidence": 0.2,
        "freshness": 0.2,
        "source_match": 0.2,
        "graph_distance": 9,
        "evidence_strength": "weak",
        "scope_match": 0.2,
        "memory_trust": "weak",
    }
    ranked = rank_retrieval_results([low, high])
    assert ranked[0]["result_id"] == "high"
    assert ranked[0]["score"] > ranked[1]["score"]


@pytest.mark.unit
def test_missing_values_conservative_with_warnings() -> None:
    candidates = _load_fixture_candidates()
    sparse = next(c for c in candidates if c["result_id"] == "res-missing-factors")
    explanation = compute_ranking_explanation(sparse)
    assert any(w.startswith("missing_factor:") for w in explanation["warnings"])
    assert "missing_factor:graph_distance" in explanation["warnings"]
    assert explanation["factor_scores"]["freshness"] == FRESHNESS_NO_TIMESTAMP_DEFAULT
    assert explanation["final_score"] < 0.75


@pytest.mark.unit
def test_created_at_derives_freshness_without_missing_warning() -> None:
    candidate = {
        "result_id": "dated",
        "source_ref": "evidence:dated",
        "created_at": "2026-05-31T12:00:00Z",
        "confidence": 0.8,
        "source_match": 0.8,
        "graph_distance": 1,
        "evidence_strength": 0.8,
        "scope_match": 0.8,
        "memory_trust": 0.8,
    }
    explanation = compute_ranking_explanation(
        candidate,
        query_context={"as_of": "2026-06-01T11:00:00Z"},
    )
    assert explanation["factor_scores"]["freshness"] == 1.0
    assert "missing_factor:freshness" not in explanation["warnings"]


@pytest.mark.unit
def test_created_at_freshness_decay_clamped() -> None:
    from datetime import datetime, timezone

    ref = datetime(2026, 6, 20, tzinfo=timezone.utc)
    created = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert created_at_to_freshness_score(created, reference=ref) == 0.1


@pytest.mark.unit
def test_non_finite_numeric_factors_are_not_treated_as_perfect() -> None:
    candidate = {
        "result_id": "nan-match",
        "source_ref": "x:nan",
        "confidence": 0.8,
        "freshness": 0.8,
        "source_match": float("inf"),
        "graph_distance": 1,
        "evidence_strength": 0.8,
        "scope_match": 0.8,
        "memory_trust": 0.8,
    }
    explanation = compute_ranking_explanation(candidate)
    assert explanation["factor_scores"]["source_match"] == MISSING_FACTOR_DEFAULT
    assert "invalid_factor:source_match" in explanation["warnings"]
    assert explanation["final_score"] < 0.9

    nan_candidate = {**candidate, "source_match": 0.8, "confidence": "NaN"}
    nan_explanation = compute_ranking_explanation(nan_candidate)
    assert nan_explanation["factor_scores"]["confidence"] == MISSING_FACTOR_DEFAULT
    assert "invalid_factor:confidence" in nan_explanation["warnings"]


@pytest.mark.unit
def test_weak_inferred_remain_visible_with_warnings() -> None:
    candidates = _load_fixture_candidates()
    ranked = rank_retrieval_results(candidates)
    weak = next(r for r in ranked if r["result_id"] == "res-weak-inferred")
    assert "weak_match:low_confidence" in weak["warnings"]
    assert "weak_match:inferred_result" in weak["warnings"]
    assert any("inferred" in c for c in weak["ranking_explanation"]["caveats"])


@pytest.mark.unit
def test_deterministic_tie_break_and_repeatable_ranking() -> None:
    candidates = _load_fixture_candidates()
    first = rank_retrieval_results(candidates)
    second = rank_retrieval_results(candidates)
    assert [r["result_id"] for r in first] == [r["result_id"] for r in second]
    tie_ids = [r["result_id"] for r in first if r["result_id"].startswith("res-tie-")]
    assert tie_ids == ["res-tie-a", "res-tie-b"]


@pytest.mark.unit
def test_vector_score_optional_no_weight_change() -> None:
    base = {
        "result_id": "base",
        "source_ref": "x:base",
        "confidence": 0.8,
        "freshness": 0.8,
        "source_match": 0.8,
        "graph_distance": 1,
        "evidence_strength": 0.8,
        "scope_match": 0.8,
        "memory_trust": 0.8,
    }
    with_vector = {**base, "vector_score": 0.99}
    score_base = rank_retrieval_results([base])[0]["score"]
    score_with = rank_retrieval_results([with_vector])[0]["score"]
    assert score_base == score_with
    caveat = rank_retrieval_results([with_vector])[0]["ranking_explanation"]["caveats"]
    assert any("deferred" in c for c in caveat)


@pytest.mark.unit
def test_guardrails_in_explanation() -> None:
    explanation = compute_ranking_explanation(_load_fixture_candidates()[0])
    assert set(GUARDRAILS).issubset(set(explanation["guardrails"]))
    assert explanation["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
def test_invalid_custom_weights_rejected() -> None:
    bad = dict(DEFAULT_RANKING_WEIGHTS)
    bad["source_match"] = 0.5
    with pytest.raises(HybridRetrievalRankingError, match="sum to 1.0"):
        rank_retrieval_results([], weights=bad)


@pytest.mark.unit
def test_empty_custom_weights_rejected() -> None:
    with pytest.raises(HybridRetrievalRankingError, match="missing ranking factors"):
        rank_retrieval_results([], weights={})


@pytest.mark.unit
def test_non_finite_custom_weights_rejected() -> None:
    nan_weights = dict(DEFAULT_RANKING_WEIGHTS)
    nan_weights["confidence"] = float("nan")
    with pytest.raises(HybridRetrievalRankingError, match="finite number"):
        rank_retrieval_results([], weights=nan_weights)

    inf_weights = dict(DEFAULT_RANKING_WEIGHTS)
    inf_weights["source_match"] = float("inf")
    with pytest.raises(HybridRetrievalRankingError, match="finite number"):
        rank_retrieval_results([], weights=inf_weights)


@pytest.mark.unit
def test_explanation_structure() -> None:
    explanation = compute_ranking_explanation(_load_fixture_candidates()[0])
    assert set(explanation["factor_scores"]) == set(RANKING_FACTORS)
    assert set(explanation["weights"]) == set(RANKING_FACTORS)
    assert set(explanation["weighted_contributions"]) == set(RANKING_FACTORS)
    assert 0.0 <= explanation["final_score"] <= 1.0
