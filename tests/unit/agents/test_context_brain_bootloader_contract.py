"""Contract anchors for Context Brain Bootloader enforcement (#3298).

Static checks that agents/AGENTS.md and AGENTS.md contain the hardened
fallback classification rules from #3298.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]

CANONICAL_FILES: dict[str, tuple[str, ...]] = {
    "agents/AGENTS.md": (
        "Context Brain Preflight Gate",
        "Fallback-Klassifikationsmatrix",
        "context_brain_attempted",
        "context_brain_used",
        "repo_fallback_reason",
        "context_tool_status",
        "context_trust_level",
        "records_found",
        "insufficient_evidence",
        "missing_record",
        "tool_blocked",
        "unavailable",
        "HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED",
        "repo_fallback_reason=unavailable",
        "is a ledger, not live truth",
        "GitHub/Repo/Live evidence wins",
        "LR remains NO-GO",
    ),
    "AGENTS.md": (
        "Context Brain first",
        "Fallback-Klassifikation hart",
        "repo_fallback_reason=unavailable",
        "HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED",
        "insufficient_evidence",
        "missing_record",
        "context_tool_status",
        "context_trust_level",
        "records_found",
        "LR status remains NO-GO",
    ),
}


@pytest.mark.parametrize("relative_path,needles", list(CANONICAL_FILES.items()))
def test_context_brain_bootloader_contract_anchors(
    relative_path: str, needles: tuple[str, ...]
) -> None:
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical file: {relative_path}"
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, f"{relative_path} missing contract anchor: {needle!r}"
