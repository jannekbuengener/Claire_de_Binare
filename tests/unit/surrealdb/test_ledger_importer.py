"""Unit tests for SurrealDB ledger importer."""

from unittest.mock import patch, MagicMock

import pytest

from tools.surrealdb.ledger_importer import (
    DuplicateEventError,
    ImportConfig,
    _parse_duplicate_ids,
    build_surrealql,
    load_ledger_events_from_text,
    normalize_events,
    post_surrealql,
)


@pytest.mark.unit
def test_ledger_importer_idempotent_chain_and_redaction():
    sample = """
event_id: "evt-1"
timestamp: "2026-01-01T00:00:01Z"
agent:
  id: "codex"
  vendor: "openai"
  role: "execution"
action:
  type: "work.start"
  summary: "Start work"
scope:
  repo: "Claire_de_Binare"
evidence:
  - "token=test_secret_value_123"
---
event_id: "evt-2"
timestamp: "2026-01-01T00:00:02Z"
agent:
  id: "codex"
  vendor: "openai"
  role: "execution"
action:
  type: "branch.create"
  summary: "Create branch"
scope:
  repo: "Claire_de_Binare"
evidence:
  - "branch=feature/test"
"""
    events = load_ledger_events_from_text(sample)
    records = normalize_events(events, "ledger.yaml", "hash")

    assert len(records) == 2
    assert records[0]["event_kind"] == "work_start"
    assert records[1]["event_kind"] == "branch_create"
    assert records[0]["prev_event_id"] is None
    assert records[1]["prev_event_id"] == "evt-1"
    assert records[0]["evidence"][0] == "[REDACTED]"


# ============================================================
# Append-only enforcement tests (Issue #742)
# ============================================================


@pytest.mark.unit
def test_build_surrealql_uses_create_not_upsert():
    """build_surrealql must emit CREATE ... CONTENT, never UPSERT/MERGE."""
    records = [
        {"surreal_id": "ledger_event:evt-1", "event_id": "evt-1", "data": "x"},
        {"surreal_id": "ledger_event:evt-2", "event_id": "evt-2", "data": "y"},
    ]
    sql = build_surrealql(records)

    assert "CREATE ledger_event:evt-1 CONTENT" in sql
    assert "CREATE ledger_event:evt-2 CONTENT" in sql
    for forbidden in ("UPSERT", "MERGE", "UPDATE", "DELETE"):
        assert forbidden not in sql, f"SQL must not contain {forbidden}"


@pytest.mark.unit
def test_parse_duplicate_ids_detects_duplicates():
    """_parse_duplicate_ids extracts record ids from SurrealDB ERR results."""
    results = [
        {"status": "OK", "result": [{"id": "ledger_event:evt-1"}]},
        {
            "status": "ERR",
            "result": "Database record `ledger_event:evt-2` already exists",
        },
    ]
    ids = _parse_duplicate_ids(results)
    assert ids == ["ledger_event:evt-2"]


@pytest.mark.unit
def test_parse_duplicate_ids_unknown_format():
    """Unknown error format still produces an entry (not silently swallowed)."""
    results = [
        {"status": "ERR", "result": "record already exists but no backtick id"},
    ]
    ids = _parse_duplicate_ids(results)
    assert ids == ["<unknown>"]


@pytest.mark.unit
def test_parse_duplicate_ids_no_errors():
    """All-OK results produce empty list."""
    results = [
        {"status": "OK", "result": [{"id": "ledger_event:evt-1"}]},
    ]
    assert _parse_duplicate_ids(results) == []


@pytest.mark.unit
def test_post_surrealql_raises_on_duplicate():
    """post_surrealql raises DuplicateEventError when SurrealDB reports duplicates."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [
        {"status": "OK", "result": [{"id": "ledger_event:evt-1"}]},
        {
            "status": "ERR",
            "result": "Database record `ledger_event:evt-2` already exists",
        },
    ]

    config = ImportConfig(
        namespace="test", database="test", url="http://localhost:8000/sql"
    )

    with patch("tools.surrealdb.ledger_importer.requests.post", return_value=mock_response):
        with pytest.raises(DuplicateEventError) as exc_info:
            post_surrealql(config, "CREATE ledger_event:evt-1 CONTENT {};")
        assert "evt-2" in str(exc_info.value)
        assert exc_info.value.event_ids == ["ledger_event:evt-2"]
