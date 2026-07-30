"""Knowledge contracts for the active PR-routing surfaces (#4202)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_canon_allows_batch_lineage_without_dedicated_final_pr() -> None:
    policy = _read("knowledge/governance/CDB_AGENT_POLICY.md")
    lifecycle = _read("knowledge/governance/ISSUE_AND_BRANCH_LIFECYCLE.md")
    assert "eindeutige Issue-Lineage" in policy
    assert "kein eigener finaler Pull Request" in lifecycle
    assert "Human Authority" in policy


def test_session_router_precedes_branch_and_close_defaults_to_slice_handoff() -> None:
    start = _read("docs/skills/cdb-session-start/SKILL.md")
    close = _read("docs/skills/cdb-session-close/SKILL.md")
    assert "cdb-pr-router" in start
    assert "vor Branch-, Worktree- oder PR-Erstellung" in start
    assert "DONE_SLICE_ADDED_TO_BATCH_PR" in close
    assert "merge: false" in close
    assert "close_issue: false" in close


def test_ci_guard_separates_slice_and_final_head_validation() -> None:
    guard = _read("docs/skills/cdb-ci-cd-guard/SKILL.md")
    assert "Slice Validation" in guard
    assert "Final Batch Head Validation" in guard
    assert "cdb-local-ci" in guard


def test_steward_is_read_only_and_registered() -> None:
    steward = _read(".cursor/agents/cdb-pr-steward.md")
    registry = _read("agents/AGENTS.md")
    assert "readonly: true" in steward
    assert "cdb-pr-steward" in registry


def test_lr_no_go_remains_explicit() -> None:
    runbook = _read("docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md")
    assert "LR bleibt `NO-GO`" in runbook
