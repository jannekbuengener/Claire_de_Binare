"""Unit tests for Wave-14 services: evidence_lookup, claim_resolver, memory_read, trust_summary.

Issues:
    #2126 — Add tests and fixtures for evidence, decision, and memory retrieval
    Parent: #2115 (Wave-14), Epic: #1976
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.evidence_lookup import (
    EvidenceLookupError,
    EvidenceLookupRequest,
    lookup_evidence_v1,
)
from tools.surrealdb.claim_resolver import (
    ClaimResolverError,
    ClaimResolveRequest,
    resolve_claims_v1,
)
from tools.surrealdb.memory_read import (
    MemoryReadError,
    MemoryReadRequest,
    read_memory_v1,
)
from tools.surrealdb.trust_summary import (
    TrustSummaryError,
    TrustSummaryRequest,
    build_trust_summary_v1,
)


FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── Evidence Lookup ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_evidence_by_artifact() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_artifact", artifact="tools/surrealdb/context_stop_resolver.py")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    assert result["mode"] == "by_artifact"
    assert any(e["evidence_id"] == "ev-001" for e in result["matched_evidence"])


@pytest.mark.unit
def test_evidence_by_claim() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_claim", claim="claim-001")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    assert any(e["evidence_id"] == "ev-001" for e in result["matched_evidence"])


@pytest.mark.unit
def test_evidence_by_evidence_type() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_evidence_type", evidence_type="test_run")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    ids = {e["evidence_id"] for e in result["matched_evidence"]}
    assert "ev-001" in ids
    assert "ev-002" in ids
    assert "ev-003" not in ids


@pytest.mark.unit
def test_evidence_by_run_id() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_run_id", run_id="run-2024-001")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    assert [e["evidence_id"] for e in result["matched_evidence"]] == ["ev-001"]


@pytest.mark.unit
def test_evidence_by_confidence() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_confidence", min_confidence=0.85)
    result = lookup_evidence_v1(fx["evidence_records"], req)
    ids = {e["evidence_id"] for e in result["matched_evidence"]}
    assert "ev-001" in ids
    assert "ev-003" not in ids


@pytest.mark.unit
def test_evidence_strength_blocking_missing() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_artifact", artifact="tools/surrealdb/trust_summary.py")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    assert "blocking_missing_evidence_present" in result["warnings"]
    assert len(result["blocking_missing_ids"]) >= 1


@pytest.mark.unit
def test_evidence_stale_flagged() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_evidence_type", evidence_type="test_run")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    assert "stale_evidence_present" in result["warnings"]


@pytest.mark.unit
def test_evidence_no_match_warning() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_run_id", run_id="run-nonexistent")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    assert "no_evidence_matched" in result["warnings"]


@pytest.mark.unit
def test_evidence_invalid_mode() -> None:
    with pytest.raises(EvidenceLookupError, match="unsupported mode"):
        lookup_evidence_v1([], EvidenceLookupRequest(mode="bad_mode"))


@pytest.mark.unit
def test_evidence_approval_semantics() -> None:
    fx = _load_fixture()
    req = EvidenceLookupRequest(mode="by_run_id", run_id="run-2024-001")
    result = lookup_evidence_v1(fx["evidence_records"], req)
    sem = result["approval_semantics"]
    assert sem.get("no_echtgeld_go") is True
    assert sem.get("no_approval") is True


# ── Claim Resolver ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_claim_by_topic() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_topic", topic="stop_conditions")
    result = resolve_claims_v1(fx["claim_records"], req)
    assert any(c["claim_id"] == "claim-001" for c in result["matched_claims"])


@pytest.mark.unit
def test_claim_by_status_supported() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_status", status="supported")
    result = resolve_claims_v1(fx["claim_records"], req)
    ids = {c["claim_id"] for c in result["matched_claims"]}
    assert "claim-001" in ids
    assert "claim-002" in ids


@pytest.mark.unit
def test_claim_disputed_flagged() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_status", status="disputed")
    result = resolve_claims_v1(fx["claim_records"], req)
    assert "claim-004" in result["disputed_claim_ids"]
    assert "disputed_claims_present" in result["warnings"]


@pytest.mark.unit
def test_claim_stale_flagged() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_status", status="stale")
    result = resolve_claims_v1(fx["claim_records"], req)
    assert "claim-005" in result["stale_claim_ids"]
    assert "stale_claims_present" in result["warnings"]


@pytest.mark.unit
def test_claim_missing_evidence_flagged() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_topic", topic="trust_summary")
    result = resolve_claims_v1(fx["claim_records"], req)
    assert "claim-003" in result["missing_evidence_claim_ids"]
    assert "missing_evidence_on_claims" in result["warnings"]


@pytest.mark.unit
def test_claim_unresolved_evidence_refs() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_topic", topic="stop_conditions")
    known = {"ev-999"}  # ev-001 not in known
    result = resolve_claims_v1(fx["claim_records"], req, known_evidence_ids=known)
    assert "unresolved_evidence_refs_present" in result["warnings"]
    assert "ev-001" in result["unresolved_evidence_refs"]


@pytest.mark.unit
def test_claim_by_artifact() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_artifact", artifact="tools/surrealdb/context_stop_resolver.py")
    result = resolve_claims_v1(fx["claim_records"], req)
    assert any(c["claim_id"] == "claim-001" for c in result["matched_claims"])


@pytest.mark.unit
def test_claim_invalid_status() -> None:
    with pytest.raises(ClaimResolverError, match="unknown claim status"):
        resolve_claims_v1([], ClaimResolveRequest(mode="by_status", status="not_a_status"))


@pytest.mark.unit
def test_claim_no_match_warning() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_topic", topic="nonexistent_topic")
    result = resolve_claims_v1(fx["claim_records"], req)
    assert "no_claims_matched" in result["warnings"]


@pytest.mark.unit
def test_claim_approval_semantics() -> None:
    fx = _load_fixture()
    req = ClaimResolveRequest(mode="by_status", status="supported")
    result = resolve_claims_v1(fx["claim_records"], req)
    sem = result["approval_semantics"]
    assert sem.get("no_echtgeld_go") is True
    assert sem.get("no_approval") is True


# ── Memory Read ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_memory_by_scope() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_scope", scope="wave14")
    result = read_memory_v1(fx["memory_records"], req)
    ids = {m["memory_id"] for m in result["matched_memory"]}
    assert "mem-001" in ids
    assert "mem-002" in ids
    assert "mem-003" not in ids  # scope=wave10


@pytest.mark.unit
def test_memory_by_topic() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_topic", topic="context_tools")
    result = read_memory_v1(fx["memory_records"], req)
    assert any(m["memory_id"] == "mem-001" for m in result["matched_memory"])


@pytest.mark.unit
def test_memory_by_agent() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_agent", agent="codex")
    result = read_memory_v1(fx["memory_records"], req)
    assert all(m["agent"] == "codex" for m in result["matched_memory"])
    assert any(m["memory_id"] == "mem-002" for m in result["matched_memory"])


@pytest.mark.unit
def test_memory_by_artifact() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_artifact", artifact="tools/surrealdb/evidence_lookup.py")
    result = read_memory_v1(fx["memory_records"], req)
    assert any(m["memory_id"] == "mem-001" for m in result["matched_memory"])


@pytest.mark.unit
def test_memory_stale_flagged() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_scope", scope="wave10")
    result = read_memory_v1(fx["memory_records"], req)
    assert "mem-003" in result["stale_memory_ids"]
    assert "stale_memory_present" in result["warnings"]


@pytest.mark.unit
def test_memory_superseded_flagged() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_scope", scope="wave12")
    result = read_memory_v1(fx["memory_records"], req)
    assert "mem-004" in result["superseded_memory_ids"]
    assert "superseded_memory_present" in result["warnings"]


@pytest.mark.unit
def test_memory_by_memory_type() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_memory_type", memory_type="constraint")
    result = read_memory_v1(fx["memory_records"], req)
    assert any(m["memory_id"] == "mem-001" for m in result["matched_memory"])


@pytest.mark.unit
def test_memory_invalid_mode() -> None:
    with pytest.raises(MemoryReadError, match="unsupported mode"):
        read_memory_v1([], MemoryReadRequest(mode="bad_mode"))


@pytest.mark.unit
def test_memory_requires_scope() -> None:
    with pytest.raises(MemoryReadError, match="scope"):
        read_memory_v1([], MemoryReadRequest(mode="by_scope"))


@pytest.mark.unit
def test_memory_no_match_warning() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_scope", scope="no-such-scope")
    result = read_memory_v1(fx["memory_records"], req)
    assert "no_memory_matched" in result["warnings"]


@pytest.mark.unit
def test_memory_approval_semantics() -> None:
    fx = _load_fixture()
    req = MemoryReadRequest(mode="by_scope", scope="wave14")
    result = read_memory_v1(fx["memory_records"], req)
    sem = result["approval_semantics"]
    assert sem.get("no_echtgeld_go") is True
    assert sem.get("no_write") is True


# ── Trust Summary ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_trust_summary_empty_inputs() -> None:
    req = TrustSummaryRequest(scope="wave14-test")
    result = build_trust_summary_v1(req)
    assert result["trust_level"] in ("blocked", "weak", "acceptable", "strong")
    assert result["scope"] == "wave14-test"
    assert result["composite_score"] >= 0.0


@pytest.mark.unit
def test_trust_summary_with_evidence_result() -> None:
    fx = _load_fixture()
    # Use an evidence result with strong overall strength
    ev_req = EvidenceLookupRequest(mode="by_evidence_type", evidence_type="test_run")
    ev_result = lookup_evidence_v1(fx["evidence_records"], ev_req)

    req = TrustSummaryRequest(scope="wave14", topic="context_tools")
    result = build_trust_summary_v1(req, evidence_result=ev_result)
    assert result["evidence_strength"] in ("none", "weak", "moderate", "strong", "blocking_missing")


@pytest.mark.unit
def test_trust_summary_blocked_on_missing_evidence() -> None:
    # A trust result with blocking_missing_ids should yield trust_level=blocked
    ev_result_mock = {
        "evidence_summary": {"overall_strength": "blocking_missing"},
        "blocking_missing_ids": ["ev-004"],
        "stale_evidence_ids": [],
    }
    req = TrustSummaryRequest(scope="wave14", topic="trust_summary")
    result = build_trust_summary_v1(req, evidence_result=ev_result_mock)
    assert result["trust_level"] == "blocked"
    assert "blocking_missing_evidence" in result["blocking_trust_findings"]


@pytest.mark.unit
def test_trust_summary_scope_required() -> None:
    with pytest.raises(TrustSummaryError, match="scope is required"):
        build_trust_summary_v1(TrustSummaryRequest(scope=""))


@pytest.mark.unit
def test_trust_summary_approval_semantics() -> None:
    req = TrustSummaryRequest(scope="wave14")
    result = build_trust_summary_v1(req)
    sem = result["approval_semantics"]
    assert sem.get("no_echtgeld_go") is True
    assert sem.get("no_approval") is True
    assert "trust_level='blocked'" in sem.get("note", "")


@pytest.mark.unit
def test_trust_summary_full_pipeline() -> None:
    """Integration of all four services feeding into trust_summary."""
    fx = _load_fixture()

    ev_req = EvidenceLookupRequest(mode="by_evidence_type", evidence_type="test_run")
    ev_result = lookup_evidence_v1(fx["evidence_records"], ev_req)

    cl_req = ClaimResolveRequest(mode="by_status", status="supported")
    cl_result = resolve_claims_v1(fx["claim_records"], cl_req)

    mem_req = MemoryReadRequest(mode="by_scope", scope="wave14")
    mem_result = read_memory_v1(fx["memory_records"], mem_req)

    trust_req = TrustSummaryRequest(scope="wave14", topic="context_tools")
    result = build_trust_summary_v1(
        trust_req,
        evidence_result=ev_result,
        claim_result=cl_result,
        memory_result=mem_result,
    )

    assert result["schema_version"] == "trust-summary/v1"
    assert result["trust_level"] in ("blocked", "weak", "acceptable", "strong")
    assert isinstance(result["composite_score"], float)
    assert result["confidence_summary"]["composite_score"] == result["composite_score"]
