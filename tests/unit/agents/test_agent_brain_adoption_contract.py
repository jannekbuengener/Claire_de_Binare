"""Contract anchors for Phase-2 read-only Agent Brain adoption (#2797 / #2775)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]

CANONICAL_FILES: dict[str, tuple[str, ...]] = {
    "agents/AGENTS.md": (
        "Source priority",
        "brain_source=repo-only",
        "PERSIST_ALLOWED=False",
        "MUTATION_ALLOWED=False",
        "is a ledger, not live truth",
        "CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md",
    ),
    ".cursor/agents/_CDB_SUBAGENT_CONTRACT.md": (
        "Context Brain adoption",
        "Source priority",
        "briefing.session_context",
        "PERSIST_ALLOWED=False",
        "MUTATION_ALLOWED=False",
        "CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md",
    ),
    "agents/OPEN_CODE_AGENTS.md": (
        "Source priority",
        "session_context",
        "PERSIST_ALLOWED=False",
        "MUTATION_ALLOWED=False",
    ),
    "knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md": (
        "read_only_context_brain = conditional",
        "Source priority",
        "repo-only",
        "surrealdb-local",
    ),
}


@pytest.mark.parametrize("relative_path,needles", list(CANONICAL_FILES.items()))
def test_agent_brain_adoption_contract_anchors(
    relative_path: str, needles: tuple[str, ...]
) -> None:
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical file: {relative_path}"
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, f"{relative_path} missing contract anchor: {needle!r}"
