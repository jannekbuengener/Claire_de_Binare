"""RED briefing contract checks for #3486 vector pipeline follow-up."""

from __future__ import annotations

import pytest

from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit


def test_3486_briefing_exposes_vector_followup_paths_without_authorizing_db_truth() -> None:
    """#3486 should surface vector path hints while staying repo-only and non-authorizing."""

    result = context_briefing_handler(
        task_id="cdb-briefing-3486-vector-pipeline",
        task_scope="Define and verify #3486 embedding pipeline and vector search path.",
        target_issue="#3486",
        target_paths=[
            "docs/surrealdb/context-embedding-pipeline-v0.md",
            "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
            "tools/surrealdb/graph_vector_proof_cli.py",
        ],
        requested_depth="standard",
        operation_mode="read_only",
        working_assumptions=[
            "#3484 graph discoverability is the existing anchor.",
            "#3487 stays out of scope for this slice.",
        ],
        limitations=[
            "Repo text, CURRENT_STATUS.md, PR body, and local staged files must stay separate truth surfaces.",
            "No DB-backed claim without Tool/Query/Record evidence.",
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
        path["path_id"] == "issue-3486-vector-pipeline-contract"
        and path["nodes"]
        == [
            "knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
            "docs/surrealdb/context-embedding-pipeline-v0.md",
        ]
        and path["relationships"] == ["canonically_discovers"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
    assert any(
        path["path_id"] == "issue-3486-hnsw-fixtures"
        and path["nodes"]
        == [
            "docs/surrealdb/context-embedding-pipeline-v0.md",
            "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        ]
        and path["relationships"] == ["verifies_query_contract"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
    assert any(
        path["path_id"] == "issue-3486-proof-boundary"
        and path["nodes"]
        == [
            "docs/surrealdb/context-embedding-pipeline-v0.md",
            "tools/surrealdb/graph_vector_proof_cli.py",
            "#3445",
        ]
        and path["relationships"] == ["requires_machine_readable_proof", "builds_on"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
    assert any(
        path["path_id"] == "issue-3486-follow-on-boundary"
        and path["nodes"] == ["#3484", "#3486", "#3487"]
        and path["relationships"] == ["builds_on", "later_follow_on"]
        and path["source"] == "repo_only"
        and path["authorizes"] is False
        for path in graph_paths
    )
