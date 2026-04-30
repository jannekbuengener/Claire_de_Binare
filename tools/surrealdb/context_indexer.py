"""Context Indexer CLI scaffold for read-only scope-config validation.

This module intentionally does not connect to SurrealDB and does not implement
the full discovery, hashing, chunking, export, or snapshot pipeline. Those
behaviors belong to later Context Intelligence slices.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "context-indexer/v0"
SCOPE_CONFIG_SCHEMA_VERSION = "context-ingestion-scope/v0"
REQUIRED_SCOPE_KEYS = {
    "schema_version",
    "include_paths",
    "conditional_paths",
    "exclude_paths",
    "allowed_file_types",
    "sensitivity_classes",
    "guardrails",
}
EXPECTED_SENSITIVITY_CLASSES = {
    "public_context",
    "internal_context",
    "sensitive_metadata",
    "forbidden",
}
SUPPORTED_FORMATS = {"json", "markdown", "text"}
APPROVED_OUTPUT_ROOTS = ("artifacts", "temp")

EXIT_VALIDATION_ERROR = 1
EXIT_INPUT_NOT_FOUND = 3
EXIT_UNSUPPORTED_FORMAT = 4
EXIT_WRITE_DENIED = 5
EXIT_INTERNAL_ERROR = 6


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


class UnsupportedFormatError(ContextIndexerError):
    exit_code = EXIT_UNSUPPORTED_FORMAT
    code = "unsupported_format"


class WriteDeniedError(ContextIndexerError):
    exit_code = EXIT_WRITE_DENIED
    code = "write_denied"


@dataclass(frozen=True)
class ScopeConfigSummary:
    path: str
    schema_version: str
    include_paths: list[str]
    conditional_paths: list[str]
    exclude_paths: list[str]
    sensitivity_classes: list[str]


@dataclass(frozen=True)
class CommandResult:
    command: str
    dry_run: bool
    write_requested: bool
    output: str | None
    format: str
    scope_config: ScopeConfigSummary
    status: str = "scaffolded"
    surrealdb_connection: str = "disabled"
    message: str = "Command scaffold only; deeper indexer behavior is deferred."

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "command": self.command,
            "status": self.status,
            "message": self.message,
            "dry_run": self.dry_run,
            "write_requested": self.write_requested,
            "output": self.output,
            "format": self.format,
            "surrealdb_connection": self.surrealdb_connection,
            "scope_config": {
                "path": self.scope_config.path,
                "schema_version": self.scope_config.schema_version,
                "include_paths": self.scope_config.include_paths,
                "conditional_paths": self.scope_config.conditional_paths,
                "exclude_paths": self.scope_config.exclude_paths,
                "sensitivity_classes": self.scope_config.sensitivity_classes,
            },
            "deferred": [
                "full_file_discovery",
                "content_hashing",
                "markdown_chunking",
                "jsonl_artifact_export",
                "snapshot_report_generation",
                "surrealdb_import_apply_reconcile",
            ],
        }


def _path_entries(value: Any, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ScopeConfigValidationError(f"{key} must be a list")
    paths: list[str] = []
    for item in value:
        if not isinstance(item, dict) or not item.get("path"):
            raise ScopeConfigValidationError(f"{key} entries must contain path")
        paths.append(str(item["path"]))
    return sorted(paths)


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
    if not schema_version:
        raise ScopeConfigValidationError("scope config schema_version is required")
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

    return ScopeConfigSummary(
        path=path.as_posix(),
        schema_version=str(schema_version),
        include_paths=_path_entries(data["include_paths"], "include_paths"),
        conditional_paths=_path_entries(data["conditional_paths"], "conditional_paths"),
        exclude_paths=_path_entries(data["exclude_paths"], "exclude_paths"),
        sensitivity_classes=sorted(found_classes),
    )


def validate_output_path(output: Path | None, apply_writes: bool) -> Path | None:
    if not apply_writes:
        return output
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
    if len(normalized.parts) == 1 or normalized.suffix == "":
        raise WriteDeniedError("output must include a file name under an approved root")
    return normalized


def build_result(args: argparse.Namespace) -> CommandResult:
    output = validate_output_path(args.output, args.apply_writes)
    scope_summary = load_scope_config(args.scope_config)
    return CommandResult(
        command=args.command,
        dry_run=not args.apply_writes or args.dry_run,
        write_requested=args.apply_writes,
        output=output.as_posix() if output is not None else None,
        format=args.format,
        scope_config=scope_summary,
    )


def render_payload(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, sort_keys=True, indent=2)
    if output_format == "markdown":
        return "\n".join(
            [
                f"# Context Indexer {payload['command']}",
                "",
                f"Status: {payload['status']}",
                f"Schema: {payload['schema_version']}",
                f"Dry run: {payload['dry_run']}",
                f"SurrealDB connection: {payload['surrealdb_connection']}",
                f"Scope config: {payload['scope_config']['path']}",
                "",
                payload["message"],
            ]
        )
    if output_format == "text":
        return (
            f"{payload['command']}: {payload['status']} "
            f"(dry_run={payload['dry_run']}, "
            f"surrealdb_connection={payload['surrealdb_connection']})"
        )
    raise UnsupportedFormatError(f"unsupported format: {output_format}")


def write_if_requested(result: CommandResult, rendered: str) -> None:
    if not result.write_requested or result.dry_run:
        return
    if result.output is None:
        raise WriteDeniedError("writes require an explicit --output path")
    output_path = Path(result.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Context Indexer CLI scaffold (read-only/dry-run by default)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("scan", "plan", "export-jsonl", "snapshot", "validate"):
        subparser = subparsers.add_parser(
            command,
            help=f"{command} scaffold; deeper behavior is deferred",
        )
        subparser.add_argument(
            "--root",
            type=Path,
            default=Path("."),
            help="Repo root for future scans (currently recorded only).",
        )
        subparser.add_argument(
            "--scope-config",
            type=Path,
            required=True,
            help="Path to context_ingestion_scope.yaml.",
        )
        subparser.add_argument(
            "--output",
            type=Path,
            default=None,
            help="Explicit output path. Writes require --apply-writes.",
        )
        subparser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate only. This is the default scaffold behavior.",
        )
        subparser.add_argument(
            "--apply-writes",
            action="store_true",
            help="Opt in to writing an explicit --output under artifacts/ or temp/.",
        )
        subparser.add_argument(
            "--format",
            choices=sorted(SUPPORTED_FORMATS),
            default="json",
            help="Render format for scaffold output.",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = build_result(args)
        rendered = render_payload(result.to_payload(), result.format)
        write_if_requested(result, rendered)
    except ContextIndexerError as exc:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "error": exc.code,
                    "message": exc.message,
                },
                sort_keys=True,
            )
        )
        return exc.exit_code

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
