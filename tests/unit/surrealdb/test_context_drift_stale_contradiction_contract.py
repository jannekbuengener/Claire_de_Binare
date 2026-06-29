"""
test_id: tc_context_drift_stale_contradiction_contract_001
test_type: wissens
cdb_area: surrealdb/context_warning_layer
rule_ref: INV-CONTEXT-011
decision_ref: Drift-, Stale- und Contradiction-Erkennung braucht einen expliziten CDB-Contract
issue_ref: "#3491"
pr_ref: TBD
evidence_ref: RED_ONLY - Contract existiert noch nicht
"""

from __future__ import annotations

from pathlib import Path
import json

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

CONTRACT_DOC_PATH = (
    REPO_ROOT
    / "docs"
    / "surrealdb"
    / "CDB_CONTEXT_DRIFT_STALE_CONTRADICTION_CONTRACT.md"
)
CONTRACT_ARTIFACT_PATH = (
    REPO_ROOT
    / "artifacts"
    / "surrealdb"
    / "context_drift_stale_contradiction_contract.json"
)
OWNERSHIP_MATRIX_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_data_model_ownership_matrix.json"
)
FULLTEXT_CONTRACT_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_fulltext_bm25_contract.json"
)
AGENT_MEMORY_CONTRACT_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "agent_memory_contract.json"
)

DETECTABLE_SIGNAL_TYPES = frozenset(
    {
        "stale_doc",
        "stale_issue_status",
        "stale_pr_status",
        "stale_claim",
        "stale_memory",
        "contradicted_claim",
        "contradicted_decision",
        "repo_doc_drift",
        "github_repo_drift",
    }
)

REQUIRED_SIGNAL_FIELDS = frozenset(
    {
        "source_category",
        "evidence_required",
        "freshness_policy",
        "detection_basis",
        "severity",
        "resolution_state",
        "owner",
        "allowed_action",
    }
)

RESOLUTION_STATES = frozenset(
    {
        "open",
        "confirmed",
        "dismissed",
        "superseded",
        "fixed",
        "parked",
    }
)

UNSAFE_AUTO_RESOLUTIONS = frozenset(
    {
        "auto_close_issue",
        "auto_change_live_gate",
        "auto_override_lr_status",
        "auto_delete_memory",
        "auto_mutate_db",
        "auto_mark_claim_true_without_evidence",
    }
)


def _load_contract() -> dict:
    if not CONTRACT_ARTIFACT_PATH.exists():
        pytest.fail(
            f"Drift/Stale/Contradiction contract artifact not found at "
            f"{CONTRACT_ARTIFACT_PATH}. Expected a JSON file with detectable "
            f"signal types, resolution states, and unsafe auto-resolution blocklist."
        )
    with open(CONTRACT_ARTIFACT_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestContextDriftStaleContradictionContract:
    def test_drift_stale_contradiction_contract_doc_exists(self):
        assert CONTRACT_DOC_PATH.exists(), (
            f"RED: Drift/Stale/Contradiction contract documentation does not exist at "
            f"{CONTRACT_DOC_PATH}. Expected: "
            f"docs/surrealdb/CDB_CONTEXT_DRIFT_STALE_CONTRADICTION_CONTRACT.md"
        )

    def test_drift_stale_contradiction_contract_artifact_exists(self):
        assert CONTRACT_ARTIFACT_PATH.exists(), (
            f"RED: Drift/Stale/Contradiction contract artifact does not exist at "
            f"{CONTRACT_ARTIFACT_PATH}. Expected: "
            f"artifacts/surrealdb/context_drift_stale_contradiction_contract.json"
        )

    def test_contract_defines_detectable_signal_types(self):
        contract = _load_contract()
        signal_types = set(contract.get("detectable_signal_types", {}).keys())
        missing = DETECTABLE_SIGNAL_TYPES - signal_types
        assert not missing, (
            f"RED: Required detectable signal types missing from contract: "
            f"{sorted(missing)}. Expected signal types: "
            f"{sorted(DETECTABLE_SIGNAL_TYPES)}"
        )

    def test_each_signal_type_requires_evidence_and_resolution_state(self):
        contract = _load_contract()
        for signal_name, signal_data in contract.get("detectable_signal_types", {}).items():
            missing_fields = REQUIRED_SIGNAL_FIELDS - set(signal_data.keys())
            assert not missing_fields, (
                f"RED: Signal type '{signal_name}' missing required fields: "
                f"{sorted(missing_fields)}. Expected fields: "
                f"{sorted(REQUIRED_SIGNAL_FIELDS)}"
            )

    def test_contract_defines_resolution_states(self):
        contract = _load_contract()
        states = set(contract.get("resolution_states", []))
        missing_states = RESOLUTION_STATES - states
        assert not missing_states, (
            f"RED: Required resolution states missing from contract: "
            f"{sorted(missing_states)}. Expected states: {sorted(RESOLUTION_STATES)}"
        )

    def test_contract_blocks_unsafe_auto_resolution(self):
        contract = _load_contract()
        blocked = set(contract.get("forbidden_auto_resolution", {}).keys())
        missing_blocked = UNSAFE_AUTO_RESOLUTIONS - blocked
        assert not missing_blocked, (
            f"RED: Unsafe auto-resolution actions missing from blocklist: "
            f"{sorted(missing_blocked)}. These actions must remain explicitly blocked."
        )

    def test_contract_links_to_foundation_contracts(self):
        contract = _load_contract()
        refs = contract.get("references", [])
        assert str(OWNERSHIP_MATRIX_PATH) in refs or "context_data_model_ownership_matrix.json" in str(
            refs
        ), (
            f"RED: Contract does not reference the ownership matrix at "
            f"{OWNERSHIP_MATRIX_PATH}."
        )
        assert str(FULLTEXT_CONTRACT_PATH) in refs or "context_fulltext_bm25_contract.json" in str(
            refs
        ), (
            f"RED: Contract does not reference the fulltext contract at "
            f"{FULLTEXT_CONTRACT_PATH}."
        )
        assert str(AGENT_MEMORY_CONTRACT_PATH) in refs or "agent_memory_contract.json" in str(
            refs
        ), (
            f"RED: Contract does not reference the agent memory contract at "
            f"{AGENT_MEMORY_CONTRACT_PATH}."
        )

    def test_no_contract_claims_operational_surrealdb_detection(self):
        contract = _load_contract()
        for signal_name, signal_data in contract.get("detectable_signal_types", {}).items():
            assert signal_data.get("operational") is not True, (
                f"RED: Signal type '{signal_name}' claims operational=true. "
                f"No contract may claim live SurrealDB detection without adapter evidence."
            )
            assert signal_data.get("backing_status") != "DB_BACKED_READONLY_PROVEN", (
                f"RED: Signal type '{signal_name}' claims DB_BACKED_READONLY_PROVEN. "
                f"Contract must remain CONTRACT_ONLY until adapter evidence exists."
            )
            assert signal_data.get("live_detection_enabled") is not True, (
                f"RED: Signal type '{signal_name}' claims live_detection_enabled=true. "
                f"No live detection may be claimed without real DB evidence."
            )
            assert signal_data.get("mutation_allowed") is not True, (
                f"RED: Signal type '{signal_name}' claims mutation_allowed=true. "
                f"Detection findings must remain read-only in this contract slice."
            )
