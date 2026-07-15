"""Tests for the repository root layout guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.validate_root_layout import (
    classify_tracked_paths,
    git_tracked_paths,
    load_policy,
    validate_layout,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "config/repository/root_layout.json"


def test_current_tracked_root_matches_policy() -> None:
    policy = load_policy(POLICY_PATH)
    directories, files = classify_tracked_paths(git_tracked_paths(REPO_ROOT))

    assert validate_layout(policy, directories, files, repo_root=REPO_ROOT) == []


def test_unapproved_root_entries_fail_closed() -> None:
    policy = load_policy(POLICY_PATH)
    directories, files = classify_tracked_paths(
        ["README.md", "core/app.py", "random-dump/result.json", "notes.tmp"]
    )

    violations = validate_layout(policy, directories, files)
    summaries = {(item.kind, item.path) for item in violations}

    assert ("unexpected directory", "random-dump") in summaries
    assert ("unexpected file", "notes.tmp") in summaries


def test_retired_config_file_does_not_reject_config_directory() -> None:
    policy = load_policy(POLICY_PATH)

    directory_violations = validate_layout(policy, {"config"}, set())
    file_violations = validate_layout(policy, set(), {"config"})

    assert not any(
        item.kind == "retired root entry" and item.path == "config"
        for item in directory_violations
    )
    assert any(
        item.kind == "retired root entry" and item.path == "config"
        for item in file_violations
    )
