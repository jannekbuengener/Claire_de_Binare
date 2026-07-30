"""Mirror-aware reviewability assessment contracts (#4220)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tools.pr_routing.engine import (
    CandidatePullRequest,
    IssueFacts,
    LockState,
    RoutingDecision,
    assess_candidate_reviewability,
    evaluate_merge_triggers,
    route_issue,
)
from tools.pr_routing.policy import load_policy
from tools.pr_routing.reviewability import (
    assess_reviewability,
    expected_skill_members,
    mapping_content_reader,
)
from tools.validate_skill_surface_mirror import SURFACES

pytestmark = [pytest.mark.unit, pytest.mark.contract]

SHA = "a" * 40
SKILL_BODY = "# Skill\n\nBody for parity.\n"


def _adapter_text(skill: str) -> str:
    return (
        f"<!--\nCanonical Skill Source: docs/skills/{skill}/SKILL.md\n"
        "Surface: test\nSync Status: mirrored-from-canon\n-->\n"
        f"{SKILL_BODY}"
    )


def _skill_paths(skill: str) -> list[str]:
    return list(expected_skill_members(skill))


def _skill_contents(skill: str) -> dict[str, str]:
    contents = {f"docs/skills/{skill}/SKILL.md": SKILL_BODY}
    for surface, template in SURFACES.items():
        path = template.format(name=skill)
        contents[path] = _adapter_text(skill)
    return contents


def _policy():
    return load_policy()


def _issue(**overrides: object) -> IssueFacts:
    values = {
        "number": 4202,
        "title": "[GOVERNANCE] Reconcile agent guidance",
        "labels": frozenset({"governance"}),
        "base_branch": "main",
        "paused": False,
        "objective_key": "pr-flow",
        "contract_keys": ("pr-routing",),
        "risk_flags": ("none",),
    }
    values.update(overrides)
    return IssueFacts(**values)


def _body(*, issue: int = 4202, state: str = "accepting_slices") -> str:
    return f"""<!-- cdb-batch-pr:v1
policy_id: cdb-pr-routing-v1
batch_key: docs-governance
lane: docs-governance
base_branch: main
validation_profile: docs-governance-v1
merge_mode: batch
steward_state: {state}
objective_key: pr-flow
planned_issues: #{issue}
contract_keys: pr-routing
risk_flags: none
-->

## CDB Batch Ledger

| Issue | Status | Commit | Targeted Validation | Risk Class | Restunsicherheit |
| --- | --- | --- | --- | --- | --- |
| #{issue} | SLICE_DELIVERED | {SHA} | unit + contract | governance | none |

Closes #{issue}
"""


def _candidate(**overrides: object) -> CandidatePullRequest:
    values = {
        "number": 4210,
        "title": "governance: batch",
        "head_branch": "batch/docs-governance",
        "base_branch": "main",
        "is_draft": True,
        "body": _body(),
        "lock_state": LockState.UNLOCKED,
        "created_at": datetime(2026, 7, 29, tzinfo=timezone.utc),
        "changed_files": 2,
        "additions": 20,
        "deletions": 5,
        "merge_mode": "batch",
    }
    values.update(overrides)
    return CandidatePullRequest(**values)


def test_ordinary_twenty_files_still_block() -> None:
    paths = [f"docs/runbooks/file_{idx}.md" for idx in range(20)]
    assessment = assess_reviewability(
        physical_changed_files=20,
        additions=10,
        deletions=10,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=paths,
        content_reader=mapping_content_reader({}),
    )
    assert assessment.logical_review_units == 20
    assert assessment.exceeds_files_limit is True
    result = route_issue(
        _policy(),
        _issue(),
        [
            _candidate(
                changed_files=20,
                changed_file_paths=tuple(paths),
                file_contents={},
            )
        ],
    )
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert "REVIEWABILITY_LIMIT_REACHED" in result.incompatibility_reasons


def test_one_canon_plus_four_valid_mirrors_is_one_unit() -> None:
    skill = "cdb-pr-router"
    paths = _skill_paths(skill)
    contents = _skill_contents(skill)
    assessment = assess_reviewability(
        physical_changed_files=5,
        additions=40,
        deletions=0,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=paths,
        content_reader=mapping_content_reader(contents),
    )
    assert assessment.logical_review_units == 1
    assert assessment.physical_changed_files == 5
    assert len(assessment.recognized_mirror_groups) == 1
    assert assessment.recognized_mirror_groups[0].skill == skill
    assert assessment.exceeds_files_limit is False


def test_multiple_valid_skill_groups() -> None:
    skills = ("cdb-pr-router", "cdb-session-close")
    paths: list[str] = []
    contents: dict[str, str] = {}
    for skill in skills:
        paths.extend(_skill_paths(skill))
        contents.update(_skill_contents(skill))
    extras = (
        "docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md",
        "tests/unit/governance/test_example.py",
    )
    paths.extend(extras)
    assessment = assess_reviewability(
        physical_changed_files=len(paths),
        additions=100,
        deletions=5,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=paths,
        content_reader=mapping_content_reader(contents),
    )
    assert assessment.physical_changed_files == 12
    assert assessment.logical_review_units == 4  # 2 groups + 2 extras
    assert {group.skill for group in assessment.recognized_mirror_groups} == set(
        skills
    )


def test_pr_4219_shaped_fixture_routes_without_pr_hardcode() -> None:
    skills = (
        "cdb-batch-merge-conductor",
        "cdb-docs-ops",
        "cdb-drift-reconcile",
        "cdb-pr-router",
        "cdb-session-close",
    )
    paths: list[str] = []
    contents: dict[str, str] = {}
    for skill in skills:
        paths.extend(_skill_paths(skill))
        contents.update(_skill_contents(skill))
    extras = [
        "docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md",
        "knowledge/governance/ISSUE_AND_BRANCH_LIFECYCLE.md",
        "knowledge/logs/sessions/2026-07-30-example.md",
        "tests/unit/governance/test_no_status_tail_pr_contract.py",
    ]
    paths.extend(extras)
    assert len(paths) == 29
    assert "4219" not in "".join(paths)

    candidate = _candidate(
        number=9001,
        changed_files=29,
        additions=349,
        deletions=5,
        changed_file_paths=tuple(paths),
        file_contents=contents,
    )
    assessment = assess_candidate_reviewability(_policy(), candidate)
    assert assessment.physical_changed_files == 29
    assert assessment.logical_review_units == 9
    assert assessment.exceeds_reviewability is False

    result = route_issue(_policy(), _issue(), [candidate])
    assert result.routing_decision is RoutingDecision.ROUTE_TO_EXISTING_BATCH_PR
    assert result.target_pr == 9001
    assert "REVIEWABILITY_LIMIT_REACHED" not in result.incompatibility_reasons


def test_mirror_drift_fails_closed() -> None:
    skill = "cdb-pr-router"
    paths = _skill_paths(skill)
    contents = _skill_contents(skill)
    mirror = ".cursor/skills/cdb-pr-router/SKILL.md"
    contents[mirror] = _adapter_text(skill) + "\n# drifted\n"
    assessment = assess_reviewability(
        physical_changed_files=5,
        additions=10,
        deletions=0,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=paths,
        content_reader=mapping_content_reader(contents),
    )
    assert assessment.logical_review_units == 5
    assert assessment.recognized_mirror_groups == ()
    assert "MIRROR_BODY_DRIFT" in assessment.reason_codes


def test_mirror_without_canon_is_not_free() -> None:
    skill = "cdb-pr-router"
    paths = [
        template.format(name=skill) for template in SURFACES.values()
    ]
    contents = {path: _adapter_text(skill) for path in paths}
    assessment = assess_reviewability(
        physical_changed_files=4,
        additions=8,
        deletions=0,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=paths,
        content_reader=mapping_content_reader(contents),
    )
    assert assessment.logical_review_units == 4
    assert "MIRROR_WITHOUT_CANON" in assessment.reason_codes


def test_diff_limit_remains_effective() -> None:
    paths = _skill_paths("cdb-pr-router")
    contents = _skill_contents("cdb-pr-router")
    assessment = assess_reviewability(
        physical_changed_files=5,
        additions=700,
        deletions=300,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=paths,
        content_reader=mapping_content_reader(contents),
    )
    assert assessment.logical_review_units == 1
    assert assessment.exceeds_diff_limit is True
    assert assessment.exceeds_reviewability is True

    trigger = evaluate_merge_triggers(
        _policy(),
        _candidate(
            changed_files=5,
            additions=700,
            deletions=300,
            changed_file_paths=tuple(paths),
            file_contents=contents,
            created_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
        ),
        observed_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
        explicit_operator_go=False,
        dependency_blocker=False,
        security_or_safety=False,
    )
    assert "SIZE_LIMIT" in trigger.trigger_ids


def test_router_and_merge_trigger_share_result() -> None:
    skills = ("cdb-pr-router", "cdb-session-close")
    paths: list[str] = []
    contents: dict[str, str] = {}
    for skill in skills:
        paths.extend(_skill_paths(skill))
        contents.update(_skill_contents(skill))
    paths.append("docs/runbooks/example.md")
    candidate = _candidate(
        changed_files=len(paths),
        additions=50,
        deletions=5,
        changed_file_paths=tuple(paths),
        file_contents=contents,
    )
    router_assessment = assess_candidate_reviewability(_policy(), candidate)
    merge_assessment = assess_candidate_reviewability(
        _policy(), candidate, limit_source="merge_triggers"
    )
    assert (
        router_assessment.logical_review_units
        == merge_assessment.logical_review_units
        == 3
    )
    assert (
        router_assessment.recognized_mirror_groups
        == merge_assessment.recognized_mirror_groups
    )
    result = route_issue(_policy(), _issue(), [candidate])
    trigger = evaluate_merge_triggers(
        _policy(),
        candidate,
        observed_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
        explicit_operator_go=False,
        dependency_blocker=False,
        security_or_safety=False,
    )
    assert result.routing_decision is RoutingDecision.ROUTE_TO_EXISTING_BATCH_PR
    assert "SIZE_LIMIT" not in trigger.trigger_ids
    assert trigger.reviewability_evidence is not None
    assert (
        trigger.reviewability_evidence["logical_review_units"]
        == router_assessment.logical_review_units
    )


def test_github_inventory_failure_uses_physical_fallback() -> None:
    assessment = assess_reviewability(
        physical_changed_files=29,
        additions=100,
        deletions=10,
        files_limit=20,
        diff_lines_limit=1000,
        changed_paths=None,
        inventory_complete=False,
    )
    assert assessment.logical_review_units == 29
    assert assessment.exceeds_files_limit is True
    assert "REVIEWABILITY_PHYSICAL_FALLBACK" in assessment.reason_codes
