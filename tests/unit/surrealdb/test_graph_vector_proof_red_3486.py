"""RED machine-readable proof contract for #3486 vector pipeline follow-up."""

from __future__ import annotations

import pytest

from tools.surrealdb.graph_vector_proof_cli import _build_evidence

pytestmark = pytest.mark.unit


def test_3486_vector_proof_reports_embedding_pipeline_contract() -> None:
    """#3486 requires more than a toy-vector capability proof."""

    evidence = _build_evidence(
        {
            "available": True,
            "health": {"status": "ok"},
            "version": {"version": "surrealdb-test"},
        },
        {"tables_found": ["doc_chunk", "doc_page"]},
        None,
        {
            "vector_pass": True,
            "chunk_count": 5,
            "queries": [],
        },
        1.0,
    )

    metadata = evidence["report_metadata"]
    assert metadata["proof_type"] == "vector_pipeline_contract"

    contract = metadata["vector_pipeline_contract"]
    assert contract["chunk_source"] == "real_cdb_chunks"
    assert contract["embedding_source_status"] in {"defined", "gap"}
    assert contract["embedding_model_id_status"] in {"defined", "gap"}
    assert contract["embedding_dimension"] == 1536
    assert contract["rebuild_rule_status"] in {"defined", "gap"}
    assert contract["proof_boundaries"] == [
        "no_secrets",
        "no_live_go",
        "no_echtgeld_go",
    ]
