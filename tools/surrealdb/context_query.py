"""SurrealDB context query CLI scaffold (read-only, no-network).

Issues:
    #2080 - Context Query CLI scaffold + config loader + statement classifier v0
    Parent: #2079
    Epic: #1976
    Depends on: #1992, #2068, #2069
    Config basis: #2081

This module implements only the first safe query slice:

* a minimal ``classify`` CLI subcommand,
* explicit local config loading and validation,
* a fail-closed SurrealQL statement classifier,
* a no-op query adapter boundary that never opens network sockets.

There is no SurrealDB SDK usage, no real DB connection, no retrieval, no apply,
and no write path in this slice.

Exit codes:
    0 = success
    1 = validation failure
    2 = argparse usage error
    3 = input/config not found
    4 = unsupported format
    5 = write denied
    6 = internal error
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any

import yaml

logger = logging.getLogger(__name__)


SCHEMA_VERSION = "context-query/v0"
CONFIG_SCHEMA_VERSION = "context-query-local/v0"

EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_INPUT_NOT_FOUND = 3
EXIT_UNSUPPORTED_FORMAT = 4
EXIT_WRITE_DENIED = 5
EXIT_INTERNAL = 6

SUPPORTED_FORMATS = frozenset({"json", "markdown", "text"})

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
    {"governance_event", "governance_decision", "governance_state"}
)
FORBIDDEN_CONTEXT_QUERY_TABLES = TRADING_STATE_TABLES | GOVERNANCE_MIRROR_TABLES

SECRET_FIELD_NAMES = frozenset({"password", "token", "api_key", "secret", "credential"})
SECRET_FIELD_SEGMENTS = frozenset(
    {"password", "token", "api", "key", "secret", "credential"}
)

DENIED_KEYWORDS = frozenset(
    {
        "CREATE",
        "INSERT",
        "UPDATE",
        "UPSERT",
        "DELETE",
        "RELATE",
        "MERGE",
        "PATCH",
        "DEFINE",
        "REMOVE",
        "ALTER",
        "LIVE",
        "KILL",
        "USE",
        "BEGIN",
        "COMMIT",
        "CANCEL",
        "EXPLAIN",
        "SHOW CHANGES",
        "INFO FOR ROOT",
    }
)
ALLOWED_PREFIXES = ("SELECT", "INFO FOR DB", "INFO FOR TABLE", "INFO FOR NS")


class ContextQueryError(Exception):
    """Base error for context_query."""

    code: str = "CONTEXT_QUERY_ERROR"
    exit_code: int = EXIT_INTERNAL

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigValidationError(ContextQueryError):
    """Raised when the local query config is invalid or unsafe."""

    code = "CONFIG_VALIDATION_ERROR"
    exit_code = EXIT_VALIDATION_ERROR


class InputNotFoundError(ContextQueryError):
    """Raised when an explicitly supplied config path does not exist."""

    code = "INPUT_NOT_FOUND"
    exit_code = EXIT_INPUT_NOT_FOUND


class UnsupportedFormatError(ContextQueryError):
    """Raised when an unsupported output format is requested internally."""

    code = "UNSUPPORTED_FORMAT"
    exit_code = EXIT_UNSUPPORTED_FORMAT


class WriteDeniedError(ContextQueryError):
    """Raised when a statement or flow would write or control state."""

    code = "WRITE_DENIED"
    exit_code = EXIT_WRITE_DENIED


@dataclass(frozen=True)
class ContextQueryConfig:
    """Validated local config for context query classification."""

    path: Path
    schema_version: str
    surreal_url: str
    namespace: str
    database: str
    auth_mode: str
    timeout: int
    read_only: bool
    mode_read_only: bool
    surrealdb_write: str
    surrealdb_apply: str
    allowed_tables: tuple[str, ...]
    forbidden_tables: tuple[str, ...]
    max_limit_default: int
    max_limit_hard: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "schema_version": self.schema_version,
            "surreal_url": self.surreal_url,
            "namespace": self.namespace,
            "database": self.database,
            "auth_mode": self.auth_mode,
            "timeout": self.timeout,
            "read_only": self.read_only,
            "mode": {
                "read_only": self.mode_read_only,
                "surrealdb_write": self.surrealdb_write,
                "surrealdb_apply": self.surrealdb_apply,
            },
            "allowed_tables": list(self.allowed_tables),
            "forbidden_tables": list(self.forbidden_tables),
            "max_limit_default": self.max_limit_default,
            "max_limit_hard": self.max_limit_hard,
        }


@dataclass(frozen=True)
class StatementClassification:
    """Deterministic read-only classifier result."""

    statement: str
    normalized: str
    allowed: bool
    operation: str
    reason: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "normalized": self.normalized,
            "allowed": self.allowed,
            "operation": self.operation,
            "reason": self.reason,
        }


class QueryAdapter:
    """Base class for read-only SurrealDB query adapters.

    Subclasses must implement ``execute()`` to perform queries
    and must never open write paths.
    """

    status = "adapter-base"

    def __init__(self, config: ContextQueryConfig | None = None) -> None:
        self.config = config

    def execute(self, query: str) -> list[dict[str, Any]]:
        """Execute a read-only SELECT query and return results."""
        raise NotImplementedError

    def classify(self, statement: str) -> StatementClassification:
        """Classify a statement through the v0 read-only guardrail."""
        return classify_statement(statement, config=self.config)


class NoopQueryAdapter(QueryAdapter):
    """No-network query adapter placeholder for this scaffold."""

    status = "noop-no-network"

    def execute(self, query: str) -> list[dict[str, Any]]:
        """Return empty results; this adapter never contacts a database."""
        return []


def _require_mapping(value: Any, *, path: Path | None = None) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        detail = f" in {path}" if path is not None else ""
        raise ConfigValidationError(f"config root must be a mapping{detail}")
    return value


def _require_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{key} must be a non-empty string")
    return value


def _require_bool(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{key} must be a boolean")
    return value


def _require_int(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigValidationError(f"{key} must be an integer")
    return value


def _require_str_list(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigValidationError(f"{key} must be a list of strings")
    return tuple(value)


def _find_secret_fields(value: Any, *, prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, raw_item in value.items():
            key = str(raw_key)
            path = f"{prefix}.{key}" if prefix else key
            key_segments = _secret_key_segments(key)
            if key.lower() in SECRET_FIELD_NAMES or key_segments.intersection(
                SECRET_FIELD_SEGMENTS
            ):
                findings.append(path)
            findings.extend(_find_secret_fields(raw_item, prefix=path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            findings.extend(_find_secret_fields(item, prefix=path))
    return findings


def load_config(path: Path) -> ContextQueryConfig:
    """Load and validate an explicit local context query config."""

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
    secret_fields = _find_secret_fields(data)
    if secret_fields:
        raise ConfigValidationError(
            "config must not contain secret-bearing fields: " f"{sorted(secret_fields)}"
        )

    schema_version = _require_str(data, "schema_version")
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ConfigValidationError(
            "unsupported config schema_version: "
            f"{schema_version!r}; expected {CONFIG_SCHEMA_VERSION!r}"
        )

    read_only = _require_bool(data, "read_only")
    if read_only is not True:
        raise ConfigValidationError("read_only must be true for context query config")

    mode = _require_mapping(data.get("mode"))
    mode_read_only = _require_bool(mode, "read_only")
    if mode_read_only is not True:
        raise ConfigValidationError("mode.read_only must be true")

    surrealdb_write = _require_str(mode, "surrealdb_write")
    if surrealdb_write != "forbidden":
        raise ConfigValidationError("mode.surrealdb_write must be 'forbidden'")

    surrealdb_apply = _require_str(mode, "surrealdb_apply")
    if surrealdb_apply != "forbidden":
        raise ConfigValidationError("mode.surrealdb_apply must be 'forbidden'")

    allowed_tables = _require_str_list(data, "allowed_tables")
    forbidden_tables = _require_str_list(data, "forbidden_tables")

    forbidden_in_allowed = sorted(
        set(allowed_tables).intersection(FORBIDDEN_CONTEXT_QUERY_TABLES)
    )
    if forbidden_in_allowed:
        raise ConfigValidationError(
            "allowed_tables contains forbidden trading/governance tables: "
            f"{forbidden_in_allowed}"
        )

    missing_forbidden = sorted(
        FORBIDDEN_CONTEXT_QUERY_TABLES.difference(forbidden_tables)
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

    max_limit_default = _require_int(data, "max_limit_default")
    max_limit_hard = _require_int(data, "max_limit_hard")
    if max_limit_default > max_limit_hard:
        raise ConfigValidationError("max_limit_default must be <= max_limit_hard")

    return ContextQueryConfig(
        path=path,
        schema_version=schema_version,
        surreal_url=_require_str(data, "surreal_url"),
        namespace=_require_str(data, "namespace"),
        database=_require_str(data, "database"),
        auth_mode=_require_str(data, "auth_mode"),
        timeout=_require_int(data, "timeout"),
        read_only=read_only,
        mode_read_only=mode_read_only,
        surrealdb_write=surrealdb_write,
        surrealdb_apply=surrealdb_apply,
        allowed_tables=allowed_tables,
        forbidden_tables=forbidden_tables,
        max_limit_default=max_limit_default,
        max_limit_hard=max_limit_hard,
    )


def _normalize_statement(statement: str) -> str:
    return re.sub(r"\s+", " ", statement.strip()).upper()


def _secret_key_segments(key: str) -> set[str]:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    return {segment for segment in re.split(r"[_\-.]+", separated.lower()) if segment}


def _statement_tokens(normalized: str) -> set[str]:
    return set(re.findall(r"[A-Z_][A-Z0-9_]*", normalized))


def _extract_direct_table_references(normalized: str) -> set[str]:
    refs: set[str] = set()
    refs.update(re.findall(r"\bFROM\s+([A-Z_][A-Z0-9_]*)\b", normalized))
    refs.update(re.findall(r"\bINFO\s+FOR\s+TABLE\s+([A-Z_][A-Z0-9_]*)\b", normalized))
    return refs


def _enforce_table_policy_tokens(
    normalized: str, config: ContextQueryConfig | None
) -> None:
    if config is None:
        return

    # v0 uses conservative token-based forbidden table detection; this is not
    # a SurrealQL parser and intentionally fails closed for direct table tokens.
    table_refs = _extract_direct_table_references(normalized)
    if not table_refs:
        table_refs = _statement_tokens(normalized)
    allowed_tables = {table.upper() for table in config.allowed_tables}
    forbidden_tables = {table.upper() for table in config.forbidden_tables}
    forbidden_hits = sorted(
        table for table in config.forbidden_tables if table.upper() in table_refs
    )
    if forbidden_hits:
        raise WriteDeniedError(
            "statement references forbidden table(s): " f"{forbidden_hits}"
        )
    unknown_hits = sorted(
        table
        for table in table_refs
        if table not in allowed_tables and table not in forbidden_tables
    )
    if unknown_hits:
        raise WriteDeniedError(
            "statement references table(s) outside allowed_tables: " f"{unknown_hits}"
        )


def classify_statement(
    statement: str, config: ContextQueryConfig | None = None
) -> StatementClassification:
    """Classify a SurrealQL statement as allowed read-only or denied."""

    normalized = _normalize_statement(statement)
    if not normalized:
        raise ConfigValidationError("statement must be non-empty")

    if ";" in statement:
        raise WriteDeniedError("multi-statement input is denied in v0")

    if re.search(r"\b(APPLY|MIGRATION|TRANSACTION)\b", normalized):
        raise WriteDeniedError("transaction/migration/apply flows are denied")

    for keyword in sorted(DENIED_KEYWORDS, key=len, reverse=True):
        if keyword in {"SHOW CHANGES", "INFO FOR ROOT"}:
            if normalized.startswith(keyword):
                raise WriteDeniedError(f"{keyword} statements are denied")
            continue
        if normalized == keyword or normalized.startswith(f"{keyword} "):
            raise WriteDeniedError(f"{keyword} statements are denied")

    for prefix in ALLOWED_PREFIXES:
        if normalized == prefix or normalized.startswith(f"{prefix} "):
            _enforce_table_policy_tokens(normalized, config)
            return StatementClassification(
                statement=statement,
                normalized=normalized,
                allowed=True,
                operation=prefix,
                reason="read-only statement allowed by v0 classifier",
            )

    raise WriteDeniedError("statement is not in the v0 read-only allowlist")


def build_artifact_query(
    source_path: str | None = None,
    file_type: str | None = None,
    hash_value: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for the ``repo_artifact`` table.

    All parameters are optional filters.  The query is built as a
    ``SELECT * FROM repo_artifact WHERE ... LIMIT ...`` statement.
    """
    conditions: list[str] = []
    if source_path:
        conditions.append(f"source_path CONTAINS '{source_path}'")
    if file_type:
        conditions.append(f"file_type = '{file_type}'")
    if hash_value:
        conditions.append(f"normalized_sha256 = '{hash_value}'")
    if not include_tombstoned:
        conditions.append("tombstoned = false")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM repo_artifact{where}{limit_str}"


def build_doc_query(
    query_text: str | None = None,
    source_path: str | None = None,
    heading: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for the ``doc_chunk`` table.

    All parameters are optional filters.  The query is built as a
    ``SELECT * FROM doc_chunk WHERE ... LIMIT ...`` statement.
    """
    conditions: list[str] = []
    if query_text:
        conditions.append(f"content CONTAINS '{query_text}'")
    if source_path:
        conditions.append(f"source_path CONTAINS '{source_path}'")
    if heading:
        # heading_path is an array; check if it contains the heading
        conditions.append(f"heading_path CONTAINS '{heading}'")
    if not include_tombstoned:
        conditions.append("tombstoned = false")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM doc_chunk{where}{limit_str}"


def _error_payload(exc: ContextQueryError) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "error": exc.code,
        "message": exc.message,
    }


def _render(payload: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    if fmt == "text":
        lines = [f"status: {payload.get('status', 'unknown')}"]
        if "classification" in payload:
            classification = payload["classification"]
            lines.append(f"operation: {classification['operation']}")
            lines.append(f"allowed: {classification['allowed']}")
        if "query" in payload:
            lines.append(f"query: {payload['query']}")
        if "count" in payload:
            lines.append(f"count: {payload['count']}")
        if "results" in payload:
            lines.append("results:")
            for row in payload["results"][:20]:  # limit displayed results
                lines.append(f"  - {row}")
        if "error" in payload:
            lines.append(f"error: {payload['error']}")
            lines.append(f"message: {payload.get('message', '')}")
        lines.append(
            f"surrealdb_connection: {payload.get('surrealdb_connection', 'n/a')}"
        )
        return "\n".join(lines)
    if fmt == "markdown":
        cmd = payload.get("command", "classify")
        lines = [f"# context_query: {cmd}", f"- **status**: `{payload.get('status')}`"]
        if "classification" in payload:
            classification = payload["classification"]
            lines.extend(
                [
                    f"- **operation**: `{classification['operation']}`",
                    f"- **allowed**: `{classification['allowed']}`",
                    f"- **surrealdb_connection**: `{payload.get('surrealdb_connection')}`",
                ]
            )
        if "query" in payload:
            lines.append(f"- **query**: `{payload['query']}`")
        if "count" in payload:
            lines.append(f"- **count**: `{payload['count']}`")
        if "results" in payload:
            lines.append("**results**:")
            for row in payload["results"][:20]:
                lines.append(f"  - `{row}`")
        if "error" in payload:
            lines.extend(
                [
                    f"- **error**: `{payload['error']}`",
                    f"- **message**: `{payload.get('message', '')}`",
                ]
            )
        return "\n".join(lines)
    raise UnsupportedFormatError(f"unsupported format: {fmt!r}")


def handle_find_artifact(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``find-artifact`` subcommand."""
    query = build_artifact_query(
        source_path=args.source_path or None,
        file_type=args.file_type or None,
        hash_value=args.hash or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "find-artifact",
        "status": "ok",
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
    }, EXIT_OK


def handle_find_doc(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``find-doc`` subcommand."""
    query = build_doc_query(
        query_text=args.query or None,
        source_path=args.source_path or None,
        heading=args.heading or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "find-doc",
        "status": "ok",
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
    }, EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context_query",
        description=(
            "Context Query CLI (#2080+). Read-only artifact/doc search "
            "with statement classification guardrails."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Local context query config YAML to load and validate.",
    )
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="json",
        help="Render format for command output (default: json).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional query limit; validated against config hard limit when config is loaded.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser(
        "classify",
        help="Classify a SurrealQL statement without connecting to SurrealDB.",
    )
    classify.add_argument(
        "--statement",
        required=True,
        help="Single SurrealQL statement to classify. Semicolons are denied in v0.",
    )

    find_artifact = subparsers.add_parser(
        "find-artifact",
        help="Search repo_artifact table with read-only filters.",
    )
    find_artifact.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    find_artifact.add_argument("--file-type", default=None, help="Filter by file type.")
    find_artifact.add_argument(
        "--hash", default=None, help="Filter by normalized SHA-256 hash."
    )
    find_artifact.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    find_doc = subparsers.add_parser(
        "find-doc",
        help="Search doc_chunk table with read-only filters.",
    )
    find_doc.add_argument("--query", default=None, help="Filter by content substring.")
    find_doc.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    find_doc.add_argument(
        "--heading", default=None, help="Filter by heading path element."
    )
    find_doc.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    return parser


def _handle(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    config: ContextQueryConfig | None = None
    if args.config is not None:
        config = load_config(args.config)

    if args.command in {"classify", "find-artifact", "find-doc"} and config is None:
        raise InputNotFoundError(f"--config is required for {args.command}")

    if config is not None:
        if args.limit is not None and args.limit < 1:
            raise ConfigValidationError("--limit must be >= 1")
        if args.limit is not None and args.limit > config.max_limit_hard:
            raise ConfigValidationError(
                "--limit may not exceed max_limit_hard from config"
            )

    adapter: QueryAdapter = NoopQueryAdapter(config=config)

    if args.command == "classify":
        classification = adapter.classify(args.statement)
        return (
            {
                "schema_version": SCHEMA_VERSION,
                "command": args.command,
                "status": "ok",
                "surrealdb_connection": adapter.status,
                "config_loaded": config is not None,
                "config": config.to_payload() if config is not None else None,
                "limit": args.limit,
                "classification": classification.to_payload(),
            },
            EXIT_OK,
        )
    if args.command == "find-artifact":
        return handle_find_artifact(args, config, adapter)
    if args.command == "find-doc":
        return handle_find_doc(args, config, adapter)

    raise ConfigValidationError(f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        payload, exit_code = _handle(args)
        rendered = _render(payload, args.format)
    except ContextQueryError as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=True, sort_keys=True))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - CLI scaffold safety net
        logger.exception("context_query internal error")
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

    print(rendered)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
