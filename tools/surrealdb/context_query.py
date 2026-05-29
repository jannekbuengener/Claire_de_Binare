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
import base64
from collections.abc import Mapping
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

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

LOCAL_QUERY_ALLOWED_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
ALLOWED_QUERY_SCHEMES = frozenset({"http", "https"})
ALLOWED_AUTH_MODES = frozenset({"none", "root"})
REAL_SURREALDB_QUERY_ADAPTER_AVAILABLE = True

# Tombstone-filter compatibility note (#2459 / PR #2465):
# context_intelligence_v0.surql does not declare a ``tombstoned`` field.
# Under SCHEMAFULL, WHERE predicates on undeclared fields are silently ignored,
# so ``WHERE tombstoned = false`` would return 0 rows instead of the expected
# records.  The ``include_tombstoned`` parameter is API-preserved for
# forward-compatibility.  A real tombstone filter belongs in a later schema
# slice, not this PR.
TOMBSTONE_FILTER_SCHEMA_SUPPORTED = False
_TOMBSTONE_FILTER_REASON_NO_SCHEMA = "schema-field-not-defined"
_TOMBSTONE_FILTER_REASON_INCLUDE_REQUESTED = "include-tombstoned-requested"


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


class QueryAdapterError(ContextQueryError):
    """Raised when the real query adapter encounters a network or protocol error."""

    code = "QUERY_ADAPTER_ERROR"
    exit_code = EXIT_INTERNAL


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


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that unconditionally blocks all HTTP redirects.

    ``urllib.request.urlopen`` follows 3xx redirects by default, including
    converting POST→GET for 301/302/303 and preserving headers (including
    ``Authorization``) for 307/308.  If a local service on localhost returns a
    redirect to a remote ``Location:`` URL, the Basic-auth credential would be
    forwarded to that remote host — a credential-leak vector.

    This handler raises ``QueryAdapterError`` before any redirect is followed,
    ensuring the Authorization header is never sent to a non-local host.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise QueryAdapterError(
            f"redirect denied for local SurrealDB query request (HTTP {code})"
        )


class SurrealDBLocalQueryAdapter(QueryAdapter):
    """Real HTTP REST query adapter for a local SurrealDB instance. Issue #2459.

    - Connects ONLY to localhost (127.0.0.1, ::1, localhost) via http/https.
    - All queries classified as read-only before any HTTP call.
    - Writes/admin statements fail before HTTP (WriteDeniedError).
    - HTTP redirects are blocked: Authorization header is never forwarded to
      a redirect Location (credential-leak prevention).
    - Unreachable DB: soft mode → empty results + status unavailable;
                      hard mode → QueryAdapterError (non-zero exit).
    - No new dependencies: stdlib urllib.request, base64, json.
    """

    _STATUS_CONNECTED = "surrealdb-local"
    _STATUS_UNAVAILABLE = "surrealdb-local-unavailable"

    def __init__(
        self,
        surreal_url: str,
        namespace: str,
        database: str,
        user: str | None,
        password: str | None,
        timeout: int = 10,
        hard_mode: bool = False,
        config: ContextQueryConfig | None = None,
    ) -> None:
        super().__init__(config=config)
        _validate_local_query_url(surreal_url)  # defense-in-depth
        self._url = surreal_url.rstrip("/")
        self._namespace = namespace
        self._database = database
        self._user = user
        self._password = password
        self._timeout = timeout
        self._hard_mode = hard_mode
        self.status = self._STATUS_CONNECTED

    def _make_auth_header(self) -> str | None:
        if self._user and self._password:
            token = base64.b64encode(f"{self._user}:{self._password}".encode()).decode()
            return f"Basic {token}"
        return None

    def _sql_request(self, sql: str) -> list[dict[str, Any]]:
        endpoint = f"{self._url}/sql"
        data = sql.encode("utf-8")
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "surreal-ns": self._namespace,
            "surreal-db": self._database,
        }
        auth_header = self._make_auth_header()
        if auth_header is not None:
            headers["Authorization"] = auth_header
        req = urllib.request.Request(
            endpoint, data=data, headers=headers, method="POST"
        )
        _opener = urllib.request.build_opener(_NoRedirectHandler())
        try:
            with _opener.open(req, timeout=self._timeout) as resp:
                body = resp.read()
        except QueryAdapterError:
            raise
        except urllib.error.HTTPError as exc:
            raise QueryAdapterError(
                f"SurrealDB HTTP error: {exc.code} {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            self.status = self._STATUS_UNAVAILABLE
            if self._hard_mode:
                raise QueryAdapterError(f"SurrealDB unreachable: {exc.reason}") from exc
            logger.warning("SurrealDB unreachable (soft mode): %s", exc.reason)
            return []
        try:
            response_list = json.loads(body)
        except json.JSONDecodeError as exc:
            raise QueryAdapterError(
                f"SurrealDB response is not valid JSON: {exc}"
            ) from exc
        if not isinstance(response_list, list):
            raise QueryAdapterError("SurrealDB response must be a JSON array")
        results: list[dict[str, Any]] = []
        for item in response_list:
            if not isinstance(item, dict):
                raise QueryAdapterError("SurrealDB response item must be a mapping")
            if item.get("status") != "OK":
                raise QueryAdapterError(
                    f"SurrealDB query failed: status={item.get('status')!r}, "
                    f"result={str(item.get('result'))[:200]!r}"
                )
            result = item.get("result")
            if isinstance(result, list):
                results.extend(result)
        return results

    def execute(self, query: str) -> list[dict[str, Any]]:
        classification = self.classify(query)
        if not classification.allowed:
            raise WriteDeniedError(
                f"query not allowed by classifier: {classification.reason}"
            )
        return self._sql_request(query)


def _validate_local_query_url(url: str) -> None:
    """Reject non-local or non-HTTP(S) SurrealDB URLs for the query adapter."""
    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if scheme not in ALLOWED_QUERY_SCHEMES:
        raise ConfigValidationError(
            f"surreal_url must use http or https scheme; got scheme={scheme!r}. "
            "WebSocket URLs (ws://, wss://) are not supported for the query adapter."
        )
    if host not in LOCAL_QUERY_ALLOWED_HOSTS:
        raise ConfigValidationError(
            f"surreal_url must point to a local host; got host={host!r}, "
            f"allowed={sorted(LOCAL_QUERY_ALLOWED_HOSTS)}"
        )


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

    surreal_url = _require_str(data, "surreal_url")
    _validate_local_query_url(surreal_url)
    auth_mode = _require_str(data, "auth_mode")
    if auth_mode not in ALLOWED_AUTH_MODES:
        raise ConfigValidationError(
            f"auth_mode must be one of {sorted(ALLOWED_AUTH_MODES)}; got {auth_mode!r}"
        )

    return ContextQueryConfig(
        path=path,
        schema_version=schema_version,
        surreal_url=surreal_url,
        namespace=_require_str(data, "namespace"),
        database=_require_str(data, "database"),
        auth_mode=auth_mode,
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


def _load_query_credentials(
    config: ContextQueryConfig, secrets_path: Path | None
) -> tuple[str | None, str | None]:
    """Load SurrealDB credentials based on auth_mode from config.

    Returns (user, password); both None for auth_mode 'none'.
    Reads SURREALDB_ENV file for auth_mode 'root'.
    """
    if config.auth_mode == "none":
        return None, None
    if config.auth_mode == "root":
        if secrets_path is None:
            raise ConfigValidationError(
                "auth_mode 'root' requires --secrets-path pointing to the directory "
                "containing SURREALDB_ENV"
            )
        env_file = secrets_path / "SURREALDB_ENV"
        if not env_file.is_file():
            raise InputNotFoundError(f"SURREALDB_ENV not found at: {env_file}")
        user: str | None = None
        password: str | None = None
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SURREAL_USER="):
                user = line[len("SURREAL_USER=") :].strip()
            elif line.startswith("SURREAL_PASS="):
                password = line[len("SURREAL_PASS=") :].strip()
        if not user or not password:
            raise ConfigValidationError(
                "SURREALDB_ENV must contain non-empty SURREAL_USER and SURREAL_PASS lines"
            )
        return user, password
    raise ConfigValidationError(f"unsupported auth_mode: {config.auth_mode!r}")


def _surrealql_string(value: str) -> str:
    """Return value as a safe SurrealQL string literal (double-quoted JSON format).

    Uses json.dumps() to produce a properly-escaped double-quoted string.
    Handles backslashes, apostrophes, control characters, and all special chars.
    SurrealDB accepts both single-quoted and double-quoted string literals.
    """
    return json.dumps(value)


def _tombstone_meta(include_tombstoned: bool) -> dict[str, Any]:
    """Return tombstone-filter transparency metadata for query handler payloads.

    The tombstone filter is currently schema-disabled:
    ``context_intelligence_v0.surql`` does not declare a ``tombstoned`` field.
    Under SCHEMAFULL, a ``WHERE tombstoned = false`` predicate silently returns
    0 rows because the field does not exist.  The parameter is kept for API
    forward-compatibility; a real filter belongs in a later schema slice.

    Returns a dict with ``tombstone_filter_applied`` always ``False``, plus a
    ``tombstone_filter_reason`` key.  When ``include_tombstoned=True``, also
    sets ``include_tombstoned: True`` so callers can see the requested intent.
    See :data:`TOMBSTONE_FILTER_SCHEMA_SUPPORTED`.
    """
    if include_tombstoned:
        return {
            "tombstone_filter_applied": False,
            "include_tombstoned": True,
            "tombstone_filter_reason": _TOMBSTONE_FILTER_REASON_INCLUDE_REQUESTED,
        }
    return {
        "tombstone_filter_applied": False,
        "tombstone_filter_reason": _TOMBSTONE_FILTER_REASON_NO_SCHEMA,
    }


_SURQL_STRING_LITERAL_RE = re.compile(
    r'"(?:\\.|[^"\\])*"' + r"|" + r"'(?:\\.|[^'\\])*'"
)


def _normalize_statement(statement: str) -> str:
    """Collapse whitespace and uppercase keywords for classifier guards only.

    String literal contents are preserved so write-keyword checks and
    classification metadata do not mutate user filter values.
    """
    collapsed = re.sub(r"\s+", " ", statement.strip())
    if not collapsed:
        return collapsed

    parts: list[str] = []
    last = 0
    for match in _SURQL_STRING_LITERAL_RE.finditer(collapsed):
        parts.append(collapsed[last : match.start()].upper())
        parts.append(match.group(0))
        last = match.end()
    parts.append(collapsed[last:].upper())
    return "".join(parts)


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

    SCHEMA_COMPAT_NOTE: ``include_tombstoned`` does **not** add a
    ``WHERE tombstoned`` predicate.  The field is not declared in
    ``context_intelligence_v0.surql``; under SCHEMAFULL such a predicate
    silently returns 0 rows.  Filter semantics are reported transparently in
    the handler payload via ``tombstone_filter_applied`` and
    ``tombstone_filter_reason``.  See :data:`TOMBSTONE_FILTER_SCHEMA_SUPPORTED`.
    """
    conditions: list[str] = []
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")
    if file_type:
        conditions.append(f"file_type = {_surrealql_string(file_type)}")
    if hash_value:
        conditions.append(f"normalized_sha256 = {_surrealql_string(hash_value)}")
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
        conditions.append(f"content CONTAINS {_surrealql_string(query_text)}")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")
    if heading:
        # heading_path is an array; check if it contains the heading
        conditions.append(f"heading_path CONTAINS {_surrealql_string(heading)}")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM doc_chunk{where}{limit_str}"


def build_symbol_query(
    name: str | None = None,
    qualified_name: str | None = None,
    source_path: str | None = None,
    symbol_type: str | None = None,
    symbol_id: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for the ``code_symbol`` table.

    All parameters are optional filters. The query is built as a
    ``SELECT * FROM code_symbol WHERE ... LIMIT ...`` statement.
    """
    conditions: list[str] = []
    if name:
        conditions.append(f"name CONTAINS {_surrealql_string(name)}")
    if qualified_name:
        conditions.append(
            f"qualified_name CONTAINS {_surrealql_string(qualified_name)}"
        )
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")
    if symbol_type:
        conditions.append(f"symbol_type = {_surrealql_string(symbol_type)}")
    if symbol_id:
        conditions.append(f"symbol_id = {_surrealql_string(symbol_id)}")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM code_symbol{where}{limit_str}"


def build_import_query(
    module: str | None = None,
    source_path: str | None = None,
    source_hash: str | None = None,
    import_id: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for the ``import_reference`` table.

    All parameters are optional filters. The query is built as a
    ``SELECT * FROM import_reference WHERE ... LIMIT ...`` statement.
    """
    conditions: list[str] = []
    if module:
        conditions.append(f"module CONTAINS {_surrealql_string(module)}")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")
    if source_hash:
        conditions.append(f"source_hash = {_surrealql_string(source_hash)}")
    if import_id:
        conditions.append(f"import_id = {_surrealql_string(import_id)}")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM import_reference{where}{limit_str}"


DEFAULT_TRACE_DEPTH = 3
MAX_TRACE_DEPTH = 10


def build_trace_query(
    target_ref: str | None = None,
    source_path: str | None = None,
    symbol_name: str | None = None,
    direction: str | None = None,
    edge_type: str | None = None,
    confidence: str | None = None,
    depth: int | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for the ``dependency_edge`` table.

    All parameters are optional filters. The query traces dependency edges
    from a starting reference (artifact, symbol, or import).

    Direction is one-way v0: if not specified, returns all edges from target.
    If specified, filters to 'upstream' (dependencies) or 'downstream' (dependents).

    Note: depth validation is performed in handle_trace; this builder focuses
    on query construction only.
    """
    conditions: list[str] = []
    if target_ref:
        conditions.append(f"source_ref CONTAINS {_surrealql_string(target_ref)}")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")
    if symbol_name:
        conditions.append(f"symbol_name CONTAINS {_surrealql_string(symbol_name)}")
    if direction == "upstream":
        conditions.append("edge_type = 'depends_on'")
    elif direction == "downstream":
        conditions.append("edge_type = 'used_by'")
    elif edge_type:
        conditions.append(f"edge_type = {_surrealql_string(edge_type)}")
    if confidence:
        conditions.append(f"confidence = {_surrealql_string(confidence)}")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM dependency_edge{where}{limit_str}"


def build_explain_source_query(
    artifact_id: str | None = None,
    chunk_id: str | None = None,
    symbol_id: str | None = None,
    edge_id: str | None = None,
    evidence_id: str | None = None,
    decision_id: str | None = None,
    source_path: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query to explain source/evidence for a context artifact.

    This query traces the provenance of a context record by looking up its
    source information from repo_artifact, doc_chunk, or code_symbol tables.

    Only one of the ID parameters should be provided to identify the target.
    """
    id_conditions: list[str] = []
    if artifact_id:
        id_conditions.append(f"artifact_id = {_surrealql_string(artifact_id)}")
    if chunk_id:
        id_conditions.append(f"chunk_id = {_surrealql_string(chunk_id)}")
    if symbol_id:
        id_conditions.append(f"symbol_id = {_surrealql_string(symbol_id)}")
    if edge_id:
        id_conditions.append(f"edge_id = {_surrealql_string(edge_id)}")
    if evidence_id:
        id_conditions.append(f"evidence_id = {_surrealql_string(evidence_id)}")
    if decision_id:
        id_conditions.append(f"decision_id = {_surrealql_string(decision_id)}")

    if (
        len(
            [
                c
                for c in [
                    artifact_id,
                    chunk_id,
                    symbol_id,
                    edge_id,
                    evidence_id,
                    decision_id,
                ]
                if c
            ]
        )
        > 1
    ):
        raise ConfigValidationError(
            "only one of artifact_id, chunk_id, symbol_id, edge_id, evidence_id, "
            "or decision_id may be provided"
        )

    conditions: list[str] = []
    if id_conditions:
        id_clause = " OR ".join(id_conditions)
        conditions.append(f"({id_clause})")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""

    return f"SELECT artifact_id, chunk_id, symbol_id, edge_id, source_path, source_hash, source_commit, run_id, import_audit_ref, tombstoned FROM repo_artifact{where}{limit_str}"


def build_snapshot_query(
    snapshot_id: str | None = None,
    run_id: str | None = None,
    source_path: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for snapshot information.

    Queries repo_artifact table to retrieve snapshot data filtered by
    snapshot_id, run_id, or source_path.
    """
    conditions: list[str] = []
    if snapshot_id:
        conditions.append(f"snapshot_id = {_surrealql_string(snapshot_id)}")
    if run_id:
        conditions.append(f"run_id = {_surrealql_string(run_id)}")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM repo_artifact{where}{limit_str}"


def build_drift_query(
    artifact_id: str | None = None,
    source_path: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for drift information.

    Queries dependency_edge table to retrieve drift/changes data.
    Filters by artifact, source path, status (blocking/warning/info),
    and kind.
    """
    conditions: list[str] = []
    if artifact_id:
        conditions.append(f"source_ref CONTAINS {_surrealql_string(artifact_id)}")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")
    if status:
        conditions.append(f"status = {_surrealql_string(status)}")
    if kind:
        conditions.append(f"edge_type = {_surrealql_string(kind)}")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM dependency_edge{where}{limit_str}"


def build_audit_query(
    audit_id: str | None = None,
    run_id: str | None = None,
    source_path: str | None = None,
    limit: int | None = None,
    include_tombstoned: bool = False,
) -> str:
    """Build a read-only SELECT query for audit information.

    Queries import_reference table to retrieve import audit data
    filtered by audit_id, run_id, or source_path.
    """
    conditions: list[str] = []
    if audit_id:
        conditions.append(f"import_id = {_surrealql_string(audit_id)}")
    if run_id:
        conditions.append(f"run_id = {_surrealql_string(run_id)}")
    if source_path:
        conditions.append(f"source_path CONTAINS {_surrealql_string(source_path)}")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    limit_str = f" LIMIT {limit}" if limit else ""
    return f"SELECT * FROM import_reference{where}{limit_str}"


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
            f"source: {payload.get('source', payload.get('surrealdb_connection', 'n/a'))}"
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
                    f"- **source**: `{payload.get('source', payload.get('surrealdb_connection', 'n/a'))}`",
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
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
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
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_find_symbol(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``find-symbol`` subcommand."""
    query = build_symbol_query(
        name=args.name or None,
        qualified_name=args.qualified_name or None,
        source_path=args.source_path or None,
        symbol_type=args.symbol_type or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "find-symbol",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_show_symbol(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-symbol`` subcommand."""
    query = build_symbol_query(
        symbol_id=args.symbol_id,
        limit=1,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "show-symbol",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_find_imports(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``find-imports`` subcommand."""
    query = build_import_query(
        module=args.module or None,
        source_path=args.source_path or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "find-imports",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_show_imports_for_artifact(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-imports-for-artifact`` subcommand."""
    query = build_import_query(
        source_hash=args.source_hash,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "show-imports-for-artifact",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_trace(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``trace`` subcommand."""
    if args.depth is not None and (args.depth < 1 or args.depth > MAX_TRACE_DEPTH):
        raise ConfigValidationError(f"--depth must be between 1 and {MAX_TRACE_DEPTH}")
    effective_depth = args.depth if args.depth is not None else DEFAULT_TRACE_DEPTH

    query = build_trace_query(
        target_ref=args.target_ref or None,
        source_path=args.source_path or None,
        symbol_name=args.symbol or None,
        direction=args.direction or None,
        edge_type=args.edge_type or None,
        confidence=args.confidence or None,
        depth=effective_depth,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "trace",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "depth": effective_depth,
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_explain_source(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``explain-source`` subcommand."""
    id_params = [
        args.artifact_id,
        args.chunk_id,
        args.symbol_id,
        args.edge_id,
        args.evidence_id,
        args.decision_id,
    ]
    provided_ids = [p for p in id_params if p]

    if len(provided_ids) > 1:
        raise ConfigValidationError(
            "only one of --artifact-id, --chunk-id, --symbol-id, --edge-id, "
            "--evidence-id, or --decision-id may be provided"
        )
    if not any(id_params):
        raise ConfigValidationError(
            "one of --artifact-id, --chunk-id, --symbol-id, --edge-id, "
            "--evidence-id, or --decision-id is required"
        )

    query = build_explain_source_query(
        artifact_id=args.artifact_id or None,
        chunk_id=args.chunk_id or None,
        symbol_id=args.symbol_id or None,
        edge_id=args.edge_id or None,
        evidence_id=args.evidence_id or None,
        decision_id=args.decision_id or None,
        source_path=args.source_path or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)

    warnings: list[str] = []
    if not results:
        warnings.append("no source information found for the given identifier")
    else:
        for row in results:
            if row.get("tombstoned"):
                warnings.append(
                    f"record is tombstoned: {row.get('artifact_id', row.get('chunk_id', row.get('symbol_id', 'unknown')))}"
                )
            if not row.get("source_hash"):
                warnings.append(
                    f"source_hash missing for: {row.get('artifact_id', 'unknown')}"
                )
            if not row.get("source_commit"):
                warnings.append(
                    f"source_commit missing for: {row.get('artifact_id', 'unknown')}"
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "command": "explain-source",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        "warnings": warnings if warnings else None,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_show_snapshot(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-snapshot`` subcommand."""
    query = build_snapshot_query(
        snapshot_id=args.snapshot_id or None,
        run_id=args.run_id or None,
        source_path=args.source_path or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "show-snapshot",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_show_drift(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-drift`` subcommand."""
    query = build_drift_query(
        artifact_id=args.artifact_id or None,
        source_path=args.source_path or None,
        status=args.status or None,
        kind=args.kind or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    findings: list[dict[str, str]] = []
    for row in results:
        status = row.get("status", "unknown")
        if status == "blocking":
            findings.append(
                {
                    "severity": "blocking",
                    "artifact": row.get("source_ref", "unknown"),
                    "detail": "requires attention",
                }
            )
        elif status == "warning":
            findings.append(
                {
                    "severity": "warning",
                    "artifact": row.get("source_ref", "unknown"),
                    "detail": "review recommended",
                }
            )
        elif status == "info":
            findings.append(
                {
                    "severity": "info",
                    "artifact": row.get("source_ref", "unknown"),
                    "detail": "informational",
                }
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "command": "show-drift",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        "findings": findings if findings else None,
        **_tombstone_meta(args.include_tombstoned),
    }, EXIT_OK


def handle_show_audit(
    args: argparse.Namespace, config: ContextQueryConfig, adapter: QueryAdapter
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-audit`` subcommand."""
    query = build_audit_query(
        audit_id=args.audit_id or None,
        run_id=args.run_id or None,
        source_path=args.source_path or None,
        limit=args.limit or config.max_limit_default,
        include_tombstoned=args.include_tombstoned,
    )
    classification = adapter.classify(query)
    if not classification.allowed:
        raise WriteDeniedError(f"query not allowed: {classification.reason}")

    results = adapter.execute(query)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "show-audit",
        "status": "ok",
        "source": adapter.status,
        "query": query,
        "classification": classification.to_payload(),
        "count": len(results),
        "results": results,
        **_tombstone_meta(args.include_tombstoned),
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
    parser.add_argument(
        "--adapter",
        choices=["noop", "surrealdb-local"],
        default="noop",
        help=(
            "Query adapter: 'noop' (safe default, no network) or "
            "'surrealdb-local' (real HTTP REST to local SurrealDB)."
        ),
    )
    parser.add_argument(
        "--secrets-path",
        type=Path,
        default=None,
        dest="secrets_path",
        help="Path to secrets directory containing SURREALDB_ENV (required for auth_mode: root).",
    )
    parser.add_argument(
        "--hard-mode",
        action="store_true",
        default=False,
        dest="hard_mode",
        help="Non-zero exit if DB is unreachable (default: soft mode, returns empty results).",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=0,
        dest="min_count",
        help=(
            "Minimum number of records the query must return; exit 1 if count is below "
            "this threshold (default: 0, no enforcement). Used by 'make context-smoke-db' "
            "(#2460) to prove real DB records were written."
        ),
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
        help=(
            "Include tombstoned records in results. "
            "Currently a no-op: the 'tombstoned' field is not declared in "
            "context_intelligence_v0.surql (SCHEMAFULL), so no WHERE filter "
            "is applied regardless of this flag. "
            "Tombstone-filter semantics are reported in the payload via "
            "'tombstone_filter_applied' and 'tombstone_filter_reason'. "
            "A real filter belongs in a later schema slice (not this PR)."
        ),
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

    find_symbol = subparsers.add_parser(
        "find-symbol",
        help="Search code_symbol table with read-only filters.",
    )
    find_symbol.add_argument(
        "--name", default=None, help="Filter by symbol name substring."
    )
    find_symbol.add_argument(
        "--qualified-name", default=None, help="Filter by qualified name substring."
    )
    find_symbol.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    find_symbol.add_argument(
        "--symbol-type",
        default=None,
        help="Filter by symbol type (function, class, etc.).",
    )
    find_symbol.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    show_symbol = subparsers.add_parser(
        "show-symbol",
        help="Show a single code symbol by symbol_id.",
    )
    show_symbol.add_argument("--symbol-id", required=True, help="Symbol ID to look up.")
    show_symbol.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    find_imports = subparsers.add_parser(
        "find-imports",
        help="Search import_reference table with read-only filters.",
    )
    find_imports.add_argument(
        "--module", default=None, help="Filter by module name substring."
    )
    find_imports.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    find_imports.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    show_imports_for_artifact = subparsers.add_parser(
        "show-imports-for-artifact",
        help="Show import references for a specific artifact by source hash.",
    )
    show_imports_for_artifact.add_argument(
        "--source-hash",
        required=True,
        help="Source hash of the artifact to look up imports for.",
    )
    show_imports_for_artifact.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    trace = subparsers.add_parser(
        "trace",
        help="Trace dependency edges from a starting reference (artifact/symbol/import).",
    )
    trace.add_argument(
        "--target-ref",
        default=None,
        help="Starting reference (artifact, symbol, or import identifier).",
    )
    trace.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    trace.add_argument(
        "--symbol",
        default=None,
        help="Filter by symbol name substring.",
    )
    trace.add_argument(
        "--direction",
        choices=["upstream", "downstream"],
        default=None,
        help="Trace direction: upstream (dependencies) or downstream (dependents).",
    )
    trace.add_argument("--edge-type", default=None, help="Filter by edge type.")
    trace.add_argument(
        "--confidence",
        default=None,
        help="Filter by confidence level (high, medium, low).",
    )
    trace.add_argument(
        "--depth",
        type=int,
        default=None,
        help=f"Trace depth (default: {DEFAULT_TRACE_DEPTH}, max: {MAX_TRACE_DEPTH}).",
    )
    trace.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    explain_source = subparsers.add_parser(
        "explain-source",
        help="Explain source/evidence for a context artifact (provenance trace).",
    )
    explain_source.add_argument(
        "--artifact-id",
        default=None,
        help="Artifact ID to explain source for.",
    )
    explain_source.add_argument(
        "--chunk-id",
        default=None,
        help="Chunk ID to explain source for.",
    )
    explain_source.add_argument(
        "--symbol-id",
        default=None,
        help="Symbol ID to explain source for.",
    )
    explain_source.add_argument(
        "--edge-id",
        default=None,
        help="Edge ID to explain source for.",
    )
    explain_source.add_argument(
        "--evidence-id",
        default=None,
        help="Evidence ID to explain source for.",
    )
    explain_source.add_argument(
        "--decision-id",
        default=None,
        help="Decision ID to explain source for.",
    )
    explain_source.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    explain_source.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    show_snapshot = subparsers.add_parser(
        "show-snapshot",
        help="Show snapshot information from context data.",
    )
    show_snapshot.add_argument(
        "--snapshot-id",
        default=None,
        help="Filter by snapshot ID.",
    )
    show_snapshot.add_argument(
        "--run-id",
        default=None,
        help="Filter by run ID.",
    )
    show_snapshot.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    show_snapshot.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    show_drift = subparsers.add_parser(
        "show-drift",
        help="Show drift/changes information from dependency edges.",
    )
    show_drift.add_argument(
        "--artifact-id",
        default=None,
        help="Filter by artifact ID or reference.",
    )
    show_drift.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    show_drift.add_argument(
        "--status",
        choices=["blocking", "warning", "info"],
        default=None,
        help="Filter by finding severity/status.",
    )
    show_drift.add_argument(
        "--kind",
        default=None,
        help="Filter by drift kind/edge type.",
    )
    show_drift.add_argument(
        "--include-tombstoned",
        action="store_true",
        default=False,
        help="Include tombstoned records in results (default: hidden).",
    )

    show_audit = subparsers.add_parser(
        "show-audit",
        help="Show import audit information.",
    )
    show_audit.add_argument(
        "--audit-id",
        default=None,
        help="Filter by audit/import ID.",
    )
    show_audit.add_argument(
        "--run-id",
        default=None,
        help="Filter by run ID.",
    )
    show_audit.add_argument(
        "--source-path", default=None, help="Filter by source path substring."
    )
    show_audit.add_argument(
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

    if (
        args.command
        in {
            "classify",
            "find-artifact",
            "find-doc",
            "find-symbol",
            "show-symbol",
            "find-imports",
            "show-imports-for-artifact",
            "trace",
            "explain-source",
            "show-snapshot",
            "show-drift",
            "show-audit",
        }
        and config is None
    ):
        raise InputNotFoundError(f"--config is required for {args.command}")

    if config is not None:
        if args.limit is not None and args.limit < 1:
            raise ConfigValidationError("--limit must be >= 1")
        if args.limit is not None and args.limit > config.max_limit_hard:
            raise ConfigValidationError(
                "--limit may not exceed max_limit_hard from config"
            )

    adapter: QueryAdapter
    adapter_name = getattr(args, "adapter", "noop")
    if adapter_name == "surrealdb-local":
        if config is None:
            raise InputNotFoundError(
                "--config is required for --adapter surrealdb-local"
            )
        secrets_path = getattr(args, "secrets_path", None)
        user, password = _load_query_credentials(config, secrets_path)
        hard_mode = getattr(args, "hard_mode", False)
        adapter = SurrealDBLocalQueryAdapter(
            surreal_url=config.surreal_url,
            namespace=config.namespace,
            database=config.database,
            user=user,
            password=password,
            timeout=config.timeout,
            hard_mode=hard_mode,
            config=config,
        )
    else:
        adapter = NoopQueryAdapter(config=config)

    if args.command == "classify":
        classification = adapter.classify(args.statement)
        return (
            {
                "schema_version": SCHEMA_VERSION,
                "command": args.command,
                "status": "ok",
                "surrealdb_connection": adapter.status,
                "source": adapter.status,
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
    if args.command == "find-symbol":
        return handle_find_symbol(args, config, adapter)
    if args.command == "show-symbol":
        return handle_show_symbol(args, config, adapter)
    if args.command == "find-imports":
        return handle_find_imports(args, config, adapter)
    if args.command == "show-imports-for-artifact":
        return handle_show_imports_for_artifact(args, config, adapter)
    if args.command == "trace":
        return handle_trace(args, config, adapter)
    if args.command == "explain-source":
        return handle_explain_source(args, config, adapter)
    if args.command == "show-snapshot":
        return handle_show_snapshot(args, config, adapter)
    if args.command == "show-drift":
        return handle_show_drift(args, config, adapter)
    if args.command == "show-audit":
        return handle_show_audit(args, config, adapter)

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

    min_count = getattr(args, "min_count", 0)
    if exit_code == EXIT_OK and min_count > 0:
        actual_count = payload.get("count", 0) if isinstance(payload, dict) else 0
        if actual_count < min_count:
            print(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "status": "error",
                        "error": "MIN_COUNT_NOT_MET",
                        "message": (
                            f"query returned {actual_count} record(s); "
                            f"--min-count requires at least {min_count}"
                        ),
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            )
            return EXIT_VALIDATION_ERROR

    print(rendered)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
