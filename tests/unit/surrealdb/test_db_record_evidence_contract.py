"""Unit tests for DB-record evidence contract (#2851)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.db_record_evidence_contract import (
    ACCEPTED_LIMITATION_CODES,
    SCHEMA_VERSION,
    build_example_claim,
    classify_trust,
    compute_determinism_hash,
    redact_for_summary,
    validate_db_record_evidence_claim,
)

EXAMPLES_DIR = Path("docs/contracts/examples")


def _load_example(name: str) -> dict:
    data = json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))
    data["determinism_hash"] = compute_determinism_hash(data)
    return data


@pytest.mark.unit
def test_valid_db_backed_example_passes_validator() -> None:
    claim = _load_example("db_record_evidence_valid.json")
    assert classify_trust(claim) == "valid_db_backed"
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_invalid_fake_db_example_classifies_but_has_no_valid_db_proof() -> None:
    claim = _load_example("db_record_evidence_invalid_fake_db.json")
    assert classify_trust(claim) == "invalid_fake_db"
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_accepted_limitation_example_passes() -> None:
    claim = _load_example("db_record_evidence_accepted_limitation.json")
    assert classify_trust(claim) == "accepted_limitation"
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_repo_only_baseline_from_builder() -> None:
    claim = build_example_claim()
    assert classify_trust(claim) == "repo_only"
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_caller_brain_source_without_records_is_invalid_fake_db() -> None:
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
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_secret_substring_rejected() -> None:
    claim = build_example_claim(
        claim_text_or_summary="api_key=super-secret-value",
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    violations = validate_db_record_evidence_claim(claim)
    assert any("secret" in v.lower() for v in violations)


@pytest.mark.unit
def test_redact_for_summary_masks_secrets() -> None:
    claim = build_example_claim(
        claim_text_or_summary="SURREAL_PASS=must-not-appear",
    )
    redacted = redact_for_summary(claim)
    assert "[REDACTED]" in redacted["claim_text_or_summary"]


@pytest.mark.unit
def test_determinism_hash_stable_and_excludes_freshness() -> None:
    claim = build_example_claim(
        record_timestamps_or_freshness_signal="2026-06-03T18:00:00Z",
    )
    h1 = compute_determinism_hash(claim)
    claim2 = dict(claim)
    claim2["record_timestamps_or_freshness_signal"] = "2026-06-04T19:00:00Z"
    h2 = compute_determinism_hash(claim2)
    assert h1 == h2
    claim["determinism_hash"] = h1
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_determinism_hash_mismatch_reported() -> None:
    claim = build_example_claim()
    claim["determinism_hash"] = "0" * 64
    violations = validate_db_record_evidence_claim(claim)
    assert any("determinism_hash mismatch" in v for v in violations)


@pytest.mark.unit
def test_valid_db_backed_requires_record_proof() -> None:
    claim = build_example_claim(
        record_source="surrealdb-local",
        trust_classification="valid_db_backed",
        source_priority="surrealdb_context",
        producer_tool="cdb_context_evidence_resolve",
        query_or_lookup_fingerprint="SELECT 1",
        record_ids=["evidence_ref:test"],
        limitations=["LR NO-GO"],
    )
    claim["determinism_hash"] = compute_determinism_hash(claim)
    assert validate_db_record_evidence_claim(claim) == []


@pytest.mark.unit
def test_accepted_limitation_codes_align_with_harness() -> None:
    from tools.surrealdb.context_live_invocation_harness import (
        PASS_WITH_LIMITS_ERROR_CODES,
    )

    assert ACCEPTED_LIMITATION_CODES == PASS_WITH_LIMITS_ERROR_CODES


@pytest.mark.unit
def test_schema_version_constant() -> None:
    claim = build_example_claim()
    assert claim["schema_version"] == SCHEMA_VERSION
