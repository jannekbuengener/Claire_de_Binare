"""Unit tests for claim evidence at rest enforcement — #2719."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tools.surrealdb.claim_evidence_at_rest import (
    ClaimEvidenceAtRestError,
    enforce_claim_records_at_rest,
    prove_claim_evidence_at_rest_db_v1,
    reject_caller_metadata_as_evidence,
    validate_claim_record_structure,
    validate_evidence_refs_resolve,
)

_SCOPE = "memory_db_proof:unittest"


def _evidence_row(evidence_id: str, *, scope: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "evidence_id": evidence_id,
        "evidence_type": "test_run",
    }
    if scope is not None:
        row["scope"] = scope
    return row


def _claim_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "claim_id": "claim-unit-001",
        "scope": _SCOPE,
        "status": "supported",
        "evidence_refs": ["ev-unit-001"],
        "title": "unit claim",
        "statement": "unit claim statement",
    }
    base.update(overrides)
    return base


def _mock_adapter(
    claim_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> MagicMock:
    adapter = MagicMock()
    adapter.status = "surrealdb-local"

    def _execute(query: str) -> list[dict[str, Any]]:
        if "FROM claim" in query:
            return claim_rows
        if "FROM evidence_ref" in query:
            return evidence_rows
        return []

    adapter.execute.side_effect = _execute
    return adapter


@pytest.mark.unit
def test_validate_claim_record_structure_requires_evidence_refs_for_supported() -> None:
    with pytest.raises(ClaimEvidenceAtRestError, match="evidence_refs required"):
        validate_claim_record_structure(
            _claim_row(status="supported", evidence_refs=[])
        )


@pytest.mark.unit
def test_validate_evidence_refs_resolve_blocks_bogus_ref() -> None:
    claim = validate_claim_record_structure(_claim_row())
    with pytest.raises(ClaimEvidenceAtRestError, match="not found at rest"):
        validate_evidence_refs_resolve(claim, {})


@pytest.mark.unit
def test_validate_evidence_refs_resolve_blocks_scope_mismatch() -> None:
    claim = validate_claim_record_structure(_claim_row())
    index = {"ev-unit-001": _evidence_row("ev-unit-001", scope="other_scope")}
    with pytest.raises(ClaimEvidenceAtRestError, match="scope mismatch"):
        validate_evidence_refs_resolve(claim, index, require_scope_match=True)


@pytest.mark.unit
def test_reject_caller_metadata_as_evidence_blocks_brain_source() -> None:
    with pytest.raises(ClaimEvidenceAtRestError, match="cannot substitute"):
        reject_caller_metadata_as_evidence(
            {"brain_source": "repo-only"},
            known_evidence_ids=frozenset(),
        )


@pytest.mark.unit
def test_reject_caller_metadata_blocks_unbacked_evidence_id() -> None:
    with pytest.raises(ClaimEvidenceAtRestError, match="not backed"):
        reject_caller_metadata_as_evidence(
            {"evidence_id": "ev-fake-999"},
            known_evidence_ids=frozenset({"ev-unit-001"}),
        )


@pytest.mark.unit
def test_enforce_claim_records_at_rest_valid_batch() -> None:
    evidence = [_evidence_row("ev-unit-001")]
    claims = [_claim_row()]
    result = enforce_claim_records_at_rest(claims, evidence)
    assert result["schema_version"] == "claim-evidence-at-rest/v1"
    assert result["valid_claim_count"] == 1
    assert len(result["claim_resolution"]["matched_claims"]) == 1


@pytest.mark.unit
def test_prove_claim_evidence_at_rest_db_v1_passes_with_adapter() -> None:
    claim = _claim_row()
    evidence = _evidence_row("ev-unit-001")
    adapter = _mock_adapter([claim], [evidence])
    proof = prove_claim_evidence_at_rest_db_v1(adapter, scope=_SCOPE, limit=10)
    assert proof["schema_version"] == "claim-evidence-at-rest/v1"
    assert proof["claim_count"] == 1
    assert "SURREAL_PASS" not in str(proof)
    assert proof["approval_semantics"]["no_live_go"] is True


@pytest.mark.unit
def test_prove_claim_evidence_at_rest_db_v1_blocks_missing_evidence_ref() -> None:
    claim = _claim_row(evidence_refs=["ev-missing"])
    adapter = _mock_adapter([claim], [])
    with pytest.raises(ClaimEvidenceAtRestError, match="blocked row"):
        prove_claim_evidence_at_rest_db_v1(adapter, scope=_SCOPE, limit=10)


@pytest.mark.unit
def test_envelope_has_no_secret_substrings() -> None:
    adapter = _mock_adapter(
        [_claim_row()],
        [_evidence_row("ev-unit-001")],
    )
    proof = prove_claim_evidence_at_rest_db_v1(adapter, scope=_SCOPE, limit=5)
    rendered = str(proof)
    assert "SURREAL_PASS" not in rendered
    assert "Authorization" not in rendered
