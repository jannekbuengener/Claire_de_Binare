"""RED briefing contract checks for #3484 graph operationalization."""

from __future__ import annotations

import pytest

from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit


def test_3484_briefing_exposes_graph_paths_without_upgrading_repo_only_truth() -> None:
    """#3484 should surface graph paths in briefing while staying repo-only and non-authorizing."""

    result = context_briefing_handler(
        task_id="cdb-briefing-3484-graph-paths",
        task_scope="Operationalize #3484 graph relations and traversal semantics.",
        target_issue="#3484",
        target_paths=[
            "docs/surrealdb/context-relationship-vocabulary-v0.md",
            "infrastructure/surrealdb/traversal_query_fixtures.surql",
        ],
        requested_depth="standard",
        operation_mode="read_only",
        working_assumptions=[
            "#3480 sensory canon remains the anchor.",
            "#3486 and #3487 stay out of scope for this slice.",
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
    assert "graph_paths" in briefing
    assert isinstance(briefing["graph_paths"], list)
    assert briefing["graph_paths"], "expected at least one graph path for #3484 scope"
