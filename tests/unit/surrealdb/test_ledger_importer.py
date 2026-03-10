"""Unit tests for SurrealDB ledger importer."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from tools.surrealdb.ledger_importer import (
    DuplicateEventError,
    ImportConfig,
    LEDGER_IMPORT_DUPLICATE_EVENT_ID,
    LEDGER_IMPORT_HASH_MISMATCH,
    LEDGER_IMPORT_SIGNATURE_INVALID,
    LEDGER_IMPORT_SIGNATURE_UNSUPPORTED,
    _parse_duplicate_ids,
    build_surrealql,
    load_ledger_events_from_text,
    main,
    normalize_events,
    post_surrealql,
)


def _write_ledger_file(tmp_path, text: str):
    ledger_path = tmp_path / "ledger.yaml"
    ledger_path.write_text(text, encoding="utf-8")
    return ledger_path


def _run_main(monkeypatch, ledger_path, *extra_args: str) -> int:
    monkeypatch.setattr(
        "sys.argv",
        [
            "ledger_importer.py",
            str(ledger_path),
            "--url",
            "http://surreal.test/sql",
            *extra_args,
        ],
    )
    return main()


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
    assert len(records[0]["integrity"]["sha256"]) == 64
    assert records[0]["integrity"]["hash_verified"] is False


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
    assert "BEGIN TRANSACTION;" in sql
    assert "COMMIT TRANSACTION;" in sql
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
    assert ids == ["evt-2"]


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

    with patch(
        "tools.surrealdb.ledger_importer.requests.post", return_value=mock_response
    ):
        with pytest.raises(DuplicateEventError) as exc_info:
            post_surrealql(config, "CREATE ledger_event:evt-1 CONTENT {};")
        assert "evt-2" in str(exc_info.value)
        assert exc_info.value.event_ids == ["evt-2"]


@pytest.mark.unit
def test_main_duplicate_event_id_preflight_aborts_without_write(
    tmp_path, monkeypatch, caplog
):
    ledger_path = _write_ledger_file(
        tmp_path,
        """
event_id: "evt-1"
timestamp: "2026-01-01T00:00:01Z"
agent:
  id: "codex"
action:
  type: "work.start"
  summary: "Start work"
""",
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = [{"status": "OK", "result": ["evt-1"]}]
    queries: list[str] = []

    def fake_post(url, headers, data, timeout):
        queries.append(data)
        return mock_response

    with caplog.at_level(logging.ERROR):
        with patch(
            "tools.surrealdb.ledger_importer.requests.post", side_effect=fake_post
        ) as mock_post:
            exit_code = _run_main(monkeypatch, ledger_path)

    assert exit_code == 1
    assert mock_post.call_count == 1
    assert queries[0].startswith(
        "SELECT VALUE event_id FROM ledger_event WHERE event_id IN"
    )
    assert LEDGER_IMPORT_DUPLICATE_EVENT_ID in caplog.text
    assert '"import_correlation_id":"' in caplog.text
    assert '"reason":"event_id already exists in ledger_event"' in caplog.text


@pytest.mark.unit
def test_main_hash_mismatch_aborts_without_db_write(tmp_path, monkeypatch, caplog):
    ledger_path = _write_ledger_file(
        tmp_path,
        """
event_id: "evt-1"
event_hash: "deadbeef"
timestamp: "2026-01-01T00:00:01Z"
agent:
  id: "codex"
action:
  type: "work.start"
  summary: "Start work"
""",
    )

    with caplog.at_level(logging.ERROR):
        with patch("tools.surrealdb.ledger_importer.requests.post") as mock_post:
            exit_code = _run_main(monkeypatch, ledger_path)

    assert exit_code == 1
    mock_post.assert_not_called()
    assert LEDGER_IMPORT_HASH_MISMATCH in caplog.text
    assert (
        '"reason":"declared hash at event_hash does not match canonical payload hash"'
        in caplog.text
    )


@pytest.mark.unit
def test_main_signature_present_aborts_without_db_write(tmp_path, monkeypatch, caplog):
    ledger_path = _write_ledger_file(
        tmp_path,
        """
event_id: "evt-1"
signature: "sig-test"
timestamp: "2026-01-01T00:00:01Z"
agent:
  id: "codex"
action:
  type: "work.start"
  summary: "Start work"
""",
    )

    with caplog.at_level(logging.ERROR):
        with patch("tools.surrealdb.ledger_importer.requests.post") as mock_post:
            exit_code = _run_main(monkeypatch, ledger_path)

    assert exit_code == 1
    mock_post.assert_not_called()
    assert LEDGER_IMPORT_SIGNATURE_UNSUPPORTED in caplog.text
    assert (
        '"reason":"signature at signature is present but no verifier is configured"'
        in caplog.text
    )


@pytest.mark.unit
def test_main_signature_invalid_aborts_without_db_write(tmp_path, monkeypatch, caplog):
    ledger_path = _write_ledger_file(
        tmp_path,
        """
event_id: "evt-1"
signature: ""
timestamp: "2026-01-01T00:00:01Z"
agent:
  id: "codex"
action:
  type: "work.start"
  summary: "Start work"
""",
    )

    with caplog.at_level(logging.ERROR):
        with patch("tools.surrealdb.ledger_importer.requests.post") as mock_post:
            exit_code = _run_main(monkeypatch, ledger_path)

    assert exit_code == 1
    mock_post.assert_not_called()
    assert LEDGER_IMPORT_SIGNATURE_INVALID in caplog.text
    assert '"reason":"signature at signature is empty or malformed"' in caplog.text
