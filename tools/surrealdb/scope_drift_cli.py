"""Scope Drift Check CLI — read-only, no writes, no DB, no network.

Issues:
    #2164 — [SURREALDB][CONTEXT][SCOPE-CLI] Add scope drift check CLI
    Parent: #2162 (Wave-17 anchor)
    Depends on: #2163 (scope_drift_firewall service, merged via PR #2376)
    Epic: #1976

Commands:
    scan-scope-drift    Scan input bundle, output all findings
    show-scope-drift    Show a single finding by drift_id
    report-scope-drift  Generate summary report

Exit codes:
    0 = success (or blocking findings without --fail-on-blocking)
    1 = blocking findings found and --fail-on-blocking set
    2 = CLI / input / validation error
    3 = show-scope-drift: drift_id not found

Guardrails:
    - Read-only.  No writes.  No file output.  Stdout only.
    - No DB access.  No SurrealDB SDK.  No network.  No GitHub calls.
    - No direct wall-clock calls — as_of via bundle meta (cdb_utcnow in service).
    - Detection is signal, not action authority.
    - LR status remains NO-GO for live trading.
    - No auto-fix.  No live-go.  No Echtgeld-Go.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.surrealdb.scope_drift_blocking import build_blocking_output, render_blocking_markdown
from tools.surrealdb.scope_drift_firewall import (
    DRIFT_TYPES,
    GUARDRAILS,
    ScopeDriftFirewallError,
    scan_scope_drift_v1,
)

# ── Constants ─────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "scope-drift-cli/v1"

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


class ScopeDriftCLIError(Exception):
    """Raised for CLI / input / validation errors (exit 2) or not-found (exit 3)."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


# ── Bundle Loader ─────────────────────────────────────────────────────────────


def _load_bundle(path: Path) -> tuple[dict[str, Any], str | None]:
    """Load a JSON input bundle from *path*.

    Reads the top-level ``"meta"`` key (if present) and extracts an advisory
    ``as_of`` timestamp from it WITHOUT mutating the bundle dict.  The full
    bundle (including meta) is returned so that the firewall service can read
    ``bundle["meta"]`` for the ``missing_human_go`` rule.

    The ``as_of`` string is passed to ``scan_scope_drift_v1`` so that
    time-based rules use a deterministic reference time from the bundle rather
    than direct wall-clock time.

    Raises:
        ScopeDriftCLIError: if the file is missing, unreadable, not valid JSON,
            or not a JSON object (exit 2).
    """
    try:
        exists = path.exists()
    except OSError as exc:
        raise ScopeDriftCLIError(f"cannot stat input file: {path}: {exc}") from exc

    if not exists:
        raise ScopeDriftCLIError(f"input file not found: {path}")

    if not path.is_file():
        raise ScopeDriftCLIError(f"input path is not a file: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScopeDriftCLIError(f"cannot read input file: {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScopeDriftCLIError(
            f"input file is not valid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ScopeDriftCLIError(
            f"input file must be a JSON object (dict), got {type(data).__name__}: {path}"
        )

    # Extract as_of from meta WITHOUT mutating the bundle (service reads meta internally)
    as_of: str | None = None
    meta = data.get("meta")
    if isinstance(meta, dict):
        raw_as_of = meta.get("as_of")
        if isinstance(raw_as_of, str) and raw_as_of.strip():
            as_of = raw_as_of.strip()

    return data, as_of


# ── Serialization ─────────────────────────────────────────────────────────────


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)


def _severity_summary_from_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {"info": 0, "warning": 0, "blocking": 0}
    for f in findings:
        sev = f.get("severity", "")
        if sev in summary:
            summary[sev] += 1
    return summary


def _drift_type_summary_from_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {t: 0 for t in sorted(DRIFT_TYPES)}
    for f in findings:
        dt = f.get("drift_type", "")
        if dt in summary:
            summary[dt] += 1
    return summary


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render a CLI result payload as a human-readable Markdown report."""
    command = payload.get("command", "unknown")
    status = payload.get("status", "unknown")
    scanned_at = payload.get("scanned_at", "n/a")
    total = payload.get("total_count", 0)
    blocking = payload.get("blocking_count", 0)

    lines: list[str] = [
        f"# Scope Drift Scan — `{command}`",
        "",
        f"- **status**: `{status}`",
        f"- **scanned_at**: `{scanned_at}`",
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

    # Drift type summary (report only)
    dt_summary = payload.get("drift_type_summary")
    if dt_summary:
        lines += ["## Drift Type Summary", ""]
        for drift_type, count in sorted(dt_summary.items()):
            lines.append(f"- **{drift_type}**: {count}")
        lines.append("")

    # Blocking findings section
    blocking_findings = payload.get("blocking_findings") or [
        f for f in payload.get("findings", []) if f.get("human_go_required")
    ]
    if blocking_findings:
        lines += ["## Blocking Findings", ""]
        for f in blocking_findings:
            stop = f.get("stop_conditions", [])
            stop_str = stop[0] if stop else f.get("required_action", "")
            lines.append(
                f"- **{f['drift_id']}** `{f['drift_type']}` "
                f"({f['required_action']}): {stop_str}"
            )
        lines.append("")

    # All findings table (scan-scope-drift only)
    findings = payload.get("findings", [])
    if findings:
        lines += ["## All Findings", ""]
        lines.append("| ID | Type | Severity | Blocking | Action | Observed |")
        lines.append("|---|---|---|---|---|---|")
        for f in findings:
            lines.append(
                f"| `{f['drift_id']}` "
                f"| `{f['drift_type']}` "
                f"| {f['severity']} "
                f"| {f['human_go_required']} "
                f"| {f['required_action']} "
                f"| {f.get('observed_scope', '')} |"
            )
        lines.append("")

    # Single finding (show-scope-drift)
    if "finding" in payload:
        f = payload["finding"]
        lines += ["## Finding", ""]
        lines.append(f"- **drift_id**: `{f['drift_id']}`")
        lines.append(f"- **drift_type**: `{f['drift_type']}`")
        lines.append(f"- **severity**: {f['severity']}")
        lines.append(f"- **blocking**: {f['human_go_required']}")
        lines.append(f"- **required_action**: {f['required_action']}")
        lines.append(f"- **status**: {f['status']}")
        lines.append(f"- **allowed_scope**: {f['allowed_scope']}")
        lines.append(f"- **observed_scope**: {f['observed_scope']}")
        stop = f.get("stop_conditions", [])
        if stop:
            lines.append(f"- **stop_conditions**: {stop[0]}")
        reads = f.get("recommended_next_reads", [])
        if reads:
            lines += ["", "### Recommended Next Reads", ""]
            for r in reads:
                lines.append(f"- `{r}`")
        lines.append("")

    # Recommended next reads (report only — aggregated)
    recs = payload.get("recommended_next_reads", [])
    if recs:
        lines += ["## Recommended Next Reads", ""]
        for r in recs:
            lines.append(f"- {r}")
        lines.append("")

    # Blocking output section (Wave 17-D — report command only)
    blocking_output = payload.get("blocking_output")
    if blocking_output:
        lines.append(render_blocking_markdown(blocking_output))

    # Guardrails — always present
    guardrails = payload.get("guardrails", list(GUARDRAILS))
    lines += ["## Guardrails", ""]
    for g in guardrails:
        lines.append(f"- {g}")
    lines.append("")

    lines.append(f"> ⚠ Guardrail: {_GUARDRAIL_NOTE}")
    return "\n".join(lines)


# ── Handlers ──────────────────────────────────────────────────────────────────


def handle_scan_scope_drift(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``scan-scope-drift`` subcommand."""
    bundle, as_of = _load_bundle(Path(args.input))
    result = scan_scope_drift_v1(bundle, as_of=as_of)

    findings_dicts = [f.to_dict() for f in result.findings]
    sev_summary = _severity_summary_from_findings(findings_dicts)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "scan-scope-drift",
        "status": result.status,
        "scanned_at": result.scanned_at,
        "total_count": len(result.findings),
        "blocking_count": result.blocking_count,
        "severity_summary": sev_summary,
        "findings": findings_dicts,
        "guardrails": list(result.guardrails),
    }
    exit_code = EXIT_OK
    if args.fail_on_blocking and result.blocking_count > 0:
        exit_code = EXIT_BLOCKING
    return payload, exit_code


def handle_show_scope_drift(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-scope-drift`` subcommand."""
    bundle, as_of = _load_bundle(Path(args.input))
    result = scan_scope_drift_v1(bundle, as_of=as_of)

    matches = [f for f in result.findings if f.drift_id == args.drift_id]
    if not matches:
        raise ScopeDriftCLIError(
            f"drift_id not found: {args.drift_id!r}",
            exit_code=EXIT_NOT_FOUND,
        )

    finding = matches[0]
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "show-scope-drift",
        "status": "ok",
        "scanned_at": result.scanned_at,
        "finding": finding.to_dict(),
    }
    return payload, EXIT_OK


def handle_report_scope_drift(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``report-scope-drift`` subcommand."""
    bundle, as_of = _load_bundle(Path(args.input))
    result = scan_scope_drift_v1(bundle, as_of=as_of)

    findings_dicts = [f.to_dict() for f in result.findings]
    sev_summary = _severity_summary_from_findings(findings_dicts)
    dt_summary = _drift_type_summary_from_findings(findings_dicts)
    blocking_findings = [d for d in findings_dicts if d.get("human_go_required")]

    # Aggregate recommended_next_reads across all findings (deduplicated, stable order)
    seen: set[str] = set()
    agg_reads: list[str] = []
    for f in result.findings:
        for r in f.recommended_next_reads:
            if r not in seen:
                seen.add(r)
                agg_reads.append(r)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": "report-scope-drift",
        "status": result.status,
        "scanned_at": result.scanned_at,
        "total_count": len(result.findings),
        "blocking_count": result.blocking_count,
        "severity_summary": sev_summary,
        "drift_type_summary": dt_summary,
        "blocking_findings": blocking_findings,
        "recommended_next_reads": agg_reads,
        "guardrails": list(result.guardrails),
    }
    if result.blocking_count > 0:
        payload["blocking_output"] = build_blocking_output(result)
    return payload, EXIT_OK


# ── Argument Parser ───────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scope_drift_cli",
        description=(
            "Scope Drift Check CLI (#2164). Read-only local scan — "
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

    # ── scan-scope-drift ──────────────────────────────────────────────────────
    scan = subparsers.add_parser(
        "scan-scope-drift",
        help="Scan input bundle and output all scope drift findings.",
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

    # ── show-scope-drift ──────────────────────────────────────────────────────
    show = subparsers.add_parser(
        "show-scope-drift",
        help="Show a single scope drift finding by its drift_id.",
    )
    show.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to JSON input bundle.",
    )
    show.add_argument(
        "--drift-id",
        required=True,
        dest="drift_id",
        metavar="DRIFT_ID",
        help="The drift_id of the finding to show.",
    )

    # ── report-scope-drift ────────────────────────────────────────────────────
    report = subparsers.add_parser(
        "report-scope-drift",
        help="Generate a summary report of all scope drift findings.",
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
        if args.command == "scan-scope-drift":
            payload, exit_code = handle_scan_scope_drift(args)
        elif args.command == "show-scope-drift":
            payload, exit_code = handle_show_scope_drift(args)
        elif args.command == "report-scope-drift":
            payload, exit_code = handle_report_scope_drift(args)
        else:
            # argparse required=True makes this unreachable in normal use
            raise ScopeDriftCLIError(f"unknown command: {args.command}")

        fmt = getattr(args, "format", "json")
        if fmt == "markdown":
            print(_render_markdown(payload))
        else:
            print(_render_json(payload))
        return exit_code

    except ScopeDriftCLIError as exc:
        print(_render_json(_error_payload("CLI_ERROR", exc.message)))
        return exc.exit_code
    except ScopeDriftFirewallError as exc:
        print(_render_json(_error_payload("SCAN_ERROR", str(exc))))
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 — CLI safety net
        print(_render_json(_error_payload("INTERNAL", str(exc))))
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())
