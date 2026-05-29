"""Wave-14 SurrealDB context record schema contract tests (#2643)."""

from __future__ import annotations

import pytest

from tests.unit.surrealdb import wave14_contract_constants as contracts
from tools.mcp.context_evidence_memory_tools import (
    _normalize_claim_row,
    _normalize_evidence_ref_row,
    _normalize_memory_row,
)
from tools.surrealdb.context_importer import TABLE_BY_ARTIFACT
from tools.surrealdb.decision_history_query import (
    DecisionHistoryQueryRequest,
    _normalize_decision,
    query_decision_history_v1,
)


@pytest.fixture(scope="module")
def surql_text() -> str:
    return contracts.load_surql_text()


@pytest.mark.unit
@pytest.mark.parametrize("table", contracts.WAVE14_TABLES)
def test_surql_defines_wave14_table_and_pk_field(surql_text: str, table: str) -> None:
    assert f"DEFINE TABLE {table} SCHEMAFULL;" in surql_text
    pk_field = contracts.WAVE14_PK_FIELDS[table]
    assert f"DEFINE FIELD {pk_field} ON TABLE {table}" in surql_text
    assert f"ON TABLE {table} FIELDS {pk_field} UNIQUE" in surql_text


@pytest.mark.unit
@pytest.mark.parametrize("table", contracts.WAVE14_TABLES)
def test_surql_declares_created_at_for_wave14_tables(
    surql_text: str, table: str
) -> None:
    fields = contracts.parse_surql_table_fields(surql_text, table)
    assert "created_at" in fields
    for required in contracts.SURQL_REQUIRED_DRAFT_FIELDS[table]:
        assert required in fields


@pytest.mark.unit
@pytest.mark.parametrize(
    ("artifact", "table"),
    [
        (artifact, TABLE_BY_ARTIFACT[artifact])
        for artifact in contracts.WAVE14_JSONL_ARTIFACTS
    ],
)
def test_jsonl_required_fields_map_to_surql_columns(
    surql_text: str, artifact: str, table: str
) -> None:
    surql_fields = contracts.parse_surql_table_fields(surql_text, table)
    jsonl_required = contracts.WAVE14_JSONL_REQUIRED[artifact]
    record_fields = jsonl_required - contracts.JSONL_ENVELOPE_FIELDS
    missing = record_fields - surql_fields
    assert (
        not missing
    ), f"{artifact} JSONL fields missing from {table} surql: {sorted(missing)}"


@pytest.mark.unit
def test_evidence_ref_normalization_aliases() -> None:
    row = {
        "evidence_id": "ev-schema-001",
        "validates": ["claim-001"],
        "related_artifacts": ["tools/surrealdb/evidence_lookup.py"],
        "related_decisions": ["dec-001"],
        "source_path": "tests/unit/test_foo.py",
    }
    normalized = _normalize_evidence_ref_row(row)

    for (
        schema_field,
        contract_field,
    ) in contracts.EVIDENCE_SCHEMA_TO_LOOKUP_ALIASES.items():
        if schema_field == "source_path":
            assert normalized[contract_field] == [row[schema_field]]
        else:
            assert normalized[contract_field] == row[schema_field]

    assert normalized["claim_refs"] == row["validates"]
    assert normalized["artifact_refs"] == row["related_artifacts"]


@pytest.mark.unit
def test_evidence_ref_normalization_preserves_existing_contract_fields() -> None:
    row = {
        "evidence_id": "ev-fixture-001",
        "claim_refs": ["claim-preexisting"],
        "artifact_refs": ["tools/mcp/context_bridge.py"],
        "decision_refs": [],
        "source_refs": ["docs/example.md"],
    }
    normalized = _normalize_evidence_ref_row(row)
    assert normalized["claim_refs"] == ["claim-preexisting"]
    assert normalized["artifact_refs"] == ["tools/mcp/context_bridge.py"]
    assert normalized["source_refs"] == ["docs/example.md"]


@pytest.mark.unit
def test_claim_normalization_adds_resolver_defaults() -> None:
    row = {
        "claim_id": "claim-schema-001",
        "title": "Schema claim",
        "statement": "read-only",
        "scope": "wave14",
        "status": "supported",
        "evidence_refs": ["ev-001"],
    }
    normalized = _normalize_claim_row(row)
    for field in contracts.CLAIM_SCHEMA_DEFAULTS:
        assert field in normalized
    assert normalized["topics"] == []
    assert normalized["topic"] is None
    assert normalized["artifact_refs"] == []
    assert normalized["decision_refs"] == []


@pytest.mark.unit
def test_memory_normalization_maps_schema_aliases() -> None:
    row = {
        "memory_id": "mem-schema-001",
        "scope": "wave14",
        "namespace": "session",
        "memory_type": "constraint",
        "content": "read-only MCP",
        "created_by": "agent-test-001",
        "ttl": 7,
    }
    normalized = _normalize_memory_row(row)
    assert normalized["agent"] == "agent-test-001"
    assert normalized["ttl"] == 7
    assert "ttl_days" not in normalized
    for field in contracts.MEMORY_SCHEMA_DEFAULTS:
        assert field in normalized


@pytest.mark.unit
def test_agent_memory_stale_after_schema_is_optional(surql_text: str) -> None:
    assert (
        "DEFINE FIELD stale_after ON TABLE agent_memory TYPE option<int>;" in surql_text
    )


@pytest.mark.unit
def test_agent_memory_superseded_by_schema_is_optional(surql_text: str) -> None:
    assert (
        "DEFINE FIELD superseded_by ON TABLE agent_memory TYPE option<string>;"
        in surql_text
    )


@pytest.mark.unit
def test_memory_normalization_uses_scope_when_created_by_missing() -> None:
    row = {
        "memory_id": "mem-scope-fallback",
        "scope": "wave14",
        "memory_type": "note",
        "content": "fallback agent",
    }
    normalized = _normalize_memory_row(row)
    assert normalized["agent"] == "wave14"


@pytest.mark.unit
def test_decision_event_normalization_shape() -> None:
    raw = {
        "decision_id": "dec-schema-001",
        "title": "Schema decision",
        "question": "Use scope filter?",
        "answer": "Yes",
        "decision_type": "implementation",
        "status": "accepted",
        "scope": "wave14",
        "evidence_refs": ["ev-001"],
        "claim_refs": ["claim-001"],
        "affected_artifacts": ["tools/mcp/context_decision_tools.py"],
        "agent": "codex",
        "human_go": False,
        "created_at": "2026-05-25T00:00:00Z",
    }
    normalized = _normalize_decision(raw)
    assert contracts.DECISION_EVENT_NORMALIZED_KEYS <= frozenset(normalized.keys())
    assert normalized["decision_id"] == "dec-schema-001"
    assert normalized["human_go"] is False
    assert normalized["created_at"] == "2026-05-25T00:00:00+00:00"


@pytest.mark.unit
def test_decision_event_null_and_empty_fields_do_not_crash_history_query() -> None:
    events = [
        {
            "decision_id": "dec-empty-001",
            "title": None,
            "question": "",
            "answer": None,
            "decision_type": "",
            "status": "accepted",
            "scope": "wave14",
            "evidence_refs": [],
            "claim_refs": None,
            "affected_artifacts": [],
            "agent": None,
            "human_go": None,
            "created_at": None,
        }
    ]
    result = query_decision_history_v1(
        events,
        DecisionHistoryQueryRequest(mode="by_scope", scope="wave14"),
    )
    assert (
        result["schema_version"]
        == contracts.SERVICE_SCHEMA_VERSIONS["cdb_context_decision_history"]
    )
    assert len(result["matched_decisions"]) == 1
    decision = result["matched_decisions"][0]
    assert decision["decision_id"] == "dec-empty-001"
    assert decision["title"] == ""
    assert decision["evidence_refs"] == []
    assert decision["claim_refs"] == []
