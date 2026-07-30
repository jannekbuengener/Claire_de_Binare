"""Surface discovery and mirror parity for PR-acceptance skills (#4207/#4208)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.validate_skill_surface_mirror import strip_header

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]

SKILLS = (
    "cdb-integration-wiring-audit",
    "cdb-pr-gap-classifier",
)

SURFACES = {
    "opencode": ".opencode/skills/{name}/SKILL.md",
    "cursor": ".cursor/skills/{name}/SKILL.md",
    "codex": ".codex/cdb_skills/{name}/SKILL.md",
    "claude": ".claude/skills/{name}/SKILL.md",
}

_HEADER_RE = re.compile(r"<!--(.*?)-->", flags=re.DOTALL)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("skill", SKILLS)
def test_canon_and_mirrors_have_header_and_body_parity(skill: str) -> None:
    canon_path = ROOT / "docs" / "skills" / skill / "SKILL.md"
    canon = canon_path.read_text(encoding="utf-8")
    assert "Sync Status: canonical" in canon
    assert "Surface: docs (canonical)" in canon
    canon_body = strip_header(canon)
    for surface, template in SURFACES.items():
        adapter_path = ROOT / template.format(name=skill)
        assert adapter_path.is_file(), adapter_path
        adapter = adapter_path.read_text(encoding="utf-8")
        header = _HEADER_RE.search(adapter)
        assert header is not None
        header_text = header.group(1)
        assert "mirrored-from-canon" in header_text
        assert f"Surface: {surface}" in header_text
        assert f"docs/skills/{skill}/SKILL.md" in header_text
        assert strip_header(adapter) == canon_body


def test_registry_lists_new_skills_and_counts() -> None:
    registry = _read("docs/skills/SKILL_SURFACE_REGISTRY.md")
    for skill in SKILLS:
        assert skill in registry
    assert "32" in registry
    assert "125" in registry


def test_discovery_surfaces_list_skills() -> None:
    docs_readme = _read("docs/skills/README.md")
    contracts = _read("docs/contracts/README.md")
    agents = _read("AGENTS.md")
    for skill in SKILLS:
        assert skill in docs_readme
        assert skill in agents
    assert "pr_acceptance_skill_family.v1.schema.json" in contracts


@pytest.mark.parametrize(
    "readme",
    [
        ".cursor/skills/README.md",
        ".opencode/skills/README.md",
        ".codex/cdb_skills/README.md",
    ],
)
def test_surface_readmes_list_skills(readme: str) -> None:
    text = _read(readme)
    for skill in SKILLS:
        assert skill in text
