"""Tests for check_jules_ai_reviewer_workflow.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from check_jules_ai_reviewer_workflow import forbid_markers, main, require_markers


def test_current_repo_jules_ai_reviewer_workflow_passes() -> None:
    assert main() == 0


def test_marker_helpers_report_missing_and_forbidden_markers(tmp_path: Path) -> None:
    sample = tmp_path / "ai-review-router.yml"
    sample.write_text(
        "name: Jules AI Reviewer\n" "pull_request_target:\n" "pull-requests: write\n",
        encoding="utf-8",
    )

    missing = require_markers(
        sample,
        [
            "pull_request:",
            "issues: write",
        ],
    )
    forbidden = forbid_markers(sample, ["pull_request_target:", "pull-requests: write"])

    assert len(missing) == 2
    assert any("pull_request:" in item for item in missing)
    assert any("issues: write" in item for item in missing)
    assert len(forbidden) == 2
    assert any("pull_request_target:" in item for item in forbidden)
    assert any("pull-requests: write" in item for item in forbidden)
