"""Governance contract: no immediate post-merge CURRENT_STATUS/ledger-only tail PRs (#4218).

test_id: tc_gov_no_status_tail_pr_001
test_name: no_immediate_post_merge_status_tail_pr
test_type: Agenten-Wissens-Test
cdb_area: governance
rule_ref: ISSUE_AND_BRANCH_LIFECYCLE.md#post-merge-status-ledger
decision_ref: no-post-merge-status-tail
issue_ref: 4218
security_relevant: false
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]

# Phrases that must appear in the canonical surfaces so agents cannot
# re-open an immediate CURRENT_STATUS-/ledger-only Nachlauf-PR after merge.
REQUIRED_FORBIDDEN_MARKERS = (
    "CURRENT_STATUS-only",
    "ledger-only",
    "Nachlauf-PR",
)
REQUIRED_ALLOWED_MARKERS = (
    "vor dem Freeze",
    "docs-governance",
)
REQUIRED_EXCEPTION_MARKERS = (
    "sicherheitskritisch",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_lifecycle_forbids_immediate_status_tail_pr() -> None:
    text = _read("knowledge/governance/ISSUE_AND_BRANCH_LIFECYCLE.md")
    for marker in REQUIRED_FORBIDDEN_MARKERS:
        assert marker in text, f"missing forbidden-path marker in lifecycle: {marker}"
    for marker in REQUIRED_ALLOWED_MARKERS:
        assert marker in text, f"missing allowed-path marker in lifecycle: {marker}"
    for marker in REQUIRED_EXCEPTION_MARKERS:
        assert marker in text, f"missing exception marker in lifecycle: {marker}"


def test_session_close_forbids_immediate_status_tail_pr() -> None:
    text = _read("docs/skills/cdb-session-close/SKILL.md")
    assert "CURRENT_STATUS-only" in text or "ledger-only" in text
    assert "Nachlauf-PR" in text
    assert "vor dem Freeze" in text
    assert "docs-governance" in text
    # Must not re-authorize an immediate dedicated status-only PR after merge.
    assert "kein unmittelbarer" in text.lower() or "kein sofortiger" in text.lower() or "verboten" in text.lower()


def test_pr_routing_runbook_documents_allowed_paths() -> None:
    text = _read("docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md")
    for marker in REQUIRED_FORBIDDEN_MARKERS:
        assert marker in text, f"missing marker in routing runbook: {marker}"
    assert "vor dem Freeze" in text
    assert "docs-governance" in text


def test_docs_ops_and_drift_align_with_no_tail_pr() -> None:
    docs_ops = _read("docs/skills/cdb-docs-ops/SKILL.md")
    drift = _read("docs/skills/cdb-drift-reconcile/SKILL.md")
    assert "Nachlauf-PR" in docs_ops or "CURRENT_STATUS-only" in docs_ops
    assert "docs-governance" in docs_ops
    assert "Nachlauf-PR" in drift or "CURRENT_STATUS-only" in drift


def test_router_and_conductor_surfaces_mention_policy() -> None:
    router = _read("docs/skills/cdb-pr-router/SKILL.md")
    conductor = _read("docs/skills/cdb-batch-merge-conductor/SKILL.md")
    assert "CURRENT_STATUS-only" in router or "Nachlauf-PR" in router
    assert "vor dem Freeze" in conductor or "Freeze" in conductor
    assert "CURRENT_STATUS" in conductor or "Ledger" in conductor
