"""Unit tests for contradiction_scan.py — Contradiction Scan Runtime v1.

Issues:
    #2146 — [SURREALDB][CONTEXT][CONTRADICTION-RUNTIME] Implement contradiction scan service v1
    #2150 — Tests/Fixtures (future Wave-15 slice, not scope here)
    Parent: #2145 (Wave-15)

Scope:
    Unit tests for tools/surrealdb/contradiction_scan.py.
    All fixtures are inline (no file loading — keeps slice narrow).
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No real datetime.now() — validated by test_clock.py::test_guardrails_no_forbidden_calls.

Coverage:
    - All 9 contradiction_type rules produce at least one finding with contradictory input.
    - Severity and confidence are set and within allowed ranges.
    - SourceRefs and EvidenceRefs are present in every finding.
    - blocking findings are visible and queryable.
    - false_positive makes a finding non-blocking but retains it.
    - accepted_risk makes a finding non-blocking but retains it.
    - Deterministic IDs (same input → same contradiction_id).
    - read-only: scan_contradictions_v1 returns ContradictionScanResult (no side effects).
"""

from __future__ import annotations

import pytest

from tools.surrealdb.contradiction_scan import (
    CONTRADICTION_TYPES,
    DETECTED_BY,
    SCHEMA_VERSION,
    SEVERITY_LEVELS,
    STATUS_VALUES,
    ContradictionFinding,
    ContradictionScanError,
    ContradictionScanResult,
    EvidenceRef,
    SourceRef,
    _contradiction_id,
    scan_contradictions_v1,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_valid_finding(f: ContradictionFinding) -> None:
    """Assert all mandatory fields on a ContradictionFinding are valid."""
    assert isinstance(f.contradiction_id, str) and len(f.contradiction_id) > 0
    assert f.contradiction_type in CONTRADICTION_TYPES
    assert isinstance(f.source_a_ref, SourceRef)
    assert isinstance(f.source_b_ref, SourceRef)
    assert isinstance(f.claim_refs, tuple)
    assert isinstance(f.evidence_refs, tuple)
    assert f.severity in SEVERITY_LEVELS
    assert isinstance(f.confidence, float)
    assert 0.0 <= f.confidence <= 1.0
    assert isinstance(f.detected_by, str) and len(f.detected_by) > 0
    assert isinstance(f.detected_at, str) and len(f.detected_at) > 0
    assert f.status in STATUS_VALUES
    assert isinstance(f.recommended_action, str) and len(f.recommended_action) > 0
    assert isinstance(f.blocking, bool)


# ── Rule Tests: one per contradiction_type ────────────────────────────────────


@pytest.mark.unit
def test_rule_doc_vs_code_finding() -> None:
    """doc_vs_code: doc asserts symbol exists but code_symbols is missing → finding."""
    records = {
        "doc_claims": [
            {"claim_id": "c-001", "path": "docs/api.md", "symbol": "MyService", "exists": True}
        ],
        "code_symbols": [],  # symbol absent → contradiction
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "doc_vs_code"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.source_a_ref.ref_type == "doc"
    assert f.source_b_ref.ref_type == "code_symbol"
    assert len(f.evidence_refs) >= 1


@pytest.mark.unit
def test_rule_doc_vs_decision_finding() -> None:
    """doc_vs_decision: doc rule is superseded by an active decision → finding."""
    records = {
        "doc_rules": [
            {"rule_id": "rule-abc", "path": "docs/runbook.md", "rule_text": "Always use strategy A"}
        ],
        "decisions": [
            {"decision_id": "dec-001", "supersedes": ["rule-abc"], "status": "open"}
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "doc_vs_decision"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.source_a_ref.ref_type == "doc"
    assert f.source_b_ref.ref_type == "decision"


@pytest.mark.unit
def test_rule_decision_vs_evidence_finding() -> None:
    """decision_vs_evidence: decision requires evidence but none referenced → blocking finding."""
    records = {
        "decisions": [
            {
                "decision_id": "dec-evidence-required",
                "requires_evidence": True,
                "evidence_refs": [],  # no evidence → contradiction
            }
        ],
        "evidence_records": [],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "decision_vs_evidence"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.blocking is True


@pytest.mark.unit
def test_rule_claim_vs_evidence_finding() -> None:
    """claim_vs_evidence: claim with disputed status → blocking finding."""
    records = {
        "claims": [
            {"claim_id": "cl-disputed", "status": "disputed", "evidence_refs": ["ev-x"]}
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "claim_vs_evidence"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.blocking is True
    assert "cl-disputed" in f.claim_refs


@pytest.mark.unit
def test_rule_claim_vs_evidence_stale_is_warning() -> None:
    """claim_vs_evidence: stale claim → warning (not blocking)."""
    records = {
        "claims": [
            {"claim_id": "cl-stale", "status": "stale", "evidence_refs": []}
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "claim_vs_evidence"]
    assert len(findings) >= 1
    assert findings[0].severity == "warning"
    assert findings[0].blocking is False


@pytest.mark.unit
def test_rule_memory_vs_source_finding() -> None:
    """memory_vs_source: source explicitly contradicts memory → warning finding."""
    records = {
        "memory_records": [
            {"memory_id": "mem-001", "scope": "cdb", "content": "Old fact", "updated_at": "2025-01-01T00:00:00"}
        ],
        "source_records": [
            {"source_id": "src-001", "updated_at": "2026-01-01T00:00:00", "contradicts_memory": ["mem-001"]}
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "memory_vs_source"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.source_a_ref.ref_type == "memory"
    assert f.source_b_ref.ref_type == "source"


@pytest.mark.unit
def test_rule_memory_vs_source_stale_timestamp() -> None:
    """memory_vs_source: source is newer than memory for the same source_ref → warning."""
    records = {
        "memory_records": [
            {
                "memory_id": "mem-002",
                "scope": "cdb",
                "content": "Cached info",
                "updated_at": "2025-06-01T00:00:00",
                "source_ref": "src-002",
            }
        ],
        "source_records": [
            {
                "source_id": "src-002",
                "updated_at": "2026-03-01T00:00:00",
                "contradicts_memory": [],
            }
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "memory_vs_source"]
    assert len(findings) >= 1
    assert findings[0].severity == "warning"


@pytest.mark.unit
def test_rule_current_status_vs_live_surface_finding() -> None:
    """current_status_vs_live_surface: ledger says closed, surface says open → blocking."""
    records = {
        "status_ledger_records": [
            {"ledger_id": "ledger-001", "item_id": "issue-2099", "status": "closed"}
        ],
        "live_surface_records": [
            {"surface_id": "surface-001", "item_id": "issue-2099", "status": "open"}
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "current_status_vs_live_surface"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.blocking is True


@pytest.mark.unit
def test_rule_runbook_vs_contract_finding() -> None:
    """runbook_vs_contract: runbook step violates a governance constraint → finding."""
    records = {
        "runbook_steps": [
            {
                "step_id": "step-001",
                "runbook_id": "runbooks/deploy.md",
                "instruction": "Push directly to main without review",
                "violates_contract": "CONTRACT-REVIEW-REQUIRED",
                "severity_hint": "blocking",
            }
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "runbook_vs_contract"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.source_a_ref.ref_type == "runbook"
    assert f.source_b_ref.ref_type == "contract"


@pytest.mark.unit
def test_rule_test_vs_claim_finding() -> None:
    """test_vs_claim: claim asserts 'tested' but no test refs → blocking finding."""
    records = {
        "claims": [
            {"claim_id": "cl-test-001", "coverage_claim": "tested", "test_refs": []}
        ],
        "test_results": [],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "test_vs_claim"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.blocking is True


@pytest.mark.unit
def test_rule_test_vs_claim_failed_test() -> None:
    """test_vs_claim: claim says 'covered' but referenced test is failed → blocking."""
    records = {
        "claims": [
            {"claim_id": "cl-covered", "coverage_claim": "covered", "test_refs": ["test-abc"]}
        ],
        "test_results": [
            {"test_id": "test-abc", "status": "failed"}
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "test_vs_claim"]
    assert len(findings) >= 1
    assert findings[0].severity == "blocking"


@pytest.mark.unit
def test_rule_stale_decision_vs_new_evidence_finding() -> None:
    """stale_decision_vs_new_evidence: evidence supersedes an open decision → finding."""
    records = {
        "decisions": [
            {
                "decision_id": "dec-old",
                "created_at": "2024-01-01T00:00:00",
                "status": "open",
            }
        ],
        "evidence_records": [
            {
                "evidence_id": "ev-new",
                "created_at": "2025-06-01T00:00:00",
                "supersedes_decision": "dec-old",
            }
        ],
    }
    result = scan_contradictions_v1(records)
    findings = [f for f in result.findings if f.contradiction_type == "stale_decision_vs_new_evidence"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.source_a_ref.ref_id == "dec-old"
    assert f.source_b_ref.ref_id == "ev-new"


# ── Severity and Confidence Range ─────────────────────────────────────────────


@pytest.mark.unit
def test_severity_and_confidence_range() -> None:
    """All findings have valid severity and confidence in [0.0, 1.0]."""
    records = {
        "doc_claims": [{"claim_id": "c1", "symbol": "MissingClass", "exists": True}],
        "code_symbols": [],
        "claims": [{"claim_id": "c2", "status": "disputed", "evidence_refs": []}],
        "decisions": [
            {"decision_id": "d1", "requires_evidence": True, "evidence_refs": [], "status": "open"}
        ],
        "evidence_records": [],
    }
    result = scan_contradictions_v1(records)
    assert result.total_count > 0
    for f in result.findings:
        assert f.severity in SEVERITY_LEVELS, f"Invalid severity: {f.severity}"
        assert 0.0 <= f.confidence <= 1.0, f"Confidence out of range: {f.confidence}"


# ── Blocking Findings Visibility ─────────────────────────────────────────────


@pytest.mark.unit
def test_blocking_findings_visible() -> None:
    """Blocking findings are clearly identifiable in scan result."""
    records = {
        "decisions": [
            {"decision_id": "dec-block", "requires_evidence": True, "evidence_refs": [], "status": "open"}
        ],
        "evidence_records": [],
    }
    result = scan_contradictions_v1(records)
    blocking = [f for f in result.findings if f.blocking]
    assert len(blocking) >= 1
    assert result.blocking_count == len(blocking)
    for f in blocking:
        assert f.severity == "blocking"
        assert f.status not in {"false_positive", "accepted_risk", "resolved", "superseded"}


# ── False-Positive Override ───────────────────────────────────────────────────


@pytest.mark.unit
def test_false_positive_makes_nonblocking() -> None:
    """false_positive override: finding is retained but blocking=False and status=false_positive."""
    records = {
        "decisions": [
            {"decision_id": "dec-fp", "requires_evidence": True, "evidence_refs": [], "status": "open"}
        ],
        "evidence_records": [],
    }
    result_no_override = scan_contradictions_v1(records)
    blocking_finding = next((f for f in result_no_override.findings if f.blocking), None)
    assert blocking_finding is not None

    overrides = {blocking_finding.contradiction_id: "false_positive"}
    result_with_override = scan_contradictions_v1(records, overrides=overrides)

    overridden = next(
        (f for f in result_with_override.findings if f.contradiction_id == blocking_finding.contradiction_id),
        None,
    )
    assert overridden is not None, "Finding must be retained after false_positive override"
    assert overridden.status == "false_positive"
    assert overridden.blocking is False
    # Result still contains the finding
    assert result_with_override.total_count >= 1


@pytest.mark.unit
def test_false_positive_reduces_blocking_count() -> None:
    """false_positive override reduces blocking_count but total_count stays the same."""
    records = {
        "decisions": [
            {"decision_id": "dec-fp2", "requires_evidence": True, "evidence_refs": [], "status": "open"}
        ],
        "evidence_records": [],
    }
    result_raw = scan_contradictions_v1(records)
    blocking_ids = {f.contradiction_id for f in result_raw.findings if f.blocking}
    assert len(blocking_ids) >= 1

    overrides = {cid: "false_positive" for cid in blocking_ids}
    result_overridden = scan_contradictions_v1(records, overrides=overrides)

    assert result_overridden.total_count == result_raw.total_count
    assert result_overridden.blocking_count == 0


# ── Accepted-Risk Override ────────────────────────────────────────────────────


@pytest.mark.unit
def test_accepted_risk_makes_nonblocking() -> None:
    """accepted_risk override: finding retained, non-blocking, status=accepted_risk."""
    records = {
        "status_ledger_records": [
            {"ledger_id": "l1", "item_id": "item-xyz", "status": "closed"}
        ],
        "live_surface_records": [
            {"surface_id": "s1", "item_id": "item-xyz", "status": "open"}
        ],
    }
    result_raw = scan_contradictions_v1(records)
    blocking = [f for f in result_raw.findings if f.blocking]
    assert len(blocking) >= 1

    overrides = {blocking[0].contradiction_id: "accepted_risk"}
    result_ar = scan_contradictions_v1(records, overrides=overrides)

    overridden = next(
        (f for f in result_ar.findings if f.contradiction_id == blocking[0].contradiction_id),
        None,
    )
    assert overridden is not None, "Finding must be retained after accepted_risk override"
    assert overridden.status == "accepted_risk"
    assert overridden.blocking is False
    assert result_ar.total_count >= 1


@pytest.mark.unit
def test_accepted_risk_finding_visible_in_results() -> None:
    """accepted_risk findings remain visible (not hidden) in the scan result."""
    records = {
        "claims": [{"claim_id": "cl-ar", "status": "disputed", "evidence_refs": []}],
    }
    result_raw = scan_contradictions_v1(records)
    blocking = [f for f in result_raw.findings if f.blocking]
    assert len(blocking) >= 1

    overrides = {blocking[0].contradiction_id: "accepted_risk"}
    result_ar = scan_contradictions_v1(records, overrides=overrides)

    # Finding is still in results
    assert any(f.contradiction_id == blocking[0].contradiction_id for f in result_ar.findings)
    # But blocking count is reduced
    assert result_ar.blocking_count < result_raw.blocking_count


# ── Deterministic IDs ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_deterministic_ids() -> None:
    """Same input always produces identical contradiction_ids."""
    records = {
        "doc_claims": [{"claim_id": "c-det", "symbol": "DetSymbol", "exists": True}],
        "code_symbols": [],
    }
    result_a = scan_contradictions_v1(records)
    result_b = scan_contradictions_v1(records)

    ids_a = {f.contradiction_id for f in result_a.findings}
    ids_b = {f.contradiction_id for f in result_b.findings}
    assert ids_a == ids_b, "contradiction_ids must be deterministic"


@pytest.mark.unit
def test_contradiction_id_helper_determinism() -> None:
    """_contradiction_id is stable across multiple calls."""
    cid1 = _contradiction_id("doc_vs_code", "ref-a", "ref-b")
    cid2 = _contradiction_id("doc_vs_code", "ref-a", "ref-b")
    assert cid1 == cid2
    assert len(cid1) == 16
    assert cid1 != _contradiction_id("doc_vs_code", "ref-b", "ref-a")


# ── SourceRef / EvidenceRef in Output ────────────────────────────────────────


@pytest.mark.unit
def test_source_refs_in_output() -> None:
    """Every finding has SourceRef instances for source_a_ref and source_b_ref."""
    records = {
        "doc_claims": [{"claim_id": "c-sr", "symbol": "MissingX", "exists": True}],
        "code_symbols": [],
        "claims": [{"claim_id": "cl-sr", "status": "invalidated", "evidence_refs": []}],
    }
    result = scan_contradictions_v1(records)
    assert result.total_count >= 1
    for f in result.findings:
        assert isinstance(f.source_a_ref, SourceRef)
        assert isinstance(f.source_b_ref, SourceRef)
        assert f.source_a_ref.ref_id
        assert f.source_b_ref.ref_id


@pytest.mark.unit
def test_evidence_refs_present() -> None:
    """Every finding has at least one EvidenceRef."""
    records = {
        "doc_claims": [{"claim_id": "c-ev", "symbol": "MissingY", "exists": True}],
        "code_symbols": [],
    }
    result = scan_contradictions_v1(records)
    assert result.total_count >= 1
    for f in result.findings:
        assert isinstance(f.evidence_refs, tuple)
        assert len(f.evidence_refs) >= 1
        for er in f.evidence_refs:
            assert isinstance(er, EvidenceRef)
            assert er.evidence_id
            assert er.evidence_type


# ── Read-Only (No Writes) ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_writes() -> None:
    """scan_contradictions_v1 returns a ContradictionScanResult without side effects."""
    records = {
        "doc_claims": [{"claim_id": "c-rw", "symbol": "NoWrite", "exists": True}],
        "code_symbols": [],
    }
    result = scan_contradictions_v1(records)
    assert isinstance(result, ContradictionScanResult)
    assert result.schema_version == SCHEMA_VERSION
    assert isinstance(result.findings, tuple)
    assert isinstance(result.blocking_count, int)
    assert isinstance(result.total_count, int)
    assert result.total_count == len(result.findings)
    assert result.blocking_count <= result.total_count


@pytest.mark.unit
def test_empty_records_no_findings() -> None:
    """Empty records produce no findings — no crashes."""
    result = scan_contradictions_v1({})
    assert isinstance(result, ContradictionScanResult)
    assert result.total_count == 0
    assert result.blocking_count == 0
    assert result.findings == ()


@pytest.mark.unit
def test_invalid_records_raises() -> None:
    """Non-mapping records raise ContradictionScanError."""
    with pytest.raises(ContradictionScanError):
        scan_contradictions_v1([])  # type: ignore[arg-type]


# ── Schema and Constants ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_schema_constants() -> None:
    """SCHEMA_VERSION, DETECTED_BY, CONTRADICTION_TYPES, STATUS_VALUES are correct."""
    assert SCHEMA_VERSION == "contradiction-scan/v1"
    assert DETECTED_BY == "contradiction-scan/v1"
    assert len(CONTRADICTION_TYPES) == 9
    assert "doc_vs_code" in CONTRADICTION_TYPES
    assert "stale_decision_vs_new_evidence" in CONTRADICTION_TYPES
    assert "false_positive" in STATUS_VALUES
    assert "accepted_risk" in STATUS_VALUES
    assert "acknowledged" in STATUS_VALUES


@pytest.mark.unit
def test_detected_by_in_findings() -> None:
    """All findings have detected_by set to the service version constant."""
    records = {
        "claims": [{"claim_id": "cl-db", "status": "disputed", "evidence_refs": []}],
    }
    result = scan_contradictions_v1(records)
    assert result.total_count >= 1
    for f in result.findings:
        assert f.detected_by == DETECTED_BY


@pytest.mark.unit
def test_detected_at_is_iso_string() -> None:
    """detected_at on every finding is a non-empty ISO-8601 string (no datetime.now)."""
    records = {
        "doc_claims": [{"claim_id": "c-dt", "symbol": "TimeSymbol", "exists": True}],
        "code_symbols": [],
    }
    result = scan_contradictions_v1(records)
    assert result.total_count >= 1
    for f in result.findings:
        assert isinstance(f.detected_at, str)
        assert len(f.detected_at) >= 10  # at least YYYY-MM-DD
        # Must not contain any forbidden patterns — just validate it's a valid ISO form
        assert "T" in f.detected_at or "-" in f.detected_at


# ── Scanned_at in Result ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_scan_result_scanned_at_present() -> None:
    """ContradictionScanResult.scanned_at is a non-empty string."""
    result = scan_contradictions_v1({})
    assert isinstance(result.scanned_at, str)
    assert len(result.scanned_at) >= 10


# ── No false_positive/accepted_risk when no override given ────────────────────


@pytest.mark.unit
def test_no_override_status_is_open() -> None:
    """Without overrides, all findings default to status='open'."""
    records = {
        "doc_claims": [{"claim_id": "c-open", "symbol": "OpenSymbol", "exists": True}],
        "code_symbols": [],
    }
    result = scan_contradictions_v1(records)
    for f in result.findings:
        assert f.status == "open"


# ── Override with unknown ID is a no-op ───────────────────────────────────────


@pytest.mark.unit
def test_unknown_override_id_is_noop() -> None:
    """Override for non-existent contradiction_id does not crash or corrupt results."""
    records = {
        "doc_claims": [{"claim_id": "c-noop", "symbol": "NoopSymbol", "exists": True}],
        "code_symbols": [],
    }
    overrides = {"nonexistent-id-0000": "false_positive"}
    result = scan_contradictions_v1(records, overrides=overrides)
    assert result.total_count >= 1
    for f in result.findings:
        assert f.status == "open"
