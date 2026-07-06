"""Brain Evidence Block contract tests (#3774).

Refs #3771. Consolidates fail-closed Brain Evidence gate rules: DB-backed claims
require real tool/query/record evidence; caller-supplied brain fields are not
evidence; repo-only/LOW/insufficient_evidence must not authorize DB-backed
closure, roadmap, or status claims. Fixture/in-memory only — no live SurrealDB.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.mcp.context_bridge import (
    _build_brain_evidence_block,
    _normalize_brain_evidence_fields,
    context_briefing_handler,
)
from tools.surrealdb.claim_evidence_at_rest import (
    ClaimEvidenceAtRestError,
    reject_caller_metadata_as_evidence,
)
from tools.surrealdb.context_graph_contract import (
    classify_graph_evidence_posture,
)
from tools.surrealdb.db_record_evidence_contract import (
    build_example_claim,
    classify_trust,
    compute_determinism_hash,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")

BRAIN_EVIDENCE_BLOCK_FIELDS = frozenset(
    {
        "brain_source",
        "brain_status",
        "tools_or_queries",
        "records_or_results",
        "repo_crosscheck",
        "impact_on_plan",
        "limitations",
    }
)

FALLBACK_GATE_FIELDS = frozenset(
    {
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

AGENTS_BRAIN_EVIDENCE_ANCHORS = (
    "Brain Evidence Gate",
    "brain_source: surrealdb-local",
    "brain_source=repo-only",
    "brain_status=not-used",
    "context_brain_attempted",
    "context_brain_used",
    "context_available",
    "repo_fallback_used",
    "repo_fallback_reason",
    "context_tool_status",
    "context_trust_level",
    "records_found",
    "insufficient_evidence",
    "HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED",
    "caller-supplied",
    "metadata.source",
)


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _briefing(**extra: object) -> dict[str, Any]:
    result = context_briefing_handler(
        task_id="contract-3774",
        task_scope="RED_ONLY issue #3774 Brain Evidence block contract tests",
        target_issue="#3774",
        requested_depth="quick",
        operation_mode="read_only",
        **extra,
    )
    assert result["status"] == "ok"
    return result["briefing"]


def _session_context(briefing: dict[str, Any]) -> dict[str, Any]:
    return briefing["session_context"]


def _brain_block(briefing: dict[str, Any]) -> dict[str, Any]:
    return briefing["brain_evidence_block"]


def _sensory_loop(briefing: dict[str, Any]) -> dict[str, Any]:
    loop = briefing.get("default_sensory_loop")
    assert isinstance(loop, dict)
    return loop


# ---------------------------------------------------------------------------
# surrealdb-local only with record evidence
# ---------------------------------------------------------------------------


def test_surrealdb_local_only_with_record_evidence_fixtures() -> None:
    """brain_source=surrealdb-local requires record_source + record IDs."""
    posture = classify_graph_evidence_posture(
        db_record_ids=["evidence_ref:ev-001"],
        record_source="surrealdb-local",
    )
    assert posture["brain_source"] == "surrealdb-local"
    assert posture["brain_status"] == "partial"
    assert posture["db_claims_allowed"] is True

    without_source = classify_graph_evidence_posture(
        db_record_ids=["evidence_ref:ev-001"],
        record_source=None,
    )
    assert without_source["brain_source"] == "repo-only"
    assert without_source["db_claims_allowed"] is False


def test_surrealdb_local_briefing_requires_adapter_metadata_not_caller_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DB-backed briefing posture needs adapter metadata, not caller brain_source."""
    monkeypatch.setattr(
        "tools.mcp.context_evidence_memory_tools.handle_cdb_context_trust_summary",
        lambda request: {
            "tool": "cdb_context_trust_summary",
            "status": "ok",
            "result": {
                "operator_trust_level": "MEDIUM",
                "trust_level": "medium",
                "composite_score": 0.75,
                "blocking_trust_findings": [],
                "stale_flags": [],
                "limitations": [],
            },
            "metadata": {
                "query_time_ms": 0,
                "source": "surrealdb-local",
                "read_only": True,
            },
        },
    )
    briefing = _briefing(
        adapter_config_path="infrastructure/config/surrealdb/context_query.local.example.yaml",
        secrets_path="D:/tmp/fake-secrets",
    )
    session = _session_context(briefing)
    assert session["brain_source"] == "surrealdb-local"
    assert session["brain_status"] == "used"
    assert session["agent_operating_mode"]["db_claims_allowed"] is True
    block = _brain_block(briefing)
    assert "cdb_context_trust_summary" in block["tools_or_queries"]


# ---------------------------------------------------------------------------
# repo-only + insufficient_evidence fail-closed
# ---------------------------------------------------------------------------


def test_repo_only_insufficient_evidence_forces_not_used_and_unavailable_context() -> None:
    """repo-only + insufficient_evidence → brain_status=not-used, context_available=false."""
    session = _session_context(_briefing())
    assert session["brain_source"] == "repo-only"
    assert session["brain_status"] == "not-used"
    assert session["context_available"] is False
    assert session["context_brain_used"] is False
    assert session["repo_fallback_used"] is True
    assert session["repo_fallback_reason"] == "insufficient_evidence"


# ---------------------------------------------------------------------------
# tool available without records — not misclassified as unavailable
# ---------------------------------------------------------------------------


def test_tool_available_no_records_is_not_classified_unavailable() -> None:
    """Available context tool with zero records must use insufficient_evidence."""
    session = _session_context(_briefing())
    assert session["context_tool_status"] == "available"
    assert session["repo_fallback_reason"] == "insufficient_evidence"
    assert session["repo_fallback_reason"] != "unavailable"
    assert session["context_tool_status"] != "absent"


@pytest.mark.parametrize(
    "brain_source,brain_status,operator_trust_level,records_found,expected_reason,expected_tool_status",
    [
        ("repo-only", "not-used", "LOW", 0, "insufficient_evidence", "available"),
        ("unavailable", "not-used", "BLOCKED", 0, "unavailable", "absent"),
        ("unavailable", "blocked", "BLOCKED", 0, "tool_blocked", "blocked"),
        ("in_memory", "used", "MEDIUM", 1, "none", "available"),
    ],
)
def test_normalize_brain_evidence_fallback_classification_matrix(
    brain_source: str,
    brain_status: str,
    operator_trust_level: str,
    records_found: int,
    expected_reason: str,
    expected_tool_status: str,
) -> None:
    """Fallback fields stay stable per agents/AGENTS.md classification matrix."""
    fields = _normalize_brain_evidence_fields(
        brain_source=brain_source,
        brain_status=brain_status,
        operator_trust_level=operator_trust_level,
        records_found=records_found,
    )
    assert fields["context_brain_attempted"] is True
    assert fields["repo_fallback_reason"] == expected_reason
    assert fields["context_tool_status"] == expected_tool_status
    assert FALLBACK_GATE_FIELDS.issubset(fields.keys())


# ---------------------------------------------------------------------------
# LOW trust degradation
# ---------------------------------------------------------------------------


def test_low_trust_degrades_sensory_loop_without_db_backed_claims() -> None:
    """LOW operator trust degrades the default sensory loop."""
    loop = _sensory_loop(_briefing())
    assert loop["status"] in {"degraded", "fail_closed"}
    degraded_reasons = loop.get("degraded_reasons")
    assert isinstance(degraded_reasons, list)
    assert "LOW" in degraded_reasons or "repo_only" in degraded_reasons
    claim_boundaries = loop["claim_boundaries"]
    assert claim_boundaries["allow_db_backed_closure_claims"] is False
    assert claim_boundaries["allow_db_backed_roadmap_claims"] is False
    assert claim_boundaries["allow_db_backed_status_claims"] is False


# ---------------------------------------------------------------------------
# caller-supplied fields rejected
# ---------------------------------------------------------------------------


def test_caller_supplied_brain_source_and_metadata_not_db_evidence() -> None:
    """Caller brain_source/brain_status/metadata.source are not record evidence."""
    briefing = _briefing(
        brain_source="surrealdb-local",
        brain_status="used",
    )
    session = _session_context(briefing)
    assert session["brain_source"] == "repo-only"
    assert session["brain_status"] == "not-used"
    assert any("caller input ignored" in item for item in session["limitations"])

    with pytest.raises(ClaimEvidenceAtRestError, match="cannot substitute"):
        reject_caller_metadata_as_evidence(
            {"brain_source": "surrealdb-local", "metadata.source": "surrealdb-local"},
            known_evidence_ids=frozenset(),
        )

    claim = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="invalid_fake_db",
        record_ids=[],
        record_hashes_or_content_fingerprints=[],
        caller_evidence={"brain_source": "surrealdb-local"},
        limitations=["caller brain_source ignored"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert classify_trust(claim) == "invalid_fake_db"


# ---------------------------------------------------------------------------
# complete Brain Evidence block shape
# ---------------------------------------------------------------------------


def test_complete_brain_evidence_block_shape_in_mcp_briefing() -> None:
    """Briefing must emit all mandatory Brain Evidence block fields."""
    block = _brain_block(_briefing())
    missing = BRAIN_EVIDENCE_BLOCK_FIELDS - set(block)
    assert not missing, f"missing Brain Evidence block fields: {sorted(missing)}"
    for key in ("tools_or_queries", "records_or_results", "repo_crosscheck", "impact_on_plan", "limitations"):
        assert isinstance(block[key], list)


def test_brain_evidence_block_merges_fallback_gate_fields() -> None:
    """Normalized fallback gate fields are merged into the Brain Evidence block."""
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
        limitations=["test limitation"],
        operator_trust_level="LOW",
        missing_evidence_notice=["no_evidence_records_provided"],
        blocking_trust_findings=[],
        records_found=0,
    )
    assert FALLBACK_GATE_FIELDS.issubset(block.keys())
    assert block["brain_source"] == "repo-only"
    assert block["context_available"] is False


def test_agents_md_brain_evidence_gate_contract_anchors() -> None:
    """Static governance anchors for Brain Evidence block contract (#3774)."""
    text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    for needle in AGENTS_BRAIN_EVIDENCE_ANCHORS:
        assert needle in text, f"agents/AGENTS.md missing anchor: {needle!r}"


# ---------------------------------------------------------------------------
# no DB-backed closure / roadmap / status claims
# ---------------------------------------------------------------------------


def test_no_db_backed_closure_roadmap_or_status_claims_under_repo_only() -> None:
    """repo-only/LOW/insufficient_evidence must block DB-backed closure claims."""
    loop = _sensory_loop(
        _briefing(
            repo_state={
                "working_tree": "staged-local-files-present",
                "delivery_state": "local_only",
            },
            github_state={"target_issue": "#3774", "roadmap_issue": "#3771"},
            working_assumptions=[
                "Roadmap truth is implied by local files.",
                "Closure truth is implied by a branch-local summary.",
                "Status proof is implied without DB-backed evidence.",
            ],
        )
    )
    boundaries = loop["claim_boundaries"]
    assert boundaries["allow_db_backed_roadmap_claims"] is False
    assert boundaries["allow_db_backed_closure_claims"] is False
    assert boundaries["allow_db_backed_status_claims"] is False
    briefing = _briefing(
        working_assumptions=["Ledger wording is enough for a DB-backed trust claim."],
    )
    blocking = briefing["blocking_trust_findings"]
    assert any("non_db_backed" in item.lower() for item in blocking)


# ---------------------------------------------------------------------------
# MCP briefing LOW-trust full block
# ---------------------------------------------------------------------------


def test_mcp_briefing_low_trust_exposes_full_brain_evidence_block() -> None:
    """LOW-trust/no-record briefing returns complete Brain Evidence block."""
    briefing = _briefing()
    session = _session_context(briefing)
    block = _brain_block(briefing)

    assert session["context_trust_level"] == "none"
    assert briefing["operator_trust_level"] == "LOW"
    assert session["records_found"] == "none"

    assert block["brain_source"] == "repo-only"
    assert block["brain_status"] == "not-used"
    assert FALLBACK_GATE_FIELDS.issubset(block.keys())
    assert BRAIN_EVIDENCE_BLOCK_FIELDS.issubset(block.keys())
    assert block["context_available"] is False
    assert block["repo_fallback_reason"] == "insufficient_evidence"
    assert any(
        "no DB-backed" in item or "Repo/GitHub fallback" in item
        for item in block["impact_on_plan"]
    )


def test_in_memory_fixture_records_max_medium_trust_not_surrealdb_local() -> None:
    """Inline fixture records derive in_memory posture — not surrealdb-local DB claims."""
    fx = _load_fixture()
    briefing = _briefing(
        evidence_records=fx["evidence_records"],
        claim_records=fx["claim_records"],
        enrichment_scope="wave14",
    )
    session = _session_context(briefing)
    block = _brain_block(briefing)
    assert session["brain_source"] == "in_memory"
    assert session["brain_status"] == "used"
    assert session["context_trust_level"] == "medium"
    assert session["agent_operating_mode"]["db_claims_allowed"] is False
    assert block["brain_source"] == "in_memory"
    assert "cdb_context_trust_summary" not in block["tools_or_queries"]
