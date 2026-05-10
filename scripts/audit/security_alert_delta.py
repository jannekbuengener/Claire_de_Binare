#!/usr/bin/env python3
"""Read-only delta analysis for GitHub security alert readouts.

Compares two ``github_security_quality_readout.v1`` JSON files (previous and
current) and emits a structured delta report identifying:

- new alerts: alerts present in current but not in previous (by source + number)
- resolved alerts: previously-open alerts no longer open in current
- new alert groups: unique (source, subject, branch) tuples new in current
- escalation status: True if any new open Critical/High alert exists
- secret_scanning delta: surface-status change only (no payload comparison)

Design invariants:
- Read-only: reads JSON files, writes delta JSON/Markdown to ``--out-dir``.
- No GitHub API calls.
- secret_scanning: only surface-status comparison, never payload fields.
- Fail-closed: missing or malformed input JSON is an explicit error.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "security_alert_delta.v1"

# Severity labels that trigger escalation (covers CodeQL "error" → high,
# Dependabot "critical"/"high" labels, and CodeQL explicit "critical"/"high").
ESCALATION_SEVERITIES: frozenset[str] = frozenset({"critical", "high", "error"})

OPEN_STATES: frozenset[str] = frozenset({"open"})

# Sources with numbered alerts that can be delta-compared.
NUMBERED_SOURCES: frozenset[str] = frozenset({"code_scanning", "dependabot"})


class SecurityAlertDeltaError(ValueError):
    """Raised when delta input is invalid or unreadable."""


@dataclass(frozen=True)
class AlertKey:
    source: str
    number: int


@dataclass(frozen=True)
class AlertGroupKey:
    source: str
    subject: str
    branch: str


@dataclass
class DeltaResult:
    """Internal delta computation result (not persisted directly)."""

    new_alerts: list[dict[str, Any]] = field(default_factory=list)
    resolved_keys: list[AlertKey] = field(default_factory=list)
    new_groups: list[AlertGroupKey] = field(default_factory=list)
    escalation_needed: bool = False
    escalation_alerts: list[dict[str, Any]] = field(default_factory=list)
    secret_scanning_status_change: str | None = None
    prev_reference_now_utc: str = ""
    current_reference_now_utc: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_readout(path: Path) -> dict[str, Any]:
    """Load and validate a github_security_quality_readout JSON file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SecurityAlertDeltaError(f"Cannot read {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SecurityAlertDeltaError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SecurityAlertDeltaError(
            f"Readout root must be a JSON object: {path}"
        )
    schema: object = data.get("schema_version", "")
    if not isinstance(schema, str) or not schema.startswith(
        "github_security_quality_readout"
    ):
        raise SecurityAlertDeltaError(
            f"Unexpected schema_version '{schema}' in {path}; "
            "expected github_security_quality_readout.*"
        )
    return data


def _extract_numbered_alerts(
    readout: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return alerts from numbered sources (code_scanning, dependabot) only."""
    alerts = readout.get("alerts", [])
    if not isinstance(alerts, list):
        return []
    return [
        a
        for a in alerts
        if isinstance(a, dict)
        and a.get("source") in NUMBERED_SOURCES
        and isinstance(a.get("number"), int)
    ]


def _extract_surface_status(readout: dict[str, Any], source: str) -> str | None:
    """Return the status string for a given surface, or None if not found."""
    surfaces = readout.get("surfaces", [])
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("source") == source:
            return str(surface.get("status", "unknown"))
    return None


def _alert_key(alert: dict[str, Any]) -> AlertKey:
    return AlertKey(
        source=str(alert["source"]),
        number=int(alert["number"]),
    )


def _group_key(alert: dict[str, Any]) -> AlertGroupKey:
    return AlertGroupKey(
        source=str(alert.get("source", "unknown")),
        subject=str(alert.get("subject") or alert.get("rule_or_advisory") or "unknown"),
        branch=str(alert.get("branch") or "not_provided"),
    )


def _sanitize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized dict containing only safe, non-sensitive alert fields.

    Strips all payload, URL, and raw-content fields from the alert object.
    Only code_scanning and dependabot alerts (never secret_scanning) are
    passed here, enforced by the NUMBERED_SOURCES filter upstream.
    """
    return {
        "source": str(alert.get("source", "")),
        "number": int(alert["number"]),
        "state": str(alert.get("state", "")),
        "severity": str(alert.get("severity", "")),
        "subject": str(alert.get("subject") or alert.get("rule_or_advisory") or ""),
        "branch": str(alert.get("branch") or ""),
        "affected_component": str(alert.get("affected_component") or ""),
    }


# ---------------------------------------------------------------------------
# Core delta computation
# ---------------------------------------------------------------------------


def compute_delta(
    *,
    prev_readout: dict[str, Any],
    current_readout: dict[str, Any],
) -> DeltaResult:
    """Compute the delta between two readout dicts.

    Args:
        prev_readout: Parsed previous readout JSON.
        current_readout: Parsed current readout JSON.

    Returns:
        A :class:`DeltaResult` with all delta fields populated.
    """
    result = DeltaResult(
        prev_reference_now_utc=str(prev_readout.get("reference_now_utc", "")),
        current_reference_now_utc=str(current_readout.get("reference_now_utc", "")),
    )

    prev_alerts = _extract_numbered_alerts(prev_readout)
    current_alerts = _extract_numbered_alerts(current_readout)

    # Key sets
    prev_keys: set[AlertKey] = {_alert_key(a) for a in prev_alerts}
    current_keys: set[AlertKey] = {_alert_key(a) for a in current_alerts}

    prev_open_keys: set[AlertKey] = {
        _alert_key(a) for a in prev_alerts if a.get("state") in OPEN_STATES
    }
    current_open_keys: set[AlertKey] = {
        _alert_key(a) for a in current_alerts if a.get("state") in OPEN_STATES
    }

    # New alerts: in current but not in previous
    new_keys = current_keys - prev_keys
    current_by_key: dict[AlertKey, dict[str, Any]] = {
        _alert_key(a): a for a in current_alerts
    }
    result.new_alerts = sorted(
        (_sanitize_alert(current_by_key[k]) for k in new_keys),
        key=lambda a: (a["source"], a["number"]),
    )

    # Resolved: previously open but no longer open in current
    resolved_keys = prev_open_keys - current_open_keys
    result.resolved_keys = sorted(
        resolved_keys, key=lambda k: (k.source, k.number)
    )

    # New alert groups: (source, subject, branch) tuples new in current
    prev_groups: set[AlertGroupKey] = {_group_key(a) for a in prev_alerts}
    current_groups: set[AlertGroupKey] = {_group_key(a) for a in current_alerts}
    new_group_keys = current_groups - prev_groups
    result.new_groups = sorted(
        new_group_keys, key=lambda g: (g.source, g.subject, g.branch)
    )

    # Escalation: new alerts that are open AND severity is Critical/High
    escalation_alerts = [
        a
        for a in result.new_alerts
        if a["state"] in OPEN_STATES
        and a["severity"].lower() in ESCALATION_SEVERITIES
    ]
    result.escalation_needed = bool(escalation_alerts)
    result.escalation_alerts = escalation_alerts

    # Secret-scanning: surface-status comparison only (never payload)
    prev_secret_status = _extract_surface_status(prev_readout, "secret_scanning")
    current_secret_status = _extract_surface_status(
        current_readout, "secret_scanning"
    )
    if prev_secret_status != current_secret_status:
        result.secret_scanning_status_change = (
            f"prev={prev_secret_status} → current={current_secret_status}"
        )

    return result


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def _safe_readout_meta(readout: dict[str, Any]) -> dict[str, Any]:
    """Extract only non-sensitive scalar metadata from a raw readout dict.

    Never returns alert payloads or any potentially sensitive field.
    Use this to break the taint chain from raw readout data before passing
    information to reporting or storage functions.
    """
    summary = readout.get("summary")
    total = 0
    if isinstance(summary, dict):
        try:
            total = int(summary.get("total_alerts", 0))
        except (TypeError, ValueError):
            total = 0
    return {
        "status": str(readout.get("status", "unknown")),
        "total_alerts": total,
    }


def build_delta_report(
    *,
    prev_path: Path,
    current_path: Path,
    delta: DeltaResult,
    prev_meta: dict[str, Any],
    current_meta: dict[str, Any],
) -> dict[str, Any]:
    """Build the persistable delta report dict (schema_version = security_alert_delta.v1)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "prev_readout": {
            "path": str(prev_path),
            "reference_now_utc": delta.prev_reference_now_utc,
            "status": prev_meta["status"],
            "total_alerts": prev_meta["total_alerts"],
        },
        "current_readout": {
            "path": str(current_path),
            "reference_now_utc": delta.current_reference_now_utc,
            "status": current_meta["status"],
            "total_alerts": current_meta["total_alerts"],
        },
        "new_alert_count": len(delta.new_alerts),
        "new_alerts": [
            {
                "source": a["source"],
                "number": a["number"],
                "state": a["state"],
                "severity": a["severity"],
                "subject": a["subject"],
                "branch": a["branch"],
                "affected_component": a["affected_component"],
            }
            for a in delta.new_alerts
        ],
        "resolved_alert_count": len(delta.resolved_keys),
        "resolved_alerts": [
            {"source": k.source, "number": k.number}
            for k in delta.resolved_keys
        ],
        "new_group_count": len(delta.new_groups),
        "new_groups": [
            {"source": g.source, "subject": g.subject, "branch": g.branch}
            for g in delta.new_groups
        ],
        "escalation_needed": delta.escalation_needed,
        "escalation_alert_count": len(delta.escalation_alerts),
        "escalation_alerts": [
            {
                "source": a["source"],
                "number": a["number"],
                "severity": a["severity"],
                "subject": a["subject"],
                "branch": a["branch"],
            }
            for a in delta.escalation_alerts
        ],
        "secret_scanning_status_change": delta.secret_scanning_status_change,
    }


def build_markdown_summary(delta_report: dict[str, Any]) -> str:
    """Build a human-readable Markdown summary of the delta report."""
    prev = delta_report["prev_readout"]
    current = delta_report["current_readout"]

    lines: list[str] = [
        "## Security Alert Delta",
        "",
        f"- **Prev:** `{prev['reference_now_utc']}` "
        f"— {prev['total_alerts']} total alerts ({prev['status']})",
        f"- **Current:** `{current['reference_now_utc']}` "
        f"— {current['total_alerts']} total alerts ({current['status']})",
        "",
    ]

    if delta_report["escalation_needed"]:
        lines += [
            "### :rotating_light: ESCALATION — New Critical/High Open Alerts",
            "",
            "| Source | # | Severity | Subject | Branch |",
            "|--------|---|----------|---------|--------|",
        ]
        for a in delta_report["escalation_alerts"]:
            lines.append(
                f"| {a['source']} | {a['number']} | **{a['severity']}** "
                f"| `{a['subject']}` | {a['branch']} |"
            )
        lines.append("")
    else:
        lines += [
            "### :white_check_mark: No new Critical/High alerts",
            "",
        ]

    lines += [
        f"- New alerts detected: **{delta_report['new_alert_count']}**",
        f"- Resolved since prev: **{delta_report['resolved_alert_count']}**",
        f"- New alert groups: **{delta_report['new_group_count']}**",
    ]

    if delta_report.get("secret_scanning_status_change"):
        lines.append(
            f"- Secret scanning surface change: "
            f"`{delta_report['secret_scanning_status_change']}`"
        )

    if delta_report["new_groups"]:
        lines += [
            "",
            "### New Alert Groups",
            "",
            "| Source | Subject | Branch |",
            "|--------|---------|--------|",
        ]
        for g in delta_report["new_groups"]:
            lines.append(f"| {g['source']} | `{g['subject']}` | {g['branch']} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# High-level entry points
# ---------------------------------------------------------------------------


def generate_delta(
    *,
    prev_path: Path,
    current_path: Path,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Load two readout files, compute delta, optionally write artifacts.

    Args:
        prev_path: Path to the previous readout JSON.
        current_path: Path to the current readout JSON.
        out_dir: If given, write ``security_alert_delta.json`` and
            ``security_alert_delta.md`` here.

    Returns:
        The delta report dict.

    Raises:
        SecurityAlertDeltaError: If either readout cannot be loaded.
    """
    prev_readout = _load_readout(prev_path)
    current_readout = _load_readout(current_path)
    delta = compute_delta(prev_readout=prev_readout, current_readout=current_readout)
    report = build_delta_report(
        prev_path=prev_path,
        current_path=current_path,
        delta=delta,
        prev_meta=_safe_readout_meta(prev_readout),
        current_meta=_safe_readout_meta(current_readout),
    )

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "security_alert_delta.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out_dir / "security_alert_delta.md").write_text(
            build_markdown_summary(report),
            encoding="utf-8",
        )

    return report


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Delta analysis between two github_security_quality_readout JSON files."
        )
    )
    parser.add_argument(
        "--prev-readout",
        required=True,
        metavar="PATH",
        help="Path to the previous readout JSON file.",
    )
    parser.add_argument(
        "--current-readout",
        required=True,
        metavar="PATH",
        help="Path to the current readout JSON file.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        metavar="DIR",
        help="Optional directory for delta JSON and Markdown output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Exit codes:
        0 — success, no escalation needed.
        1 — input error (missing/malformed file).
        2 — success, but escalation_needed=true (for CI gate usage).
    """
    args = _build_arg_parser().parse_args(argv)

    try:
        report = generate_delta(
            prev_path=Path(args.prev_readout),
            current_path=Path(args.current_readout),
            out_dir=Path(args.out_dir) if args.out_dir else None,
        )
    except SecurityAlertDeltaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(build_markdown_summary(report))

    if report["escalation_needed"]:
        print("EXIT: escalation_needed=true", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
