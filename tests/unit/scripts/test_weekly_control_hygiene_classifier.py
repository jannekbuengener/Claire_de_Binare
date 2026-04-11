"""Unit tests for .github/scripts/weekly_control_hygiene_classifier.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    module_path = (
        Path(__file__).resolve().parents[3]
        / ".github"
        / "scripts"
        / "weekly_control_hygiene_classifier.py"
    )
    spec = importlib.util.spec_from_file_location(
        "weekly_control_hygiene_classifier", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_branch_obsolescence_marks_cleanup_ready(monkeypatch):
    mod = _load_module()

    def fake_api(args, input_text=None):  # noqa: ARG001
        endpoint = args[0]
        if endpoint.startswith("repos/test/repo/branches"):
            return [
                {"name": "main", "protected": True},
                {"name": "issue-4242-cleanup-candidate", "protected": False},
            ]
        if endpoint.startswith("repos/test/repo/compare/"):
            return {"ahead_by": 0, "behind_by": 3, "status": "behind"}
        raise AssertionError(f"Unexpected API call: {args}")

    def fake_gh(repo, args):  # noqa: ARG001
        if args[:4] == ["pr", "list", "--state", "open"]:
            return []
        if args[:4] == ["pr", "list", "--state", "closed"]:
            return [
                {
                    "number": 9001,
                    "headRefName": "issue-4242-cleanup-candidate",
                    "url": "https://example/pr/9001",
                    "mergedAt": "2026-04-10T00:00:00Z",
                    "closedAt": "2026-04-10T00:00:00Z",
                }
            ]
        raise AssertionError(f"Unexpected gh_json call: {args}")

    monkeypatch.setattr(mod, "gh_api_json", fake_api)
    monkeypatch.setattr(mod, "gh_json", fake_gh)

    candidates = mod.branch_obsolescence_candidates("test/repo", open_issues=[])
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.rule_id == "branch_obsolescence"
    assert candidate.cleanup_state == "cleanup_ready"
    assert candidate.classification == "follow_up_issue"
    assert "manual-approval" in (candidate.issue_labels or [])


def test_branch_obsolescence_stays_unclear_when_issue_open(monkeypatch):
    mod = _load_module()

    def fake_api(args, input_text=None):  # noqa: ARG001
        endpoint = args[0]
        if endpoint.startswith("repos/test/repo/branches"):
            return [
                {"name": "main", "protected": True},
                {"name": "issue-1589-weekly-hygiene", "protected": False},
            ]
        if endpoint.startswith("repos/test/repo/compare/"):
            return {"ahead_by": 0, "behind_by": 2, "status": "behind"}
        raise AssertionError(f"Unexpected API call: {args}")

    def fake_gh(repo, args):  # noqa: ARG001
        if args[:4] == ["pr", "list", "--state", "open"]:
            return []
        if args[:4] == ["pr", "list", "--state", "closed"]:
            return []
        raise AssertionError(f"Unexpected gh_json call: {args}")

    monkeypatch.setattr(mod, "gh_api_json", fake_api)
    monkeypatch.setattr(mod, "gh_json", fake_gh)

    candidates = mod.branch_obsolescence_candidates(
        "test/repo", open_issues=[{"number": 1589}]
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.cleanup_state == "unclear"
    assert candidate.classification == "unclear"
    assert "open issue #1589" in candidate.evidence


def test_local_worktree_boundary_candidate():
    mod = _load_module()
    candidate = mod.local_worktree_boundary_candidate()
    assert candidate.rule_id == "worktree_obsolescence_boundary"
    assert candidate.classification == "report_only"
    assert candidate.cleanup_state == "report_only"


def test_cleanup_state_counts():
    mod = _load_module()
    candidates = [
        mod.Candidate(
            rule_id="r1",
            title="t1",
            classification="report_only",
            confidence=0.5,
            affected_artifacts=[],
            suggested_next_step="n/a",
            evidence="e1",
            cleanup_state="cleanup_ready",
        ),
        mod.Candidate(
            rule_id="r2",
            title="t2",
            classification="report_only",
            confidence=0.5,
            affected_artifacts=[],
            suggested_next_step="n/a",
            evidence="e2",
            cleanup_state="report_only",
        ),
        mod.Candidate(
            rule_id="r3",
            title="t3",
            classification="unclear",
            confidence=0.5,
            affected_artifacts=[],
            suggested_next_step="n/a",
            evidence="e3",
            cleanup_state="unclear",
        ),
    ]
    counts = mod.cleanup_state_counts(candidates)
    assert counts == {"cleanup_ready": 1, "report_only": 1, "unclear": 1}
