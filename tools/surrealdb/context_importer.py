"""SurrealDB context importer CLI scaffold (offline, dry-run by default).

Issue: #2068 (Wave 10, Slice 1)
Parent: #2067 / Epic #1976

This module implements the offline CLI scaffold for the future
context-import pipeline plus the read-only JSONL validation slice.
It is hard-blocked from performing any SurrealDB operation.

Design rules enforced here:

* Default behavior is dry-run / no-write.
* The ``apply`` subcommand and the global ``--apply`` flag exist
  so that downstream slices can wire real behavior, but in this
  scaffold any apply attempt is hard-blocked with exit code 5
  (``WRITE_DENIED``) and a deterministic error payload.
* No SurrealDB connection is opened. ``--surreal-url``,
  ``--namespace``, and ``--database`` are parsed but never used.
* No config loader is invoked (that belongs to #2069).
* No real plan / audit / rollback-plan logic exists.

Subcommands implemented as scaffold stubs (per #2068 spec):
    validate-jsonl, plan, dry-run, apply, audit, rollback-plan

Exit codes (aligned with the context-indexer contract):
    0 = success / scaffold acknowledged
    1 = validation failure (reserved; not raised in scaffold)
    2 = argparse usage error (raised by argparse itself)
    3 = input-not-found (reserved; not raised in scaffold)
    4 = unsupported format
    5 = write denied (path violation OR apply attempt in scaffold)
    6 = internal error / scaffold anomaly
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any

import yaml

logger = logging.getLogger(__name__)


SCHEMA_VERSION = "context-importer/v0"

SUPPORTED_COMMANDS = (
    "validate-jsonl",
    "plan",
    "dry-run",
    "apply",
    "audit",
    "rollback-plan",
)

SUPPORTED_FORMATS = frozenset({"json", "jsonl", "markdown"})

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
ALLOWED_CONTEXT_IMPORT_TABLES = frozenset(TABLE_BY_ARTIFACT.values())

ALLOWED_AUTH_MODES = frozenset({"none", "root", "scope"})

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
    return ExistingRecord(
        table=table,
        record_id=record_id,
        payload_hash=payload_hash,
        schema_version=schema_version,
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


def build_import_plan(
    input_dir: Path, expected_run_id: str | None = None
) -> ImportPlan:
    report = validate_jsonl(input_dir, expected_run_id)
    if report.blocking_count:
        warnings = tuple(
            ImportPlanWarning(
                code=finding.code,
                message=finding.message,
                artifact=finding.artifact,
                source_ref=finding.source_path,
                severity=finding.severity,
            )
            for finding in report.findings
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
    warnings: list[ImportPlanWarning] = []
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
                "Opt in to write/apply. HARD-BLOCKED in #2068; any use of "
                "this flag exits with code 5 (WRITE_DENIED)."
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
    """Resolve command behavior for the scaffold.

    Returns ``(payload, exit_code)``. The scaffold never performs the
    real action; it only acknowledges the call or refuses it.
    """

    command: str = args.command
    apply_requested: bool = bool(args.apply)
    # Default is dry-run; --apply is the only opt-in surface.
    dry_run: bool = not apply_requested or bool(args.dry_run)

    if command == "apply" or apply_requested:
        raise WriteDeniedError(
            "apply path is not implemented in scaffold (#2068); "
            "writes will land in a follow-up slice."
        )

    # Validate format and output path defensively even though we do not
    # write. This makes the safety contract verifiable from tests.
    _validate_format(args.format)
    report_output = _validate_output_path(args.report_output)
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
        return payload, EXIT_VALIDATION_ERROR if report.blocking_count else EXIT_OK

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
