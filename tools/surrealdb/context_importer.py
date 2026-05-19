"""SurrealDB context importer CLI (offline by default; gated local apply).

Issues:
    #2068 - scaffold (Wave 10, Slice 1)
    #2069 - config loader
    #2070 - JSONL validation
    #2071 - plan
    #2072 - reconcile (dry-run)
    #2073 - explicit local apply mode (this slice)
    #2074 - tombstone handling   (this slice)
Parent: #2067 / Epic #1976

This module implements the offline CLI plus a strictly gated
local-dev apply pipeline with a mockable adapter boundary.

Design rules enforced here:

* Default behavior is dry-run / no-write.
* The ``apply`` subcommand requires the explicit combination
  ``--apply --apply-mode local-dev --config <path> --input-dir <dir>
  --run-id <str>``; any other invocation of apply (subcommand without
  ``--apply``, or ``--apply`` on a non-apply subcommand) is hard-blocked
  with exit code 5 (``WRITE_DENIED``).
* The default apply adapter is the in-memory, no-network
  ``InMemoryContextApplyAdapter``. A real SurrealDB adapter is
  explicitly OUT-OF-SCOPE in this slice and is not wired into the CLI.
* The local-dev apply gate additionally requires the loaded config's
  ``surreal_url`` host to be in ``LOCAL_DEV_ALLOWED_HOSTS``.
* Tombstone handling is field-only (``tombstoned``, ``tombstoned_at``,
  ``tombstone_reason``, ``last_seen_run_id``, ``superseded_by``). There
  is no hard-delete API on the apply adapter.
* ``tombstoned_at`` is produced via an injected
  :class:`core.utils.clock.ClockProvider` (default: ``SystemClock``)
  and serialized as ISO8601 UTC; tests inject a ``FixedClock`` for
  determinism.
* No SurrealDB connection is opened by the in-memory adapter.

Subcommands:
    validate-jsonl, plan, dry-run, apply, audit, rollback-plan

Exit codes (aligned with the context-indexer contract):
    0 = success
    1 = validation failure (incl. blocking reconcile findings on apply)
    2 = argparse usage error (raised by argparse itself)
    3 = input-not-found
    4 = unsupported format
    5 = write denied (path violation, apply gate violation,
        forbidden table at apply boundary)
    6 = internal error
"""

from __future__ import annotations

import argparse
import base64
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Protocol
import urllib.error
import urllib.request
from urllib.parse import urlparse

import yaml

from core.utils.clock import ClockProvider, SystemClock

logger = logging.getLogger(__name__)


SCHEMA_VERSION = "context-importer/v0"
AUDIT_SCHEMA_VERSION = "context-import-audit/v0"
TOOL_VERSION = SCHEMA_VERSION

SUPPORTED_COMMANDS = (
    "validate-jsonl",
    "plan",
    "dry-run",
    "apply",
    "audit",
    "rollback-plan",
)

SUPPORTED_FORMATS = frozenset({"json", "jsonl", "markdown"})

AUDIT_MODE_PLAN = "plan"
AUDIT_MODE_DRY_RUN = "dry-run"
AUDIT_MODE_APPLY = "apply"
SUPPORTED_AUDIT_MODES = frozenset(
    {AUDIT_MODE_PLAN, AUDIT_MODE_DRY_RUN, AUDIT_MODE_APPLY}
)

ALLOWED_OUTPUT_PREFIXES = ("artifacts", "temp")

CONFIG_SCHEMA_VERSION = "context-import-local/v0"
INDEXER_SCHEMA_VERSION = "context-indexer/v0"

EXPECTED_JSONL_FILES = {
    "repo_artifacts": "repo_artifacts.jsonl",
    "doc_pages": "doc_pages.jsonl",
    "doc_sections": "doc_sections.jsonl",
    "doc_chunks": "doc_chunks.jsonl",
    "code_symbols": "code_symbols.jsonl",
    "import_references": "import_references.jsonl",
    "test_cases": "test_cases.jsonl",
    "config_references": "config_references.jsonl",
    "doc_code_links": "doc_code_links.jsonl",
    "dependency_edges": "dependency_edges.jsonl",
    "evidence_refs": "evidence_refs.jsonl",
    "claims": "claims.jsonl",
    "decision_events": "decision_events.jsonl",
    "agent_memories": "agent_memories.jsonl",
}

IMPORT_ORDER = (
    "repo_artifacts",
    "doc_pages",
    "doc_sections",
    "doc_chunks",
    "code_symbols",
    "import_references",
    "test_cases",
    "config_references",
    "doc_code_links",
    "dependency_edges",
    "evidence_refs",
    "claims",
    "decision_events",
    "agent_memories",
)

TABLE_BY_ARTIFACT = {
    "repo_artifacts": "repo_artifact",
    "doc_pages": "doc_page",
    "doc_sections": "doc_section",
    "doc_chunks": "doc_chunk",
    "code_symbols": "code_symbol",
    "import_references": "import_reference",
    "test_cases": "test_case",
    "config_references": "config_reference",
    "doc_code_links": "doc_code_link",
    "dependency_edges": "dependency_edge",
    "evidence_refs": "evidence_ref",
    "claims": "claim",
    "decision_events": "decision_event",
    "agent_memories": "agent_memory",
}

ID_FIELD_BY_ARTIFACT = {
    "repo_artifacts": "artifact_id",
    "doc_pages": "page_id",
    "doc_sections": "section_id",
    "doc_chunks": "chunk_id",
    "code_symbols": "symbol_id",
    "import_references": "import_id",
    "test_cases": "test_id",
    "config_references": "config_ref_id",
    "doc_code_links": "link_id",
    "dependency_edges": "edge_id",
    "evidence_refs": "evidence_id",
    "claims": "claim_id",
    "decision_events": "decision_id",
    "agent_memories": "memory_id",
}

REQUIRED_JSONL_FIELDS: dict[str, frozenset[str]] = {
    "repo_artifacts": frozenset(
        {
            "schema_version",
            "run_id",
            "artifact_id",
            "source_path",
            "file_type",
            "raw_sha256",
            "normalized_sha256",
            "source_hash",
            "integrity_algo",
            "size_bytes",
            "sensitivity",
        }
    ),
    "doc_pages": frozenset(
        {"schema_version", "run_id", "page_id", "source_path", "source_hash", "title"}
    ),
    "doc_sections": frozenset(
        {
            "schema_version",
            "run_id",
            "section_id",
            "page_id",
            "source_path",
            "source_hash",
            "heading",
            "section_level",
        }
    ),
    "doc_chunks": frozenset(
        {
            "schema_version",
            "run_id",
            "chunk_id",
            "page_id",
            "section_id",
            "source_path",
            "source_hash",
            "content",
            "content_hash",
        }
    ),
    "code_symbols": frozenset(
        {"schema_version", "run_id", "symbol_id", "source_path", "source_hash", "name"}
    ),
    "import_references": frozenset(
        {
            "schema_version",
            "run_id",
            "import_id",
            "source_path",
            "source_hash",
            "module",
        }
    ),
    "test_cases": frozenset(
        {
            "schema_version",
            "run_id",
            "test_id",
            "source_path",
            "source_hash",
            "symbol_id",
            "name",
        }
    ),
    "config_references": frozenset(
        {
            "schema_version",
            "run_id",
            "config_ref_id",
            "source_path",
            "source_hash",
            "config_key",
            "sensitive",
        }
    ),
    "doc_code_links": frozenset(
        {
            "schema_version",
            "run_id",
            "link_id",
            "source_path",
            "source_hash",
            "target_symbol",
        }
    ),
    "dependency_edges": frozenset(
        {"schema_version", "run_id", "edge_id", "from_id", "to_id", "edge_type"}
    ),
    "evidence_refs": frozenset(
        {"schema_version", "run_id", "evidence_id", "created_at"}
    ),
    "claims": frozenset(
        {"schema_version", "run_id", "claim_id", "created_at"}
    ),
    "decision_events": frozenset(
        {"schema_version", "run_id", "decision_id", "created_at"}
    ),
    "agent_memories": frozenset(
        {"schema_version", "run_id", "memory_id", "created_at"}
    ),
}

TRADING_STATE_TABLES = frozenset(
    {
        "orders",
        "fills",
        "positions",
        "balances",
        "pnl",
        "risk_state",
        "execution_state",
    }
)

GOVERNANCE_MIRROR_TABLES = frozenset(
    {
        "governance_event",
        "governance_decision",
        "governance_state",
    }
)

FORBIDDEN_CONTEXT_IMPORT_TABLES = TRADING_STATE_TABLES | GOVERNANCE_MIRROR_TABLES

# Wave-14 Context Intelligence tables (evidence / claim / decision / memory).
# Kept as an explicit documentation anchor for the Context-only table surface.
# The JSONL artifacts for these tables are defined in the import constants above.
WAVE14_CONTEXT_IMPORT_TABLES = frozenset(
    {
        "evidence_ref",
        "claim",
        "decision_event",
        "agent_memory",
    }
)

ALLOWED_CONTEXT_IMPORT_TABLES = (
    frozenset(TABLE_BY_ARTIFACT.values()) | WAVE14_CONTEXT_IMPORT_TABLES
)

ALLOWED_AUTH_MODES = frozenset({"none", "root", "scope"})

# Apply mode constants (#2073). The CLI only exposes ``local-dev``;
# any other apply mode is rejected at the gate.
APPLY_MODE_LOCAL_DEV = "local-dev"
SUPPORTED_APPLY_MODES = frozenset({APPLY_MODE_LOCAL_DEV})

# Local-dev gate: the loaded config's ``surreal_url`` host must resolve
# to one of these hosts. This is a defense-in-depth check; the
# in-memory adapter never opens any socket regardless.
LOCAL_DEV_ALLOWED_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

# Apply operation kinds (#2073/#2074). ``delete`` is intentionally not
# part of this enum: there is no hard-delete API.
APPLY_OP_CREATE = "create"
APPLY_OP_UPDATE = "update"
APPLY_OP_TOMBSTONE = "tombstone"
APPLY_OP_KINDS = frozenset({APPLY_OP_CREATE, APPLY_OP_UPDATE, APPLY_OP_TOMBSTONE})

# Tombstone field names (#2074). Adapter callers are required to set
# these on the tombstone payload; the in-memory adapter validates the
# shape so regressions are caught at unit-test time.
TOMBSTONE_FIELD_FLAG = "tombstoned"
TOMBSTONE_FIELD_AT = "tombstoned_at"
TOMBSTONE_FIELD_REASON = "tombstone_reason"
TOMBSTONE_FIELD_LAST_SEEN_RUN_ID = "last_seen_run_id"
TOMBSTONE_FIELD_SUPERSEDED_BY = "superseded_by"
TOMBSTONE_REQUIRED_FIELDS = frozenset(
    {
        TOMBSTONE_FIELD_FLAG,
        TOMBSTONE_FIELD_AT,
        TOMBSTONE_FIELD_REASON,
        TOMBSTONE_FIELD_LAST_SEEN_RUN_ID,
        TOMBSTONE_FIELD_SUPERSEDED_BY,
    }
)
TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT = "record_removed_from_snapshot"

# A real local SurrealDB adapter is implemented behind an explicit
# opt-in gate (--adapter surrealdb-local / CDB_CONTEXT_APPLY_ADAPTER).
# The CLI defaults to the in-memory adapter. This constant is exported
# for documentation and regression.
REAL_SURREALDB_ADAPTER_AVAILABLE = True
ADAPTER_KIND_IN_MEMORY = "in-memory"
ADAPTER_KIND_SURREALDB_LOCAL = "surrealdb-local"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:")
SECRET_LIKE_KEYS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "auth_token",
        "bearer_token",
        "secret_token",
        "api_key",
        "private_key",
        "password",
        "passwd",
        "secret",
        "credential",
        "auth_key",
        "access_key",
        "signing_key",
        "encryption_key",
    }
)
BENIGN_TOKEN_KEYS = frozenset(
    {
        "tokens_estimate",
        "token_count",
        "max_tokens",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    }
)
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|private[_-]?key|password|passwd|secret|token|credential)"
    r"\b\s*[:=]\s*[\"']?[A-Za-z0-9_.+/=@:-]{12,}"
)
AWS_ACCESS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TRADING_STATE_PATH_PARTS = frozenset(
    {
        "orders",
        "positions",
        "fills",
        "balances",
        "exposures",
        "live_risk_state",
        "broker_state",
        "execution_state",
    }
)

# Fields stripped from JSONL records before writing to SurrealDB.
# Includes importer-internal fields (__line) and JSONL envelope fields
# (schema_version, run_id, sensitivity) that are not declared in any table
# schema. SurrealDB v2 SCHEMAFULL tables reject undeclared fields; SCHEMALESS
# tables accept them but these fields carry no domain meaning in the DB.
_JSONL_INTERNAL_FIELDS = frozenset({"__line", "schema_version", "run_id", "sensitivity"})

# Datetime field names declared as TYPE datetime in context_intelligence_v0.surql.
# SurrealDB v2 SCHEMAFULL tables reject plain JSON strings for TYPE datetime fields
# when records are written via the HTTP /sql endpoint.  The _payload_to_surql_content
# helper converts only these allowlisted fields (when their value is an ISO-8601-Z
# string) to SurrealQL datetime literals (d"...").
_SURQL_DATETIME_FIELDS: frozenset[str] = frozenset({
    "collected_at",
    "computed_at",
    "created_at",
    "detected_at",
    "expires_at",
    "generated_at",
    "observed_at",
})
_SURQL_DATETIME_RE: re.Pattern[str] = re.compile(
    r'"('
    + "|".join(sorted(_SURQL_DATETIME_FIELDS))
    + r')":\s*"(\d{4}-\d{2}-\d{2}T[^"]+Z)"'
)

# SurrealDB table names that have a real schema table (from TABLE_BY_ARTIFACT).
# Used by _remap_record_refs_for_db_payload to gate dependency_edge ref building:
# virtual nodes (e.g. "module", "symbol_mention") are absent and refs are skipped.
_KNOWN_SURQL_RECORD_TABLES: frozenset[str] = frozenset(TABLE_BY_ARTIFACT.values())

# Record-ref field names that must be written as unquoted SurrealDB record refs
# rather than plain JSON strings.
_SURQL_RECORD_REF_FIELDS: frozenset[str] = frozenset(
    {"from_ref", "page_ref", "section_ref", "to_ref"}
)
# Matches the JSON-serialised form of a record-ref value produced by
# _remap_record_refs_for_db_payload after json.dumps(..., ensure_ascii=False).
# ensure_ascii=False is required so that U+27E8/U+27E9 (⟨⟩) appear as literal
# Unicode chars in the JSON output and can be matched by this pattern.
# Example input:  "page_ref": "doc_page:⟨page-example⟩"
# Capture groups: (1) field name, (2) table:⟨id⟩  (without quotes)
# Table prefix alternation is derived from _KNOWN_SURQL_RECORD_TABLES so that
# doc_page/doc_section (existing) and repo_artifact/code_symbol (dependency_edge)
# are all covered without hardcoding.
_SURQL_RECORD_REF_RE: re.Pattern[str] = re.compile(
    '"('
    + "|".join(sorted(_SURQL_RECORD_REF_FIELDS))
    + ')":\\s*"((?:'
    + "|".join(sorted(_KNOWN_SURQL_RECORD_TABLES))
    + '):\u27e8[^\u27e9]+\u27e9)"'
)

# Supplementary-plane Unicode characters (U+10000–U+10FFFF, e.g. emoji) are encoded
# as 4-byte UTF-8 sequences when json.dumps(..., ensure_ascii=False) is used.
# SurrealDB's HTTP /sql endpoint returns HTTP 400 for statements that contain literal
# 4-byte UTF-8 code points in string values (confirmed by all 9 doc_page failures in
# import-run10.json — every failing title contains emoji; all 593 passing ones do not).
# BMP characters (U+0000–U+FFFF), including the ⟨⟩ bracket chars used for record refs,
# are not affected and must remain as literal Unicode for _SURQL_RECORD_REF_RE to match.
_SUPPLEMENTARY_UNICODE_RE: re.Pattern[str] = re.compile(r"[\U00010000-\U0010FFFF]")


def _escape_supplementary(m: re.Match[str]) -> str:
    """Convert a supplementary-plane code point to a JSON \\uXXXX\\uYYYY surrogate pair."""
    cp = ord(m.group()) - 0x10000
    return f"\\u{0xD800 | (cp >> 10):04x}\\u{0xDC00 | (cp & 0x3FF):04x}"


# Maps SurrealDB table name → [(src_field, dst_field, target_table), ...]
# _remap_record_refs_for_db_payload uses this to convert plain-string ID fields
# emitted by the indexer (e.g. page_id) into SurrealDB record-ref strings
# (e.g. page_ref = "doc_page:⟨id⟩") before the DB-write payload is serialised.
# The JSONL contract (page_id / section_id) is not changed; only the adapter
# payload for create/update is remapped.
_TABLE_RECORD_REF_REMAP: dict[str, list[tuple[str, str, str]]] = {
    "doc_section": [("page_id", "page_ref", "doc_page")],
    "doc_chunk": [
        ("page_id", "page_ref", "doc_page"),
        ("section_id", "section_ref", "doc_section"),
    ],
}


def _remap_record_refs_for_db_payload(
    table: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Remap plain-string ID fields to SurrealDB record-ref strings for *table*.

    For tables listed in ``_TABLE_RECORD_REF_REMAP``, pops the source field
    (e.g. ``page_id``) and inserts the destination field (e.g. ``page_ref``)
    with a record-ref string in the form ``"doc_page:\u27e8<id>\u27e9"``.

    For ``dependency_edge`` the source and target tables are dynamic and come
    from ``from_table``/``to_table`` payload fields emitted by the indexer.
    Both ``from_id``/``to_id`` and ``from_table``/``to_table`` are always
    popped from the DB payload (they are not SurrealDB schema fields).  If
    ``from_table``/``to_table`` name a real schema table (present in
    ``_KNOWN_SURQL_RECORD_TABLES``) the corresponding ``from_ref``/``to_ref``
    record-ref is built; otherwise the field is omitted and SurrealDB's own
    ``TYPE record`` constraint will surface the gap.  Virtual/inferred nodes
    (``module``, ``symbol_mention``) fall into this category — edges that
    target them continue to fail import the same as before this change.

    The ref string is later unquoted by ``_payload_to_surql_content`` via
    ``_SURQL_RECORD_REF_RE``, producing a valid SurrealDB ``TYPE record`` value.

    All other tables are returned unchanged (no-op).
    """
    mappings = _TABLE_RECORD_REF_REMAP.get(table)
    if mappings is not None:
        result = dict(payload)
        for src_field, dst_field, target_table in mappings:
            raw_id = result.pop(src_field, None)
            if raw_id and isinstance(raw_id, str):
                escaped = raw_id.replace("\u27e9", "\\u27e9")
                result[dst_field] = f"{target_table}:\u27e8{escaped}\u27e9"
        return result
    if table == "dependency_edge":
        result = dict(payload)
        from_table = result.pop("from_table", None)
        to_table = result.pop("to_table", None)
        from_id = result.pop("from_id", None)
        to_id = result.pop("to_id", None)
        if from_table in _KNOWN_SURQL_RECORD_TABLES and from_id and isinstance(from_id, str):
            escaped = from_id.replace("\u27e9", "\\u27e9")
            result["from_ref"] = f"{from_table}:\u27e8{escaped}\u27e9"
        if to_table in _KNOWN_SURQL_RECORD_TABLES and to_id and isinstance(to_id, str):
            escaped = to_id.replace("\u27e9", "\\u27e9")
            result["to_ref"] = f"{to_table}:\u27e8{escaped}\u27e9"
        return result
    return payload


def _payload_to_surql_content(payload: dict[str, Any]) -> str:
    """Serialize *payload* to a SurrealQL CONTENT string.

    Behaves like ``json.dumps(payload, ensure_ascii=False, sort_keys=True)``
    but additionally:

    - escapes supplementary-plane Unicode code points (U+10000–U+10FFFF,
      e.g. emoji in ``title`` fields) as JSON ``\\uXXXX\\uYYYY`` surrogate
      pairs via ``_SUPPLEMENTARY_UNICODE_RE``.  SurrealDB's HTTP ``/sql``
      endpoint returns HTTP 400 for statements containing literal 4-byte
      UTF-8 codepoints; BMP chars (U+0000–U+FFFF), including the ⟨⟩ bracket
      chars used for record refs, are intentionally left as literal Unicode;
    - converts allowlisted ISO-8601-Z datetime string values to SurrealQL
      datetime literals (``d"..."``) via ``_SURQL_DATETIME_RE``; and
    - unquotes allowlisted record-ref string values (e.g.
      ``"doc_page:\u27e8id\u27e9"``) so SurrealDB accepts them as
      ``TYPE record`` values via ``_SURQL_RECORD_REF_RE``.

    ``ensure_ascii=False`` is required so that SurrealDB bracket chars
    U+27E8/U+27E9 (⟨⟩) appear as literal Unicode in the JSON output,
    enabling the ``_SURQL_RECORD_REF_RE`` pattern to match them.
    """
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    raw = _SUPPLEMENTARY_UNICODE_RE.sub(_escape_supplementary, raw)
    raw = _SURQL_DATETIME_RE.sub(r'"\1": d"\2"', raw)
    raw = _SURQL_RECORD_REF_RE.sub(r'"\1": \2', raw)
    return raw


EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_INPUT_NOT_FOUND = 3
EXIT_UNSUPPORTED_FORMAT = 4
EXIT_WRITE_DENIED = 5
EXIT_INTERNAL = 6


class ContextImporterError(Exception):
    """Base error for the context_importer scaffold."""

    code: str = "CONTEXT_IMPORTER_ERROR"
    exit_code: int = EXIT_INTERNAL

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WriteDeniedError(ContextImporterError):
    """Raised when a write or apply path is attempted in the scaffold."""

    code = "WRITE_DENIED"
    exit_code = EXIT_WRITE_DENIED


class UnsupportedFormatError(ContextImporterError):
    """Raised when an unsupported --format value is supplied."""

    code = "UNSUPPORTED_FORMAT"
    exit_code = EXIT_UNSUPPORTED_FORMAT


class InputNotFoundError(ContextImporterError):
    """Raised when an explicitly supplied input/config path does not exist."""

    code = "INPUT_NOT_FOUND"
    exit_code = EXIT_INPUT_NOT_FOUND


class ConfigValidationError(ContextImporterError):
    """Raised when the local importer config is invalid or unsafe."""

    code = "CONFIG_VALIDATION_ERROR"
    exit_code = EXIT_VALIDATION_ERROR


class ExistingRecordsValidationError(ContextImporterError):
    """Raised when the read-only existing-records fixture is invalid."""

    code = "EXISTING_RECORDS_VALIDATION_ERROR"
    exit_code = EXIT_VALIDATION_ERROR


class AuditReportError(ContextImporterError):
    """Raised when an audit report cannot be generated safely."""

    code = "AUDIT_REPORT_ERROR"
    exit_code = EXIT_VALIDATION_ERROR


@dataclass(frozen=True)
class JsonlValidationFinding:
    severity: str
    code: str
    message: str
    artifact: str | None = None
    line: int | None = None
    source_path: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.artifact is not None:
            payload["artifact"] = self.artifact
        if self.line is not None:
            payload["line"] = self.line
        if self.source_path is not None:
            payload["source_path"] = self.source_path
        return payload


@dataclass(frozen=True)
class JsonlValidationReport:
    input_dir: Path
    run_id: str | None
    records: dict[str, list[dict[str, Any]]]
    findings: tuple[JsonlValidationFinding, ...]

    @property
    def blocking_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "blocking")

    @property
    def warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "info")

    @property
    def status(self) -> str:
        return "blocked" if self.blocking_count else "passed"

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "command": "validate-jsonl",
            "status": self.status,
            "dry_run": True,
            "apply_requested": False,
            "surrealdb_connection": "disabled",
            "implemented": True,
            "input_dir": str(self.input_dir),
            "run_id": self.run_id,
            "artifact_counts": {
                artifact: len(items) for artifact, items in sorted(self.records.items())
            },
            "validation": {
                "blocking_count": self.blocking_count,
                "warning_count": self.warning_count,
                "info_count": self.info_count,
                "finding_count": len(self.findings),
            },
            "findings": [finding.to_payload() for finding in self.findings],
        }


@dataclass(frozen=True)
class ImportPlanAction:
    action: str
    table: str
    record_id: str
    artifact: str
    source_ref: str | None
    depends_on: tuple[str, ...]
    reason: str
    payload_hash: str
    # Verbatim JSONL record content minus ``__line``; populated for ``create``
    # actions and threaded to the apply pipeline so the adapter writes actual
    # domain fields rather than import metadata. Not included in to_payload()
    # to avoid leaking record content into plan/dry-run reports.
    payload: Mapping[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "table": self.table,
            "record_id": self.record_id,
            "artifact": self.artifact,
            "source_ref": self.source_ref,
            "depends_on": list(self.depends_on),
            "reason": self.reason,
            "payload_hash": self.payload_hash,
        }


@dataclass(frozen=True)
class ImportPlanWarning:
    code: str
    message: str
    artifact: str | None = None
    source_ref: str | None = None
    severity: str = "warning"

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.artifact is not None:
            payload["artifact"] = self.artifact
        if self.source_ref is not None:
            payload["source_ref"] = self.source_ref
        return payload


@dataclass(frozen=True)
class ImportPlan:
    schema_version: str
    run_id: str | None
    input_dir: Path
    status: str
    actions: tuple[ImportPlanAction, ...]
    warnings: tuple[ImportPlanWarning, ...]
    table_counts: dict[str, int]
    action_counts: dict[str, int]
    has_blocking_validation_findings: bool
    validation_report: JsonlValidationReport
    import_order: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        validation_summary = {
            "blocking_count": self.validation_report.blocking_count,
            "warning_count": self.validation_report.warning_count,
            "info_count": self.validation_report.info_count,
            "finding_count": len(self.validation_report.findings),
        }
        return {
            "schema_version": self.schema_version,
            "command": "plan",
            "run_id": self.run_id,
            "input_dir": str(self.input_dir),
            "status": self.status,
            "dry_run": True,
            "apply_requested": False,
            "surrealdb_connection": "disabled",
            "implemented": True,
            "actions": [action.to_payload() for action in self.actions],
            "warnings": [warning.to_payload() for warning in self.warnings],
            "counts": {
                "actions": len(self.actions),
                "warnings": len(self.warnings),
                "tables": len(self.table_counts),
                "validation_findings": len(self.validation_report.findings),
            },
            "table_counts": dict(sorted(self.table_counts.items())),
            "action_counts": dict(sorted(self.action_counts.items())),
            "has_blocking_validation_findings": self.has_blocking_validation_findings,
            "validation_summary": validation_summary,
            "import_order": list(self.import_order),
        }


@dataclass(frozen=True)
class ExistingRecord:
    table: str
    record_id: str
    payload_hash: str | None
    schema_version: str | None
    # Optional verbatim copy of the prior record payload (control keys
    # like ``__line``/``payload_hash``/``schema_version``/``table``/
    # ``record_id``/``id`` already stripped). Carried forward so the
    # tombstone apply path can preserve original record fields per
    # context-importer-cli-contract.md §5.3 ("Der Adapter ueberschreibt
    # das Original-Record nicht; es bleibt erhalten und bekommt die
    # Tombstone-Felder dazu."). Never serialized into reports to avoid
    # payload leakage; consumed only by the apply pipeline.
    payload: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReadOnlyExistingRecords:
    """Mockable read-only boundary for records already present in SurrealDB."""

    records: tuple[ExistingRecord, ...]
    source: str

    def by_record_id(self) -> dict[str, ExistingRecord]:
        records_by_id: dict[str, ExistingRecord] = {}
        for record in self.records:
            if record.record_id in records_by_id:
                raise ExistingRecordsValidationError(
                    "duplicate existing record_id in existing records fixture"
                )
            records_by_id[record.record_id] = record
        return records_by_id


@dataclass(frozen=True)
class ReconcileAction:
    action: str
    table: str
    record_id: str
    source_ref: str | None
    reason: str
    payload_hash: str | None
    existing_payload_hash: str | None
    # Optional verbatim copy of the prior record payload, only populated
    # for ``tombstone_candidate`` actions whose existing record carried a
    # ``payload`` object in the existing-records fixture. Plumbed to the
    # apply pipeline so tombstones can preserve original record fields.
    # Intentionally **not** included in :meth:`to_payload` to avoid
    # leaking record contents into dry-run/apply reports.
    existing_payload: Mapping[str, Any] | None = None
    # Verbatim JSONL domain payload for ``create``/``update_candidate`` actions;
    # threaded from ``ImportPlanAction.payload`` so the adapter receives actual
    # record fields rather than import metadata. Not in to_payload().
    payload: Mapping[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "table": self.table,
            "record_id": self.record_id,
            "source_ref": self.source_ref,
            "reason": self.reason,
            "payload_hash": self.payload_hash,
            "existing_payload_hash": self.existing_payload_hash,
        }


@dataclass(frozen=True)
class ReconcileFinding:
    severity: str
    code: str
    message: str
    table: str | None = None
    record_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.table is not None:
            payload["table"] = self.table
        if self.record_id is not None:
            payload["record_id"] = self.record_id
        return payload


@dataclass(frozen=True)
class ReconcileReport:
    schema_version: str
    run_id: str | None
    input_dir: Path
    status: str
    existing_records_source: str
    actions: tuple[ReconcileAction, ...]
    findings: tuple[ReconcileFinding, ...]
    warnings: tuple[ImportPlanWarning, ...]
    plan: ImportPlan

    @property
    def blocking_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == "blocking")

    @property
    def warning_count(self) -> int:
        finding_warnings = sum(
            1 for finding in self.findings if finding.severity == "warning"
        )
        plan_warnings = sum(
            1 for warning in self.warnings if warning.severity == "warning"
        )
        return finding_warnings + plan_warnings

    def action_counts(self) -> dict[str, int]:
        counts = {
            "creates": 0,
            "skips": 0,
            "update_candidates": 0,
            "tombstone_candidates": 0,
            "blocking": self.blocking_count,
            "warnings": self.warning_count,
        }
        for action in self.actions:
            if action.action == "create":
                counts["creates"] += 1
            elif action.action == "skip":
                counts["skips"] += 1
            elif action.action == "update_candidate":
                counts["update_candidates"] += 1
            elif action.action == "tombstone_candidate":
                counts["tombstone_candidates"] += 1
        return counts

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "command": "dry-run",
            "run_id": self.run_id,
            "input_dir": str(self.input_dir),
            "status": self.status,
            "dry_run": True,
            "apply_requested": False,
            "surrealdb_connection": "read-only-fixture"
            if self.existing_records_source != "empty"
            else "disabled",
            "surrealdb_writes": "disabled",
            "implemented": True,
            "existing_records_source": self.existing_records_source,
            "actions": [action.to_payload() for action in self.actions],
            "findings": [finding.to_payload() for finding in self.findings],
            "warnings": [warning.to_payload() for warning in self.warnings],
            "counts": self.action_counts(),
            "plan_summary": {
                "status": self.plan.status,
                "actions": len(self.plan.actions),
                "warnings": len(self.plan.warnings),
                "has_blocking_validation_findings": self.plan.has_blocking_validation_findings,
            },
        }


@dataclass(frozen=True)
class ContextImportConfig:
    """Validated local config for the context importer."""

    path: Path
    schema_version: str
    surreal_url: str
    namespace: str
    database: str
    auth_mode: str
    timeout: int
    allow_apply_default: bool
    allowed_tables: tuple[str, ...]
    forbidden_tables: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "schema_version": self.schema_version,
            "surreal_url": self.surreal_url,
            "namespace": self.namespace,
            "database": self.database,
            "auth_mode": self.auth_mode,
            "timeout": self.timeout,
            "allow_apply_default": self.allow_apply_default,
            "allowed_tables": list(self.allowed_tables),
            "forbidden_tables": list(self.forbidden_tables),
        }


# ---------------------------------------------------------------------------
# Apply pipeline (#2073/#2074)
#
# The apply pipeline is a strictly gated local-dev path. The default
# adapter is the in-memory :class:`InMemoryContextApplyAdapter`; it
# never opens a network socket. A real SurrealDB adapter is OUT-OF-SCOPE
# in this slice (``REAL_SURREALDB_ADAPTER_AVAILABLE == False``).
# ---------------------------------------------------------------------------


class ApplyGateError(ContextImporterError):
    """Raised when the local-dev apply gate is not satisfied."""

    code = "APPLY_GATE_DENIED"
    exit_code = EXIT_WRITE_DENIED


class ApplyAdapterError(ContextImporterError):
    """Raised by an adapter to report a per-operation failure.

    Caught by the executor and surfaced as a ``failed`` apply result;
    it does not propagate out of :func:`execute_context_apply`.
    """

    code = "APPLY_ADAPTER_ERROR"
    exit_code = EXIT_INTERNAL


@dataclass(frozen=True)
class ContextApplyOperation:
    """Single normalized apply operation derived from a reconcile action."""

    op: str
    table: str
    record_id: str
    payload_hash: str | None
    existing_payload_hash: str | None
    source_ref: str | None
    reason: str
    note: str | None = None
    # Optional verbatim prior-record payload (control keys stripped),
    # only populated for tombstone operations whose source ``ExistingRecord``
    # carried a ``payload`` object. Consumed by ``_build_payload_for_op`` so
    # tombstones preserve original record fields under the tombstone
    # metadata. Intentionally **not** included in :meth:`to_payload` to
    # avoid leaking record contents into apply reports.
    existing_payload: Mapping[str, Any] | None = None
    # Verbatim JSONL domain payload for create/update operations; threaded
    # from ReconcileAction.payload so _build_payload_for_op writes actual
    # record fields to the adapter. Not included in to_payload().
    payload: Mapping[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "table": self.table,
            "record_id": self.record_id,
            "payload_hash": self.payload_hash,
            "existing_payload_hash": self.existing_payload_hash,
            "source_ref": self.source_ref,
            "reason": self.reason,
            "note": self.note,
        }


@dataclass(frozen=True)
class ContextApplyResult:
    """Outcome of a single :class:`ContextApplyOperation`."""

    op: str
    table: str
    record_id: str
    status: str  # one of: applied | skipped | failed
    detail: str | None = None
    tombstoned_at: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "table": self.table,
            "record_id": self.record_id,
            "status": self.status,
            "detail": self.detail,
            "tombstoned_at": self.tombstoned_at,
        }


@dataclass(frozen=True)
class ContextApplyReport:
    """Deterministic, render-friendly apply report."""

    schema_version: str
    run_id: str
    input_dir: Path
    apply_mode: str
    adapter: str
    config_path: Path
    surreal_url: str
    namespace: str
    database: str
    operations: tuple[ContextApplyOperation, ...]
    results: tuple[ContextApplyResult, ...]
    blocking_findings_present: bool
    blocking_finding_codes: tuple[str, ...]
    apply_executed: bool
    status: str
    note: str

    def counts(self) -> dict[str, int]:
        c = {
            "creates": 0,
            "updates": 0,
            "tombstones": 0,
            "applied": 0,
            "skipped": 0,
            "failed": 0,
            "blocked": 0,
        }
        for op in self.operations:
            if op.op == APPLY_OP_CREATE:
                c["creates"] += 1
            elif op.op == APPLY_OP_UPDATE:
                c["updates"] += 1
            elif op.op == APPLY_OP_TOMBSTONE:
                c["tombstones"] += 1
        for res in self.results:
            if res.status == "applied":
                c["applied"] += 1
            elif res.status == "skipped":
                c["skipped"] += 1
            elif res.status == "failed":
                c["failed"] += 1
            elif res.status == "blocked":
                c["blocked"] += 1
        return c

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "command": "apply",
            "run_id": self.run_id,
            "input_dir": str(self.input_dir),
            "apply_mode": self.apply_mode,
            "adapter": self.adapter,
            "config_path": str(self.config_path),
            "surreal_url": self.surreal_url,
            "namespace": self.namespace,
            "database": self.database,
            "dry_run": False,
            "apply_requested": True,
            "apply_executed": self.apply_executed,
            "surrealdb_connection": (
                "local-http-api"
                if self.adapter == ADAPTER_KIND_SURREALDB_LOCAL
                else "in-memory-no-network"
            ),
            "surrealdb_writes": (
                "local-db-writes"
                if self.adapter == ADAPTER_KIND_SURREALDB_LOCAL
                else "in-memory-only"
            ),
            "real_surrealdb_adapter_available": REAL_SURREALDB_ADAPTER_AVAILABLE,
            "implemented": True,
            "status": self.status,
            "note": self.note,
            "operations": [op.to_payload() for op in self.operations],
            "results": [res.to_payload() for res in self.results],
            "counts": self.counts(),
            "blocking_findings_present": self.blocking_findings_present,
            "blocking_finding_codes": list(self.blocking_finding_codes),
        }


@dataclass(frozen=True)
class ContextImportAuditReport:
    """Payload-safe audit envelope for plan, dry-run, and apply runs."""

    run_id: str | None
    input_dir: Path
    git_commit: str
    namespace: str | None
    database: str | None
    mode: str
    artifact_counts: Mapping[str, int]
    planned_counts: Mapping[str, int]
    actual_counts: Mapping[str, int]
    warnings: tuple[dict[str, Any], ...]
    blocking_findings: tuple[dict[str, Any], ...]
    duration_ms: int
    generated_at: str
    operator_tool_version: str
    status: str
    report_source: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "command": "audit",
            "status": self.status,
            "run_id": self.run_id,
            "input_dir": str(self.input_dir),
            "git_commit": self.git_commit,
            "namespace": self.namespace,
            "database": self.database,
            "mode": self.mode,
            "artifact_counts": dict(sorted(self.artifact_counts.items())),
            "planned_counts": dict(sorted(self.planned_counts.items())),
            "actual_counts": dict(sorted(self.actual_counts.items())),
            "warnings": list(self.warnings),
            "blocking_findings": list(self.blocking_findings),
            "duration_ms": self.duration_ms,
            "generated_at": self.generated_at,
            "operator_tool_version": self.operator_tool_version,
            "report_source": self.report_source,
            "payload_policy": "metadata-only; no record payloads serialized",
        }


@dataclass(frozen=True)
class _FixedAuditClock:
    value: datetime

    def now(self) -> datetime:
        return self.value


class ContextApplyAdapter(Protocol):
    """Mockable apply boundary.

    Implementations must perform no network I/O unless the caller
    explicitly opts in. The default :class:`InMemoryContextApplyAdapter`
    keeps everything in-process.
    """

    kind: str

    def apply_create(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None: pass

    def apply_update(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None: pass

    def apply_tombstone(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None: pass


class InMemoryContextApplyAdapter:
    """Default in-memory, no-network apply adapter for tests and local dev.

    Records every operation in :attr:`operations` so tests can assert
    against the exact sequence. Has no ``delete`` API by design (#2074).
    """

    kind: str = ADAPTER_KIND_IN_MEMORY

    def __init__(self) -> None:
        self.operations: list[tuple[str, str, str, dict[str, Any]]] = []
        self.records: dict[str, dict[str, Any]] = {}

    # No `delete` method exists. This is intentional and is asserted by
    # tests in tests/unit/surrealdb/test_context_import_tombstones.py.

    def apply_create(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        self.operations.append((APPLY_OP_CREATE, table, record_id, dict(payload)))
        self.records[record_id] = dict(payload)

    def apply_update(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        self.operations.append((APPLY_OP_UPDATE, table, record_id, dict(payload)))
        self.records[record_id] = dict(payload)

    def apply_tombstone(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        missing = TOMBSTONE_REQUIRED_FIELDS - set(payload.keys())
        if missing:
            raise ApplyAdapterError(
                f"tombstone payload missing required fields: {sorted(missing)}"
            )
        if payload.get(TOMBSTONE_FIELD_FLAG) is not True:
            raise ApplyAdapterError(
                f"tombstone payload must set {TOMBSTONE_FIELD_FLAG!r} to True"
            )
        self.operations.append((APPLY_OP_TOMBSTONE, table, record_id, dict(payload)))
        # Tombstone updates the record in place; no hard delete.
        existing = self.records.get(record_id, {})
        existing.update(payload)
        self.records[record_id] = existing


def _isoformat_utc(dt: datetime) -> str:
    """Serialize a datetime to ISO8601 UTC with a trailing ``Z``.

    Accepts naive datetimes (treated as UTC) or aware datetimes (converted
    to UTC). Returns deterministic output for a fixed input.
    """

    if dt.tzinfo is None:
        aware = dt.replace(tzinfo=timezone.utc)
    else:
        aware = dt.astimezone(timezone.utc)
    # Drop tzinfo in formatting and append explicit Z to keep the contract
    # stable across Python versions.
    return aware.replace(tzinfo=None).isoformat() + "Z"


class SurrealDBLocalContextApplyAdapter:
    """Real local SurrealDB apply adapter — writes via HTTP REST API.

    Connects only to localhost/127.0.0.1/::1. Rejects remote targets
    fail-closed. Credentials are never logged.

    Issue: #2458
    """

    kind: str = ADAPTER_KIND_SURREALDB_LOCAL

    def __init__(
        self,
        surreal_url: str,
        namespace: str,
        database: str,
        user: str | None,
        password: str | None,
        timeout: int = 10,
    ) -> None:
        _validate_local_dev_url(surreal_url)  # defense-in-depth
        self._url = surreal_url.rstrip("/")
        self._namespace = namespace
        self._database = database
        self._user = user
        self._password = password
        self._timeout = timeout

    def _sql_request(self, sql: str) -> None:
        """POST SQL to /sql endpoint. Raises ApplyAdapterError on failure."""
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "surreal-ns": self._namespace,
            "surreal-db": self._database,
        }
        if self._user is not None and self._password is not None:
            token = base64.b64encode(
                f"{self._user}:{self._password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {token}"

        data = sql.encode("utf-8")
        req = urllib.request.Request(
            f"{self._url}/sql", data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = exc.read()
        except urllib.error.URLError as exc:
            raise ApplyAdapterError(
                f"surrealdb-local connection failed: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise ApplyAdapterError(
                f"surrealdb-local connection error: {type(exc).__name__}"
            ) from exc

        if status not in (200, 204):
            raise ApplyAdapterError(
                f"surrealdb-local HTTP {status} — check container is running"
            )

        try:
            raw = body.decode("utf-8", errors="replace")
        except Exception as exc:
            raise ApplyAdapterError(
                f"surrealdb-local response not decodable: {type(exc).__name__}"
            ) from exc

        if not raw.strip():
            raise ApplyAdapterError(
                "surrealdb-local returned empty response body"
            )

        try:
            results = json.loads(raw)
        except json.JSONDecodeError as exc:
            truncated = raw[:200]
            raise ApplyAdapterError(
                f"surrealdb-local response not valid JSON: {truncated!r}"
            ) from exc

        if not isinstance(results, list):
            raise ApplyAdapterError(
                f"surrealdb-local response not a JSON array: {type(results).__name__}"
            )

        for item in results:
            if not isinstance(item, dict):
                continue
            item_status = item.get("status", "").upper()
            if item_status != "OK":
                detail = str(item.get("result", "") or item.get("detail", ""))[:200]
                raise ApplyAdapterError(
                    f"surrealdb-local statement error ({item_status}): {detail}"
                )

    @staticmethod
    def _surql_record_id(table: str, record_id: str) -> str:
        """Escape record_id using SurrealDB \u27e8\u27e9 notation for arbitrary string IDs."""
        # U+27E8 = \u27e8, U+27E9 = \u27e9; escape closing bracket if present in the ID.
        escaped = record_id.replace("\u27e9", "\\u27e9")
        return f"{table}:\u27e8{escaped}\u27e9"

    def apply_create(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        rid = self._surql_record_id(table, record_id)
        db_payload = _remap_record_refs_for_db_payload(table, payload)
        payload_json = _payload_to_surql_content(db_payload)
        sql = f"UPSERT {rid} CONTENT {payload_json};"
        self._sql_request(sql)

    def apply_update(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        rid = self._surql_record_id(table, record_id)
        db_payload = _remap_record_refs_for_db_payload(table, payload)
        payload_json = _payload_to_surql_content(db_payload)
        sql = f"UPSERT {rid} CONTENT {payload_json};"
        self._sql_request(sql)

    def apply_tombstone(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        missing = TOMBSTONE_REQUIRED_FIELDS - set(payload.keys())
        if missing:
            raise ApplyAdapterError(
                f"tombstone payload missing required fields: {sorted(missing)}"
            )
        if payload.get(TOMBSTONE_FIELD_FLAG) is not True:
            raise ApplyAdapterError(
                f"tombstone payload must set {TOMBSTONE_FIELD_FLAG!r} to True"
            )
        # Strip tombstone meta-fields and pipeline meta-fields before writing.
        # None of these are declared in context_intelligence_v0.surql; SCHEMAFULL
        # tables only persist declared fields, so explicitly excluding them makes
        # the DB write deterministic and avoids silent field-rejection surprises.
        _meta = TOMBSTONE_REQUIRED_FIELDS | frozenset(
            {"table", "record_id", "run_id", "payload_hash"}
        )
        domain_payload = {k: v for k, v in payload.items() if k not in _meta}
        rid = self._surql_record_id(table, record_id)
        payload_json = _payload_to_surql_content(domain_payload)
        sql = f"UPSERT {rid} CONTENT {payload_json};"
        self._sql_request(sql)


def _load_surrealdb_credentials(
    config: "ContextImportConfig",
    secrets_path: Path | None,
) -> tuple[str | None, str | None]:
    """Load SurrealDB credentials for the local apply adapter.

    Returns (user, password) or (None, None) for auth_mode 'none'.
    Credentials are never logged.
    """
    auth_mode = config.auth_mode
    if auth_mode == "none":
        return None, None

    if auth_mode == "root":
        if secrets_path is not None:
            env_file = secrets_path / "SURREALDB_ENV"
        else:
            env_root = os.environ.get(
                "SECRETS_PATH",
                str(Path.home() / "Documents" / ".secrets" / ".cdb"),
            )
            env_file = Path(env_root) / "SURREALDB_ENV"

        if not env_file.exists():
            raise ApplyGateError(
                f"SURREALDB_ENV not found at {env_file}; "
                "required for auth_mode: root — "
                "create from infrastructure/config/surrealdb/SURREALDB_ENV.example"
            )

        user: str | None = None
        password: str | None = None
        with env_file.open() as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("SURREAL_USER="):
                    user = stripped[len("SURREAL_USER="):]
                elif stripped.startswith("SURREAL_PASS="):
                    password = stripped[len("SURREAL_PASS="):]

        if not user:
            raise ApplyGateError("SURREALDB_ENV missing field SURREAL_USER")
        if not password:
            raise ApplyGateError("SURREALDB_ENV missing field SURREAL_PASS")
        return user, password

    raise ApplyGateError(
        f"unsupported auth_mode: {auth_mode!r}; supported: none, root"
    )


def _git_commit_value(value: str | None) -> str:
    if value is None or not value.strip():
        return "unknown"
    return value.strip()


def _duration_ms_value(value: int | None) -> int:
    if value is None:
        return 0
    if value < 0:
        raise AuditReportError("audit duration_ms must be non-negative")
    return value


def _parse_audit_generated_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise AuditReportError("audit generated_at must be a non-empty ISO8601 value")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AuditReportError(
            f"audit generated_at must be ISO8601-compatible: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_warning_payload(warning: ImportPlanWarning) -> dict[str, Any]:
    return warning.to_payload()


def _safe_validation_finding_payload(finding: JsonlValidationFinding) -> dict[str, Any]:
    return finding.to_payload()


def _safe_reconcile_finding_payload(finding: ReconcileFinding) -> dict[str, Any]:
    return finding.to_payload()


def _planned_counts_from_reconcile(report: ReconcileReport) -> dict[str, int]:
    counts = report.action_counts()
    return {
        "creates": counts["creates"],
        "updates": counts["update_candidates"],
        "skips": counts["skips"],
        "tombstones": counts["tombstone_candidates"],
    }


def _actual_counts_from_apply(report: ContextApplyReport) -> dict[str, int]:
    counts = {"creates": 0, "updates": 0, "skips": 0, "tombstones": 0}
    for result in report.results:
        if result.status != "applied":
            continue
        if result.op == APPLY_OP_CREATE:
            counts["creates"] += 1
        elif result.op == APPLY_OP_UPDATE:
            counts["updates"] += 1
        elif result.op == APPLY_OP_TOMBSTONE:
            counts["tombstones"] += 1
    return counts


def _audit_status(blocking_findings: tuple[dict[str, Any], ...], status: str) -> str:
    if blocking_findings:
        return "blocked"
    return status


def build_audit_report(
    *,
    mode: str,
    input_dir: Path,
    run_id: str | None,
    git_commit: str | None = None,
    namespace: str | None = None,
    database: str | None = None,
    clock: ClockProvider | None = None,
    duration_ms: int | None = None,
    plan: ImportPlan | None = None,
    reconcile_report: ReconcileReport | None = None,
    apply_report: ContextApplyReport | None = None,
) -> ContextImportAuditReport:
    """Build a deterministic, payload-safe audit report.

    Callers inject ``clock``, ``duration_ms`` and ``git_commit`` in tests or
    evidence-producing runs. The report deliberately serializes only counts,
    finding metadata, IDs and hashes already present in command summaries; it
    never serializes record payloads from JSONL or existing-record fixtures.
    """

    if mode not in SUPPORTED_AUDIT_MODES:
        raise AuditReportError(
            f"unsupported audit mode: {mode!r}; allowed: {sorted(SUPPORTED_AUDIT_MODES)}"
        )
    if mode == AUDIT_MODE_PLAN and plan is None:
        raise AuditReportError("plan audit requires an ImportPlan")
    if mode == AUDIT_MODE_DRY_RUN and reconcile_report is None:
        raise AuditReportError("dry-run audit requires a ReconcileReport")
    if mode == AUDIT_MODE_APPLY and (reconcile_report is None or apply_report is None):
        raise AuditReportError("apply audit requires ReconcileReport and ContextApplyReport")

    used_clock: ClockProvider = clock or SystemClock()
    generated_at = _isoformat_utc(used_clock.now())
    duration = _duration_ms_value(duration_ms)

    source_plan = plan or (reconcile_report.plan if reconcile_report is not None else None)
    artifact_counts = (
        {
            artifact: len(items)
            for artifact, items in sorted(source_plan.validation_report.records.items())
        }
        if source_plan is not None
        else {}
    )

    if mode == AUDIT_MODE_PLAN:
        assert plan is not None  # narrowed by guard above
        planned_counts = {
            "creates": plan.action_counts.get("create", 0),
            "updates": plan.action_counts.get("update", 0),
            "skips": plan.action_counts.get("skip", 0),
            "tombstones": plan.action_counts.get("tombstone", 0),
        }
        actual_counts = {"creates": 0, "updates": 0, "skips": 0, "tombstones": 0}
        warnings = tuple(_safe_warning_payload(warning) for warning in plan.warnings)
        blocking_findings = tuple(
            _safe_validation_finding_payload(finding)
            for finding in plan.validation_report.findings
            if finding.severity == "blocking"
        )
        status = _audit_status(blocking_findings, plan.status)
        report_source = "import-plan"
    elif mode == AUDIT_MODE_DRY_RUN:
        assert reconcile_report is not None
        planned_counts = _planned_counts_from_reconcile(reconcile_report)
        actual_counts = {"creates": 0, "updates": 0, "skips": 0, "tombstones": 0}
        warnings = tuple(
            _safe_warning_payload(warning) for warning in reconcile_report.warnings
        ) + tuple(
            _safe_reconcile_finding_payload(finding)
            for finding in reconcile_report.findings
            if finding.severity == "warning"
        )
        blocking_findings = tuple(
            _safe_reconcile_finding_payload(finding)
            for finding in reconcile_report.findings
            if finding.severity == "blocking"
        )
        status = _audit_status(blocking_findings, reconcile_report.status)
        report_source = "dry-run-reconcile"
    else:
        assert reconcile_report is not None and apply_report is not None
        planned_counts = _planned_counts_from_reconcile(reconcile_report)
        actual_counts = _actual_counts_from_apply(apply_report)
        actual_counts["skips"] = reconcile_report.action_counts()["skips"]
        warnings = tuple(
            _safe_warning_payload(warning) for warning in reconcile_report.warnings
        ) + tuple(
            _safe_reconcile_finding_payload(finding)
            for finding in reconcile_report.findings
            if finding.severity == "warning"
        )
        blocking_findings = tuple(
            _safe_reconcile_finding_payload(finding)
            for finding in reconcile_report.findings
            if finding.severity == "blocking"
        )
        blocking_findings += tuple(
            {
                "severity": "blocking",
                "code": code,
                "message": "apply blocked by reconcile finding",
            }
            for code in apply_report.blocking_finding_codes
        )
        status = _audit_status(blocking_findings, apply_report.status)
        report_source = "local-dev-apply"

    return ContextImportAuditReport(
        run_id=run_id,
        input_dir=input_dir,
        git_commit=_git_commit_value(git_commit),
        namespace=namespace,
        database=database,
        mode=mode,
        artifact_counts=artifact_counts,
        planned_counts=planned_counts,
        actual_counts=actual_counts,
        warnings=warnings,
        blocking_findings=blocking_findings,
        duration_ms=duration,
        generated_at=generated_at,
        operator_tool_version=TOOL_VERSION,
        status=status,
        report_source=report_source,
    )


def _validate_local_dev_url(surreal_url: str) -> None:
    """Reject any non-local-dev SurrealDB URL when the local-dev gate is active."""

    parsed = urlparse(surreal_url)
    host = (parsed.hostname or "").lower()
    if host not in LOCAL_DEV_ALLOWED_HOSTS:
        raise ApplyGateError(
            "local-dev apply requires a localhost surreal_url; "
            f"got host={host!r}, allowed={sorted(LOCAL_DEV_ALLOWED_HOSTS)}"
        )


def _validate_apply_table_policy(
    table: str, *, allowed: frozenset[str], forbidden: frozenset[str]
) -> None:
    """Fail-closed table policy gate for apply.

    Effective policy:
        allow_effective  = ALLOWED_CONTEXT_IMPORT_TABLES ∩ allowed
        forbid_effective = FORBIDDEN_CONTEXT_IMPORT_TABLES ∪ forbidden

    Forbidden trumps allowed. ``allowed`` (operator config
    ``allowed_tables``) is strictly restrictive: a table that the
    operator removed from ``config.allowed_tables`` is blocked even
    when it is in the global allow-list. There is no fallback to the
    global allow-list when the configured allow-list is narrower.

    Errors only carry the table name and a reason; payloads, hashes,
    and other record content are never included.
    """

    if table in forbidden or table in FORBIDDEN_CONTEXT_IMPORT_TABLES:
        raise ApplyGateError(
            f"apply target table is forbidden by table policy: {table!r}"
        )
    if table not in ALLOWED_CONTEXT_IMPORT_TABLES:
        raise ApplyGateError(
            f"apply target table is not in the global allow-list: {table!r}"
        )
    if table not in allowed:
        raise ApplyGateError(
            f"apply target table is not in the configured allow-list: {table!r}"
        )


def _build_payload_for_op(
    op: ContextApplyOperation,
    *,
    run_id: str,
    clock: ClockProvider,
    last_seen_run_id: str | None,
) -> tuple[dict[str, Any], str | None]:
    """Build the adapter payload for a single operation.

    Returns ``(payload, tombstoned_at_iso)``. ``tombstoned_at_iso`` is
    only set for tombstone operations.
    """

    if op.op == APPLY_OP_TOMBSTONE:
        ts_iso = _isoformat_utc(clock.now())
        # Start from the prior record payload (when available) so the
        # tombstone preserves all original record fields, then overlay
        # the tombstone metadata + identity fields. Per
        # context-importer-cli-contract.md §5.3 the adapter must keep
        # the original record and only add tombstone fields. When no
        # prior payload is available (e.g. hash-only existing-records
        # entry, or no --existing-records fixture), the payload remains
        # the deterministic minimal shape. Tombstone metadata and
        # identity keys always win over any colliding prior field.
        payload: dict[str, Any] = {}
        if op.existing_payload is not None:
            payload.update(copy.deepcopy(dict(op.existing_payload)))
        payload.update(
            {
                TOMBSTONE_FIELD_FLAG: True,
                TOMBSTONE_FIELD_AT: ts_iso,
                TOMBSTONE_FIELD_REASON: op.reason
                or TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT,
                TOMBSTONE_FIELD_LAST_SEEN_RUN_ID: last_seen_run_id,
                TOMBSTONE_FIELD_SUPERSEDED_BY: None,
                "table": op.table,
                "record_id": op.record_id,
                "run_id": run_id,
                "payload_hash": op.existing_payload_hash,
            }
        )
        return payload, ts_iso

    # For create/update: write the actual JSONL domain payload to the adapter.
    # Envelope fields (schema_version, run_id, sensitivity, __line) are stripped
    # at plan-build time via _JSONL_INTERNAL_FIELDS; remaining fields are the
    # domain payload declared in the table schema.
    db_payload = dict(op.payload) if op.payload is not None else {}
    return db_payload, None


def _operations_from_reconcile(
    report: ReconcileReport,
) -> tuple[ContextApplyOperation, ...]:
    """Map reconcile actions to apply operations.

    ``skip`` actions are dropped (they would do nothing and we surface
    the count via the reconcile report counts already).
    """

    ops: list[ContextApplyOperation] = []
    # Track previously-tombstoned records (best-effort heuristic on
    # existing_payload_hash being equal to a sentinel later; for now
    # we surface re-emergence as a note when reason hints at it).
    for action in report.actions:
        if action.action == "create":
            ops.append(
                ContextApplyOperation(
                    op=APPLY_OP_CREATE,
                    table=action.table,
                    record_id=action.record_id,
                    payload_hash=action.payload_hash,
                    existing_payload_hash=action.existing_payload_hash,
                    source_ref=action.source_ref,
                    reason=action.reason,
                    payload=action.payload,
                )
            )
        elif action.action == "update_candidate":
            note: str | None = None
            if action.reason == "record_changed_after_tombstone":
                note = "re-emerged_after_tombstone"
            ops.append(
                ContextApplyOperation(
                    op=APPLY_OP_UPDATE,
                    table=action.table,
                    record_id=action.record_id,
                    payload_hash=action.payload_hash,
                    existing_payload_hash=action.existing_payload_hash,
                    source_ref=action.source_ref,
                    reason=action.reason,
                    note=note,
                    payload=action.payload,
                )
            )
        elif action.action == "tombstone_candidate":
            ops.append(
                ContextApplyOperation(
                    op=APPLY_OP_TOMBSTONE,
                    table=action.table,
                    record_id=action.record_id,
                    payload_hash=None,
                    existing_payload_hash=action.existing_payload_hash,
                    source_ref=action.source_ref,
                    reason=action.reason or TOMBSTONE_REASON_REMOVED_FROM_SNAPSHOT,
                    existing_payload=action.existing_payload,
                )
            )
        # ``skip`` is intentionally dropped; nothing to apply.
    # Deterministic ordering: by (op kind order, table, record_id).
    op_order = {APPLY_OP_CREATE: 0, APPLY_OP_UPDATE: 1, APPLY_OP_TOMBSTONE: 2}
    ops.sort(key=lambda o: (op_order[o.op], o.table, o.record_id))
    return tuple(ops)


def execute_context_apply(
    *,
    reconcile_report: ReconcileReport,
    config: ContextImportConfig,
    run_id: str,
    apply_mode: str,
    adapter: ContextApplyAdapter | None = None,
    clock: ClockProvider | None = None,
) -> ContextApplyReport:
    """Execute the gated local-dev apply pipeline.

    The gate caller is responsible for verifying CLI flags. This function
    additionally enforces:

    * apply mode is supported,
    * ``config.surreal_url`` host is local-dev,
    * ``config.allow_apply_default`` is False (defense-in-depth; the
      config loader already rejects ``True``),
    * no blocking reconcile findings,
    * each operation's table is in the allowed set and not forbidden.

    On any blocking-findings condition the function returns a report
    with ``apply_executed=False`` and ``status="blocked"``; no adapter
    method is called.
    """

    if apply_mode not in SUPPORTED_APPLY_MODES:
        raise ApplyGateError(
            f"unsupported apply_mode: {apply_mode!r}; "
            f"allowed: {sorted(SUPPORTED_APPLY_MODES)}"
        )
    if config.allow_apply_default:
        # Defense in depth; load_config already rejects True.
        raise ApplyGateError(
            "config.allow_apply_default must be False for context apply"
        )
    _validate_local_dev_url(config.surreal_url)

    used_adapter: ContextApplyAdapter = adapter or InMemoryContextApplyAdapter()
    used_clock: ClockProvider = clock or SystemClock()

    blocking_codes = tuple(
        sorted({f.code for f in reconcile_report.findings if f.severity == "blocking"})
    )
    if blocking_codes:
        return ContextApplyReport(
            schema_version=SCHEMA_VERSION,
            run_id=run_id,
            input_dir=reconcile_report.input_dir,
            apply_mode=apply_mode,
            adapter=used_adapter.kind,
            config_path=config.path,
            surreal_url=config.surreal_url,
            namespace=config.namespace,
            database=config.database,
            operations=(),
            results=(),
            blocking_findings_present=True,
            blocking_finding_codes=blocking_codes,
            apply_executed=False,
            status="blocked",
            note=(
                "apply blocked by reconcile blocking findings; "
                "no adapter operation was performed"
            ),
        )

    operations = _operations_from_reconcile(reconcile_report)

    allowed_tables = frozenset(config.allowed_tables)
    forbidden_tables = frozenset(config.forbidden_tables)

    results: list[ContextApplyResult] = []
    for op in operations:
        try:
            _validate_apply_table_policy(
                op.table, allowed=allowed_tables, forbidden=forbidden_tables
            )
        except ApplyGateError as exc:
            results.append(
                ContextApplyResult(
                    op=op.op,
                    table=op.table,
                    record_id=op.record_id,
                    status="blocked",
                    detail=exc.message,
                )
            )
            continue

        payload, tombstoned_at = _build_payload_for_op(
            op,
            run_id=run_id,
            clock=used_clock,
            last_seen_run_id=None,
        )
        try:
            if op.op == APPLY_OP_CREATE:
                used_adapter.apply_create(op.table, op.record_id, payload)
            elif op.op == APPLY_OP_UPDATE:
                used_adapter.apply_update(op.table, op.record_id, payload)
            elif op.op == APPLY_OP_TOMBSTONE:
                used_adapter.apply_tombstone(op.table, op.record_id, payload)
            else:  # pragma: no cover - defensive; enum-bounded above
                raise ApplyAdapterError(f"unknown apply op: {op.op!r}")
        except ApplyAdapterError as exc:
            results.append(
                ContextApplyResult(
                    op=op.op,
                    table=op.table,
                    record_id=op.record_id,
                    status="failed",
                    detail=exc.message,
                    tombstoned_at=tombstoned_at,
                )
            )
            continue
        except Exception as exc:  # noqa: BLE001 - adapter contract surface
            results.append(
                ContextApplyResult(
                    op=op.op,
                    table=op.table,
                    record_id=op.record_id,
                    status="failed",
                    detail=f"adapter raised: {exc.__class__.__name__}: {exc}",
                    tombstoned_at=tombstoned_at,
                )
            )
            continue

        results.append(
            ContextApplyResult(
                op=op.op,
                table=op.table,
                record_id=op.record_id,
                status="applied",
                detail=op.note,
                tombstoned_at=tombstoned_at,
            )
        )

    any_failed = any(r.status == "failed" for r in results)
    any_blocked = any(r.status == "blocked" for r in results)
    if any_failed or any_blocked:
        status = "partial"
    elif not operations:
        status = "noop"
    else:
        status = "applied"

    return ContextApplyReport(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        input_dir=reconcile_report.input_dir,
        apply_mode=apply_mode,
        adapter=used_adapter.kind,
        config_path=config.path,
        surreal_url=config.surreal_url,
        namespace=config.namespace,
        database=config.database,
        operations=operations,
        results=tuple(results),
        blocking_findings_present=False,
        blocking_finding_codes=(),
        apply_executed=True,
        status=status,
        note=(
            f"local-dev apply executed against {used_adapter.kind} adapter; "
            "no production SurrealDB activation, no default write"
        ),
    )


def _validate_format(fmt: str) -> str:
    if fmt not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"unsupported format: {fmt!r}; allowed: {sorted(SUPPORTED_FORMATS)}"
        )
    return fmt


def _validate_output_path(output: Path | None) -> Path | None:
    """Whitelist output paths to ``artifacts/`` and ``temp/`` only.

    Even though the scaffold never writes anything, we validate the
    flag eagerly so that downstream slices inherit the guard.
    """

    if output is None:
        return None
    if output.is_absolute():
        raise WriteDeniedError(f"absolute output paths are forbidden: {output}")
    parts = output.parts
    if not parts or parts[0] not in ALLOWED_OUTPUT_PREFIXES:
        raise WriteDeniedError(
            "output path must live under " f"{ALLOWED_OUTPUT_PREFIXES}, got: {output}"
        )
    if ".." in parts:
        raise WriteDeniedError(f"output path may not traverse with '..': {output}")
    return output


def _validate_input_dir(input_dir: Path | None) -> Path:
    if input_dir is None:
        raise InputNotFoundError("validate-jsonl requires --input-dir")
    try:
        exists = input_dir.exists()
        is_dir = input_dir.is_dir() if exists else False
    except OSError as exc:
        raise InputNotFoundError(
            f"cannot stat input directory: {input_dir}: {exc}"
        ) from exc
    if not exists:
        raise InputNotFoundError(f"input directory not found: {input_dir}")
    if not is_dir:
        raise InputNotFoundError(f"input path is not a directory: {input_dir}")
    return input_dir


def _path_contains_trading_state(source_path: str) -> bool:
    parts = {part.lower() for part in source_path.replace("\\", "/").split("/")}
    return bool(parts & TRADING_STATE_PATH_PARTS)


def _is_forbidden_source_path(source_path: str) -> bool:
    normalized = source_path.strip().replace("\\", "/")
    if not normalized:
        return True
    if normalized.startswith("//") or normalized.startswith("/"):
        return True
    if WINDOWS_DRIVE_PREFIX_RE.match(normalized):
        return True
    return any(part == ".." for part in normalized.split("/"))


def _contains_secret_like_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(
            SECRET_VALUE_RE.search(value)
            or AWS_ACCESS_KEY_RE.search(value)
            or PRIVATE_KEY_RE.search(value)
        )
    if isinstance(value, list):
        return any(_contains_secret_like_value(item) for item in value)
    if isinstance(value, dict):
        return any(
            _is_secret_like_key(str(key)) or _contains_secret_like_value(item)
            for key, item in value.items()
        )
    return False


def _is_secret_like_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in SECRET_LIKE_KEYS and normalized not in BENIGN_TOKEN_KEYS


def _record_source_path(record: dict[str, Any]) -> str | None:
    value = record.get("source_path")
    return value if isinstance(value, str) else None


def _validated_source_path(
    artifact: str,
    record: dict[str, Any],
    findings: list[JsonlValidationFinding],
    line: int | None,
) -> str | None:
    source_path_required = "source_path" in REQUIRED_JSONL_FIELDS[artifact]
    if "source_path" not in record:
        return None
    value = record["source_path"]
    if value is None and source_path_required:
        return None
    if not isinstance(value, str):
        findings.append(
            _finding(
                "blocking",
                "source_path_invalid_type",
                "source_path must be a non-empty string",
                artifact=artifact,
                line=line,
                record=record,
            )
        )
        return None
    if value == "" and source_path_required:
        return None
    if not value.strip():
        findings.append(
            _finding(
                "blocking",
                "source_path_blank",
                "source_path must be a non-empty string",
                artifact=artifact,
                line=line,
                record=record,
            )
        )
        return None
    return value


def _finding(
    severity: str,
    code: str,
    message: str,
    *,
    artifact: str | None = None,
    line: int | None = None,
    record: dict[str, Any] | None = None,
) -> JsonlValidationFinding:
    return JsonlValidationFinding(
        severity=severity,
        code=code,
        message=message,
        artifact=artifact,
        line=line,
        source_path=_record_source_path(record) if record is not None else None,
    )


def _read_jsonl_file(
    input_dir: Path,
    artifact: str,
    filename: str,
    findings: list[JsonlValidationFinding],
) -> list[dict[str, Any]]:
    path = input_dir / filename
    try:
        exists = path.exists()
        is_file = path.is_file() if exists else False
    except OSError as exc:
        findings.append(
            _finding("blocking", "jsonl_file_stat_failed", str(exc), artifact=artifact)
        )
        return []

    if not exists:
        findings.append(
            _finding(
                "blocking",
                "jsonl_file_missing",
                f"required JSONL artifact is missing: {filename}",
                artifact=artifact,
            )
        )
        return []
    if not is_file:
        findings.append(
            _finding(
                "blocking",
                "jsonl_path_not_file",
                f"JSONL artifact path is not a file: {filename}",
                artifact=artifact,
            )
        )
        return []

    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        findings.append(
            _finding("blocking", "jsonl_file_read_failed", str(exc), artifact=artifact)
        )
        return []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            findings.append(
                _finding(
                    "warning",
                    "jsonl_blank_line",
                    "blank JSONL lines are ignored",
                    artifact=artifact,
                    line=line_number,
                )
            )
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(
                _finding(
                    "blocking",
                    "jsonl_invalid_json",
                    f"invalid JSON at line {line_number}: {exc.msg}",
                    artifact=artifact,
                    line=line_number,
                )
            )
            continue
        if not isinstance(record, dict):
            findings.append(
                _finding(
                    "blocking",
                    "jsonl_record_not_object",
                    "JSONL record must be an object",
                    artifact=artifact,
                    line=line_number,
                )
            )
            continue
        record["__line"] = line_number
        records.append(record)
    return records


def _validate_record_fields(
    artifact: str,
    record: dict[str, Any],
    findings: list[JsonlValidationFinding],
    expected_run_id: str | None,
) -> str | None:
    line = record.get("__line") if isinstance(record.get("__line"), int) else None
    required = REQUIRED_JSONL_FIELDS[artifact]
    missing = sorted(field for field in required if record.get(field) in (None, ""))
    for field in missing:
        findings.append(
            _finding(
                "blocking",
                "required_field_missing",
                f"missing required field: {field}",
                artifact=artifact,
                line=line,
                record=record,
            )
        )

    schema_version = record.get("schema_version")
    if schema_version != INDEXER_SCHEMA_VERSION:
        findings.append(
            _finding(
                "blocking",
                "schema_version_mismatch",
                "record schema_version must match context-indexer/v0",
                artifact=artifact,
                line=line,
                record=record,
            )
        )

    run_id = record.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        findings.append(
            _finding(
                "blocking",
                "run_id_missing",
                "record run_id must be a non-empty string",
                artifact=artifact,
                line=line,
                record=record,
            )
        )
    elif expected_run_id is not None and run_id != expected_run_id:
        findings.append(
            _finding(
                "blocking",
                "run_id_mismatch",
                "record run_id differs from CLI --run-id",
                artifact=artifact,
                line=line,
                record=record,
            )
        )

    source_path = _validated_source_path(artifact, record, findings, line)
    if source_path is not None:
        if _is_forbidden_source_path(source_path):
            findings.append(
                _finding(
                    "blocking",
                    "forbidden_source_path",
                    "source_path must be relative and may not traverse",
                    artifact=artifact,
                    line=line,
                    record=record,
                )
            )
        if _path_contains_trading_state(source_path):
            findings.append(
                _finding(
                    "blocking",
                    "trading_state_path_in_jsonl",
                    "source_path looks like trading/runtime state",
                    artifact=artifact,
                    line=line,
                    record=record,
                )
            )

    for hash_field in (
        "source_hash",
        "raw_sha256",
        "normalized_sha256",
        "content_hash",
    ):
        value = record.get(hash_field)
        if value is not None and (
            not isinstance(value, str) or not SHA256_RE.match(value)
        ):
            findings.append(
                _finding(
                    "blocking",
                    "hash_field_invalid",
                    f"{hash_field} must be lowercase sha256 hex",
                    artifact=artifact,
                    line=line,
                    record=record,
                )
            )

    if artifact == "repo_artifacts":
        if record.get("integrity_algo") != "sha256":
            findings.append(
                _finding(
                    "blocking",
                    "integrity_algo_invalid",
                    "repo_artifact integrity_algo must be sha256",
                    artifact=artifact,
                    line=line,
                    record=record,
                )
            )
        if record.get("source_hash") != record.get("normalized_sha256"):
            findings.append(
                _finding(
                    "blocking",
                    "source_hash_mismatch",
                    "repo_artifact source_hash must equal normalized_sha256",
                    artifact=artifact,
                    line=line,
                    record=record,
                )
            )

    if _contains_secret_like_value(record):
        findings.append(
            _finding(
                "blocking",
                "secret_like_value_in_jsonl",
                "record contains a secret-like key or high-confidence secret pattern",
                artifact=artifact,
                line=line,
                record=record,
            )
        )

    return run_id if isinstance(run_id, str) and run_id.strip() else None


def _validate_cross_references(
    records: dict[str, list[dict[str, Any]]],
    findings: list[JsonlValidationFinding],
) -> None:
    artifact_hashes = {
        item.get("normalized_sha256")
        for item in records["repo_artifacts"]
        if isinstance(item.get("normalized_sha256"), str)
    }
    page_ids = {
        item.get("page_id")
        for item in records["doc_pages"]
        if isinstance(item.get("page_id"), str)
    }
    section_ids = {
        item.get("section_id")
        for item in records["doc_sections"]
        if isinstance(item.get("section_id"), str)
    }
    chunk_ids = {
        item.get("chunk_id")
        for item in records["doc_chunks"]
        if isinstance(item.get("chunk_id"), str)
    }
    symbol_ids = {
        item.get("symbol_id")
        for item in records["code_symbols"]
        if isinstance(item.get("symbol_id"), str)
    }

    source_hash_artifacts = (
        "doc_pages",
        "doc_sections",
        "doc_chunks",
        "code_symbols",
        "import_references",
        "test_cases",
        "config_references",
        "doc_code_links",
    )
    for artifact in source_hash_artifacts:
        for record in records[artifact]:
            if record.get("source_hash") not in artifact_hashes:
                findings.append(
                    _finding(
                        "blocking",
                        "source_hash_ref_missing",
                        "source_hash does not reference a repo_artifact normalized_sha256",
                        artifact=artifact,
                        line=record.get("__line"),
                        record=record,
                    )
                )

    for record in records["doc_sections"]:
        if record.get("page_id") not in page_ids:
            findings.append(
                _finding(
                    "blocking",
                    "doc_section_page_ref_missing",
                    "page_id does not reference doc_pages",
                    artifact="doc_sections",
                    line=record.get("__line"),
                    record=record,
                )
            )
    for record in records["doc_chunks"]:
        if record.get("page_id") not in page_ids:
            findings.append(
                _finding(
                    "blocking",
                    "doc_chunk_page_ref_missing",
                    "page_id does not reference doc_pages",
                    artifact="doc_chunks",
                    line=record.get("__line"),
                    record=record,
                )
            )
        if record.get("section_id") not in section_ids:
            findings.append(
                _finding(
                    "blocking",
                    "doc_chunk_section_ref_missing",
                    "section_id does not reference doc_sections",
                    artifact="doc_chunks",
                    line=record.get("__line"),
                    record=record,
                )
            )
        for field_name in ("previous_chunk_id", "next_chunk_id"):
            value = record.get(field_name)
            if value is not None and value not in chunk_ids:
                findings.append(
                    _finding(
                        "blocking",
                        "doc_chunk_neighbor_ref_missing",
                        f"{field_name} does not reference doc_chunks",
                        artifact="doc_chunks",
                        line=record.get("__line"),
                        record=record,
                    )
                )
    for record in records["test_cases"]:
        if record.get("symbol_id") not in symbol_ids:
            findings.append(
                _finding(
                    "blocking",
                    "test_case_symbol_ref_missing",
                    "symbol_id does not reference code_symbols",
                    artifact="test_cases",
                    line=record.get("__line"),
                    record=record,
                )
            )
    for record in records["doc_code_links"]:
        value = record.get("source_chunk_id")
        if value is not None and value not in chunk_ids:
            findings.append(
                _finding(
                    "blocking",
                    "doc_code_link_chunk_ref_missing",
                    "source_chunk_id does not reference doc_chunks",
                    artifact="doc_code_links",
                    line=record.get("__line"),
                    record=record,
                )
            )

    # Wave-14 within-batch cross-reference checks (warning only).
    # References across batches are valid (evidence may exist from prior imports),
    # so missing IDs are warnings, never blocking.
    evidence_ids = {
        item.get("evidence_id")
        for item in records["evidence_refs"]
        if isinstance(item.get("evidence_id"), str)
    }
    claim_ids_w14 = {
        item.get("claim_id")
        for item in records["claims"]
        if isinstance(item.get("claim_id"), str)
    }

    for record in records["claims"]:
        for ref in record.get("evidence_refs") or []:
            if isinstance(ref, str) and ref not in evidence_ids:
                findings.append(
                    _finding(
                        "warning",
                        "claim_evidence_ref_not_in_batch",
                        "claim evidence_ref is not present in this JSONL batch;"
                        " it may refer to existing DB evidence",
                        artifact="claims",
                        line=record.get("__line"),
                        record=record,
                    )
                )

    for record in records["decision_events"]:
        for ref in record.get("evidence_refs") or []:
            if isinstance(ref, str) and ref not in evidence_ids:
                findings.append(
                    _finding(
                        "warning",
                        "decision_evidence_ref_not_in_batch",
                        "decision_event evidence_ref is not present in this JSONL batch;"
                        " it may refer to existing DB evidence",
                        artifact="decision_events",
                        line=record.get("__line"),
                        record=record,
                    )
                )
        for ref in record.get("claim_refs") or []:
            if isinstance(ref, str) and ref not in claim_ids_w14:
                findings.append(
                    _finding(
                        "warning",
                        "decision_claim_ref_not_in_batch",
                        "decision_event claim_ref is not present in this JSONL batch;"
                        " it may refer to existing DB claim",
                        artifact="decision_events",
                        line=record.get("__line"),
                        record=record,
                    )
                )

    for record in records["agent_memories"]:
        for ref in record.get("evidence_refs") or []:
            if isinstance(ref, str) and ref not in evidence_ids:
                findings.append(
                    _finding(
                        "warning",
                        "memory_evidence_ref_not_in_batch",
                        "agent_memory evidence_ref is not present in this JSONL batch;"
                        " it may refer to existing DB evidence",
                        artifact="agent_memories",
                        line=record.get("__line"),
                        record=record,
                    )
                )


def validate_jsonl(
    input_dir: Path, expected_run_id: str | None = None
) -> JsonlValidationReport:
    findings: list[JsonlValidationFinding] = []
    records = {
        artifact: _read_jsonl_file(input_dir, artifact, filename, findings)
        for artifact, filename in EXPECTED_JSONL_FILES.items()
    }

    observed_run_ids: set[str] = set()
    for artifact, items in records.items():
        for record in items:
            run_id = _validate_record_fields(
                artifact, record, findings, expected_run_id
            )
            if run_id is not None:
                observed_run_ids.add(run_id)

    if expected_run_id is None and len(observed_run_ids) > 1:
        findings.append(
            _finding(
                "blocking",
                "run_id_inconsistent",
                "JSONL artifacts contain more than one run_id",
            )
        )

    _validate_cross_references(records, findings)

    for items in records.values():
        for record in items:
            record.pop("__line", None)

    run_id = expected_run_id or (
        next(iter(observed_run_ids)) if len(observed_run_ids) == 1 else None
    )
    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda item: (
                item.severity,
                item.code,
                item.artifact or "",
                item.line or 0,
                item.source_path or "",
            ),
        )
    )
    return JsonlValidationReport(
        input_dir=input_dir, run_id=run_id, records=records, findings=ordered_findings
    )


def _record_id(table: str, raw_id: str) -> str:
    return f"{table}:{raw_id}"


def _payload_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "__line"}
    encoded = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe_payload_hash(record: dict[str, Any]) -> str | None:
    value = record.get("payload_hash")
    if isinstance(value, str) and SHA256_RE.match(value):
        return value
    payload = record.get("payload")
    if isinstance(payload, dict):
        return _payload_hash(payload)
    return None


def _existing_record_from_raw(raw: dict[str, Any]) -> ExistingRecord:
    table = raw.get("table")
    record_id = raw.get("record_id") or raw.get("id")
    if not isinstance(table, str) or not table.strip():
        raise ExistingRecordsValidationError("existing record table must be a string")
    if not isinstance(record_id, str) or not record_id.strip():
        raise ExistingRecordsValidationError("existing record_id must be a string")
    record_table, _, raw_id = record_id.partition(":")
    if not record_table or not raw_id or record_table != table:
        raise ExistingRecordsValidationError(
            "existing record_id must be prefixed with matching table"
        )
    schema_version = raw.get("schema_version")
    if schema_version is not None and not isinstance(schema_version, str):
        raise ExistingRecordsValidationError("existing record schema_version must be a string")
    payload_hash = _safe_payload_hash(raw)
    if payload_hash is None:
        raise ExistingRecordsValidationError(
            "existing record must provide payload_hash or object payload"
        )
    # Capture the prior-record payload (when present) so the apply
    # pipeline can preserve original record fields under tombstone
    # metadata. Strip control keys that belong to the fixture envelope
    # rather than the record body, and never carry the line counter.
    raw_payload = raw.get("payload")
    preserved_payload: Mapping[str, Any] | None
    if isinstance(raw_payload, dict):
        _control_keys = {
            "__line",
            "payload_hash",
            "schema_version",
            "table",
            "record_id",
            "id",
        }
        preserved_payload = {
            key: copy.deepcopy(value)
            for key, value in raw_payload.items()
            if key not in _control_keys
        }
    else:
        preserved_payload = None
    return ExistingRecord(
        table=table,
        record_id=record_id,
        payload_hash=payload_hash,
        schema_version=schema_version,
        payload=preserved_payload,
    )


def load_existing_records(path: Path | None) -> ReadOnlyExistingRecords:
    """Load read-only existing DB state from an explicit local fixture.

    This boundary models records fetched from SurrealDB without opening a client
    or allowing writes. A future adapter can implement the same shape.
    """

    if path is None:
        return ReadOnlyExistingRecords(records=(), source="empty")
    try:
        exists = path.exists()
        is_file = path.is_file() if exists else False
    except OSError as exc:
        raise InputNotFoundError(
            f"cannot stat existing records fixture: {path}: {exc}"
        ) from exc
    if not exists:
        raise InputNotFoundError(f"existing records fixture not found: {path}")
    if not is_file:
        raise ExistingRecordsValidationError(
            f"existing records fixture path is not a file: {path}"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExistingRecordsValidationError(
            f"invalid existing records JSON: {path}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise InputNotFoundError(
            f"cannot read existing records fixture: {path}: {exc}"
        ) from exc

    if isinstance(raw, dict):
        items = raw.get("records")
    else:
        items = raw
    if not isinstance(items, list):
        raise ExistingRecordsValidationError(
            "existing records fixture must be a list or mapping with records list"
        )
    records: list[ExistingRecord] = []
    seen_record_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ExistingRecordsValidationError("existing record entries must be objects")
        record = _existing_record_from_raw(item)
        if record.record_id in seen_record_ids:
            raise ExistingRecordsValidationError(
                "duplicate existing record_id in existing records fixture"
            )
        seen_record_ids.add(record.record_id)
        records.append(record)
    return ReadOnlyExistingRecords(
        records=tuple(sorted(records, key=lambda item: (item.table, item.record_id))),
        source=str(path),
    )


def _source_ref(record: dict[str, Any]) -> str | None:
    for field_name in (
        "source_path",
        "source_chunk_id",
        "from_id",
    ):
        value = record.get(field_name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _dependency_record_id(artifact: str, value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    table = TABLE_BY_ARTIFACT[artifact]
    return _record_id(table, value)


def _action_dependencies(artifact: str, record: dict[str, Any]) -> tuple[str, ...]:
    dependencies: list[str] = []
    if artifact == "doc_sections":
        dependency = _dependency_record_id("doc_pages", record.get("page_id"))
        if dependency is not None:
            dependencies.append(dependency)
    elif artifact == "doc_chunks":
        for dependency_artifact, field_name in (
            ("doc_pages", "page_id"),
            ("doc_sections", "section_id"),
            ("doc_chunks", "previous_chunk_id"),
        ):
            dependency = _dependency_record_id(
                dependency_artifact, record.get(field_name)
            )
            if dependency is not None:
                dependencies.append(dependency)
    elif artifact == "test_cases":
        dependency = _dependency_record_id("code_symbols", record.get("symbol_id"))
        if dependency is not None:
            dependencies.append(dependency)
    elif artifact == "doc_code_links":
        dependency = _dependency_record_id("doc_chunks", record.get("source_chunk_id"))
        if dependency is not None:
            dependencies.append(dependency)
    elif artifact == "dependency_edges":
        for field_name in ("from_id", "to_id"):
            value = record.get(field_name)
            if isinstance(value, str) and value.strip():
                dependencies.append(value)
    return tuple(sorted(dict.fromkeys(dependencies)))


def _plan_warning_from_finding(finding: JsonlValidationFinding) -> ImportPlanWarning:
    return ImportPlanWarning(
        code=finding.code,
        message=finding.message,
        artifact=finding.artifact,
        source_ref=finding.source_path,
        severity=finding.severity,
    )


def build_import_plan(
    input_dir: Path, expected_run_id: str | None = None
) -> ImportPlan:
    report = validate_jsonl(input_dir, expected_run_id)
    if report.blocking_count:
        warnings = tuple(
            _plan_warning_from_finding(finding) for finding in report.findings
        )
        return ImportPlan(
            schema_version=SCHEMA_VERSION,
            run_id=report.run_id,
            input_dir=input_dir,
            status="blocked",
            actions=(),
            warnings=warnings,
            table_counts={},
            action_counts={},
            has_blocking_validation_findings=True,
            validation_report=report,
            import_order=tuple(
                TABLE_BY_ARTIFACT[artifact] for artifact in IMPORT_ORDER
            ),
        )

    actions: list[ImportPlanAction] = []
    warnings: list[ImportPlanWarning] = [
        _plan_warning_from_finding(finding)
        for finding in report.findings
        if finding.severity == "warning"
    ]
    seen_record_ids: set[str] = set()

    for artifact in IMPORT_ORDER:
        table = TABLE_BY_ARTIFACT[artifact]
        id_field = ID_FIELD_BY_ARTIFACT[artifact]
        records = sorted(
            report.records[artifact],
            key=lambda item: str(item.get(id_field, "")),
        )
        for record in records:
            raw_id = record.get(id_field)
            if not isinstance(raw_id, str) or not raw_id.strip():
                warnings.append(
                    ImportPlanWarning(
                        code="missing_record_id",
                        message=f"record missing deterministic id field: {id_field}",
                        artifact=artifact,
                        source_ref=_source_ref(record),
                        severity="blocking",
                    )
                )
                continue
            record_id = _record_id(table, raw_id)
            if record_id in seen_record_ids:
                action = "skip"
                reason = "duplicate record_id in validated input; first occurrence wins"
            else:
                action = "create"
                reason = "validated JSONL record; DB-independent candidate create"
                seen_record_ids.add(record_id)
            actions.append(
                ImportPlanAction(
                    action=action,
                    table=table,
                    record_id=record_id,
                    artifact=artifact,
                    source_ref=_source_ref(record),
                    depends_on=_action_dependencies(artifact, record),
                    reason=reason,
                    payload_hash=_payload_hash(record),
                    payload=(
                        {
                            k: v
                            for k, v in record.items()
                            if k not in _JSONL_INTERNAL_FIELDS
                        }
                        if action == "create"
                        else None
                    ),
                )
            )

    table_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for action in actions:
        table_counts[action.table] = table_counts.get(action.table, 0) + 1
        action_counts[action.action] = action_counts.get(action.action, 0) + 1

    return ImportPlan(
        schema_version=SCHEMA_VERSION,
        run_id=report.run_id,
        input_dir=input_dir,
        status="planned",
        actions=tuple(
            sorted(
                actions,
                key=lambda item: (
                    IMPORT_ORDER.index(item.artifact),
                    item.table,
                    item.record_id,
                    item.action,
                ),
            )
        ),
        warnings=tuple(
            sorted(
                warnings,
                key=lambda item: (
                    item.severity,
                    item.code,
                    item.artifact or "",
                    item.source_ref or "",
                ),
            )
        ),
        table_counts=table_counts,
        action_counts=action_counts,
        has_blocking_validation_findings=False,
        validation_report=report,
        import_order=tuple(TABLE_BY_ARTIFACT[artifact] for artifact in IMPORT_ORDER),
    )


def _finding_from_plan_warning(warning: ImportPlanWarning) -> ReconcileFinding:
    return ReconcileFinding(
        severity=warning.severity,
        code=warning.code,
        message=warning.message,
        record_id=warning.source_ref,
    )


def _validate_reconcile_table_policy(
    table: str, record_id: str, findings: list[ReconcileFinding]
) -> bool:
    if table in FORBIDDEN_CONTEXT_IMPORT_TABLES:
        findings.append(
            ReconcileFinding(
                severity="blocking",
                code="forbidden_table",
                message="table is forbidden for context import reconcile",
                table=table,
                record_id=record_id,
            )
        )
        return False
    if table not in ALLOWED_CONTEXT_IMPORT_TABLES:
        findings.append(
            ReconcileFinding(
                severity="blocking",
                code="forbidden_table",
                message="table is not in the context import allow-list",
                table=table,
                record_id=record_id,
            )
        )
        return False
    return True


def reconcile_import_plan(
    plan: ImportPlan,
    existing_records: ReadOnlyExistingRecords,
) -> ReconcileReport:
    findings: list[ReconcileFinding] = []
    warnings = list(plan.warnings)

    if plan.has_blocking_validation_findings:
        findings.extend(_finding_from_plan_warning(warning) for warning in plan.warnings)
        return ReconcileReport(
            schema_version=SCHEMA_VERSION,
            run_id=plan.run_id,
            input_dir=plan.input_dir,
            status="blocked",
            existing_records_source=existing_records.source,
            actions=(),
            findings=tuple(findings),
            warnings=(),
            plan=plan,
        )

    existing_by_id = existing_records.by_record_id()
    planned_ids: set[str] = set()
    reconciled_ids: set[str] = set()
    actions: list[ReconcileAction] = []

    for plan_action in plan.actions:
        planned_ids.add(plan_action.record_id)
        if not _validate_reconcile_table_policy(
            plan_action.table, plan_action.record_id, findings
        ):
            continue
        if plan_action.record_id in reconciled_ids:
            continue
        reconciled_ids.add(plan_action.record_id)
        if plan_action.action == "skip":
            existing = existing_by_id.get(plan_action.record_id)
            if existing is not None and (
                existing.table != plan_action.table
                or existing.schema_version not in (None, SCHEMA_VERSION)
            ):
                findings.append(
                    ReconcileFinding(
                        severity="blocking",
                        code="schema_mismatch",
                        message="existing record table or schema_version differs from import plan",
                        table=existing.table,
                        record_id=existing.record_id,
                    )
                )
                continue
            actions.append(
                ReconcileAction(
                    action="skip",
                    table=plan_action.table,
                    record_id=plan_action.record_id,
                    source_ref=plan_action.source_ref,
                    reason=plan_action.reason,
                    payload_hash=plan_action.payload_hash,
                    existing_payload_hash=existing.payload_hash
                    if existing is not None
                    else None,
                )
            )
            continue
        existing = existing_by_id.get(plan_action.record_id)
        if existing is None:
            actions.append(
                ReconcileAction(
                    action="create",
                    table=plan_action.table,
                    record_id=plan_action.record_id,
                    source_ref=plan_action.source_ref,
                    reason="record_missing",
                    payload_hash=plan_action.payload_hash,
                    existing_payload_hash=None,
                    payload=plan_action.payload,
                )
            )
            continue
        if existing.table != plan_action.table or existing.schema_version not in (
            None,
            SCHEMA_VERSION,
        ):
            findings.append(
                ReconcileFinding(
                    severity="blocking",
                    code="schema_mismatch",
                    message="existing record table or schema_version differs from import plan",
                    table=existing.table,
                    record_id=existing.record_id,
                )
            )
            continue
        if existing.payload_hash == plan_action.payload_hash:
            actions.append(
                ReconcileAction(
                    action="skip",
                    table=plan_action.table,
                    record_id=plan_action.record_id,
                    source_ref=plan_action.source_ref,
                    reason="record_same",
                    payload_hash=plan_action.payload_hash,
                    existing_payload_hash=existing.payload_hash,
                )
            )
        else:
            actions.append(
                ReconcileAction(
                    action="update_candidate",
                    table=plan_action.table,
                    record_id=plan_action.record_id,
                    source_ref=plan_action.source_ref,
                    reason="record_changed",
                    payload_hash=plan_action.payload_hash,
                    existing_payload_hash=existing.payload_hash,
                    payload=plan_action.payload,
                )
            )

    for existing in existing_records.records:
        if existing.record_id in planned_ids:
            continue
        if not _validate_reconcile_table_policy(existing.table, existing.record_id, findings):
            continue
        if existing.schema_version not in (None, SCHEMA_VERSION):
            findings.append(
                ReconcileFinding(
                    severity="blocking",
                    code="schema_mismatch",
                    message="existing record schema_version differs from context importer schema",
                    table=existing.table,
                    record_id=existing.record_id,
                )
            )
            continue
        actions.append(
            ReconcileAction(
                action="tombstone_candidate",
                table=existing.table,
                record_id=existing.record_id,
                source_ref=None,
                reason="record_removed_from_snapshot",
                payload_hash=None,
                existing_payload_hash=existing.payload_hash,
                existing_payload=existing.payload,
            )
        )

    ordered_actions = tuple(
        sorted(actions, key=lambda item: (item.table, item.record_id, item.action))
    )
    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda item: (
                item.severity,
                item.code,
                item.table or "",
                item.record_id or "",
            ),
        )
    )
    return ReconcileReport(
        schema_version=SCHEMA_VERSION,
        run_id=plan.run_id,
        input_dir=plan.input_dir,
        status="blocked" if ordered_findings else "reconciled",
        existing_records_source=existing_records.source,
        actions=ordered_actions,
        findings=ordered_findings,
        warnings=tuple(warnings),
        plan=plan,
    )


def _require_mapping(raw: Any, *, path: Path) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigValidationError(f"config must be a YAML mapping: {path}")
    return raw


def _require_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"config field {key!r} must be a non-empty string")
    return value


def _require_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigValidationError(f"config field {key!r} must be a positive integer")
    return value


def _require_bool(raw: dict[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ConfigValidationError(f"config field {key!r} must be a boolean")
    return value


def _require_str_list(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigValidationError(f"config field {key!r} must be a non-empty list")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigValidationError(
                f"config field {key!r} must contain only non-empty strings"
            )
        normalized.append(item.strip())
    if len(normalized) != len(set(normalized)):
        raise ConfigValidationError(f"config field {key!r} contains duplicates")
    return tuple(normalized)


def load_config(path: Path) -> ContextImportConfig:
    """Load and validate the explicit local importer config.

    The config is a local development input only. It never enables writes and
    never opens a SurrealDB connection in this scaffold.
    """

    try:
        exists = path.exists()
        is_file = path.is_file() if exists else False
    except OSError as exc:
        raise InputNotFoundError(f"cannot stat config file: {path}: {exc}") from exc

    if not exists:
        raise InputNotFoundError(f"config file not found: {path}")
    if not is_file:
        raise ConfigValidationError(f"config path is not a file: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"invalid YAML config: {path}: {exc}") from exc
    except OSError as exc:
        raise InputNotFoundError(f"cannot read config file: {path}: {exc}") from exc

    data = _require_mapping(raw, path=path)

    schema_version = _require_str(data, "schema_version")
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ConfigValidationError(
            "unsupported config schema_version: "
            f"{schema_version!r}; expected {CONFIG_SCHEMA_VERSION!r}"
        )

    auth_mode = _require_str(data, "auth_mode")
    if auth_mode not in ALLOWED_AUTH_MODES:
        raise ConfigValidationError(
            f"unsupported auth_mode: {auth_mode!r}; allowed: {sorted(ALLOWED_AUTH_MODES)}"
        )

    allow_apply_default = _require_bool(data, "allow_apply_default")
    if allow_apply_default:
        raise ConfigValidationError(
            "allow_apply_default must remain false for the context importer"
        )

    allowed_tables = _require_str_list(data, "allowed_tables")
    forbidden_tables = _require_str_list(data, "forbidden_tables")

    forbidden_in_allowed = sorted(
        set(allowed_tables).intersection(FORBIDDEN_CONTEXT_IMPORT_TABLES)
    )
    if forbidden_in_allowed:
        raise ConfigValidationError(
            "allowed_tables contains forbidden trading/governance tables: "
            f"{forbidden_in_allowed}"
        )

    missing_forbidden = sorted(
        FORBIDDEN_CONTEXT_IMPORT_TABLES.difference(forbidden_tables)
    )
    if missing_forbidden:
        raise ConfigValidationError(
            "forbidden_tables must explicitly include all blocked "
            f"trading/governance tables; missing: {missing_forbidden}"
        )

    overlap = sorted(set(allowed_tables).intersection(forbidden_tables))
    if overlap:
        raise ConfigValidationError(
            f"tables may not appear in both allowed_tables and forbidden_tables: {overlap}"
        )

    return ContextImportConfig(
        path=path,
        schema_version=schema_version,
        surreal_url=_require_str(data, "surreal_url"),
        namespace=_require_str(data, "namespace"),
        database=_require_str(data, "database"),
        auth_mode=auth_mode,
        timeout=_require_int(data, "timeout"),
        allow_apply_default=allow_apply_default,
        allowed_tables=allowed_tables,
        forbidden_tables=forbidden_tables,
    )


def _build_payload(
    command: str,
    *,
    dry_run: bool,
    apply_requested: bool,
    config: ContextImportConfig | None = None,
    status: str = "scaffold-ack",
    note: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "dry_run": dry_run,
        "apply_requested": apply_requested,
        "surrealdb_connection": "disabled",
        "implemented": False,
        "config_loaded": config is not None,
    }
    if config is not None:
        payload["config"] = config.to_payload()
    if note is not None:
        payload["note"] = note
    return payload


def _render(payload: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    if fmt == "jsonl":
        if payload.get("command") == "audit":
            return json.dumps(payload, ensure_ascii=True, sort_keys=True)
        if payload.get("command") == "dry-run" and payload.get("implemented") is True:
            lines = [
                json.dumps(
                    {
                        key: value
                        for key, value in payload.items()
                        if key not in {"actions", "findings", "warnings"}
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            ]
            lines.extend(
                json.dumps(
                    {"record_type": "action", **action},
                    ensure_ascii=True,
                    sort_keys=True,
                )
                for action in payload["actions"]
            )
            lines.extend(
                json.dumps(
                    {"record_type": "finding", **finding},
                    ensure_ascii=True,
                    sort_keys=True,
                )
                for finding in payload["findings"]
            )
            lines.extend(
                json.dumps(
                    {"record_type": "warning", **warning},
                    ensure_ascii=True,
                    sort_keys=True,
                )
                for warning in payload["warnings"]
            )
            return "\n".join(lines)
        if payload.get("command") == "plan" and payload.get("implemented") is True:
            lines = [
                json.dumps(
                    {
                        key: value
                        for key, value in payload.items()
                        if key not in {"actions", "warnings"}
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            ]
            lines.extend(
                json.dumps(
                    {"record_type": "action", **action},
                    ensure_ascii=True,
                    sort_keys=True,
                )
                for action in payload["actions"]
            )
            lines.extend(
                json.dumps(
                    {"record_type": "warning", **warning},
                    ensure_ascii=True,
                    sort_keys=True,
                )
                for warning in payload["warnings"]
            )
            return "\n".join(lines)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if fmt == "markdown":
        if payload.get("command") == "audit":
            lines = [f"# context_importer audit: {payload['mode']}"]
            lines.extend(
                [
                    f"- **status**: `{payload['status']}`",
                    f"- **run_id**: `{payload['run_id']}`",
                    f"- **input_dir**: `{payload['input_dir']}`",
                    f"- **git_commit**: `{payload['git_commit']}`",
                    f"- **namespace**: `{payload['namespace']}`",
                    f"- **database**: `{payload['database']}`",
                    f"- **generated_at**: `{payload['generated_at']}`",
                    f"- **duration_ms**: `{payload['duration_ms']}`",
                    f"- **operator_tool_version**: `{payload['operator_tool_version']}`",
                    f"- **payload_policy**: `{payload['payload_policy']}`",
                    "",
                    "## Artifact Counts",
                ]
            )
            if payload["artifact_counts"]:
                for artifact, count in payload["artifact_counts"].items():
                    lines.append(f"- `{artifact}`: `{count}`")
            else:
                lines.append("- No artifacts counted.")
            lines.extend(["", "## Planned Counts"])
            for key, value in payload["planned_counts"].items():
                lines.append(f"- `{key}`: `{value}`")
            lines.extend(["", "## Actual Counts"])
            for key, value in payload["actual_counts"].items():
                lines.append(f"- `{key}`: `{value}`")
            lines.extend(["", "## Warnings"])
            if not payload["warnings"]:
                lines.append("- No warnings.")
            for warning in payload["warnings"]:
                code = warning.get("code", "unknown")
                severity = warning.get("severity", "warning")
                location = warning.get("artifact") or warning.get("table") or "global"
                lines.append(f"- **{severity}** `{code}` ({location})")
            lines.extend(["", "## Blocking Findings"])
            if not payload["blocking_findings"]:
                lines.append("- No blocking findings.")
            for finding in payload["blocking_findings"]:
                code = finding.get("code", "unknown")
                location = finding.get("artifact") or finding.get("table") or "global"
                lines.append(f"- **blocking** `{code}` ({location})")
            return "\n".join(lines)
        if payload.get("command") == "dry-run" and payload.get("implemented") is True:
            lines = ["# context_importer: dry-run reconcile"]
            lines.extend(
                [
                    f"- **status**: `{payload['status']}`",
                    f"- **input_dir**: `{payload['input_dir']}`",
                    f"- **run_id**: `{payload['run_id']}`",
                    f"- **existing_records_source**: `{payload['existing_records_source']}`",
                    f"- **surrealdb_writes**: `{payload['surrealdb_writes']}`",
                    "",
                    "## Counts",
                ]
            )
            for key, value in payload["counts"].items():
                lines.append(f"- `{key}`: `{value}`")
            lines.extend(["", "## Actions"])
            if not payload["actions"]:
                lines.append("- No reconcile actions generated.")
            for action in payload["actions"]:
                lines.append(
                    "- "
                    f"`{action['action']}` `{action['record_id']}` "
                    f"({action['table']}, reason: `{action['reason']}`, "
                    f"payload_hash: `{action['payload_hash']}`, "
                    f"existing_payload_hash: `{action['existing_payload_hash']}`)"
                )
            lines.extend(["", "## Findings"])
            if not payload["findings"]:
                lines.append("- No findings.")
            for finding in payload["findings"]:
                table = finding.get("table") or "global"
                record_id = finding.get("record_id") or "none"
                lines.append(
                    "- "
                    f"**{finding['severity']}** `{finding['code']}` "
                    f"({table}, record_id: `{record_id}`): {finding['message']}"
                )
            lines.extend(["", "## Warnings"])
            if not payload["warnings"]:
                lines.append("- No warnings.")
            for warning in payload["warnings"]:
                artifact = warning.get("artifact") or "global"
                source_ref = warning.get("source_ref") or "none"
                lines.append(
                    "- "
                    f"**{warning['severity']}** `{warning['code']}` "
                    f"({artifact}, source_ref: `{source_ref}`): {warning['message']}"
                )
            return "\n".join(lines)
        if payload.get("command") == "plan" and payload.get("implemented") is True:
            lines = ["# context_importer: plan"]
            lines.extend(
                [
                    f"- **status**: `{payload['status']}`",
                    f"- **input_dir**: `{payload['input_dir']}`",
                    f"- **run_id**: `{payload['run_id']}`",
                    f"- **has_blocking_validation_findings**: `{payload['has_blocking_validation_findings']}`",
                    f"- **actions**: `{payload['counts']['actions']}`",
                    f"- **warnings**: `{payload['counts']['warnings']}`",
                    "",
                    "## Import Order",
                ]
            )
            for table in payload["import_order"]:
                lines.append(f"- `{table}`")
            lines.extend(["", "## Table Counts"])
            for table, count in payload["table_counts"].items():
                lines.append(f"- `{table}`: `{count}`")
            lines.extend(["", "## Action Counts"])
            if payload["action_counts"]:
                for action, count in payload["action_counts"].items():
                    lines.append(f"- `{action}`: `{count}`")
            else:
                lines.append("- No write-ready actions.")
            lines.extend(["", "## Actions"])
            if not payload["actions"]:
                lines.append("- No actions generated.")
            for action in payload["actions"]:
                depends_on = ", ".join(action["depends_on"]) or "none"
                lines.append(
                    "- "
                    f"`{action['action']}` `{action['record_id']}` "
                    f"({action['artifact']}, depends_on: `{depends_on}`, "
                    f"payload_hash: `{action['payload_hash']}`)"
                )
            lines.extend(["", "## Warnings"])
            if not payload["warnings"]:
                lines.append("- No warnings.")
            for warning in payload["warnings"]:
                artifact = warning.get("artifact") or "global"
                source_ref = warning.get("source_ref") or "none"
                lines.append(
                    "- "
                    f"**{warning['severity']}** `{warning['code']}` "
                    f"({artifact}, source_ref: `{source_ref}`): {warning['message']}"
                )
            return "\n".join(lines)
        lines = [f"# context_importer: {payload['command']}"]
        for key in sorted(payload.keys()):
            lines.append(f"- **{key}**: `{payload[key]}`")
        return "\n".join(lines)
    raise UnsupportedFormatError(f"unsupported format: {fmt!r}")


def _render_audit_report(report: ContextImportAuditReport, fmt: str) -> str:
    return _render(report.to_payload(), fmt)


def _audit_markdown_path(path: Path) -> Path:
    # When the JSON output already ends in ``.md`` we must not collapse the
    # markdown sibling onto the same path, otherwise ``_write_audit_outputs``
    # would silently overwrite the JSON artifact with the markdown render.
    # Append ``.md`` instead of replacing the suffix in that case so the two
    # outputs stay distinct (e.g. ``foo.md`` -> ``foo.md.md``).
    if path.suffix == ".md":
        return path.with_name(path.name + ".md")
    if path.suffix:
        return path.with_suffix(".md")
    return path.with_name(path.name + ".md")


def _write_audit_outputs(path: Path, report: ContextImportAuditReport) -> None:
    _write_report(path, _render_audit_report(report, "json"))
    _write_report(_audit_markdown_path(path), _render_audit_report(report, "markdown"))


def _render_jsonl_report(report: JsonlValidationReport, fmt: str) -> str:
    payload = report.to_payload()
    if fmt == "json":
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    if fmt == "jsonl":
        artifact_counts = {
            artifact: len(items) for artifact, items in sorted(report.records.items())
        }
        summary = {
            "record_type": "summary",
            "schema_version": SCHEMA_VERSION,
            "command": "validate-jsonl",
            "status": report.status,
            "input_dir": str(report.input_dir),
            "run_id": report.run_id,
            "artifact_count": len(report.records),
            "artifact_counts": artifact_counts,
            "checked_records": sum(artifact_counts.values()),
            "finding_count": len(report.findings),
            "has_blocking": report.blocking_count > 0,
        }
        lines = [json.dumps(summary, ensure_ascii=True, sort_keys=True)]
        lines.extend(
            json.dumps(
                {"record_type": "finding", **finding.to_payload()},
                ensure_ascii=True,
                sort_keys=True,
            )
            for finding in report.findings
        )
        return "\n".join(lines)
    if fmt == "markdown":
        lines = ["# context_importer: validate-jsonl"]
        lines.extend(
            [
                f"- **status**: `{report.status}`",
                f"- **input_dir**: `{report.input_dir}`",
                f"- **run_id**: `{report.run_id}`",
                f"- **blocking_count**: `{report.blocking_count}`",
                f"- **warning_count**: `{report.warning_count}`",
                f"- **info_count**: `{report.info_count}`",
                "",
                "## Artifact Counts",
            ]
        )
        for artifact, items in sorted(report.records.items()):
            lines.append(f"- **{artifact}**: `{len(items)}`")
        lines.extend(["", "## Findings"])
        if not report.findings:
            lines.append("- No findings.")
        for finding in report.findings:
            location = finding.artifact or "global"
            if finding.line is not None:
                location = f"{location}:{finding.line}"
            source = f" `{finding.source_path}`" if finding.source_path else ""
            lines.append(
                f"- **{finding.severity}** `{finding.code}` ({location}){source}: {finding.message}"
            )
        return "\n".join(lines)
    raise UnsupportedFormatError(f"unsupported format: {fmt!r}")


def _write_report(path: Path, rendered: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        target = path.resolve(strict=False)
        cwd = Path.cwd().resolve()
        allowed_roots = tuple(cwd / prefix for prefix in ALLOWED_OUTPUT_PREFIXES)
        if not any(target.is_relative_to(root) for root in allowed_roots):
            raise WriteDeniedError(
                "report output must resolve under "
                f"{ALLOWED_OUTPUT_PREFIXES}, got: {path}"
            )
        path.write_text(rendered + "\n", encoding="utf-8")
    except WriteDeniedError:
        raise
    except OSError as exc:
        raise WriteDeniedError(f"cannot write report output: {path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context_importer",
        description=(
            "Context Importer CLI scaffold (#2068). Offline, dry-run-only "
            "in this slice. No SurrealDB connection, no writes."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in SUPPORTED_COMMANDS:
        sub = subparsers.add_parser(
            command,
            help=f"{command} (scaffold; not implemented in #2068)",
            description=(
                f"Scaffold stub for `{command}`. Implementation will land "
                "in a follow-up slice."
            ),
        )
        sub.add_argument(
            "--input-dir",
            type=Path,
            default=None,
            help="Directory containing JSONL artefacts (read-only).",
        )
        sub.add_argument(
            "--surreal-url",
            type=str,
            default="",
            help="SurrealDB URL (parsed but never used in scaffold).",
        )
        sub.add_argument(
            "--namespace",
            type=str,
            default=None,
            help="SurrealDB namespace (parsed but never used in scaffold).",
        )
        sub.add_argument(
            "--database",
            type=str,
            default=None,
            help="SurrealDB database (parsed but never used in scaffold).",
        )
        sub.add_argument(
            "--run-id",
            type=str,
            default=None,
            help="Optional deterministic run identifier (echoed only).",
        )
        sub.add_argument(
            "--config",
            type=Path,
            default=None,
            help=(
                "Optional local importer config YAML. Loaded and validated only "
                "when supplied; it never enables writes in this scaffold."
            ),
        )
        sub.add_argument(
            "--report-output",
            type=Path,
            default=None,
            help=(
                "Optional report output path. Must live under artifacts/ or temp/. "
                "Only validate-jsonl writes a report, and only when supplied."
            ),
        )
        sub.add_argument(
            "--audit-output",
            type=Path,
            default=None,
            help=(
                "Optional audit JSON output path for plan, dry-run, apply, or audit. "
                "Must live under artifacts/ or temp/. A Markdown summary is written "
                "next to it with .md suffix."
            ),
        )
        sub.add_argument(
            "--audit-mode",
            choices=sorted(SUPPORTED_AUDIT_MODES),
            default=None,
            help=(
                "Mode for the audit subcommand. Defaults to dry-run when omitted. "
                "plan/dry-run are read-only; apply runs only through the existing "
                "local-dev apply gate."
            ),
        )
        sub.add_argument(
            "--git-commit",
            type=str,
            default=None,
            help="Git commit to embed in audit reports; defaults to 'unknown'.",
        )
        sub.add_argument(
            "--audit-generated-at",
            type=str,
            default=None,
            help=(
                "Optional ISO8601 timestamp injection for deterministic audit tests. "
                "When omitted, the injectable clock defaults to SystemClock."
            ),
        )
        sub.add_argument(
            "--audit-duration-ms",
            type=int,
            default=None,
            help="Optional non-negative duration in milliseconds for audit reports.",
        )
        sub.add_argument(
            "--existing-records",
            type=Path,
            default=None,
            help=(
                "Optional read-only JSON fixture representing existing SurrealDB "
                "records for dry-run reconcile. No SurrealDB client is opened."
            ),
        )
        sub.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate only. This is the default behavior.",
        )
        sub.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Opt in to write/apply. Required (together with "
                "--apply-mode local-dev, --config, --input-dir, --run-id) "
                "to enter the gated local-dev apply pipeline on the "
                "`apply` subcommand. Any use of --apply on a non-apply "
                "subcommand exits with code 5 (WRITE_DENIED)."
            ),
        )
        sub.add_argument(
            "--apply-mode",
            choices=sorted(SUPPORTED_APPLY_MODES),
            default=None,
            help=(
                "Apply mode gate. Only meaningful on the `apply` "
                "subcommand combined with --apply. Use 'local-dev' to "
                "enter the gated local-dev apply pipeline against the "
                "default in-memory adapter. No production SurrealDB "
                "activation, no default write."
            ),
        )
        sub.add_argument(
            "--adapter",
            choices=["in-memory", "surrealdb-local"],
            default="in-memory",
            help=(
                "Apply adapter (default: in-memory, no network). "
                "Use 'surrealdb-local' to opt in to real local SurrealDB "
                "writes via HTTP API. Requires --apply and a running "
                "local SurrealDB container at 127.0.0.1:8010. (#2458)"
            ),
        )
        sub.add_argument(
            "--secrets-path",
            type=Path,
            default=None,
            help=(
                "Directory containing SURREALDB_ENV credentials file. "
                "Defaults to $SECRETS_PATH or ~/Documents/.secrets/.cdb. "
                "Only used when config auth_mode is 'root'."
            ),
        )
        sub.add_argument(
            "--format",
            choices=sorted(SUPPORTED_FORMATS),
            default="json",
            help="Render format for command output (default: json).",
        )

    return parser


def _handle(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Resolve command behavior.

    Returns ``(payload, exit_code)``. Most subcommands are dry-run; the
    only command that may execute writes is ``apply`` and only under
    the strict local-dev gate (#2073).
    """

    command: str = args.command
    apply_requested: bool = bool(args.apply)
    apply_mode: str | None = getattr(args, "apply_mode", None)
    audit_clock_input = _parse_audit_generated_at(args.audit_generated_at)
    audit_clock: ClockProvider | None = (
        _FixedAuditClock(audit_clock_input) if audit_clock_input is not None else None
    )
    audit_duration_ms = _duration_ms_value(args.audit_duration_ms)
    # Default is dry-run; --apply is the only opt-in surface.
    dry_run: bool = not apply_requested or bool(args.dry_run)

    # Gate 1: --apply on any non-apply subcommand stays hard-blocked.
    if command != "apply" and apply_requested:
        raise WriteDeniedError(
            "the --apply flag is only valid on the `apply` subcommand; "
            "use of --apply on other subcommands is hard-blocked"
        )

    # Gate 2: `apply` subcommand requires the explicit local-dev gate.
    if command == "apply":
        if not apply_requested:
            raise WriteDeniedError(
                "apply subcommand requires --apply to opt in to writes; "
                "no default-write path exists"
            )
        if apply_mode is None:
            raise WriteDeniedError(
                "apply requires --apply-mode local-dev; "
                "no default apply mode is provided"
            )
        if apply_mode not in SUPPORTED_APPLY_MODES:
            raise WriteDeniedError(
                f"unsupported --apply-mode: {apply_mode!r}; "
                f"allowed: {sorted(SUPPORTED_APPLY_MODES)}"
            )
        if args.config is None:
            raise WriteDeniedError(
                "apply requires --config <path> (explicit local config)"
            )
        if args.input_dir is None:
            raise WriteDeniedError(
                "apply requires --input-dir <dir>"
            )
        if not args.run_id:
            raise WriteDeniedError(
                "apply requires --run-id <str> for deterministic auditability"
            )

        _validate_format(args.format)
        report_output = _validate_output_path(args.report_output)
        audit_output = _validate_output_path(args.audit_output)
        config = load_config(args.config)
        input_dir = _validate_input_dir(args.input_dir)
        plan = build_import_plan(input_dir, args.run_id)
        existing_records = load_existing_records(
            None if plan.has_blocking_validation_findings else args.existing_records
        )
        reconcile_report = reconcile_import_plan(plan, existing_records)

        # Adapter selection: CLI flag wins over env var; in-memory is default.
        _adapter_kind = (
            getattr(args, "adapter", None)
            or os.environ.get("CDB_CONTEXT_APPLY_ADAPTER", "")
            or ADAPTER_KIND_IN_MEMORY
        )
        if _adapter_kind == ADAPTER_KIND_SURREALDB_LOCAL:
            _user, _password = _load_surrealdb_credentials(
                config, getattr(args, "secrets_path", None)
            )
            _selected_adapter: ContextApplyAdapter = SurrealDBLocalContextApplyAdapter(
                surreal_url=config.surreal_url,
                namespace=config.namespace,
                database=config.database,
                user=_user,
                password=_password,
                timeout=config.timeout,
            )
        else:
            _selected_adapter = InMemoryContextApplyAdapter()

        apply_report = execute_context_apply(
            reconcile_report=reconcile_report,
            config=config,
            run_id=args.run_id,
            apply_mode=apply_mode,
            adapter=_selected_adapter,
            # NOTE: Do not forward the audit clock here. ``audit_clock`` is the
            # injectable ``--audit-generated-at`` flag and must only influence
            # the audit report's ``generated_at`` field. Forwarding it into
            # ``execute_context_apply`` would let an operator backdate or
            # forward-date applied tombstone payload timestamps
            # (``tombstoned_at``), turning an audit-determinism control into a
            # data-mutation control. Apply payload timestamps stay on the
            # default runtime clock (``SystemClock``) inside
            # ``execute_context_apply``.
        )
        payload = apply_report.to_payload()
        payload["config_loaded"] = True
        payload["config"] = config.to_payload()
        payload["reconcile_summary"] = {
            "status": reconcile_report.status,
            "blocking_count": reconcile_report.blocking_count,
            "warning_count": reconcile_report.warning_count,
            "actions": len(reconcile_report.actions),
        }
        if report_output is not None:
            _write_report(report_output, _render(payload, args.format))
            payload["report_output"] = str(report_output)
        if audit_output is not None:
            audit_report = build_audit_report(
                mode=AUDIT_MODE_APPLY,
                input_dir=input_dir,
                run_id=args.run_id,
                git_commit=args.git_commit,
                namespace=config.namespace,
                database=config.database,
                clock=audit_clock,
                duration_ms=audit_duration_ms,
                reconcile_report=reconcile_report,
                apply_report=apply_report,
            )
            _write_audit_outputs(audit_output, audit_report)
            payload["audit_output"] = str(audit_output)
            payload["audit_markdown_output"] = str(_audit_markdown_path(audit_output))

        if apply_report.blocking_findings_present:
            return payload, EXIT_VALIDATION_ERROR
        if any(r.status == "failed" for r in apply_report.results):
            return payload, EXIT_INTERNAL
        if any(r.status == "blocked" for r in apply_report.results):
            return payload, EXIT_WRITE_DENIED
        return payload, EXIT_OK

    # Validate format and output path defensively even though we do not
    # write. This makes the safety contract verifiable from tests.
    _validate_format(args.format)
    report_output = _validate_output_path(args.report_output)
    audit_output = _validate_output_path(args.audit_output)
    config = load_config(args.config) if args.config is not None else None

    if command == "validate-jsonl":
        input_dir = _validate_input_dir(args.input_dir)
        report = validate_jsonl(input_dir, args.run_id)
        payload = report.to_payload()
        payload["config_loaded"] = config is not None
        if config is not None:
            payload["config"] = config.to_payload()
        if report_output is not None:
            _write_report(report_output, _render_jsonl_report(report, args.format))
            payload["report_output"] = str(report_output)
        return payload, EXIT_VALIDATION_ERROR if report.blocking_count else EXIT_OK

    if command == "plan" and args.input_dir is not None:
        input_dir = _validate_input_dir(args.input_dir)
        plan = build_import_plan(input_dir, args.run_id)
        payload = plan.to_payload()
        payload["config_loaded"] = config is not None
        if config is not None:
            payload["config"] = config.to_payload()
        if report_output is not None:
            _write_report(report_output, _render(payload, args.format))
            payload["report_output"] = str(report_output)
        if audit_output is not None:
            audit_report = build_audit_report(
                mode=AUDIT_MODE_PLAN,
                input_dir=input_dir,
                run_id=plan.run_id,
                git_commit=args.git_commit,
                namespace=args.namespace or (config.namespace if config is not None else None),
                database=args.database or (config.database if config is not None else None),
                clock=audit_clock,
                duration_ms=audit_duration_ms,
                plan=plan,
            )
            _write_audit_outputs(audit_output, audit_report)
            payload["audit_output"] = str(audit_output)
            payload["audit_markdown_output"] = str(_audit_markdown_path(audit_output))
        return payload, (
            EXIT_VALIDATION_ERROR if plan.has_blocking_validation_findings else EXIT_OK
        )

    if command == "dry-run" and args.input_dir is not None:
        input_dir = _validate_input_dir(args.input_dir)
        plan = build_import_plan(input_dir, args.run_id)
        existing_records = load_existing_records(
            None if plan.has_blocking_validation_findings else args.existing_records
        )
        report = reconcile_import_plan(plan, existing_records)
        payload = report.to_payload()
        payload["config_loaded"] = config is not None
        if config is not None:
            payload["config"] = config.to_payload()
        if report_output is not None:
            _write_report(report_output, _render(payload, args.format))
            payload["report_output"] = str(report_output)
        if audit_output is not None:
            audit_report = build_audit_report(
                mode=AUDIT_MODE_DRY_RUN,
                input_dir=input_dir,
                run_id=report.run_id,
                git_commit=args.git_commit,
                namespace=args.namespace or (config.namespace if config is not None else None),
                database=args.database or (config.database if config is not None else None),
                clock=audit_clock,
                duration_ms=audit_duration_ms,
                reconcile_report=report,
            )
            _write_audit_outputs(audit_output, audit_report)
            payload["audit_output"] = str(audit_output)
            payload["audit_markdown_output"] = str(_audit_markdown_path(audit_output))
        return payload, EXIT_VALIDATION_ERROR if report.blocking_count else EXIT_OK

    if command == "audit":
        if args.input_dir is None:
            payload = _build_payload(
                command,
                dry_run=dry_run,
                apply_requested=apply_requested,
                config=config,
                status="scaffold-ack",
                note="audit requires --input-dir for implemented audit report generation.",
            )
            return payload, EXIT_OK
        input_dir = _validate_input_dir(args.input_dir)
        audit_mode = args.audit_mode or AUDIT_MODE_DRY_RUN
        namespace = args.namespace or (config.namespace if config is not None else None)
        database = args.database or (config.database if config is not None else None)
        if audit_mode == AUDIT_MODE_PLAN:
            plan = build_import_plan(input_dir, args.run_id)
            audit_report = build_audit_report(
                mode=AUDIT_MODE_PLAN,
                input_dir=input_dir,
                run_id=plan.run_id,
                git_commit=args.git_commit,
                namespace=namespace,
                database=database,
                clock=audit_clock,
                duration_ms=audit_duration_ms,
                plan=plan,
            )
        elif audit_mode == AUDIT_MODE_DRY_RUN:
            plan = build_import_plan(input_dir, args.run_id)
            existing_records = load_existing_records(
                None if plan.has_blocking_validation_findings else args.existing_records
            )
            reconcile_report = reconcile_import_plan(plan, existing_records)
            audit_report = build_audit_report(
                mode=AUDIT_MODE_DRY_RUN,
                input_dir=input_dir,
                run_id=reconcile_report.run_id,
                git_commit=args.git_commit,
                namespace=namespace,
                database=database,
                clock=audit_clock,
                duration_ms=audit_duration_ms,
                reconcile_report=reconcile_report,
            )
        else:
            raise WriteDeniedError(
                "audit --audit-mode apply is not a write entrypoint; "
                "use `apply --apply --apply-mode local-dev ... --audit-output <path>`"
            )
        if audit_output is not None:
            _write_audit_outputs(audit_output, audit_report)
        payload = audit_report.to_payload()
        if audit_output is not None:
            payload["audit_output"] = str(audit_output)
            payload["audit_markdown_output"] = str(_audit_markdown_path(audit_output))
        return payload, EXIT_VALIDATION_ERROR if payload["blocking_findings"] else EXIT_OK

    payload = _build_payload(
        command,
        dry_run=dry_run,
        apply_requested=apply_requested,
        config=config,
        status="scaffold-ack",
        note=(
            "scaffold only; optional local config validation only; "
            "no JSONL parsing, no SurrealDB connection, no writes performed."
        ),
    )
    return payload, EXIT_OK


def _emit_error(exc: ContextImporterError) -> str:
    return json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "error": exc.code,
            "message": exc.message,
        },
        ensure_ascii=True,
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        payload, exit_code = _handle(args)
    except ContextImporterError as exc:
        print(_emit_error(exc))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - scaffold safety net
        logger.exception("context_importer internal error")
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "error": "INTERNAL",
                    "message": str(exc),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return EXIT_INTERNAL

    try:
        rendered = _render(payload, args.format)
    except ContextImporterError as exc:
        print(_emit_error(exc))
        return exc.exit_code

    print(rendered)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
