"""Offline Context Indexer for Wave 8 dry-run exports.

The indexer is intentionally local-only: it never connects to SurrealDB and it
does not mutate runtime, trading, risk, execution, or live-readiness state.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.utils.clock import utcnow as cdb_utcnow


SCHEMA_VERSION = "context-indexer/v0"
SCOPE_CONFIG_SCHEMA_VERSION = "context-ingestion-scope/v0"
DEFAULT_SCOPE_CONFIG = Path(
    "infrastructure/config/surrealdb/context_ingestion_scope.yaml"
)
REQUIRED_SCOPE_KEYS = {
    "schema_version",
    "include_paths",
    "conditional_paths",
    "exclude_paths",
    "allowed_file_types",
    "sensitivity_classes",
    "forbidden_patterns",
    "limits",
    "guardrails",
}
EXPECTED_SENSITIVITY_CLASSES = {
    "public_context",
    "internal_context",
    "sensitive_metadata",
    "forbidden",
}
SUPPORTED_FORMATS = {"json", "jsonl", "markdown", "text"}
APPROVED_OUTPUT_ROOTS = ("artifacts", "temp")
DEFAULT_MAX_CHUNK_CHARS = 4000

EXPORT_FILES = {
    "repo_artifacts": "repo_artifacts.jsonl",
    "doc_pages": "doc_pages.jsonl",
    "doc_sections": "doc_sections.jsonl",
    "doc_chunks": "doc_chunks.jsonl",
    "skipped_files": "skipped_files.jsonl",
    "forbidden_files": "forbidden_files.jsonl",
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

EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_NOT_FOUND = 3
EXIT_UNSUPPORTED_FORMAT = 4
EXIT_WRITE_DENIED = 5
EXIT_INTERNAL_ERROR = 6

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HIGH_CONFIDENCE_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|private[_-]?key|password|passwd|secret|token|credential)"
    r"\b\s*[:=]\s*[\"']?[A-Za-z0-9_.+/=@:-]{12,}"
)
AWS_ACCESS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
TRADING_STATE_PATH_PARTS = {
    "orders",
    "positions",
    "fills",
    "balances",
    "exposures",
    "live_risk_state",
    "broker_state",
    "execution_state",
}

KNOWN_LOCAL_MODULE_PREFIXES: frozenset[str] = frozenset({
    "core", "services", "tools", "infrastructure", "tests"
})
SECRET_CONFIG_KEY_RE = re.compile(
    r"(?i)(api[_\-]?key|private[_\-]?key|password|passwd|secret|token|credential"
    r"|auth[_\-]?key|access[_\-]?key|signing[_\-]?key|encryption[_\-]?key)"
)
BACKTICK_SYMBOL_RE = re.compile(r"`([A-Za-z_]\w*(?:\.\w+)*)`")


class ContextIndexerError(Exception):
    """Base error that maps to a stable CLI exit code."""

    exit_code = EXIT_INTERNAL_ERROR
    code = "internal_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ScopeConfigNotFoundError(ContextIndexerError):
    exit_code = EXIT_INPUT_NOT_FOUND
    code = "scope_config_not_found"


class ScopeConfigValidationError(ContextIndexerError):
    exit_code = EXIT_VALIDATION_ERROR
    code = "scope_config_invalid"


class RootNotFoundError(ContextIndexerError):
    exit_code = EXIT_INPUT_NOT_FOUND
    code = "root_not_found"


class UnsupportedFormatError(ContextIndexerError):
    exit_code = EXIT_UNSUPPORTED_FORMAT
    code = "unsupported_format"


class WriteDeniedError(ContextIndexerError):
    exit_code = EXIT_WRITE_DENIED
    code = "write_denied"


class OutputPathOutsideAllowedRootsError(WriteDeniedError):
    code = "output_path_outside_allowed_roots"


class OutputWriteError(ContextIndexerError):
    exit_code = EXIT_WRITE_DENIED
    code = "output_write_failed"


@dataclass(frozen=True)
class PathRule:
    path: str
    sensitivity_class: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class FileTypeRule:
    file_type: str
    extension: str | None = None
    pattern: str | None = None


@dataclass(frozen=True)
class ScopeConfigSummary:
    path: str
    schema_version: str
    include_paths: list[str]
    conditional_paths: list[str]
    exclude_paths: list[str]
    sensitivity_classes: list[str]
    include_rules: list[PathRule]
    conditional_rules: list[PathRule]
    exclude_rules: list[PathRule]
    file_type_rules: list[FileTypeRule]
    forbidden_patterns: list[str]
    max_file_size_bytes: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "schema_version": self.schema_version,
            "include_paths": self.include_paths,
            "conditional_paths": self.conditional_paths,
            "exclude_paths": self.exclude_paths,
            "sensitivity_classes": self.sensitivity_classes,
            "max_file_size_bytes": self.max_file_size_bytes,
        }


@dataclass(frozen=True)
class FileRecord:
    source_path: str
    file_type: str | None
    sensitivity: str
    size_bytes: int
    status: str
    reason: str

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "path": self.source_path,
            "source_path": self.source_path,
            "file_type": self.file_type,
            "sensitivity": self.sensitivity,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RepoArtifact:
    artifact_id: str
    source_path: str
    file_type: str
    raw_sha256: str
    normalized_sha256: str
    size_bytes: int
    git_commit: str | None
    observed_at: str
    sensitivity: str

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "artifact_id": self.artifact_id,
            "source_path": self.source_path,
            "file_type": self.file_type,
            "raw_sha256": self.raw_sha256,
            "normalized_sha256": self.normalized_sha256,
            "source_hash": self.normalized_sha256,
            "integrity_algo": "sha256",
            "size_bytes": self.size_bytes,
            "git_commit": self.git_commit,
            "observed_at": self.observed_at,
            "sensitivity": self.sensitivity,
        }

    def to_state_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "source_path": self.source_path,
            "file_type": self.file_type,
            "raw_sha256": self.raw_sha256,
            "normalized_sha256": self.normalized_sha256,
            "size_bytes": self.size_bytes,
            "sensitivity": self.sensitivity,
        }


@dataclass(frozen=True)
class DocPage:
    page_id: str
    source_path: str
    source_hash: str
    title: str
    doc_format: str
    git_commit: str | None
    observed_at: str
    sensitivity: str

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "page_id": self.page_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "title": self.title,
            "doc_format": self.doc_format,
            "git_commit": self.git_commit,
            "observed_at": self.observed_at,
            "sensitivity": self.sensitivity,
        }


@dataclass(frozen=True)
class DocSection:
    section_id: str
    page_id: str
    source_path: str
    source_hash: str
    heading: str
    heading_path: list[str]
    section_level: int
    section_index: int
    span_start_line: int
    span_end_line: int

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "section_id": self.section_id,
            "page_id": self.page_id,
            "page_ref": f"doc_page:{self.page_id}",
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "heading": self.heading,
            "heading_path": self.heading_path,
            "section_level": self.section_level,
            "section_index": self.section_index,
            "span_start_line": self.span_start_line,
            "span_end_line": self.span_end_line,
        }


@dataclass(frozen=True)
class DocChunk:
    chunk_id: str
    page_id: str
    section_id: str
    source_path: str
    source_hash: str
    heading_path: list[str]
    chunk_index: int
    content: str
    content_hash: str
    previous_chunk_id: str | None
    next_chunk_id: str | None

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "chunk_id": self.chunk_id,
            "page_id": self.page_id,
            "page_ref": f"doc_page:{self.page_id}",
            "section_id": self.section_id,
            "section_ref": f"doc_section:{self.section_id}",
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "heading_path": self.heading_path,
            "chunk_index": self.chunk_index,
            "previous_chunk_id": self.previous_chunk_id,
            "next_chunk_id": self.next_chunk_id,
            "content": self.content,
            "content_hash": self.content_hash,
            "tokens_estimate": estimate_tokens(self.content),
        }

    def to_state_payload(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "section_id": self.section_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "chunk_index": self.chunk_index,
        }


@dataclass(frozen=True)
class ValidationFinding:
    severity: str
    code: str
    message: str
    source_path: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.source_path is not None:
            payload["source_path"] = self.source_path
        return payload


@dataclass(frozen=True)
class AstParseError:
    source_path: str
    error_message: str
    error_type: str

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "source_path": self.source_path,
            "error_message": self.error_message,
            "error_type": self.error_type,
        }


@dataclass(frozen=True)
class CodeSymbol:
    symbol_id: str
    source_path: str
    source_hash: str
    symbol_type: str
    name: str
    qualified_name: str
    line_start: int
    line_end: int
    decorators: list[str]
    is_async: bool
    parent_class: str | None
    confidence: str
    inferred: bool

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "symbol_id": self.symbol_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "symbol_type": self.symbol_type,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "decorators": self.decorators,
            "is_async": self.is_async,
            "parent_class": self.parent_class,
            "confidence": self.confidence,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class ImportReference:
    import_id: str
    source_path: str
    source_hash: str
    module: str
    alias: str | None
    imported_names: list[str]
    import_type: str
    locality: str
    line_number: int
    confidence: str
    inferred: bool
    import_level: int = 0  # AST node.level; 0 = absolute, 1+ = relative dots

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "import_id": self.import_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "module": self.module,
            "alias": self.alias,
            "imported_names": self.imported_names,
            "import_type": self.import_type,
            "locality": self.locality,
            "line_number": self.line_number,
            "confidence": self.confidence,
            "inferred": self.inferred,
            "import_level": self.import_level,
        }


@dataclass(frozen=True)
class TestCase:
    test_id: str
    source_path: str
    source_hash: str
    symbol_id: str
    name: str
    qualified_name: str
    line_start: int
    line_end: int
    test_type: str
    parent_class: str | None
    confidence: str
    inferred: bool

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "test_id": self.test_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "symbol_id": self.symbol_id,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "test_type": self.test_type,
            "parent_class": self.parent_class,
            "confidence": self.confidence,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class ConfigReference:
    config_ref_id: str
    source_path: str
    source_hash: str
    config_key: str
    config_value: str
    sensitive: bool
    line_number: int
    config_format: str
    confidence: str
    inferred: bool

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "config_ref_id": self.config_ref_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "config_key": self.config_key,
            "config_value": self.config_value,
            "sensitive": self.sensitive,
            "line_number": self.line_number,
            "config_format": self.config_format,
            "confidence": self.confidence,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class DocCodeLink:
    link_id: str
    source_path: str
    source_hash: str
    target_symbol: str
    source_chunk_id: str | None
    confidence: str
    inferred: bool

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "link_id": self.link_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "target_symbol": self.target_symbol,
            "source_chunk_id": self.source_chunk_id,
            "confidence": self.confidence,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class DependencyEdge:
    edge_id: str
    from_id: str
    to_id: str
    edge_type: str
    source_path: str | None
    confidence: str
    inferred: bool

    def to_payload(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "edge_id": self.edge_id,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "edge_type": self.edge_type,
            "source_path": self.source_path,
            "confidence": self.confidence,
            "inferred": self.inferred,
        }


@dataclass(frozen=True)
class IndexerResult:
    root: Path
    scope_config: ScopeConfigSummary
    git_commit: str | None
    generated_at: str
    run_id: str
    state_hash: str
    files: list[FileRecord]
    repo_artifacts: list[RepoArtifact]
    doc_pages: list[DocPage]
    doc_sections: list[DocSection]
    doc_chunks: list[DocChunk]
    validation_findings: list[ValidationFinding]
    ast_parse_errors: list[AstParseError] = field(default_factory=list)
    code_symbols: list[CodeSymbol] = field(default_factory=list)
    import_references: list[ImportReference] = field(default_factory=list)
    test_cases: list[TestCase] = field(default_factory=list)
    config_references: list[ConfigReference] = field(default_factory=list)
    doc_code_links: list[DocCodeLink] = field(default_factory=list)
    dependency_edges: list[DependencyEdge] = field(default_factory=list)

    @property
    def included_files(self) -> list[FileRecord]:
        return [item for item in self.files if item.status == "included"]

    @property
    def skipped_files(self) -> list[FileRecord]:
        return [item for item in self.files if item.status == "skipped"]

    @property
    def forbidden_files(self) -> list[FileRecord]:
        return [item for item in self.files if item.status == "forbidden"]

    @property
    def blocking_findings(self) -> list[ValidationFinding]:
        return [item for item in self.validation_findings if item.severity == "blocking"]


def _path_entries(value: Any, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ScopeConfigValidationError(f"{key} must be a list")
    paths: list[str] = []
    for item in value:
        if not isinstance(item, dict) or not item.get("path"):
            raise ScopeConfigValidationError(f"{key} entries must contain path")
        paths.append(_normalize_config_path(str(item["path"])))
    return sorted(paths)


def _path_rules(value: Any, key: str) -> list[PathRule]:
    if not isinstance(value, list):
        raise ScopeConfigValidationError(f"{key} must be a list")
    rules: list[PathRule] = []
    for item in value:
        if not isinstance(item, dict) or not item.get("path"):
            raise ScopeConfigValidationError(f"{key} entries must contain path")
        sensitivity_class = item.get("sensitivity_class")
        if sensitivity_class is not None and sensitivity_class not in EXPECTED_SENSITIVITY_CLASSES:
            raise ScopeConfigValidationError(
                f"{key} entry has unsupported sensitivity_class: {sensitivity_class}"
            )
        rules.append(
            PathRule(
                path=_normalize_config_path(str(item["path"])),
                sensitivity_class=str(sensitivity_class) if sensitivity_class else None,
                reason=str(item.get("reason")) if item.get("reason") else None,
            )
        )
    return sorted(rules, key=lambda rule: rule.path)


def _file_type_rules(value: Any) -> list[FileTypeRule]:
    if not isinstance(value, list):
        raise ScopeConfigValidationError("allowed_file_types must be a list")
    rules: list[FileTypeRule] = []
    for item in value:
        if not isinstance(item, dict) or not item.get("type"):
            raise ScopeConfigValidationError("allowed_file_types entries must contain type")
        extension = item.get("extension")
        pattern = item.get("pattern")
        if not extension and not pattern:
            raise ScopeConfigValidationError(
                "allowed_file_types entries must contain extension or pattern"
            )
        rules.append(
            FileTypeRule(
                file_type=str(item["type"]),
                extension=str(extension).lower() if extension else None,
                pattern=str(pattern) if pattern else None,
            )
        )
    return sorted(rules, key=lambda rule: (rule.file_type, rule.extension or rule.pattern or ""))


def _flatten_forbidden_patterns(value: Any) -> list[str]:
    if not isinstance(value, dict):
        raise ScopeConfigValidationError("forbidden_patterns must be a mapping")
    patterns: list[str] = []
    for entries in value.values():
        if not isinstance(entries, list):
            raise ScopeConfigValidationError("forbidden_patterns values must be lists")
        patterns.extend(str(entry) for entry in entries)
    return sorted(patterns)


def load_scope_config(path: Path) -> ScopeConfigSummary:
    if not path.exists():
        raise ScopeConfigNotFoundError(f"scope config not found: {path}")
    if not path.is_file():
        raise ScopeConfigValidationError(f"scope config is not a file: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScopeConfigValidationError(f"scope config read failed: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ScopeConfigValidationError(f"scope config YAML parse failed: {exc}") from exc

    if not isinstance(data, dict):
        raise ScopeConfigValidationError("scope config must be a YAML mapping")

    missing = sorted(REQUIRED_SCOPE_KEYS - set(data))
    if missing:
        raise ScopeConfigValidationError(
            f"scope config missing required keys: {', '.join(missing)}"
        )

    schema_version = data.get("schema_version")
    if schema_version != SCOPE_CONFIG_SCHEMA_VERSION:
        raise ScopeConfigValidationError(
            f"unsupported scope config schema_version: {schema_version}"
        )

    sensitivity_classes = data.get("sensitivity_classes")
    if not isinstance(sensitivity_classes, dict):
        raise ScopeConfigValidationError("sensitivity_classes must be a mapping")
    found_classes = set(str(key) for key in sensitivity_classes)
    if found_classes != EXPECTED_SENSITIVITY_CLASSES:
        expected = ", ".join(sorted(EXPECTED_SENSITIVITY_CLASSES))
        found = ", ".join(sorted(found_classes))
        raise ScopeConfigValidationError(
            f"sensitivity classes mismatch: expected {expected}; found {found}"
        )

    limits = data.get("limits")
    if not isinstance(limits, dict):
        raise ScopeConfigValidationError("limits must be a mapping")
    max_file_size_bytes = limits.get("max_file_size_bytes")
    if not isinstance(max_file_size_bytes, int) or max_file_size_bytes <= 0:
        raise ScopeConfigValidationError("limits.max_file_size_bytes must be positive")

    include_rules = _path_rules(data["include_paths"], "include_paths")
    conditional_rules = _path_rules(data["conditional_paths"], "conditional_paths")
    exclude_rules = _path_rules(data["exclude_paths"], "exclude_paths")

    return ScopeConfigSummary(
        path=path.as_posix(),
        schema_version=str(schema_version),
        include_paths=_path_entries(data["include_paths"], "include_paths"),
        conditional_paths=_path_entries(data["conditional_paths"], "conditional_paths"),
        exclude_paths=_path_entries(data["exclude_paths"], "exclude_paths"),
        sensitivity_classes=sorted(found_classes),
        include_rules=include_rules,
        conditional_rules=conditional_rules,
        exclude_rules=exclude_rules,
        file_type_rules=_file_type_rules(data["allowed_file_types"]),
        forbidden_patterns=_flatten_forbidden_patterns(data["forbidden_patterns"]),
        max_file_size_bytes=max_file_size_bytes,
    )


def _normalize_config_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def _normalize_relative_path(path: Path) -> str:
    return path.as_posix().lstrip("./")


def _has_glob_magic(value: str) -> bool:
    return any(char in value for char in "*?[")


def _matches_rule(rel_path: str, rule_path: str) -> bool:
    rule = rule_path.strip()
    normalized_rule = rule.strip("/")
    normalized_rel = rel_path.strip("/")
    if _has_glob_magic(rule):
        return fnmatch.fnmatchcase(normalized_rel, normalized_rule) or fnmatch.fnmatchcase(
            Path(normalized_rel).name, normalized_rule
        )
    return normalized_rel == normalized_rule or normalized_rel.startswith(
        f"{normalized_rule}/"
    )


def _iter_rule_files(root: Path, rule_path: str) -> list[Path]:
    rule = rule_path.strip("/")
    if _has_glob_magic(rule):
        candidates = root.glob(rule)
    else:
        target = root / rule
        if target.is_file():
            return [target]
        if not target.exists() or not target.is_dir():
            return []
        candidates = target.rglob("*")
    return sorted(path for path in candidates if path.is_file())


def _safe_relative_to_root(path: Path, root: Path) -> str | None:
    try:
        resolved = path.resolve(strict=True)
        rel = resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    return _normalize_relative_path(rel)


def _detect_file_type(rel_path: str, path: Path, scope: ScopeConfigSummary) -> str | None:
    name = path.name
    suffix = path.suffix.lower()
    for rule in scope.file_type_rules:
        if rule.pattern and (
            fnmatch.fnmatchcase(name, rule.pattern)
            or fnmatch.fnmatchcase(rel_path, rule.pattern)
        ):
            return rule.file_type
        if rule.extension and suffix == rule.extension:
            return rule.file_type
    return None


def _matched_exclude_rule(rel_path: str, scope: ScopeConfigSummary) -> PathRule | None:
    matches = [rule for rule in scope.exclude_rules if _matches_rule(rel_path, rule.path)]
    if not matches:
        return None
    return max(matches, key=lambda rule: len(rule.path))


def _matched_include_rule(rel_path: str, scope: ScopeConfigSummary) -> PathRule | None:
    rules = scope.include_rules + scope.conditional_rules
    matches = [rule for rule in rules if _matches_rule(rel_path, rule.path)]
    if not matches:
        return None
    return max(matches, key=lambda rule: len(rule.path))


def _contains_high_confidence_secret(text: str) -> bool:
    return bool(
        HIGH_CONFIDENCE_SECRET_RE.search(text)
        or AWS_ACCESS_KEY_RE.search(text)
        or PRIVATE_KEY_RE.search(text)
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_json_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return _sha256_text(encoded)


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{_stable_json_hash([SCHEMA_VERSION, prefix, *parts])}"


def normalize_text(raw: bytes) -> str:
    text = raw.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def estimate_tokens(content: str) -> int:
    return max(1, len(content.split())) if content else 0


def _git_value(root: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def current_git_commit(root: Path) -> str | None:
    return _git_value(root, ["rev-parse", "HEAD"])


def current_git_commit_timestamp(root: Path) -> str | None:
    return _git_value(root, ["show", "-s", "--format=%cI", "HEAD"])


def _utc_now() -> str:
    dt = cdb_utcnow().replace(microsecond=0)
    iso = dt.isoformat().replace("+00:00", "")
    return iso if iso.endswith("Z") else iso + "Z"


def _resolve_existing_root(path: Path) -> Path:
    if not path.exists():
        raise RootNotFoundError(f"root not found: {path}")
    if not path.is_dir():
        raise RootNotFoundError(f"root is not a directory: {path}")
    return path.resolve()


def resolve_input_path(path: Path, root: Path) -> Path:
    if path.is_absolute():
        return path
    root_path = (root / path).resolve(strict=False)
    if root_path.exists():
        return root_path
    cwd_path = (Path.cwd() / path).resolve(strict=False)
    if cwd_path.exists():
        return cwd_path
    return root_path


def validate_output_path(output: Path | None, apply_writes: bool) -> Path | None:
    if not apply_writes:
        return output
    normalized = _validate_repo_output_base(output)
    if len(normalized.parts) == 1 or normalized.suffix == "":
        raise WriteDeniedError("output must include a file name under an approved root")
    return normalized


def validate_output_directory(output: Path | None, apply_writes: bool) -> Path | None:
    if not apply_writes:
        return output
    normalized = _validate_repo_output_base(output)
    if len(normalized.parts) == 1:
        raise WriteDeniedError("output directory must be below an approved root")
    if normalized.suffix:
        raise WriteDeniedError("output directory must not include a file suffix")
    return normalized


def _validate_repo_output_base(output: Path | None) -> Path:
    if output is None:
        raise WriteDeniedError("writes require an explicit --output path")
    if output.is_absolute() or output.drive or str(output).startswith("\\\\"):
        raise WriteDeniedError("output must be a repo-relative path")

    normalized = Path(*output.parts)
    if ".." in normalized.parts:
        raise WriteDeniedError("output path traversal is not allowed")
    if not normalized.parts or normalized.parts[0] not in APPROVED_OUTPUT_ROOTS:
        approved = ", ".join(f"{root}/" for root in APPROVED_OUTPUT_ROOTS)
        raise WriteDeniedError(f"output must be under one of: {approved}")

    repo_root = Path.cwd().resolve()
    approved_root = repo_root / normalized.parts[0]
    resolved_approved_root = approved_root.resolve(strict=False)
    resolved_output = (repo_root / normalized).resolve(strict=False)
    try:
        if resolved_approved_root != approved_root:
            raise OutputPathOutsideAllowedRootsError(
                "approved output root must remain anchored under the repository"
            )
        resolved_approved_root.relative_to(repo_root)
        resolved_output.relative_to(resolved_approved_root)
    except ValueError as exc:
        raise OutputPathOutsideAllowedRootsError(
            "output path must resolve under a repo-local approved root"
        ) from exc
    return normalized


def discover_paths(root: Path, scope: ScopeConfigSummary) -> list[Path]:
    candidates: dict[str, Path] = {}
    for rule in scope.include_rules + scope.conditional_rules:
        for path in _iter_rule_files(root, rule.path):
            rel_path = _safe_relative_to_root(path, root)
            if rel_path is not None:
                candidates[rel_path] = path
    return [candidates[key] for key in sorted(candidates)]


def classify_and_hash_files(
    root: Path,
    scope: ScopeConfigSummary,
    git_commit: str | None,
    observed_at: str,
) -> tuple[list[FileRecord], list[RepoArtifact], dict[str, str]]:
    files: list[FileRecord] = []
    artifacts: list[RepoArtifact] = []
    normalized_text_by_path: dict[str, str] = {}

    for path in discover_paths(root, scope):
        rel_path = _safe_relative_to_root(path, root)
        if rel_path is None:
            files.append(
                FileRecord(
                    source_path=_normalize_relative_path(path),
                    file_type=None,
                    sensitivity="forbidden",
                    size_bytes=0,
                    status="forbidden",
                    reason="path_resolves_outside_root",
                )
            )
            continue

        exclude_rule = _matched_exclude_rule(rel_path, scope)
        if exclude_rule is not None:
            files.append(
                FileRecord(
                    source_path=rel_path,
                    file_type=None,
                    sensitivity="forbidden",
                    size_bytes=_safe_file_size(path),
                    status="forbidden",
                    reason=exclude_rule.reason or "excluded_by_scope",
                )
            )
            continue

        include_rule = _matched_include_rule(rel_path, scope)
        if include_rule is None:
            files.append(
                FileRecord(
                    source_path=rel_path,
                    file_type=None,
                    sensitivity="forbidden",
                    size_bytes=_safe_file_size(path),
                    status="forbidden",
                    reason="not_in_scope",
                )
            )
            continue

        file_type = _detect_file_type(rel_path, path, scope)
        size_bytes = _safe_file_size(path)
        sensitivity = include_rule.sensitivity_class or "internal_context"

        if file_type is None:
            files.append(
                FileRecord(
                    source_path=rel_path,
                    file_type=None,
                    sensitivity=sensitivity,
                    size_bytes=size_bytes,
                    status="skipped",
                    reason="unsupported_file_type",
                )
            )
            continue

        if size_bytes > scope.max_file_size_bytes:
            files.append(
                FileRecord(
                    source_path=rel_path,
                    file_type=file_type,
                    sensitivity=sensitivity,
                    size_bytes=size_bytes,
                    status="skipped",
                    reason="max_file_size_exceeded",
                )
            )
            continue

        try:
            raw = path.read_bytes()
            normalized_text = normalize_text(raw)
        except (OSError, UnicodeDecodeError):
            files.append(
                FileRecord(
                    source_path=rel_path,
                    file_type=file_type,
                    sensitivity=sensitivity,
                    size_bytes=size_bytes,
                    status="skipped",
                    reason="non_utf8_or_unreadable",
                )
            )
            continue

        if _contains_high_confidence_secret(normalized_text):
            files.append(
                FileRecord(
                    source_path=rel_path,
                    file_type=file_type,
                    sensitivity="forbidden",
                    size_bytes=size_bytes,
                    status="forbidden",
                    reason="content_forbidden_pattern",
                )
            )
            continue

        raw_sha256 = _sha256_bytes(raw)
        normalized_sha256 = _sha256_text(normalized_text)
        artifact_id = stable_id("repo_artifact", rel_path, normalized_sha256)
        files.append(
            FileRecord(
                source_path=rel_path,
                file_type=file_type,
                sensitivity=sensitivity,
                size_bytes=size_bytes,
                status="included",
                reason="included_by_scope",
            )
        )
        artifacts.append(
            RepoArtifact(
                artifact_id=artifact_id,
                source_path=rel_path,
                file_type=file_type,
                raw_sha256=raw_sha256,
                normalized_sha256=normalized_sha256,
                size_bytes=size_bytes,
                git_commit=git_commit,
                observed_at=observed_at,
                sensitivity=sensitivity,
            )
        )
        normalized_text_by_path[rel_path] = normalized_text

    return files, sorted(artifacts, key=lambda item: item.source_path), normalized_text_by_path


def _safe_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


@dataclass(frozen=True)
class ParsedSection:
    heading: str
    heading_path: list[str]
    section_level: int
    section_index: int
    span_start_line: int
    span_end_line: int
    lines: list[str]


def _parse_markdown_sections(text: str) -> list[ParsedSection]:
    lines = text.split("\n")
    sections: list[ParsedSection] = []
    current_heading = ""
    current_heading_path: list[str] = []
    current_level = 0
    current_start = 1
    current_lines: list[str] = []
    heading_stack: list[str] = []
    in_fence = False

    def finalize(end_line: int) -> None:
        if not current_lines:
            return
        sections.append(
            ParsedSection(
                heading=current_heading,
                heading_path=list(current_heading_path),
                section_level=current_level,
                section_index=len(sections),
                span_start_line=current_start,
                span_end_line=end_line,
                lines=list(current_lines),
            )
        )

    for line_number, line in enumerate(lines, start=1):
        heading_match = None if in_fence else HEADING_RE.match(line)
        if heading_match is not None:
            finalize(line_number - 1)
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(heading)
            current_heading = heading
            current_heading_path = list(heading_stack)
            current_level = level
            current_start = line_number
            current_lines = [line]
        else:
            if not current_lines:
                current_start = line_number
            current_lines.append(line)

        if FENCE_RE.match(line):
            in_fence = not in_fence

    finalize(len(lines))
    return sections


def _split_lines_for_chunks(lines: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        add_len = len(line) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            chunks.append("\n".join(current).strip("\n"))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += add_len
    if current:
        chunks.append("\n".join(current).strip("\n"))
    return [chunk for chunk in chunks if chunk]


def build_markdown_records(
    artifacts: list[RepoArtifact],
    normalized_text_by_path: dict[str, str],
) -> tuple[list[DocPage], list[DocSection], list[DocChunk]]:
    pages: list[DocPage] = []
    sections: list[DocSection] = []
    chunks_without_links: list[DocChunk] = []

    for artifact in artifacts:
        if artifact.file_type != "markdown" or artifact.sensitivity == "sensitive_metadata":
            continue
        text = normalized_text_by_path.get(artifact.source_path)
        if text is None:
            continue
        parsed_sections = _parse_markdown_sections(text)
        title = _markdown_title(parsed_sections, artifact.source_path)
        page_id = stable_id("doc_page", artifact.source_path, artifact.normalized_sha256)
        pages.append(
            DocPage(
                page_id=page_id,
                source_path=artifact.source_path,
                source_hash=artifact.normalized_sha256,
                title=title,
                doc_format="markdown",
                git_commit=artifact.git_commit,
                observed_at=artifact.observed_at,
                sensitivity=artifact.sensitivity,
            )
        )

        for parsed_section in parsed_sections:
            section_id = stable_id(
                "doc_section",
                page_id,
                parsed_section.section_index,
                parsed_section.heading_path,
            )
            sections.append(
                DocSection(
                    section_id=section_id,
                    page_id=page_id,
                    source_path=artifact.source_path,
                    source_hash=artifact.normalized_sha256,
                    heading=parsed_section.heading,
                    heading_path=parsed_section.heading_path,
                    section_level=parsed_section.section_level,
                    section_index=parsed_section.section_index,
                    span_start_line=parsed_section.span_start_line,
                    span_end_line=parsed_section.span_end_line,
                )
            )

            section_chunks = _split_lines_for_chunks(
                parsed_section.lines, DEFAULT_MAX_CHUNK_CHARS
            )
            chunk_ids = [
                stable_id("doc_chunk", section_id, index, _sha256_text(content))
                for index, content in enumerate(section_chunks)
            ]
            for index, content in enumerate(section_chunks):
                content_hash = _sha256_text(content)
                chunks_without_links.append(
                    DocChunk(
                        chunk_id=chunk_ids[index],
                        page_id=page_id,
                        section_id=section_id,
                        source_path=artifact.source_path,
                        source_hash=artifact.normalized_sha256,
                        heading_path=parsed_section.heading_path,
                        chunk_index=index,
                        content=content,
                        content_hash=content_hash,
                        previous_chunk_id=chunk_ids[index - 1] if index > 0 else None,
                        next_chunk_id=chunk_ids[index + 1]
                        if index + 1 < len(chunk_ids)
                        else None,
                    )
                )

    return (
        sorted(pages, key=lambda item: item.source_path),
        sorted(sections, key=lambda item: (item.source_path, item.section_index)),
        sorted(chunks_without_links, key=lambda item: (item.source_path, item.chunk_index)),
    )


# ---------------------------------------------------------------------------
# Wave 9: Static Python AST symbol & dependency extraction
# ---------------------------------------------------------------------------


def _parse_python_ast(
    source_path: str, text: str
) -> tuple["ast.Module | None", "AstParseError | None"]:
    """Parse Python source text into an AST; return error record on failure."""
    try:
        tree = ast.parse(text, filename=source_path)
        return tree, None
    except SyntaxError as exc:
        return None, AstParseError(
            source_path=source_path,
            error_message=str(exc),
            error_type="SyntaxError",
        )
    except Exception as exc:  # pragma: no cover — unexpected parser errors
        return None, AstParseError(
            source_path=source_path,
            error_message=str(exc),
            error_type=type(exc).__name__,
        )


def _classify_import_locality(module: str, level: int) -> str:
    """Return 'local' for relative imports or known in-repo root modules."""
    if level > 0:
        return "local"
    root = module.split(".")[0] if module else ""
    return "local" if root in KNOWN_LOCAL_MODULE_PREFIXES else "unknown"


def extract_code_symbols(
    artifact: RepoArtifact, text: str
) -> tuple[list[CodeSymbol], list[AstParseError]]:
    """Extract top-level functions, classes, and their direct methods from a Python file."""
    if artifact.file_type != "python":
        return [], []

    tree, parse_error = _parse_python_ast(artifact.source_path, text)
    if parse_error is not None:
        return [], [parse_error]

    symbols: list[CodeSymbol] = []

    def _add_func(
        node: ast.FunctionDef | ast.AsyncFunctionDef, parent_class: str | None
    ) -> None:
        is_async = isinstance(node, ast.AsyncFunctionDef)
        if parent_class is not None:
            sym_type = "async_method" if is_async else "method"
        else:
            sym_type = "async_function" if is_async else "function"
        qname = f"{parent_class}.{node.name}" if parent_class else node.name
        symbols.append(
            CodeSymbol(
                symbol_id=stable_id("code_symbol", artifact.source_path, qname),
                source_path=artifact.source_path,
                source_hash=artifact.normalized_sha256,
                symbol_type=sym_type,
                name=node.name,
                qualified_name=qname,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                decorators=[ast.unparse(d) for d in node.decorator_list],
                is_async=is_async,
                parent_class=parent_class,
                confidence="high",
                inferred=False,
            )
        )

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _add_func(node, None)
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                CodeSymbol(
                    symbol_id=stable_id("code_symbol", artifact.source_path, node.name),
                    source_path=artifact.source_path,
                    source_hash=artifact.normalized_sha256,
                    symbol_type="class",
                    name=node.name,
                    qualified_name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    decorators=[ast.unparse(d) for d in node.decorator_list],
                    is_async=False,
                    parent_class=None,
                    confidence="high",
                    inferred=False,
                )
            )
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _add_func(child, node.name)

    return sorted(symbols, key=lambda s: s.line_start), []


def extract_import_references(
    artifact: RepoArtifact, text: str
) -> tuple[list[ImportReference], list[AstParseError]]:
    """Extract all import statements from a Python file."""
    if artifact.file_type != "python":
        return [], []

    tree, parse_error = _parse_python_ast(artifact.source_path, text)
    if parse_error is not None:
        return [], [parse_error]

    refs: list[ImportReference] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                locality = _classify_import_locality(module, 0)
                refs.append(
                    ImportReference(
                        import_id=stable_id(
                            "import_ref", artifact.source_path, node.lineno, module
                        ),
                        source_path=artifact.source_path,
                        source_hash=artifact.normalized_sha256,
                        module=module,
                        alias=alias.asname,
                        imported_names=[],
                        import_type="import",
                        locality=locality,
                        line_number=node.lineno,
                        confidence="high",
                        inferred=False,
                        import_level=0,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            locality = _classify_import_locality(module, level)
            imported_names = [alias.name for alias in node.names]
            refs.append(
                ImportReference(
                    import_id=stable_id(
                        "import_ref", artifact.source_path, node.lineno, module, level
                    ),
                    source_path=artifact.source_path,
                    source_hash=artifact.normalized_sha256,
                    module=module,
                    alias=None,
                    imported_names=imported_names,
                    import_type="from_import",
                    locality=locality,
                    line_number=node.lineno,
                    confidence="high",
                    inferred=False,
                    import_level=level,
                )
            )

    return sorted(refs, key=lambda r: r.line_number), []


def extract_test_cases(code_symbols: list[CodeSymbol]) -> list[TestCase]:
    """Derive TestCase records from CodeSymbol records with test naming conventions."""
    test_cases: list[TestCase] = []
    for symbol in code_symbols:
        is_test_func = symbol.name.startswith("test_") and symbol.symbol_type in (
            "function",
            "async_function",
        )
        is_test_method = symbol.name.startswith("test_") and symbol.symbol_type in (
            "method",
            "async_method",
        ) and symbol.parent_class is not None and symbol.parent_class.startswith("Test")
        if is_test_func or is_test_method:
            test_type = "function" if symbol.parent_class is None else "method"
            test_cases.append(
                TestCase(
                    test_id=stable_id(
                        "test_case", symbol.source_path, symbol.qualified_name
                    ),
                    source_path=symbol.source_path,
                    source_hash=symbol.source_hash,
                    symbol_id=symbol.symbol_id,
                    name=symbol.name,
                    qualified_name=symbol.qualified_name,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                    test_type=test_type,
                    parent_class=symbol.parent_class,
                    confidence=symbol.confidence,
                    inferred=symbol.inferred,
                )
            )
    return test_cases


def _flatten_config_dict(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Flatten a nested dict/list into dotted-key value pairs."""
    items: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                items.extend(_flatten_config_dict(v, full_key))
            else:
                items.append((full_key, v))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            full_key = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                items.extend(_flatten_config_dict(v, full_key))
            else:
                items.append((full_key, v))
    return items


def _redact_config_value(key: str, value: Any) -> tuple[str, bool]:
    """Return (display_value, sensitive). Redact values for sensitive keys."""
    str_value = str(value) if value is not None else ""
    if SECRET_CONFIG_KEY_RE.search(key):
        redacted = f"[REDACTED:sha256={_sha256_text(str_value)[:16]}]"
        return redacted, True
    return str_value, False


def extract_config_references(
    artifact: RepoArtifact, text: str
) -> list[ConfigReference]:
    """Extract config key-value pairs from TOML, YAML, or JSON files."""
    fmt = artifact.file_type
    if fmt not in ("toml", "yaml", "json"):
        return []

    data: Any = None
    try:
        if fmt == "toml":
            data = tomllib.loads(text)
        elif fmt == "yaml":
            data = yaml.safe_load(text)
        elif fmt == "json":
            data = json.loads(text)
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    refs: list[ConfigReference] = []
    for config_key, raw_value in _flatten_config_dict(data):
        display_value, sensitive = _redact_config_value(config_key, raw_value)
        refs.append(
            ConfigReference(
                config_ref_id=stable_id("config_ref", artifact.source_path, config_key),
                source_path=artifact.source_path,
                source_hash=artifact.normalized_sha256,
                config_key=config_key,
                config_value=display_value,
                sensitive=sensitive,
                line_number=0,
                config_format=fmt,
                confidence="high",
                inferred=False,
            )
        )
    return refs


def extract_doc_code_links(
    artifacts: list[RepoArtifact],
    normalized_text_by_path: dict[str, str],
) -> list[DocCodeLink]:
    """Extract backtick code references from markdown files."""
    links: list[DocCodeLink] = []
    for artifact in artifacts:
        if artifact.file_type != "markdown":
            continue
        text = normalized_text_by_path.get(artifact.source_path, "")
        seen: set[str] = set()
        for match in BACKTICK_SYMBOL_RE.finditer(text):
            symbol = match.group(1)
            if symbol in seen:
                continue
            seen.add(symbol)
            links.append(
                DocCodeLink(
                    link_id=stable_id("doc_code_link", artifact.source_path, symbol),
                    source_path=artifact.source_path,
                    source_hash=artifact.normalized_sha256,
                    target_symbol=symbol,
                    source_chunk_id=None,
                    confidence="high",
                    inferred=False,
                )
            )
    return sorted(links, key=lambda lnk: (lnk.source_path, lnk.target_symbol))


def derive_dependency_edges(
    artifacts: list[RepoArtifact],
    code_symbols: list[CodeSymbol],
    import_references: list[ImportReference],
    doc_code_links: list[DocCodeLink],
) -> list[DependencyEdge]:
    """Derive contains/imports/documents/mentions dependency edges."""
    edges: list[DependencyEdge] = []

    artifact_by_path: dict[str, RepoArtifact] = {a.source_path: a for a in artifacts}
    symbol_by_qname: dict[str, CodeSymbol] = {s.qualified_name: s for s in code_symbols}

    # "contains": file artifact → code symbol
    for symbol in code_symbols:
        artifact = artifact_by_path.get(symbol.source_path)
        if artifact is None:
            continue
        edges.append(
            DependencyEdge(
                edge_id=stable_id(
                    "dep_edge", "contains", artifact.artifact_id, symbol.symbol_id
                ),
                from_id=artifact.artifact_id,
                to_id=symbol.symbol_id,
                edge_type="contains",
                source_path=symbol.source_path,
                confidence="high",
                inferred=False,
            )
        )

    # "imports": file artifact → imported file artifact or inferred module node
    def _module_to_path(
        module: str, level: int, source_path: str, imported_names: list[str]
    ) -> str | None:
        """Resolve a module reference to an artifact source_path.

        Handles both absolute imports (level=0) and relative imports (level>0).
        For relative imports with module="", tries each name in imported_names
        as a sibling module (e.g. ``from . import sibling``).
        Returns the first matching artifact path, or None if unresolvable.
        """
        if level > 0:
            src_parts = Path(source_path).parent.parts
            n_up = level - 1
            if n_up > len(src_parts):
                return None
            base_parts = src_parts[: len(src_parts) - n_up] if n_up else src_parts
            base = "/".join(base_parts)
            if module:
                mod_rel = module.replace(".", "/")
                # Try each imported name as a submodule first (most specific)
                for name in imported_names:
                    for cand in (
                        f"{base}/{mod_rel}/{name}.py",
                        f"{base}/{mod_rel}/{name}/__init__.py",
                    ):
                        if cand in artifact_by_path:
                            return cand
                # Fall back to the module package itself
                for cand in (f"{base}/{mod_rel}.py", f"{base}/{mod_rel}/__init__.py"):
                    if cand in artifact_by_path:
                        return cand
            else:
                # bare relative: ``from . import name`` — each name is a sibling
                for name in imported_names:
                    for cand in (f"{base}/{name}.py", f"{base}/{name}/__init__.py"):
                        if cand in artifact_by_path:
                            return cand
            return None
        else:
            parts = module.replace(".", "/")
            # Try each imported name as a submodule first (e.g.
            # ``from core.utils import clock`` → core/utils/clock.py)
            for name in imported_names:
                for cand in (
                    f"{parts}/{name}.py",
                    f"{parts}/{name}/__init__.py",
                ):
                    if cand in artifact_by_path:
                        return cand
            # Fall back to the module package itself
            for cand in (f"{parts}.py", f"{parts}/__init__.py"):
                if cand in artifact_by_path:
                    return cand
            return None

    for imp_ref in import_references:
        if imp_ref.locality != "local":
            continue
        src_artifact = artifact_by_path.get(imp_ref.source_path)
        if src_artifact is None:
            continue
        target_path = _module_to_path(
            imp_ref.module,
            imp_ref.import_level,
            imp_ref.source_path,
            imp_ref.imported_names,
        )
        if target_path is not None:
            target_artifact = artifact_by_path[target_path]
            edges.append(
                DependencyEdge(
                    edge_id=stable_id(
                        "dep_edge",
                        "imports",
                        src_artifact.artifact_id,
                        target_artifact.artifact_id,
                    ),
                    from_id=src_artifact.artifact_id,
                    to_id=target_artifact.artifact_id,
                    edge_type="imports",
                    source_path=imp_ref.source_path,
                    confidence="high",
                    inferred=False,
                )
            )
        else:
            module_id = stable_id("module", imp_ref.module)
            edges.append(
                DependencyEdge(
                    edge_id=stable_id(
                        "dep_edge",
                        "imports",
                        src_artifact.artifact_id,
                        module_id,
                    ),
                    from_id=src_artifact.artifact_id,
                    to_id=module_id,
                    edge_type="imports",
                    source_path=imp_ref.source_path,
                    confidence="high",
                    inferred=True,
                )
            )

    # "documents" / "mentions": doc artifact → code symbol
    for link in doc_code_links:
        doc_artifact = artifact_by_path.get(link.source_path)
        if doc_artifact is None:
            continue
        target_symbol = symbol_by_qname.get(link.target_symbol)
        if target_symbol is not None:
            edges.append(
                DependencyEdge(
                    edge_id=stable_id(
                        "dep_edge",
                        "documents",
                        doc_artifact.artifact_id,
                        target_symbol.symbol_id,
                    ),
                    from_id=doc_artifact.artifact_id,
                    to_id=target_symbol.symbol_id,
                    edge_type="documents",
                    source_path=link.source_path,
                    confidence="high",
                    inferred=False,
                )
            )
        else:
            mention_id = stable_id("symbol_mention", link.target_symbol)
            edges.append(
                DependencyEdge(
                    edge_id=stable_id(
                        "dep_edge",
                        "mentions",
                        doc_artifact.artifact_id,
                        mention_id,
                    ),
                    from_id=doc_artifact.artifact_id,
                    to_id=mention_id,
                    edge_type="mentions",
                    source_path=link.source_path,
                    confidence="high",
                    inferred=True,
                )
            )

    return sorted(edges, key=lambda e: (e.edge_type, e.from_id, e.to_id))


def _markdown_title(sections: list[ParsedSection], source_path: str) -> str:
    for section in sections:
        if section.section_level == 1 and section.heading:
            return section.heading
    return Path(source_path).stem


def build_state_hash(
    files: list[FileRecord],
    artifacts: list[RepoArtifact],
    pages: list[DocPage],
    sections: list[DocSection],
    chunks: list[DocChunk],
) -> str:
    return _stable_json_hash(
        {
            "files": [
                {
                    "source_path": item.source_path,
                    "file_type": item.file_type,
                    "sensitivity": item.sensitivity,
                    "size_bytes": item.size_bytes,
                    "status": item.status,
                    "reason": item.reason,
                }
                for item in files
            ],
            "repo_artifacts": [item.to_state_payload() for item in artifacts],
            "doc_pages": [
                {
                    "page_id": item.page_id,
                    "source_path": item.source_path,
                    "source_hash": item.source_hash,
                    "title": item.title,
                    "doc_format": item.doc_format,
                    "sensitivity": item.sensitivity,
                }
                for item in pages
            ],
            "doc_sections": [
                {
                    "section_id": item.section_id,
                    "page_id": item.page_id,
                    "source_path": item.source_path,
                    "source_hash": item.source_hash,
                    "heading_path": item.heading_path,
                    "section_index": item.section_index,
                    "span_start_line": item.span_start_line,
                    "span_end_line": item.span_end_line,
                }
                for item in sections
            ],
            "doc_chunks": [item.to_state_payload() for item in chunks],
        }
    )


def run_indexer(root: Path, scope_config_path: Path) -> IndexerResult:
    resolved_root = _resolve_existing_root(root)
    resolved_scope_config = resolve_input_path(scope_config_path, resolved_root)
    scope = load_scope_config(resolved_scope_config)
    git_commit = current_git_commit(resolved_root)
    generated_at = current_git_commit_timestamp(resolved_root) or _utc_now()
    files, artifacts, normalized_text_by_path = classify_and_hash_files(
        resolved_root,
        scope,
        git_commit,
        generated_at,
    )
    pages, sections, chunks = build_markdown_records(artifacts, normalized_text_by_path)
    state_hash = build_state_hash(files, artifacts, pages, sections, chunks)
    run_id = f"context-indexer-{state_hash[:16]}"

    # Wave 9: static code/config/doc-link extraction
    ast_errors_all: list[AstParseError] = []
    code_symbols_all: list[CodeSymbol] = []
    import_refs_all: list[ImportReference] = []
    config_refs_all: list[ConfigReference] = []
    for artifact in artifacts:
        text = normalized_text_by_path.get(artifact.source_path, "")
        if artifact.file_type == "python":
            syms, errs = extract_code_symbols(artifact, text)
            code_symbols_all.extend(syms)
            ast_errors_all.extend(errs)
            imp_refs, errs2 = extract_import_references(artifact, text)
            import_refs_all.extend(imp_refs)
            # Both extractors call ast.parse; when the file is invalid, both
            # return the same error. Only extend if the first pass succeeded
            # to avoid duplicate AstParseError entries for the same file.
            if not errs:
                ast_errors_all.extend(errs2)
        if artifact.file_type in ("toml", "yaml", "json"):
            config_refs_all.extend(extract_config_references(artifact, text))
    test_cases_all = extract_test_cases(code_symbols_all)
    doc_code_links_all = extract_doc_code_links(artifacts, normalized_text_by_path)
    dep_edges_all = derive_dependency_edges(
        artifacts, code_symbols_all, import_refs_all, doc_code_links_all
    )

    partial_result = IndexerResult(
        root=resolved_root,
        scope_config=scope,
        git_commit=git_commit,
        generated_at=generated_at,
        run_id=run_id,
        state_hash=state_hash,
        files=files,
        repo_artifacts=artifacts,
        doc_pages=pages,
        doc_sections=sections,
        doc_chunks=chunks,
        validation_findings=[],
        ast_parse_errors=ast_errors_all,
        code_symbols=code_symbols_all,
        import_references=import_refs_all,
        test_cases=test_cases_all,
        config_references=config_refs_all,
        doc_code_links=doc_code_links_all,
        dependency_edges=dep_edges_all,
    )
    findings = validate_indexer_result(partial_result)
    return IndexerResult(
        root=partial_result.root,
        scope_config=partial_result.scope_config,
        git_commit=partial_result.git_commit,
        generated_at=partial_result.generated_at,
        run_id=partial_result.run_id,
        state_hash=partial_result.state_hash,
        files=partial_result.files,
        repo_artifacts=partial_result.repo_artifacts,
        doc_pages=partial_result.doc_pages,
        doc_sections=partial_result.doc_sections,
        doc_chunks=partial_result.doc_chunks,
        validation_findings=findings,
        ast_parse_errors=partial_result.ast_parse_errors,
        code_symbols=partial_result.code_symbols,
        import_references=partial_result.import_references,
        test_cases=partial_result.test_cases,
        config_references=partial_result.config_references,
        doc_code_links=partial_result.doc_code_links,
        dependency_edges=partial_result.dependency_edges,
    )


def validate_indexer_result(result: IndexerResult) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    artifact_by_path = {item.source_path: item for item in result.repo_artifacts}
    artifact_hashes = {item.normalized_sha256 for item in result.repo_artifacts}
    section_ids = {item.section_id for item in result.doc_sections}
    page_ids = {item.page_id for item in result.doc_pages}

    for file_record in result.files:
        if file_record.status == "included":
            if _matched_exclude_rule(file_record.source_path, result.scope_config) is not None:
                findings.append(
                    ValidationFinding(
                        severity="blocking",
                        code="forbidden_file_included",
                        message="included file matches an excluded scope path",
                        source_path=file_record.source_path,
                    )
                )
            if file_record.source_path not in artifact_by_path:
                findings.append(
                    ValidationFinding(
                        severity="blocking",
                        code="included_file_missing_artifact",
                        message="included file has no repo_artifact record",
                        source_path=file_record.source_path,
                    )
                )
            if _path_contains_trading_state(file_record.source_path):
                findings.append(
                    ValidationFinding(
                        severity="blocking",
                        code="trading_state_path_included",
                        message="included path looks like trading/runtime state",
                        source_path=file_record.source_path,
                    )
                )
        elif file_record.status == "skipped":
            findings.append(
                ValidationFinding(
                    severity="info",
                    code="file_skipped",
                    message=file_record.reason,
                    source_path=file_record.source_path,
                )
            )
        elif file_record.reason == "content_forbidden_pattern":
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="content_forbidden_pattern",
                    message="high-confidence forbidden content pattern detected and omitted",
                    source_path=file_record.source_path,
                )
            )

    for artifact in result.repo_artifacts:
        for field_name in (
            "artifact_id",
            "source_path",
            "file_type",
            "raw_sha256",
            "normalized_sha256",
            "size_bytes",
            "sensitivity",
        ):
            if getattr(artifact, field_name) in (None, ""):
                findings.append(
                    ValidationFinding(
                        severity="blocking",
                        code="repo_artifact_required_field_missing",
                        message=f"repo_artifact missing required field {field_name}",
                        source_path=artifact.source_path,
                    )
                )

    for page in result.doc_pages:
        if page.source_hash not in artifact_hashes:
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="doc_page_source_hash_missing",
                    message="doc_page source_hash does not reference a repo_artifact",
                    source_path=page.source_path,
                )
            )

    for section in result.doc_sections:
        if section.page_id not in page_ids:
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="doc_section_page_ref_missing",
                    message="doc_section page_id does not reference a doc_page",
                    source_path=section.source_path,
                )
            )
        if section.source_hash not in artifact_hashes:
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="doc_section_source_hash_missing",
                    message="doc_section source_hash does not reference a repo_artifact",
                    source_path=section.source_path,
                )
            )

    for chunk in result.doc_chunks:
        if chunk.section_id not in section_ids:
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="doc_chunk_section_ref_missing",
                    message="doc_chunk section_id does not reference a doc_section",
                    source_path=chunk.source_path,
                )
            )
        if chunk.source_hash not in artifact_hashes:
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="doc_chunk_source_hash_missing",
                    message="doc_chunk source_hash does not reference a repo_artifact",
                    source_path=chunk.source_path,
                )
            )
        if _contains_high_confidence_secret(chunk.content):
            findings.append(
                ValidationFinding(
                    severity="blocking",
                    code="secret_pattern_in_doc_chunk",
                    message="doc_chunk contains a high-confidence secret pattern",
                    source_path=chunk.source_path,
                )
            )

    # Wave 9: emit info findings for AST parse errors
    for parse_error in result.ast_parse_errors:
        findings.append(
            ValidationFinding(
                severity="info",
                code="ast_parse_error",
                message=f"ast parse failed ({parse_error.error_type}): {parse_error.error_message}",
                source_path=parse_error.source_path,
            )
        )

    return sorted(findings, key=lambda item: (item.severity, item.code, item.source_path or ""))


def _path_contains_trading_state(source_path: str) -> bool:
    parts = {part.lower() for part in source_path.replace("\\", "/").split("/")}
    return bool(parts & TRADING_STATE_PATH_PARTS)


def jsonl_records(result: IndexerResult) -> dict[str, list[dict[str, Any]]]:
    return {
        "repo_artifacts": [
            artifact.to_payload(result.run_id) for artifact in result.repo_artifacts
        ],
        "doc_pages": [page.to_payload(result.run_id) for page in result.doc_pages],
        "doc_sections": [
            section.to_payload(result.run_id) for section in result.doc_sections
        ],
        "doc_chunks": [chunk.to_payload(result.run_id) for chunk in result.doc_chunks],
        "skipped_files": [
            file_record.to_payload(result.run_id) for file_record in result.skipped_files
        ],
        "forbidden_files": [
            file_record.to_payload(result.run_id) for file_record in result.forbidden_files
        ],
        "code_symbols": [sym.to_payload(result.run_id) for sym in result.code_symbols],
        "import_references": [
            ref.to_payload(result.run_id) for ref in result.import_references
        ],
        "test_cases": [tc.to_payload(result.run_id) for tc in result.test_cases],
        "config_references": [
            cr.to_payload(result.run_id) for cr in result.config_references
        ],
        "doc_code_links": [
            link.to_payload(result.run_id) for link in result.doc_code_links
        ],
        "dependency_edges": [
            edge.to_payload(result.run_id) for edge in result.dependency_edges
        ],
        "evidence_refs": [],
        "claims": [],
        "decision_events": [],
        "agent_memories": [],
    }


def build_snapshot(
    result: IndexerResult, output_dir: Path | None = None
) -> dict[str, Any]:
    jsonl_files = {
        key: (output_dir / filename).as_posix() if output_dir else filename
        for key, filename in EXPORT_FILES.items()
    }
    warnings = [
        finding.to_payload()
        for finding in result.validation_findings
        if finding.severity in {"warning", "info"}
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": result.run_id,
        "generated_at": result.generated_at,
        "git_commit": result.git_commit,
        "scope_config": result.scope_config.path,
        "scope_config_schema_version": result.scope_config.schema_version,
        "state_hash": result.state_hash,
        "included_count": len(result.included_files),
        "skipped_count": len(result.skipped_files),
        "forbidden_count": len(result.forbidden_files),
        "artifact_count": len(result.repo_artifacts),
        "page_count": len(result.doc_pages),
        "section_count": len(result.doc_sections),
        "chunk_count": len(result.doc_chunks),
        "code_symbol_count": len(result.code_symbols),
        "import_ref_count": len(result.import_references),
        "test_case_count": len(result.test_cases),
        "config_ref_count": len(result.config_references),
        "doc_code_link_count": len(result.doc_code_links),
        "dependency_edge_count": len(result.dependency_edges),
        "ast_parse_error_count": len(result.ast_parse_errors),
        "validation": {
            "blocking_count": len(result.blocking_findings),
            "finding_count": len(result.validation_findings),
        },
        "warnings": warnings,
        "jsonl_files": jsonl_files,
        "surrealdb_connection": "disabled",
        "live_readiness_verdict": "NO-GO",
    }


def build_validation_report(result: IndexerResult) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": result.run_id,
        "status": "blocked" if result.blocking_findings else "passed",
        "blocking_count": len(result.blocking_findings),
        "finding_count": len(result.validation_findings),
        "findings": [finding.to_payload() for finding in result.validation_findings],
    }


def build_command_payload(
    command: str,
    result: IndexerResult,
    dry_run: bool,
    write_requested: bool,
    output: Path | None,
) -> dict[str, Any]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "run_id": result.run_id,
        "command": command,
        "dry_run": dry_run,
        "write_requested": write_requested,
        "output": output.as_posix() if output is not None else None,
        "surrealdb_connection": "disabled",
        "live_readiness_verdict": "NO-GO",
        "scope_config": result.scope_config.to_payload(),
    }
    if command == "scan":
        base.update(
            {
                "status": "completed",
                "counts": _counts(result),
                "files": [file_record.to_payload(result.run_id) for file_record in result.files],
            }
        )
        return base
    if command == "plan":
        base.update(
            {
                "status": "completed",
                "counts": _counts(result),
                "planned_outputs": list(EXPORT_FILES.values()),
                "blocking_findings": [
                    finding.to_payload() for finding in result.blocking_findings
                ],
            }
        )
        return base
    if command == "export-jsonl":
        base.update(
            {
                "status": "blocked" if result.blocking_findings else "completed",
                "counts": _counts(result),
                "would_write_files": list(EXPORT_FILES.values()),
                "validation": build_validation_report(result),
            }
        )
        return base
    if command == "snapshot":
        snapshot_output_dir = output if output and not output.suffix else None
        snapshot = build_snapshot(result, snapshot_output_dir)
        base.update({"status": "completed", "snapshot": snapshot})
        return base
    if command == "validate":
        base.update(build_validation_report(result))
        return base
    raise UnsupportedFormatError(f"unsupported command: {command}")


def _counts(result: IndexerResult) -> dict[str, int]:
    return {
        "included": len(result.included_files),
        "skipped": len(result.skipped_files),
        "forbidden": len(result.forbidden_files),
        "repo_artifacts": len(result.repo_artifacts),
        "doc_pages": len(result.doc_pages),
        "doc_sections": len(result.doc_sections),
        "doc_chunks": len(result.doc_chunks),
        "code_symbols": len(result.code_symbols),
        "import_references": len(result.import_references),
        "test_cases": len(result.test_cases),
        "config_references": len(result.config_references),
        "doc_code_links": len(result.doc_code_links),
        "dependency_edges": len(result.dependency_edges),
        "ast_parse_errors": len(result.ast_parse_errors),
        "validation_findings": len(result.validation_findings),
        "blocking_findings": len(result.blocking_findings),
    }


def render_payload(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=True, indent=2)
    if output_format == "jsonl":
        records = payload.get("files") or payload.get("findings") or [payload]
        return "\n".join(_json_dumps_record(record) for record in records)
    if output_format == "markdown":
        return render_markdown_payload(payload)
    if output_format == "text":
        status = payload.get("status", "completed")
        counts = payload.get("counts", {})
        return (
            f"{payload['command']}: {status} "
            f"(dry_run={payload['dry_run']}, "
            f"included={counts.get('included', 0)}, "
            f"blocking={counts.get('blocking_findings', payload.get('blocking_count', 0))}, "
            "surrealdb_connection=disabled)"
        )
    raise UnsupportedFormatError(f"unsupported format: {output_format}")


def render_markdown_payload(payload: dict[str, Any]) -> str:
    counts = payload.get("counts", {})
    lines = [
        f"# Context Indexer {payload['command']}",
        "",
        f"Status: {payload.get('status', 'completed')}",
        f"Schema: {payload['schema_version']}",
        f"Run ID: {payload['run_id']}",
        f"Dry run: {payload['dry_run']}",
        "SurrealDB connection: disabled",
        "Live-Readiness: NO-GO",
        "",
        "## Counts",
        f"- Included: {counts.get('included', 0)}",
        f"- Skipped: {counts.get('skipped', 0)}",
        f"- Forbidden: {counts.get('forbidden', 0)}",
        f"- Artifacts: {counts.get('repo_artifacts', 0)}",
        f"- Chunks: {counts.get('doc_chunks', 0)}",
    ]
    blocking = counts.get("blocking_findings", payload.get("blocking_count", 0))
    lines.extend([f"- Blocking findings: {blocking}"])
    return "\n".join(lines)


def write_command_output(output_path: Path, rendered: str) -> None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"output write failed: {exc}") from exc


def write_jsonl_exports(result: IndexerResult, output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            raise OutputWriteError(f"output path is not a directory: {output_dir}")
        records = jsonl_records(result)
        for key, filename in EXPORT_FILES.items():
            lines = [_json_dumps_record(record) for record in records[key]]
            (output_dir / filename).write_text(
                ("\n".join(lines) + "\n") if lines else "", encoding="utf-8"
            )
        snapshot = build_snapshot(result, output_dir)
        (output_dir / "snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        validation_report = build_validation_report(result)
        (output_dir / "validation_report.json").write_text(
            json.dumps(validation_report, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise OutputWriteError(f"output write failed: {exc}") from exc


def _json_dumps_record(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=True, separators=(",", ":"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Context Indexer CLI (offline, read-only/dry-run by default)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("scan", "plan", "export-jsonl", "snapshot", "validate"):
        subparser = subparsers.add_parser(
            command,
            help=f"{command} offline context-indexer command",
        )
        subparser.add_argument(
            "--root",
            type=Path,
            default=Path("."),
            help="Repo root for scans (default: current directory).",
        )
        subparser.add_argument(
            "--scope-config",
            type=Path,
            default=DEFAULT_SCOPE_CONFIG,
            help="Path to context_ingestion_scope.yaml.",
        )
        subparser.add_argument(
            "--output",
            type=Path,
            default=None,
            help=(
                "Explicit output path. export-jsonl expects a directory; other "
                "commands expect a file. Writes require --apply-writes."
            ),
        )
        subparser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate only. This is the default behavior.",
        )
        subparser.add_argument(
            "--apply-writes",
            action="store_true",
            help="Opt in to writing explicit outputs under artifacts/ or temp/.",
        )
        subparser.add_argument(
            "--format",
            choices=sorted(SUPPORTED_FORMATS),
            default="json",
            help="Render format for command output.",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dry_run = args.dry_run or not args.apply_writes

    try:
        if args.command == "export-jsonl":
            output = validate_output_directory(args.output, args.apply_writes and not dry_run)
        else:
            output = validate_output_path(args.output, args.apply_writes and not dry_run)
        result = run_indexer(args.root, args.scope_config)
        payload = build_command_payload(
            args.command,
            result,
            dry_run=dry_run,
            write_requested=args.apply_writes,
            output=output,
        )
        rendered = render_payload(payload, args.format)

        if result.blocking_findings and args.command in {"export-jsonl", "validate"}:
            print(rendered)
            return EXIT_VALIDATION_ERROR

        if args.apply_writes and not dry_run:
            if output is None:
                raise WriteDeniedError("writes require an explicit --output path")
            if args.command == "export-jsonl":
                write_jsonl_exports(result, output)
            else:
                write_command_output(output, rendered)
    except ContextIndexerError as exc:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "error": exc.code,
                    "message": exc.message,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return exc.exit_code

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
