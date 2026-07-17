"""Contract tests for the single agent onboarding canon (#4118)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.mcp.context_bridge import create_bridge

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CANON = ROOT / "agents" / "agent_orga" / "AGENT_ONBOARDING.md"
MANIFEST = ROOT / "agents" / "AUTOLOAD_MANIFEST.yaml"

OBSOLETE_MAKE_TARGETS = (
    "agent-status",
    "agent-config-ci",
    "agent-config-local",
    "agent-validate",
    "agent-help",
    "agent-docs",
)

POINTERS = (
    ROOT / "agents" / "AGENT_QUICKSTART.md",
    ROOT / "agents" / "AGENT_SETUP_GUIDE.md",
    ROOT / "agents" / "PLAN_AGENT_DOCS_ORCHESTRATION.md",
    ROOT / "agents" / "agent_orga" / "AGENT_QUICKSTART.md",
    ROOT / "agents" / "agent_orga" / "AGENT_SETUP_GUIDE.md",
    ROOT / "agents" / "agent_orga" / "PLAN_AGENT_DOCS_ORCHESTRATION.md",
)


def test_agents_readme_routes_to_single_onboarding_canon() -> None:
    readme = (ROOT / "agents" / "README.md").read_text(encoding="utf-8")
    assert "agent_orga/AGENT_ONBOARDING.md" in readme
    assert CANON.is_file()


def test_active_onboarding_omits_obsolete_make_targets() -> None:
    text = CANON.read_text(encoding="utf-8")
    for target in OBSOLETE_MAKE_TARGETS:
        assert target not in text


def test_autoload_manifest_paths_and_bridge_inventory_are_current() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    assert data["canonical_onboarding"] == "agents/agent_orga/AGENT_ONBOARDING.md"
    assert "knowledge/CDB_KNOWLEDGE_HUB.md" not in data["shared"]["must_read"]

    for path in data["shared"]["must_read"]:
        assert (ROOT / path).is_file(), path

    for agent in data["agents"].values():
        assert (ROOT / agent["role_file"]).is_file(), agent["role_file"]

    expected = data["context_bridge"]["expected_tool_count"]
    assert expected == 27
    assert len(create_bridge().list_tools()) == expected


def test_legacy_guides_are_pointer_only() -> None:
    for path in POINTERS:
        text = path.read_text(encoding="utf-8")
        assert "Pointer" in text or "POINTER" in text
        assert len(text.splitlines()) <= 20
