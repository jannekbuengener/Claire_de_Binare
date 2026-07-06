"""Evidence Resolver regression tests (#3773).

Refs #3771. Systematic coverage for claim/evidence resolution classes and
DB-backed claim boundaries. Uses fixture-backed in-memory records only; no
live SurrealDB required in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp.context_evidence_memory_tools import (
    handle_cdb_context_claim_resolve,
    handle_cdb_context_evidence_resolve,
)
from tools.surrealdb.claim_evidence_at_rest import reject_caller_metadata_as_evidence
from tools.surrealdb.claim_resolver import ClaimResolveRequest, resolve_claims_v1
from tools.surrealdb.db_record_evidence_contract import (
    build_example_claim,
    classify_trust,
    compute_determinism_hash,
    validate_db_record_evidence_claim,
)
from tools.surrealdb.evidence_lookup import EvidenceLookupRequest, lookup_evidence_v1

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _resolve_claims(
    fx: dict,
    *,
    mode: str | None = None,
    claim_id: str | None = None,
    status: str | None = None,
    topic: str | None = None,
    known_evidence_ids: set[str] | None = None,
) -> dict:
    resolved_mode = mode
    if resolved_mode is None:
        if claim_id is not None:
            resolved_mode = "by_claim_id"
        elif status is not None:
            resolved_mode = "by_status"
        elif topic is not None:
            resolved_mode = "by_topic"
        else:
            resolved_mode = "by_claim_id"
    return resolve_claims_v1(
        fx["claim_records"],
        ClaimResolveRequest(
            mode=resolved_mode,
            claim_id=claim_id,
            status=status,
            topic=topic,
        ),
        known_evidence_ids=known_evidence_ids,
    )


def _lookup_evidence(
    fx: dict,
    *,
    mode: str | None = None,
    claim: str | None = None,
    artifact: str | None = None,
    evidence_type: str | None = None,
) -> dict:
    resolved_mode = mode
    if resolved_mode is None:
        if claim is not None:
            resolved_mode = "by_claim"
        elif artifact is not None:
            resolved_mode = "by_artifact"
        elif evidence_type is not None:
            resolved_mode = "by_evidence_type"
        else:
            resolved_mode = "by_claim"
    return lookup_evidence_v1(
        fx["evidence_records"],
        EvidenceLookupRequest(
            mode=resolved_mode,
            claim=claim,
            artifact=artifact,
            evidence_type=evidence_type,
        ),
    )


# ---------------------------------------------------------------------------
# Claim classification: supported / contradicted / stale / weak / missing
# ---------------------------------------------------------------------------


def test_supported_claim_has_resolved_evidence_refs() -> None:
    """Supported claim with real fixture evidence stays supported, not missing."""
    fx = _load_fixture()
    result = _resolve_claims(fx, claim_id="claim-001")
    matched = result["matched_claims"]
    assert len(matched) == 1
    claim = matched[0]
    assert claim["status"] == "supported"
    assert claim["evidence_refs"] == ["ev-001"]
    assert "claim-001" not in result["missing_evidence_claim_ids"]

    ev = _lookup_evidence(fx, claim="claim-001")
    assert any(row["evidence_id"] == "ev-001" for row in ev["matched_evidence"])
    assert ev["evidence_summary"]["overall_strength"] in {"strong", "moderate"}


def test_contradicted_claim_maps_to_disputed_status() -> None:
    """Contradicted claims surface as disputed with explicit warning bucket."""
    fx = _load_fixture()
    result = _resolve_claims(fx, claim_id="claim-004")
    claim = result["matched_claims"][0]
    assert claim["status"] == "disputed"
    assert "claim-004" in result["disputed_claim_ids"]
    assert "disputed_claims_present" in result["warnings"]


def test_stale_claim_and_stale_evidence_are_flagged() -> None:
    """Stale classification applies to both claim rows and evidence rows."""
    fx = _load_fixture()
    claim_result = _resolve_claims(fx, status="stale")
    assert "claim-005" in claim_result["stale_claim_ids"]
    assert "stale_claims_present" in claim_result["warnings"]

    ev_result = _lookup_evidence(
        fx,
        mode="by_evidence_type",
        evidence_type="test_run",
    )
    assert "ev-005" in ev_result["stale_evidence_ids"]
    assert "stale_evidence_present" in ev_result["warnings"]


def test_weak_claim_and_weak_evidence_strength() -> None:
    """Weakly supported claims and low-confidence evidence stay weak."""
    fx = _load_fixture()
    claim_result = _resolve_claims(fx, topic="trust_summary")
    claim = claim_result["matched_claims"][0]
    assert claim["status"] == "weakly_supported"
    assert claim["missing_evidence_blocker"] is True
    assert "claim-003" in claim_result["missing_evidence_claim_ids"]

    ev_result = _lookup_evidence(fx, artifact="tools/surrealdb/trust_summary.py")
    strengths = {
        row["evidence_id"]: row["strength"]
        for row in ev_result["matched_evidence"]
    }
    assert strengths.get("ev-004") == "blocking_missing"
    assert "blocking_missing_evidence_present" in ev_result["warnings"]

    assumed = _lookup_evidence(
        fx,
        mode="by_evidence_type",
        evidence_type="assumed",
    )
    assert assumed["matched_evidence"][0]["strength"] == "weak"


def test_missing_evidence_claim_stays_non_supported() -> None:
    """Claims without backing evidence remain missing/blocking, not supported."""
    fx = _load_fixture()
    result = _resolve_claims(fx, topic="trust_summary")
    assert "missing_evidence_on_claims" in result["warnings"]
    assert result["matched_claims"][0]["evidence_refs"] == []

    empty = resolve_claims_v1(
        [
            {
                "claim_id": "claim-missing-3773",
                "status": "proposed",
                "scope": "wave14",
                "topic": "regression",
                "topics": ["regression"],
                "evidence_refs": [],
            }
        ],
        ClaimResolveRequest(mode="by_topic", topic="regression"),
    )
    assert empty["matched_claims"][0]["status"] == "proposed"
    assert empty["matched_claims"][0]["missing_evidence_blocker"] is False
    assert empty["missing_evidence_claim_ids"] == []


# ---------------------------------------------------------------------------
# DB-backed claim boundaries
# ---------------------------------------------------------------------------


def test_caller_supplied_metadata_is_not_db_proof() -> None:
    """Caller brain_source/metadata.source cannot substitute record proof."""
    claim = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="invalid_fake_db",
        record_ids=[],
        record_hashes_or_content_fingerprints=[],
        caller_evidence={
            "brain_source": "surrealdb-local",
            "metadata_source": "surrealdb-local",
        },
        limitations=["caller metadata ignored"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert classify_trust(claim) == "invalid_fake_db"
    assert validate_db_record_evidence_claim(claim) == []

    with pytest.raises(Exception, match="cannot substitute"):
        reject_caller_metadata_as_evidence(
            {"brain_source": "surrealdb-local"},
            known_evidence_ids=frozenset(),
        )


def test_pr_body_summary_cannot_promote_valid_db_backed() -> None:
    """PR-body prose with live_github priority is not valid DB-backed proof."""
    claim = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="valid_db_backed",
        source_priority="live_github",
        claim_text_or_summary=(
            "Merged per PR #9999 body; no adapter record IDs attached."
        ),
        record_ids=[],
        record_hashes_or_content_fingerprints=[],
        caller_evidence={"brain_source": "surrealdb-local"},
        limitations=["pr_body_only_not_db_proof"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert classify_trust(claim) == "invalid_fake_db"
    violations = validate_db_record_evidence_claim(claim)
    assert any("inconsistent" in v or "valid_db_backed" in v for v in violations)


def test_ledger_snapshot_cannot_promote_valid_db_backed() -> None:
    """Ledger/CURRENT_STATUS wording stays repo-only, not DB-backed."""
    claim = build_example_claim(
        record_source="repo-only",
        trust_classification="repo_only",
        source_priority="ledger_snapshots",
        claim_text_or_summary="CURRENT_STATUS.md ledger says issue is done.",
        repo_crosscheck={"path": "CURRENT_STATUS.md", "commit": "395dc3d9"},
        limitations=["ledger_snapshots are not live GitHub truth"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert classify_trust(claim) == "repo_only"
    assert validate_db_record_evidence_claim(claim) == []

    forged = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="valid_db_backed",
        source_priority="ledger_snapshots",
        claim_text_or_summary="Ledger implies surrealdb-local record proof.",
        record_ids=[],
        repo_crosscheck={"path": "CURRENT_STATUS.md"},
        limitations=["ledger cannot assert DB proof"],
    )
    forged["determinism_hash"] = compute_determinism_hash(forged)
    assert classify_trust(forged) in {"invalid_fake_db", "partial"}


def test_local_staged_file_cannot_promote_valid_db_backed() -> None:
    """Local/staged file paths alone do not yield valid_db_backed classification."""
    claim = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="valid_db_backed",
        source_priority="repo_files",
        claim_text_or_summary="Staged local file proves DB closure.",
        record_ids=[],
        record_hashes_or_content_fingerprints=[],
        repo_crosscheck={
            "path": "knowledge/logs/sessions/staged-local-only.md",
            "commit": "uncommitted",
        },
        limitations=["local staged file is not DB proof"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert classify_trust(claim) in {"invalid_fake_db", "partial"}
    violations = validate_db_record_evidence_claim(claim)
    assert violations


# ---------------------------------------------------------------------------
# Deterministic evidence links
# ---------------------------------------------------------------------------


def test_resolver_outputs_are_deterministic_across_repeated_calls() -> None:
    """Evidence/claim links and ref ordering stay reproducible."""
    fx = _load_fixture()
    claim_req = ClaimResolveRequest(mode="by_status", status="supported")
    first = resolve_claims_v1(fx["claim_records"], claim_req)
    second = resolve_claims_v1(fx["claim_records"], claim_req)

    assert first["all_evidence_refs"] == second["all_evidence_refs"]
    assert [c["claim_id"] for c in first["matched_claims"]] == [
        c["claim_id"] for c in second["matched_claims"]
    ]

    ev_req = EvidenceLookupRequest(mode="by_claim", claim="claim-001")
    ev_a = lookup_evidence_v1(fx["evidence_records"], ev_req)
    ev_b = lookup_evidence_v1(fx["evidence_records"], ev_req)
    assert ev_a["evidence_by_strength"] == ev_b["evidence_by_strength"]
    assert [e["evidence_id"] for e in ev_a["matched_evidence"]] == [
        e["evidence_id"] for e in ev_b["matched_evidence"]
    ]

    claim = build_example_claim(
        record_ids=["evidence_ref:ev-regression-3773"],
        record_hashes_or_content_fingerprints=["sha256:" + "a" * 64],
        record_source="surrealdb-local",
        trust_classification="valid_db_backed",
        limitations=["LR NO-GO"],
    )
    h1 = compute_determinism_hash(claim)
    h2 = compute_determinism_hash(dict(claim))
    assert h1 == h2


# ---------------------------------------------------------------------------
# MCP handler regression (cdb_context_*_resolve)
# ---------------------------------------------------------------------------


def test_mcp_evidence_resolve_preserves_domain_classification() -> None:
    """cdb_context_evidence_resolve must not upgrade weak/stale/missing evidence."""
    fx = _load_fixture()
    response = handle_cdb_context_evidence_resolve(
        {
            "tool": "cdb_context_evidence_resolve",
            "parameters": {
                "mode": "by_evidence_type",
                "evidence_type": "test_run",
                "evidence_records": fx["evidence_records"],
            },
        }
    )
    assert response["status"] == "ok"
    result = response["result"]
    assert response["metadata"]["source"] == "in_memory"
    assert "stale_evidence_present" in result["warnings"]
    assert result["evidence_summary"]["overall_strength"] in {
        "weak",
        "moderate",
        "strong",
        "blocking_missing",
    }


def test_mcp_claim_resolve_preserves_disputed_and_missing_buckets() -> None:
    """cdb_context_claim_resolve surfaces disputed/stale/missing claim buckets."""
    fx = _load_fixture()
    response = handle_cdb_context_claim_resolve(
        {
            "tool": "cdb_context_claim_resolve",
            "parameters": {
                "mode": "by_status",
                "status": "disputed",
                "claim_records": fx["claim_records"],
            },
        }
    )
    assert response["status"] == "ok"
    result = response["result"]
    assert response["metadata"]["source"] == "in_memory"
    assert "claim-004" in result["disputed_claim_ids"]
    assert "disputed_claims_present" in result["warnings"]

    missing = handle_cdb_context_claim_resolve(
        {
            "tool": "cdb_context_claim_resolve",
            "parameters": {
                "mode": "by_topic",
                "topic": "trust_summary",
                "claim_records": fx["claim_records"],
            },
        }
    )
    missing_result = missing["result"]
    assert "claim-003" in missing_result["missing_evidence_claim_ids"]


def test_mcp_handlers_ignore_forged_db_source_metadata() -> None:
    """Forged surrealdb-local metadata on in-memory path stays in_memory source."""
    fx = _load_fixture()
    forged = {
        "source": "surrealdb-local",
        "brain_source": "surrealdb-local",
        "brain_status": "used",
        "metadata": {"source": "surrealdb-local"},
    }
    ev = handle_cdb_context_evidence_resolve(
        {
            "tool": "cdb_context_evidence_resolve",
            "parameters": {
                "mode": "by_claim",
                "claim": "claim-001",
                "evidence_records": fx["evidence_records"],
                **forged,
            },
        }
    )
    assert ev["metadata"]["source"] == "in_memory"

    cl = handle_cdb_context_claim_resolve(
        {
            "tool": "cdb_context_claim_resolve",
            "parameters": {
                "mode": "by_claim_id",
                "claim_id": "claim-001",
                "claim_records": fx["claim_records"],
                **forged,
            },
        }
    )
    assert cl["metadata"]["source"] == "in_memory"
