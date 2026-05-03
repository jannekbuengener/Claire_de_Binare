"""Unit tests for Context Query query builders (#2088)."""

from __future__ import annotations

import pytest

from tools.surrealdb.context_query import (
    ConfigValidationError,
    build_artifact_query,
    build_doc_query,
    build_symbol_query,
    build_import_query,
    build_trace_query,
    build_explain_source_query,
    build_snapshot_query,
    build_drift_query,
    build_audit_query,
)

EXAMPLE_CONFIG = "infrastructure/config/surrealdb/context_query.local.example.yaml"


@pytest.mark.unit
def test_build_artifact_query_with_filters() -> None:
    query = build_artifact_query(
        source_path="src/",
        file_type="python",
        hash_value="abc123",
        limit=50,
        include_tombstoned=False,
    )
    assert "FROM repo_artifact" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "file_type = 'python'" in query
    assert "normalized_sha256 = 'abc123'" in query
    assert "LIMIT 50" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_artifact_query_no_filters() -> None:
    query = build_artifact_query(limit=10, include_tombstoned=True)
    assert "FROM repo_artifact" in query
    assert "LIMIT 10" in query
    assert "tombstoned" not in query


@pytest.mark.unit
def test_build_doc_query_with_filters() -> None:
    query = build_doc_query(
        query_text="test",
        source_path="docs/",
        heading="intro",
        limit=20,
        include_tombstoned=False,
    )
    assert "FROM doc_chunk" in query
    assert "content CONTAINS 'test'" in query
    assert "source_path CONTAINS 'docs/'" in query
    assert "heading_path CONTAINS 'intro'" in query
    assert "LIMIT 20" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_doc_query_no_filters() -> None:
    query = build_doc_query(limit=5, include_tombstoned=True)
    assert "FROM doc_chunk" in query
    assert "LIMIT 5" in query
    assert "tombstoned" not in query


@pytest.mark.unit
def test_build_symbol_query_with_filters() -> None:
    query = build_symbol_query(
        name="MyClass",
        qualified_name="module.submodule.MyClass",
        source_path="src/",
        symbol_type="class",
        limit=25,
        include_tombstoned=False,
    )
    assert "FROM code_symbol" in query
    assert "name CONTAINS 'MyClass'" in query
    assert "qualified_name CONTAINS 'module.submodule.MyClass'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "symbol_type = 'class'" in query
    assert "LIMIT 25" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_symbol_query_no_filters() -> None:
    query = build_symbol_query(limit=10, include_tombstoned=True)
    assert "FROM code_symbol" in query
    assert "LIMIT 10" in query


@pytest.mark.unit
def test_build_import_query_with_filters() -> None:
    query = build_import_query(
        module="json",
        source_path="src/",
        source_hash="abc123",
        import_id="import-1",
        limit=30,
        include_tombstoned=False,
    )
    assert "FROM import_reference" in query
    assert "module CONTAINS 'json'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "source_hash = 'abc123'" in query
    assert "import_id = 'import-1'" in query
    assert "LIMIT 30" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_import_query_no_filters() -> None:
    query = build_import_query(limit=10, include_tombstoned=True)
    assert "FROM import_reference" in query
    assert "LIMIT 10" in query


@pytest.mark.unit
def test_build_trace_query_with_filters() -> None:
    query = build_trace_query(
        target_ref="module",
        source_path="src/",
        symbol_name="func",
        direction="upstream",
        edge_type="depends_on",
        confidence="high",
        limit=15,
        include_tombstoned=False,
    )
    assert "FROM dependency_edge" in query
    assert "source_ref CONTAINS 'module'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "symbol_name CONTAINS 'func'" in query
    assert "edge_type = 'depends_on'" in query
    assert "confidence = 'high'" in query
    assert "LIMIT 15" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_trace_query_direction_downstream() -> None:
    query = build_trace_query(target_ref="test", direction="downstream")
    assert "FROM dependency_edge" in query
    assert "edge_type = 'used_by'" in query


@pytest.mark.unit
def test_build_trace_query_no_filters() -> None:
    query = build_trace_query(limit=10, include_tombstoned=True)
    assert "FROM dependency_edge" in query
    assert "LIMIT 10" in query


@pytest.mark.unit
def test_build_explain_source_query_with_artifact_id() -> None:
    query = build_explain_source_query(
        artifact_id="artifact-1",
        source_path="src/",
        limit=10,
        include_tombstoned=False,
    )
    assert "FROM repo_artifact" in query
    assert "artifact_id = 'artifact-1'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "LIMIT 10" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_explain_source_query_with_chunk_id() -> None:
    query = build_explain_source_query(chunk_id="chunk-1")
    assert "FROM repo_artifact" in query
    assert "chunk_id = 'chunk-1'" in query


@pytest.mark.unit
def test_build_explain_source_query_multiple_ids_raises() -> None:
    with pytest.raises(ConfigValidationError):
        build_explain_source_query(artifact_id="a", chunk_id="b")


@pytest.mark.unit
def test_build_snapshot_query_with_filters() -> None:
    query = build_snapshot_query(
        snapshot_id="snap-1",
        run_id="run-123",
        source_path="src/",
        limit=10,
        include_tombstoned=False,
    )
    assert "FROM repo_artifact" in query
    assert "snapshot_id = 'snap-1'" in query
    assert "run_id = 'run-123'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "LIMIT 10" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_snapshot_query_no_filters() -> None:
    query = build_snapshot_query(limit=5, include_tombstoned=True)
    assert "FROM repo_artifact" in query
    assert "LIMIT 5" in query


@pytest.mark.unit
def test_build_drift_query_with_filters() -> None:
    query = build_drift_query(
        artifact_id="artifact-1",
        source_path="src/",
        status="blocking",
        kind="depends_on",
        limit=20,
        include_tombstoned=False,
    )
    assert "FROM dependency_edge" in query
    assert "source_ref CONTAINS 'artifact-1'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "status = 'blocking'" in query
    assert "edge_type = 'depends_on'" in query
    assert "LIMIT 20" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_drift_query_no_filters() -> None:
    query = build_drift_query(limit=5, include_tombstoned=True)
    assert "FROM dependency_edge" in query
    assert "LIMIT 5" in query


@pytest.mark.unit
def test_build_audit_query_with_filters() -> None:
    query = build_audit_query(
        audit_id="audit-1",
        run_id="run-123",
        source_path="src/",
        limit=10,
        include_tombstoned=False,
    )
    assert "FROM import_reference" in query
    assert "import_id = 'audit-1'" in query
    assert "run_id = 'run-123'" in query
    assert "source_path CONTAINS 'src/'" in query
    assert "LIMIT 10" in query
    assert "tombstoned = false" in query


@pytest.mark.unit
def test_build_audit_query_no_filters() -> None:
    query = build_audit_query(limit=5, include_tombstoned=True)
    assert "FROM import_reference" in query
    assert "LIMIT 5" in query
