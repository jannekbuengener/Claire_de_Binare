"""RED_ONLY contract tests for #3492 default sensory loop gates."""

from __future__ import annotations

import pytest

from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit

ALLOWED_NEXT_MOVES = {
    "Plan",
    "RED_ONLY",
    "Implementation",
    "Reconcile",
    "Closeout",
    "Blocked",
}


def _briefing(**extra: object) -> dict:
    result = context_briefing_handler(
        task_id="red-3492",
        task_scope="RED_ONLY issue #3492 default sensory loop gates",
        target_issue="#3492",
        requested_depth="quick",
        operation_mode="write (code/docs)",
        **extra,
    )
    assert result["status"] == "ok"
    return result["briefing"]


def _loop(briefing: dict) -> dict:
    loop = briefing.get("default_sensory_loop")
    assert isinstance(
        loop, dict
    ), "default_sensory_loop contract missing from context.briefing output"
    return loop


def test_loop_models_required_reads_readiness_and_briefing_as_preflight_steps() -> None:
    """#3492: the default sensory loop must model required_reads, readiness, and briefing explicitly."""
    loop = _loop(_briefing())
    preflight_steps = loop.get("preflight_steps")
    assert isinstance(preflight_steps, list), "preflight_steps missing from default_sensory_loop"
    step_names = [step.get("tool") for step in preflight_steps if isinstance(step, dict)]
    assert step_names[:3] == [
        "context.required_reads",
        "context.readiness",
        "context.briefing",
    ]


def test_loop_forwards_machine_readable_brain_evidence_block() -> None:
    """#3492: the loop must carry the normalized #3488 brain-evidence block, not only a sibling field."""
    briefing = _briefing()
    loop = _loop(briefing)
    assert loop.get("brain_evidence_block") == briefing["brain_evidence_block"]


def test_loop_forwards_status_proof_block_and_decision_replay_gate() -> None:
    """#3492: the loop must forward #3489 status-proof and replay-gate surfaces."""
    loop = _loop(_briefing())
    assert "status_proof_block" in loop
    assert "decision_replay_gate" in loop


def test_repo_only_or_low_trust_loop_fails_closed_instead_of_staying_neutral() -> None:
    """#3492: repo-only / LOW trust must visibly degrade the loop outcome."""
    loop = _loop(_briefing())
    assert loop.get("status") in {"degraded", "fail_closed"}
    degraded_reasons = loop.get("degraded_reasons")
    assert isinstance(degraded_reasons, list), "degraded_reasons missing"
    assert any(reason in {"repo_only", "LOW", "insufficient_evidence"} for reason in degraded_reasons)


def test_loop_blocks_db_backed_roadmap_closure_and_status_claims_without_db_evidence() -> None:
    """#3492: repo-only evidence must not authorize DB-backed roadmap, closure, or status claims."""
    loop = _loop(
        _briefing(
            repo_state={
                "working_tree": "dirty",
                "main_state": "stale",
                "delivery_state": "local_only",
            },
            github_state={
                "target_issue": "#3492",
                "roadmap_issue": "#3479",
            },
            working_assumptions=[
                "Roadmap truth is implied by local files.",
                "Closure truth is implied by a branch-local summary.",
                "Status proof is implied without DB-backed evidence.",
            ],
        )
    )
    claim_boundaries = loop.get("claim_boundaries")
    assert isinstance(claim_boundaries, dict), "claim_boundaries missing"
    assert claim_boundaries["allow_db_backed_roadmap_claims"] is False
    assert claim_boundaries["allow_db_backed_closure_claims"] is False
    assert claim_boundaries["allow_db_backed_status_claims"] is False


def test_dirty_or_stale_worktree_becomes_a_risky_condition_without_forcing_write() -> None:
    """#3492: dirty/stale worktree state must be explicit and must not produce a write recommendation."""
    loop = _loop(
        _briefing(
            repo_state={
                "worktree": "dirty",
                "main_sync": "stale",
            }
        )
    )
    risky_conditions = loop.get("risky_conditions")
    assert isinstance(risky_conditions, list), "risky_conditions missing"
    risky_ids = {item.get("id") for item in risky_conditions if isinstance(item, dict)}
    assert {"dirty_worktree", "stale_main"}.issubset(risky_ids)
    next_move = loop.get("next_move")
    assert isinstance(next_move, dict), "next_move missing"
    assert next_move.get("kind") == "Blocked"


def test_loop_separates_trade_capable_stage_from_lr_no_go() -> None:
    """#3492: stage and LR must remain separate proof surfaces."""
    loop = _loop(_briefing())
    status_surfaces = loop.get("status_surfaces")
    assert isinstance(status_surfaces, dict), "status_surfaces missing"
    assert status_surfaces["board_stage"]["value"] == "trade-capable"
    assert status_surfaces["lr_verdict"]["value"] == "NO-GO"
    assert status_surfaces["board_stage"]["implies_live_go"] is False


def test_loop_returns_exactly_one_machine_readable_next_move() -> None:
    """#3492: the loop must decide one bounded next move, not an open-ended list of options."""
    loop = _loop(_briefing())
    next_move = loop.get("next_move")
    assert isinstance(next_move, dict), "next_move missing"
    assert next_move.get("kind") in ALLOWED_NEXT_MOVES
    assert isinstance(next_move.get("reason"), str) and next_move["reason"].strip()
    assert "candidate_next_moves" not in loop


def test_loop_explicitly_marks_3494_end_to_end_proof_as_out_of_scope() -> None:
    """#3492: the default sensory loop slice must not pre-empt the #3494 end-to-end proof slice."""
    loop = _loop(_briefing())
    proof_boundary = loop.get("proof_boundary")
    assert isinstance(proof_boundary, dict), "proof_boundary missing"
    assert proof_boundary["e2e_proof_issue"] == "#3494"
    assert proof_boundary["e2e_proof_scope"] == "excluded"
