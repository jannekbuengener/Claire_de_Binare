from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .snapshot import SNAPSHOT_SCHEMA_VERSION, SAFETY_BANNER

ALERT_REPORT_SCHEMA_VERSION = "cdb.evidence_harvester.alert_report.v1"
ALLOWED_SOURCE_MODES = {"fixture", "future_readonly"}
EXPECTED_SNAPSHOT_SCHEMA = SNAPSHOT_SCHEMA_VERSION
EXPECTED_ALERT_SCHEMA = ALERT_REPORT_SCHEMA_VERSION

DEFAULT_EXPECTED_SNAPSHOT_COUNT = 1
DEFAULT_EXPECTED_WINDOW_HOURS = 24
DEFAULT_CADENCE_TOLERANCE_MINUTES = 60


class ValidationError(ValueError):
    pass


def _parse_ts(value: str, field_name: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must not be blank")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must not be blank")
    return text


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be an object")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a boolean")
    return value


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be a non-negative integer")
    if value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValidationError(f"Failed to parse {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{path.name} JSON root must be an object")
    return payload


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    check_id: str
    check_name: str
    severity: str
    message: str
    artifact: str = ""
    field_name: str = ""


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    verdict: str
    total_checks: int
    fail_count: int
    warn_count: int
    pass_count: int


@dataclass(frozen=True, slots=True)
class ValidationReport:
    schema_version: str
    validated_at_utc: str
    window_start_utc: str
    window_end_utc: str
    snapshot_count: int
    alert_report_count: int
    findings: tuple[ValidationFinding, ...]
    summary: ValidationSummary

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_safety_flags(
    metadata: dict[str, Any],
    safety: dict[str, Any],
    artifact_label: str,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    safety_fields = {
        "lr_status": "NO-GO",
        "live_status": "NO-GO",
        "echtgeld_status": "NO-GO",
        "runtime_actions": "not_allowed",
        "db_execution": "not_allowed",
    }
    for sf_key, expected in safety_fields.items():
        actual = safety.get(sf_key)
        if actual != expected:
            findings.append(
                ValidationFinding(
                    check_id=f"safety-{sf_key}",
                    check_name=f"Safety flag: {sf_key}",
                    severity="fail",
                    message=(f"Expected {sf_key}={expected!r}, got {actual!r}"),
                    artifact=artifact_label,
                    field_name=f"safety.{sf_key}",
                )
            )
    banner = safety.get("banner", "")
    if SAFETY_BANNER not in banner:
        findings.append(
            ValidationFinding(
                check_id="safety-banner",
                check_name="Safety banner present",
                severity="fail",
                message="Safety banner does not match expected text",
                artifact=artifact_label,
                field_name="safety.banner",
            )
        )
    source_mode = metadata.get("source_mode", "")
    if source_mode not in ALLOWED_SOURCE_MODES:
        findings.append(
            ValidationFinding(
                check_id="safety-source-mode",
                check_name="Source mode is safe",
                severity="fail",
                message=(f"source_mode={source_mode!r} not in allowed set"),
                artifact=artifact_label,
                field_name="metadata.source_mode",
            )
        )
    return findings


def _check_snapshot_integrity(
    payload: dict[str, Any],
    artifact_label: str,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    metadata = _require_mapping(
        payload.get("metadata", {}), f"{artifact_label}.metadata"
    )
    schema_version = metadata.get("schema_version", "")
    if schema_version != EXPECTED_SNAPSHOT_SCHEMA:
        findings.append(
            ValidationFinding(
                check_id="snapshot-schema-version",
                check_name="Snapshot schema version",
                severity="fail",
                message=(
                    f"Expected schema_version={EXPECTED_SNAPSHOT_SCHEMA!r}, "
                    f"got {schema_version!r}"
                ),
                artifact=artifact_label,
                field_name="metadata.schema_version",
            )
        )
    collector_report_hash = metadata.get("collector_report_hash", "")
    if not collector_report_hash:
        findings.append(
            ValidationFinding(
                check_id="snapshot-collector-hash",
                check_name="Collector report hash present",
                severity="fail",
                message="collector_report_hash is missing or empty",
                artifact=artifact_label,
                field_name="metadata.collector_report_hash",
            )
        )
    generated_at_utc = metadata.get("generated_at_utc", "")
    if generated_at_utc:
        try:
            _parse_ts(generated_at_utc, "metadata.generated_at_utc")
        except ValidationError:
            findings.append(
                ValidationFinding(
                    check_id="snapshot-generated-at",
                    check_name="Snapshot generated_at_utc is valid ISO-8601",
                    severity="fail",
                    message=f"generated_at_utc={generated_at_utc!r} is not valid ISO-8601",
                    artifact=artifact_label,
                    field_name="metadata.generated_at_utc",
                )
            )
    else:
        findings.append(
            ValidationFinding(
                check_id="snapshot-generated-at",
                check_name="Snapshot generated_at_utc present",
                severity="fail",
                message="generated_at_utc is missing or empty",
                artifact=artifact_label,
                field_name="metadata.generated_at_utc",
            )
        )
    safety = _require_mapping(payload.get("safety", {}), f"{artifact_label}.safety")
    findings.extend(_check_safety_flags(metadata, safety, artifact_label))
    return findings


def _check_alert_report_integrity(
    payload: dict[str, Any],
    artifact_label: str,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    schema_version = payload.get("schema_version", "")
    if schema_version != EXPECTED_ALERT_SCHEMA:
        findings.append(
            ValidationFinding(
                check_id="alert-schema-version",
                check_name="Alert schema version",
                severity="fail",
                message=(
                    f"Expected schema_version={EXPECTED_ALERT_SCHEMA!r}, "
                    f"got {schema_version!r}"
                ),
                artifact=artifact_label,
                field_name="schema_version",
            )
        )
    evaluated_at_utc = payload.get("evaluated_at_utc", "")
    if evaluated_at_utc:
        try:
            _parse_ts(evaluated_at_utc, "evaluated_at_utc")
        except ValidationError:
            findings.append(
                ValidationFinding(
                    check_id="alert-evaluated-at",
                    check_name="Alert evaluated_at_utc is valid ISO-8601",
                    severity="fail",
                    message=f"evaluated_at_utc={evaluated_at_utc!r} is not valid ISO-8601",
                    artifact=artifact_label,
                    field_name="evaluated_at_utc",
                )
            )
    else:
        findings.append(
            ValidationFinding(
                check_id="alert-evaluated-at",
                check_name="Alert evaluated_at_utc present",
                severity="fail",
                message="evaluated_at_utc is missing or empty",
                artifact=artifact_label,
                field_name="evaluated_at_utc",
            )
        )
    snapshot_generated_at_utc = payload.get("snapshot_generated_at_utc", "")
    if snapshot_generated_at_utc:
        try:
            _parse_ts(snapshot_generated_at_utc, "snapshot_generated_at_utc")
        except ValidationError:
            findings.append(
                ValidationFinding(
                    check_id="alert-snapshot-ts",
                    check_name="Alert snapshot_generated_at_utc is valid ISO-8601",
                    severity="fail",
                    message=(
                        f"snapshot_generated_at_utc={snapshot_generated_at_utc!r} "
                        "is not valid ISO-8601"
                    ),
                    artifact=artifact_label,
                    field_name="snapshot_generated_at_utc",
                )
            )
    collector_report_hash = payload.get("collector_report_hash", "")
    if not collector_report_hash:
        findings.append(
            ValidationFinding(
                check_id="alert-collector-hash",
                check_name="Alert collector_report_hash present",
                severity="fail",
                message="collector_report_hash is missing or empty",
                artifact=artifact_label,
                field_name="collector_report_hash",
            )
        )
    summary = _require_mapping(payload.get("summary", {}), f"{artifact_label}.summary")
    manual_escalation_only = summary.get(
        "manual_escalation_only", payload.get("manual_escalation_only", True)
    )
    if isinstance(manual_escalation_only, bool) and not manual_escalation_only:
        findings.append(
            ValidationFinding(
                check_id="alert-manual-escalation",
                check_name="Alert is manual-escalation only",
                severity="fail",
                message="manual_escalation_only is false; auto-escalation would violate safety",
                artifact=artifact_label,
                field_name="manual_escalation_only",
            )
        )
    return findings


def _check_no_trading_side_effects(
    payload: dict[str, Any],
    artifact_label: str,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    scan_payload = {k: v for k, v in payload.items() if k != "safety"}
    text = json.dumps(scan_payload, sort_keys=True)
    forbidden_patterns = [
        "LR-Go",
        "Live-Go",
        "Echtgeld-Go",
        "trade_executed",
        "order_submitted",
        "position_opened",
    ]
    for pattern in forbidden_patterns:
        if pattern in text:
            findings.append(
                ValidationFinding(
                    check_id=f"side-effect-{pattern.lower().replace('-', '_').replace(' ', '_')}",
                    check_name=f"No trading side-effect: {pattern}",
                    severity="fail",
                    message=f"Found forbidden pattern {pattern!r} in artifact content outside safety section",
                    artifact=artifact_label,
                )
            )
    return findings


def validate_24h_window(
    snapshot_paths: Sequence[Path],
    alert_report_paths: Sequence[Path],
    *,
    window_start_utc: datetime,
    window_end_utc: datetime,
    expected_snapshot_count: int = DEFAULT_EXPECTED_SNAPSHOT_COUNT,
    cadence_tolerance_minutes: int = DEFAULT_CADENCE_TOLERANCE_MINUTES,
) -> ValidationReport:
    if window_end_utc <= window_start_utc:
        raise ValidationError("window_end_utc must be after window_start_utc")
    if expected_snapshot_count < 1:
        raise ValidationError("expected_snapshot_count must be >= 1")
    if cadence_tolerance_minutes < 0:
        raise ValidationError("cadence_tolerance_minutes must be >= 0")

    findings: list[ValidationFinding] = []
    check_id_counter = 0

    def _next_id() -> str:
        nonlocal check_id_counter
        check_id_counter += 1
        return f"V{check_id_counter:03d}"

    snapshot_payloads: list[dict[str, Any]] = []
    for path in snapshot_paths:
        label = path.name
        try:
            payload = _load_json(path)
            snapshot_payloads.append(payload)
            findings.append(
                ValidationFinding(
                    check_id=_next_id(),
                    check_name=f"Snapshot {label} parses as valid JSON",
                    severity="pass",
                    message=f"Valid JSON ({len(json.dumps(payload))} bytes)",
                    artifact=label,
                )
            )
        except ValidationError as exc:
            findings.append(
                ValidationFinding(
                    check_id=_next_id(),
                    check_name=f"Snapshot {label} parses as valid JSON",
                    severity="fail",
                    message=str(exc),
                    artifact=label,
                )
            )
            continue
        findings.extend(_check_snapshot_integrity(payload, label))
        findings.extend(_check_no_trading_side_effects(payload, label))

    alert_payloads: list[dict[str, Any]] = []
    for path in alert_report_paths:
        label = path.name
        try:
            payload = _load_json(path)
            alert_payloads.append(payload)
            findings.append(
                ValidationFinding(
                    check_id=_next_id(),
                    check_name=f"Alert report {label} parses as valid JSON",
                    severity="pass",
                    message=f"Valid JSON ({len(json.dumps(payload))} bytes)",
                    artifact=label,
                )
            )
        except ValidationError as exc:
            findings.append(
                ValidationFinding(
                    check_id=_next_id(),
                    check_name=f"Alert report {label} parses as valid JSON",
                    severity="fail",
                    message=str(exc),
                    artifact=label,
                )
            )
            continue
        findings.extend(_check_alert_report_integrity(payload, label))
        findings.extend(_check_no_trading_side_effects(payload, label))

    if len(snapshot_paths) < expected_snapshot_count:
        findings.append(
            ValidationFinding(
                check_id=_next_id(),
                check_name="Expected snapshot count",
                severity="fail",
                message=(
                    f"Expected at least {expected_snapshot_count} snapshot(s), "
                    f"found {len(snapshot_paths)}"
                ),
            )
        )
    else:
        findings.append(
            ValidationFinding(
                check_id=_next_id(),
                check_name="Expected snapshot count",
                severity="pass",
                message=(
                    f"Found {len(snapshot_paths)} snapshot(s), "
                    f"meets minimum of {expected_snapshot_count}"
                ),
            )
        )

    timestamps: list[datetime] = []
    for payload in snapshot_payloads:
        try:
            ts = _parse_ts(
                payload.get("metadata", {}).get("generated_at_utc", ""),
                "generated_at_utc",
            )
            timestamps.append(ts)
        except ValidationError:
            pass

    if timestamps:
        earliest = min(timestamps)
        latest = max(timestamps)
        if earliest < window_start_utc:
            findings.append(
                ValidationFinding(
                    check_id=_next_id(),
                    check_name="Snapshot timestamps within window",
                    severity="warn",
                    message=(
                        f"Earliest snapshot at {_format_ts(earliest)} "
                        f"is before window start {_format_ts(window_start_utc)}"
                    ),
                )
            )
        if latest > window_end_utc:
            findings.append(
                ValidationFinding(
                    check_id=_next_id(),
                    check_name="Snapshot timestamps within window",
                    severity="warn",
                    message=(
                        f"Latest snapshot at {_format_ts(latest)} "
                        f"is after window end {_format_ts(window_end_utc)}"
                    ),
                )
            )
        if len(timestamps) > 1:
            sorted_ts = sorted(timestamps)
            for i in range(len(sorted_ts) - 1):
                gap = (sorted_ts[i + 1] - sorted_ts[i]).total_seconds() / 60
                if gap > cadence_tolerance_minutes:
                    findings.append(
                        ValidationFinding(
                            check_id=_next_id(),
                            check_name="Snapshot cadence",
                            severity="warn",
                            message=(
                                f"Gap of {gap:.0f} minutes between snapshots "
                                f"exceeds tolerance of {cadence_tolerance_minutes} minutes"
                            ),
                        )
                    )

    if not alert_report_paths:
        findings.append(
            ValidationFinding(
                check_id=_next_id(),
                check_name="Alert report existence",
                severity="warn",
                message=(
                    "No alert report provided; if no alerts were generated, "
                    "explicit no-alert evidence is recommended"
                ),
            )
        )
    else:
        findings.append(
            ValidationFinding(
                check_id=_next_id(),
                check_name="Alert report existence",
                severity="pass",
                message=f"Found {len(alert_report_paths)} alert report(s)",
            )
        )

    fail_count = sum(1 for f in findings if f.severity == "fail")
    warn_count = sum(1 for f in findings if f.severity == "warn")
    pass_count = sum(1 for f in findings if f.severity == "pass")
    if fail_count:
        verdict = "FAIL"
    elif warn_count:
        verdict = "WARN"
    else:
        verdict = "PASS"

    now = cdb_utcnow().astimezone(UTC)
    return ValidationReport(
        schema_version="cdb.evidence_harvester.24h_validation.v1",
        validated_at_utc=_format_ts(now),
        window_start_utc=_format_ts(window_start_utc),
        window_end_utc=_format_ts(window_end_utc),
        snapshot_count=len(snapshot_paths),
        alert_report_count=len(alert_report_paths),
        findings=tuple(
            sorted(
                findings,
                key=lambda f: (
                    {"fail": 0, "warn": 1, "pass": 2}.get(f.severity, 9),
                    f.check_id,
                ),
            )
        ),
        summary=ValidationSummary(
            verdict=verdict,
            total_checks=len(findings),
            fail_count=fail_count,
            warn_count=warn_count,
            pass_count=pass_count,
        ),
    )


def validate_24h_window_from_dir(
    artifact_dir: Path,
    *,
    window_start_utc: datetime | None = None,
    window_end_utc: datetime | None = None,
    expected_snapshot_count: int = DEFAULT_EXPECTED_SNAPSHOT_COUNT,
    cadence_tolerance_minutes: int = DEFAULT_CADENCE_TOLERANCE_MINUTES,
) -> ValidationReport:
    if not artifact_dir.exists():
        raise ValidationError(f"Artifact directory does not exist: {artifact_dir}")
    if not artifact_dir.is_dir():
        raise ValidationError(f"Path is not a directory: {artifact_dir}")

    snapshot_paths = sorted(artifact_dir.glob("snapshot_*.json"))
    alert_paths = sorted(artifact_dir.glob("alert_*.json"))
    if not alert_paths:
        alert_paths = sorted(artifact_dir.glob("alerts_*.json"))

    window_end = window_end_utc or cdb_utcnow().astimezone(UTC)
    if window_start_utc is None:
        window_start = window_end - timedelta(hours=DEFAULT_EXPECTED_WINDOW_HOURS)
    else:
        window_start = window_start_utc

    return validate_24h_window(
        snapshot_paths,
        alert_paths,
        window_start_utc=window_start,
        window_end_utc=window_end,
        expected_snapshot_count=expected_snapshot_count,
        cadence_tolerance_minutes=cadence_tolerance_minutes,
    )


def _render_finding(f: ValidationFinding) -> str:
    icon = {"fail": "FAIL", "warn": "WARN", "pass": "PASS"}.get(f.severity, "????")
    artifact_part = f" [{f.artifact}]" if f.artifact else ""
    field_part = f" ({f.field_name})" if f.field_name else ""
    return f"  [{icon}] {f.check_name}{artifact_part}{field_part}: {f.message}"


def report_to_markdown(report: ValidationReport) -> str:
    payload = report.to_dict()
    lines = [
        "# 24h Dry Validation Report",
        "",
        "## Metadata",
        f"- Schema version: {payload['schema_version']}",
        f"- Validated at (UTC): {payload['validated_at_utc']}",
        f"- Window start (UTC): {payload['window_start_utc']}",
        f"- Window end (UTC): {payload['window_end_utc']}",
        f"- Snapshot count: {payload['snapshot_count']}",
        f"- Alert report count: {payload['alert_report_count']}",
        "",
        "## Summary",
        f"- Verdict: **{payload['summary']['verdict']}**",
        f"- Total checks: {payload['summary']['total_checks']}",
        f"- Pass: {payload['summary']['pass_count']}",
        f"- Warn: {payload['summary']['warn_count']}",
        f"- Fail: {payload['summary']['fail_count']}",
        "",
        "## Findings",
    ]
    for item in payload["findings"]:
        lines.append(_render_finding(ValidationFinding(**item)))
    lines.extend(
        [
            "",
            "## Safety",
            "- No LR-Go / No Live-Go / No Echtgeld-Go.",
            "- No runtime / no DB execution / no Docker / no secrets.",
            "- Validation is read-only and does not start any background process.",
        ]
    )
    return "\n".join(lines) + "\n"


def _now_utc() -> datetime:
    return cdb_utcnow().astimezone(UTC)


def parse_args(argv: list[str] | None = None) -> Any:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate 24h evidence harvester dry collection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dir_parser = subparsers.add_parser(
        "validate-dir",
        help="Validate artifacts in a directory.",
    )
    dir_parser.add_argument(
        "--artifact-dir",
        type=Path,
        required=True,
        help="Directory containing snapshot_*.json and alert_*.json files.",
    )
    dir_parser.add_argument(
        "--window-start-utc",
        help="ISO-8601 start of the 24h window.",
    )
    dir_parser.add_argument(
        "--window-end-utc",
        help="ISO-8601 end of the 24h window (default: now).",
    )
    dir_parser.add_argument(
        "--expected-snapshot-count",
        type=int,
        default=DEFAULT_EXPECTED_SNAPSHOT_COUNT,
        help="Minimum expected snapshots (default: 1).",
    )
    dir_parser.add_argument(
        "--cadence-tolerance-minutes",
        type=int,
        default=DEFAULT_CADENCE_TOLERANCE_MINUTES,
        help="Max gap between consecutive snapshots in minutes (default: 60).",
    )
    dir_parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for JSON validation report.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    dir_parser.set_defaults(handler=_handle_validate_dir)

    return parser.parse_args(argv)


def _handle_validate_dir(args: Any) -> int:
    window_start = (
        _parse_ts(args.window_start_utc, "--window-start-utc")
        if args.window_start_utc
        else None
    )
    window_end = (
        _parse_ts(args.window_end_utc, "--window-end-utc")
        if args.window_end_utc
        else None
    )
    report = validate_24h_window_from_dir(
        args.artifact_dir,
        window_start_utc=window_start,
        window_end_utc=window_end,
        expected_snapshot_count=args.expected_snapshot_count,
        cadence_tolerance_minutes=args.cadence_tolerance_minutes,
    )
    payload = report.to_dict()
    json_text = json.dumps(
        payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )
    if args.json_output:
        args.json_output.write_text(
            json_text + ("\n" if not json_text.endswith("\n") else ""),
            encoding="utf-8",
        )
        print(report_to_markdown(report))
    else:
        print(json_text)
    return 0 if report.summary.verdict != "FAIL" else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
