"""Unit tests for Context Query statement classifier v0 (#2080)."""

from __future__ import annotations

import pytest

from tools.surrealdb.context_query import WriteDeniedError, classify_statement


@pytest.mark.unit
@pytest.mark.parametrize(
    ("statement", "operation"),
    [
        ("SELECT * FROM doc_chunk", "SELECT"),
        ("INFO FOR DB", "INFO FOR DB"),
        ("INFO FOR TABLE doc_chunk", "INFO FOR TABLE"),
        ("INFO FOR NS", "INFO FOR NS"),
    ],
)
def test_read_only_statements_are_allowed(statement: str, operation: str) -> None:
    result = classify_statement(statement)

    assert result.allowed is True
    assert result.operation == operation


@pytest.mark.unit
@pytest.mark.parametrize(
    "statement",
    [
        "CREATE doc_chunk SET title = 'x'",
        "INSERT INTO doc_chunk { title: 'x' }",
        "UPDATE doc_chunk SET title = 'x'",
        "UPSERT doc_chunk CONTENT {}",
        "DELETE doc_chunk",
        "RELATE a->edge->b",
        "MERGE doc_chunk CONTENT {}",
        "PATCH doc_chunk [{ op: 'replace' }]",
        "DEFINE TABLE doc_chunk",
        "REMOVE TABLE doc_chunk",
        "ALTER TABLE doc_chunk",
        "LIVE SELECT * FROM doc_chunk",
        "KILL 'abc'",
        "USE NS test DB test",
        "BEGIN TRANSACTION",
        "COMMIT TRANSACTION",
        "CANCEL TRANSACTION",
    ],
)
def test_write_schema_live_and_control_keywords_are_blocked(statement: str) -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement(statement)


@pytest.mark.unit
def test_explain_is_blocked() -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement("EXPLAIN SELECT * FROM doc_chunk")


@pytest.mark.unit
def test_show_changes_is_blocked() -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement("SHOW CHANGES FOR TABLE doc_chunk")


@pytest.mark.unit
def test_info_for_root_is_blocked() -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement("INFO FOR ROOT")


@pytest.mark.unit
def test_multi_statement_with_semicolon_is_blocked() -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement("SELECT * FROM doc_chunk; SELECT * FROM repo_artifact")

    with pytest.raises(WriteDeniedError):
        classify_statement("SELECT * FROM doc_chunk;")


@pytest.mark.unit
def test_whitespace_and_case_variants_are_stable() -> None:
    result = classify_statement("  select\n  *\tfrom   doc_chunk  ")

    assert result.allowed is True
    assert result.operation == "SELECT"
    assert result.normalized == "SELECT * FROM DOC_CHUNK"


@pytest.mark.unit
@pytest.mark.parametrize("statement", ["APPLY something", "MIGRATION run", "TRANSACTION start"])
def test_transaction_migration_apply_flows_are_blocked(statement: str) -> None:
    with pytest.raises(WriteDeniedError):
        classify_statement(statement)
