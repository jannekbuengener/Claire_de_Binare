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
import json
import logging
from pathlib import Path
from typing import Any

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


def _build_payload(
    command: str,
    *,
    dry_run: bool,
    apply_requested: bool,
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
    }
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

    # Validate format and output path defensively even though we do not
    # write. This makes the safety contract verifiable from tests.
    _validate_format(args.format)
    _validate_output_path(args.report_output)

    if command == "apply" or apply_requested:
        raise WriteDeniedError(
            "apply path is not implemented in scaffold (#2068); "
            "writes will land in a follow-up slice."
        )

    payload = _build_payload(
        command,
        dry_run=dry_run,
        apply_requested=apply_requested,
        status="scaffold-ack",
        note=(
            "scaffold only; no JSONL parsing, no SurrealDB connection, "
            "no writes performed."
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
