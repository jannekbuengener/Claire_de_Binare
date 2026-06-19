from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .snapshot import EvidenceSnapshot, SNAPSHOT_SCHEMA_VERSION

ALERT_REPORT_SCHEMA_VERSION = "cdb.evidence_harvester.alert_report.v1"
DEFAULT_STALE_SNAPSHOT_AFTER_MINUTES = 180
DEFAULT_CRITICAL_STALE_SNAPSHOT_AFTER_MINUTES = 360
ALLOWED_SOURCE_MODES = {"fixture", "future_readonly"}
ALLOWED_GAP_SEVERITIES = {"blocking", "warning", "info"}
ALLOWED_OVERALL_STATUSES = {"ok", "warning", "blocked"}
ALLOWED_ALERT_SEVERITIES = {"info", "warn", "critical"}


class AlertValidationError(ValueError):
    pass


def _parse_ts(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise AlertValidationError(f"{field_name} must not be blank")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise AlertValidationError(
                f"{field_name} must be an ISO-8601 UTC timestamp"
            ) from exc
    else:
        raise AlertValidationError(f"{field_name} must be an ISO-8601 UTC timestamp")

    if parsed.tzinfo is None:
        raise AlertValidationError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AlertValidationError(f"{field_name} must be an object")
    return value


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise AlertValidationError(f"{field_name} must be an array")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise AlertValidationError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise AlertValidationError(f"{field_name} must not be blank")
    return text


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AlertValidationError(f"{field_name} must be a non-negative integer")
    if value < 0:
        raise AlertValidationError(f"{field_name} must be a non-negative integer")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise AlertValidationError(f"{field_name} must be a boolean")
    return value


def _require_exact_keys(
    mapping: Mapping[str, Any],
    field_name: str,
    expected: Sequence[str],
) -> None:
    actual = set(mapping.keys())
    required = set(expected)
    missing = sorted(required - actual)
    extra = sorted(actual - required)
    if missing or extra:
        problems: list[str] = []
        if missing:
            problems.append(f"missing keys: {', '.join(missing)}")
        if extra:
            problems.append(f"unexpected keys: {', '.join(extra)}")
        raise AlertValidationError(f"{field_name} malformed ({'; '.join(problems)})")


def _severity_rank(value: str) -> int:
    return {"critical": 0, "warn": 1, "info": 2}.get(value, 99)


def _gap_severity_to_alert(value: str) -> str:
    if value == "blocking":
        return "critical"
    if value == "warning":
        return "warn"
    return "info"


def _finding_title(finding_type: str) -> str:
    titles = {
        "missing_candles": "Missing candle coverage detected",
        "missing_regime": "Regime coverage gap detected",
        "missing_signal_density": "Zero signal density detected",
        "partial_paper_chains": "Partial paper chains detected",
        "provenance_contamination": "Provenance contamination detected",
        "stale_feed": "Stale candle feed detected",
        "stale_regime": "Stale regime feed detected",
        "stale_snapshot": "Snapshot is stale",
        "zero_paper_chains": "Zero complete paper chains detected",
    }
    return titles.get(finding_type, finding_type.replace("_", " ").title())


def _hash_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_finding_id(
    finding_type: str,
    severity: str,
    scope: str,
    source_refs: Sequence[str],
    summary: str,
) -> str:
    digest = _hash_payload(
        {
            "finding_type": finding_type,
            "severity": severity,
            "scope": scope,
            "source_refs": sorted(source_refs),
            "summary": summary,
        }
    )
    return f"alert-{digest[:12]}"


def _validate_gap_item(index: int, payload: Any) -> dict[str, Any]:
    mapping = _require_mapping(payload, f"gap_findings.items[{index}]")
    _require_exact_keys(
        mapping,
        f"gap_findings.items[{index}]",
        ["gap_id", "gap_type", "severity", "message", "scope", "source_refs"],
    )
    severity = _require_string(
        mapping["severity"], f"gap_findings.items[{index}].severity"
    )
    if severity not in ALLOWED_GAP_SEVERITIES:
        raise AlertValidationError(
            f"gap_findings.items[{index}].severity must be one of blocking|warning|info"
        )
    source_refs = tuple(
        sorted(
            _require_string(
                item,
                f"gap_findings.items[{index}].source_refs[{ref_index}]",
            )
            for ref_index, item in enumerate(
                _require_sequence(
                    mapping["source_refs"],
                    f"gap_findings.items[{index}].source_refs",
                )
            )
        )
    )
    return {
        "gap_id": _require_string(
            mapping["gap_id"], f"gap_findings.items[{index}].gap_id"
        ),
        "gap_type": _require_string(
            mapping["gap_type"], f"gap_findings.items[{index}].gap_type"
        ),
        "severity": severity,
        "message": _require_string(
            mapping["message"], f"gap_findings.items[{index}].message"
        ),
        "scope": _require_string(
            mapping["scope"], f"gap_findings.items[{index}].scope"
        ),
        "source_refs": source_refs,
    }


def _normalize_snapshot(
    snapshot_payload: Mapping[str, Any] | EvidenceSnapshot,
) -> dict[str, Any]:
    payload = (
        snapshot_payload.to_dict()
        if isinstance(snapshot_payload, EvidenceSnapshot)
        else dict(snapshot_payload)
    )
    _require_exact_keys(
        payload,
        "snapshot",
        [
            "metadata",
            "status",
            "coverage",
            "provenance",
            "paper_chains",
            "gap_findings",
            "safety",
            "next_action_hints",
        ],
    )

    metadata = _require_mapping(payload["metadata"], "metadata")
    _require_exact_keys(
        metadata,
        "metadata",
        [
            "schema_version",
            "generated_at_utc",
            "collector_report_hash",
            "collector_report_id",
            "collector_report_schema_version",
            "source_mode",
            "evidence_class",
            "evidence_class_version",
            "produced_by",
            "collector_report_produced_at_utc",
        ],
    )
    schema_version = _require_string(
        metadata["schema_version"], "metadata.schema_version"
    )
    if schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise AlertValidationError(
            f"metadata.schema_version must be {SNAPSHOT_SCHEMA_VERSION}"
        )
    source_mode = _require_string(metadata["source_mode"], "metadata.source_mode")
    if source_mode not in ALLOWED_SOURCE_MODES:
        raise AlertValidationError(
            "metadata.source_mode must be one of fixture|future_readonly"
        )

    status = _require_mapping(payload["status"], "status")
    _require_exact_keys(
        status,
        "status",
        ["overall_status", "gap_counts", "has_zero_paper_chains", "raw_evidence"],
    )
    overall_status = _require_string(status["overall_status"], "status.overall_status")
    if overall_status not in ALLOWED_OVERALL_STATUSES:
        raise AlertValidationError(
            "status.overall_status must be one of ok|warning|blocked"
        )
    gap_counts = _require_mapping(status["gap_counts"], "status.gap_counts")
    _require_exact_keys(
        gap_counts,
        "status.gap_counts",
        ["blocking", "warning", "info"],
    )
    raw_evidence = _require_mapping(status["raw_evidence"], "status.raw_evidence")
    _require_exact_keys(
        raw_evidence,
        "status.raw_evidence",
        [
            "candle_input_count",
            "regime_input_count",
            "paper_chain_input_count",
            "provenance_input_count",
            "observed_input_count",
        ],
    )

    coverage = _require_mapping(payload["coverage"], "coverage")
    _require_exact_keys(coverage, "coverage", ["candles", "regimes"])
    candles = _require_mapping(coverage["candles"], "coverage.candles")
    _require_exact_keys(
        candles,
        "coverage.candles",
        [
            "status",
            "total_streams",
            "observed_count_total",
            "expected_count_total",
            "coverage_pct",
            "stale_stream_count",
            "status_counts",
            "items",
        ],
    )
    regimes = _require_mapping(coverage["regimes"], "coverage.regimes")
    _require_exact_keys(
        regimes,
        "coverage.regimes",
        [
            "status",
            "total_streams",
            "observed_count_total",
            "expected_count_total",
            "coverage_pct",
            "zero_coverage_stream_count",
            "status_counts",
            "items",
        ],
    )

    provenance = _require_mapping(payload["provenance"], "provenance")
    _require_exact_keys(
        provenance,
        "provenance",
        [
            "status",
            "allowed_sources",
            "unknown_source_count",
            "contaminated_source_count",
            "source_findings",
        ],
    )

    paper_chains = _require_mapping(payload["paper_chains"], "paper_chains")
    _require_exact_keys(
        paper_chains,
        "paper_chains",
        [
            "status",
            "total_streams",
            "signal_count_total",
            "decision_count_total",
            "order_count_total",
            "fill_count_total",
            "complete_chain_count_total",
            "partial_chain_count_total",
            "zero_complete_stream_count",
            "zero_signal_stream_count",
            "average_signal_density_per_hour",
            "status_counts",
            "items",
        ],
    )

    gap_findings = _require_mapping(payload["gap_findings"], "gap_findings")
    _require_exact_keys(gap_findings, "gap_findings", ["summary", "items"])
    gap_summary = _require_mapping(gap_findings["summary"], "gap_findings.summary")
    _require_exact_keys(
        gap_summary,
        "gap_findings.summary",
        ["total_count", "blocking_count", "warning_count", "info_count", "by_type"],
    )
    gap_by_type = _require_mapping(
        gap_summary["by_type"], "gap_findings.summary.by_type"
    )
    normalized_gap_items = [
        _validate_gap_item(index, item)
        for index, item in enumerate(
            _require_sequence(gap_findings["items"], "gap_findings.items")
        )
    ]

    safety = _require_mapping(payload["safety"], "safety")
    _require_exact_keys(
        safety,
        "safety",
        [
            "banner",
            "lr_status",
            "live_status",
            "echtgeld_status",
            "runtime_actions",
            "db_execution",
            "background_job_orchestration",
            "allowed_scope",
        ],
    )
    next_action_hints = tuple(
        _require_string(item, f"next_action_hints[{index}]")
        for index, item in enumerate(
            _require_sequence(payload["next_action_hints"], "next_action_hints")
        )
    )

    normalized = {
        "metadata": {
            "schema_version": schema_version,
            "generated_at_utc": _format_ts(
                _parse_ts(metadata["generated_at_utc"], "metadata.generated_at_utc")
            ),
            "collector_report_hash": _require_string(
                metadata["collector_report_hash"], "metadata.collector_report_hash"
            ),
            "collector_report_id": _require_string(
                metadata["collector_report_id"], "metadata.collector_report_id"
            ),
            "collector_report_schema_version": _require_string(
                metadata["collector_report_schema_version"],
                "metadata.collector_report_schema_version",
            ),
            "source_mode": source_mode,
            "evidence_class": _require_string(
                metadata["evidence_class"], "metadata.evidence_class"
            ),
            "evidence_class_version": _require_string(
                metadata["evidence_class_version"],
                "metadata.evidence_class_version",
            ),
            "produced_by": _require_string(
                metadata["produced_by"], "metadata.produced_by"
            ),
            "collector_report_produced_at_utc": _format_ts(
                _parse_ts(
                    metadata["collector_report_produced_at_utc"],
                    "metadata.collector_report_produced_at_utc",
                )
            ),
        },
        "status": {
            "overall_status": overall_status,
            "gap_counts": {
                "blocking": _require_non_negative_int(
                    gap_counts["blocking"], "status.gap_counts.blocking"
                ),
                "warning": _require_non_negative_int(
                    gap_counts["warning"], "status.gap_counts.warning"
                ),
                "info": _require_non_negative_int(
                    gap_counts["info"], "status.gap_counts.info"
                ),
            },
            "has_zero_paper_chains": _require_bool(
                status["has_zero_paper_chains"], "status.has_zero_paper_chains"
            ),
            "raw_evidence": {
                key: _require_non_negative_int(
                    raw_evidence[key], f"status.raw_evidence.{key}"
                )
                for key in raw_evidence
            },
        },
        "gap_findings": {
            "summary": {
                "total_count": _require_non_negative_int(
                    gap_summary["total_count"], "gap_findings.summary.total_count"
                ),
                "blocking_count": _require_non_negative_int(
                    gap_summary["blocking_count"],
                    "gap_findings.summary.blocking_count",
                ),
                "warning_count": _require_non_negative_int(
                    gap_summary["warning_count"],
                    "gap_findings.summary.warning_count",
                ),
                "info_count": _require_non_negative_int(
                    gap_summary["info_count"], "gap_findings.summary.info_count"
                ),
                "by_type": {
                    _require_string(
                        key, f"gap_findings.summary.by_type[{index}].key"
                    ): _require_non_negative_int(
                        value,
                        f"gap_findings.summary.by_type[{index}].value",
                    )
                    for index, (key, value) in enumerate(sorted(gap_by_type.items()))
                },
            },
            "items": tuple(
                sorted(
                    normalized_gap_items,
                    key=lambda item: (
                        item["severity"],
                        item["gap_type"],
                        item["scope"],
                        item["gap_id"],
                    ),
                )
            ),
        },
        "next_action_hints": next_action_hints,
    }
    return normalized


def load_snapshot_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AlertValidationError("Snapshot fixture JSON root must be an object")
    return dict(payload)


@dataclass(frozen=True, slots=True)
class AlertFinding:
    finding_id: str
    finding_type: str
    severity: str
    title: str
    summary: str
    scope: str
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    related_gap_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AlertSummary:
    highest_severity: str
    total_count: int
    critical_count: int
    warn_count: int
    info_count: int
    manual_escalation_recommended: bool


@dataclass(frozen=True, slots=True)
class AlertReport:
    schema_version: str
    evaluated_at_utc: str
    snapshot_generated_at_utc: str
    collector_report_id: str
    collector_report_hash: str
    snapshot_age_minutes: int
    summary: AlertSummary
    findings: tuple[AlertFinding, ...]
    manual_escalation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _merge_finding(existing: AlertFinding, candidate: AlertFinding) -> AlertFinding:
    return AlertFinding(
        finding_id=existing.finding_id,
        finding_type=existing.finding_type,
        severity=existing.severity,
        title=existing.title,
        summary=existing.summary,
        scope=existing.scope,
        source_refs=tuple(sorted({*existing.source_refs, *candidate.source_refs})),
        related_gap_ids=tuple(
            sorted({*existing.related_gap_ids, *candidate.related_gap_ids})
        ),
    )


def _make_gap_finding(gap_item: Mapping[str, Any]) -> AlertFinding | None:
    finding_type = str(gap_item["gap_type"])
    severity = _gap_severity_to_alert(str(gap_item["severity"]))
    if finding_type in {"stale_feed", "zero_paper_chains", "provenance_contamination"}:
        severity = "critical"
    elif finding_type == "missing_signal_density":
        severity = "critical"
    elif finding_type == "partial_paper_chains":
        severity = "warn"
    elif finding_type == "stale_regime":
        severity = "critical"
    elif finding_type not in {
        "missing_candles",
        "missing_regime",
        "stale_feed",
        "stale_regime",
        "zero_paper_chains",
        "partial_paper_chains",
        "missing_signal_density",
        "provenance_contamination",
    }:
        return None

    source_refs = tuple(sorted(str(item) for item in gap_item["source_refs"]))
    summary = str(gap_item["message"])
    finding_id = _build_finding_id(
        finding_type=finding_type,
        severity=severity,
        scope=str(gap_item["scope"]),
        source_refs=source_refs,
        summary=summary,
    )
    return AlertFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        severity=severity,
        title=_finding_title(finding_type),
        summary=summary,
        scope=str(gap_item["scope"]),
        source_refs=source_refs,
        related_gap_ids=(str(gap_item["gap_id"]),),
    )


def _make_stale_snapshot_finding(
    *,
    snapshot_age_minutes: int,
    stale_after_minutes: int,
    critical_after_minutes: int,
    collector_report_id: str,
) -> AlertFinding | None:
    if snapshot_age_minutes <= stale_after_minutes:
        return None
    severity = "critical" if snapshot_age_minutes > critical_after_minutes else "warn"
    summary = (
        f"Snapshot {collector_report_id} is {snapshot_age_minutes} minutes old; "
        f"thresholds warn>{stale_after_minutes} critical>{critical_after_minutes}"
    )
    return AlertFinding(
        finding_id=_build_finding_id(
            finding_type="stale_snapshot",
            severity=severity,
            scope="snapshot",
            source_refs=(collector_report_id,),
            summary=summary,
        ),
        finding_type="stale_snapshot",
        severity=severity,
        title=_finding_title("stale_snapshot"),
        summary=summary,
        scope="snapshot",
        source_refs=(collector_report_id,),
        related_gap_ids=tuple(),
    )


def build_alert_report(
    snapshot_payload: Mapping[str, Any] | EvidenceSnapshot,
    *,
    evaluated_at_utc: datetime | str | None = None,
    stale_snapshot_after_minutes: int = DEFAULT_STALE_SNAPSHOT_AFTER_MINUTES,
    critical_snapshot_after_minutes: int = DEFAULT_CRITICAL_STALE_SNAPSHOT_AFTER_MINUTES,
) -> AlertReport:
    if stale_snapshot_after_minutes <= 0:
        raise AlertValidationError("stale_snapshot_after_minutes must be > 0")
    if critical_snapshot_after_minutes < stale_snapshot_after_minutes:
        raise AlertValidationError(
            "critical_snapshot_after_minutes must be >= stale_snapshot_after_minutes"
        )

    snapshot = _normalize_snapshot(snapshot_payload)
    snapshot_generated_at = _parse_ts(
        snapshot["metadata"]["generated_at_utc"],
        "metadata.generated_at_utc",
    )
    evaluated_at = (
        _parse_ts(evaluated_at_utc, "evaluated_at_utc")
        if evaluated_at_utc is not None
        else snapshot_generated_at
    )
    snapshot_age_minutes = int(
        (evaluated_at - snapshot_generated_at).total_seconds() // 60
    )
    if snapshot_age_minutes < 0:
        raise AlertValidationError(
            "evaluated_at_utc must be >= metadata.generated_at_utc"
        )

    findings_by_id: dict[str, AlertFinding] = {}
    for gap_item in snapshot["gap_findings"]["items"]:
        finding = _make_gap_finding(gap_item)
        if finding is None:
            continue
        existing = findings_by_id.get(finding.finding_id)
        findings_by_id[finding.finding_id] = (
            _merge_finding(existing, finding) if existing else finding
        )

    stale_snapshot_finding = _make_stale_snapshot_finding(
        snapshot_age_minutes=snapshot_age_minutes,
        stale_after_minutes=stale_snapshot_after_minutes,
        critical_after_minutes=critical_snapshot_after_minutes,
        collector_report_id=snapshot["metadata"]["collector_report_id"],
    )
    if stale_snapshot_finding is not None:
        findings_by_id[stale_snapshot_finding.finding_id] = stale_snapshot_finding

    findings = tuple(
        sorted(
            findings_by_id.values(),
            key=lambda item: (
                _severity_rank(item.severity),
                item.finding_type,
                item.scope,
                item.finding_id,
            ),
        )
    )
    critical_count = sum(1 for item in findings if item.severity == "critical")
    warn_count = sum(1 for item in findings if item.severity == "warn")
    info_count = sum(1 for item in findings if item.severity == "info")
    if critical_count:
        highest_severity = "critical"
    elif warn_count:
        highest_severity = "warn"
    else:
        highest_severity = "info"
    summary = AlertSummary(
        highest_severity=highest_severity,
        total_count=len(findings),
        critical_count=critical_count,
        warn_count=warn_count,
        info_count=info_count,
        manual_escalation_recommended=bool(findings),
    )
    return AlertReport(
        schema_version=ALERT_REPORT_SCHEMA_VERSION,
        evaluated_at_utc=_format_ts(evaluated_at),
        snapshot_generated_at_utc=_format_ts(snapshot_generated_at),
        collector_report_id=snapshot["metadata"]["collector_report_id"],
        collector_report_hash=snapshot["metadata"]["collector_report_hash"],
        snapshot_age_minutes=snapshot_age_minutes,
        summary=summary,
        findings=findings,
    )


def alert_report_to_markdown(report: AlertReport) -> str:
    payload = report.to_dict()
    lines = [
        "# Evidence Alert Report",
        "",
        "## Summary",
        f"- Highest severity: {payload['summary']['highest_severity']}",
        f"- Evaluated at (UTC): {payload['evaluated_at_utc']}",
        f"- Snapshot generated at (UTC): {payload['snapshot_generated_at_utc']}",
        f"- Snapshot age (minutes): {payload['snapshot_age_minutes']}",
        f"- Collector report: {payload['collector_report_id']}",
        f"- Findings: total={payload['summary']['total_count']}, critical={payload['summary']['critical_count']}, warn={payload['summary']['warn_count']}, info={payload['summary']['info_count']}",
        "- Escalation mode: manual only; no automatic GitHub writes.",
        "",
        "## Findings",
    ]
    if payload["findings"]:
        for item in payload["findings"]:
            lines.append(
                f"- [{item['severity']}] {item['finding_type']} @ {item['scope']}: {item['summary']}"
            )
    else:
        lines.append("- No alert-worthy evidence gaps detected.")
    lines.extend(
        [
            "",
            "## Manual Escalation",
            "- Report and issue draft generation are local text outputs only.",
            "- Review findings before creating or updating any GitHub issue manually.",
            "- No LR-Go, no Live-Go, no Echtgeld-Go.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_issue_draft(
    report: AlertReport,
    *,
    issue_number: str | int | None = None,
    parent_issue: str | int | None = None,
) -> str:
    payload = report.to_dict()
    title = f"[EVIDENCE][HARVESTER][ALERTS] Manual escalation for {payload['collector_report_id']}"
    lines = [
        title,
        "",
        "Manual escalation draft only. No automatic GitHub writes were performed.",
        "",
        "## Alerting summary",
        f"- Collector report: `{payload['collector_report_id']}`",
        f"- Highest severity: `{payload['summary']['highest_severity']}`",
        f"- Evaluated at (UTC): `{payload['evaluated_at_utc']}`",
        f"- Snapshot age (minutes): `{payload['snapshot_age_minutes']}`",
        f"- Findings: total={payload['summary']['total_count']}, critical={payload['summary']['critical_count']}, warn={payload['summary']['warn_count']}, info={payload['summary']['info_count']}",
    ]
    if issue_number is not None:
        lines.append(f"- Target issue context: `#{issue_number}`")
    if parent_issue is not None:
        lines.append(f"- Parent issue context: `#{parent_issue}`")
    lines.extend(["", "## Findings"])
    if payload["findings"]:
        for item in payload["findings"]:
            lines.append(
                f"- [{item['severity']}] `{item['finding_type']}` at `{item['scope']}`: {item['summary']}"
            )
    else:
        lines.append("- No findings.")
    lines.extend(
        [
            "",
            "## Safety",
            "- Manual review required before any GitHub action.",
            "- No runtime / no DB execution / no Docker / no secrets.",
            "- No LR-Go / No Live-Go / No Echtgeld-Go.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic evidence-gap alerts from snapshot fixtures."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Path to a normalized snapshot JSON fixture.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for the JSON alert report.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for the Markdown alert report.",
    )
    parser.add_argument(
        "--issue-draft-output",
        type=Path,
        help="Optional path for a plain-text/Markdown issue draft.",
    )
    parser.add_argument(
        "--evaluated-at-utc",
        help="Optional explicit evaluation timestamp for deterministic stale-snapshot checks.",
    )
    parser.add_argument(
        "--stale-snapshot-after-minutes",
        type=int,
        default=DEFAULT_STALE_SNAPSHOT_AFTER_MINUTES,
        help="Warn threshold for snapshot staleness.",
    )
    parser.add_argument(
        "--critical-snapshot-after-minutes",
        type=int,
        default=DEFAULT_CRITICAL_STALE_SNAPSHOT_AFTER_MINUTES,
        help="Critical threshold for snapshot staleness.",
    )
    parser.add_argument(
        "--issue-number",
        help="Optional issue number to include in the issue draft text.",
    )
    parser.add_argument(
        "--parent-issue",
        help="Optional parent issue number to include in the issue draft text.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output instead of compact JSON.",
    )
    return parser.parse_args(argv)


def _write_text(path: Path, text: str) -> None:
    path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshot_payload = load_snapshot_fixture(args.fixture)
    report = build_alert_report(
        snapshot_payload,
        evaluated_at_utc=args.evaluated_at_utc,
        stale_snapshot_after_minutes=args.stale_snapshot_after_minutes,
        critical_snapshot_after_minutes=args.critical_snapshot_after_minutes,
    )
    report_payload = report.to_dict()
    json_text = json.dumps(
        report_payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )
    markdown_text = alert_report_to_markdown(report)
    issue_draft_text = build_issue_draft(
        report,
        issue_number=args.issue_number,
        parent_issue=args.parent_issue,
    )

    if args.json_output:
        _write_text(args.json_output, json_text)
    if args.markdown_output:
        _write_text(args.markdown_output, markdown_text)
    if args.issue_draft_output:
        _write_text(args.issue_draft_output, issue_draft_text)
    if (
        not args.json_output
        and not args.markdown_output
        and not args.issue_draft_output
    ):
        print(json_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
