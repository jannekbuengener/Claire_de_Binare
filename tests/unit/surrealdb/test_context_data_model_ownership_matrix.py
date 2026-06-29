from __future__ import annotations

from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

MATRIX_PATH = (
    REPO_ROOT / "artifacts" / "surrealdb" / "context_data_model_ownership_matrix.json"
)
DOC_PATH = (
    REPO_ROOT / "docs" / "surrealdb" / "CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md"
)

REQUIRED_CATEGORIES = frozenset(
    {
        "repo_file",
        "github_issue",
        "github_pr",
        "context_tool",
        "mcp_boundary",
        "evidence",
        "claim",
        "decision",
        "agent_memory",
        "external_doc",
    }
)

REQUIRED_FIELDS = frozenset(
    {
        "owner",
        "source_of_truth",
        "mirror_allowed",
        "persist_allowed",
        "mutation_allowed",
        "ttl_policy",
        "evidence_required",
    }
)

FORBIDDEN_CATEGORIES = frozenset(
    {
        "secrets",
        "broker_credentials",
        "live_positions",
        "live_orders",
        "live_fills",
        "live_risk_state",
        "trading_runtime_control",
    }
)


def _load_matrix() -> dict:
    if not MATRIX_PATH.exists():
        pytest.fail(
            f"Data model ownership matrix not found at {MATRIX_PATH}. "
            f"Expected a JSON file with categories, owners, and source-of-truth entries."
        )
    with open(MATRIX_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestDataModelOwnershipMatrixArtifact:
    def test_context_data_model_ownership_matrix_artifact_exists(self):
        assert MATRIX_PATH.exists(), (
            f"RED: Data model ownership matrix artifact does not exist at {MATRIX_PATH}. "
            f"Expected: artifacts/surrealdb/context_data_model_ownership_matrix.json"
        )

    def test_matrix_defines_required_context_data_categories(self):
        matrix = _load_matrix()
        categories = set(matrix.get("categories", {}).keys())
        missing = REQUIRED_CATEGORIES - categories
        assert not missing, (
            f"RED: Required data categories missing from matrix: {sorted(missing)}. "
            f"Expected categories: {sorted(REQUIRED_CATEGORIES)}"
        )

    def test_each_category_has_owner_and_source_of_truth(self):
        matrix = _load_matrix()
        for cat_name, cat_data in matrix.get("categories", {}).items():
            missing_fields = REQUIRED_FIELDS - set(cat_data.keys())
            assert not missing_fields, (
                f"RED: Category '{cat_name}' missing required fields: {sorted(missing_fields)}. "
                f"Expected fields: {sorted(REQUIRED_FIELDS)}"
            )

    def test_forbidden_categories_are_explicitly_blocked(self):
        matrix = _load_matrix()
        blocked = set(matrix.get("forbidden_categories", {}).keys())
        missing_blocked = FORBIDDEN_CATEGORIES - blocked
        assert not missing_blocked, (
            f"RED: Forbidden categories missing from blocklist: {sorted(missing_blocked)}. "
            f"All live trading state, secrets, and credentials must be explicitly blocked."
        )
        for cat_name, cat_data in matrix.get("forbidden_categories", {}).items():
            assert cat_data.get("persist_allowed") is False, (
                f"RED: Forbidden category '{cat_name}' must have persist_allowed=false"
            )
            assert cat_data.get("mutation_allowed") is False, (
                f"RED: Forbidden category '{cat_name}' must have mutation_allowed=false"
            )

    def test_no_category_claims_db_backed_without_evidence(self):
        matrix = _load_matrix()
        for cat_name, cat_data in matrix.get("categories", {}).items():
            is_db_backed = cat_data.get("backing_status") == "DB_BACKED"
            evidence_required = cat_data.get("evidence_required")
            if is_db_backed:
                assert evidence_required, (
                    f"RED: Category '{cat_name}' claims DB_BACKED but has no evidence_required field. "
                    f"DB-backed claims require adapter evidence."
                )

    def test_context_data_model_doc_exists(self):
        assert DOC_PATH.exists(), (
            f"RED: Data model ownership documentation does not exist at {DOC_PATH}. "
            f"Expected: docs/surrealdb/CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md"
        )
