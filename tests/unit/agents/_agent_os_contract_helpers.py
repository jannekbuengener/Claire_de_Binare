"""Shared helpers for Agent OS contract tests (#3866, #3867)."""

from __future__ import annotations

import re
from pathlib import Path

# CDB Final Report Rule (.cursor/rules/CDB-Final-Report-Rule.mdc) — session close shape.
FINAL_REPORT_SECTIONS: tuple[str, ...] = (
    "Status:",
    "Scope:",
    "Delivered:",
    "Validation:",
    "GitHub/Repo State:",
    "Boundaries:",
    "Follow-ups:",
    "Limitations:",
)

FINAL_REPORT_STATUS_VALUES: frozenset[str] = frozenset(
    {
        "DONE_MERGED",
        "DONE_NO_PR",
        "HOLD",
        "BLOCKED",
        "PARTIAL",
    }
)

SKILL_SURFACE_REGISTRY_ANCHORS: tuple[str, ...] = (
    "validate_skill_surface_mirror.py",
    "mirrored-from-canon",
    "docs/skills/",
    "cdb-onboarding",
    "codex-only",
    "gh-fix-ci",
    "Bewusste Abweichungen",
    "Skill Surface Mirror Drift Guard",
)

REGISTRY_SURFACE_PATHS: dict[str, str] = {
    "opencode": ".opencode/skills/{name}/SKILL.md",
    "cursor": ".cursor/skills/{name}/SKILL.md",
    "codex": ".codex/cdb_skills/{name}/SKILL.md",
    "claude": ".claude/skills/{name}/SKILL.md",
}

SECTION_16_ONBOARDING_SURFACES: frozenset[str] = frozenset({"opencode", "cursor", "claude"})


def parse_registry_excluded_onboarding_surfaces(registry_text: str) -> frozenset[str]:
    """Return surfaces documented as excluded for cdb-onboarding in Registry §16."""
    # Table row: | cdb-onboarding | Y | — | — | sync | — | alias; codex-only |
    match = re.search(
        r"\|\s*cdb-onboarding\s*\|[^\n]+\n",
        registry_text,
    )
    if match is None:
        return frozenset()
    row = match.group(0)
    excluded: set[str] = set()
    columns = [c.strip() for c in row.strip("|").split("|")]
    # columns: skill, canon, opencode, cursor, codex, claude, notes
    surface_cols = ("opencode", "cursor", "codex", "claude")
    for idx, surface in enumerate(surface_cols, start=2):
        if idx < len(columns) and columns[idx].strip() in {"—", "-", ""}:
            excluded.add(surface)
    return frozenset(excluded)


def final_report_rule_path(repo_root: Path) -> Path:
    return repo_root / ".cursor" / "rules" / "CDB-Final-Report-Rule.mdc"


def skill_surface_registry_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "skills" / "SKILL_SURFACE_REGISTRY.md"
