"""RED discovery anchors for #3484 graph operationalization follow-up."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]

GRAPH_DISCOVERY_ANCHORS: dict[str, tuple[str, ...]] = {
    "knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md": (
        "#3479",
        "#3480",
        "#3484",
        "#3486",
        "#3487",
        "CURRENT_STATUS.md",
        "PR body",
        "local staged files",
        "docs/surrealdb/context-relationship-vocabulary-v0.md",
        "infrastructure/surrealdb/traversal_query_fixtures.surql",
        "#3423",
        "#3445",
    ),
    "knowledge/decisions/README.md": (
        "CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
        "docs/surrealdb/context-relationship-vocabulary-v0.md",
        "infrastructure/surrealdb/traversal_query_fixtures.surql",
    ),
    "docs/onboarding/repo_brain_context_intelligence.md": (
        "CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
        "docs/surrealdb/context-relationship-vocabulary-v0.md",
        "infrastructure/surrealdb/traversal_query_fixtures.surql",
    ),
}


@pytest.mark.parametrize("relative_path,needles", list(GRAPH_DISCOVERY_ANCHORS.items()))
def test_3484_graph_followup_is_canonically_discoverable(
    relative_path: str, needles: tuple[str, ...]
) -> None:
    """#3484 must be discoverable from the #3480 sensory canon and entrypoints."""

    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical file: {relative_path}"
    text = path.read_text(encoding="utf-8")

    for needle in needles:
        assert needle in text, f"{relative_path} missing #3484 graph anchor: {needle!r}"
