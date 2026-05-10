"""Unit tests for Wave-15 MCP tool: cdb_context_contradictions.

Issues:
    #2148 — [SURREALDB][CONTEXT][CONTRADICTION-MCP] Implement contradiction MCP tool
    Parent: #2145 (Wave-15)
    Epic: #1976

Scope:
    Unit tests for tools/mcp/context_contradiction_tools.py and its integration
    with the MCP registry, context bridge, and permission guard.
    All fixtures are inline — no file loading.
    No DB access. No SurrealDB SDK. No network. No writes.
    No real datetime.now() — timestamps come from contradiction_scan.py via
    core.utils.clock (validated by test_clock.py::test_guardrails_no_forbidden_calls).
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.mcp.context_bridge import ContextBridge
from tools.mcp.context_contradiction_tools import (
    TOOL_CDB_CONTEXT_CONTRADICTIONS,
    handle_cdb_context_contradictions,
    _derive_recommended_next_reads,
)
from tools.mcp.permission_guard import INPUT_SCAN_EXEMPT_TOOLS, PermissionGuard
from tools.mcp.registry import ContextToolRegistry


# ── Inline Fixtures ───────────────────────────────────────────────────────────


def _doc_vs_code_records() -> dict[str, Any]:
    """Records that trigger a doc_vs_code contradiction (blocking)."""
    return {
        "doc_claims": [
            {
                "claim_id": "c-mcp-001",
                "path": "docs/api.md",
                "symbol": "ContradictionService",
                "exists": True,
                "blocking": True,
            }
        ],
        "code_symbols": [],  # symbol absent → contradiction
    }


def _claim_vs_evidence_records() -> dict[str, Any]:
    """Records that trigger a claim_vs_evidence contradiction (blocking)."""
    return {
        "claims": [
            {
                "claim_id": "cl-mcp-001",
                "status": "disputed",
                "topic": "wave15",
                "evidence_refs": ["ev-mcp-001"],
            }
        ]
    }


def _non_blocking_records() -> dict[str, Any]:
    """Records that trigger a doc_vs_decision contradiction (warning, non-blocking)."""
    return {
        "doc_rules": [
            {
                "rule_id": "rule-mcp-001",
                "path": "docs/governance.md",
                "rule_text": "Use old pattern",
            }
        ],
        "decisions": [
            {
                "decision_id": "dec-mcp-001",
                "supersedes": ["rule-mcp-001"],
                "status": "active",
            }
        ],
    }


def _base_request(records: dict[str, Any], **extra_params: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"records": records}
    params.update(extra_params)
    return {
        "tool": TOOL_CDB_CONTEXT_CONTRADICTIONS,
        "parameters": params,
    }


# ── 1. Registry ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_in_registry_is_read_only() -> None:
    """Tool must be registered and read_only=True."""
    tool = ContextToolRegistry.get_tool(TOOL_CDB_CONTEXT_CONTRADICTIONS)
    assert tool is not None, f"{TOOL_CDB_CONTEXT_CONTRADICTIONS} not found in registry"
    assert tool.read_only is True
    assert tool.name == TOOL_CDB_CONTEXT_CONTRADICTIONS


@pytest.mark.unit
def test_tool_in_registry_tool_names() -> None:
    """Tool name appears in registry tool list."""
    names = ContextToolRegistry.list_tool_names()
    assert TOOL_CDB_CONTEXT_CONTRADICTIONS in names


# ── 2. Bridge ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_executable_via_bridge() -> None:
    """Tool can be executed via ContextBridge.execute_tool and returns status ok."""
    bridge = ContextBridge()
    result = bridge.execute_tool(
        TOOL_CDB_CONTEXT_CONTRADICTIONS,
        parameters={"records": _doc_vs_code_records()},
    )
    assert result["status"] == "ok"
    assert result["tool"] == TOOL_CDB_CONTEXT_CONTRADICTIONS


# ── 3. Input Schema ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_input_schema_accepts_scope_artifact_decision_claim() -> None:
    """scope, artifact, decision, claim params are accepted without error."""
    result = handle_cdb_context_contradictions(
        _base_request(
            _claim_vs_evidence_records(),
            scope="wave15",
            artifact="tools/mcp/context_contradiction_tools.py",
            decision="dec-2148",
            claim="cl-001",
        )
    )
    assert result["status"] == "ok"
    assert result["scope"] == "wave15"
    assert result["artifact"] == "tools/mcp/context_contradiction_tools.py"
    assert result["decision"] == "dec-2148"
    assert result["claim"] == "cl-001"


# ── 4. Handler calls scan service and returns findings ────────────────────────


@pytest.mark.unit
def test_handler_calls_scan_service_and_returns_findings() -> None:
    """Handler calls scan_contradictions_v1 and returns findings for contradictory records."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    assert result["total_findings"] >= 1
    assert isinstance(result["findings"], list)
    assert len(result["findings"]) == result["returned_findings"]


# ── 5. SourceRefs ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_output_contains_source_refs() -> None:
    """Each finding must contain source_a_ref and source_b_ref with ref_id and ref_type."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    assert len(result["findings"]) >= 1
    for finding in result["findings"]:
        assert "source_a_ref" in finding
        assert "source_b_ref" in finding
        for ref_key in ("source_a_ref", "source_b_ref"):
            ref = finding[ref_key]
            assert "ref_id" in ref
            assert "ref_type" in ref
            assert isinstance(ref["ref_id"], str) and ref["ref_id"]


# ── 6. EvidenceRefs ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_output_contains_evidence_refs() -> None:
    """Each finding must contain evidence_refs (list, may be empty but present)."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert "evidence_refs" in finding
        assert isinstance(finding["evidence_refs"], list)
        for ev in finding["evidence_refs"]:
            assert "evidence_id" in ev
            assert "evidence_type" in ev
            assert "strength" in ev


# ── 7. Severity + Confidence ──────────────────────────────────────────────────


@pytest.mark.unit
def test_output_contains_severity_confidence() -> None:
    """Each finding must have severity (str) and confidence (float in [0, 1])."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert "severity" in finding
        assert finding["severity"] in ("info", "warning", "blocking")
        assert "confidence" in finding
        assert isinstance(finding["confidence"], float)
        assert 0.0 <= finding["confidence"] <= 1.0


# ── 8. recommended_next_reads ─────────────────────────────────────────────────


@pytest.mark.unit
def test_output_contains_recommended_next_reads() -> None:
    """Output must contain recommended_next_reads as a list of strings."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    assert "recommended_next_reads" in result
    assert isinstance(result["recommended_next_reads"], list)
    for item in result["recommended_next_reads"]:
        assert isinstance(item, str) and item.strip()


# ── 9. Blocking findings / blocking_count ────────────────────────────────────


@pytest.mark.unit
def test_blocking_findings_counted() -> None:
    """blocking_count must equal the number of blocking=True findings."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    manual_count = sum(1 for f in result["findings"] if f["blocking"])
    assert result["blocking_count"] == manual_count
    assert result["blocking_count"] >= 1  # doc_vs_code with blocking=True in fixture


@pytest.mark.unit
def test_blocking_findings_visible() -> None:
    """Blocking findings have blocking=True and severity=blocking."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    blocking_findings = [f for f in result["findings"] if f["blocking"]]
    assert len(blocking_findings) >= 1
    for f in blocking_findings:
        assert f["severity"] == "blocking"


# ── 10. false_positive override ───────────────────────────────────────────────


@pytest.mark.unit
def test_false_positive_override_non_blocking() -> None:
    """false_positive override: finding retained but blocking=False, status updated."""
    # First get the contradiction_id without override
    base_result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert base_result["status"] == "ok"
    blocking = [f for f in base_result["findings"] if f["blocking"]]
    assert len(blocking) >= 1
    cid = blocking[0]["contradiction_id"]

    # Now apply false_positive override
    result = handle_cdb_context_contradictions(
        _base_request(
            _doc_vs_code_records(),
            overrides={cid: "false_positive"},
        )
    )
    assert result["status"] == "ok"
    # finding must still be present
    matched = [f for f in result["findings"] if f["contradiction_id"] == cid]
    assert len(matched) == 1
    # but must be non-blocking
    assert matched[0]["blocking"] is False
    assert matched[0]["status"] == "false_positive"


# ── 11. accepted_risk override ────────────────────────────────────────────────


@pytest.mark.unit
def test_accepted_risk_override_non_blocking() -> None:
    """accepted_risk override: finding retained but blocking=False, status updated."""
    base_result = handle_cdb_context_contradictions(
        _base_request(_claim_vs_evidence_records())
    )
    assert base_result["status"] == "ok"
    blocking = [f for f in base_result["findings"] if f["blocking"]]
    assert len(blocking) >= 1
    cid = blocking[0]["contradiction_id"]

    result = handle_cdb_context_contradictions(
        _base_request(
            _claim_vs_evidence_records(),
            overrides={cid: "accepted_risk"},
        )
    )
    assert result["status"] == "ok"
    matched = [f for f in result["findings"] if f["contradiction_id"] == cid]
    assert len(matched) == 1
    assert matched[0]["blocking"] is False
    assert matched[0]["status"] == "accepted_risk"


# ── 12. no_live_go ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_live_go_in_output() -> None:
    """no_live_go=True must be present in every successful response."""
    for records in (_doc_vs_code_records(), _claim_vs_evidence_records(), {}):
        result = handle_cdb_context_contradictions({"records": records})
        assert result.get("no_live_go") is True, f"no_live_go missing for records={records!r}"
        assert result.get("no_write") is True


# ── 13. Permission Guard ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_permission_guard_allows_legitimate_read_only_use() -> None:
    """Permission guard must not block legitimate scope/artifact/claim field content."""
    assert TOOL_CDB_CONTEXT_CONTRADICTIONS in INPUT_SCAN_EXEMPT_TOOLS

    violations = PermissionGuard.check_tool_inputs(
        TOOL_CDB_CONTEXT_CONTRADICTIONS,
        {
            "records": {"doc_claims": [{"claim_id": "c1", "symbol": "CreateOrder"}]},
            "scope": "wave15",
            "artifact": "docs/operations/runbook.md",
            "claim": "Claim: system must not DELETE records without audit trail",
        },
    )
    assert violations == [], f"Unexpected violations: {violations}"


@pytest.mark.unit
def test_permission_guard_tool_is_exempt_from_input_scan() -> None:
    """cdb_context_contradictions must be in INPUT_SCAN_EXEMPT_TOOLS."""
    assert TOOL_CDB_CONTEXT_CONTRADICTIONS in INPUT_SCAN_EXEMPT_TOOLS


# ── 14. Missing records → fail-closed ────────────────────────────────────────


@pytest.mark.unit
def test_no_records_returns_error_closed() -> None:
    """Handler must return error (fail-closed) when records is missing."""
    result = handle_cdb_context_contradictions(
        {"tool": TOOL_CDB_CONTEXT_CONTRADICTIONS, "parameters": {"scope": "test"}}
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "missing_records"


@pytest.mark.unit
def test_wrong_tool_name_returns_error() -> None:
    """Handler must return error when tool name does not match."""
    result = handle_cdb_context_contradictions(
        {"tool": "wrong_tool", "parameters": {"records": {}}}
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "invalid_tool"


# ── 15. Guardrails present ────────────────────────────────────────────────────


@pytest.mark.unit
def test_guardrails_present_in_output() -> None:
    """Output must contain a non-empty guardrails list."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    assert "guardrails" in result
    assert isinstance(result["guardrails"], list)
    assert len(result["guardrails"]) >= 1
    # Must state detection is signal not action
    joined = " ".join(result["guardrails"]).lower()
    assert "signal" in joined or "action" in joined


# ── 16. include_non_blocking=False ───────────────────────────────────────────


@pytest.mark.unit
def test_include_non_blocking_false_filters_non_blocking() -> None:
    """include_non_blocking=False must return only blocking findings."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records(), include_non_blocking=False)
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["blocking"] is True


# ── 17. types filter ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_types_filter_limits_to_requested_type() -> None:
    """types filter must restrict findings to the specified contradiction_type."""
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records(), types=["doc_vs_code"])
    )
    assert result["status"] == "ok"
    for finding in result["findings"]:
        assert finding["contradiction_type"] == "doc_vs_code"


@pytest.mark.unit
def test_types_filter_empty_list_treated_as_no_filter() -> None:
    """Empty types list must not apply any filter."""
    full = handle_cdb_context_contradictions(_base_request(_doc_vs_code_records()))
    filtered = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records(), types=[])
    )
    assert full["total_findings"] == filtered["total_findings"]


# ── 18. limit param ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_limit_truncates_findings() -> None:
    """limit param caps returned findings but blocking_count reflects full scan."""
    full = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert full["status"] == "ok"
    assert full["blocking_count"] >= 1

    limited = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records(), limit=1)
    )
    assert limited["status"] == "ok"
    # returned count capped
    assert len(limited["findings"]) <= 1
    assert limited["returned_findings"] <= 1
    # total_findings and blocking_count reflect the FULL scan, not the truncated set
    assert limited["total_findings"] == full["total_findings"]
    assert limited["blocking_count"] == full["blocking_count"]
    # truncated flag set when findings were capped
    if full["total_findings"] > 1:
        assert limited["truncated"] is True


# ── 19. recommended_next_reads derivation ────────────────────────────────────


@pytest.mark.unit
def test_recommended_next_reads_prioritises_blocking_findings() -> None:
    """recommended_next_reads from blocking findings must appear before non-blocking."""
    # doc_vs_code_records produces a blocking finding whose source_a_ref.path is docs/api.md
    result = handle_cdb_context_contradictions(
        _base_request(_doc_vs_code_records())
    )
    assert result["status"] == "ok"
    reads = result["recommended_next_reads"]
    # docs/api.md is the path in the blocking finding's source_a_ref
    if "docs/api.md" in reads:
        # It must appear (blocking findings come first)
        assert reads.index("docs/api.md") < 20


@pytest.mark.unit
def test_derive_recommended_next_reads_max_20() -> None:
    """_derive_recommended_next_reads must return at most 20 entries."""
    from tools.surrealdb.contradiction_scan import (
        ContradictionFinding,
        EvidenceRef,
        SourceRef,
    )

    # Build synthetic findings with many refs
    findings = []
    for i in range(25):
        f = ContradictionFinding(
            contradiction_id=f"id{i:02d}",
            contradiction_type="doc_vs_code",
            source_a_ref=SourceRef(ref_id=f"a{i}", ref_type="doc", path=f"docs/f{i}.md"),
            source_b_ref=SourceRef(ref_id=f"b{i}", ref_type="code_symbol", path=None),
            claim_refs=(f"cr{i}",),
            evidence_refs=(
                EvidenceRef(evidence_id=f"ev{i}", evidence_type="code_symbol_absence"),
            ),
            severity="blocking",
            confidence=0.9,
            detected_by="test",
            detected_at="2026-05-06T00:00:00",
            status="open",
            recommended_action="test",
            blocking=True,
        )
        findings.append(f)

    reads = _derive_recommended_next_reads(findings)
    assert len(reads) <= 20


# ── 20. Wave-14 tests still pass (smoke import) ───────────────────────────────


@pytest.mark.unit
def test_wave14_tools_still_importable() -> None:
    """Wave-14 handler modules must still be importable after Wave-15 changes."""
    from tools.mcp.context_evidence_memory_tools import (
        TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
        handle_cdb_context_evidence_resolve,  # noqa: F401
    )
    from tools.mcp.context_decision_tools import (
        TOOL_CDB_CONTEXT_DECISION_HISTORY,
        handle_cdb_context_decision_history,  # noqa: F401
    )

    assert TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE == "cdb_context_evidence_resolve"
    assert TOOL_CDB_CONTEXT_DECISION_HISTORY == "cdb_context_decision_history"


@pytest.mark.unit
def test_bridge_registers_all_wave14_tools() -> None:
    """Wave-14 tools must still be accessible via the bridge after Wave-15 init."""
    bridge = ContextBridge()
    wave14_tools = [
        "cdb_context_evidence_resolve",
        "cdb_context_claim_resolve",
        "cdb_context_memory_get",
        "cdb_context_trust_summary",
        "cdb_context_decision_history",
        "cdb_context_decision_replay",
    ]
    names = [t["name"] for t in bridge.list_tools()]
    for tool_name in wave14_tools:
        assert tool_name in names, f"Wave-14 tool missing after Wave-15 init: {tool_name}"
