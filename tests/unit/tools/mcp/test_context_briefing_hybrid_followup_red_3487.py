"""RED briefing contract checks for #3487 hybrid retrieval follow-up."""

from __future__ import annotations

import pytest

from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit


def test_3487_briefing_exposes_hybrid_followup_paths_without_authorizing_db_truth() -> None:
    """#3487 should surface hybrid path hints while staying repo-only and non-authorizing."""

    result = context_briefing_handler(
        task_id="cdb-briefing-3487-hybrid-retrieval",
        task_scope="Build RED_ONLY tests for #3487 hybrid retrieval sensory fusion.",
        target_issue="#3487",
        target_paths=[
            "docs/surrealdb/context-hybrid-retrieval-strategy-v1.md",
            "docs/surrealdb/context-relationship-vocabulary-v0.md",
            "docs/surrealdb/context-embedding-pipeline-v0.md",
            "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        ],
        requested_depth="standard",
        operation_mode="read_only",
        working_assumptions=[
            "#3484 graph semantics and #3486 vector pipeline are existing foundations.",
            "This slice remains repo-only and must not claim DB-backed hybrid truth.",
        ],
        limitations=[
            "No DB-backed claim without Tool/Query/Record evidence.",
            "No productive vector search, graph traversal, or hybrid ranking against a DB.",
            "No LR, live, or Echtgeld implication.",
        ],
    )

    assert result["status"] == "ok"
    briefing = result["briefing"]

    assert briefing["approval_semantics"]["no_echtgeld_go"] is True
    assert briefing["session_context"]["brain_source"] == "repo-only"
    assert briefing["session_context"]["brain_status"] == "not-used"

    graph_paths = briefing["graph_paths"]
    assert any(
        path["path_id"] == "issue-3487-hybrid-strategy"
        and path["nodes"]
        == [
            "knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
            "docs/surrealdb/context-hybrid-retrieval-strategy-v1.md",
        ]
        and path["relationships"] == ["canonically_discovers"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
    assert any(
        path["path_id"] == "issue-3487-foundation-chain"
        and path["nodes"]
        == [
            "docs/surrealdb/context-relationship-vocabulary-v0.md",
            "docs/surrealdb/context-embedding-pipeline-v0.md",
            "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        ]
        and path["relationships"]
        == ["builds_on_graph_anchor", "builds_on_vector_anchor"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
    assert any(
        path["path_id"] == "issue-3487-ranking-split"
        and path["nodes"]
        == [
            "docs/surrealdb/context-hybrid-retrieval-strategy-v1.md",
            "tools/surrealdb/hybrid_retrieval_ranking.py",
            "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        ]
        and path["relationships"]
        == ["python_ranking_parallel_to_surrealql_rrf", "verifies_query_contract"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
    assert any(
        path["path_id"] == "issue-3487-context-search-status"
        and path["nodes"] == ["context.search", "tools/mcp/context_bridge.py", "#3487"]
        and path["relationships"]
        == ["status_must_be_classified", "fail_closed_if_vector_missing"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
