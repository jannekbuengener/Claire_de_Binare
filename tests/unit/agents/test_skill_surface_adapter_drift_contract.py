"""Skill surface mirror and adapter drift contract tests (#3866).

Wissens-Test / Contract-Test: protects the CDB skill SSOT mirror model
(docs/skills -> surface adapters) and documents allowed adapter exceptions.
Builds on tools/validate_skill_surface_mirror.py (#3643) and
docs/skills/SKILL_SURFACE_REGISTRY.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.agents._agent_os_contract_helpers import (
    REGISTRY_SURFACE_PATHS,
    SECTION_16_ONBOARDING_SURFACES,
    SKILL_SURFACE_REGISTRY_ANCHORS,
    parse_registry_excluded_onboarding_surfaces,
    skill_surface_registry_path,
)
from tools import validate_skill_surface_mirror as guard

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_validator_surfaces_match_registry_section_4() -> None:
    """Adapter path templates stay aligned with SKILL_SURFACE_REGISTRY §4."""
    assert guard.SURFACES == REGISTRY_SURFACE_PATHS


def test_cdb_onboarding_exclusions_match_registry_section_16() -> None:
    """Documented cdb-onboarding adapter exclusions match Registry §16."""
    registry_text = skill_surface_registry_path(REPO_ROOT).read_text(encoding="utf-8")
    registry_excluded = parse_registry_excluded_onboarding_surfaces(registry_text)
    validator_excluded = frozenset(guard.EXCLUDED_ADAPTERS.get("cdb-onboarding", {}))
    assert registry_excluded == SECTION_16_ONBOARDING_SURFACES
    assert validator_excluded == SECTION_16_ONBOARDING_SURFACES
    assert "codex" not in validator_excluded


def test_skill_surface_registry_documents_drift_guard_and_exceptions() -> None:
    """Registry §8.1 anchors the drift guard and documented exceptions (#3866)."""
    text = skill_surface_registry_path(REPO_ROOT).read_text(encoding="utf-8")
    for needle in SKILL_SURFACE_REGISTRY_ANCHORS:
        assert needle in text, f"SKILL_SURFACE_REGISTRY.md missing anchor: {needle!r}"


def test_excluded_adapters_carry_documented_reasons() -> None:
    """Every EXCLUDED_ADAPTERS entry must include a non-empty reason string."""
    for skill, surfaces in guard.EXCLUDED_ADAPTERS.items():
        assert skill, "empty skill key in EXCLUDED_ADAPTERS"
        for surface, reason in surfaces.items():
            assert surface in guard.SURFACES, f"unknown surface {surface!r} for {skill}"
            assert reason.strip(), f"missing exclusion reason for {skill}/{surface}"


def test_real_repo_skill_surface_mirror_passes_ci_gate() -> None:
    """Production repo must have zero skill surface drift (Issue #3866 acceptance)."""
    report = guard.run(REPO_ROOT)
    assert report["status"] == "PASS", (
        f"skill surface drift: mismatches={report['mismatches']} "
        f"missing={report['missing']}"
    )
    assert report["canon_count"] >= 1
    assert report["adapter_count"] >= 1


def test_drift_guard_detects_missing_adapter_and_body_mismatch(tmp_path: Path) -> None:
    """Regression: missing adapter and body drift are both DRIFT_FOUND (#3866)."""
    name = "cdb-contract"
    body = "---\nname: cdb-contract\n---\n\n# body\n"
    header = (
        "<!--\n"
        f"Canonical Skill Source: docs/skills/{name}/SKILL.md\n"
        "Surface: cursor\n"
        "Sync Status: mirrored-from-canon\n"
        "-->\n"
    )
    canon = tmp_path / "docs" / "skills" / name / "SKILL.md"
    canon.parent.mkdir(parents=True)
    canon.write_text(header + body, encoding="utf-8")
    adapter = tmp_path / ".cursor" / "skills" / name / "SKILL.md"
    adapter.parent.mkdir(parents=True)
    adapter.write_text(header + "---\nname: cdb-contract\n---\n\n# tampered\n", encoding="utf-8")
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert report["mismatches"]
