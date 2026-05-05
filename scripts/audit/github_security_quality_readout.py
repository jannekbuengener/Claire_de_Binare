#!/usr/bin/env python3
"""
Read-only GitHub security and quality readout for the current repository.

This script fetches GitHub Security-and-quality alert surfaces via `gh api`,
normalizes them into a shared schema, and emits both machine-readable JSON and
an operator-facing Markdown summary.

Scope:
  - code scanning alerts
  - dependabot alerts
  - secret scanning alerts

Design rules:
  - read-only GitHub access only
  - fail-closed surface handling: unavailable APIs/permissions are explicit
  - deterministic JSON/Markdown output for the same fetched payloads and
    reference timestamp
  - no raw alert payloads are persisted in the output artifacts
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.utils.clock import utcnow

DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
DEFAULT_GH_EXECUTABLE = "gh"
JSON_FILENAME = "github_security_quality_readout.json"
MARKDOWN_FILENAME = "github_security_quality_summary.md"
SCHEMA_VERSION = "github_security_quality_readout.v1"
SOURCE_ORDER = ("code_scanning", "dependabot", "secret_scanning")
REDACTED_SECRET_SUBJECT = "redacted_secret_alert"
REDACTED_SECRET_RULE = "redacted_secret_type"
REDACTED_SECRET_PATH = "redacted_secret_location"
REDACTED_SECRET_COMPONENT = "secret_scanning_alert"
SEVERITY_ORDER = (
    "critical",
    "high",
    "medium",
    "low",
    "warning",
    "error",
    "note",
    "not_provided",
    "unknown",
)
STATE_ORDER = (
    "open",
    "dismissed",
    "fixed",
    "resolved",
    "auto_dismissed",
    "closed",
    "unknown",
)
SURFACE_ENDPOINTS = {
    "code_scanning": "repos/{repo}/code-scanning/alerts?per_page=100",
    "dependabot": "repos/{repo}/dependabot/alerts?per_page=100",
    "secret_scanning": "repos/{repo}/secret-scanning/alerts?per_page=100",
}


class SecurityQualityReadoutError(ValueError):
    """Raised when the readout configuration is invalid."""


@dataclass(frozen=True, slots=True)
class SurfaceFetchResult:
    source: str
    endpoint: str
    status: str
    alerts: tuple[dict[str, Any], ...]
    alert_count: int | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.alert_count is not None:
            alert_count: int | None = self.alert_count
        elif self.source == "secret_scanning":
            alert_count = None
        else:
            alert_count = len(self.alerts)
        result: dict[str, Any] = {
            "source": self.source,
            "endpoint": self.endpoint,
            "status": self.status,
            "alert_count": alert_count,
            "artifact_detail_status": (
                "redacted"
                if self.source == "secret_scanning"
                else "full" if self.status == "readable" else "none"
            ),
        }
        if self.note is not None:
            result["note"] = self.note
        return result


def _utc_now_iso() -> str:
    current = utcnow()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso8601(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_branch(value: str | None) -> str:
    if not value:
        return "not_provided"
    if value.startswith("refs/heads/"):
        return value[len("refs/heads/") :]
    return value


def _normalize_severity(value: str | None) -> str:
    if not value:
        return "not_provided"
    return value.strip().lower() or "not_provided"


def _age_bucket(
    *,
    created_at: str | None,
    updated_at: str | None,
    reference_now: datetime,
) -> str:
    basis = updated_at or created_at
    if basis is None:
        return "unknown"
    age_days = (reference_now - _parse_iso8601(basis)).days
    if age_days < 0:
        return "future"
    if age_days <= 7:
        return "0-7d"
    if age_days <= 30:
        return "8-30d"
    if age_days <= 90:
        return "31-90d"
    return "91d+"


def _completed_process_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def fetch_surface(
    *,
    source: str,
    repo: str,
    gh_executable: str = DEFAULT_GH_EXECUTABLE,
    runner: Callable[
        [list[str]], subprocess.CompletedProcess[str]
    ] = _completed_process_runner,
) -> SurfaceFetchResult:
    if source not in SURFACE_ENDPOINTS:
        raise SecurityQualityReadoutError(f"Unsupported source: {source}")

    if source == "secret_scanning":
        return SurfaceFetchResult(
            source="secret_scanning",
            endpoint=SURFACE_ENDPOINTS[source].format(repo=repo),
            status="redacted",
            alerts=(),
            alert_count=None,
            note=(
                "not-fetched: secret-scanning alert payloads are intentionally "
                "not requested or persisted"
            ),
        )

    endpoint = SURFACE_ENDPOINTS[source].format(repo=repo)
    command = [gh_executable, "api", "--paginate", "--slurp", endpoint]
    result = runner(command)
    if result.returncode != 0:
        note = (result.stderr or result.stdout).strip() or "gh api failed"
        return SurfaceFetchResult(
            source=source,
            endpoint=endpoint,
            status="unavailable",
            alerts=(),
            note=note,
        )

    if not isinstance(result.stdout, str):
        return SurfaceFetchResult(
            source=source,
            endpoint=endpoint,
            status="unavailable",
            alerts=(),
            note="gh api returned no stdout payload",
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return SurfaceFetchResult(
            source=source,
            endpoint=endpoint,
            status="unavailable",
            alerts=(),
            note=f"invalid json from gh api: {exc}",
        )

    if not isinstance(payload, list):
        return SurfaceFetchResult(
            source=source,
            endpoint=endpoint,
            status="unavailable",
            alerts=(),
            note="gh api payload root must be a JSON array of pages",
        )

    alerts: list[dict[str, Any]] = []
    for page_index, page in enumerate(payload):
        if not isinstance(page, list):
            return SurfaceFetchResult(
                source=source,
                endpoint=endpoint,
                status="unavailable",
                alerts=(),
                note=f"gh api page {page_index} is not a JSON array",
            )
        for item_index, item in enumerate(page):
            if not isinstance(item, dict):
                return SurfaceFetchResult(
                    source=source,
                    endpoint=endpoint,
                    status="unavailable",
                    alerts=(),
                    note=(
                        f"gh api page {page_index} item {item_index} "
                        f"is not a JSON object"
                    ),
                )
            alerts.append(item)

    return SurfaceFetchResult(
        source=source,
        endpoint=endpoint,
        status="readable",
        alerts=tuple(alerts),
        alert_count=len(alerts),
    )


def normalize_code_scanning_alert(
    raw: dict[str, Any], *, reference_now: datetime
) -> dict[str, Any]:
    rule = raw.get("rule", {}) if isinstance(raw.get("rule"), dict) else {}
    most_recent = (
        raw.get("most_recent_instance", {})
        if isinstance(raw.get("most_recent_instance"), dict)
        else {}
    )
    location = (
        most_recent.get("location", {})
        if isinstance(most_recent.get("location"), dict)
        else {}
    )
    path = location.get("path") if isinstance(location.get("path"), str) else None
    created_at = (
        raw.get("created_at") if isinstance(raw.get("created_at"), str) else None
    )
    updated_at = (
        raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else None
    )
    subject = (
        rule.get("id")
        if isinstance(rule.get("id"), str) and rule.get("id")
        else rule.get("name") if isinstance(rule.get("name"), str) else "unknown"
    )
    tool = raw.get("tool", {}) if isinstance(raw.get("tool"), dict) else {}
    return {
        "source": "code_scanning",
        "number": raw.get("number"),
        "state": raw.get("state", "unknown"),
        "severity": _normalize_severity(
            rule.get("security_severity_level") or rule.get("severity")
        ),
        "subject": subject,
        "rule_or_advisory": subject,
        "package": None,
        "affected_path": path,
        "affected_component": path,
        "branch": _normalize_branch(
            most_recent.get("ref") if isinstance(most_recent.get("ref"), str) else None
        ),
        "created_at": created_at,
        "updated_at": updated_at,
        "age_bucket": _age_bucket(
            created_at=created_at,
            updated_at=updated_at,
            reference_now=reference_now,
        ),
        "url": raw.get("html_url"),
        "tool": tool.get("name"),
    }


def normalize_dependabot_alert(
    raw: dict[str, Any], *, reference_now: datetime
) -> dict[str, Any]:
    dependency = (
        raw.get("dependency", {}) if isinstance(raw.get("dependency"), dict) else {}
    )
    package = (
        dependency.get("package", {})
        if isinstance(dependency.get("package"), dict)
        else {}
    )
    advisory = (
        raw.get("security_advisory", {})
        if isinstance(raw.get("security_advisory"), dict)
        else {}
    )
    package_name = package.get("name") if isinstance(package.get("name"), str) else None
    ghsa_id = (
        advisory.get("ghsa_id") if isinstance(advisory.get("ghsa_id"), str) else None
    )
    created_at = (
        raw.get("created_at") if isinstance(raw.get("created_at"), str) else None
    )
    updated_at = (
        raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else None
    )
    return {
        "source": "dependabot",
        "number": raw.get("number"),
        "state": raw.get("state", "unknown"),
        "severity": _normalize_severity(advisory.get("severity")),
        "subject": package_name or ghsa_id or "unknown",
        "rule_or_advisory": ghsa_id,
        "package": package_name,
        "affected_path": dependency.get("manifest_path"),
        "affected_component": package_name,
        "branch": "not_provided",
        "created_at": created_at,
        "updated_at": updated_at,
        "age_bucket": _age_bucket(
            created_at=created_at,
            updated_at=updated_at,
            reference_now=reference_now,
        ),
        "url": raw.get("html_url"),
        "tool": "Dependabot",
    }


def normalize_secret_scanning_alert(
    raw: dict[str, Any], *, reference_now: datetime
) -> dict[str, Any]:
    created_at = (
        raw.get("created_at") if isinstance(raw.get("created_at"), str) else None
    )
    updated_at = (
        raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else None
    )
    return {
        "source": "secret_scanning",
        "number": raw.get("number"),
        "state": raw.get("state", "unknown"),
        "severity": "not_provided",
        # GitHub secret-scanning payloads may carry security-sensitive detail.
        # Persist only redacted operator-safe placeholders in report artifacts.
        "subject": REDACTED_SECRET_SUBJECT,
        "rule_or_advisory": REDACTED_SECRET_RULE,
        "package": None,
        "affected_path": REDACTED_SECRET_PATH,
        "affected_component": REDACTED_SECRET_COMPONENT,
        "branch": "not_provided",
        "created_at": created_at,
        "updated_at": updated_at,
        "age_bucket": _age_bucket(
            created_at=created_at,
            updated_at=updated_at,
            reference_now=reference_now,
        ),
        "url": None,
        "tool": "Secret scanning",
    }


def normalize_alert(
    source: str, raw: dict[str, Any], *, reference_now: datetime
) -> dict[str, Any]:
    if source == "code_scanning":
        return normalize_code_scanning_alert(raw, reference_now=reference_now)
    if source == "dependabot":
        return normalize_dependabot_alert(raw, reference_now=reference_now)
    if source == "secret_scanning":
        return normalize_secret_scanning_alert(raw, reference_now=reference_now)
    raise SecurityQualityReadoutError(f"Unsupported source: {source}")


def _counter_items(
    counter: Counter[str], preferred_order: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    order_map = {value: index for index, value in enumerate(preferred_order)}
    return [
        {"value": key, "count": count}
        for key, count in sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                order_map.get(item[0], len(order_map)),
                item[0],
            ),
        )
    ]


def build_summary(
    alerts: list[dict[str, Any]],
    *,
    readable_surface_counts: Counter[str],
) -> dict[str, Any]:
    counts_by_source = Counter(readable_surface_counts)
    counts_by_state = Counter(alert["state"] for alert in alerts)
    counts_by_severity = Counter(alert["severity"] for alert in alerts)
    top_subjects = Counter(
        alert["subject"] for alert in alerts if isinstance(alert.get("subject"), str)
    )
    top_components = Counter(
        (
            alert.get("affected_path")
            if isinstance(alert.get("affected_path"), str)
            and alert.get("affected_path")
            else alert.get("affected_component")
        )
        for alert in alerts
        if (isinstance(alert.get("affected_path"), str) and alert.get("affected_path"))
        or (
            isinstance(alert.get("affected_component"), str)
            and alert.get("affected_component")
        )
    )
    return {
        "total_alerts": sum(counts_by_source.values()),
        "counts_by_source": _counter_items(counts_by_source, SOURCE_ORDER),
        "counts_by_state": _counter_items(counts_by_state, STATE_ORDER),
        "counts_by_severity": _counter_items(counts_by_severity, SEVERITY_ORDER),
        "top_subjects": _counter_items(top_subjects)[:10],
        "top_components": _counter_items(top_components)[:10],
    }


def build_markdown_report(readout: dict[str, Any]) -> str:
    lines = [
        "# GitHub Security and Quality Readout",
        "",
        f"- Repo: `{readout['repo']}`",
        f"- Reference now (UTC): `{readout['reference_now_utc']}`",
        f"- Overall status: **{readout['status']}**",
        f"- Readable surfaces: `{readout['readable_surface_count']}/{len(readout['surfaces'])}`",
        f"- Total normalized alerts: `{readout['summary']['total_alerts']}`",
        "",
        "## Surface Coverage",
        "",
        "| Source | Status | Alerts | Note |",
        "|--------|--------|--------|------|",
    ]

    for surface in readout["surfaces"]:
        note = surface.get("note") or "—"
        lines.append(
            f"| `{surface['source']}` | {surface['status']} | "
            f"{'redacted' if surface['alert_count'] is None else surface['alert_count']} | {note} |"
        )

    def add_counter_section(title: str, rows: list[dict[str, Any]]) -> None:
        lines.extend(["", f"## {title}", "", "| Value | Count |", "|-------|-------|"])
        if rows:
            for row in rows:
                lines.append(f"| `{row['value']}` | {row['count']} |")
        else:
            lines.append("| `none` | 0 |")

    summary = readout["summary"]
    add_counter_section("Counts by Source", summary["counts_by_source"])
    add_counter_section("Counts by Severity", summary["counts_by_severity"])
    add_counter_section("Counts by State", summary["counts_by_state"])
    add_counter_section("Top Subjects", summary["top_subjects"])
    add_counter_section("Top Components or Paths", summary["top_components"])

    unavailable = [
        surface
        for surface in readout["surfaces"]
        if surface["status"] not in ("readable", "redacted")
    ]
    redacted = [
        surface
        for surface in readout["surfaces"]
        if surface.get("artifact_detail_status") == "redacted"
    ]
    lines.extend(["", "## Coverage Notes", ""])
    if unavailable:
        lines.append(
            "Dieses Bild ist partiell. Mindestens eine GitHub-Surface war nicht lesbar:"
        )
        lines.append("")
        for surface in unavailable:
            lines.append(
                f"- `{surface['source']}`: {surface.get('note') or 'unavailable'}"
            )
    else:
        lines.append("Alle angefragten GitHub-Surfaces waren lesbar.")
    if redacted:
        lines.append("")
        lines.append(
            "Secret-Scanning bleibt in der Surface-Coverage sichtbar; "
            "payload-abgeleitete Counts und Breakdowns werden dafuer bewusst nicht persistiert."
        )

    lines.extend(
        [
            "",
            "## Scope Note",
            "",
            "- Read-only GitHub-Readout; kein Auto-Fix, kein Dismiss, kein Close.",
            "- Secret-Scanning-Detailfelder werden im Artefakt absichtlich redigiert, damit keine GitHub-seitigen Secret-Kontexte als Klartext persistiert werden.",
            "- `severity=not_provided` bedeutet: GitHub liefert fuer diese Surface keine native Severity.",
            "- `branch=not_provided` bedeutet: GitHub liefert fuer diese Alert-Surface keinen Branch-Kontext.",
            "",
        ]
    )
    return "\n".join(lines)


def build_readout(
    *,
    repo: str,
    reference_now_utc: str,
    fetched_surfaces: list[SurfaceFetchResult],
) -> dict[str, Any]:
    reference_now = _parse_iso8601(reference_now_utc)
    alerts: list[dict[str, Any]] = []
    surfaces_payload = [surface.to_dict() for surface in fetched_surfaces]
    readable_surfaces = 0
    readable_surface_counts: Counter[str] = Counter()
    for surface in fetched_surfaces:
        if surface.status in ("readable", "redacted"):
            readable_surfaces += 1
            if surface.source == "secret_scanning":
                continue
            surface_alert_count = (
                surface.alert_count
                if surface.alert_count is not None
                else len(surface.alerts)
            )
            if surface_alert_count:
                readable_surface_counts[surface.source] += surface_alert_count
            for raw in surface.alerts:
                alerts.append(
                    normalize_alert(
                        surface.source,
                        raw,
                        reference_now=reference_now,
                    )
                )

    alerts.sort(
        key=lambda alert: (
            alert["source"],
            str(alert["state"]),
            str(alert["severity"]),
            str(alert["subject"]),
            str(alert.get("affected_component")),
            str(alert.get("affected_path")),
            str(alert["branch"]),
            str(alert.get("created_at")),
            str(alert.get("number")),
        )
    )

    if readable_surfaces == len(fetched_surfaces):
        status = "PASS"
    elif readable_surfaces == 0:
        status = "FAIL"
    else:
        status = "PARTIAL"

    return {
        "schema_version": SCHEMA_VERSION,
        "repo": repo,
        "reference_now_utc": reference_now_utc,
        "status": status,
        "readable_surface_count": readable_surfaces,
        "surfaces": surfaces_payload,
        "summary": build_summary(
            alerts,
            readable_surface_counts=readable_surface_counts,
        ),
        "alerts": alerts,
    }


def _copy_count_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied_rows: list[dict[str, Any]] = []
    for row in rows:
        copied_rows.append(
            {
                "value": str(row["value"]),
                "count": int(row["count"]),
            }
        )
    return copied_rows


def build_exportable_readout(readout: dict[str, Any]) -> dict[str, Any]:
    export_surfaces: list[dict[str, Any]] = []
    for surface in readout["surfaces"]:
        export_surface = {
            "source": str(surface["source"]),
            "endpoint": str(surface["endpoint"]),
            "status": str(surface["status"]),
            "alert_count": (
                int(surface["alert_count"])
                if surface["alert_count"] is not None
                else None
            ),
            "artifact_detail_status": str(surface["artifact_detail_status"]),
        }
        if isinstance(surface.get("note"), str):
            export_surface["note"] = surface["note"]
        export_surfaces.append(export_surface)

    export_alerts: list[dict[str, Any]] = []
    for alert in readout["alerts"]:
        export_alerts.append(
            {
                "source": str(alert["source"]),
                "number": alert.get("number"),
                "state": str(alert["state"]),
                "severity": str(alert["severity"]),
                "subject": str(alert["subject"]),
                "rule_or_advisory": (
                    str(alert["rule_or_advisory"])
                    if isinstance(alert.get("rule_or_advisory"), str)
                    else None
                ),
                "package": (
                    str(alert["package"])
                    if isinstance(alert.get("package"), str)
                    else None
                ),
                "affected_path": (
                    str(alert["affected_path"])
                    if isinstance(alert.get("affected_path"), str)
                    else None
                ),
                "affected_component": (
                    str(alert["affected_component"])
                    if isinstance(alert.get("affected_component"), str)
                    else None
                ),
                "branch": str(alert["branch"]),
                "created_at": (
                    str(alert["created_at"])
                    if isinstance(alert.get("created_at"), str)
                    else None
                ),
                "updated_at": (
                    str(alert["updated_at"])
                    if isinstance(alert.get("updated_at"), str)
                    else None
                ),
                "age_bucket": str(alert["age_bucket"]),
                "url": str(alert["url"]) if isinstance(alert.get("url"), str) else None,
                "tool": (
                    str(alert["tool"]) if isinstance(alert.get("tool"), str) else None
                ),
            }
        )

    summary = readout["summary"]
    export_summary = {
        "total_alerts": int(summary["total_alerts"]),
        "counts_by_source": _copy_count_rows(summary["counts_by_source"]),
        "counts_by_state": _copy_count_rows(summary["counts_by_state"]),
        "counts_by_severity": _copy_count_rows(summary["counts_by_severity"]),
        "top_subjects": _copy_count_rows(summary["top_subjects"]),
        "top_components": _copy_count_rows(summary["top_components"]),
    }

    return {
        "schema_version": str(readout["schema_version"]),
        "repo": str(readout["repo"]),
        "reference_now_utc": str(readout["reference_now_utc"]),
        "status": str(readout["status"]),
        "readable_surface_count": int(readout["readable_surface_count"]),
        "surfaces": export_surfaces,
        "summary": export_summary,
        "alerts": export_alerts,
    }


def build_persistable_readout(readout: dict[str, Any]) -> dict[str, Any]:
    """
    Build a readout structure safe for persistence (JSON/Markdown export).

    Excludes secret_scanning alerts entirely and replaces their summary
    entries with coverage-only markers to avoid taint tracking of secret
    payloads through to file I/O sinks.

    Only code_scanning and dependabot alerts are included in the
    persisted output.
    """
    persistable_surfaces: list[dict[str, Any]] = []
    for surface in readout["surfaces"]:
        if surface["source"] == "secret_scanning":
            persistable_surfaces.append(
                {
                    "source": "secret_scanning",
                    "endpoint": str(surface["endpoint"]),
                    "status": str(surface["status"]),
                    "alert_count": None,
                    "artifact_detail_status": "redacted",
                    "note": "payload-redacted: secret scanning details excluded from artifacts",
                }
            )
        else:
            persistable_surfaces.append(
                {
                    "source": str(surface["source"]),
                    "endpoint": str(surface["endpoint"]),
                    "status": str(surface["status"]),
                    "alert_count": (
                        int(surface["alert_count"])
                        if surface["alert_count"] is not None
                        else None
                    ),
                    "artifact_detail_status": str(surface["artifact_detail_status"]),
                }
            )
            if isinstance(surface.get("note"), str):
                persistable_surfaces[-1]["note"] = surface["note"]

    persistable_alerts: list[dict[str, Any]] = []
    for alert in readout["alerts"]:
        if alert["source"] != "secret_scanning":
            persistable_alerts.append(
                {
                    "source": str(alert["source"]),
                    "number": alert.get("number"),
                    "state": str(alert["state"]),
                    "severity": str(alert["severity"]),
                    "subject": str(alert["subject"]),
                    "rule_or_advisory": (
                        str(alert["rule_or_advisory"])
                        if isinstance(alert.get("rule_or_advisory"), str)
                        else None
                    ),
                    "package": (
                        str(alert["package"])
                        if isinstance(alert.get("package"), str)
                        else None
                    ),
                    "affected_path": (
                        str(alert["affected_path"])
                        if isinstance(alert.get("affected_path"), str)
                        else None
                    ),
                    "affected_component": (
                        str(alert["affected_component"])
                        if isinstance(alert.get("affected_component"), str)
                        else None
                    ),
                    "branch": str(alert["branch"]),
                    "created_at": (
                        str(alert["created_at"])
                        if isinstance(alert.get("created_at"), str)
                        else None
                    ),
                    "updated_at": (
                        str(alert["updated_at"])
                        if isinstance(alert.get("updated_at"), str)
                        else None
                    ),
                    "age_bucket": str(alert["age_bucket"]),
                    "url": (
                        str(alert["url"]) if isinstance(alert.get("url"), str) else None
                    ),
                    "tool": (
                        str(alert["tool"])
                        if isinstance(alert.get("tool"), str)
                        else None
                    ),
                }
            )

    summary = readout["summary"]
    persistable_summary = {
        "total_alerts": int(summary["total_alerts"]),
        "counts_by_source": _copy_count_rows(summary["counts_by_source"]),
        "counts_by_state": _copy_count_rows(summary["counts_by_state"]),
        "counts_by_severity": _copy_count_rows(summary["counts_by_severity"]),
        "top_subjects": _copy_count_rows(summary["top_subjects"]),
        "top_components": _copy_count_rows(summary["top_components"]),
    }

    return {
        "schema_version": str(readout["schema_version"]),
        "repo": str(readout["repo"]),
        "reference_now_utc": str(readout["reference_now_utc"]),
        "status": str(readout["status"]),
        "readable_surface_count": int(readout["readable_surface_count"]),
        "surfaces": persistable_surfaces,
        "summary": persistable_summary,
        "alerts": persistable_alerts,
    }


def write_report_artifacts(persistable_readout: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / JSON_FILENAME
    markdown_path = out_dir / MARKDOWN_FILENAME
    json_path.write_text(
        json.dumps(persistable_readout, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        build_markdown_report(persistable_readout),
        encoding="utf-8",
    )


def generate_readout(
    *,
    repo: str,
    out_dir: Path,
    reference_now_utc: str | None = None,
    gh_executable: str = DEFAULT_GH_EXECUTABLE,
    runner: Callable[
        [list[str]], subprocess.CompletedProcess[str]
    ] = _completed_process_runner,
) -> dict[str, Any]:
    if reference_now_utc is None:
        reference_now_utc = _utc_now_iso()
    _parse_iso8601(reference_now_utc)

    surfaces = [
        fetch_surface(
            source=source,
            repo=repo,
            gh_executable=gh_executable,
            runner=runner,
        )
        for source in SOURCE_ORDER
    ]
    readout = build_readout(
        repo=repo,
        reference_now_utc=reference_now_utc,
        fetched_surfaces=surfaces,
    )
    persistable_readout = build_persistable_readout(readout)
    write_report_artifacts(persistable_readout, out_dir)
    return readout


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only GitHub Security and quality readout for code scanning, "
            "Dependabot, and secret scanning."
        )
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help="owner/repo, default CDB repo",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory for JSON and Markdown output artifacts",
    )
    parser.add_argument(
        "--reference-now",
        default=None,
        help="Optional UTC reference timestamp (ISO-8601) for deterministic age buckets",
    )
    parser.add_argument(
        "--gh-executable",
        default=DEFAULT_GH_EXECUTABLE,
        help="gh executable path/name",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    repo = args.repo
    readout = generate_readout(
        repo=repo,
        out_dir=Path(args.out_dir),
        reference_now_utc=args.reference_now,
        gh_executable=args.gh_executable,
    )

    if readout["status"] == "PASS":
        print(
            f"PASS: wrote {JSON_FILENAME} and {MARKDOWN_FILENAME} for {repo}.",
            file=sys.stderr,
        )
        return 0
    if readout["status"] == "PARTIAL":
        print(
            "PARTIAL: one or more GitHub Security surfaces were unavailable; "
            "artifacts were still written fail-closed.",
            file=sys.stderr,
        )
        return 2

    print(
        "FAIL: no GitHub Security surfaces were readable; artifacts were written "
        "with explicit unavailable status.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
