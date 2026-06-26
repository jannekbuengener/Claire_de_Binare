"""Unit tests for isolated Graph + Vector Proof CLI.

No DB connection needed. All tests mock external calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.surrealdb.graph_vector_proof_cli import (
    EXIT_FAIL,
    EXIT_OK,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_USAGE,
    ProofSqlClient,
    _build_evidence,
    _build_parser,
    _chunk_id,
    _decision_id,
    _edge_id,
    _make_toy_vector,
    _page_id,
    _query_vector_near_cluster,
    _surql_datetime,
    _surql_escape,
    _symbol_id,
    _vector_sql_literal,
)

_CLI = (
    Path(__file__).parents[3] / "tools" / "surrealdb" / "graph_vector_proof_cli.py"
)
_SETUP = (
    Path(__file__).parents[3]
    / "infrastructure"
    / "surrealdb"
    / "proof_graph_vector_setup.surql"
)


@pytest.mark.unit
def test_cli_module_exists() -> None:
    assert _CLI.is_file()
    assert _SETUP.is_file()


@pytest.mark.unit
def test_parser_defaults() -> None:
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.host == "localhost"
    assert args.port == 8010
    assert args.user == "root"
    assert args.password == "root"
    assert args.ns == "cdb_proof"
    assert args.db == "graph_vector_proof"
    assert args.cleanup is True


@pytest.mark.unit
def test_parser_custom_args() -> None:
    parser = _build_parser()
    args = parser.parse_args([
        "--host", "127.0.0.1",
        "--port", "9000",
        "--user", "admin",
        "--pass", "secret",
        "--ns", "test_ns",
        "--db", "test_db",
        "--output", "/tmp/out",
        "--no-cleanup",
    ])
    assert args.host == "127.0.0.1"
    assert args.port == 9000
    assert args.user == "admin"
    assert args.password == "secret"
    assert args.ns == "test_ns"
    assert args.db == "test_db"
    assert args.cleanup is False


@pytest.mark.unit
def test_surql_escape_simple() -> None:
    assert _surql_escape("hello") == "'hello'"


@pytest.mark.unit
def test_surql_escape_with_quote() -> None:
    assert _surql_escape("it's") == "'it\\'s'"


@pytest.mark.unit
def test_surql_escape_with_backslash() -> None:
    assert _surql_escape("path\\to") == "'path\\\\to'"


@pytest.mark.unit
def test_surql_datetime_format() -> None:
    from datetime import datetime, timezone
    dt = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)
    result = _surql_datetime(dt)
    assert result == "'2026-06-26T12:00:00Z'"


@pytest.mark.unit
def test_id_helpers() -> None:
    assert _chunk_id("test") == "gv-proof-chunk-test"
    assert _page_id("test") == "gv-proof-page-test"
    assert _decision_id("test") == "gv-proof-decision-test"
    assert _symbol_id("test") == "gv-proof-symbol-test"
    assert _edge_id("test") == "gv-proof-edge-test"


@pytest.mark.unit
def test_toy_vector_dimensions() -> None:
    vec = _make_toy_vector(0, 0)
    assert len(vec) == 1536


@pytest.mark.unit
def test_toy_vector_determinism() -> None:
    v1 = _make_toy_vector(0, 0)
    v2 = _make_toy_vector(0, 0)
    assert v1 == v2


@pytest.mark.unit
def test_toy_vector_cluster_variance() -> None:
    v0 = _make_toy_vector(0, 0)
    v1 = _make_toy_vector(1, 0)
    assert v0 != v1


@pytest.mark.unit
def test_toy_vector_first_ten_nonzero() -> None:
    vec = _make_toy_vector(0, 0)
    assert all(v != 0.0 for v in vec[:10])
    assert all(v == 0.0 for v in vec[10:])


@pytest.mark.unit
def test_vector_sql_literal() -> None:
    vec = [0.1, 0.2, 0.3]
    result = _vector_sql_literal(vec)
    assert result == "[0.1,0.2,0.3]"


@pytest.mark.unit
def test_vector_sql_literal_1536() -> None:
    vec = _make_toy_vector(0, 0)
    result = _vector_sql_literal(vec)
    assert result.startswith("[0.95")
    assert result.endswith("]")
    assert result.count(",") == 1535


@pytest.mark.unit
def test_query_vector_near_cluster_dimensions() -> None:
    qv = _query_vector_near_cluster(0)
    assert len(qv) == 1536


@pytest.mark.unit
def test_query_vector_determinism() -> None:
    assert _query_vector_near_cluster(0) == _query_vector_near_cluster(0)


@pytest.mark.unit
def test_query_vector_differs_by_cluster() -> None:
    assert _query_vector_near_cluster(0) != _query_vector_near_cluster(1)


@pytest.mark.unit
def test_proof_sql_client_rejects_non_local() -> None:
    with pytest.raises(ValueError, match="host must be localhost"):
        ProofSqlClient(
            surreal_url="http://remote.example.com:8010",
            namespace="test",
            database="test",
            user="root",
            password="root",
        )


@pytest.mark.unit
def test_proof_sql_client_accepts_localhost() -> None:
    client = ProofSqlClient(
        surreal_url="http://localhost:8010",
        namespace="test",
        database="test",
        user="root",
        password="root",
    )
    assert client._url == "http://localhost:8010"


@pytest.mark.unit
def test_proof_sql_client_accepts_127_0_0_1() -> None:
    client = ProofSqlClient(
        surreal_url="http://127.0.0.1:8010",
        namespace="test",
        database="test",
        user="root",
        password="root",
    )
    assert client._url == "http://127.0.0.1:8010"


@pytest.mark.unit
def test_health_check_handles_unreachable() -> None:
    client = ProofSqlClient(
        surreal_url="http://localhost:19999",
        namespace="test",
        database="test",
        user="x",
        password="y",
        timeout=1,
    )
    result = client.health_check()
    assert result["status"] == "unreachable"


@pytest.mark.unit
def test_version_check_handles_unreachable() -> None:
    client = ProofSqlClient(
        surreal_url="http://localhost:19999",
        namespace="test",
        database="test",
        user="x",
        password="y",
        timeout=1,
    )
    result = client.version_check()
    assert result["status"] == "unreachable"


@pytest.mark.unit
def test_build_evidence_with_unavailable_db() -> None:
    db_info = {
        "health": {"status": "unreachable"},
        "version": {"status": "unreachable"},
        "available": False,
    }
    evidence = _build_evidence(db_info, None, None, None, 100.0)
    assert evidence["summary"] == "FAIL"
    assert evidence["overall_pass"] is False


@pytest.mark.unit
def test_build_evidence_with_all_pass() -> None:
    db_info = {
        "health": {"status": "ok"},
        "version": {"status": "ok", "version": "surrealdb-3.1.5"},
        "available": True,
    }
    schema = {
        "tables_found": [
            "artifact_cites_decision", "chunk_mentions_symbol",
            "claim", "code_symbol", "decision_event",
            "dependency_edge", "doc_chunk", "doc_page",
        ],
        "table_count": 8,
    }
    graph = {
        "graph_pass": True,
        "relations_created": 3,
        "traversals_executed": 4,
        "traversals": [
            {
                "query": "Forward traversal",
                "pass": True,
                "expected_decision_id": "dec-1",
                "found_decision_ids": ["dec-1"],
            },
            {
                "query": "Backward traversal",
                "pass": True,
                "expected_chunk_ids": ["chunk-a", "chunk-b"],
                "found_chunk_ids": ["chunk-a", "chunk-b"],
            },
        ],
    }
    vector = {
        "vector_pass": True,
        "chunk_count": 5,
        "queries_executed": 2,
        "queries": [
            {
                "label": "cluster_A",
                "order_pass": True,
                "result_count": 3,
                "expected_first_chunk": "gv-proof-chunk-pos-sizing-a",
                "results": [{"chunk_id": "gv-proof-chunk-pos-sizing-a", "vector_distance": 0.1}],
            },
            {
                "label": "cluster_B",
                "order_pass": True,
                "result_count": 3,
                "expected_first_chunk": "gv-proof-chunk-risk-limit-a",
                "results": [{"chunk_id": "gv-proof-chunk-risk-limit-a", "vector_distance": 0.1}],
            },
        ],
    }
    evidence = _build_evidence(db_info, schema, graph, vector, 500.0)
    assert evidence["summary"] == "PASS"
    assert evidence["overall_pass"] is True


@pytest.mark.unit
def test_build_evidence_with_graph_fail() -> None:
    db_info = {
        "health": {"status": "ok"},
        "version": {"status": "ok", "version": "surrealdb-3.1.5"},
        "available": True,
    }
    schema = {"tables_found": ["doc_chunk"], "table_count": 1}
    graph = {
        "graph_pass": False,
        "relations_created": 0,
        "traversals_executed": 1,
        "traversals": [
            {
                "query": "Forward traversal",
                "pass": False,
                "expected_decision_id": "dec-1",
                "found_decision_ids": [],
            },
        ],
    }
    evidence = _build_evidence(db_info, schema, graph, None, 300.0)
    assert evidence["summary"] == "FAIL"
    assert evidence["overall_pass"] is False


@pytest.mark.unit
def test_evidence_report_metadata() -> None:
    db_info = {
        "health": {"status": "ok"},
        "version": {"status": "ok", "version": "surrealdb-3.1.5"},
        "available": True,
    }
    evidence = _build_evidence(db_info, None, None, None, 250.0)
    meta = evidence["report_metadata"]
    assert meta["lr_status"] == "NO-GO"
    assert meta["isolation"]["namespace"] == "cdb_proof"
    assert meta["isolation"]["database"] == "graph_vector_proof"
    assert "Capability proof only" in meta["limitation"]


@pytest.mark.unit
def test_evidence_json_serializable() -> None:
    db_info = {
        "health": {"status": "ok"},
        "version": {"status": "ok", "version": "surrealdb-3.1.5"},
        "available": True,
    }
    schema = {"tables_found": ["doc_chunk"], "table_count": 1}
    graph = {
        "graph_pass": True,
        "relations_created": 3,
        "traversals_executed": 2,
        "traversals": [{"query": "T1", "pass": True, "expected_decision_id": "x", "found_decision_ids": ["x"]}],
    }
    vector = {
        "vector_pass": True,
        "chunk_count": 5,
        "queries_executed": 1,
        "queries": [{"label": "Q1", "order_pass": True, "result_count": 2, "expected_first_chunk": "c1", "results": [{"chunk_id": "c1", "vector_distance": 0.1}]}],
    }
    evidence = _build_evidence(db_info, schema, graph, vector, 100.0)
    serialized = json.dumps(evidence, default=str)
    assert isinstance(serialized, str)
    assert 'overall_pass": false' in serialized
    assert '"summary": "FAIL"' in serialized
    parsed = json.loads(serialized)
    assert parsed["report_metadata"]["lr_status"] == "NO-GO"


@pytest.mark.unit
def test_cli_exit_codes_are_distinct() -> None:
    codes = {EXIT_OK, EXIT_FAIL, EXIT_RUNTIME_UNAVAILABLE, EXIT_USAGE}
    assert len(codes) == 4
    assert EXIT_OK == 0
