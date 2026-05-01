"""SurrealDB context importer CLI scaffold (offline, dry-run by default).

Issue: #2068 (Wave 10, Slice 1)
Parent: #2067 / Epic #1976

This module implements ONLY the CLI scaffold for the future
context-import pipeline. It is intentionally a no-op for all
business commands and is hard-blocked from performing any write,
network, or SurrealDB operation.

Design rules enforced here:

* Default behavior is dry-run / no-write.
* The ``apply`` subcommand and the global ``--apply`` flag exist
  so that downstream slices can wire real behavior, but in this
  scaffold any apply attempt is hard-blocked with exit code 5
  (``WRITE_DENIED``) and a deterministic error payload.
* No SurrealDB connection is opened. ``--surreal-url``,
  ``--namespace``, and ``--database`` are parsed but never used.
* No JSONL is read, parsed, or validated.
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
import json
import logging
from pathlib import Path
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

ALLOWED_AUTH_MODES = frozenset({"none", "root", "scope"})

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
        raise WriteDeniedError(
            f"absolute output paths are forbidden: {output}"
        )
    parts = output.parts
    if not parts or parts[0] not in ALLOWED_OUTPUT_PREFIXES:
        raise WriteDeniedError(
            "output path must live under "
            f"{ALLOWED_OUTPUT_PREFIXES}, got: {output}"
        )
    if ".." in parts:
        raise WriteDeniedError(
            f"output path may not traverse with '..': {output}"
        )
    return output


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

    missing_forbidden = sorted(FORBIDDEN_CONTEXT_IMPORT_TABLES.difference(forbidden_tables))
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
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if fmt == "markdown":
        lines = [f"# context_importer: {payload['command']}"]
        for key in sorted(payload.keys()):
            lines.append(f"- **{key}**: `{payload[key]}`")
        return "\n".join(lines)
    raise UnsupportedFormatError(f"unsupported format: {fmt!r}")


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
            help="Directory containing JSONL artefacts (read-only; unused in scaffold).",
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
                "Optional report output path. Must live under artifacts/ or "
                "temp/. Scaffold never writes; the path is only validated."
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
    _validate_output_path(args.report_output)
    config = load_config(args.config) if args.config is not None else None

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
