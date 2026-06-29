"""RED_ONLY contract tests for #3489 decision replay and status-proof gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_decision_tools import (
    TOOL_CDB_CONTEXT_DECISION_REPLAY,
    handle_cdb_context_decision_replay,
)

pytestmark = pytest.mark.unit

FIXTURE_PATH = Path("tests/fixtures/surrealdb/decision_mcp/decision_mcp_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _replay(**overrides) -> dict:
    fixture = _load_fixture()
    parameters = {
        **fixture["cases"]["replay_by_decision_id"]["parameters"],
        "decision_events": fixture["decision_events"],
        "known_evidence_ids": fixture["known_evidence_ids"],
        "known_claim_ids": fixture["known_claim_ids"],
        "evidence_summaries": fixture["evidence_summaries"],
        "claim_summaries": fixture["claim_summaries"],
        "stop_conditions": fixture["stop_conditions"],
        **overrides,
    }
    result = handle_cdb_context_decision_replay(
        {"tool": TOOL_CDB_CONTEXT_DECISION_REPLAY, "parameters": parameters}
    )
    assert result["status"] == "ok"
    return result["result"]


def test_replay_requires_machine_readable_status_proof_block() -> None:
    """#3489: replay must separate GitHub, repo, ledger, and brain proof surfaces."""
    replay = _replay()
    status_proof = replay["status_proof_block"]
    assert set(status_proof) >= {"github_live", "repo_live", "ledger", "brain"}


def test_replay_degrades_without_evidence_claim_and_memory_resolution_inputs() -> None:
    """#3489: missing resolution inputs must be surfaced as a replay gate, not refs_only only."""
    replay = _replay(
        known_evidence_ids=[],
        known_claim_ids=[],
        evidence_summaries={},
        claim_summaries={},
    )
    gate = replay["decision_replay_gate"]
    assert gate["status"] in {"degraded", "fail_closed"}
    assert set(gate["missing_inputs"]) >= {
        "evidence_records",
        "claim_records",
        "decision_events",
    }


def test_replay_inherits_brain_evidence_gate_contract_from_3488() -> None:
    """#3489: decision replay must not bypass the machine-readable #3488 brain-evidence gates."""
    replay = _replay()
    block = replay["brain_evidence_block"]
    assert set(block) >= {
        "brain_source",
        "brain_status",
        "context_brain_attempted",
        "context_brain_used",
        "repo_fallback_used",
        "repo_fallback_reason",
        "context_tool_status",
        "context_trust_level",
        "records_found",
    }


def test_issue_state_cannot_be_inferred_from_ledger_or_pr_body_claims() -> None:
    """#3489: ledger- and PR-body-only issue state claims must stay non-proving."""
    replay = _replay(
        status_claims=[
            {
                "surface": "issue_state",
                "sources": ["ledger", "pr_body"],
                "state": "closed",
            }
        ]
    )
    issue_state = replay["status_proof_block"]["github_live"]["issue_state"]
    assert issue_state["proof_status"] == "missing_live_truth"
    assert "ledger_only_issue_state" in issue_state["blocking_findings"]
    assert "pr_body_issue_state" in issue_state["blocking_findings"]


def test_merge_state_does_not_imply_issue_closure_without_closing_reference() -> None:
    """#3489: merge proof and issue-closure proof must remain separate surfaces."""
    replay = _replay(
        status_claims=[
            {
                "surface": "merge_state",
                "state": "merged",
                "closing_reference_present": False,
            }
        ]
    )
    merge_state = replay["status_proof_block"]["github_live"]["merge_state"]
    assert merge_state["issue_closure_inferred"] is False
    assert "missing_closing_reference" in merge_state["blocking_findings"]


def test_replay_can_mark_closure_drift_or_partial_delivery() -> None:
    """#3489: open issue plus repo-delivered surface must be markable as drift/partial delivery."""
    replay = _replay(
        status_claims=[
            {
                "surface": "delivery_reconcile",
                "github_issue_state": "open",
                "repo_delivery_state": "delivered",
            }
        ]
    )
    assert set(replay["closure_drift_markers"]) >= {"closure_drift", "partial_delivery"}


def test_roadmap_status_rejects_local_staged_and_pr_narrative_as_db_backed_claims() -> None:
    """#3489: roadmap state must not become DB-backed from local/staged or PR narrative inputs."""
    replay = _replay(
        status_claims=[
            {
                "surface": "roadmap_state",
                "sources": ["local_staged_files", "pr_narrative"],
                "state": "done",
            }
        ]
    )
    roadmap_state = replay["status_proof_block"]["ledger"]["roadmap_state"]
    assert roadmap_state["db_backed_claim"] is False
    assert "staged_files_non_db_backed" in roadmap_state["blocking_findings"]
    assert "pr_narrative_non_db_backed" in roadmap_state["blocking_findings"]


def test_replay_carries_explicit_no_lr_go_in_addition_to_live_and_echtgeld_guards() -> None:
    """#3489: replay must explicitly forbid LR decisions, not only live/echtgeld ones."""
    replay = _replay()
    semantics = replay["approval_semantics"]
    assert semantics["no_lr_go"] is True
    assert semantics["no_live_go"] is True
    assert semantics["no_echtgeld_go"] is True
