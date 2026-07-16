"""Agent-facing knowledge and skill map contract tests (#3871).

Static checks that agents can discover skills, onboarding docs, and canon
paths; docs vs knowledge roles stay separated; archive/historical surfaces
are not promoted as active canon.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.agents._agent_os_contract_helpers import (
    ACTIVE_CANON_PATHS,
    ARCHIVE_ONLY_PATHS,
    HISTORICAL_SNAPSHOT_PATHS,
    KNOWLEDGE_SKILL_MAP_ANCHORS,
    ONBOARDING_PRIMARY_ROUTE,
    SKILL_SURFACE_REGISTRY_ANCHORS,
    SKILLS_LIST_GLOB,
    skill_surface_registry_path,
)
from tools.validate_onboarding_docs import ACTIVE_ONBOARDING_SURFACES, validate_all

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

AGENT_ROOT_SURFACE_MATRIX = REPO_ROOT / "docs" / "onboarding" / "AGENT_ROOT_SURFACE_MATRIX.md"
REPOSITORY_CANON = REPO_ROOT / "docs" / "meta" / "REPOSITORY_CANON.md"
KNOWLEDGE_HUB = REPO_ROOT / "knowledge" / "CDB_KNOWLEDGE_HUB.md"
AGENTS_REGISTRY = REPO_ROOT / "agents" / "AGENTS.md"
AGENTS_ROOT = REPO_ROOT / "AGENTS.md"


# ---------------------------------------------------------------------------
# Skill registry + root surface matrix discoverability
# ---------------------------------------------------------------------------


def test_skill_surface_registry_exists_with_canon_anchors() -> None:
    """Skill SSOT registry is present and names docs/skills/ as canon (#3871)."""
    path = skill_surface_registry_path(REPO_ROOT)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    for anchor in SKILL_SURFACE_REGISTRY_ANCHORS:
        assert anchor in text, f"skill registry missing: {anchor!r}"


def test_agents_registry_points_to_skill_registry_and_surfaces() -> None:
    """Agent entrypoints route to skill registry and root surface matrix."""
    root_text = AGENTS_ROOT.read_text(encoding="utf-8")
    registry_text = AGENTS_REGISTRY.read_text(encoding="utf-8")
    assert "docs/skills/SKILL_SURFACE_REGISTRY.md" in root_text
    assert "AGENT_ROOT_SURFACE_MATRIX.md" in registry_text or "AGENT_ROOT_SURFACE_MATRIX" in root_text
    assert ".cursor/skills/" in root_text or ".cursor/skills/" in registry_text


def test_agent_root_surface_matrix_lists_all_root_surfaces() -> None:
    """Six versioned agent root surfaces are documented for onboarding."""
    text = AGENT_ROOT_SURFACE_MATRIX.read_text(encoding="utf-8")
    for surface in (".claude/", ".codex/", ".cursor/", ".gemini/", ".opencode/", ".vscode/"):
        assert surface in text, f"missing surface row: {surface}"
    assert ONBOARDING_PRIMARY_ROUTE in text


def test_available_skills_list_file_exists() -> None:
    """Agent-facing skills list is discoverable under docs/skills/."""
    matches = sorted(REPO_ROOT.glob(SKILLS_LIST_GLOB))
    assert matches, f"no skills list matching {SKILLS_LIST_GLOB}"
    latest = matches[-1]
    text = latest.read_text(encoding="utf-8")
    assert "cdb-session-start" in text
    assert "docs/skills/" in text


# ---------------------------------------------------------------------------
# Onboarding docs + active surfaces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative_path", ACTIVE_ONBOARDING_SURFACES[:8])
def test_active_onboarding_surfaces_exist_on_disk(relative_path: str) -> None:
    """Core onboarding surfaces from validate_onboarding_docs are present."""
    assert (REPO_ROOT / relative_path).is_file(), f"missing onboarding surface: {relative_path}"


def test_validate_onboarding_docs_passes_for_active_surfaces() -> None:
    """Onboarding doc integrity validator passes on the real repo (#3871)."""
    errors = validate_all(root=REPO_ROOT)
    assert not errors, f"onboarding validation failures: {errors[:5]}"


def test_agents_root_routes_onboarding_intent_to_orchestrator() -> None:
    """Root AGENTS.md quick router exposes onboarding_orchestrator path."""
    text = AGENTS_ROOT.read_text(encoding="utf-8")
    assert ONBOARDING_PRIMARY_ROUTE in text
    assert "onboarding" in text.lower()


# ---------------------------------------------------------------------------
# docs vs knowledge distinction
# ---------------------------------------------------------------------------


def test_claire_de_binare_repository_canon_separates_knowledge_and_docs_domains() -> None:
    """REPOSITORY_CANON maps governance/knowledge vs docs/navigation (#3871)."""
    text = REPOSITORY_CANON.read_text(encoding="utf-8")
    assert "knowledge/governance/" in text
    assert "knowledge/" in text
    assert "docs/" in text
    assert "historical" in text.lower() or "Historical" in text


def test_knowledge_hub_declares_canonical_knowledge_role() -> None:
    """CDB_KNOWLEDGE_HUB is the knowledge-domain entry anchor."""
    assert KNOWLEDGE_HUB.is_file()
    text = KNOWLEDGE_HUB.read_text(encoding="utf-8")
    assert "knowledge" in text.lower()
    assert "governance" in text.lower() or "Governance" in text


def test_agents_registry_read_order_includes_knowledge_and_docs_canon() -> None:
    """Bootloader Read Order spans governance knowledge and docs meta canon."""
    text = AGENTS_REGISTRY.read_text(encoding="utf-8")
    assert "knowledge/governance/" in text
    assert "docs/meta/REPOSITORY_CANON.md" in text


# ---------------------------------------------------------------------------
# active vs archive — archive must not be promoted as active canon
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative_path", ACTIVE_CANON_PATHS)
def test_active_canon_paths_exist(relative_path: str) -> None:
    assert (REPO_ROOT / relative_path).is_file(), f"missing active canon: {relative_path}"


def test_agents_root_declares_archive_not_productive_canon() -> None:
    """docs/archive is historical only, not active canon."""
    text = AGENTS_ROOT.read_text(encoding="utf-8")
    assert "docs/archive/" in text
    assert "kein zweiter Canon" in text


def test_claire_de_binare_repository_canon_marks_archive_noncanonical() -> None:
    """REPOSITORY_CANON keeps historical evidence outside the productive canon."""
    text = REPOSITORY_CANON.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "Historische Einzelartefakte" in text
    assert "keine alternative Repository- oder Dokumentationsquelle" in normalized


def test_historical_snapshots_labeled_in_claire_de_binare_repository_canon() -> None:
    """PROJECT_STATUS / knowledge/CURRENT_STATUS are historical, not SSOT."""
    text = REPOSITORY_CANON.read_text(encoding="utf-8")
    for snap in HISTORICAL_SNAPSHOT_PATHS:
        assert snap in text, f"canon matrix must classify snapshot: {snap}"


def test_skill_registry_archive_row_is_read_only_legacy() -> None:
    """SKILL_SURFACE_REGISTRY § archive row is read-only, not active skill canon."""
    text = skill_surface_registry_path(REPO_ROOT).read_text(encoding="utf-8")
    assert "docs/archive/" in text
    assert "Historische" in text or "historical" in text.lower() or "Read-only" in text


def test_archive_paths_not_listed_as_active_onboarding_surfaces() -> None:
    """Archive tree paths must not appear in ACTIVE_ONBOARDING_SURFACES."""
    for archive_prefix in ARCHIVE_ONLY_PATHS:
        for surface in ACTIVE_ONBOARDING_SURFACES:
            assert not surface.startswith(archive_prefix), (
                f"archive path promoted as active onboarding: {surface}"
            )


# ---------------------------------------------------------------------------
# missing map findings — fail-closed when canon map files absent
# ---------------------------------------------------------------------------


def test_missing_skill_registry_would_fail_contract(tmp_path: Path) -> None:
    """Contract helper detects absent skill registry (missing map finding)."""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    assert not skill_surface_registry_path(fake_root).is_file()


def test_knowledge_skill_map_anchors_present_in_agents_quick_reference() -> None:
    """AGENTS.md quick reference surfaces skills path for agent discovery."""
    text = AGENTS_ROOT.read_text(encoding="utf-8")
    for anchor in KNOWLEDGE_SKILL_MAP_ANCHORS:
        if anchor == "SKILL_SURFACE_REGISTRY":
            assert "SKILL_SURFACE_REGISTRY" in text or "docs/skills/" in text
        elif anchor == "AGENT_ROOT_SURFACE_MATRIX":
            assert "AGENT_ROOT_SURFACE_MATRIX" in text
        else:
            assert anchor in text, f"agents root missing map anchor: {anchor!r}"
