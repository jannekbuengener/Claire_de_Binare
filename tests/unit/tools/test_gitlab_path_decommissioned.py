"""#4121 — GitLab secondary path is decommissioned (no active frontdoors)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.validate_root_layout import (
    classify_tracked_paths,
    load_policy,
    validate_layout,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "config/repository/root_layout.json"
MAKEFILE_PATH = REPO_ROOT / "Makefile"

REMOVED_PATHS = (
    ".gitlab-ci.yml",
    "scripts/rollback_pr.sh",
    "scripts/cleanup_branches.sh",
    "scripts/validate_write_zones.sh",
    "infrastructure/scripts/rollback_pr.sh",
    "infrastructure/scripts/cleanup_branches.sh",
    "infrastructure/scripts/validate_write_zones.sh",
)

GITLAB_MAKE_TARGETS = ("rollback", "cleanup", "cleanup-live")


def test_root_layout_policy_does_not_allow_gitlab_ci() -> None:
    policy = load_policy(POLICY_PATH)
    assert ".gitlab-ci.yml" not in policy["approved_files"]
    assert ".gitlab-ci.yml" not in policy["required_files"]


def test_gitlab_ci_at_root_is_unexpected_file() -> None:
    policy = load_policy(POLICY_PATH)
    directories, files = classify_tracked_paths(
        ["README.md", ".gitlab-ci.yml", "core/app.py"]
    )
    violations = validate_layout(policy, directories, files)
    summaries = {(item.kind, item.path) for item in violations}
    assert ("unexpected file", ".gitlab-ci.yml") in summaries


def test_removed_gitlab_frontdoor_files_are_absent() -> None:
    missing = [path for path in REMOVED_PATHS if (REPO_ROOT / path).exists()]
    assert missing == [], f"GitLab frontdoor files still present: {missing}"


def test_makefile_has_no_gitlab_operator_targets() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    for target in GITLAB_MAKE_TARGETS:
        assert not re.search(
            rf"^{re.escape(target)}\s*:",
            text,
            flags=re.MULTILINE,
        ), f"Makefile still defines GitLab target {target!r}"
        assert (
            f"make {target}" not in text
        ), f"Makefile help still advertises make {target}"

    phony_lines = [line for line in text.splitlines() if line.startswith(".PHONY:")]
    joined = " ".join(phony_lines)
    for target in ("rollback", "cleanup"):
        assert (
            re.search(rf"(^|\s){re.escape(target)}(\s|$)", joined) is None
        ), f".PHONY still lists GitLab target {target!r}"


def test_makefile_keeps_local_root_layout_guard() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert re.search(r"^root-layout-guard\s*:", text, flags=re.MULTILINE)
    assert "make root-layout-guard" in text
