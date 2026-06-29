"""RED_ONLY contract tests for #3494 end-to-end sensory proof gates."""

from __future__ import annotations

import pytest

from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit

FOUNDATION_ISSUES = {
    "#3481",
    "#3482",
    "#3488",
    "#3489",
    "#3492",
    "#3493",
}

ALLOWED_NEXT_MOVES = {
    "Close #3479",
    "Continue with follow-up",
    "Blocked",
    "Reconcile",
}


def _briefing(**extra: object) -> dict:
    default_repo_state = {
        "branch": "test-only/3494-end-to-end-sensory-proof",
        "commit": "5e522fdf75e66c07880994e87928f64ec3439722",
        "working_tree": "clean",
        "main_sync": "current",
    }
    default_github_state = {
        "target_issue": "#3494",
        "related_prs": [],
        "open_epics": ["#3479"],
    }
    repo_state = extra.pop("repo_state", default_repo_state)
    github_state = extra.pop("github_state", default_github_state)
    result = context_briefing_handler(
        task_id="red-3494",
        task_scope="RED_ONLY issue #3494 end-to-end sensory proof gates",
        target_issue="#3494",
        requested_depth="quick",
        operation_mode="write (code/docs)",
        repo_state=repo_state,
        github_state=github_state,
        **extra,
    )
    assert result["status"] == "ok"
    return result["briefing"]


def _proof(briefing: dict) -> dict:
    proof = briefing.get("end_to_end_sensory_proof")
    assert isinstance(
        proof, dict
    ), "end_to_end_sensory_proof contract missing from context.briefing output"
    return proof


def test_e2e_proof_references_all_foundation_slices() -> None:
    """#3494: the E2E proof must make all prerequisite slices machine-readable."""
    proof = _proof(_briefing())
    foundations = proof.get("foundation_slices")
    assert isinstance(foundations, list), "foundation_slices missing from end_to_end_sensory_proof"
    issue_refs = {
        item.get("issue")
        for item in foundations
        if isinstance(item, dict) and isinstance(item.get("issue"), str)
    }
    assert FOUNDATION_ISSUES <= issue_refs


def test_e2e_proof_checks_loop_brain_status_and_replay_surfaces_together() -> None:
    """#3494: the proof must join loop, brain-evidence, status-proof, and replay gates."""
    proof = _proof(_briefing())
    assert "default_sensory_loop" in proof
    assert "brain_evidence_block" in proof
    assert "status_proof_block" in proof
    assert "decision_replay_gate" in proof


def test_e2e_proof_prevents_repo_only_or_low_trust_from_escalating_to_db_backed_claims() -> None:
    """#3494: repo-only / LOW / insufficient_evidence / blocked must stay fail-closed."""
    proof = _proof(_briefing())
    escalation_guard = proof.get("claim_escalation_guard")
    assert isinstance(escalation_guard, dict), "claim_escalation_guard missing"
    assert escalation_guard["allow_db_backed_claims"] is False
    degraded_inputs = escalation_guard.get("blocked_inputs")
    assert isinstance(degraded_inputs, list), "blocked_inputs missing"
    assert {"repo_only", "LOW", "insufficient_evidence"} <= set(degraded_inputs)


def test_e2e_proof_keeps_github_repo_ledger_pr_and_local_state_separate() -> None:
    """#3494: GitHub live, repo live, ledger, PR body, brain, and staged files must not blur together."""
    proof = _proof(
        _briefing(
            repo_state={
                "branch": "test-only/3494-end-to-end-sensory-proof",
                "commit": "5e522fdf75e66c07880994e87928f64ec3439722",
                "working_tree": "dirty",
                "main_sync": "stale",
            },
            working_assumptions=[
                "GitHub live truth is implied by a PR body.",
                "Roadmap truth is implied by local staged files.",
                "Ledger wording is enough for closure.",
            ],
        )
    )
    truth_surfaces = proof.get("truth_surfaces")
    assert isinstance(truth_surfaces, dict), "truth_surfaces missing"
    assert set(truth_surfaces) >= {
        "github_live",
        "repo_live",
        "ledger",
        "pr_body",
        "brain",
        "local_staged_files",
    }


def test_e2e_proof_marks_closure_drift_and_partial_delivery() -> None:
    """#3494: the proof must make closure drift and partial delivery machine-readable."""
    proof = _proof(_briefing())
    drift_markers = proof.get("closure_drift_markers")
    assert isinstance(drift_markers, list), "closure_drift_markers missing"
    assert {"closure_drift", "partial_delivery"} <= set(drift_markers)


def test_e2e_proof_remains_non_authorizing_for_lr_live_and_echtgeld() -> None:
    """#3494: the proof is evidence-only and must never create operational authorization."""
    proof = _proof(_briefing())
    approval_semantics = proof.get("approval_semantics")
    assert isinstance(approval_semantics, dict), "approval_semantics missing"
    assert approval_semantics["no_lr_go"] is True
    assert approval_semantics["no_live_go"] is True
    assert approval_semantics["no_echtgeld_go"] is True


def test_e2e_proof_returns_exactly_one_machine_readable_next_move() -> None:
    """#3494: the roadmap proof must converge to one bounded next move."""
    proof = _proof(_briefing())
    next_move = proof.get("next_move")
    assert isinstance(next_move, dict), "next_move missing"
    assert next_move.get("kind") in ALLOWED_NEXT_MOVES
    assert isinstance(next_move.get("reason"), str) and next_move["reason"].strip()
    assert "candidate_next_moves" not in proof


def test_e2e_proof_allows_closing_3479_only_when_all_children_are_closed_without_rest_gaps() -> None:
    """#3494: roadmap closure must stay blocked until all children close and no gaps remain."""
    proof = _proof(_briefing())
    closure_gate = proof.get("roadmap_closure_gate")
    assert isinstance(closure_gate, dict), "roadmap_closure_gate missing"
    assert closure_gate["roadmap_issue"] == "#3479"
    assert closure_gate["allow_close"] is False
    assert set(closure_gate["required_closed_issues"]) >= FOUNDATION_ISSUES | {"#3494"}


def test_e2e_proof_marks_pr_and_issue_cleanup_as_later_autopilot_slice() -> None:
    """#3494: cleanup work must stay out of the proof contract and remain a later slice."""
    proof = _proof(_briefing())
    autopilot_boundary = proof.get("autopilot_boundary")
    assert isinstance(autopilot_boundary, dict), "autopilot_boundary missing"
    assert autopilot_boundary["later_slice_only"] is True
    assert autopilot_boundary["excluded_scope"] == "pr_issue_cleanup"
