"""Stale Context CLI — read-only, no writes, no DB, no network.

Issues:
    #2155 — [SURREALDB][CONTEXT][STALE-CLI] Add stale context CLI
    Parent: #2153 (Wave-16 anchor)
    Depends on: #2154 (stale_knowledge_scan service, merged via PR #2368)
    Epic: #1976

Commands:
    scan-stale-context    Scan input bundle, output all findings
    show-stale-context    Show a single finding by stale_id
    report-stale-context  Generate summary report

Exit codes:
    0 = success (or blocking findings without --fail-on-blocking)
    1 = blocking findings found and --fail-on-blocking set
    2 = CLI / input / validation error
    3 = show-stale-context: stale_id not found

Guardrails:
    - Read-only.  No writes.  No file output.  Stdout only.
    - No DB access.  No SurrealDB SDK.  No network.  No GitHub calls.
    - No direct wall-clock calls — as_of via bundle meta or scan service (cdb_utcnow).
    - Detection is signal, not action authority.
    - LR status remains NO-GO for live trading.
    - No auto-fix.  No live-go.  No Echtgeld-Go.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from tools.surrealdb.stale_knowledge_scan import (
    GUARDRAILS,
    STALE_TYPES,
    StaleFinding,
    StaleKnowledgeScanError,
    StaleKnowledgeScanResult,
    scan_stale_knowledge_v1,
)

# ── Constants ─────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "stale-context-cli/v1"

EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_ERROR = 2
EXIT_NOT_FOUND = 3

SUPPORTED_FORMATS = frozenset({"json", "markdown"})

_GUARDRAIL_NOTE = (
    "Detection is signal, not action. "
    "No auto-fix. No live-go. No real-money scope. "
    "LR status remains NO-GO for live trading."
)


# ── Error ─────────────────────────────────────────────────────────────────────


class StaleCLIError(Exception):
    """Raised for CLI / input / validation errors (exit 2) or not-found (exit 3)."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


# ── Bundle Loader ─────────────────────────────────────────────────────────────


def _load_bundle(path: Path) -> tuple[dict[str, Any], str | None]:
    """Load a JSON input bundle from *path*.

    Pops the top-level ``"meta"`` key (if present) and extracts an advisory
    ``as_of`` timestamp from it.  The remaining data dict is returned together
    with the extracted ``as_of`` string (or ``None`` if absent/invalid).

    The ``as_of`` string is passed to ``scan_stale_knowledge_v1`` so that
    time-based rules use a deterministic reference time from the bundle rather
    than direct wall-clock time.

    Raises:
        StaleCLIError: if the file is missing, unreadable, not valid JSON, or
            not a JSON object (exit 2).
    """
    try:
        exists = path.exists()
    except OSError as exc:
        raise StaleCLIError(f"cannot stat input file: {path}: {exc}") from exc

    if not exists:
        raise StaleCLIError(f"input file not found: {path}")

    if not path.is_file():
        raise StaleCLIError(f"input path is not a file: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StaleCLIError(f"cannot read input file: {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StaleCLIError(
            f"input file is not valid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise StaleCLIError(
            f"input file must be a JSON object (dict), got {type(data).__name__}: {path}"
        )

    meta = data.pop("meta", None)
    as_of: str | None = None
    if isinstance(meta, dict):
        raw_as_of = meta.get("as_of")
        if isinstance(raw_as_of, str) and raw_as_of.strip():
            as_of = raw_as_of.strip()

    return data, as_of


# ── Serialization ─────────────────────────────────────────────────────────────


def _finding_to_dict(f: StaleFinding) -> dict[str, Any]:
    """Convert a StaleFinding dataclass to a plain dict."""
    return dataclasses.asdict(f)


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)


def _severity_summary_from_findings(findings: tuple[StaleFinding, ...]) -> dict[str, int]:
    summary: dict[str, int] = {"info": 0, "warning": 0, "blocking": 0}
    for f in findings:
        if f.severity in summary:
            summary[f.severity] += 1
    return summary


def _stale_type_summary_from_findings(findings: tuple[StaleFinding, ...]) -> dict[str, int]:
    summary: dict[str, int] = {t: 0 for t in sorted(STALE_TYPES)}
    for f in findings:
        if f.stale_type in summary:
            summary[f.stale_type] += 1
    return summary


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render a CLI result payload as a human-readable Markdown report."""
    command = payload.get("command", "unknown")
    status = payload.get("status", "unknown")
    as_of = payload.get("as_of", "n/a")
    total = payload.get("total_count", 0)
    blocking = payload.get("blocking_count", 0)

    lines: list[str] = [
        f"# Stale Context Scan — `{command}`",
        "",
        f"- **status**: `{status}`",
        f"- **as_of**: `{as_of}`",
        f"- **total_count**: {total}",
        f"- **blocking_count**: {blocking}",
        "",
    ]

    # Error case
    if status == "error":
        lines += [
            "## Error",
            "",
            f"**{payload.get('error', 'UNKNOWN')}**: {payload.get('message', '')}",
            "",
        ]
        lines.append(f"> ⚠ Guardrail: {_GUARDRAIL_NOTE}")
        return "\n".join(lines)

    # Severity summary
    sev = payload.get("severity_summary", {})
    if sev:
        lines += ["## Severity Summary", ""]
        for level in ("info", "warning", "blocking"):
            lines.append(f"- **{level}**: {sev.get(level, 0)}")
        lines.append("")

    # Stale type summary (report only)
    st_summary = payload.get("stale_type_summary")
    if st_summary:
        lines += ["## Stale Type Summary", ""]
        for t, count in sorted(st_summary.items()):
            lines.append(f"- **{t}**: {count}")
        lines.append("")

    # Blocking findings section
    blocking_findings = payload.get("blocking_findings") or [
        f for f in payload.get("findings", []) if f.get("blocking")
    ]
    if blocking_findings:
        lines += ["## Blocking Findings", ""]
        for f in blocking_findings:
            lines.append(
                f"- **{f['stale_id']}** `{f['stale_type']}` "
                f"(confidence: {f['confidence']:.2f}): {f['recommended_refresh']}"
            )
        lines.append("")

    # All findings table (scan-stale-context only)
    findings = payload.get("findings", [])
    if findings:
        lines += ["## All Findings", ""]
        lines.append("| ID | Type | Severity | Blocking | Confidence | Target |")
        lines.append("|---|---|---|---|---|---|")
        for f in findings:
            lines.append(
                f"| `{f['stale_id']}` "
                f"| `{f['stale_type']}` "
                f"| {f['severity']} "
                f"| {f['blocking']} "
                f"| {f['confidence']:.2f} "
                f"| {f.get('target_ref', '')} |"
            )
        lines.append("")

    # Single finding (show-stale-context)
    if "finding" in payload:
        f = payload["finding"]
        lines += ["## Finding", ""]
        lines.append(f"- **stale_id**: `{f['stale_id']}`")
        lines.append(f"- **stale_type**: `{f['stale_type']}`")
        lines.append(f"- **target_ref**: {f['target_ref']}")
        lines.append(f"- **severity**: {f['severity']}")
        lines.append(f"- **blocking**: {f['blocking']}")
        lines.append(f"- **confidence**: {f['confidence']:.2f}")
        lines.append(f"- **status**: {f['status']}")
        lines.append(f"- **reason**: {f['reason']}")
        lines.append(f"- **recommended_refresh**: {f['recommended_refresh']}")
        lines.append("")

    # Recommended refresh
    recs = payload.get("recommended_refresh", [])
    if recs:
        lines += ["## Recommended Refresh", ""]
        for r in recs:
            lines.append(f"- {r}")
        lines.append("")

    # Guardrails — always present
    guardrails = payload.get("guardrails", list(GUARDRAILS))
    lines += ["## Guardrails", ""]
    for g in guardrails:
        lines.append(f"- {g}")
    lines.append("")

    lines.append(f"> ⚠ Guardrail: {_GUARDRAIL_NOTE}")
    return "\n".join(lines)


# ── Handlers ──────────────────────────────────────────────────────────────────


def handle_scan_stale_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``scan-stale-context`` subcommand."""
    data, as_of = _load_bundle(Path(args.input))
    result: StaleKnowledgeScanResult = scan_stale_knowledge_v1(data, as_of=as_of)

    sev_summary = _severity_summary_from_findings(result.findings)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "scan-stale-context",
        "status": "ok",
        "as_of": result.as_of,
        "total_count": result.total_count,
        "blocking_count": result.blocking_count,
        "severity_summary": sev_summary,
        "findings": [_finding_to_dict(f) for f in result.findings],
        "recommended_refresh": list(result.recommended_refresh),
        "guardrails": list(result.guardrails),
    }
    exit_code = EXIT_OK
    if args.fail_on_blocking and result.blocking_count > 0:
        exit_code = EXIT_BLOCKING
    return payload, exit_code


def handle_show_stale_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-stale-context`` subcommand."""
    data, as_of = _load_bundle(Path(args.input))
    result: StaleKnowledgeScanResult = scan_stale_knowledge_v1(data, as_of=as_of)

    matches = [f for f in result.findings if f.stale_id == args.stale_id]
    if not matches:
        raise StaleCLIError(
            f"stale_id not found: {args.stale_id!r}",
            exit_code=EXIT_NOT_FOUND,
        )

    finding = matches[0]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "show-stale-context",
        "status": "ok",
        "as_of": result.as_of,
        "finding": _finding_to_dict(finding),
    }
    return payload, EXIT_OK


def handle_report_stale_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``report-stale-context`` subcommand."""
    data, as_of = _load_bundle(Path(args.input))
    result: StaleKnowledgeScanResult = scan_stale_knowledge_v1(data, as_of=as_of)

    sev_summary = _severity_summary_from_findings(result.findings)
    st_summary = _stale_type_summary_from_findings(result.findings)
    blocking_findings = [_finding_to_dict(f) for f in result.findings if f.blocking]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "report-stale-context",
        "status": "ok",
        "as_of": result.as_of,
        "total_count": result.total_count,
        "blocking_count": result.blocking_count,
        "severity_summary": sev_summary,
        "stale_type_summary": st_summary,
        "blocking_findings": blocking_findings,
        "recommended_refresh": list(result.recommended_refresh),
        "guardrails": list(result.guardrails),
    }
    return payload, EXIT_OK


# ── Argument Parser ───────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stale_context_cli",
        description=(
            "Stale Context CLI (#2155). Read-only local scan — "
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

    # ── scan-stale-context ────────────────────────────────────────────────────
    scan = subparsers.add_parser(
        "scan-stale-context",
        help="Scan input bundle and output all stale-knowledge findings.",
    )
    scan.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to JSON input bundle.",
    )
    scan.add_argument(
        "--fail-on-blocking",
        action="store_true",
        default=False,
        help="Exit with code 1 if any blocking findings are present.",
    )

    # ── show-stale-context ────────────────────────────────────────────────────
    show = subparsers.add_parser(
        "show-stale-context",
        help="Show a single stale-knowledge finding by its stale_id.",
    )
    show.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to JSON input bundle.",
    )
    show.add_argument(
        "--stale-id",
        required=True,
        dest="stale_id",
        metavar="STALE_ID",
        help="The stale_id of the finding to show.",
    )

    # ── report-stale-context ──────────────────────────────────────────────────
    report = subparsers.add_parser(
        "report-stale-context",
        help="Generate a summary report of all stale-knowledge findings.",
    )
    report.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to JSON input bundle.",
    )

    return parser


# ── Error Payload ─────────────────────────────────────────────────────────────


def _error_payload(error_code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "error": error_code,
        "message": message,
    }


# ── Main Entry Point ──────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns integer exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "scan-stale-context":
            payload, exit_code = handle_scan_stale_context(args)
        elif args.command == "show-stale-context":
            payload, exit_code = handle_show_stale_context(args)
        elif args.command == "report-stale-context":
            payload, exit_code = handle_report_stale_context(args)
        else:
            # argparse required=True makes this unreachable in normal use
            raise StaleCLIError(f"unknown command: {args.command}")

        fmt = getattr(args, "format", "json")
        if fmt == "markdown":
            print(_render_markdown(payload))
        else:
            print(_render_json(payload))
        return exit_code

    except StaleCLIError as exc:
        print(_render_json(_error_payload("CLI_ERROR", exc.message)))
        return exc.exit_code
    except StaleKnowledgeScanError as exc:
        print(_render_json(_error_payload("SCAN_ERROR", str(exc))))
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 — CLI safety net
        print(_render_json(_error_payload("INTERNAL", str(exc))))
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())
