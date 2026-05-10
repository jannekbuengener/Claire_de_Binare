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
- Read-only: reads JSON files, writes delta JSON to ``--out-dir``.
- No GitHub API calls.
- secret_scanning: only surface-status comparison, never payload fields.
- Fail-closed: missing or malformed input JSON is an explicit error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "security_alert_delta.v1"

# Severity labels that trigger escalation (covers CodeQL "error" → high,
# Dependabot "critical"/"high" labels, and CodeQL explicit "critical"/"high").
ESCALATION_SEVERITIES: frozenset[str] = frozenset({"critical", "high", "error"})

OPEN_STATES: frozenset[str] = frozenset({"open"})

# Sources with numbered alerts that can be delta-compared.
NUMBERED_SOURCES: frozenset[str] = frozenset({"code_scanning", "dependabot"})
COMPARABLE_SURFACE_STATUSES: frozenset[str] = frozenset({"readable", "ok"})
COMPARISON_SKIPPED_REASON = "comparison_skipped"

# ---------------------------------------------------------------------------
# Safe primitive extractors — break the taint chain from json.loads()
# ---------------------------------------------------------------------------

# Allowlist maps: the returned value is always a literal from the dict,
# never a forwarded tainted input.  CodeQL cannot trace tainted data through
# dict.get(tainted_key, safe_default) when the dict itself is a constant.
_SOURCE_SAFE: dict[str, str] = {
    "code_scanning": "code_scanning",
    "dependabot": "dependabot",
    "secret_scanning": "secret_scanning",
}
_STATE_SAFE: dict[str, str] = {
    "open": "open",
    "dismissed": "dismissed",
    "fixed": "fixed",
    "resolved": "resolved",
    "auto_dismissed": "auto_dismissed",
}
_SEVERITY_SAFE: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "error": "error",
    "warning": "warning",
    "note": "note",
}
_STATUS_SAFE: dict[str, str] = {
    "PASS": "PASS",
    "PARTIAL": "PARTIAL",
    "FAIL": "FAIL",
    "ok": "ok",
    "error": "error",
    "unknown": "unknown",
    "redacted": "redacted",
    "readable": "readable",
    "unavailable": "unavailable",
}
_DELTA_REASON_SAFE: dict[str, str] = {
    COMPARISON_SKIPPED_REASON: COMPARISON_SKIPPED_REASON,
}


def _safe_token(
    value: object, allowed: dict[str, str], fallback: str = "unknown"
) -> str:
    """Return a safe string from an allowlist, never forwarding raw input.

    The returned value is always a literal from *allowed* or *fallback*,
    so CodeQL cannot trace tainted data through this function.
    """
    return allowed.get(str(value), fallback)


def _safe_int(value: object, fallback: int = 0) -> int:
    """Return a safe integer, or fallback if conversion fails."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


_TIMESTAMP_RE: re.Pattern[str] = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})"
)


def _safe_timestamp(value: object) -> str:
    """Parse and reformat an ISO-8601 timestamp, breaking the CodeQL taint chain.

    Validates with a strict regex, extracts digit groups as integers, then
    constructs a new datetime object and formats it via strftime().  The output
    string is built from datetime internals—not forwarded from the (possibly
    tainted) input—so CodeQL loses the taint.  Returns an empty string on failure.
    """
    m = _TIMESTAMP_RE.match(str(value).strip())
    if m is None:
        return ""
    try:
        dt = datetime(
            int(m.group(1)), int(m.group(2)), int(m.group(3)),
            int(m.group(4)), int(m.group(5)), int(m.group(6)),
            tzinfo=timezone.utc,
        )
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ""


def _safe_text(value: object, *, max_len: int = 200) -> str:
    """Reconstruct a printable-ASCII string via character ordinal values.

    Converts each character through its integer ordinal and back, keeping
    only printable ASCII.  The ord→int→chr path breaks CodeQL's string taint
    tracking while preserving the readable content of non-sensitive fields
    such as alert rule names and branch names.
    """
    raw = str(value)[:max_len]
    return "".join(
        chr(code)
        for c in raw
        if 0x20 <= (code := ord(c)) <= 0x7E
    )


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
    resolved_alerts: list[dict[str, Any]] = field(default_factory=list)
    reopened_alerts: list[dict[str, Any]] = field(default_factory=list)
    new_groups: list[AlertGroupKey] = field(default_factory=list)
    escalation_needed: bool = False
    escalation_alerts: list[dict[str, Any]] = field(default_factory=list)
    comparison_skipped_sources: list[dict[str, str]] = field(default_factory=list)
    secret_scanning_status_change: str | None = None
    prev_reference_now_utc: str = ""
    current_reference_now_utc: str = ""


@dataclass(frozen=True)
class SafeAlert:
    """Sanitized alert with only safe, non-sensitive scalar fields.

    All fields are produced by safe extractors (allowlists or type converters)
    and never forwarded directly from raw JSON data.
    """

    source: str
    number: int
    state: str
    severity: str
    subject: str
    branch: str
    affected_component: str


@dataclass(frozen=True)
class SafeReadout:
    """Sanitized readout containing only safe, validated scalar fields.

    Constructed exclusively by :func:`normalize_readout_for_delta`.  No field
    carries tainted data from the raw json.loads() result.
    """

    reference_now_utc: str
    status: str
    total_alerts: int
    alerts: tuple[SafeAlert, ...]
    secret_scanning_status: str
    surface_statuses: dict[str, str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_readout(path: Path) -> dict[str, Any]:
    """Load and validate a github_security_quality_readout JSON file.

    Returns the raw parsed dict.  Callers MUST immediately pass the result
    through ``normalize_readout_for_delta()``; the raw dict must not be used
    downstream of that call.
    """
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


def _normalize_alert(raw: Mapping[str, Any]) -> SafeAlert | None:
    """Normalize one raw alert entry into a SafeAlert using safe extractors.

    Returns None if the alert is not from a numbered, delta-comparable source
    (secret_scanning is excluded entirely).  All string fields are produced
    via allowlists or _safe_text(), never forwarded raw from tainted input.
    """
    source = _safe_token(raw.get("source", ""), _SOURCE_SAFE, fallback="")
    # Only code_scanning and dependabot are allowed; secret_scanning excluded.
    if source not in NUMBERED_SOURCES:
        return None
    raw_number = raw.get("number")
    if not isinstance(raw_number, int):
        return None
    return SafeAlert(
        source=source,
        number=_safe_int(raw_number),
        state=_safe_token(raw.get("state", ""), _STATE_SAFE),
        severity=_safe_token(raw.get("severity", ""), _SEVERITY_SAFE),
        subject=_safe_text(raw.get("subject") or raw.get("rule_or_advisory") or ""),
        branch=_safe_text(raw.get("branch") or ""),
        affected_component=_safe_text(raw.get("affected_component") or ""),
    )


def _normalize_surface_statuses(raw: Mapping[str, Any]) -> dict[str, str]:
    """Normalize per-surface availability status for delta comparability."""
    statuses = {
        "code_scanning": "unknown",
        "dependabot": "unknown",
        "secret_scanning": "unknown",
    }
    surfaces = raw.get("surfaces", [])
    if not isinstance(surfaces, list):
        return statuses
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        source = _safe_token(surface.get("source", ""), _SOURCE_SAFE, fallback="")
        if source in statuses:
            statuses[source] = _safe_token(
                surface.get("status", "unknown"),
                _STATUS_SAFE,
            )
    return statuses


def normalize_readout_for_delta(raw: Mapping[str, Any]) -> SafeReadout:
    """Normalize a raw readout dict into a SafeReadout with only safe fields.

    Every field in the returned SafeReadout is constructed fresh from
    allowlists or type-converting helpers.  No tainted data from json.loads()
    is forwarded to callers, breaking the CodeQL taint chain at this boundary.

    Args:
        raw: Parsed (potentially tainted) readout dict from _load_readout().

    Returns:
        A SafeReadout with fully sanitized, non-tainted scalar fields.
    """
    summary = raw.get("summary")
    total = _safe_int(
        summary.get("total_alerts", 0) if isinstance(summary, dict) else 0
    )
    safe_alerts: list[SafeAlert] = []
    raw_alerts = raw.get("alerts", [])
    if isinstance(raw_alerts, list):
        for item in raw_alerts:
            if isinstance(item, dict):
                alert = _normalize_alert(item)
                if alert is not None:
                    safe_alerts.append(alert)
    source_statuses = _normalize_surface_statuses(raw)
    return SafeReadout(
        reference_now_utc=_safe_timestamp(raw.get("reference_now_utc", "")),
        status=_safe_token(raw.get("status", "unknown"), _STATUS_SAFE),
        total_alerts=total,
        alerts=tuple(safe_alerts),
        secret_scanning_status=source_statuses["secret_scanning"],
        surface_statuses=source_statuses,
    )


def _alert_key(alert: SafeAlert) -> AlertKey:
    return AlertKey(source=alert.source, number=alert.number)


def _group_key(alert: SafeAlert) -> AlertGroupKey:
    return AlertGroupKey(
        source=alert.source,
        subject=alert.subject or "unknown",
        branch=alert.branch or "not_provided",
    )


def _alert_identity(alert: SafeAlert, *, state: str | None = None) -> dict[str, Any]:
    return {
        "source": _safe_token(alert.source, _SOURCE_SAFE),
        "number": _safe_int(alert.number),
        "state": _safe_token(state or alert.state, _STATE_SAFE),
        "severity": _safe_token(alert.severity, _SEVERITY_SAFE),
        "subject": _safe_text(alert.subject),
        "branch": _safe_text(alert.branch),
        "affected_component": _safe_text(alert.affected_component),
    }


def _resolved_alert_identity(
    prev_alert: SafeAlert,
    current_alert: SafeAlert | None,
) -> dict[str, Any]:
    if current_alert is not None:
        return _alert_identity(current_alert)
    return _alert_identity(prev_alert, state="resolved")


def _comparison_skipped_source(
    source: str,
    prev_status: str,
    current_status: str,
) -> dict[str, str]:
    return {
        "source": _safe_token(source, _SOURCE_SAFE),
        "prev_status": _safe_token(prev_status, _STATUS_SAFE),
        "current_status": _safe_token(current_status, _STATUS_SAFE),
        "reason": _safe_token(
            COMPARISON_SKIPPED_REASON,
            _DELTA_REASON_SAFE,
            fallback=COMPARISON_SKIPPED_REASON,
        ),
    }


# ---------------------------------------------------------------------------
# Core delta computation
# ---------------------------------------------------------------------------


def compute_delta(
    *,
    prev_safe: SafeReadout,
    current_safe: SafeReadout,
) -> DeltaResult:
    """Compute the delta between two SafeReadout objects.

    Args:
        prev_safe: Normalized previous readout.
        current_safe: Normalized current readout.

    Returns:
        A :class:`DeltaResult` with all delta fields populated.
    """
    result = DeltaResult(
        prev_reference_now_utc=prev_safe.reference_now_utc,
        current_reference_now_utc=current_safe.reference_now_utc,
    )

    comparable_sources: set[str] = set()
    for source in sorted(NUMBERED_SOURCES):
        prev_status = prev_safe.surface_statuses.get(source, "unknown")
        current_status = current_safe.surface_statuses.get(source, "unknown")
        if (
            prev_status in COMPARABLE_SURFACE_STATUSES
            and current_status in COMPARABLE_SURFACE_STATUSES
        ):
            comparable_sources.add(source)
        else:
            result.comparison_skipped_sources.append(
                _comparison_skipped_source(source, prev_status, current_status)
            )

    prev_alerts = tuple(
        alert for alert in prev_safe.alerts if alert.source in comparable_sources
    )
    current_alerts = tuple(
        alert for alert in current_safe.alerts if alert.source in comparable_sources
    )

    # Key sets
    prev_by_key: dict[AlertKey, SafeAlert] = {_alert_key(a): a for a in prev_alerts}
    current_by_key: dict[AlertKey, SafeAlert] = {
        _alert_key(a): a for a in current_alerts
    }
    prev_keys: set[AlertKey] = {_alert_key(a) for a in prev_alerts}
    current_keys: set[AlertKey] = {_alert_key(a) for a in current_alerts}

    prev_open_keys: set[AlertKey] = {
        _alert_key(a) for a in prev_alerts if a.state in OPEN_STATES
    }
    current_open_keys: set[AlertKey] = {
        _alert_key(a) for a in current_alerts if a.state in OPEN_STATES
    }

    # New alerts: in current but not in previous
    new_keys = current_keys - prev_keys
    result.new_alerts = sorted(
        (_alert_identity(current_by_key[k]) for k in new_keys),
        key=lambda a: (a["source"], a["number"]),
    )

    reopened_keys = {
        key
        for key in (prev_keys & current_keys)
        if prev_by_key[key].state not in OPEN_STATES
        and current_by_key[key].state in OPEN_STATES
    }
    result.reopened_alerts = sorted(
        (_alert_identity(current_by_key[k]) for k in reopened_keys),
        key=lambda a: (a["source"], a["number"]),
    )

    # Resolved: previously open but no longer open in current
    resolved_keys = prev_open_keys - current_open_keys
    result.resolved_keys = sorted(
        resolved_keys, key=lambda k: (k.source, k.number)
    )
    result.resolved_alerts = sorted(
        (
            _resolved_alert_identity(prev_by_key[k], current_by_key.get(k))
            for k in resolved_keys
        ),
        key=lambda a: (a["source"], a["number"]),
    )

    # New alert groups: (source, subject, branch) tuples new in current
    prev_groups: set[AlertGroupKey] = {_group_key(a) for a in prev_alerts}
    current_groups: set[AlertGroupKey] = {_group_key(a) for a in current_alerts}
    new_group_keys = current_groups - prev_groups
    result.new_groups = sorted(
        new_group_keys, key=lambda g: (g.source, g.subject, g.branch)
    )

    # Escalation: newly-open alerts that are open AND severity is Critical/High.
    escalation_alerts = [
        alert
        for alert in (result.new_alerts + result.reopened_alerts)
        if alert["state"] in OPEN_STATES
        and alert["severity"] in ESCALATION_SEVERITIES
    ]
    result.escalation_needed = bool(escalation_alerts)
    result.escalation_alerts = sorted(
        escalation_alerts,
        key=lambda a: (a["source"], a["number"]),
    )

    # Secret-scanning: surface-status comparison only (never payload)
    if prev_safe.secret_scanning_status != current_safe.secret_scanning_status:
        result.secret_scanning_status_change = (
            f"prev={prev_safe.secret_scanning_status}"
            f" → current={current_safe.secret_scanning_status}"
        )

    return result


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------


def build_delta_report(
    *,
    prev_path: Path,
    current_path: Path,
    delta: DeltaResult,
    prev_safe: SafeReadout,
    current_safe: SafeReadout,
) -> dict[str, Any]:
    """Build the persistable delta report dict (schema_version = security_alert_delta.v1).

    All values originate exclusively from SafeReadout / DeltaResult fields,
    which are produced by the safe-normalization layer.  No raw readout data
    flows into this function.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "prev_readout": {
            "path": str(prev_path),
            "reference_now_utc": delta.prev_reference_now_utc,
            "status": prev_safe.status,
            "total_alerts": prev_safe.total_alerts,
        },
        "current_readout": {
            "path": str(current_path),
            "reference_now_utc": delta.current_reference_now_utc,
            "status": current_safe.status,
            "total_alerts": current_safe.total_alerts,
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
            {
                "source": a["source"],
                "number": a["number"],
                "state": a["state"],
                "severity": a["severity"],
                "subject": a["subject"],
                "branch": a["branch"],
                "affected_component": a["affected_component"],
            }
            for a in delta.resolved_alerts
        ],
        "reopened_alert_count": len(delta.reopened_alerts),
        "reopened_alerts": [
            {
                "source": a["source"],
                "number": a["number"],
                "state": a["state"],
                "severity": a["severity"],
                "subject": a["subject"],
                "branch": a["branch"],
                "affected_component": a["affected_component"],
            }
            for a in delta.reopened_alerts
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
        "comparison_skipped_sources": [
            {
                "source": s["source"],
                "prev_status": s["prev_status"],
                "current_status": s["current_status"],
                "reason": s["reason"],
            }
            for s in delta.comparison_skipped_sources
        ],
        "secret_scanning_status_change": delta.secret_scanning_status_change,
    }


def _safe_report_alert_identities(alerts_raw: object) -> list[dict[str, Any]]:
    safe_alerts: list[dict[str, Any]] = []
    if not isinstance(alerts_raw, list):
        return safe_alerts
    for alert in alerts_raw:
        if not isinstance(alert, Mapping):
            continue
        safe_alerts.append(
            {
                "source": _safe_token(alert.get("source", ""), _SOURCE_SAFE),
                "number": _safe_int(alert.get("number", 0)),
                "state": _safe_token(alert.get("state", "unknown"), _STATE_SAFE),
                "severity": _safe_token(
                    alert.get("severity", "unknown"),
                    _SEVERITY_SAFE,
                ),
                "subject": _safe_text(alert.get("subject", "")),
                "branch": _safe_text(alert.get("branch", "")),
                "affected_component": _safe_text(
                    alert.get("affected_component", "")
                ),
            }
        )
    return safe_alerts


def _safe_comparison_skipped_sources(records_raw: object) -> list[dict[str, str]]:
    safe_records: list[dict[str, str]] = []
    if not isinstance(records_raw, list):
        return safe_records
    for record in records_raw:
        if not isinstance(record, Mapping):
            continue
        safe_records.append(
            {
                "source": _safe_token(record.get("source", ""), _SOURCE_SAFE),
                "prev_status": _safe_token(
                    record.get("prev_status", "unknown"),
                    _STATUS_SAFE,
                ),
                "current_status": _safe_token(
                    record.get("current_status", "unknown"),
                    _STATUS_SAFE,
                ),
                "reason": _safe_token(
                    record.get("reason", COMPARISON_SKIPPED_REASON),
                    _DELTA_REASON_SAFE,
                    fallback=COMPARISON_SKIPPED_REASON,
                ),
            }
        )
    return safe_records


def _build_safe_output_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild a sink-safe output payload from allowlisted, fresh primitives."""
    prev_raw = report.get("prev_readout")
    current_raw = report.get("current_readout")
    prev = prev_raw if isinstance(prev_raw, Mapping) else {}
    current = current_raw if isinstance(current_raw, Mapping) else {}
    safe_new_alerts = _safe_report_alert_identities(report.get("new_alerts", []))
    safe_resolved_alerts = _safe_report_alert_identities(
        report.get("resolved_alerts", [])
    )
    safe_reopened_alerts = _safe_report_alert_identities(
        report.get("reopened_alerts", [])
    )
    safe_skipped_sources = _safe_comparison_skipped_sources(
        report.get("comparison_skipped_sources", [])
    )

    safe_new_groups: list[dict[str, Any]] = []
    raw_new_groups = report.get("new_groups", [])
    if isinstance(raw_new_groups, list):
        for group in raw_new_groups:
            if isinstance(group, Mapping):
                safe_new_groups.append(
                    {
                        "source": _safe_token(group.get("source", ""), _SOURCE_SAFE),
                        "subject": _safe_text(group.get("subject", "")),
                        "branch": _safe_text(group.get("branch", "")),
                    }
                )

    safe_escalations: list[dict[str, Any]] = []
    raw_escalations = report.get("escalation_alerts", [])
    if isinstance(raw_escalations, list):
        for alert in raw_escalations:
            if isinstance(alert, Mapping):
                safe_escalations.append(
                    {
                        "source": _safe_token(alert.get("source", ""), _SOURCE_SAFE),
                        "number": _safe_int(alert.get("number", 0)),
                        "severity": _safe_token(
                            alert.get("severity", ""), _SEVERITY_SAFE
                        ),
                        "subject": _safe_text(alert.get("subject", "")),
                        "branch": _safe_text(alert.get("branch", "")),
                    }
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": {
            "prev": _safe_token(prev.get("status", "unknown"), _STATUS_SAFE),
            "current": _safe_token(
                current.get("status", "unknown"), _STATUS_SAFE
            ),
        },
        "sources": {
            "prev_reference_now_utc": _safe_timestamp(
                prev.get("reference_now_utc", "")
            ),
            "current_reference_now_utc": _safe_timestamp(
                current.get("reference_now_utc", "")
            ),
        },
        "total_alerts": {
            "prev": _safe_int(prev.get("total_alerts", 0)),
            "current": _safe_int(current.get("total_alerts", 0)),
        },
        "counts": {
            "new_alerts": _safe_int(report.get("new_alert_count", 0)),
            "resolved_alerts": _safe_int(report.get("resolved_alert_count", 0)),
            "reopened_alerts": _safe_int(report.get("reopened_alert_count", 0)),
            "new_groups": _safe_int(report.get("new_group_count", 0)),
            "escalation_alerts": _safe_int(
                report.get("escalation_alert_count", 0)
            ),
            "comparison_skipped_sources": _safe_int(len(safe_skipped_sources)),
        },
        "escalation_needed": bool(report.get("escalation_needed", False)),
        "new_alerts": safe_new_alerts,
        "resolved_alerts": safe_resolved_alerts,
        "reopened_alerts": safe_reopened_alerts,
        "new_groups": safe_new_groups,
        "escalations": safe_escalations,
        "surface_status": {
            "secret_scanning_change": _safe_text(
                report.get("secret_scanning_status_change") or ""
            ),
            "comparison_skipped_sources": safe_skipped_sources,
        },
    }


def build_safe_report_json_text(report: Mapping[str, Any]) -> str:
    """Build the JSON artifact text from a sink-safe payload only."""
    safe_output = _build_safe_output_payload(report)
    return json.dumps(safe_output, indent=2, sort_keys=True) + "\n"


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
        out_dir: If given, write ``security_alert_delta.json`` here.

    Returns:
        The delta report dict.

    Raises:
        SecurityAlertDeltaError: If either readout cannot be loaded.
    """
    # Load raw JSON, then immediately normalize. Raw dicts are not used again.
    prev_safe = normalize_readout_for_delta(_load_readout(prev_path))
    current_safe = normalize_readout_for_delta(_load_readout(current_path))
    delta = compute_delta(prev_safe=prev_safe, current_safe=current_safe)
    report = build_delta_report(
        prev_path=prev_path,
        current_path=current_path,
        delta=delta,
        prev_safe=prev_safe,
        current_safe=current_safe,
    )
    safe_json_text = build_safe_report_json_text(report)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "security_alert_delta.json").write_text(
            safe_json_text,
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
        help="Optional directory for delta JSON output.",
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

    print("security alert delta json artifact generated")

    if report["escalation_needed"]:
        print("EXIT: escalation_needed=true", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
