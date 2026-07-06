"""Brain Evidence Block agent-wide regression contract tests (#3867).

Contract-Test: required Brain Evidence fields, repo-only fallback, trust
degradation, no DB-backed claims without records, tool_blocked /
insufficient_evidence classification, and final report session-close shape.
Fixtures/in-memory only — no live SurrealDB.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.agents._agent_os_contract_helpers import (
    FINAL_REPORT_SECTIONS,
    FINAL_REPORT_STATUS_VALUES,
    final_report_rule_path,
)
from tests.unit.agents._bootloader_read_order_helpers import REPO_FALLBACK_REASONS
from tools.mcp.context_bridge import (
    _build_brain_evidence_block,
    _normalize_brain_evidence_fields,
    context_briefing_handler,
)
from tools.surrealdb.context_graph_contract import classify_graph_evidence_posture

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

BRAIN_EVIDENCE_REQUIRED_FIELDS = frozenset(
    {
        "brain_source",
        "brain_status",
        "tools_or_queries",
        "records_or_results",
        "repo_crosscheck",
        "impact_on_plan",
        "limitations",
        "context_brain_attempted",
        "context_brain_used",
        "context_available",
        "repo_fallback_used",
        "repo_fallback_reason",
        "context_tool_status",
        "context_trust_level",
        "records_found",
    }
)

CURSOR_BRAIN_EVIDENCE_RULE_ANCHORS = (
    "Brain Evidence",
    "brain_source",
    "brain_status",
    "repo-only",
)

AGENTS_BRAIN_EVIDENCE_EXTENDED_ANCHORS = (
    "repo_fallback_reason",
    "insufficient_evidence",
    "context_brain_attempted",
    "HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED",
    "DB-backed Claims",
)


def _briefing(**extra: object) -> dict:
    result = context_briefing_handler(
        task_id="contract-3867",
        task_scope="Agent OS Brain Evidence regression #3867",
        target_issue="#3867",
        requested_depth="quick",
        operation_mode="read_only",
        **extra,
    )
    assert result["status"] == "ok"
    return result["briefing"]


def test_final_report_rule_defines_required_session_close_sections() -> None:
    """Final report contract anchors for agent session close (#3867 scope)."""
    text = final_report_rule_path(REPO_ROOT).read_text(encoding="utf-8")
    for section in FINAL_REPORT_SECTIONS:
        assert section in text, f"CDB-Final-Report-Rule missing section: {section!r}"
    for status in FINAL_REPORT_STATUS_VALUES:
        assert status in text


def test_cursor_brain_evidence_rule_aligns_with_agents_registry() -> None:
    """Cursor Brain Evidence rule core fields; agents/AGENTS.md holds extended gate."""
    rule_text = (REPO_ROOT / ".cursor" / "rules" / "CDB-Brain-Evidence-Rule.mdc").read_text(
        encoding="utf-8"
    )
    agents_text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    for needle in CURSOR_BRAIN_EVIDENCE_RULE_ANCHORS:
        assert needle in rule_text, f"Brain Evidence rule missing: {needle!r}"
    for needle in CURSOR_BRAIN_EVIDENCE_RULE_ANCHORS:
        if needle == "Brain Evidence":
            assert "Brain Evidence Gate" in agents_text
        else:
            assert needle in agents_text, f"agents/AGENTS.md missing core: {needle!r}"
    for needle in AGENTS_BRAIN_EVIDENCE_EXTENDED_ANCHORS:
        assert needle in agents_text, f"agents/AGENTS.md missing extended: {needle!r}"


def test_repo_only_briefing_never_allows_db_backed_claims() -> None:
    """repo-only + insufficient_evidence must not authorize DB-backed claims (#3867)."""
    briefing = _briefing()
    session = briefing["session_context"]
    block = briefing["brain_evidence_block"]
    loop = briefing["default_sensory_loop"]

    assert session["brain_source"] == "repo-only"
    assert session["brain_status"] == "not-used"
    assert session["repo_fallback_reason"] == "insufficient_evidence"
    assert session["context_available"] is False
    assert session["agent_operating_mode"]["db_claims_allowed"] is False

    boundaries = loop["claim_boundaries"]
    assert boundaries["allow_db_backed_closure_claims"] is False
    assert boundaries["allow_db_backed_roadmap_claims"] is False
    assert boundaries["allow_db_backed_status_claims"] is False

    assert block["brain_source"] == "repo-only"
    assert block["repo_fallback_reason"] == "insufficient_evidence"
    assert "surrealdb-local" not in str(block.get("records_or_results"))


@pytest.mark.parametrize(
    "record_source,record_ids,expected_source,db_allowed",
    [
        ("surrealdb-local", ["evidence_ref:ev-001"], "surrealdb-local", True),
        (None, ["evidence_ref:ev-001"], "repo-only", False),
        ("surrealdb-local", [], "repo-only", False),
    ],
)
def test_db_backed_posture_requires_record_source_and_ids(
    record_source: str | None,
    record_ids: list[str],
    expected_source: str,
    db_allowed: bool,
) -> None:
    """No DB-backed claim without record_source + record IDs (#3867)."""
    posture = classify_graph_evidence_posture(
        db_record_ids=record_ids,
        record_source=record_source,
    )
    assert posture["brain_source"] == expected_source
    assert posture["db_claims_allowed"] is db_allowed


@pytest.mark.parametrize(
    "brain_source,brain_status,operator_trust,records,expected_reason,tool_status",
    [
        ("repo-only", "not-used", "LOW", 0, "insufficient_evidence", "available"),
        ("unavailable", "blocked", "BLOCKED", 0, "tool_blocked", "blocked"),
        ("unavailable", "not-used", "BLOCKED", 0, "unavailable", "absent"),
        ("in_memory", "used", "MEDIUM", 2, "none", "available"),
    ],
)
def test_fallback_reason_enum_matches_agents_matrix(
    brain_source: str,
    brain_status: str,
    operator_trust: str,
    records: int,
    expected_reason: str,
    tool_status: str,
) -> None:
    """tool_blocked / insufficient_evidence / unavailable stay distinct (#3867)."""
    fields = _normalize_brain_evidence_fields(
        brain_source=brain_source,
        brain_status=brain_status,
        operator_trust_level=operator_trust,
        records_found=records,
    )
    assert fields["repo_fallback_reason"] in REPO_FALLBACK_REASONS
    assert fields["repo_fallback_reason"] == expected_reason
    assert fields["context_tool_status"] == tool_status
    if expected_reason == "insufficient_evidence":
        assert fields["repo_fallback_reason"] != "unavailable"


def test_brain_evidence_block_emits_all_agent_os_required_fields() -> None:
    """Briefing Brain Evidence block includes full required field set (#3867)."""
    block = _briefing()["brain_evidence_block"]
    missing = BRAIN_EVIDENCE_REQUIRED_FIELDS - set(block)
    assert not missing, f"missing Brain Evidence fields: {sorted(missing)}"


def test_build_brain_evidence_block_merges_fallback_gate_fields() -> None:
    """_build_brain_evidence_block merges normalized fallback fields."""
    fields = _normalize_brain_evidence_fields(
        brain_source="repo-only",
        brain_status="not-used",
        operator_trust_level="LOW",
        records_found=0,
    )
    block = _build_brain_evidence_block(
        brain_source="repo-only",
        brain_status="not-used",
        brain_evidence_fields=fields,
        required_reads=["agents/AGENTS.md"],
        working_assumptions=[],
        limitations=["contract test"],
        operator_trust_level="LOW",
        missing_evidence_notice=["no_evidence_records_provided"],
        blocking_trust_findings=[],
        records_found=0,
    )
    assert BRAIN_EVIDENCE_REQUIRED_FIELDS.issubset(block.keys())
    assert block["context_available"] is False
    assert block["brain_status"] == "not-used"
