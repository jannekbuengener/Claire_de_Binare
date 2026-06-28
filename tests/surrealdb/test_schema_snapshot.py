"""Tests for the deterministic schema snapshot tool.

All tests are static — no DB connection needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.surrealdb.schema_snapshot import (
    build_snapshot,
    compute_schema_hash,
    parse_surql,
)
from tests.surrealdb.conftest import SURQL_ORIGINAL, SURQL_DEPLOY, BASELINE_PATH
from tests.surrealdb.test_context_intelligence_v0_surql import EXPECTED_TABLES

FIXED_TS = "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_parses_all_expected_tables() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    for table in EXPECTED_TABLES:
        assert table in canonical["tables"], f"Missing table: {table}"
    assert len(canonical["tables"]) == len(EXPECTED_TABLES)


@pytest.mark.unit
def test_snapshot_parses_fields_and_indexes() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    assert len(canonical["fields"]) > 0, "No fields parsed"
    assert len(canonical["indexes"]) > 0, "No indexes parsed"


@pytest.mark.unit
def test_snapshot_parses_analyzers() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    assert "cdb_code_analyzer" in canonical["analyzers"], "Missing analyzer"


@pytest.mark.unit
def test_snapshot_parses_new_embedding_field() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    assert {"field": "embedding", "table": "doc_chunk"} in canonical[
        "fields"
    ], "Missing embedding field on doc_chunk"


@pytest.mark.unit
def test_snapshot_parses_new_vector_and_fulltext_indexes() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    indexes = canonical["indexes"]
    assert {"index": "idx_doc_chunk_embedding_hnsw", "table": "doc_chunk"} in indexes
    assert {"index": "idx_doc_chunk_content_ft", "table": "doc_chunk"} in indexes


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_hash_is_deterministic() -> None:
    s1 = build_snapshot(SURQL_ORIGINAL, fixed_generated_at=FIXED_TS)
    s2 = build_snapshot(SURQL_ORIGINAL, fixed_generated_at=FIXED_TS)
    assert s1["schema_hash"] == s2["schema_hash"]


@pytest.mark.unit
def test_snapshot_hash_differs_for_different_input() -> None:
    hash_original = build_snapshot(SURQL_ORIGINAL, fixed_generated_at=FIXED_TS)[
        "schema_hash"
    ]
    hash_deploy = build_snapshot(SURQL_DEPLOY, fixed_generated_at=FIXED_TS)[
        "schema_hash"
    ]
    assert (
        hash_original == hash_deploy
    ), "Core definitions should match between original and deploy"


@pytest.mark.unit
def test_snapshot_hash_not_affected_by_generated_at() -> None:
    """generated_at must NOT influence schema_hash."""
    s_fixed = build_snapshot(SURQL_ORIGINAL, fixed_generated_at=FIXED_TS)
    s_empty = build_snapshot(SURQL_ORIGINAL, fixed_generated_at="")
    assert s_fixed["schema_hash"] == s_empty["schema_hash"]


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_baseline_matches_current_schema(baseline_json: dict) -> None:
    current = build_snapshot(SURQL_ORIGINAL, fixed_generated_at=FIXED_TS)
    assert current["schema_hash"] == baseline_json["schema_hash"], (
        f"Schema drift: baseline hash differs. "
        f"Run: python tools/surrealdb/schema_snapshot.py "
        f"--surql-path infrastructure/surrealdb/context_intelligence_v0.surql "
        f"--output infrastructure/surrealdb/schema_baseline.json"
    )


@pytest.mark.unit
def test_baseline_contains_essential_keys(baseline_json: dict) -> None:
    for key in (
        "schema_hash",
        "table_count",
        "field_count",
        "index_count",
        "analyzer_count",
        "tables",
    ):
        assert key in baseline_json, f"Baseline missing key: {key}"
    assert baseline_json["table_count"] == len(EXPECTED_TABLES)


# ---------------------------------------------------------------------------
# Deploy file consistency
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deploy_has_same_tables_as_original() -> None:
    orig = parse_surql(SURQL_ORIGINAL)
    depl = parse_surql(SURQL_DEPLOY)
    assert orig["tables"] == depl["tables"]


@pytest.mark.unit
def test_deploy_has_same_core_schema_hash_as_original() -> None:
    hash_orig = build_snapshot(SURQL_ORIGINAL, fixed_generated_at=FIXED_TS)[
        "schema_hash"
    ]
    hash_depl = build_snapshot(SURQL_DEPLOY, fixed_generated_at=FIXED_TS)["schema_hash"]
    assert (
        hash_orig == hash_depl
    ), "Deploy and original must have identical core schema hash"


# ---------------------------------------------------------------------------
# TYPE RELATION parsing tests (Issue #3423)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_parses_type_relation_tables() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    for table in (
        "artifact_cites_decision",
        "memory_supports_decision",
        "chunk_mentions_symbol",
    ):
        assert table in canonical["tables"], f"Missing TYPE RELATION table: {table}"
    assert "artifact_cites_decision" in canonical["relation_tables"]
    assert "memory_supports_decision" in canonical["relation_tables"]
    assert "chunk_mentions_symbol" in canonical["relation_tables"]


@pytest.mark.unit
def test_snapshot_reports_relation_count() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    assert len(canonical["relation_tables"]) == 3


@pytest.mark.unit
def test_snapshot_table_types_are_correct() -> None:
    canonical = parse_surql(SURQL_ORIGINAL)
    for table in canonical["table_types"]:
        if table in canonical["relation_tables"]:
            assert canonical["table_types"][table] == "TYPE_RELATION"
        else:
            assert canonical["table_types"][table] == "SCHEMAFULL"


@pytest.mark.unit
def test_baseline_contains_relation_tables(baseline_json: dict) -> None:
    assert "relation_tables" in baseline_json
    assert baseline_json["relation_table_count"] == 3
    assert "artifact_cites_decision" in baseline_json["relation_tables"]


@pytest.mark.unit
def test_deploy_has_same_relation_tables_as_original() -> None:
    orig = parse_surql(SURQL_ORIGINAL)
    depl = parse_surql(SURQL_DEPLOY)
    assert orig["relation_tables"] == depl["relation_tables"]
