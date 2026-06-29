"""RED discovery anchors for #3487 hybrid retrieval follow-up."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
HYBRID_STRATEGY_DOC = "docs/surrealdb/context-hybrid-retrieval-strategy-v1.md"

HYBRID_DISCOVERY_ANCHORS: dict[str, tuple[str, ...]] = {
    "knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md": (
        "#3484",
        "#3486",
        "#3487",
        HYBRID_STRATEGY_DOC,
        "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        "tools/surrealdb/hybrid_retrieval_ranking.py",
        "context.search",
    ),
    "docs/onboarding/repo_brain_context_intelligence.md": (
        "CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
        HYBRID_STRATEGY_DOC,
        "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        "tools/surrealdb/hybrid_retrieval_ranking.py",
        "context.search",
    ),
    HYBRID_STRATEGY_DOC: (
        "#3484",
        "#3486",
        "#3487",
        "context.search",
        "operational",
        "contract-only",
        "gap",
        "fail-closed",
        "tools/mcp/context_bridge.py",
        "tools/surrealdb/hybrid_retrieval_ranking.py",
    ),
}


@pytest.mark.parametrize(
    "relative_path,needles", list(HYBRID_DISCOVERY_ANCHORS.items())
)
def test_3487_hybrid_followup_is_canonically_discoverable(
    relative_path: str, needles: tuple[str, ...]
) -> None:
    """#3487 should expose hybrid retrieval anchors before implementation exists."""

    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical file: {relative_path}"
    text = path.read_text(encoding="utf-8")

    for needle in needles:
        assert needle in text, f"{relative_path} missing #3487 hybrid anchor: {needle!r}"
