"""Guard the historical boundary of the former mandatory knowledge hub (#4117)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
HUB = ROOT / "knowledge" / "CDB_KNOWLEDGE_HUB.md"
AGENT_REGISTRY = ROOT / "agents" / "AGENTS.md"


def test_knowledge_hub_is_historical_and_not_mandatory() -> None:
    text = HUB.read_text(encoding="utf-8")

    assert "role: historical_reference" in text
    assert "status: historical" in text
    assert "mandatory_read: false" in text
    assert "**Status:** HISTORICAL / REFERENCE ONLY" in text
    assert "External-only agents — superseded" in text


def test_agent_read_order_excludes_historical_hub() -> None:
    text = AGENT_REGISTRY.read_text(encoding="utf-8")
    read_order = text.split("## Read Order", 1)[1].split("## Cursor Subagents", 1)[0]

    assert "knowledge/CDB_KNOWLEDGE_HUB.md" not in "\n".join(
        line for line in read_order.splitlines() if line.lstrip().startswith(tuple("123456789"))
    )
    assert "keine Pflichtlektuere mehr" in read_order


def test_hub_points_to_current_canon_targets() -> None:
    expected = [
        ROOT / "docs" / "meta" / "REPOSITORY_CANON.md",
        ROOT / "CURRENT_STATUS.md",
        ROOT / "docs" / "live-readiness" / "LR-AUDIT-STATUS-2026-03-05.md",
        ROOT / "docs" / "runbooks" / "CONTROL_REGISTER.md",
        ROOT / "agents" / "AGENTS.md",
    ]

    assert all(path.is_file() for path in expected)
