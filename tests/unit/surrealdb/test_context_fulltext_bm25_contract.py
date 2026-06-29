from __future__ import annotations

from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

CONTRACT_DOC_PATH = (
    REPO_ROOT / "docs" / "surrealdb" / "CDB_CONTEXT_FULLTEXT_BM25_CONTRACT.md"
)
CONTRACT_ARTIFACT_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_fulltext_bm25_contract.json"
)
OWNERSHIP_MATRIX_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_data_model_ownership_matrix.json"
)
OWNERSHIP_DOC_PATH = (
    REPO_ROOT / "docs" / "surrealdb" / "CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md"
)

INDEXABLE_CATEGORIES = frozenset(
    {
        "repo_file",
        "github_issue",
        "github_pr",
        "evidence",
        "claim",
        "decision",
        "external_doc",
    }
)

BLOCKED_CATEGORIES = frozenset(
    {
        "secrets",
        "broker_credentials",
        "live_positions",
        "live_orders",
        "live_fills",
        "live_risk_state",
        "trading_runtime_control",
        "agent_memory_raw",
    }
)

REQUIRED_INDEX_FIELDS = frozenset(
    {
        "analyzer",
        "indexed_fields",
        "score_function",
        "highlight_allowed",
        "evidence_required",
        "source_of_truth",
        "freshness_policy",
    }
)


def _load_contract() -> dict:
    if not CONTRACT_ARTIFACT_PATH.exists():
        pytest.fail(
            f"Fulltext BM25 contract artifact not found at {CONTRACT_ARTIFACT_PATH}. "
            f"Expected a JSON file with indexable categories, analyzers, and score configuration."
        )
    with open(CONTRACT_ARTIFACT_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestFulltextBM25Contract:
    def test_fulltext_bm25_contract_doc_exists(self):
        assert CONTRACT_DOC_PATH.exists(), (
            f"RED: Fulltext BM25 contract documentation does not exist at "
            f"{CONTRACT_DOC_PATH}. "
            f"Expected: docs/surrealdb/CDB_CONTEXT_FULLTEXT_BM25_CONTRACT.md"
        )

    def test_fulltext_bm25_contract_artifact_exists(self):
        assert CONTRACT_ARTIFACT_PATH.exists(), (
            f"RED: Fulltext BM25 contract artifact does not exist at "
            f"{CONTRACT_ARTIFACT_PATH}. "
            f"Expected: artifacts/surrealdb/context_fulltext_bm25_contract.json"
        )

    def test_contract_defines_indexable_context_categories(self):
        contract = _load_contract()
        indexable = set(contract.get("indexable_categories", {}).keys())
        missing = INDEXABLE_CATEGORIES - indexable
        assert not missing, (
            f"RED: Required indexable categories missing from contract: "
            f"{sorted(missing)}. "
            f"Expected indexable: {sorted(INDEXABLE_CATEGORIES)}"
        )

    def test_contract_blocks_forbidden_categories_from_fulltext(self):
        contract = _load_contract()
        blocked = set(contract.get("forbidden_categories", {}).keys())
        missing_blocked = BLOCKED_CATEGORIES - blocked
        assert not missing_blocked, (
            f"RED: Forbidden categories missing from fulltext blocklist: "
            f"{sorted(missing_blocked)}. "
            f"All secrets, live trading state, credentials, and raw agent memory "
            f"must be explicitly blocked from fulltext indexing."
        )

    def test_contract_requires_analyzer_and_score_fields(self):
        contract = _load_contract()
        for cat_name, cat_data in contract.get("indexable_categories", {}).items():
            missing_fields = REQUIRED_INDEX_FIELDS - set(cat_data.keys())
            assert not missing_fields, (
                f"RED: Indexable category '{cat_name}' missing required fields: "
                f"{sorted(missing_fields)}. "
                f"Expected fields: {sorted(REQUIRED_INDEX_FIELDS)}"
            )

    def test_no_fulltext_contract_claims_live_db_operationality(self):
        contract = _load_contract()
        for cat_name, cat_data in contract.get("indexable_categories", {}).items():
            assert cat_data.get("operational") is not True, (
                f"RED: Category '{cat_name}' claims operational=true. "
                f"No fulltext contract may claim live DB operationality "
                f"without adapter evidence."
            )
            assert cat_data.get("backing_status") != "DB_BACKED_READONLY_PROVEN", (
                f"RED: Category '{cat_name}' claims DB_BACKED_READONLY_PROVEN. "
                f"Fulltext contract must remain CONTRACT_ONLY until "
                f"adapter evidence is provided."
            )
            assert cat_data.get("live_index_exists") is not True, (
                f"RED: Category '{cat_name}' claims live_index_exists=true. "
                f"No live index may be claimed without real SurrealDB adapter."
            )

    def test_fulltext_contract_links_to_data_model_ownership_matrix(self):
        contract = _load_contract()
        refs = contract.get("references", [])
        assert str(OWNERSHIP_MATRIX_PATH) in refs or "context_data_model_ownership_matrix.json" in str(
            refs
        ), (
            f"RED: Fulltext contract does not reference the data model ownership "
            f"matrix at {OWNERSHIP_MATRIX_PATH}."
        )
        assert str(OWNERSHIP_DOC_PATH) in refs or "CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md" in str(
            refs
        ), (
            f"RED: Fulltext contract does not reference the data model ownership "
            f"doc at {OWNERSHIP_DOC_PATH}."
        )
