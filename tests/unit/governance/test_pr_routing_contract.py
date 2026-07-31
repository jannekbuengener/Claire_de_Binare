"""Contract tests for CDB PR routing and batch-merge policy (#4202)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tools.pr_routing.engine import (
    CandidatePullRequest,
    IssueFacts,
    LockState,
    RoutingDecision,
    evaluate_merge_triggers,
    parse_batch_pr_body,
    route_issue,
)
from tools.pr_routing.policy import load_policy

pytestmark = [pytest.mark.unit, pytest.mark.contract]

SHA = "a" * 40


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


def test_compatible_open_batch_pr_is_reused() -> None:
    result = route_issue(_policy(), _issue(), [_candidate()])
    assert result.routing_decision is RoutingDecision.ROUTE_TO_EXISTING_BATCH_PR
    assert result.target_pr == 4210
    assert result.target_branch == "batch/docs-governance"


def test_no_compatible_pr_creates_new_batch_pr() -> None:
    result = route_issue(_policy(), _issue(), [])
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert result.target_branch == "batch/docs-governance-issue-4202"


def test_missing_issue_compatibility_metadata_creates_new_batch_with_hints() -> None:
    """
    test_id: tc_pr_routing_metadata_defaults_001
    test_type: Bauteil-Test
    rule_ref: ISSUE_COMPATIBILITY_METADATA_INCOMPLETE
    issue_ref: 4228
    """
    issue = _issue(objective_key=None, contract_keys=(), risk_flags=())
    result = route_issue(_policy(), issue, [])
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert "ISSUE_COMPATIBILITY_METADATA_INCOMPLETE" in result.reason_codes
    assert "CREATE_NEW_BATCH_WITH_DEFAULT_METADATA" in result.reason_codes
    assert result.repair_hints
    assert any("objective:issue-4202" in hint for hint in result.repair_hints)
    assert any("risk:none" in hint for hint in result.repair_hints)


def test_missing_metadata_does_not_join_existing_batch() -> None:
    issue = _issue(objective_key=None, contract_keys=(), risk_flags=())
    result = route_issue(_policy(), issue, [_candidate()])
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert "ISSUE_COMPATIBILITY_METADATA_INCOMPLETE" in result.incompatibility_reasons
    assert result.target_pr is None


def test_security_issue_requires_dedicated_pr() -> None:
    issue = _issue(
        title="[SECURITY] rotate compromised credential",
        labels=frozenset({"security"}),
    )
    result = route_issue(_policy(), issue, [])
    assert result.routing_decision is RoutingDecision.CREATE_DEDICATED_PR


def test_pr_flow_uses_fresh_dedicated_branch_not_deleted_override() -> None:
    """
    test_id: tc_pr_routing_deleted_branch_override_001
    test_type: Schutz-Test
    rule_ref: anti-repush / dedicated_branch fallback
    issue_ref: 4228
    """
    issue = _issue(title="[GOVERNANCE][PR-FLOW] Introduce PR Steward")
    result = route_issue(_policy(), issue, [])
    assert result.routing_decision is RoutingDecision.CREATE_DEDICATED_PR
    assert result.target_branch == "dedicated/docs-governance-issue-4202"
    assert result.target_branch != "governance/pr-steward-batch-routing"
    assert "governance/pr-steward-batch-routing" not in (
        _policy().dedicated_branch_overrides.values()
    )


def test_existing_dedicated_pr_is_reused() -> None:
    issue = _issue(
        title="[SECURITY] harden branch protection",
        labels=frozenset({"security"}),
    )
    pr = _candidate(
        body="Refs #4202",
        title="security: harden branch protection",
        merge_mode="dedicated",
        lock_state=LockState.HELD_BY_SELF,
    )
    result = route_issue(_policy(), issue, [pr])
    assert result.routing_decision is RoutingDecision.ROUTE_TO_EXISTING_DEDICATED_PR
    assert result.lock_state == "HELD_BY_SELF"


def test_foreign_or_partial_lock_blocks_routing() -> None:
    for state in (LockState.HELD_BY_FOREIGN, LockState.PARTIAL, LockState.INVALID):
        result = route_issue(_policy(), _issue(), [_candidate(lock_state=state)])
        assert result.routing_decision is RoutingDecision.HOLD_PR_LOCK_CONFLICT


def test_incompatible_lane_is_not_reused() -> None:
    issue = _issue(
        title="[CI] publisher",
        labels=frozenset({"ci"}),
    )
    result = route_issue(_policy(), issue, [_candidate()])
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert "LANE_MISMATCH" in result.incompatibility_reasons


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (
            _body().replace("policy_id: cdb-pr-routing-v1", "policy_id: old"),
            "POLICY_ID_MISMATCH",
        ),
        (
            _body().replace("objective_key: pr-flow", "objective_key: other"),
            "OBJECTIVE_KEY_INCOMPATIBLE",
        ),
        (
            _body().replace("contract_keys: pr-routing", "contract_keys: other"),
            "CONTRACT_KEYS_INCOMPATIBLE",
        ),
        (
            _body().replace("risk_flags: none", "risk_flags: maintenance"),
            "RISK_FLAGS_INCOMPATIBLE",
        ),
    ],
)
def test_contract_metadata_mismatch_prevents_reuse(body: str, reason: str) -> None:
    result = route_issue(_policy(), _issue(), [_candidate(body=body)])
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert reason in result.incompatibility_reasons


def test_reviewability_limit_prevents_reuse() -> None:
    result = route_issue(_policy(), _issue(), [_candidate(changed_files=20)])
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert "REVIEWABILITY_LIMIT_REACHED" in result.incompatibility_reasons


def test_dedicated_pr_lock_conflict_holds() -> None:
    issue = _issue(
        title="[SECURITY] harden branch protection",
        labels=frozenset({"security"}),
    )
    pr = _candidate(
        body="Refs #4202",
        merge_mode="dedicated",
        lock_state=LockState.HELD_BY_FOREIGN,
    )
    result = route_issue(_policy(), issue, [pr])
    assert result.routing_decision is RoutingDecision.HOLD_PR_LOCK_CONFLICT


def test_multiple_compatible_prs_hold_instead_of_guessing() -> None:
    result = route_issue(
        _policy(),
        _issue(),
        [_candidate(number=4210), _candidate(number=4211)],
    )
    assert result.routing_decision is RoutingDecision.HOLD_NO_SAFE_ROUTE
    assert "MULTIPLE_COMPATIBLE_PRS" in result.reason_codes


def test_paused_issue_is_never_routed() -> None:
    result = route_issue(_policy(), _issue(paused=True), [_candidate()])
    assert result.routing_decision is RoutingDecision.HOLD_NO_SAFE_ROUTE
    assert "ISSUE_PAUSED_OR_BLOCKED" in result.reason_codes


def test_marker_ledger_and_closure_are_strictly_parseable() -> None:
    metadata = parse_batch_pr_body(_body())
    assert metadata.lane == "docs-governance"
    assert metadata.planned_issues == (4202,)
    assert metadata.ledger[4202].commit == SHA


@pytest.mark.parametrize(
    "body",
    [
        "<!-- cdb-batch-pr:v2\npolicy_id: x\n-->",
        _body() + _body(),
        _body().replace("Closes #4202", ""),
        _body().replace(SHA, "short-sha"),
        _body().replace("accepting_slices", "unknown-state"),
    ],
)
def test_invalid_marker_or_ledger_fails_closed(body: str) -> None:
    with pytest.raises(ValueError):
        parse_batch_pr_body(body)


def test_invalid_open_batch_metadata_holds_instead_of_creating_duplicate() -> None:
    result = route_issue(
        _policy(),
        _issue(),
        [_candidate(body=_body().replace("cdb-batch-pr:v1", "cdb-batch-pr:v2"))],
    )
    assert result.routing_decision is RoutingDecision.HOLD_NO_SAFE_ROUTE
    assert "PR_METADATA_INVALID" in result.reason_codes


def test_merge_triggers_use_exact_thresholds_and_freeze() -> None:
    candidate = _candidate(
        body=_body(),
        created_at=datetime(2026, 7, 25, tzinfo=timezone.utc),
        changed_files=20,
        additions=600,
        deletions=400,
    )
    trigger = evaluate_merge_triggers(
        _policy(),
        candidate,
        observed_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
        explicit_operator_go=False,
        dependency_blocker=False,
        security_or_safety=False,
    )
    assert trigger.triggered is True
    assert {"BATCH_COMPLETE", "AGE_LIMIT", "SIZE_LIMIT"} <= set(trigger.trigger_ids)
    assert trigger.next_steward_state == "merge_candidate"


def test_merge_candidate_rejects_new_slices() -> None:
    result = route_issue(
        _policy(),
        _issue(),
        [_candidate(body=_body(state="merge_candidate"))],
    )
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR
    assert "PR_NOT_ACCEPTING_SLICES" in result.incompatibility_reasons


@pytest.mark.parametrize(
    ("title", "labels", "expected_lane", "expected_decision"),
    [
        (
            "[AGENTS][DELIVERY] PR-Handoff verpflichtend",
            frozenset(),
            "agent-skills",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[SKILLS][SESSION-CLOSE] harden cleanup",
            frozenset({"skills"}),
            "agent-skills",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[OPS][CI] Resume image PR queue",
            frozenset(),
            "ci-tooling",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[CI][PERF] Fast-CI-Laufzeitprofil",
            frozenset(),
            "ci-tooling",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[META][PARAMETERS] Parameter Correctness",
            frozenset(),
            "docs-governance",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[DATA][PROVENANCE] Content-Fingerprint",
            frozenset(),
            "validation-research",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[REGIME][REPLAY] Offline/assign paths",
            frozenset(),
            "validation-research",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[STRATEGY][PAPER] shadow readiness",
            frozenset(),
            "validation-research",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[PAPER] natural-paper pilot",
            frozenset(),
            "validation-research",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[SCRIPTS][REFACTOR] Legacy scripts",
            frozenset({"scope:infra", "type:refactor"}),
            "ci-tooling",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[INFRA][TLS] TLS-Overlay",
            frozenset({"scope:infra"}),
            "ci-tooling",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "Label-only docs reconciliation",
            frozenset({"scope:docs", "type:docs"}),
            "docs-governance",
            RoutingDecision.CREATE_NEW_BATCH_PR,
        ),
        (
            "[GOVERNANCE][PR-FLOW] cdb-pr-router real conventions",
            frozenset(),
            "docs-governance",
            RoutingDecision.CREATE_DEDICATED_PR,
        ),
        (
            "[RISK][STOP-LOSS] Restart-sicherer Consumer",
            frozenset(),
            "runtime-risk",
            RoutingDecision.CREATE_DEDICATED_PR,
        ),
        (
            "[Security][P0] CVE remediation",
            frozenset({"type:security"}),
            "runtime-risk",
            RoutingDecision.CREATE_DEDICATED_PR,
        ),
    ],
)
def test_real_repo_title_and_label_routing_matrix(
    title: str,
    labels: frozenset[str],
    expected_lane: str,
    expected_decision: RoutingDecision,
) -> None:
    """
    test_id: tc_pr_routing_real_convention_matrix_001
    test_type: Contract-Test
    rule_ref: pr-routing-policy lane matching vs live CDB titles
    issue_ref: 4228
    """
    issue = _issue(
        title=title,
        labels=labels,
        objective_key=None,
        contract_keys=(),
        risk_flags=(),
    )
    result = route_issue(_policy(), issue, [])
    assert result.lane == expected_lane
    assert result.routing_decision is expected_decision
    if expected_decision is RoutingDecision.CREATE_DEDICATED_PR:
        assert result.target_branch == f"dedicated/{expected_lane}-issue-4202"
    else:
        assert result.target_branch == f"batch/{expected_lane}-issue-4202"
        assert result.repair_hints


def test_leftmost_title_token_wins_over_secondary_governance_token() -> None:
    issue = _issue(
        title="[CI][GOVERNANCE] Harden cdb-local-ci",
        labels=frozenset({"scope:ci", "type:chore"}),
        objective_key=None,
        contract_keys=(),
        risk_flags=(),
    )
    result = route_issue(_policy(), issue, [])
    assert result.lane == "ci-tooling"
    assert result.routing_decision is RoutingDecision.CREATE_NEW_BATCH_PR


def test_title_and_label_contradiction_holds_with_repair_hints() -> None:
    issue = _issue(
        title="[AGENTS] delivery contract",
        labels=frozenset({"scope:ci"}),
        objective_key="x",
        contract_keys=("y",),
        risk_flags=("none",),
    )
    result = route_issue(_policy(), issue, [])
    assert result.routing_decision is RoutingDecision.HOLD_NO_SAFE_ROUTE
    assert "LANE_AMBIGUOUS_OR_UNKNOWN" in result.reason_codes
    assert result.repair_hints
