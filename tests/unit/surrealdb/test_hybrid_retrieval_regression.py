"""Hybrid retrieval regression suite (#3777).

Refs #3771. Fixture-backed regression coverage for hybrid retrieval ranking:
BM25/fulltext (source_match proxy), vector/HNSW contract signals, graph-distance
ranking, combined stable order, tie-breakers, and no-silent-drift pins.

In-memory/fixture only — no live SurrealDB or network in standard CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.surrealdb.hybrid_retrieval_ranking import (
    DEFAULT_RANKING_WEIGHTS,
    RANKING_FACTORS,
    compute_ranking_explanation,
    graph_distance_to_score,
    rank_retrieval_results,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_CORPUS_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "surrealdb"
    / "hybrid_retrieval_ranking"
    / "regression_corpus_v1.json"
)
BM25_CONTRACT_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_fulltext_bm25_contract.json"
)
HYBRID_SURQL_FIXTURE = REPO_ROOT / "infrastructure" / "surrealdb" / "hybrid_retrieval_fixtures.surql"
EXTERNAL_REFERENCE_SCAN = (
    REPO_ROOT / "docs" / "surrealdb" / "context-intelligence" / "external-reference-scan.md"
)
VECTOR_PROOF_MODULE = REPO_ROOT / "tools" / "surrealdb" / "graph_vector_proof_cli.py"


def _load_regression_corpus() -> dict[str, Any]:
    return json.loads(REGRESSION_CORPUS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(name="regression_corpus")
def fixture_regression_corpus() -> dict[str, Any]:
    return _load_regression_corpus()


@pytest.fixture(name="ranked_regression")
def fixture_ranked_regression(regression_corpus: dict[str, Any]) -> list[dict[str, Any]]:
    return rank_retrieval_results(
        regression_corpus["candidates"],
        query_context=regression_corpus["query_context"],
    )


# ---------------------------------------------------------------------------
# Corpus provenance / CI safety
# ---------------------------------------------------------------------------


def test_regression_corpus_is_synthetic_without_network(regression_corpus: dict[str, Any]) -> None:
    provenance = regression_corpus["corpus_provenance"]
    assert provenance["origin"] == "synthetic"
    assert provenance["network_required"] is False
    assert provenance["live_surrealdb_required"] is False
    assert "awesome-python" in provenance["structure_inspired_by"]
    assert provenance["license"].startswith("N/A")


def test_regression_corpus_contains_no_secret_indicators(regression_corpus: dict[str, Any]) -> None:
    blob = json.dumps(regression_corpus)
    for indicator in (
        "api_key",
        "api_secret",
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "MEXC_API_KEY",
        "MEXC_API_SECRET",
    ):
        assert indicator not in blob


def test_standard_ci_no_live_db_module_import_only() -> None:
    """Ranking module is pure Python; no SurrealDB SDK or HTTP client imports."""
    import tools.surrealdb.hybrid_retrieval_ranking as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "import surrealdb" not in source
    assert "from surrealdb" not in source
    assert "import requests" not in source
    assert "import httpx" not in source


# ---------------------------------------------------------------------------
# Deterministic ranking regression
# ---------------------------------------------------------------------------


def test_deterministic_ranking_fixture_matches_pinned_order(
    ranked_regression: list[dict[str, Any]],
    regression_corpus: dict[str, Any],
) -> None:
    expected = regression_corpus["expected_ranking"]["order"]
    assert [row["result_id"] for row in ranked_regression] == expected


def test_deterministic_ranking_repeatable(regression_corpus: dict[str, Any]) -> None:
    candidates = regression_corpus["candidates"]
    query_context = regression_corpus["query_context"]
    first = rank_retrieval_results(candidates, query_context=query_context)
    second = rank_retrieval_results(candidates, query_context=query_context)
    assert [r["result_id"] for r in first] == [r["result_id"] for r in second]
    assert [r["score"] for r in first] == [r["score"] for r in second]


def test_no_silent_drift_pinned_scores(
    ranked_regression: list[dict[str, Any]],
    regression_corpus: dict[str, Any],
) -> None:
    pinned = regression_corpus["expected_ranking"]["pinned_scores"]
    for row in ranked_regression:
        result_id = row["result_id"]
        assert row["score"] == pinned[result_id], (
            f"Score drift for {result_id}: got {row['score']}, expected {pinned[result_id]}"
        )


def test_weight_change_would_break_pinned_top_score() -> None:
    """Guards against silent DEFAULT_RANKING_WEIGHTS drift on primary fixture row."""
    corpus = _load_regression_corpus()
    primary = next(
        c for c in corpus["candidates"] if c["result_id"] == "reg-primary-redis"
    )
    explanation = compute_ranking_explanation(
        primary, query_context=corpus["query_context"]
    )
    assert explanation["final_score"] == corpus["expected_ranking"]["pinned_scores"]["reg-primary-redis"]
    assert explanation["weights"] == DEFAULT_RANKING_WEIGHTS


# ---------------------------------------------------------------------------
# BM25 / fulltext signal contract (source_match proxy in ranking v1)
# ---------------------------------------------------------------------------


def test_bm25_signal_contract_source_match_influences_ranking(
    ranked_regression: list[dict[str, Any]],
) -> None:
    primary = next(r for r in ranked_regression if r["result_id"] == "reg-primary-redis")
    secondary = next(
        r for r in ranked_regression if r["result_id"] == "reg-secondary-redis"
    )
    assert primary["ranking_explanation"]["factor_scores"]["source_match"] > secondary[
        "ranking_explanation"
    ]["factor_scores"]["source_match"]
    assert ranked_regression.index(primary) < ranked_regression.index(secondary)


def test_bm25_contract_artifact_declares_bm25_score_function() -> None:
    contract = json.loads(BM25_CONTRACT_PATH.read_text(encoding="utf-8"))
    for cat_name, cat_data in contract.get("indexable_categories", {}).items():
        assert cat_data.get("score_function") == "BM25", (
            f"Category {cat_name} must declare BM25 score_function"
        )


def test_hybrid_surql_fixture_declares_bm25_and_rrf_fields() -> None:
    text = HYBRID_SURQL_FIXTURE.read_text(encoding="utf-8")
    assert "bm25_score" in text
    assert "search::rrf" in text


# ---------------------------------------------------------------------------
# Vector / HNSW contract (fixture-only; deferred weight in ranking v1)
# ---------------------------------------------------------------------------


def test_vector_signal_contract_deferred_in_ranking_v1(
    regression_corpus: dict[str, Any],
) -> None:
    with_vector = next(
        c for c in regression_corpus["candidates"] if c["result_id"] == "reg-tie-aab"
    )
    without_vector = {
        k: v for k, v in with_vector.items() if k != "vector_score"
    }
    score_with = rank_retrieval_results([with_vector])[0]["score"]
    score_without = rank_retrieval_results([without_vector])[0]["score"]
    assert score_with == score_without

    explanation = compute_ranking_explanation(with_vector)
    assert any("deferred" in c for c in explanation["caveats"])


def test_vector_pipeline_contract_module_exists_for_hnsw_proof() -> None:
    assert VECTOR_PROOF_MODULE.exists()
    text = VECTOR_PROOF_MODULE.read_text(encoding="utf-8")
    assert "vector_pipeline_contract" in text
    assert "embedding_dimension" in text


# ---------------------------------------------------------------------------
# Graph distance contract
# ---------------------------------------------------------------------------


def test_graph_distance_contract_closer_nodes_score_higher() -> None:
    assert graph_distance_to_score(0) > graph_distance_to_score(3)
    assert graph_distance_to_score(3) > graph_distance_to_score(9)


def test_graph_distance_contract_influences_combined_ranking(
    ranked_regression: list[dict[str, Any]],
) -> None:
    primary = next(r for r in ranked_regression if r["result_id"] == "reg-primary-redis")
    secondary = next(
        r for r in ranked_regression if r["result_id"] == "reg-secondary-redis"
    )
    irrelevant = next(
        r for r in ranked_regression if r["result_id"] == "reg-irrelevant-trading"
    )
    assert primary["ranking_explanation"]["factor_scores"]["graph_distance"] > secondary[
        "ranking_explanation"
    ]["factor_scores"]["graph_distance"]
    assert secondary["ranking_explanation"]["factor_scores"]["graph_distance"] > irrelevant[
        "ranking_explanation"
    ]["factor_scores"]["graph_distance"]
    assert ranked_regression.index(primary) < ranked_regression.index(secondary)


def test_hybrid_surql_fixture_includes_graph_traversal_input() -> None:
    text = HYBRID_SURQL_FIXTURE.read_text(encoding="utf-8")
    assert "->chunk_mentions_symbol->code_symbol" in text
    assert "$graph" in text


# ---------------------------------------------------------------------------
# Combined ranking + demotion + tie-break
# ---------------------------------------------------------------------------


def test_combined_ranking_contract_stable_hybrid_order(
    ranked_regression: list[dict[str, Any]],
    regression_corpus: dict[str, Any],
) -> None:
    hybrid_rows = [
        r
        for r in ranked_regression
        if r["result_id"] in regression_corpus["expected_ranking"]["order"]
    ]
    assert len(hybrid_rows) == len(regression_corpus["candidates"])
    assert [r["result_id"] for r in hybrid_rows] == regression_corpus["expected_ranking"]["order"]


def test_irrelevant_document_demoted_to_last(
    ranked_regression: list[dict[str, Any]],
) -> None:
    assert ranked_regression[-1]["result_id"] == "reg-irrelevant-trading"
    assert ranked_regression[0]["score"] > ranked_regression[-1]["score"] * 3


def test_tie_breaker_stability_by_source_ref(
    ranked_regression: list[dict[str, Any]],
) -> None:
    tie_ids = [
        r["result_id"]
        for r in ranked_regression
        if r["result_id"].startswith("reg-tie-")
    ]
    assert tie_ids == ["reg-tie-aaa", "reg-tie-aab"]
    tie_a = next(r for r in ranked_regression if r["result_id"] == "reg-tie-aaa")
    tie_b = next(r for r in ranked_regression if r["result_id"] == "reg-tie-aab")
    assert tie_a["score"] == tie_b["score"]


# ---------------------------------------------------------------------------
# External reference documentation
# ---------------------------------------------------------------------------


def test_external_reference_doc_documents_regression_corpus() -> None:
    text = EXTERNAL_REFERENCE_SCAN.read_text(encoding="utf-8")
    assert "regression_corpus_v1.json" in text
    assert "test_hybrid_retrieval_regression.py" in text
    assert "synthetic" in text.lower() or "Synthetic" in text
    assert "CC0-1.0" in text or "awesome-python" in text


def test_ranking_factors_cover_hybrid_contract_surface() -> None:
    assert "source_match" in RANKING_FACTORS
    assert "graph_distance" in RANKING_FACTORS
    assert len(RANKING_FACTORS) == 7
