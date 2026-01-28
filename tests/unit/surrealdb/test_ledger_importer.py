"""Unit tests for SurrealDB ledger importer."""

import pytest

from tools.surrealdb.ledger_importer import (
    load_ledger_events_from_text,
    normalize_events,
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
