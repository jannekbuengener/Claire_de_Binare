"""Unit tests for memory agent output contract enforcement.

Issue: #2701 — enforce agent output contract on memory MCP tools
Parent: #2606 (Langzeitgedaechtnis / Persistent Agent Memory)

Validates that:
    - All four Wave-14 memory/evidence MCP handlers produce responses that
      pass ``validate_memory_output_contract``.
    - ``stamp_limitations`` injects default limitations when absent.
    - ``enforce_memory_output_contract`` raises on violations.
    - Per-record ``memory_id`` and ``trust_level`` are present in matched_memory.
    - ``metadata.source`` uses guarded values from the allowed set.
    - Error responses are not subject to contract validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.mcp.memory_output_contract import (
    ALLOWED_SOURCE_LABELS,
    MEMORY_OUTPUT_CONTRACT_VERSION,
    MemoryOutputContractError,
    default_limitations,
    enforce_memory_output_contract,
    stamp_limitations,
    validate_memory_output_contract,
)
from tools.mcp.context_evidence_memory_tools import (
    TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
    TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
    TOOL_CDB_CONTEXT_MEMORY_GET,
    TOOL_CDB_CONTEXT_TRUST_SUMMARY,
    handle_cdb_context_evidence_resolve,
    handle_cdb_context_claim_resolve,
    handle_cdb_context_memory_get,
    handle_cdb_context_trust_summary,
)

pytestmark = pytest.mark.unit

FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ── Contract module unit tests ───────────────────────────────────────────────


class TestContractVersion:
    def test_version_string_defined(self) -> None:
        assert MEMORY_OUTPUT_CONTRACT_VERSION == "memory-output-contract/v1"


class TestDefaultLimitations:
    def test_returns_list(self) -> None:
        lims = default_limitations()
        assert isinstance(lims, list)
        assert len(lims) >= 1

    def test_returns_fresh_copy(self) -> None:
        a = default_limitations()
        b = default_limitations()
        assert a == b
        assert a is not b

    def test_contains_no_go_guardrail(self) -> None:
        text = " ".join(default_limitations())
        assert "NO-GO" in text


class TestStampLimitations:
    def test_adds_limitations_when_absent(self) -> None:
        result: dict[str, Any] = {"trust_level": "weak"}
        stamp_limitations(result)
        assert "limitations" in result
        assert len(result["limitations"]) >= 1

    def test_preserves_existing_limitations(self) -> None:
        result: dict[str, Any] = {"limitations": ["custom limitation"]}
        stamp_limitations(result)
        assert "custom limitation" in result["limitations"]
        assert len(result["limitations"]) > 1

    def test_deduplicates(self) -> None:
        result: dict[str, Any] = {"limitations": list(default_limitations())}
        stamp_limitations(result)
        assert len(result["limitations"]) == len(set(result["limitations"]))

    def test_extra_appended(self) -> None:
        result: dict[str, Any] = {}
        stamp_limitations(result, extra=["extra item"])
        assert "extra item" in result["limitations"]


class TestValidateContract:
    def test_minimal_valid_memory_response(self) -> None:
        response = {
            "tool": "cdb_context_memory_get",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {
                "limitations": ["test"],
                "matched_memory": [
                    {"memory_id": "m-1", "trust_level": "weak"}
                ],
                "memory_summary": {"overall_trust": "weak"},
            },
        }
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_missing_tool_field(self) -> None:
        response = {
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {"limitations": ["x"]},
        }
        violations = validate_memory_output_contract(response)
        assert any("tool" in v for v in violations)

    def test_missing_metadata_source(self) -> None:
        response = {
            "tool": "t",
            "status": "ok",
            "metadata": {"read_only": True},
            "result": {"limitations": ["x"]},
        }
        violations = validate_memory_output_contract(response)
        assert any("source" in v for v in violations)

    def test_invalid_source_label(self) -> None:
        response = {
            "tool": "t",
            "status": "ok",
            "metadata": {"source": "spoofed-value", "read_only": True},
            "result": {"limitations": ["x"]},
        }
        violations = validate_memory_output_contract(response)
        assert any("spoofed-value" in v for v in violations)

    def test_missing_limitations(self) -> None:
        response = {
            "tool": "t",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {},
        }
        violations = validate_memory_output_contract(response)
        assert any("limitations" in v for v in violations)

    def test_missing_trust_when_memory_present(self) -> None:
        response = {
            "tool": "t",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {
                "limitations": ["x"],
                "matched_memory": [{"memory_id": "m-1"}],
            },
        }
        violations = validate_memory_output_contract(response)
        assert any("trust" in v.lower() for v in violations)

    def test_trust_not_required_when_confidence_summary_only(self) -> None:
        """claim-resolve has confidence_summary with stats, not trust context."""
        response = {
            "tool": "cdb_context_claim_resolve",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {
                "limitations": ["x"],
                "matched_claims": [{"claim_id": "c-1"}],
                "confidence_summary": {"min": 0.8, "max": 0.95, "avg": 0.9, "count": 2},
            },
        }
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_trust_not_required_for_evidence_claim(self) -> None:
        response = {
            "tool": "cdb_context_evidence_resolve",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {
                "limitations": ["x"],
                "matched_evidence": [{"evidence_id": "ev-1"}],
            },
        }
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_per_record_memory_id_required(self) -> None:
        response = {
            "tool": "t",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {
                "limitations": ["x"],
                "matched_memory": [
                    {"trust_level": "weak"},
                ],
                "memory_summary": {"overall_trust": "weak"},
            },
        }
        violations = validate_memory_output_contract(response)
        assert any("memory_id" in v for v in violations)

    def test_per_record_trust_level_required(self) -> None:
        response = {
            "tool": "t",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {
                "limitations": ["x"],
                "matched_memory": [
                    {"memory_id": "m-1"},
                ],
                "memory_summary": {"overall_trust": "weak"},
            },
        }
        violations = validate_memory_output_contract(response)
        assert any("trust_level" in v for v in violations)

    def test_error_responses_skip_result_checks(self) -> None:
        response = {
            "tool": "t",
            "status": "error",
            "error": {"code": "test", "message": "msg"},
            "metadata": {"source": "in_memory", "read_only": True},
        }
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_allowed_source_labels_complete(self) -> None:
        assert "in_memory" in ALLOWED_SOURCE_LABELS
        assert "surrealdb-local" in ALLOWED_SOURCE_LABELS
        assert "surrealdb-local-unavailable" in ALLOWED_SOURCE_LABELS


class TestEnforceContract:
    def test_raises_on_violation(self) -> None:
        bad = {"status": "ok", "metadata": {}, "result": {}}
        with pytest.raises(MemoryOutputContractError):
            enforce_memory_output_contract(bad)

    def test_passes_on_valid(self) -> None:
        good = {
            "tool": "t",
            "status": "ok",
            "metadata": {"source": "in_memory", "read_only": True},
            "result": {"limitations": ["x"]},
        }
        enforce_memory_output_contract(good)


# ── Handler integration: contract compliance ─────────────────────────────────


class TestMemoryGetOutputContract:
    """Verify cdb_context_memory_get output satisfies the memory output contract."""

    def test_contract_compliant(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_memory_get({
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "mode": "by_scope",
                "scope": "wave14",
                "memory_records": fx["memory_records"],
            },
        })
        violations = validate_memory_output_contract(response)
        assert violations == [], f"Contract violations: {violations}"

    def test_has_limitations(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_memory_get({
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "mode": "by_scope",
                "scope": "wave14",
                "memory_records": fx["memory_records"],
            },
        })
        assert isinstance(response["result"]["limitations"], list)
        assert len(response["result"]["limitations"]) >= 1

    def test_per_record_memory_id_present(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_memory_get({
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "mode": "by_scope",
                "scope": "wave14",
                "memory_records": fx["memory_records"],
            },
        })
        for record in response["result"]["matched_memory"]:
            assert "memory_id" in record, f"missing memory_id in {record}"
            assert "trust_level" in record, f"missing trust_level in {record}"

    def test_metadata_source_guarded(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_memory_get({
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {
                "mode": "by_scope",
                "scope": "wave14",
                "memory_records": fx["memory_records"],
            },
        })
        assert response["metadata"]["source"] in ALLOWED_SOURCE_LABELS


class TestTrustSummaryOutputContract:
    """Verify cdb_context_trust_summary output satisfies the memory output contract."""

    def test_contract_compliant(self) -> None:
        response = handle_cdb_context_trust_summary({
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {"scope": "wave14"},
        })
        violations = validate_memory_output_contract(response)
        assert violations == [], f"Contract violations: {violations}"

    def test_has_limitations(self) -> None:
        response = handle_cdb_context_trust_summary({
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {"scope": "wave14"},
        })
        assert isinstance(response["result"]["limitations"], list)
        assert len(response["result"]["limitations"]) >= 1

    def test_trust_level_present(self) -> None:
        response = handle_cdb_context_trust_summary({
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {"scope": "wave14"},
        })
        assert response["result"]["trust_level"] in (
            "blocked", "weak", "acceptable", "strong"
        )

    def test_metadata_source_guarded(self) -> None:
        response = handle_cdb_context_trust_summary({
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {"scope": "wave14"},
        })
        assert response["metadata"]["source"] in ALLOWED_SOURCE_LABELS


class TestEvidenceResolveOutputContract:
    """Verify cdb_context_evidence_resolve satisfies source + limitations."""

    def test_contract_compliant(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_evidence_resolve({
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/context_stop_resolver.py",
                "evidence_records": fx["evidence_records"],
            },
        })
        violations = validate_memory_output_contract(response)
        assert violations == [], f"Contract violations: {violations}"

    def test_has_limitations(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_evidence_resolve({
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/context_stop_resolver.py",
                "evidence_records": fx["evidence_records"],
            },
        })
        assert isinstance(response["result"]["limitations"], list)
        assert len(response["result"]["limitations"]) >= 1

    def test_metadata_source_guarded(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_evidence_resolve({
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {
                "mode": "by_artifact",
                "artifact": "tools/surrealdb/context_stop_resolver.py",
                "evidence_records": fx["evidence_records"],
            },
        })
        assert response["metadata"]["source"] in ALLOWED_SOURCE_LABELS


class TestClaimResolveOutputContract:
    """Verify cdb_context_claim_resolve satisfies source + limitations."""

    def test_contract_compliant(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_claim_resolve({
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "mode": "by_topic",
                "topic": "stop_conditions",
                "claim_records": fx["claim_records"],
            },
        })
        violations = validate_memory_output_contract(response)
        assert violations == [], f"Contract violations: {violations}"

    def test_has_limitations(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_claim_resolve({
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "mode": "by_topic",
                "topic": "stop_conditions",
                "claim_records": fx["claim_records"],
            },
        })
        assert isinstance(response["result"]["limitations"], list)
        assert len(response["result"]["limitations"]) >= 1

    def test_metadata_source_guarded(self) -> None:
        fx = _load_fixture()
        response = handle_cdb_context_claim_resolve({
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {
                "mode": "by_topic",
                "topic": "stop_conditions",
                "claim_records": fx["claim_records"],
            },
        })
        assert response["metadata"]["source"] in ALLOWED_SOURCE_LABELS


# ── Error response exclusions ────────────────────────────────────────────────


class TestErrorResponsesExcluded:
    """Error responses should not be flagged for missing contract fields."""

    def test_memory_get_error_passes_contract(self) -> None:
        response = handle_cdb_context_memory_get({
            "tool": TOOL_CDB_CONTEXT_MEMORY_GET,
            "parameters": {"mode": "by_scope", "scope": "x"},
        })
        assert response["status"] == "error"
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_trust_summary_error_passes_contract(self) -> None:
        response = handle_cdb_context_trust_summary({
            "tool": TOOL_CDB_CONTEXT_TRUST_SUMMARY,
            "parameters": {},
        })
        assert response["status"] == "error"
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_evidence_error_passes_contract(self) -> None:
        response = handle_cdb_context_evidence_resolve({
            "tool": TOOL_CDB_CONTEXT_EVIDENCE_RESOLVE,
            "parameters": {"mode": "by_artifact", "artifact": "x"},
        })
        assert response["status"] == "error"
        violations = validate_memory_output_contract(response)
        assert violations == []

    def test_claim_error_passes_contract(self) -> None:
        response = handle_cdb_context_claim_resolve({
            "tool": TOOL_CDB_CONTEXT_CLAIM_RESOLVE,
            "parameters": {"mode": "by_topic", "topic": "x"},
        })
        assert response["status"] == "error"
        violations = validate_memory_output_contract(response)
        assert violations == []
