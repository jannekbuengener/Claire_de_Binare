"""RED contract anchors for #3480 Context Brain sensory layer canon."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
SENSORY_LAYER_DOC = "knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md"

CANONICAL_FILES: dict[str, tuple[str, ...]] = {
    SENSORY_LAYER_DOC: (
        "# Context Brain Sensory Layer",
        "Sensorik-Schicht",
        "empfindsamer, nicht schlauer",
        "Sensory -> Evidence -> Action",
        "GitHub > Repo > Context > Memory",
        "CURRENT_STATUS.md",
        "ledger, not live truth",
        "PR body",
        "local staged files",
        "No DB-backed claim",
        "Naehe, Relevanz, Drift, Decisions, Evidence, Memory",
        "keine Autonomie",
        "keine Live-Entscheidung",
        "kein Echtgeld",
        "#3479",
        "#3484",
        "#3486",
        "#3487",
    ),
    "knowledge/decisions/README.md": (
        "CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
    ),
    "docs/onboarding/repo_brain_context_intelligence.md": (
        "CDB_CONTEXT_BRAIN_SENSORY_LAYER.md",
    ),
}


@pytest.mark.parametrize("relative_path,needles", list(CANONICAL_FILES.items()))
def test_context_brain_sensory_layer_contract_anchors(
    relative_path: str, needles: tuple[str, ...]
) -> None:
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical file: {relative_path}"
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, f"{relative_path} missing contract anchor: {needle!r}"
