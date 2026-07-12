"""Stable community-health contracts for Issue #4005."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.markdown_link_utils import extract_relative_links

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
README = REPO_ROOT / "README.md"
SECURITY = REPO_ROOT / ".github" / "SECURITY.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"

CANONICAL_CONTACT = "modusmono.dev@gmail.com"
REMOVED_CONTACT = "buengener@gmail.com"
CONTACT_PLACEHOLDER = "[Security contact - add your email]"
REMOVED_SLA_PATTERNS = (
    "Within 24 hours",
    "Within 72 hours",
    "Weekly until resolved",
    "Critical (7 days)",
    "High (14 days)",
    "Medium (30 days)",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _readme_links() -> set[str]:
    return set(extract_relative_links(_read(README)))


def test_readme_links_to_community_governance_files() -> None:
    links = _readme_links()
    assert "CONTRIBUTING.md" in links
    assert "CODE_OF_CONDUCT.md" in links
    assert "LICENSE" in links
    assert ".github/SECURITY.md" in links


def test_security_policy_has_canonical_contact() -> None:
    content = _read(SECURITY)
    assert CANONICAL_CONTACT in content


def test_security_policy_has_no_contact_placeholder() -> None:
    content = _read(SECURITY)
    assert CONTACT_PLACEHOLDER not in content


def test_security_policy_has_no_removed_active_contact() -> None:
    content = _read(SECURITY)
    assert REMOVED_CONTACT not in content


def test_security_policy_does_not_claim_dev_branch_support() -> None:
    content = _read(SECURITY)
    lowered = content.lower()
    assert "| dev" not in lowered
    assert "dev branch" not in lowered


def test_security_policy_has_no_removed_sla_patterns() -> None:
    content = _read(SECURITY)
    for pattern in REMOVED_SLA_PATTERNS:
        assert pattern not in content


def test_contributing_references_merge_policy_governance() -> None:
    content = _read(CONTRIBUTING)
    assert "docs/runbooks/merge_policy_ci_gate.md" in content
