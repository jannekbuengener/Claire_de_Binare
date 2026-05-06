"""Contradiction Scan CLI — read-only, no writes, no DB, no network.

Issues:
    #2147 — [SURREALDB][CONTEXT][CONTRADICTION-CLI] Add contradiction scan CLI
    Parent: #2145 (Wave-15)
    Depends on: #2146 (contradiction_scan runtime)

Commands:
    scan-contradictions   Scan input bundle, output all findings
    show-contradiction    Show a single finding by contradiction_id
    report-contradictions Generate summary report

Exit codes:
    0 = success (no blocking findings, or --fail-on-blocking not set)
    1 = CLI / input / validation error
    2 = blocking findings found and --fail-on-blocking set

Guardrails:
    - Read-only.  No writes.  No file output.  Stdout only.
    - No DB access.  No SurrealDB SDK.  No network.  No GitHub calls.
    - No direct wall-clock calls / random UUID generation — timestamps via scan service.
    - Detection is signal, not action authority.
    - LR status remains NO-GO for live trading.
    - No auto-fix.  No live-go.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from tools.surrealdb.contradiction_scan import (
    CONTRADICTION_TYPES,
    ContradictionFinding,
    ContradictionScanError,
    ContradictionScanResult,
    scan_contradictions_v1,
)

# ── Constants ─────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "contradiction-cli/v1"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BLOCKING = 2

SUPPORTED_FORMATS = frozenset({"json", "markdown"})

_GUARDRAIL_NOTE = (
    "Detection is signal, not action. "
    "No auto-fix. No live-go. No real-money scope. "
    "LR status remains NO-GO for live trading."
)


# ── Error ─────────────────────────────────────────────────────────────────────


class ContradictionCLIError(Exception):
    """Raised for CLI / input / validation errors (exit 1)."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


# ── Bundle Loader ─────────────────────────────────────────────────────────────


def _load_bundle(path: Path) -> tuple[dict[str, Any], dict[str, str] | None]:
    """Load a JSON input bundle from *path*.

    Returns ``(records, overrides)`` where *overrides* is extracted from the
    top-level ``"overrides"`` key (if present) before passing the rest to the
    scan service.

    Raises:
        ContradictionCLIError: if the file is missing, not valid JSON, or not
            a JSON object (exit 1).
    """
    try:
        exists = path.exists()
    except OSError as exc:
        raise ContradictionCLIError(f"cannot stat input file: {path}: {exc}") from exc

    if not exists:
        raise ContradictionCLIError(f"input file not found: {path}")

    if not path.is_file():
        raise ContradictionCLIError(f"input path is not a file: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContradictionCLIError(f"cannot read input file: {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContradictionCLIError(
            f"input file is not valid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ContradictionCLIError(
            f"input file must be a JSON object (dict), got {type(data).__name__}: {path}"
        )

    overrides_raw = data.pop("overrides", None)
    if overrides_raw is not None:
        if not isinstance(overrides_raw, dict):
            raise ContradictionCLIError(
                f"'overrides' key must be a JSON object, got {type(overrides_raw).__name__}"
            )
        overrides: dict[str, str] | None = {
            str(k): str(v) for k, v in overrides_raw.items()
        }
    else:
        overrides = None

    return data, overrides


# ── Serialization ─────────────────────────────────────────────────────────────


def _finding_to_dict(f: ContradictionFinding) -> dict[str, Any]:
    """Convert a ContradictionFinding dataclass to a plain dict."""
    return dataclasses.asdict(f)


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)


def _derive_report_recommended_reads(
    findings: tuple,
    limit: int = 20,
) -> list[str]:
    """Derive recommended next reads from contradiction findings.

    Blocking findings are prioritised; within each group the order is:
    source_a_ref.path, source_b_ref.path, claim_refs, evidence_ref evidence_ids.
    Deduplicates and caps at *limit* entries.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(value: str) -> None:
        v = value.strip() if value else ""
        if v and v not in seen and len(result) < limit:
            seen.add(v)
            result.append(v)

    for blocking_first in (True, False):
        for f in findings:
            if f.blocking != blocking_first:
                continue
            if f.source_a_ref and f.source_a_ref.path:
                _add(f.source_a_ref.path)
            if f.source_b_ref and f.source_b_ref.path:
                _add(f.source_b_ref.path)
            for cref in (f.claim_refs or ()):
                _add(cref)
            for eref in (f.evidence_refs or ()):
                if eref.evidence_id:
                    _add(eref.evidence_id)

    return result


def _collect_affected_artifacts(findings: tuple) -> list[str]:
    """Collect all affected artifact paths and IDs across all findings.

    Includes source_a/source_b paths, claim_refs, and evidence_ref evidence_ids.
    Returns a deduplicated, sorted list.
    """
    seen: set[str] = set()

    def _add(value: str) -> None:
        v = value.strip() if value else ""
        if v:
            seen.add(v)

    for f in findings:
        if f.source_a_ref and f.source_a_ref.path:
            _add(f.source_a_ref.path)
        if f.source_b_ref and f.source_b_ref.path:
            _add(f.source_b_ref.path)
        for cref in (f.claim_refs or ()):
            _add(cref)
        for eref in (f.evidence_refs or ()):
            if eref.evidence_id:
                _add(eref.evidence_id)

    return sorted(seen)


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render a CLI result payload as a human-readable Markdown report."""
    command = payload.get("command", "unknown")
    status = payload.get("status", "unknown")
    scanned_at = payload.get("scanned_at", "n/a")
    total = payload.get("total_findings", 0)
    blocking = payload.get("blocking_count", 0)

    lines: list[str] = [
        f"# Contradiction Scan — `{command}`",
        "",
        f"- **status**: `{status}`",
        f"- **scanned_at**: `{scanned_at}`",
        f"- **total_findings**: {total}",
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

    # Blocking findings section
    findings = payload.get("findings", [])
    blocking_findings = [f for f in findings if f.get("blocking")]
    if blocking_findings:
        lines += ["## Blocking Findings", ""]
        for f in blocking_findings:
            lines.append(
                f"- **{f['contradiction_id']}** `{f['contradiction_type']}` "
                f"(confidence: {f['confidence']:.2f}): {f['recommended_action']}"
            )
        lines.append("")

    # Summary section (for report-contradictions)
    if "summary" in payload:
        summary = payload["summary"]
        lines += ["## Summary", ""]
        for key, label in (
            ("blocking", "blocking"),
            ("false_positives", "false_positives"),
            ("accepted_risks", "accepted_risks"),
            ("warning", "warning"),
            ("info", "info"),
        ):
            items = summary.get(key, [])
            lines.append(f"- **{label}**: {len(items)}")
        lines.append("")
        if summary.get("blocking"):
            lines += ["### Blocking", ""]
            for f in summary["blocking"]:
                lines.append(
                    f"- `{f['contradiction_id']}` `{f['contradiction_type']}` — "
                    f"{f['recommended_action']}"
                )
            lines.append("")
        if summary.get("false_positives"):
            lines += ["### False Positives", ""]
            for f in summary["false_positives"]:
                lines.append(
                    f"- `{f['contradiction_id']}` `{f['contradiction_type']}` "
                    f"(override: false_positive)"
                )
            lines.append("")
        if summary.get("accepted_risks"):
            lines += ["### Accepted Risks", ""]
            for f in summary["accepted_risks"]:
                lines.append(
                    f"- `{f['contradiction_id']}` `{f['contradiction_type']}` "
                    f"(override: accepted_risk)"
                )
            lines.append("")
        recs = payload.get("recommended_next_reads", [])
        if recs:
            lines += ["## Recommended Next Reads", ""]
            for r in recs:
                lines.append(f"- `{r}`")
            lines.append("")
        affected = payload.get("affected_artifacts", [])
        if affected:
            lines += ["## Affected Artifacts", ""]
            for a in affected:
                lines.append(f"- `{a}`")
            lines.append("")
    elif findings:
        # Full findings table
        lines += ["## All Findings", ""]
        lines.append("| ID | Type | Severity | Blocking | Confidence | Action |")
        lines.append("|---|---|---|---|---|---|")
        for f in findings:
            lines.append(
                f"| `{f['contradiction_id']}` "
                f"| `{f['contradiction_type']}` "
                f"| {f['severity']} "
                f"| {f['blocking']} "
                f"| {f['confidence']:.2f} "
                f"| {f['recommended_action'][:60]}... |"
                if len(f.get("recommended_action", "")) > 60
                else f"| `{f['contradiction_id']}` "
                f"| `{f['contradiction_type']}` "
                f"| {f['severity']} "
                f"| {f['blocking']} "
                f"| {f['confidence']:.2f} "
                f"| {f.get('recommended_action', '')} |"
            )
        lines.append("")

    # Single finding (show-contradiction)
    if "finding" in payload:
        f = payload["finding"]
        lines += ["## Finding", ""]
        lines.append(f"- **id**: `{f['contradiction_id']}`")
        lines.append(f"- **type**: `{f['contradiction_type']}`")
        lines.append(f"- **severity**: {f['severity']}")
        lines.append(f"- **blocking**: {f['blocking']}")
        lines.append(f"- **confidence**: {f['confidence']:.2f}")
        lines.append(f"- **status**: {f['status']}")
        lines.append(f"- **action**: {f['recommended_action']}")
        lines.append("")

    lines.append(f"> ⚠ Guardrail: {_GUARDRAIL_NOTE}")
    return "\n".join(lines)


# ── Handlers ──────────────────────────────────────────────────────────────────


def handle_scan_contradictions(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``scan-contradictions`` subcommand."""
    records, overrides = _load_bundle(Path(args.input))
    result: ContradictionScanResult = scan_contradictions_v1(records, overrides)

    findings = result.findings
    if args.type is not None:
        if args.type not in CONTRADICTION_TYPES:
            raise ContradictionCLIError(
                f"unknown contradiction type: {args.type!r}. "
                f"Valid types: {sorted(CONTRADICTION_TYPES)}"
            )
        findings = tuple(f for f in findings if f.contradiction_type == args.type)

    blocking_count = sum(1 for f in findings if f.blocking)
    payload: dict[str, Any] = {
        "schema_version": result.schema_version,
        "command": "scan-contradictions",
        "status": "ok",
        "scanned_at": result.scanned_at,
        "total_findings": len(findings),
        "blocking_count": blocking_count,
        "findings": [_finding_to_dict(f) for f in findings],
    }
    exit_code = EXIT_OK
    if args.fail_on_blocking and blocking_count > 0:
        exit_code = EXIT_BLOCKING
    return payload, exit_code


def handle_show_contradiction(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``show-contradiction`` subcommand."""
    records, overrides = _load_bundle(Path(args.input))
    result: ContradictionScanResult = scan_contradictions_v1(records, overrides)

    matches = [f for f in result.findings if f.contradiction_id == args.id]
    if not matches:
        raise ContradictionCLIError(
            f"contradiction_id not found: {args.id!r}",
            exit_code=EXIT_ERROR,
        )

    finding = matches[0]
    payload: dict[str, Any] = {
        "schema_version": result.schema_version,
        "command": "show-contradiction",
        "status": "ok",
        "scanned_at": result.scanned_at,
        "finding": _finding_to_dict(finding),
    }
    return payload, EXIT_OK


def handle_report_contradictions(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], int]:
    """Handle the ``report-contradictions`` subcommand."""
    records, overrides = _load_bundle(Path(args.input))
    result: ContradictionScanResult = scan_contradictions_v1(records, overrides)

    blocking = [_finding_to_dict(f) for f in result.findings if f.blocking]
    false_positives = [
        _finding_to_dict(f)
        for f in result.findings
        if f.status == "false_positive"
    ]
    accepted_risks = [
        _finding_to_dict(f)
        for f in result.findings
        if f.status == "accepted_risk"
    ]
    warning = [
        _finding_to_dict(f)
        for f in result.findings
        if f.severity == "warning" and f.status not in ("false_positive", "accepted_risk")
    ]
    info = [
        _finding_to_dict(f)
        for f in result.findings
        if f.severity == "info" and f.status not in ("false_positive", "accepted_risk")
    ]

    payload: dict[str, Any] = {
        "schema_version": result.schema_version,
        "command": "report-contradictions",
        "status": "ok",
        "scanned_at": result.scanned_at,
        "total_findings": result.total_count,
        "blocking_count": result.blocking_count,
        "summary": {
            "blocking": blocking,
            "false_positives": false_positives,
            "accepted_risks": accepted_risks,
            "warning": warning,
            "info": info,
        },
        "recommended_next_reads": _derive_report_recommended_reads(result.findings),
        "affected_artifacts": _collect_affected_artifacts(result.findings),
        "guardrail": _GUARDRAIL_NOTE,
    }
    return payload, EXIT_OK


# ── Argument Parser ───────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contradiction_cli",
        description=(
            "Contradiction Scan CLI (#2147). Read-only local scan — "
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

    # ── scan-contradictions ───────────────────────────────────────────────────
    scan = subparsers.add_parser(
        "scan-contradictions",
        help="Scan input bundle and output all contradiction findings.",
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
        help="Exit with code 2 if any blocking findings are present.",
    )
    scan.add_argument(
        "--type",
        default=None,
        metavar="TYPE",
        help=(
            "Filter output to a specific contradiction type "
            f"(one of: {', '.join(sorted(CONTRADICTION_TYPES))})."
        ),
    )

    # ── show-contradiction ────────────────────────────────────────────────────
    show = subparsers.add_parser(
        "show-contradiction",
        help="Show a single contradiction finding by its contradiction_id.",
    )
    show.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to JSON input bundle.",
    )
    show.add_argument(
        "--id",
        required=True,
        dest="id",
        metavar="CONTRADICTION_ID",
        help="The contradiction_id of the finding to show.",
    )

    # ── report-contradictions ─────────────────────────────────────────────────
    report = subparsers.add_parser(
        "report-contradictions",
        help="Generate a summary report of all contradiction findings.",
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
        if args.command == "scan-contradictions":
            payload, exit_code = handle_scan_contradictions(args)
        elif args.command == "show-contradiction":
            payload, exit_code = handle_show_contradiction(args)
        elif args.command == "report-contradictions":
            payload, exit_code = handle_report_contradictions(args)
        else:
            # argparse required=True makes this unreachable in normal use
            raise ContradictionCLIError(f"unknown command: {args.command}")

        fmt = getattr(args, "format", "json")
        if fmt == "markdown":
            print(_render_markdown(payload))
        else:
            print(_render_json(payload))
        return exit_code

    except ContradictionCLIError as exc:
        print(
            _render_json(_error_payload("CLI_ERROR", exc.message)),
        )
        return exc.exit_code
    except ContradictionScanError as exc:
        print(
            _render_json(_error_payload("SCAN_ERROR", str(exc))),
        )
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 — CLI safety net
        print(
            _render_json(_error_payload("INTERNAL", str(exc))),
        )
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())
