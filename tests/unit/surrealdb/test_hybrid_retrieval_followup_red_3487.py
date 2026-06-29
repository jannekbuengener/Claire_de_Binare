"""RED machine-readable follow-up checks for #3487 hybrid retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.surrealdb.hybrid_retrieval_ranking import compute_ranking_explanation

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql"


def test_3487_hybrid_fixture_fuses_graph_vector_and_fulltext() -> None:
    """#3487 requires graph input in addition to BM25 and vector fixtures."""

    text = FIXTURE_PATH.read_text(encoding="utf-8")

    assert "LET $graph =" in text
    assert "->chunk_mentions_symbol->code_symbol" in text
    assert "search::rrf([$vs, $ft, $graph], $hybrid_limit, $rrf_k);" in text


def test_3487_hybrid_ranking_fails_closed_when_vector_is_required_but_missing() -> None:
    """#3487 requires an explicit fail-closed contract when vector evidence is absent."""

    explanation = compute_ranking_explanation(
        {
            "result_id": "bm25-only",
            "source_ref": "doc_chunk:bm25-only",
            "confidence": 0.92,
            "freshness": 0.91,
            "source_match": 0.88,
            "graph_distance": 1,
            "evidence_strength": "strong",
            "scope_match": 0.77,
            "memory_trust": 0.70,
            "retrieval_mode": "full_text",
        },
        query_context={
            "issue_ref": "#3487",
            "hybrid_mode": "surrealql_rrf",
            "vector_required": True,
            "vector_available": False,
            "context_search_status": "contract-only",
        },
    )

    assert "hybrid_gap:vector_required_but_missing" in explanation["warnings"]
    assert "context.search_status:contract-only" in explanation["caveats"]
