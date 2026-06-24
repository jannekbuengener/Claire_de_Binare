"""Schema contract tests for context_intelligence_v0.surql family.

All tests are static file parsing — no DB connection needed.
"""

from __future__ import annotations

import re
import json
from pathlib import Path

import pytest

from tests.surrealdb.conftest import SURQL_ORIGINAL, SURQL_DEPLOY, BASELINE_PATH

# ---------------------------------------------------------------------------
# Canonical table list — source of truth for schema expectations
# ---------------------------------------------------------------------------
EXPECTED_TABLES: tuple[str, ...] = (
    "agent_memory",
    "artifact_cites_decision",
    "audit_observation",
    "chunk_mentions_symbol",
    "claim",
    "code_symbol",
    "concept",
    "context_query",
    "contradiction",
    "decision_event",
    "dependency_edge",
    "doc_chunk",
    "doc_page",
    "doc_section",
    "evidence_ref",
    "knowledge_quality_score",
    "memory_supports_decision",
    "repo_artifact",
    "scope_drift_event",
    "stale_context",
    "visual_control_view",
)

EXPECTED_RELATION_TABLES: tuple[str, ...] = (
    "artifact_cites_decision",
    "memory_supports_decision",
    "chunk_mentions_symbol",
)

RELATION_METADATA_FIELDS: tuple[str, ...] = (
    "source",
    "confidence",
    "timestamp",
    "hash",
)

TRAVERSAL_FIXTURE_PATH = "infrastructure/surrealdb/traversal_query_fixtures.surql"

PK_FIELD_BY_TABLE: dict[str, str] = {
    "repo_artifact": "artifact_id",
    "code_symbol": "symbol_id",
    "doc_page": "page_id",
    "doc_section": "section_id",
    "doc_chunk": "chunk_id",
    "concept": "concept_id",
    "dependency_edge": "edge_id",
    "evidence_ref": "evidence_id",
    "claim": "claim_id",
    "decision_event": "decision_id",
    "agent_memory": "memory_id",
    "context_query": "query_id",
    "audit_observation": "observation_id",
    "contradiction": "contradiction_id",
    "stale_context": "stale_id",
    "scope_drift_event": "drift_id",
    "knowledge_quality_score": "score_id",
    "visual_control_view": "view_id",
}

FORBIDDEN_TABLES: tuple[str, ...] = (
    "order",
    "fill",
    "position",
    "risk_state",
    "position_state",
    "trade",
)

# Blocks that must NOT appear in deploy file permissions
PERMISSION_BLOCKS = {
    "FOR select FULL",
    "FOR create FULL",
    "FOR update FULL",
    "FOR delete FULL",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RE_DEFINE_TABLE = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+(?:SCHEMAFULL|TYPE\s+RELATION)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_DEFINE_FIELD = re.compile(
    r"^\s*DEFINE\s+FIELD\s+(\S+)\s+ON\s+TABLE\s+(\S+)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_DEFINE_INDEX = re.compile(
    r"^\s*DEFINE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+ON\s+TABLE\s+(\S+)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_TABLE_SCHEMAFULL = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+SCHEMAFULL",
    re.IGNORECASE | re.MULTILINE,
)
_RE_TABLE_TYPE = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+(?:SCHEMAFULL|TYPE\s+RELATION)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_TABLE_RELATION = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+TYPE\s+RELATION",
    re.IGNORECASE | re.MULTILINE,
)
_RE_DEFINE_TABLE_ANY = re.compile(
    r"^\s*DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_PERMISSIONS = re.compile(
    r"DEFINE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s+(?:SCHEMAFULL|TYPE\s+RELATION)\s+PERMISSIONS\s+FOR\s+select\s+NONE,\s+FOR\s+create\s+NONE,\s+FOR\s+update\s+NONE,\s+FOR\s+delete\s+NONE",
    re.IGNORECASE,
)


def extract_tables(surql_text: str) -> set[str]:
    return set(_RE_DEFINE_TABLE.findall(surql_text))


def extract_fields(surql_text: str) -> set[str]:
    return {f"{t}.{f}" for f, t in _RE_DEFINE_FIELD.findall(surql_text)}


def extract_indexes(surql_text: str) -> set[str]:
    return {f"{t}.{i}" for i, t in _RE_DEFINE_INDEX.findall(surql_text)}


# ---------------------------------------------------------------------------
# Original draft tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_surql_defines_all_expected_tables(surql_original_text: str) -> None:
    tables = extract_tables(surql_original_text)
    for table in EXPECTED_TABLES:
        assert table in tables, f"Missing table: {table}"


@pytest.mark.unit
def test_each_table_is_schemafull_or_type_relation(surql_original_text: str) -> None:
    """All tables must be either SCHEMAFULL or TYPE RELATION."""
    tables_found = _RE_TABLE_TYPE.findall(surql_original_text)
    assert len(tables_found) == len(EXPECTED_TABLES)
    schemafull = _RE_TABLE_SCHEMAFULL.findall(surql_original_text)
    relation = _RE_TABLE_RELATION.findall(surql_original_text)
    assert len(schemafull) + len(relation) == len(EXPECTED_TABLES)


@pytest.mark.unit
def test_each_table_has_pk_field_and_unique_index(surql_original_text: str) -> None:
    for table, pk_field in PK_FIELD_BY_TABLE.items():
        assert (
            f"DEFINE FIELD {pk_field} ON TABLE {table}" in surql_original_text
        ), f"Missing PK field {pk_field} on {table}"
        idx_name = f"idx_{table}_{pk_field}_unique"
        assert f"ON TABLE {table} FIELDS {pk_field} UNIQUE" in surql_original_text


@pytest.mark.unit
def test_each_table_has_created_at_field(surql_original_text: str) -> None:
    tables_found = _RE_DEFINE_TABLE.findall(surql_original_text)
    for table in tables_found:
        assert (
            f"DEFINE FIELD created_at ON TABLE {table}" in surql_original_text
        ), f"Missing created_at on {table}"


@pytest.mark.unit
def test_no_trading_state_tables(surql_original_text: str) -> None:
    tables_declared = _RE_DEFINE_TABLE_ANY.findall(surql_original_text)
    for forbidden in FORBIDDEN_TABLES:
        matches = [t for t in tables_declared if forbidden in t.lower()]
        assert not matches, f"Forbidden table found: {matches}"


# ---------------------------------------------------------------------------
# Deploy file tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deploy_file_has_ns_and_db_context(surql_deploy_text: str) -> None:
    assert "DEFINE NAMESPACE IF NOT EXISTS cdb;" in surql_deploy_text
    assert "USE NS cdb;" in surql_deploy_text
    assert "DEFINE DATABASE IF NOT EXISTS context_intel;" in surql_deploy_text
    assert "USE DB context_intel;" in surql_deploy_text


@pytest.mark.unit
def test_deploy_file_uses_if_not_exists(surql_deploy_text: str) -> None:
    for table in EXPECTED_TABLES:
        expected = f"DEFINE TABLE IF NOT EXISTS {table}"
        assert expected in surql_deploy_text, f"Missing IF NOT EXISTS for table {table}"


@pytest.mark.unit
def test_deploy_file_permissions_are_strictly_none(surql_deploy_text: str) -> None:
    """Verify each table has PERMISSIONS with all four operations set to NONE.

    Normalises whitespace (including newlines) so that multi-line PERMISSIONS
    declarations match correctly.
    """
    import re as _re

    normalized = _re.sub(r"\s+", " ", surql_deploy_text)
    relation_set = set(EXPECTED_RELATION_TABLES)
    for table in EXPECTED_TABLES:
        if table in relation_set:
            # TYPE RELATION tables: table header + PERMISSIONS block are separated by FROM/TO
            table_header = f"DEFINE TABLE IF NOT EXISTS {table} TYPE RELATION"
            permissions_block = "PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE"
            assert (
                table_header in normalized
            ), f"Table {table} missing TYPE RELATION header"
            assert (
                permissions_block in normalized
            ), f"Table {table} missing fail-closed permissions"
        else:
            expected = (
                f"DEFINE TABLE IF NOT EXISTS {table} SCHEMAFULL "
                f"PERMISSIONS FOR select NONE, FOR create NONE, "
                f"FOR update NONE, FOR delete NONE"
            )
            assert (
                expected in normalized
            ), f"Table {table} missing fail-closed permissions"


@pytest.mark.unit
def test_deploy_file_has_no_full_permissions(surql_deploy_text: str) -> None:
    for block in PERMISSION_BLOCKS:
        assert (
            block not in surql_deploy_text
        ), f"Found non-NONE permission block: {block}"


@pytest.mark.unit
def test_deploy_matches_original_draft_core_definitions(
    surql_original_text: str,
    surql_deploy_text: str,
) -> None:
    original_fields = extract_fields(surql_original_text)
    deploy_fields = extract_fields(surql_deploy_text)
    assert original_fields == deploy_fields, (
        f"Field drift: original={len(original_fields)}, deploy={len(deploy_fields)}\n"
        f"Only in original: {original_fields - deploy_fields}\n"
        f"Only in deploy: {deploy_fields - original_fields}"
    )

    original_indexes = extract_indexes(surql_original_text)
    deploy_indexes = extract_indexes(surql_deploy_text)
    assert original_indexes == deploy_indexes, (
        f"Index drift: original={len(original_indexes)}, deploy={len(deploy_indexes)}\n"
        f"Only in original: {original_indexes - deploy_indexes}\n"
        f"Only in deploy: {deploy_indexes - original_indexes}"
    )


# ---------------------------------------------------------------------------
# VectorGraph tests (Issue #3422)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_draft_has_cdb_code_analyzer(surql_original_text: str) -> None:
    assert "DEFINE ANALYZER cdb_code_analyzer" in surql_original_text


@pytest.mark.unit
def test_deploy_has_cdb_code_analyzer(surql_deploy_text: str) -> None:
    assert "DEFINE ANALYZER IF NOT EXISTS cdb_code_analyzer" in surql_deploy_text


@pytest.mark.unit
def test_doc_chunk_has_embedding_field(surql_original_text: str) -> None:
    assert "DEFINE FIELD embedding ON TABLE doc_chunk TYPE array" in surql_original_text


@pytest.mark.unit
def test_deploy_has_embedding_field(surql_deploy_text: str) -> None:
    assert "DEFINE FIELD embedding ON TABLE doc_chunk TYPE array" in surql_deploy_text


@pytest.mark.unit
def test_doc_chunk_has_hnsw_index(surql_original_text: str) -> None:
    assert (
        "DEFINE INDEX idx_doc_chunk_embedding_hnsw ON TABLE doc_chunk FIELDS embedding HNSW DIMENSION 1536 DIST COSINE"
        in surql_original_text
    )


@pytest.mark.unit
def test_deploy_has_hnsw_index(surql_deploy_text: str) -> None:
    assert "HNSW DIMENSION 1536 DIST COSINE" in surql_deploy_text


@pytest.mark.unit
def test_doc_chunk_has_fulltext_index(surql_original_text: str) -> None:
    assert (
        "DEFINE INDEX idx_doc_chunk_content_ft ON TABLE doc_chunk FIELDS content FULLTEXT ANALYZER cdb_code_analyzer"
        in surql_original_text
    )


@pytest.mark.unit
def test_deploy_has_fulltext_index(surql_deploy_text: str) -> None:
    assert "FULLTEXT ANALYZER cdb_code_analyzer BM25 HIGHLIGHTS" in surql_deploy_text


@pytest.mark.unit
def test_no_embedding_runtime_data_in_schema(surql_original_text: str) -> None:
    """Schema must NOT contain embedding values/generation — only field + index definitions."""
    for pattern in ("embedding_generated", "embedding_model", "embedding_provider"):
        assert (
            pattern not in surql_original_text
        ), f"Embedding runtime data leaking: {pattern}"


# ---------------------------------------------------------------------------
# Graph Relations tests (Issue #3423)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_all_graph_relation_tables_exist(surql_original_text: str) -> None:
    for table in EXPECTED_RELATION_TABLES:
        assert table in surql_original_text, f"Missing relation table: {table}"


@pytest.mark.unit
def test_graph_relation_tables_are_type_relation(surql_original_text: str) -> None:
    for table in EXPECTED_RELATION_TABLES:
        assert (
            f"DEFINE TABLE {table} TYPE RELATION" in surql_original_text
        ), f"{table} is not TYPE RELATION"


@pytest.mark.unit
def test_graph_relation_tables_have_metadata_fields(surql_original_text: str) -> None:
    for table in EXPECTED_RELATION_TABLES:
        for field in RELATION_METADATA_FIELDS:
            assert (
                f"DEFINE FIELD {field} ON TABLE {table}" in surql_original_text
            ), f"Missing {field} on {table}"


@pytest.mark.unit
def test_graph_relation_tables_have_created_at(surql_original_text: str) -> None:
    for table in EXPECTED_RELATION_TABLES:
        assert (
            f"DEFINE FIELD created_at ON TABLE {table}" in surql_original_text
        ), f"Missing created_at on {table}"


@pytest.mark.unit
def test_chunk_mentions_symbol_has_mention_context(surql_original_text: str) -> None:
    assert (
        "DEFINE FIELD mention_context ON TABLE chunk_mentions_symbol"
        in surql_original_text
    )


@pytest.mark.unit
def test_no_trading_state_in_relation_tables(surql_original_text: str) -> None:
    for table in EXPECTED_RELATION_TABLES:
        block = f"DEFINE TABLE {table}"
        for forbidden in FORBIDDEN_TABLES:
            assert (
                forbidden.lower() not in table.lower()
            ), f"Relation table name uses forbidden trading term: {table}"


@pytest.mark.unit
def test_deploy_relation_tables_have_if_not_exists(surql_deploy_text: str) -> None:
    for table in EXPECTED_RELATION_TABLES:
        expected = f"DEFINE TABLE IF NOT EXISTS {table}"
        assert expected in surql_deploy_text, f"Missing IF NOT EXISTS for {table}"


@pytest.mark.unit
def test_deploy_relation_tables_have_fail_closed_permissions(
    surql_deploy_text: str,
) -> None:
    normalized = re.sub(r"\s+", " ", surql_deploy_text)
    for table in EXPECTED_RELATION_TABLES:
        table_header = f"DEFINE TABLE IF NOT EXISTS {table} TYPE RELATION"
        permissions_block = (
            "PERMISSIONS FOR select NONE, FOR create NONE, "
            "FOR update NONE, FOR delete NONE"
        )
        assert table_header in normalized, f"Table {table} missing TYPE RELATION header"
        assert (
            permissions_block in normalized
        ), f"Table {table} missing fail-closed permissions"
    assert "FOR select FULL" not in surql_deploy_text
    assert "FOR create FULL" not in surql_deploy_text


@pytest.mark.unit
def test_traversal_query_fixture_exists() -> None:
    path = Path(TRAVERSAL_FIXTURE_PATH)
    assert path.exists(), f"Traversal fixture missing: {TRAVERSAL_FIXTURE_PATH}"
    text = path.read_text(encoding="utf-8")
    assert "RELATE" not in text, "Fixture must not contain RELATE (no runtime)"
    assert "->" in text, "Fixture must contain arrow traversal syntax"


@pytest.mark.unit
def test_traversal_fixture_has_recursive_query() -> None:
    path = Path(TRAVERSAL_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "@." in text, "Fixture must contain recursive traversal syntax"


@pytest.mark.unit
def test_traversal_fixture_has_backward_traversal() -> None:
    path = Path(TRAVERSAL_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "<-" in text, "Fixture must contain backward traversal syntax"


# ---------------------------------------------------------------------------
# generated_at metadata validation (no fragile time-window)
# ---------------------------------------------------------------------------
# Hybrid Retrieval Contract tests (Issue #3424)
# ---------------------------------------------------------------------------

HYBRID_FIXTURE_PATH = "infrastructure/surrealdb/hybrid_retrieval_fixtures.surql"

FORBIDDEN_EMBEDDING_PATTERNS: tuple[str, ...] = (
    "CREATE test:",
    "embedding_generated",
    "embedding_model",
    "embedding_provider",
)


@pytest.mark.unit
def test_hybrid_retrieval_fixture_exists() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    assert path.exists(), f"Hybrid retrieval fixture missing: {HYBRID_FIXTURE_PATH}"
    text = path.read_text(encoding="utf-8")
    assert "search::rrf" in text, "Fixture must contain RRF fusion"
    assert "search::linear" in text, "Fixture must contain linear fusion"


@pytest.mark.unit
def test_hybrid_fixture_has_bm25_fulltext_query() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "@1@" in text, "Fixture must contain BM25 matches operator @N@"
    assert "search::score" in text, "Fixture must contain search::score() for BM25"
    assert "bm25_score" in text, "Fixture must contain bm25_score field"


@pytest.mark.unit
def test_hybrid_fixture_has_vector_knn_query() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "<|" in text, "Fixture must contain KNN operator <|K, EF|>"
    assert "vector::distance::knn()" in text, "Fixture must contain vector::distance::knn()"
    assert "HNSW" not in text.splitlines()[-20:], "Fixture query section must not reference HNSW"
    assert "<|" in text, "Fixture must contain KNN operator <|K, EF|>"


@pytest.mark.unit
def test_hybrid_fixture_has_rrf() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "search::rrf(" in text, "Fixture must contain search::rrf()"
    assert "rrf_k" in text or "60" in text, "Fixture must reference RRF k constant"


@pytest.mark.unit
def test_hybrid_fixture_no_relate_or_create() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "RELATE" not in text, "Fixture must not contain RELATE"
    assert "CREATE " not in text, "Fixture must not contain CREATE"


@pytest.mark.unit
def test_hybrid_fixture_no_trading_tables() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    for forbidden in ("fill", "fills", "position", "positions", "risk_state", "position_state", "trade"):
        define_matches = [l for l in text.splitlines() if "DEFINE" in l.upper() and forbidden.lower() in l.lower()]
        assert not define_matches, f"Forbidden trading table defined in fixture: {forbidden}"
    order_defines = [l for l in text.splitlines() if "DEFINE" in l.upper() and re.search(r'\border\b', l, re.IGNORECASE)]
    assert not order_defines, f"Forbidden trading table defined in fixture: order"


@pytest.mark.unit
def test_no_embedding_runtime_in_hybrid_fixtures() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_EMBEDDING_PATTERNS:
        assert pattern not in text, f"Embedding runtime data leaking: {pattern}"


@pytest.mark.unit
def test_hybrid_fixture_has_result_contract_documented() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    contract_fields = ("rrf_score", "chunk_id", "content_hash", "fuse_score")
    for field in contract_fields:
        assert field in text.lower(), f"Result contract field missing in doc: {field}"


@pytest.mark.unit
def test_rrf_formula_documented() -> None:
    path = Path(HYBRID_FIXTURE_PATH)
    text = path.read_text(encoding="utf-8")
    assert "1 / (k + rank" in text or "1/(k + rank" in text, (
        "RRF formula must be documented: score = sum(1 / (k + rank))"
    )
    assert "k = 60" in text, "RRF k=60 must be documented"
    assert "rrf_score DESC" in text, "RRF tie-breaker must be documented"


@pytest.mark.unit
def test_python_hybrid_ranking_not_modified() -> None:
    ranking_path = Path("tools/surrealdb/hybrid_retrieval_ranking.py")
    assert ranking_path.exists(), "Python hybrid ranking must still exist"
    text = ranking_path.read_text(encoding="utf-8")
    assert "SCHEMA_VERSION" in text, "Ranking must still contain SCHEMA_VERSION"
    assert "RANKING_FACTORS" in text, "Ranking must still contain RANKING_FACTORS"

# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_schema_baseline_has_valid_generated_at_format(baseline_json: dict) -> None:
    ga = baseline_json.get("generated_at", "")
    assert (
        isinstance(ga, str) and len(ga) > 10
    ), f"generated_at missing or too short: {ga!r}"
    # ISO-8601 compatible: YYYY-MM-DDTHH:MM:SS...
    assert "T" in ga, f"generated_at not ISO-8601: {ga!r}"


@pytest.mark.unit
def test_generated_at_not_in_schema_hash_computation(
    surql_original_text: str,
    baseline_json: dict,
) -> None:
    """Verify generated_at is NOT part of the schema_hash input.

    If generated_at were included, changing it would change the hash.
    We can verify this by checking the hash is deterministic against
    the baseline even though generated_at differs (test uses live time
    while baseline uses fixed time).
    """
    from tools.surrealdb.schema_snapshot import build_snapshot

    snapshot_live = build_snapshot(
        surql_path=SURQL_ORIGINAL,
    )
    assert (
        snapshot_live["schema_hash"] == baseline_json["schema_hash"]
    ), "schema_hash differs from baseline — generated_at may be leaking into hash"



