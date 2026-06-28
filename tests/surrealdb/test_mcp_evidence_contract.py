"""Tests for DB-Record Evidence Response Schema validator (Issue #3421).

Covers:
    - Schema field validation (ok and error paths)
    - Source label enforcement
    - Trust classification consistency
    - Freshness computation and staleness detection
    - LIMIT and filter transparency
    - Secret leak detection
    - Empty results handling
    - no_echtgeld_go enforcement
    - build_ok_response / build_error_response factory functions
    - validate_db_record_evidence_response / enforce_response_contract
"""

from __future__ import annotations

import pytest

from tools.surrealdb.db_record_evidence_response import (
    SCHEMA_VERSION,
    ALLOWED_SOURCES,
    ALLOWED_TOOLS,
    DbRecordEvidenceResponseError,
    build_error_response,
    build_ok_response,
    derive_freshness_signal,
    derive_trust_level,
    enforce_response_contract,
    validate_db_record_evidence_response,
)

# ── derive_trust_level ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_derive_trust_level_valid_db_backed_high():
    assert derive_trust_level("surrealdb-local", "valid_db_backed", 5) == "HIGH"


@pytest.mark.unit
def test_derive_trust_level_valid_db_backed_medium_no_records():
    assert derive_trust_level("surrealdb-local", "valid_db_backed", 0) == "MEDIUM"


@pytest.mark.unit
def test_derive_trust_level_valid_db_backed_in_memory_source():
    assert derive_trust_level("in_memory", "valid_db_backed", 10) == "MEDIUM"


@pytest.mark.unit
def test_derive_trust_level_surrealdb_local_with_records():
    assert derive_trust_level("surrealdb-local", "partial", 3) == "MEDIUM"


@pytest.mark.unit
def test_derive_trust_level_in_memory_low():
    assert derive_trust_level("in_memory", "in_memory_fixture", 5) == "LOW"


@pytest.mark.unit
def test_derive_trust_level_unavailable_low():
    assert derive_trust_level("surrealdb-local-unavailable", "partial", 0) == "LOW"


@pytest.mark.unit
def test_derive_trust_level_empty_records_low():
    assert derive_trust_level("in_memory", "in_memory_fixture", 0) == "LOW"


@pytest.mark.unit
def test_derive_trust_level_invalid_fake_db_blocked():
    assert derive_trust_level("surrealdb-local", "invalid_fake_db", 0) == "BLOCKED"


@pytest.mark.unit
def test_derive_trust_level_unknown_classification_blocked():
    assert derive_trust_level("in_memory", "unknown_type", 5) == "BLOCKED"


# ── derive_freshness_signal ──────────────────────────────────────────────────


@pytest.mark.unit
def test_derive_freshness_signal_fresh():
    assert derive_freshness_signal(30, 3600) == "fresh"


@pytest.mark.unit
def test_derive_freshness_signal_aging():
    assert derive_freshness_signal(1800, 3600) == "aging"


@pytest.mark.unit
def test_derive_freshness_signal_stale():
    assert derive_freshness_signal(4000, 3600) == "stale"


@pytest.mark.unit
def test_derive_freshness_signal_at_boundary():
    assert derive_freshness_signal(3600, 3600) == "aging"


@pytest.mark.unit
def test_derive_freshness_signal_negative_age():
    assert derive_freshness_signal(-1, 3600) == "unknown"


@pytest.mark.unit
def test_derive_freshness_signal_zero_threshold():
    assert derive_freshness_signal(10, 0) == "stale"


# ── build_ok_response ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_build_ok_response_basic():
    records = [{"id": "rec:1", "name": "test"}]
    result = build_ok_response(
        "cdb_context_evidence_resolve",
        "surrealdb-local",
        records,
    )
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["status"] == "ok"
    assert result["tool"] == "cdb_context_evidence_resolve"
    assert result["source"] == "surrealdb-local"
    assert result["record_count"] == 1
    assert result["records"] == records
    assert result["metadata"]["read_only"] is True
    assert result["metadata"]["source"] == "surrealdb-local"
    assert result["trust"]["level"] == "HIGH"
    assert result["trust"]["classification"] == "valid_db_backed"
    assert result["trust"]["confidence"] == 0.9
    assert result["trust"]["source_priority"] == "surrealdb_context"
    assert isinstance(result["freshness"]["is_stale"], bool)
    assert result["no_echtgeld_go"] is True


@pytest.mark.unit
def test_build_ok_response_empty_records():
    result = build_ok_response(
        "cdb_context_memory_get",
        "surrealdb-local",
        [],
    )
    assert result["record_count"] == 0
    assert result["records"] == []
    assert result["trust"]["classification"] == "partial"
    assert result["trust"]["level"] == "LOW"


@pytest.mark.unit
def test_build_ok_response_in_memory_source():
    records = [{"id": "rec:1"}]
    result = build_ok_response(
        "cdb_context_claim_resolve",
        "in_memory",
        records,
    )
    assert result["source"] == "in_memory"
    assert result["trust"]["classification"] == "in_memory_fixture"
    assert result["trust"]["level"] == "LOW"
    assert result["trust"]["confidence"] == 0.3


@pytest.mark.unit
def test_build_ok_response_unavailable_source():
    result = build_ok_response(
        "cdb_context_trust_summary",
        "surrealdb-local-unavailable",
        [],
    )
    assert result["trust"]["classification"] == "partial"
    assert result["trust"]["level"] == "LOW"


@pytest.mark.unit
def test_build_ok_response_explicit_trust():
    records = [{"id": "rec:1"}]
    result = build_ok_response(
        "cdb_context_evidence_resolve",
        "surrealdb-local",
        records,
        trust_level="MEDIUM",
        trust_classification="partial",
        trust_confidence=0.5,
        trust_source_priority="repo_files",
    )
    assert result["trust"]["level"] == "MEDIUM"
    assert result["trust"]["classification"] == "partial"
    assert result["trust"]["confidence"] == 0.5
    assert result["trust"]["source_priority"] == "repo_files"


@pytest.mark.unit
def test_build_ok_response_with_filters():
    records = [{"id": "rec:1"}]
    filters = {"mode": "by_artifact", "artifact": "test.md", "limit": 50}
    result = build_ok_response(
        "cdb_context_evidence_resolve",
        "surrealdb-local",
        records,
        filters_applied=filters,
    )
    assert result["filters_applied"] == filters


@pytest.mark.unit
def test_build_ok_response_extra_limitations():
    result = build_ok_response(
        "cdb_context_memory_get",
        "in_memory",
        [],
        extra_limitations=["test limit"],
    )
    assert "test limit" in result["limitations"]


@pytest.mark.unit
def test_build_ok_response_invalid_source_falls_back():
    records = [{"id": "rec:1"}]
    result = build_ok_response(
        "cdb_context_evidence_resolve",
        "invalid-source",
        records,
    )
    assert result["source"] == "in_memory"


# ── build_error_response ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_build_error_response():
    result = build_error_response(
        "cdb_context_evidence_resolve",
        code="adapter_query_error",
        message="SurrealDB unreachable",
    )
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["status"] == "error"
    assert result["tool"] == "cdb_context_evidence_resolve"
    assert result["error"]["code"] == "adapter_query_error"
    assert result["error"]["message"] == "SurrealDB unreachable"
    assert result["metadata"]["read_only"] is True
    assert result["no_echtgeld_go"] is True


# ── validate_db_record_evidence_response (ok path) ───────────────────────────


@pytest.mark.unit
def test_validate_ok_response_compliant():
    records = [{"id": "rec:1"}]
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "surrealdb-local",
        records,
    )
    violations = validate_db_record_evidence_response(response)
    assert violations == []


@pytest.mark.unit
def test_validate_ok_response_empty_records():
    response = build_ok_response(
        "cdb_context_memory_get",
        "in_memory",
        [],
    )
    violations = validate_db_record_evidence_response(response)
    assert violations == []


@pytest.mark.unit
def test_validate_ok_response_missing_schema_version():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    del response["schema_version"]
    violations = validate_db_record_evidence_response(response)
    assert any("schema_version" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_wrong_schema_version():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["schema_version"] = "wrong/v1"
    violations = validate_db_record_evidence_response(response)
    assert any("schema_version" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_bad_source():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["source"] = "remote-db"
    violations = validate_db_record_evidence_response(response)
    assert any("source" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_record_count_mismatch():
    records = [{"id": "rec:1"}]
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "surrealdb-local",
        records,
    )
    response["record_count"] = 99
    violations = validate_db_record_evidence_response(response)
    assert any("record_count" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_missing_trust():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    del response["trust"]
    violations = validate_db_record_evidence_response(response)
    assert any("trust" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_bad_trust_level():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["trust"]["level"] = "INVALID"
    violations = validate_db_record_evidence_response(response)
    assert any("trust.level" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_trust_level_inconsistent():
    records = [{"id": "rec:1"}]
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "surrealdb-local",
        records,
    )
    # Override to a wrong level for the source+classification
    response["trust"]["level"] = "LOW"
    violations = validate_db_record_evidence_response(response)
    assert any("trust.level" in v and "inconsistent" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_confidence_out_of_range():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["trust"]["confidence"] = 1.5
    violations = validate_db_record_evidence_response(response)
    assert any("confidence" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_confidence_negative():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["trust"]["confidence"] = -0.1
    violations = validate_db_record_evidence_response(response)
    assert any("confidence" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_missing_freshness():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    del response["freshness"]
    violations = validate_db_record_evidence_response(response)
    assert any("freshness" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_is_stale_not_bool():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["freshness"]["is_stale"] = "yes"
    violations = validate_db_record_evidence_response(response)
    assert any("is_stale" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_freshness_inconsistent():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["freshness"]["is_stale"] = True
    response["freshness"]["freshness_signal"] = "fresh"
    violations = validate_db_record_evidence_response(response)
    assert any("freshness" in v and "inconsistent" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_stale_signal_false_stale():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["freshness"]["is_stale"] = False
    response["freshness"]["freshness_signal"] = "stale"
    violations = validate_db_record_evidence_response(response)
    assert any("freshness" in v and "inconsistent" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_missing_no_echtgeld_go():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    del response["no_echtgeld_go"]
    violations = validate_db_record_evidence_response(response)
    assert any("no_echtgeld_go" in v for v in violations)


@pytest.mark.unit
def test_validate_ok_response_no_echtgeld_go_false():
    response = build_ok_response("cdb_context_evidence_resolve", "in_memory", [])
    response["no_echtgeld_go"] = False
    violations = validate_db_record_evidence_response(response)
    assert any("no_echtgeld_go" in v for v in violations)


# ── validate_db_record_evidence_response (error path) ────────────────────────


@pytest.mark.unit
def test_validate_error_response_compliant():
    response = build_error_response(
        "cdb_context_evidence_resolve",
        code="adapter_query_error",
        message="SurrealDB unreachable",
    )
    violations = validate_db_record_evidence_response(response)
    assert violations == []


@pytest.mark.unit
def test_validate_error_response_missing_error():
    response = build_error_response(
        "cdb_context_trust_summary",
        code="adapter_query_error",
        message="test",
    )
    del response["error"]
    violations = validate_db_record_evidence_response(response)
    assert any("error" in v for v in violations)


@pytest.mark.unit
def test_validate_error_response_missing_code():
    response = build_error_response(
        "cdb_context_trust_summary",
        code="adapter_query_error",
        message="test",
    )
    response["error"] = {"message": "test"}
    violations = validate_db_record_evidence_response(response)
    assert any("error.code" in v for v in violations)


# ── enforce_response_contract ────────────────────────────────────────────────


@pytest.mark.unit
def test_enforce_response_contract_passes_on_valid():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    enforce_response_contract(response)


@pytest.mark.unit
def test_enforce_response_contract_raises_on_invalid():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    del response["no_echtgeld_go"]
    with pytest.raises(DbRecordEvidenceResponseError):
        enforce_response_contract(response)


# ── secret leak detection ────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_detects_secret_in_response():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["records"] = [{"password": "Bearer secret123"}]
    violations = validate_db_record_evidence_response(response)
    assert any("secret" in v.lower() for v in violations)


@pytest.mark.unit
def test_validate_detects_surreal_pass():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["metadata"] = {
        "source": "in_memory",
        "read_only": True,
        "query_time_ms": 0,
        "password": "SURREAL_PASS=abc123",
    }
    violations = validate_db_record_evidence_response(response)
    assert any("secret" in v.lower() for v in violations)


# ── non-mapping input ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_non_mapping_input():
    violations = validate_db_record_evidence_response("not a mapping")  # type: ignore[arg-type]
    assert any("mapping" in v for v in violations)


# ── unknown status ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_unknown_status():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["status"] = "unknown"
    violations = validate_db_record_evidence_response(response)
    assert any("status" in v for v in violations)


# ── records not a list ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_records_not_list():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["records"] = {"not": "a list"}
    violations = validate_db_record_evidence_response(response)
    assert any("records" in v for v in violations)


# ── filters_applied not a mapping ────────────────────────────────────────────


@pytest.mark.unit
def test_validate_filters_applied_not_mapping():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["filters_applied"] = ["not", "a", "mapping"]
    violations = validate_db_record_evidence_response(response)
    assert any("filters_applied" in v for v in violations)


# ── missing record_count ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_missing_record_count():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    del response["record_count"]
    violations = validate_db_record_evidence_response(response)
    assert any("record_count" in v for v in violations)


# ── tool not in allowed set ──────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_bad_tool_name():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["tool"] = "not_a_tool"
    violations = validate_db_record_evidence_response(response)
    assert any("tool" in v for v in violations)


# ── limitations not a list ───────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_limitations_not_list():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["limitations"] = "not a list"
    violations = validate_db_record_evidence_response(response)
    assert any("limitations" in v for v in violations)


# ── freshness negative age ───────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_freshness_negative_age():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["freshness"]["age_seconds"] = -5
    violations = validate_db_record_evidence_response(response)
    assert any("age_seconds" in v for v in violations)


# ── freshness zero threshold ─────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_freshness_zero_threshold():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["freshness"]["stale_threshold_seconds"] = 0
    violations = validate_db_record_evidence_response(response)
    assert any("stale_threshold_seconds" in v for v in violations)


# ── trust cross-validation: trust classification consistency ─────────────────


@pytest.mark.unit
def test_validate_trust_bad_classification():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["trust"]["classification"] = "unknown_classification"
    violations = validate_db_record_evidence_response(response)
    assert any("classification" in v for v in violations)


@pytest.mark.unit
def test_validate_trust_bad_source_priority():
    response = build_ok_response(
        "cdb_context_evidence_resolve",
        "in_memory",
        [],
    )
    response["trust"]["source_priority"] = "unknown_source"
    violations = validate_db_record_evidence_response(response)
    assert any("source_priority" in v for v in violations)
