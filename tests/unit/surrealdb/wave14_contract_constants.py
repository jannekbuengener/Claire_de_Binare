"""Test-local Wave-14 SurrealDB record and MCP query contract constants (#2643).

Not a runtime surface — consumed only by Wave-14 contract tests.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.surrealdb.context_importer import (
    ID_FIELD_BY_ARTIFACT,
    REQUIRED_JSONL_FIELDS,
    TABLE_BY_ARTIFACT,
)

SURQL_PATH = Path("infrastructure/surrealdb/context_intelligence_v0.surql")

WAVE14_JSONL_ARTIFACTS: tuple[str, ...] = (
    "evidence_refs",
    "claims",
    "decision_events",
    "agent_memories",
)

WAVE14_TABLES: tuple[str, ...] = tuple(
    TABLE_BY_ARTIFACT[artifact] for artifact in WAVE14_JSONL_ARTIFACTS
)

WAVE14_PK_FIELDS: dict[str, str] = {
    TABLE_BY_ARTIFACT[artifact]: ID_FIELD_BY_ARTIFACT[artifact]
    for artifact in WAVE14_JSONL_ARTIFACTS
}

WAVE14_JSONL_REQUIRED: dict[str, frozenset[str]] = {
    artifact: REQUIRED_JSONL_FIELDS[artifact] for artifact in WAVE14_JSONL_ARTIFACTS
}

# Indexer envelope fields are required in JSONL but not stored as Surreal columns.
JSONL_ENVELOPE_FIELDS: frozenset[str] = frozenset({"schema_version", "run_id"})

# Schema draft marks these stable-id + created_at fields as REQUIRED(v0-draft).
SURQL_REQUIRED_DRAFT_FIELDS: dict[str, frozenset[str]] = {
    "evidence_ref": frozenset({"evidence_id", "created_at"}),
    "claim": frozenset({"claim_id", "created_at"}),
    "decision_event": frozenset({"decision_id", "created_at"}),
    "agent_memory": frozenset({"memory_id", "created_at"}),
}

EVIDENCE_SCHEMA_TO_LOOKUP_ALIASES: dict[str, str] = {
    "validates": "claim_refs",
    "related_artifacts": "artifact_refs",
    "related_decisions": "decision_refs",
    "source_path": "source_refs",
}

CLAIM_SCHEMA_DEFAULTS: frozenset[str] = frozenset(
    {"topics", "topic", "artifact_refs", "decision_refs"}
)

MEMORY_SCHEMA_TO_READER_ALIASES: dict[str, str] = {
    "created_by": "agent",
    "ttl": "ttl_days",
}

MEMORY_SCHEMA_DEFAULTS: frozenset[str] = frozenset(
    {"topic", "topics", "artifact_refs", "decision_refs"}
)

DECISION_EVENT_NORMALIZED_KEYS: frozenset[str] = frozenset(
    {
        "decision_id",
        "title",
        "question",
        "answer",
        "decision_type",
        "status",
        "scope",
        "topics",
        "issue_refs",
        "evidence_refs",
        "claim_refs",
        "affected_artifacts",
        "agent",
        "human_go",
        "human_go_note",
        "superseded_by",
        "invalidated_by",
        "uncertainty",
        "comment",
        "created_at",
    }
)

MCP_OK_ENVELOPE_KEYS: frozenset[str] = frozenset({"tool", "status", "result", "metadata"})
MCP_ERROR_ENVELOPE_KEYS: frozenset[str] = frozenset({"tool", "status", "error", "metadata"})
MCP_METADATA_KEYS: frozenset[str] = frozenset({"query_time_ms", "source", "read_only"})
ALLOWED_MCP_SOURCES: frozenset[str] = frozenset(
    {"in_memory", "surrealdb-local", "surrealdb-local-unavailable"}
)

SERVICE_SCHEMA_VERSIONS: dict[str, str] = {
    "cdb_context_evidence_resolve": "evidence-lookup/v1",
    "cdb_context_claim_resolve": "claim-resolver/v1",
    "cdb_context_memory_get": "memory-read/v1",
    "cdb_context_trust_summary": "trust-summary/v1",
    "cdb_context_decision_history": "decision-history-query/v1",
    "cdb_context_decision_replay": "decision-replay-query/v2",
}

WAVE14_QUERY_RESULT_KEYS: dict[str, frozenset[str]] = {
    "cdb_context_evidence_resolve": frozenset(
        {
            "schema_version",
            "query",
            "mode",
            "matched_evidence",
            "evidence_by_strength",
            "stale_evidence_ids",
            "blocking_missing_ids",
            "evidence_summary",
            "warnings",
            "approval_semantics",
        }
    ),
    "cdb_context_claim_resolve": frozenset(
        {
            "schema_version",
            "query",
            "mode",
            "matched_claims",
            "disputed_claim_ids",
            "stale_claim_ids",
            "invalidated_claim_ids",
            "missing_evidence_claim_ids",
            "all_evidence_refs",
            "unresolved_evidence_refs",
            "confidence_summary",
            "status_counts",
            "warnings",
            "approval_semantics",
        }
    ),
    "cdb_context_memory_get": frozenset(
        {
            "schema_version",
            "query",
            "mode",
            "matched_memory",
            "stale_memory_ids",
            "superseded_memory_ids",
            "trust_counts",
            "memory_summary",
            "warnings",
            "approval_semantics",
        }
    ),
    "cdb_context_trust_summary": frozenset(
        {
            "schema_version",
            "operator_trust_contract_version",
            "scope",
            "topic",
            "artifact",
            "trust_level",
            "operator_trust_level",
            "operator_trust_mapping",
            "limitations",
            "authorization_semantics",
            "composite_score",
            "evidence_strength",
            "evidence_strength_score",
            "claim_status_summary",
            "claim_score",
            "decision_currentness",
            "decision_score",
            "memory_trust_summary",
            "memory_score",
            "stale_flags",
            "disputed_flags",
            "missing_evidence",
            "blocking_trust_findings",
            "recommended_next_reads",
            "confidence_summary",
            "warnings",
            "approval_semantics",
        }
    ),
    "cdb_context_decision_history": frozenset(
        {
            "schema_version",
            "query",
            "mode",
            "matched_decisions",
            "current_decisions",
            "superseded_decisions",
            "invalidated_decisions",
            "decision_chain",
            "evidence_refs",
            "claim_refs",
            "unresolved_evidence_refs",
            "unresolved_claim_refs",
            "uncertainty",
            "human_go",
            "warnings",
            "approval_semantics",
        }
    ),
    "cdb_context_decision_replay": frozenset(
        {
            "schema_version",
            "query",
            "decision_summary",
            "current_status",
            "old_decisions",
            "current_decisions",
            "superseded_decisions",
            "invalidated_decisions",
            "decision_chain",
            "evidence_chain",
            "claim_chain",
            "supersession_chain",
            "uncertainty",
            "stop_conditions",
            "human_go",
            "warnings",
            "approval_semantics",
            "evidence_links",
            "resolved_evidence",
            "unresolved_evidence_refs",
            "evidence_resolution_status",
            "evidence_warnings",
            "decision_chain_hash",
            "replay_explainability",
        }
    ),
}

_FIELD_RE = re.compile(r"^DEFINE FIELD (\w+) ON TABLE (\w+) ", re.MULTILINE)


def parse_surql_table_fields(surql_text: str, table: str) -> frozenset[str]:
    """Return all DEFINE FIELD names declared for *table* in the schema draft."""
    fields = {
        match.group(1)
        for match in _FIELD_RE.finditer(surql_text)
        if match.group(2) == table
    }
    return frozenset(fields)


def load_surql_text(path: Path = SURQL_PATH) -> str:
    return path.read_text(encoding="utf-8")
