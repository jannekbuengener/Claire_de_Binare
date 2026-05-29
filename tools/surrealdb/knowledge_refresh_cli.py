"""Knowledge Refresh CLI — read-only report, no writes, no DB, no network.

Issues:
    #2717 — [SURREALDB][CONTEXT][REFRESH-LOOP] Add read-only Knowledge Refresh Loop report
    Parent Epic: #1976

Commands:
    report-knowledge-refresh   Generate JSON or Markdown knowledge refresh report

Exit codes:
    0 = success
    2 = CLI / input / validation error

Guardrails:
    - Read-only. Stdout only. No file output from CLI.
    - No DB access. No SurrealDB SDK. No network. No GitHub calls.
    - LR status remains NO-GO for live trading.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.surrealdb.knowledge_refresh_report import (
    SCHEMA_VERSION,
    KnowledgeRefreshReportError,
    generate_knowledge_refresh_report_v1,
)

EXIT_OK = 0
EXIT_ERROR = 2

SUPPORTED_FORMATS = frozenset({"json", "markdown"})


class KnowledgeRefreshCLIError(Exception):
    """CLI validation error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _load_bundle(path: Path) -> dict[str, Any]:
    try:
        exists = path.exists()
    except OSError as exc:
        raise KnowledgeRefreshCLIError(f"cannot stat input file: {path}: {exc}") from exc
    if not exists:
        raise KnowledgeRefreshCLIError(f"input file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise KnowledgeRefreshCLIError(f"cannot read input file: {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KnowledgeRefreshCLIError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise KnowledgeRefreshCLIError("input bundle must be a JSON object")
    return data


def _error_payload(message: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "error": "CLI_ERROR",
        "message": message,
    }


def handle_report_knowledge_refresh(args: argparse.Namespace) -> tuple[Any, int]:
    bundle_path = Path(args.input)
    bundle = _load_bundle(bundle_path)
    report = generate_knowledge_refresh_report_v1(
        bundle,
        as_of=args.as_of,
        include_readiness=not args.no_readiness,
    )
    if args.format == "markdown":
        return report.to_markdown(), EXIT_OK
    return json.loads(report.to_json()), EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledge_refresh_cli",
        description=(
            "Knowledge Refresh CLI (#2717). Read-only local report — "
            "no DB, no network, no writes."
        ),
    )
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="json",
        help="Output format (default: json).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser(
        "report-knowledge-refresh",
        help="Generate knowledge refresh loop report from input bundle.",
    )
    report.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to JSON input bundle.",
    )
    report.add_argument(
        "--as-of",
        dest="as_of",
        default=None,
        metavar="ISO8601",
        help="Optional reference timestamp for deterministic output.",
    )
    report.add_argument(
        "--no-readiness",
        action="store_true",
        default=False,
        help="Omit optional Agent OS readiness summary signal.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command != "report-knowledge-refresh":
            raise KnowledgeRefreshCLIError(f"unknown command: {args.command}")
        payload, exit_code = handle_report_knowledge_refresh(args)
        if args.format == "markdown":
            print(payload)
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code
    except KnowledgeRefreshCLIError as exc:
        print(json.dumps(_error_payload(exc.message), indent=2, sort_keys=True))
        return EXIT_ERROR
    except KnowledgeRefreshReportError as exc:
        print(json.dumps(_error_payload(str(exc)), indent=2, sort_keys=True))
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(_error_payload(str(exc)), indent=2, sort_keys=True))
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
