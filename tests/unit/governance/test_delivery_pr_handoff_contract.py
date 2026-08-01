"""Delivery/merge separation contract for normal issue sessions (#4227).

A normal delivery session must terminate at the PR handoff. These contracts
guard the operational agent surfaces a delivery agent actually reads, so that
none of them routes such a session into a merge, the PR-acceptance chain,
final-head CI, or an issue closure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]

SKILL_SURFACE_TEMPLATES = (
    "docs/skills/{name}/SKILL.md",
    ".opencode/skills/{name}/SKILL.md",
    ".cursor/skills/{name}/SKILL.md",
    ".codex/cdb_skills/{name}/SKILL.md",
    ".claude/skills/{name}/SKILL.md",
)

DELIVERY_SKILLS = (
    "cdb-session-start",
    "cdb-issue-to-session-plan",
    "cdb-session-close",
)

ACCEPTANCE_SKILLS = (
    "cdb-integration-wiring-audit",
    "cdb-pr-gap-classifier",
    "cdb-pr-completeness-review",
    "cdb-batch-merge-conductor",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _surfaces(name: str) -> list[tuple[str, str]]:
    return [
        (template.format(name=name), _read(template.format(name=name)))
        for template in SKILL_SURFACE_TEMPLATES
    ]


def test_delivery_session_close_state_is_the_pr_handoff() -> None:
    for path, text in _surfaces("cdb-session-start"):
        assert "DONE_SLICE_ADDED_TO_BATCH_PR" in text, path
        assert "delivered into the routed PR" in text, path
    for path, text in _surfaces("cdb-issue-to-session-plan"):
        assert "Every plan ends in a PR handoff." in text, path
        assert "DONE_SLICE_ADDED_TO_BATCH_PR" in text, path
    for path, text in _surfaces("cdb-session-close"):
        assert "A delivery session closes at the PR handoff" in text, path


def test_compatible_open_pr_has_priority_over_a_new_pr() -> None:
    for path, text in _surfaces("cdb-issue-to-session-plan"):
        assert (
            "compatible open PR always has\n     priority over a new PR" in text
        ), path
    router = _read("docs/skills/cdb-pr-router/SKILL.md")
    assert "ROUTE_TO_EXISTING_BATCH_PR" in router
    assert "ROUTE_TO_EXISTING_DEDICATED_PR" in router
    assert "Never choose between multiple compatible PRs." in router
    runbook = _read("docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md")
    assert "Genau ein kompatibler PR wird gewählt." in runbook


def test_delivery_agent_does_not_merge() -> None:
    for path, text in _surfaces("cdb-session-start"):
        assert "A delivery session never plans a merge" in text, path
    for path, text in _surfaces("cdb-issue-to-session-plan"):
        assert "Never plan a merge" in text, path
    for path, text in _surfaces("cdb-session-close"):
        assert "Do not merge and do not" in text, path
        assert "merge: false" in text, path
    root_pointer = _read("AGENTS.md")
    assert "Der\n  Delivery-Agent mergt nicht" in root_pointer


def test_delivery_agent_does_not_start_the_acceptance_chain() -> None:
    for name in DELIVERY_SKILLS:
        for path, text in _surfaces(name):
            for skill in ACCEPTANCE_SKILLS:
                assert skill in text, f"{path} misses {skill}"
            assert "merge session" in text, path


def test_done_slice_status_is_reachable_without_merge_or_final_ci() -> None:
    for path, text in _surfaces("cdb-session-close"):
        assert "full_fast_ci: false" in text, path
        assert "publish_cdb_local_ci: false" in text, path
        assert "close_issue: false" in text, path
        assert "status: DONE_SLICE_ADDED_TO_BATCH_PR" in text, path
    runbook = _read("docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md")
    assert "status: DONE_SLICE_ADDED_TO_BATCH_PR" in runbook


def test_issue_stays_open_until_a_verified_merge() -> None:
    runbook = _read("docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md")
    assert "Issues bleiben bis Merge offen." in runbook
    for path, text in _surfaces("cdb-session-close"):
        assert "Der Issue bleibt bis zum verifizierten Merge offen." in text, path
    root_pointer = _read("AGENTS.md")
    assert "bleiben bis zum verifizierten Merge offen" in root_pointer


def test_acceptance_and_merge_skills_stay_available_on_every_surface() -> None:
    for name in ACCEPTANCE_SKILLS:
        for template in SKILL_SURFACE_TEMPLATES:
            path = ROOT / template.format(name=name)
            assert path.is_file(), template.format(name=name)
    conductor = _read("docs/skills/cdb-batch-merge-conductor/SKILL.md")
    completeness = _read("docs/skills/cdb-pr-completeness-review/SKILL.md")
    assert "MERGE_CANDIDATE" in completeness
    assert "--squash --delete-branch" in conductor


def test_root_pointer_states_the_delivery_merge_separation() -> None:
    root_pointer = _read("AGENTS.md")
    assert "Delivery und Merge sind getrennte Auftraege (PR-Flow v1)" in root_pointer
    assert "DONE_SLICE_ADDED_TO_BATCH_PR" in root_pointer
    assert "docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md" in root_pointer


def test_policy_and_governance_semantics_are_unchanged() -> None:
    machine_policy = _read("config/governance/pr-routing-policy.v1.yaml")
    assert '"schema_version": "cdb-pr-routing-policy/v1"' in machine_policy
    assert '"policy_id": "cdb-pr-routing-v1"' in machine_policy

    agent_policy = _read("knowledge/governance/CDB_AGENT_POLICY.md")
    assert "kompatiblen offenen Batch-PR wiederverwenden," in agent_policy
    assert "eindeutige Issue-Lineage" in agent_policy

    runbook = _read("docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md")
    assert "mindestens drei gelieferte Issue-Slices," in runbook
    assert "mindestens fünf Kalendertage," in runbook
    assert "Keine Änderung an Branch Protection durch diesen Vertrag." in runbook

    merge_gate = _read("docs/runbooks/merge_policy_ci_gate.md")
    assert "cdb-local-ci" in merge_gate
    assert "`--admin` is **never** a bypass" in merge_gate
