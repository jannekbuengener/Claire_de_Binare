"""RED_ONLY contract tests for #3488 evidence/claim/trust gating."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit

FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _briefing(**extra) -> dict:
    result = context_briefing_handler(
        task_id="red-3488",
        task_scope="RED_ONLY issue #3488 evidence/claim/trust gates",
        target_issue="#3488",
        requested_depth="quick",
        operation_mode="read_only",
        **extra,
    )
    assert result["status"] == "ok"
    return result["briefing"]


def test_repo_only_briefing_exposes_machine_readable_brain_evidence_gate_fields() -> None:
    """#3488: repo-only briefings need the Brain Evidence gate fields in-machine output."""
    session_context = _briefing()["session_context"]
    required = {
        "context_brain_attempted",
        "context_brain_used",
        "context_available",
        "repo_fallback_used",
        "repo_fallback_reason",
        "context_tool_status",
        "context_trust_level",
        "records_found",
    }
    missing = sorted(required - set(session_context))
    assert not missing, f"missing Brain Evidence fields: {missing}"


def test_repo_only_briefing_sets_fail_closed_brain_evidence_defaults() -> None:
    """#3488: repo-only/no-record briefings must classify themselves explicitly."""
    session_context = _briefing()["session_context"]
    assert session_context["brain_source"] == "repo-only"
    assert session_context["brain_status"] == "not-used"
    assert session_context["context_brain_attempted"] is True
    assert session_context["context_brain_used"] is False
    assert session_context["context_available"] is False
    assert session_context["repo_fallback_used"] is True
    assert session_context["repo_fallback_reason"] == "insufficient_evidence"
    assert session_context["context_tool_status"] == "available"
    assert session_context["context_trust_level"] == "none"
    assert session_context["records_found"] == "none"


def test_in_memory_briefing_sets_brain_evidence_gate_fields() -> None:
    """#3488: inline-record briefings must still expose explicit in-memory trust gates."""
    session_context = _briefing(
        memory_records=[{"memory_id": "mem-red-3488", "scope": "wave14", "content": "x"}],
        enrichment_scope="wave14",
    )["session_context"]
    assert session_context["brain_source"] == "in_memory"
    assert session_context["brain_status"] == "used"
    assert session_context["context_brain_attempted"] is True
    assert session_context["context_brain_used"] is True
    assert session_context["context_available"] is True
    assert session_context["repo_fallback_used"] is False
    assert session_context["repo_fallback_reason"] == "none"
    assert session_context["context_tool_status"] == "available"
    assert session_context["context_trust_level"] == "medium"
    assert session_context["records_found"] == 1


def test_briefing_exposes_normalized_brain_evidence_block() -> None:
    """#3488: briefing should return a normalized Brain Evidence block for agent output."""
    briefing = _briefing()
    block = briefing["brain_evidence_block"]
    assert block["brain_source"] == "repo-only"
    assert block["brain_status"] == "not-used"
    assert isinstance(block["tools_or_queries"], list)
    assert isinstance(block["records_or_results"], list)
    assert isinstance(block["repo_crosscheck"], list)
    assert isinstance(block["impact_on_plan"], list)
    assert isinstance(block["limitations"], list)


def test_evidence_only_briefing_marks_missing_claim_decision_and_memory_inputs() -> None:
    """#3488: evidence-only enrichment must not hide missing claim/decision/memory inputs."""
    fx = _load_fixture()
    briefing = _briefing(
        evidence_records=fx["evidence_records"],
        enrichment_scope="wave14",
    )
    notice = briefing["missing_evidence_notice"]
    assert "no_claim_records_provided" in notice
    assert "no_decision_events_provided" in notice
    assert "no_memory_records_provided" in notice


def test_claims_only_briefing_marks_missing_evidence_decision_and_memory_inputs() -> None:
    """#3488: claims-only enrichment must fail closed on missing support records."""
    fx = _load_fixture()
    briefing = _briefing(
        claim_records=fx["claim_records"],
        enrichment_scope="wave14",
    )
    notice = briefing["missing_evidence_notice"]
    assert "no_evidence_records_provided" in notice
    assert "no_decision_events_provided" in notice
    assert "no_memory_records_provided" in notice


def test_memory_only_briefing_marks_missing_evidence_claim_and_decision_inputs() -> None:
    """#3488: memory-only enrichment must not look self-supporting or DB-backed."""
    fx = _load_fixture()
    briefing = _briefing(
        memory_records=fx["memory_records"],
        enrichment_scope="wave14",
    )
    notice = briefing["missing_evidence_notice"]
    assert "no_evidence_records_provided" in notice
    assert "no_claim_records_provided" in notice
    assert "no_decision_events_provided" in notice


def test_repo_github_and_assumption_claims_are_flagged_as_non_db_backed() -> None:
    """#3488: ledger, PR-body, and staged-file style inputs must not count as DB evidence."""
    briefing = _briefing(
        repo_state={
            "branch": "test-only/3488-evidence-claim-mandatory-trust",
            "commit": "abc123",
            "working_tree": "staged-local-files-present",
        },
        github_state={
            "target_issue": "#3488",
            "related_prs": ["#9999"],
            "open_epics": ["#3479"],
        },
        working_assumptions=[
            "DB-backed closure is implied by a PR body summary.",
            "Roadmap progress is implied by local staged files.",
            "Ledger wording is enough for a DB-backed trust claim.",
        ],
    )
    blocking = briefing["blocking_trust_findings"]
    assert any("ledger" in item.lower() for item in blocking)
    assert any("pr_body" in item.lower() for item in blocking)
    assert any("staged" in item.lower() for item in blocking)
    assert any("non_db_backed" in item.lower() for item in blocking)
