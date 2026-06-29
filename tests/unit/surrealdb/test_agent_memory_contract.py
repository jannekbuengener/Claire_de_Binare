"""
test_id: tc_agent_memory_contract_001
test_type: wissens
cdb_area: surrealdb/agent_memory
rule_ref: INV-CONTEXT-010
decision_ref: Agent Memory Contract schreibt Memory-Typen, Gates, TTL, Evidence-Link und Blocklist vor
issue_ref: "#3490"
pr_ref: TBD
evidence_ref: RED_ONLY — Contract existiert noch nicht
"""

from __future__ import annotations

from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

CONTRACT_DOC_PATH = (
    REPO_ROOT / "docs" / "surrealdb" / "CDB_AGENT_MEMORY_CONTRACT.md"
)
CONTRACT_ARTIFACT_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "agent_memory_contract.json"
)
OWNERSHIP_MATRIX_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_data_model_ownership_matrix.json"
)
FULLTEXT_CONTRACT_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_fulltext_bm25_contract.json"
)

ALLOWED_MEMORY_TYPES = frozenset(
    {
        "operator_note",
        "issue_memory",
        "decision_memory",
        "evidence_summary",
        "session_lesson",
        "repo_fact_cache",
    }
)

FORBIDDEN_MEMORY_INPUTS = frozenset(
    {
        "secrets",
        "broker_credentials",
        "live_positions",
        "live_orders",
        "live_fills",
        "live_risk_state",
        "trading_runtime_control",
        "raw_chat_dump",
        "unscoped_agent_memory",
    }
)

REQUIRED_TYPE_FIELDS = frozenset(
    {
        "scope",
        "ttl_policy",
        "source_of_truth",
        "evidence_required",
        "write_gate",
        "read_gate",
        "redaction_required",
    }
)


def _load_contract() -> dict:
    if not CONTRACT_ARTIFACT_PATH.exists():
        pytest.fail(
            f"Agent Memory contract artifact not found at {CONTRACT_ARTIFACT_PATH}. "
            f"Expected a JSON file with allowed memory types, forbidden inputs, "
            f"and gate configuration."
        )
    with open(CONTRACT_ARTIFACT_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestAgentMemoryContract:
    def test_agent_memory_contract_doc_exists(self):
        assert CONTRACT_DOC_PATH.exists(), (
            f"RED: Agent Memory contract documentation does not exist at "
            f"{CONTRACT_DOC_PATH}. "
            f"Expected: docs/surrealdb/CDB_AGENT_MEMORY_CONTRACT.md"
        )

    def test_agent_memory_contract_artifact_exists(self):
        assert CONTRACT_ARTIFACT_PATH.exists(), (
            f"RED: Agent Memory contract artifact does not exist at "
            f"{CONTRACT_ARTIFACT_PATH}. "
            f"Expected: artifacts/surrealdb/agent_memory_contract.json"
        )

    def test_contract_defines_allowed_memory_types(self):
        contract = _load_contract()
        allowed = set(contract.get("allowed_memory_types", {}).keys())
        missing = ALLOWED_MEMORY_TYPES - allowed
        assert not missing, (
            f"RED: Required allowed memory types missing from contract: "
            f"{sorted(missing)}. "
            f"Expected allowed: {sorted(ALLOWED_MEMORY_TYPES)}"
        )

    def test_contract_blocks_forbidden_memory_inputs(self):
        contract = _load_contract()
        forbidden = set(contract.get("forbidden_memory_inputs", {}).keys())
        missing_blocked = FORBIDDEN_MEMORY_INPUTS - forbidden
        assert not missing_blocked, (
            f"RED: Forbidden memory inputs missing from contract blocklist: "
            f"{sorted(missing_blocked)}. "
            f"All secrets, live trading state, credentials, raw chat dumps, "
            f"and unscoped agent memory must be explicitly blocked."
        )

    def test_each_memory_type_requires_scope_ttl_and_evidence(self):
        contract = _load_contract()
        for type_name, type_data in contract.get("allowed_memory_types", {}).items():
            missing_fields = REQUIRED_TYPE_FIELDS - set(type_data.keys())
            assert not missing_fields, (
                f"RED: Allowed memory type '{type_name}' missing required fields: "
                f"{sorted(missing_fields)}. "
                f"Expected fields: {sorted(REQUIRED_TYPE_FIELDS)}"
            )

    def test_no_memory_contract_claims_productive_db_write(self):
        contract = _load_contract()
        for type_name, type_data in contract.get("allowed_memory_types", {}).items():
            assert type_data.get("operational") is not True, (
                f"RED: Memory type '{type_name}' claims operational=true. "
                f"No memory contract may claim productive DB operationality "
                f"without adapter evidence."
            )
            assert type_data.get("persist_allowed") is not True, (
                f"RED: Memory type '{type_name}' claims PERSIST_ALLOWED=true. "
                f"Agent memory contract must remain CONTRACT_ONLY until "
                f"adapter evidence is provided."
            )
            assert type_data.get("mutation_allowed") is not True, (
                f"RED: Memory type '{type_name}' claims MUTATION_ALLOWED=true. "
                f"Memory mutation must remain blocked without adapter evidence."
            )

    def test_agent_memory_links_to_ownership_and_fulltext_contracts(self):
        contract = _load_contract()
        refs = contract.get("references", [])
        assert str(OWNERSHIP_MATRIX_PATH) in refs or "context_data_model_ownership_matrix.json" in str(
            refs
        ), (
            f"RED: Agent Memory contract does not reference the data model ownership "
            f"matrix at {OWNERSHIP_MATRIX_PATH}."
        )
        assert str(FULLTEXT_CONTRACT_PATH) in refs or "context_fulltext_bm25_contract.json" in str(
            refs
        ), (
            f"RED: Agent Memory contract does not reference the fulltext BM25 "
            f"contract at {FULLTEXT_CONTRACT_PATH}."
        )
