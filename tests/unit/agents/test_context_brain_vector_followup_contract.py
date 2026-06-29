"""RED discovery anchors for #3486 vector pipeline follow-up."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
VECTOR_PIPELINE_DOC = "docs/surrealdb/context-embedding-pipeline-v0.md"

VECTOR_DISCOVERY_ANCHORS: dict[str, tuple[str, ...]] = {
    "knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md": (
        "#3484",
        "#3486",
        "#3487",
        VECTOR_PIPELINE_DOC,
        "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        "tools/surrealdb/graph_vector_proof_cli.py",
    ),
    "docs/onboarding/repo_brain_context_intelligence.md": (
        "CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
        VECTOR_PIPELINE_DOC,
        "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql",
        "tools/surrealdb/graph_vector_proof_cli.py",
    ),
    VECTOR_PIPELINE_DOC: (
        "#3479",
        "#3484",
        "#3486",
        "#3487",
        "embedding source",
        "model_id",
        "1536",
        "rebuild",
        "doc_chunk.embedding",
        "real CDB chunks",
        "no secrets",
    ),
}


@pytest.mark.parametrize("relative_path,needles", list(VECTOR_DISCOVERY_ANCHORS.items()))
def test_3486_vector_followup_is_canonically_discoverable(
    relative_path: str, needles: tuple[str, ...]
) -> None:
    """#3486 should expose vector pipeline anchors without implementing the slice yet."""

    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical file: {relative_path}"
    text = path.read_text(encoding="utf-8")

    for needle in needles:
        assert needle in text, f"{relative_path} missing #3486 vector anchor: {needle!r}"
