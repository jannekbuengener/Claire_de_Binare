from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .alerts import ALERT_REPORT_SCHEMA_VERSION
from .boot import BOOT_READINESS_SCHEMA
from .coordinator import RECOVERY_EVENT_SCHEMA
from .runner import HEARTBEAT_SCHEMA, STATE_SCHEMA
from .snapshot import SAFETY_BANNER, SNAPSHOT_SCHEMA_VERSION
from .write_audit import COLLECTOR_REPORT_SCHEMA, WRITE_AUDIT_REPORT_SCHEMA
from .watchdog import WATCHDOG_REPORT_SCHEMA

OPS_VALIDATION_SCHEMA_VERSION = "cdb.evidence_harvester.ops_validation.v1"
ALLOWED_SOURCE_MODES = {"fixture", "future_readonly"}

DEFAULT_REQUIRED_WINDOW_HOURS = 72
DEFAULT_RUNNER_CADENCE_SECONDS = 900
DEFAULT_WARN_GRACE_SECONDS = 300
DEFAULT_FAIL_MULTIPLIER = 2.0

RUNTIME_ARTIFACT_DIR_TEMPLATE = (
    "artifacts/evidence_harvester/72h_ops_validation/<run_id>/"
)
RUNTIME_SEED_FIXTURE = "artifacts/evidence_harvester/24h_dry_run/collector_input.json"

REQUIRED_ARTIFACT_RULES: dict[str, str] = {
    "collector_reports": "collector_report_*.json",
    "snapshots_json": "snapshot_*.json",
    "snapshots_md": "snapshot_*.md",
    "alerts_json": "alert_*.json",
    "alerts_md": "alert_*.md",
    "coordinator_events": "coordinator_events.jsonl",
    "heartbeat": "runner_heartbeat.json",
    "state": "runner_state.json",
    "watchdog_json": "watchdog_report_*.json",
    "watchdog_md": "watchdog_report_*.md",
    "write_audit_json": "write_audit_report_*.json",
    "write_audit_md": "write_audit_report_*.md",
    "boot_json": "boot_readiness_report*.json",
    "boot_md": "boot_readiness_report*.md",
}

REQUIRED_RUNTIME_ARTIFACTS: tuple[str, ...] = (
    "collector_report_<stamp>.json",
    "snapshot_<stamp>.json",
    "snapshot_<stamp>.md",
    "alert_<stamp>.json",
    "alert_<stamp>.md",
    "coordinator_events.jsonl",
    "runner_heartbeat.json",
    "runner_state.json",
    "watchdog_report_<stamp>.json",
    "watchdog_report_<stamp>.md",
    "write_audit_report_<stamp>.json",
    "write_audit_report_<stamp>.md",
    "boot_readiness_report.json",
    "boot_readiness_report.md",
    "recovery_event_<stamp>.json (optional)",
    "recovery_event_<stamp>.md (optional)",
    "ops_validation_report.json",
    "ops_validation_report.md",
)

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "LR-Go",
    "Live-Go",
    "Echtgeld-Go",
    "trade_executed",
    "order_submitted",
    "position_opened",
)


class OpsValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OpsValidationFinding:
    check_id: str
    check_name: str
    severity: str
    message: str
    artifact: str = ""
    field_name: str = ""


@dataclass(frozen=True, slots=True)
class OpsValidationSummary:
    verdict: str
    total_checks: int
    pass_count: int
    warn_count: int
    fail_count: int


@dataclass(frozen=True, slots=True)
class RuntimeHandoff:
    artifact_dir_template: str
    seed_fixture: str
    runner_cadence_seconds: int
    required_window_hours: int
    expected_min_cycles: int
    watchdog_after_each_runner_cycle: bool
    write_audit_after_each_runner_cycle: bool
    required_artifacts: tuple[str, ...]
    boot_preflight_commands: tuple[str, ...]
    enable_commands: tuple[str, ...]
    start_commands: tuple[str, ...]
    stop_commands: tuple[str, ...]
    side_effect_checklist: tuple[str, ...]
    operator_approval_checkpoint: str
    safety_statement: str
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OpsValidationReport:
    schema_version: str
    validated_at_utc: str
    artifact_dir: str
    window_start_utc: str
    window_end_utc: str
    observed_window_hours: float
    required_window_hours: int
    cadence_seconds: int
    expected_min_cycles: int
    observed_counts: dict[str, int]
    findings: tuple[OpsValidationFinding, ...]
    summary: OpsValidationSummary
    runtime_handoff: RuntimeHandoff

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_utc() -> datetime:
    now = cdb_utcnow()
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_ts(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise OpsValidationError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise OpsValidationError(f"{field_name} must not be blank")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise OpsValidationError(
            f"{field_name} must be an ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise OpsValidationError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OpsValidationError(f"Malformed JSON in {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OpsValidationError(f"{path.name} JSON root must be an object")
    return payload


def _collect_artifact_paths(artifact_dir: Path) -> dict[str, list[Path]]:
    return {
        "collector_reports": sorted(artifact_dir.glob("collector_report_*.json")),
        "snapshots_json": sorted(artifact_dir.glob("snapshot_*.json")),
        "snapshots_md": sorted(artifact_dir.glob("snapshot_*.md")),
        "alerts_json": sorted(artifact_dir.glob("alert_*.json")),
        "alerts_md": sorted(artifact_dir.glob("alert_*.md")),
        "coordinator_events": (
            [artifact_dir / "coordinator_events.jsonl"]
            if (artifact_dir / "coordinator_events.jsonl").exists()
            else []
        ),
        "heartbeat": (
            [artifact_dir / "runner_heartbeat.json"]
            if (artifact_dir / "runner_heartbeat.json").exists()
            else []
        ),
        "state": (
            [artifact_dir / "runner_state.json"]
            if (artifact_dir / "runner_state.json").exists()
            else []
        ),
        "watchdog_json": sorted(artifact_dir.glob("watchdog_report_*.json")),
        "watchdog_md": sorted(artifact_dir.glob("watchdog_report_*.md")),
        "write_audit_json": sorted(artifact_dir.glob("write_audit_report_*.json")),
        "write_audit_md": sorted(artifact_dir.glob("write_audit_report_*.md")),
        "boot_json": sorted(artifact_dir.glob("boot_readiness_report*.json")),
        "boot_md": sorted(artifact_dir.glob("boot_readiness_report*.md")),
        "recovery_events_json": sorted(artifact_dir.glob("recovery_event_*.json")),
        "recovery_events_md": sorted(artifact_dir.glob("recovery_event_*.md")),
    }


def _expected_min_cycles(required_window_hours: int, cadence_seconds: int) -> int:
    return max(1, math.floor((required_window_hours * 3600) / cadence_seconds))


def _build_runtime_handoff(
    *, required_window_hours: int, cadence_seconds: int
) -> RuntimeHandoff:
    expected_cycles = _expected_min_cycles(required_window_hours, cadence_seconds)
    bounded_iterations = expected_cycles + 1
    run_dir = RUNTIME_ARTIFACT_DIR_TEMPLATE.rstrip("/")
    return RuntimeHandoff(
        artifact_dir_template=RUNTIME_ARTIFACT_DIR_TEMPLATE,
        seed_fixture=RUNTIME_SEED_FIXTURE,
        runner_cadence_seconds=cadence_seconds,
        required_window_hours=required_window_hours,
        expected_min_cycles=expected_cycles,
        watchdog_after_each_runner_cycle=True,
        write_audit_after_each_runner_cycle=True,
        required_artifacts=REQUIRED_RUNTIME_ARTIFACTS,
        boot_preflight_commands=(
            "python -m tools.evidence_harvester.boot status --pretty",
            (
                "python -m tools.evidence_harvester.boot status "
                f"--json-output {run_dir}\\boot_readiness_report.json "
                f"--markdown-output {run_dir}\\boot_readiness_report.md --pretty"
            ),
        ),
        enable_commands=(
            "No Windows Task install in Phase 1.",
            (
                "Runtime-GO only if scheduling is required: "
                "python -m tools.evidence_harvester.scheduler install --fixture "
                f"{RUNTIME_SEED_FIXTURE} --explicit"
            ),
        ),
        start_commands=(
            (
                "python -m tools.evidence_harvester.coordinator --pretty run-fixture-window "
                f"--fixture {RUNTIME_SEED_FIXTURE} "
                f"--artifact-dir {run_dir} "
                f"--iterations {bounded_iterations} "
                f"--cadence-seconds {cadence_seconds} "
                "--max-restart-count 3 --restart-backoff-seconds 30"
            ),
            (
                "After each runner cycle, write the latest watchdog report for "
                "write-audit compatibility and archive a stamped copy: "
                f"watchdog_report.json plus watchdog_report_<stamp>.json in {run_dir}"
            ),
            (
                "After each runner cycle, archive write-audit outputs as "
                f"write_audit_report_<stamp>.json/.md in {run_dir}"
            ),
        ),
        stop_commands=(
            "Stop the runner process after the bounded loop completes.",
            (
                "If scheduling was enabled under a separate Runtime-GO: "
                "python -m tools.evidence_harvester.scheduler uninstall --explicit"
            ),
            (
                "Run final validation: "
                f"python -m tools.evidence_harvester.ops_validation validate-dir --artifact-dir {run_dir} --pretty"
            ),
        ),
        side_effect_checklist=(
            "No Docker start/stop or compose mutation without explicit operator approval.",
            "No runtime, DB, Redis, secrets, or GitHub write action from module code.",
            "No LR-Go, no Live-Go, no Echtgeld-Go.",
            "No trading, order, risk, or execution mutation.",
        ),
        operator_approval_checkpoint=(
            "Before any Docker or infrastructure mutation, stop and obtain documented "
            "explicit operator approval via Jannek-Ops-GO / Infra-Mutation-Gate."
        ),
        safety_statement=(
            "Dry/paper/research only. LR remains NO-GO. No Live-Go. No Echtgeld-Go."
        ),
        notes=(
            "The 72h validation depends on per-cycle stamped watchdog and write-audit archives.",
            "Keep latest watchdog_report.json/.md current as a compatibility surface for write_audit.py.",
            "Optional recovery_event_<stamp>.json/.md artifacts are accepted when they are audited and bounded.",
        ),
    )


def _check_required_artifacts(
    artifact_paths: Mapping[str, Sequence[Path]],
    add_finding: Any,
) -> None:
    for key, pattern in REQUIRED_ARTIFACT_RULES.items():
        paths = list(artifact_paths.get(key, []))
        if not paths:
            add_finding(
                "Required artifact present",
                "fail",
                f"Missing required artifact matching {pattern}",
                artifact=pattern,
            )
        else:
            add_finding(
                "Required artifact present",
                "pass",
                f"Found {len(paths)} artifact(s) matching {pattern}",
                artifact=pattern,
            )


def _check_matching_counts(
    label: str,
    left_paths: Sequence[Path],
    right_paths: Sequence[Path],
    add_finding: Any,
) -> None:
    if len(left_paths) != len(right_paths):
        add_finding(
            f"{label} companion counts",
            "fail",
            f"Expected matching counts, got {len(left_paths)} and {len(right_paths)}",
        )
    else:
        add_finding(
            f"{label} companion counts",
            "pass",
            f"Matching counts: {len(left_paths)} and {len(right_paths)}",
        )


def _load_payloads(
    paths: Sequence[Path],
    add_finding: Any,
    *,
    expected_schema: str | None = None,
    schema_field: str = "schema_version",
) -> list[tuple[Path, dict[str, Any]]]:
    results: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        try:
            payload = _load_json(path)
            results.append((path, payload))
            add_finding(
                f"{path.name} parses as JSON",
                "pass",
                f"Valid JSON ({len(json.dumps(payload, ensure_ascii=True))} bytes)",
                artifact=path.name,
            )
            if expected_schema is not None:
                actual = payload
                for part in schema_field.split("."):
                    actual = actual.get(part) if isinstance(actual, dict) else None
                if actual != expected_schema:
                    add_finding(
                        f"{path.name} schema version",
                        "fail",
                        f"Expected {schema_field}={expected_schema!r}, got {actual!r}",
                        artifact=path.name,
                        field_name=schema_field,
                    )
                else:
                    add_finding(
                        f"{path.name} schema version",
                        "pass",
                        f"{schema_field} matches {expected_schema}",
                        artifact=path.name,
                        field_name=schema_field,
                    )
        except OpsValidationError as exc:
            add_finding(
                f"{path.name} parses as JSON",
                "fail",
                str(exc),
                artifact=path.name,
            )
    return results


def _check_snapshot_payload(
    path: Path,
    payload: Mapping[str, Any],
    add_finding: Any,
) -> datetime | None:
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        add_finding(
            f"{path.name} metadata present",
            "fail",
            "metadata must be an object",
            artifact=path.name,
            field_name="metadata",
        )
        return None
    source_mode = metadata.get("source_mode", "")
    if source_mode not in ALLOWED_SOURCE_MODES:
        add_finding(
            f"{path.name} safe source_mode",
            "fail",
            f"metadata.source_mode={source_mode!r} not in allowed set",
            artifact=path.name,
            field_name="metadata.source_mode",
        )
    else:
        add_finding(
            f"{path.name} safe source_mode",
            "pass",
            f"metadata.source_mode={source_mode!r} is allowed",
            artifact=path.name,
            field_name="metadata.source_mode",
        )
    safety = payload.get("safety", {})
    if not isinstance(safety, dict):
        add_finding(
            f"{path.name} safety present",
            "fail",
            "safety must be an object",
            artifact=path.name,
            field_name="safety",
        )
        return None
    expected_flags = {
        "lr_status": "NO-GO",
        "live_status": "NO-GO",
        "echtgeld_status": "NO-GO",
        "runtime_actions": "not_allowed",
        "db_execution": "not_allowed",
    }
    for field_name, expected in expected_flags.items():
        actual = safety.get(field_name)
        if actual != expected:
            add_finding(
                f"{path.name} safety flag {field_name}",
                "fail",
                f"Expected {field_name}={expected!r}, got {actual!r}",
                artifact=path.name,
                field_name=f"safety.{field_name}",
            )
        else:
            add_finding(
                f"{path.name} safety flag {field_name}",
                "pass",
                f"{field_name} is {expected!r}",
                artifact=path.name,
                field_name=f"safety.{field_name}",
            )
    banner = str(safety.get("banner", ""))
    if SAFETY_BANNER not in banner:
        add_finding(
            f"{path.name} safety banner",
            "fail",
            "Safety banner does not match expected text",
            artifact=path.name,
            field_name="safety.banner",
        )
    else:
        add_finding(
            f"{path.name} safety banner",
            "pass",
            "Safety banner matches expected text",
            artifact=path.name,
            field_name="safety.banner",
        )
    try:
        return _parse_ts(
            metadata.get("generated_at_utc", ""), "metadata.generated_at_utc"
        )
    except OpsValidationError as exc:
        add_finding(
            f"{path.name} generated_at_utc",
            "fail",
            str(exc),
            artifact=path.name,
            field_name="metadata.generated_at_utc",
        )
        return None


def _check_alert_payload(
    path: Path,
    payload: Mapping[str, Any],
    add_finding: Any,
) -> datetime | None:
    manual_only = payload.get("manual_escalation_only", True)
    if manual_only is not True:
        add_finding(
            f"{path.name} manual escalation only",
            "fail",
            "manual_escalation_only must remain true",
            artifact=path.name,
            field_name="manual_escalation_only",
        )
    else:
        add_finding(
            f"{path.name} manual escalation only",
            "pass",
            "manual_escalation_only is true",
            artifact=path.name,
            field_name="manual_escalation_only",
        )
    try:
        return _parse_ts(payload.get("evaluated_at_utc", ""), "evaluated_at_utc")
    except OpsValidationError as exc:
        add_finding(
            f"{path.name} evaluated_at_utc",
            "fail",
            str(exc),
            artifact=path.name,
            field_name="evaluated_at_utc",
        )
        return None


def _check_boot_payload(
    path: Path,
    payload: Mapping[str, Any],
    add_finding: Any,
) -> datetime | None:
    try:
        ts = _parse_ts(payload.get("evaluated_at_utc", ""), "evaluated_at_utc")
    except OpsValidationError as exc:
        add_finding(
            f"{path.name} evaluated_at_utc",
            "fail",
            str(exc),
            artifact=path.name,
            field_name="evaluated_at_utc",
        )
        return None
    verdict = payload.get("verdict", {})
    verdict_value = verdict.get("verdict") if isinstance(verdict, dict) else None
    if verdict_value == "FAIL":
        add_finding(
            f"{path.name} boot readiness verdict",
            "fail",
            "Boot readiness report is FAIL",
            artifact=path.name,
            field_name="verdict.verdict",
        )
    elif verdict_value == "WARN":
        add_finding(
            f"{path.name} boot readiness verdict",
            "warn",
            "Boot readiness report is WARN; runtime handoff must justify it",
            artifact=path.name,
            field_name="verdict.verdict",
        )
    elif verdict_value == "PASS":
        add_finding(
            f"{path.name} boot readiness verdict",
            "pass",
            "Boot readiness report is PASS",
            artifact=path.name,
            field_name="verdict.verdict",
        )
    else:
        add_finding(
            f"{path.name} boot readiness verdict",
            "fail",
            f"Unexpected boot readiness verdict {verdict_value!r}",
            artifact=path.name,
            field_name="verdict.verdict",
        )
    return ts


def _check_recovery_events(
    payloads: Sequence[tuple[Path, Mapping[str, Any]]],
    add_finding: Any,
) -> tuple[set[str], bool]:
    covered_fail_reports: set[str] = set()
    restart_limit_exceeded = False
    if not payloads:
        return covered_fail_reports, restart_limit_exceeded

    observed_restart_count = 0
    observed_max_restart_count = 0
    worst = "pass"
    for path, payload in payloads:
        classification = str(payload.get("classification", "")).strip().lower()
        action = str(payload.get("action", "")).strip().lower()
        limit_exceeded = bool(payload.get("limit_exceeded", False))
        restart_count = payload.get("restart_count")
        max_restart_count = payload.get("max_restart_count")
        covered = payload.get("covered_report_names", [])
        reason_codes = payload.get("reason_codes", [])

        if not isinstance(restart_count, int) or restart_count < 0:
            add_finding(
                f"{path.name} restart_count",
                "fail",
                f"restart_count must be a non-negative integer, got {restart_count!r}",
                artifact=path.name,
                field_name="restart_count",
            )
            restart_limit_exceeded = True
            continue
        if not isinstance(max_restart_count, int) or max_restart_count < 0:
            add_finding(
                f"{path.name} max_restart_count",
                "fail",
                f"max_restart_count must be a non-negative integer, got {max_restart_count!r}",
                artifact=path.name,
                field_name="max_restart_count",
            )
            restart_limit_exceeded = True
            continue

        observed_restart_count = max(observed_restart_count, restart_count)
        observed_max_restart_count = max(observed_max_restart_count, max_restart_count)

        if classification not in {"recoverable", "fatal"}:
            add_finding(
                f"{path.name} recovery classification",
                "fail",
                f"Unexpected recovery classification {classification!r}",
                artifact=path.name,
                field_name="classification",
            )
            restart_limit_exceeded = True
            continue

        if limit_exceeded or restart_count > max_restart_count:
            add_finding(
                f"{path.name} restart limit",
                "fail",
                (
                    f"Recovery restart_count={restart_count} exceeds max_restart_count="
                    f"{max_restart_count}"
                ),
                artifact=path.name,
                field_name="restart_count",
            )
            restart_limit_exceeded = True
            continue

        if classification == "fatal":
            add_finding(
                f"{path.name} fatal recovery event",
                "fail",
                f"Fatal recovery event recorded with action={action!r}",
                artifact=path.name,
                field_name="classification",
            )
            restart_limit_exceeded = True
            continue

        if not payload.get("audited", False):
            add_finding(
                f"{path.name} audited recovery event",
                "fail",
                "Recovery event must set audited=true",
                artifact=path.name,
                field_name="audited",
            )
            restart_limit_exceeded = True
            continue

        if isinstance(covered, list):
            covered_fail_reports.update(
                str(name) for name in covered if str(name).strip()
            )

        if worst != "fail":
            worst = "warn"
        add_finding(
            f"{path.name} bounded recovery event",
            "warn",
            (
                f"Recoverable event accepted with action={action!r}, restart_count="
                f"{restart_count}/{max_restart_count}, reasons={list(reason_codes)!r}"
            ),
            artifact=path.name,
        )

    if restart_limit_exceeded:
        add_finding(
            "Recovery event history",
            "fail",
            "Recovery events exceed configured restart limits or include fatal events",
        )
    elif observed_restart_count > 0 or payloads:
        add_finding(
            "Recovery event history",
            "warn",
            (
                f"Observed audited recovery events within configured limit "
                f"{observed_restart_count}/{observed_max_restart_count}"
            ),
        )
    return covered_fail_reports, restart_limit_exceeded


def _check_verdict_series(
    label: str,
    payloads: Sequence[tuple[Path, Mapping[str, Any]]],
    add_finding: Any,
    *,
    covered_fail_reports: set[str] | None = None,
) -> list[datetime]:
    timestamps: list[datetime] = []
    worst: str = "PASS"
    covered_fail_reports = covered_fail_reports or set()
    for path, payload in payloads:
        try:
            ts = _parse_ts(payload.get("evaluated_at_utc", ""), "evaluated_at_utc")
            timestamps.append(ts)
        except OpsValidationError as exc:
            add_finding(
                f"{path.name} evaluated_at_utc",
                "fail",
                str(exc),
                artifact=path.name,
                field_name="evaluated_at_utc",
            )
        verdict = payload.get("verdict", {})
        verdict_value = verdict.get("verdict") if isinstance(verdict, dict) else None
        if verdict_value == "FAIL":
            if path.name in covered_fail_reports:
                if worst != "FAIL":
                    worst = "WARN"
                add_finding(
                    f"{path.name} {label} verdict",
                    "warn",
                    f"{label} report is FAIL but covered by an audited recovery event",
                    artifact=path.name,
                    field_name="verdict.verdict",
                )
            else:
                worst = "FAIL"
                add_finding(
                    f"{path.name} {label} verdict",
                    "fail",
                    f"{label} report is FAIL",
                    artifact=path.name,
                    field_name="verdict.verdict",
                )
        elif verdict_value == "WARN":
            if worst != "FAIL":
                worst = "WARN"
            add_finding(
                f"{path.name} {label} verdict",
                "warn",
                f"{label} report is WARN",
                artifact=path.name,
                field_name="verdict.verdict",
            )
        elif verdict_value == "PASS":
            add_finding(
                f"{path.name} {label} verdict",
                "pass",
                f"{label} report is PASS",
                artifact=path.name,
                field_name="verdict.verdict",
            )
        else:
            worst = "FAIL"
            add_finding(
                f"{path.name} {label} verdict",
                "fail",
                f"Unexpected {label} verdict {verdict_value!r}",
                artifact=path.name,
                field_name="verdict.verdict",
            )
    if payloads:
        if worst == "PASS":
            add_finding(
                f"{label} verdict history",
                "pass",
                f"All {label.lower()} reports are PASS",
            )
        elif worst == "WARN":
            add_finding(
                f"{label} verdict history",
                "warn",
                f"At least one {label.lower()} report is WARN, none are FAIL",
            )
        else:
            add_finding(
                f"{label} verdict history",
                "fail",
                f"At least one {label.lower()} report is FAIL",
            )
    return timestamps


def _check_runner_state(
    heartbeat_payload: Mapping[str, Any] | None,
    state_payload: Mapping[str, Any] | None,
    latest_snapshot_ts: datetime | None,
    *,
    expected_min_cycles: int,
    cadence_seconds: int,
    add_finding: Any,
) -> None:
    if heartbeat_payload is None or state_payload is None:
        return
    iteration = heartbeat_payload.get("iteration")
    if not isinstance(iteration, int) or iteration < expected_min_cycles:
        add_finding(
            "Runner heartbeat iteration count",
            "fail",
            f"Expected iteration >= {expected_min_cycles}, got {iteration!r}",
            artifact="runner_heartbeat.json",
            field_name="iteration",
        )
    else:
        add_finding(
            "Runner heartbeat iteration count",
            "pass",
            f"iteration={iteration} covers the expected minimum cycles",
            artifact="runner_heartbeat.json",
            field_name="iteration",
        )
    total_runs = state_payload.get("total_runs")
    successful_runs = state_payload.get("successful_runs")
    failed_runs = state_payload.get("failed_runs")
    if not isinstance(total_runs, int) or total_runs < expected_min_cycles:
        add_finding(
            "Runner total runs",
            "fail",
            f"Expected total_runs >= {expected_min_cycles}, got {total_runs!r}",
            artifact="runner_state.json",
            field_name="total_runs",
        )
    else:
        add_finding(
            "Runner total runs",
            "pass",
            f"total_runs={total_runs} covers the expected minimum cycles",
            artifact="runner_state.json",
            field_name="total_runs",
        )
    if not isinstance(successful_runs, int) or successful_runs < expected_min_cycles:
        add_finding(
            "Runner successful runs",
            "fail",
            (
                f"Expected successful_runs >= {expected_min_cycles}, got "
                f"{successful_runs!r}"
            ),
            artifact="runner_state.json",
            field_name="successful_runs",
        )
    else:
        add_finding(
            "Runner successful runs",
            "pass",
            f"successful_runs={successful_runs} covers the expected minimum cycles",
            artifact="runner_state.json",
            field_name="successful_runs",
        )
    if failed_runs != 0:
        add_finding(
            "Runner failed runs",
            "fail",
            f"Expected failed_runs=0, got {failed_runs!r}",
            artifact="runner_state.json",
            field_name="failed_runs",
        )
    else:
        add_finding(
            "Runner failed runs",
            "pass",
            "failed_runs=0",
            artifact="runner_state.json",
            field_name="failed_runs",
        )
    last_cycle_verdict = state_payload.get("last_cycle_verdict")
    if last_cycle_verdict != "PASS":
        add_finding(
            "Runner last cycle verdict",
            "fail",
            f"Expected last_cycle_verdict='PASS', got {last_cycle_verdict!r}",
            artifact="runner_state.json",
            field_name="last_cycle_verdict",
        )
    else:
        add_finding(
            "Runner last cycle verdict",
            "pass",
            "last_cycle_verdict is PASS",
            artifact="runner_state.json",
            field_name="last_cycle_verdict",
        )
    if latest_snapshot_ts is not None:
        try:
            last_cycle_ended = _parse_ts(
                state_payload.get("last_cycle_ended_at_utc", ""),
                "last_cycle_ended_at_utc",
            )
            delta_seconds = abs((last_cycle_ended - latest_snapshot_ts).total_seconds())
            if delta_seconds > cadence_seconds:
                add_finding(
                    "Runner state aligns with latest snapshot",
                    "warn",
                    (
                        f"last_cycle_ended_at_utc differs from the latest snapshot by "
                        f"{delta_seconds:.0f}s"
                    ),
                    artifact="runner_state.json",
                    field_name="last_cycle_ended_at_utc",
                )
            else:
                add_finding(
                    "Runner state aligns with latest snapshot",
                    "pass",
                    "last_cycle_ended_at_utc aligns with the latest snapshot",
                    artifact="runner_state.json",
                    field_name="last_cycle_ended_at_utc",
                )
        except OpsValidationError as exc:
            add_finding(
                "Runner state last_cycle_ended_at_utc",
                "fail",
                str(exc),
                artifact="runner_state.json",
                field_name="last_cycle_ended_at_utc",
            )


def _check_count_floor(
    label: str,
    count: int,
    expected_min_cycles: int,
    add_finding: Any,
) -> None:
    if count < expected_min_cycles:
        add_finding(
            f"{label} count floor",
            "fail",
            f"Expected at least {expected_min_cycles} {label.lower()} artifacts, got {count}",
        )
    else:
        add_finding(
            f"{label} count floor",
            "pass",
            f"Observed {count} {label.lower()} artifacts, meets minimum {expected_min_cycles}",
        )


def _check_cadence_series(
    label: str,
    timestamps: Sequence[datetime],
    cadence_seconds: int,
    add_finding: Any,
) -> None:
    if len(timestamps) < 2:
        add_finding(
            f"{label} cadence continuity",
            "fail",
            f"Need at least 2 {label.lower()} timestamps to verify cadence continuity",
        )
        return
    warn_gap = cadence_seconds + DEFAULT_WARN_GRACE_SECONDS
    fail_gap = int(cadence_seconds * DEFAULT_FAIL_MULTIPLIER)
    sorted_ts = sorted(timestamps)
    worst = "pass"
    worst_message = "All gaps are within cadence target"
    for left, right in zip(sorted_ts, sorted_ts[1:]):
        gap = (right - left).total_seconds()
        if gap > fail_gap:
            worst = "fail"
            worst_message = f"Gap of {gap:.0f}s exceeds fail threshold {fail_gap}s for {label.lower()} cadence"
            break
        if gap > warn_gap and worst != "fail":
            worst = "warn"
            worst_message = f"Gap of {gap:.0f}s exceeds warn threshold {warn_gap}s for {label.lower()} cadence"
    add_finding(
        f"{label} cadence continuity",
        worst,
        worst_message,
    )


def _check_window_coverage(
    snapshot_timestamps: Sequence[datetime],
    required_window_hours: int,
    add_finding: Any,
) -> tuple[datetime | None, datetime | None, float]:
    if not snapshot_timestamps:
        add_finding(
            "Snapshot window coverage",
            "fail",
            "No valid snapshot timestamps available for window coverage",
        )
        return None, None, 0.0
    ordered = sorted(snapshot_timestamps)
    observed_start = ordered[0]
    observed_end = ordered[-1]
    observed_window_hours = max(
        0.0, (observed_end - observed_start).total_seconds() / 3600.0
    )
    if observed_window_hours < required_window_hours:
        add_finding(
            "Snapshot window coverage",
            "fail",
            (
                f"Observed snapshot window {observed_window_hours:.2f}h is shorter than "
                f"required {required_window_hours}h"
            ),
        )
    else:
        add_finding(
            "Snapshot window coverage",
            "pass",
            (
                f"Observed snapshot window {observed_window_hours:.2f}h covers the "
                f"required {required_window_hours}h"
            ),
        )
    return observed_start, observed_end, observed_window_hours


def _check_no_side_effects(
    path: Path,
    payload: Mapping[str, Any],
    add_finding: Any,
) -> None:
    scan_payload = {key: value for key, value in payload.items() if key != "safety"}
    text = json.dumps(scan_payload, sort_keys=True, ensure_ascii=True)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in text:
            add_finding(
                f"{path.name} forbidden side-effect content",
                "fail",
                f"Found forbidden pattern {pattern!r} outside the safety section",
                artifact=path.name,
            )


def _load_coordinator_events(
    paths: Sequence[Path],
    add_finding: Any,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            add_finding(
                f"{path.name} readable",
                "fail",
                f"Failed to read {path.name}: {exc}",
                artifact=path.name,
            )
            continue
        if not lines:
            continue
        for index, line in enumerate(lines, start=1):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                add_finding(
                    f"{path.name} line {index} parses as JSON",
                    "fail",
                    f"Malformed JSON line: {exc}",
                    artifact=path.name,
                )
                continue
            if not isinstance(payload, dict):
                add_finding(
                    f"{path.name} line {index} event shape",
                    "fail",
                    "Lifecycle event line must be a JSON object",
                    artifact=path.name,
                )
                continue
            events.append(payload)
            add_finding(
                f"{path.name} line {index} parses as JSON",
                "pass",
                "Lifecycle event line is valid JSON",
                artifact=path.name,
            )
    return events


def _check_coordinator_events(
    events: Sequence[Mapping[str, Any]],
    add_finding: Any,
    *,
    is_final: bool = True,
) -> None:
    if not events:
        severity = "fail" if is_final else "warn"
        add_finding(
            "Coordinator lifecycle telemetry",
            severity,
            "Missing parseable coordinator lifecycle telemetry",
            artifact="coordinator_events.jsonl",
        )
        return

    required_event_types = {
        "run_started",
        "boot_readiness_completed",
        "cycle_started",
        "runner_cycle_completed",
        "watchdog_completed",
        "write_audit_completed",
        "cycle_completed",
        "final_validation_started",
        "final_validation_completed",
    }
    seen_types: set[str] = set()
    previous_ts: datetime | None = None
    chronological = True

    for index, event in enumerate(events, start=1):
        for field_name in ("schema_version", "event_at_utc", "run_id", "event_type"):
            value = event.get(field_name)
            if not isinstance(value, str) or not value.strip():
                add_finding(
                    f"Coordinator event {index} required field {field_name}",
                    "fail",
                    f"Lifecycle event missing required field {field_name}",
                    artifact="coordinator_events.jsonl",
                    field_name=field_name,
                )
        if event.get("schema_version") != "cdb.evidence_harvester.coordinator_event.v1":
            add_finding(
                f"Coordinator event {index} schema version",
                "fail",
                f"Unexpected schema_version {event.get('schema_version')!r}",
                artifact="coordinator_events.jsonl",
                field_name="schema_version",
            )
        event_type = str(event.get("event_type", "")).strip()
        if event_type:
            seen_types.add(event_type)
        try:
            event_ts = _parse_ts(event.get("event_at_utc", ""), "event_at_utc")
            if previous_ts is not None and event_ts < previous_ts:
                chronological = False
            previous_ts = event_ts
        except OpsValidationError as exc:
            chronological = False
            add_finding(
                f"Coordinator event {index} timestamp",
                "fail",
                str(exc),
                artifact="coordinator_events.jsonl",
                field_name="event_at_utc",
            )

    missing_types = sorted(required_event_types - seen_types)
    if missing_types:
        ev_severity = "fail" if is_final else "warn"
        add_finding(
            "Coordinator lifecycle required event coverage",
            ev_severity,
            f"Missing required lifecycle event types: {missing_types}",
            artifact="coordinator_events.jsonl",
        )
    else:
        add_finding(
            "Coordinator lifecycle required event coverage",
            "pass",
            "Required lifecycle event types are present",
            artifact="coordinator_events.jsonl",
        )

    add_finding(
        "Coordinator lifecycle chronology",
        "pass" if chronological else "fail",
        (
            "Lifecycle events are chronological"
            if chronological
            else "Lifecycle events are not chronological"
        ),
        artifact="coordinator_events.jsonl",
    )


def _check_sleep_lifecycle_completeness(
    events: Sequence[Mapping[str, Any]],
    state_payload: Mapping[str, Any] | None,
    add_finding: Any,
    *,
    is_final: bool = True,
) -> None:
    if not is_final:
        return
    if not events:
        return
    last_event = events[-1]
    if last_event.get("event_type") != "sleep_started":
        return
    coordinator_status = ""
    if state_payload is not None:
        coordinator_status = str(state_payload.get("coordinator_status", "") or "")
    add_finding(
        "Coordinator sleep lifecycle completeness",
        "warn",
        f"The coordinator event stream ends with sleep_started "
        f"and no matching sleep_completed or sleep_overshoot. "
        f"Coordinator status: {coordinator_status!r}. "
        f"The run may have been interrupted during sleep.",
        artifact="coordinator_events.jsonl",
    )


def _check_lifecycle_runner_state_consistency(
    coordinator_events: Sequence[Mapping[str, Any]],
    state_payload: Mapping[str, Any] | None,
    snapshot_count: int,
    add_finding: Any,
) -> None:
    if not coordinator_events or state_payload is None:
        return
    lifecycle_cycle_count = sum(
        1 for e in coordinator_events if e.get("event_type") == "cycle_completed"
    )
    state_cycle_count = state_payload.get("total_cycles_completed", 0)
    if not isinstance(state_cycle_count, int):
        add_finding(
            "Lifecycle-runner state cycle consistency",
            "fail",
            f"runner_state.total_cycles_completed is not an integer: {state_cycle_count!r}",
            artifact="runner_state.json",
            field_name="total_cycles_completed",
        )
        return
    diff = lifecycle_cycle_count - state_cycle_count
    if abs(diff) > 1:
        add_finding(
            "Lifecycle-runner state cycle consistency",
            "fail",
            f"Lifecycle cycle_completed count ({lifecycle_cycle_count}) diverges from runner_state.total_cycles_completed ({state_cycle_count}) by {abs(diff)}",
            artifact="coordinator_events.jsonl",
        )
    elif abs(diff) == 1:
        add_finding(
            "Lifecycle-runner state cycle consistency",
            "warn",
            f"Lifecycle cycle_completed count ({lifecycle_cycle_count}) differs from runner_state.total_cycles_completed ({state_cycle_count}) by 1",
            artifact="coordinator_events.jsonl",
        )
    else:
        add_finding(
            "Lifecycle-runner state cycle consistency",
            "pass",
            f"Lifecycle cycle_completed count ({lifecycle_cycle_count}) matches runner_state.total_cycles_completed ({state_cycle_count})",
            artifact="coordinator_events.jsonl",
        )
    if lifecycle_cycle_count != snapshot_count:
        add_finding(
            "Lifecycle-artifact count consistency",
            "warn",
            f"Lifecycle cycle_completed count ({lifecycle_cycle_count}) != snapshot artifact count ({snapshot_count})",
            artifact="coordinator_events.jsonl",
        )
    else:
        add_finding(
            "Lifecycle-artifact count consistency",
            "pass",
            f"Lifecycle cycle_completed count ({lifecycle_cycle_count}) matches snapshot artifact count ({snapshot_count})",
            artifact="coordinator_events.jsonl",
        )


def _check_watchdog_coordinator_liveness(
    watchdog_payloads: Sequence[tuple[Path, Mapping[str, Any]]],
    add_finding: Any,
) -> None:
    if not watchdog_payloads:
        return
    for path, payload in watchdog_payloads:
        cl = payload.get("coordinator_liveness")
        if not isinstance(cl, Mapping):
            continue
        classification = str(cl.get("classification", "")).strip()
        severity = str(cl.get("severity", "")).strip()
        reason = str(cl.get("reason", "")).strip()
        msg = f"Watchdog coordinator liveness: {classification} — {reason}"
        if classification == "FATAL_STOP":
            add_finding(
                "Watchdog coordinator liveness", "fail", msg, artifact=path.name
            )
        elif classification == "STALE_NEXT_CYCLE":
            add_finding(
                "Watchdog coordinator liveness", "fail", msg, artifact=path.name
            )
        elif classification == "STALE_HEARTBEAT" and severity == "fail":
            add_finding(
                "Watchdog coordinator liveness", "fail", msg, artifact=path.name
            )
        elif classification in ("RECOVERY_IN_PROGRESS", "COORDINATOR_STOPPED"):
            add_finding(
                "Watchdog coordinator liveness", "warn", msg, artifact=path.name
            )
        else:
            add_finding(
                "Watchdog coordinator liveness", "pass", msg, artifact=path.name
            )


def validate_72h_window(
    artifact_paths: Mapping[str, Sequence[Path]],
    *,
    artifact_dir: Path,
    window_start_utc: datetime | None = None,
    window_end_utc: datetime | None = None,
    required_window_hours: int = DEFAULT_REQUIRED_WINDOW_HOURS,
    runner_cadence_seconds: int = DEFAULT_RUNNER_CADENCE_SECONDS,
    is_final: bool = True,
) -> OpsValidationReport:
    if required_window_hours < 1:
        raise OpsValidationError("required_window_hours must be >= 1")
    if runner_cadence_seconds < 1:
        raise OpsValidationError("runner_cadence_seconds must be >= 1")
    if window_start_utc and window_end_utc and window_end_utc <= window_start_utc:
        raise OpsValidationError("window_end_utc must be after window_start_utc")

    findings: list[OpsValidationFinding] = []
    counter = 0

    def add_finding(
        check_name: str,
        severity: str,
        message: str,
        *,
        artifact: str = "",
        field_name: str = "",
    ) -> None:
        nonlocal counter
        counter += 1
        findings.append(
            OpsValidationFinding(
                check_id=f"O{counter:03d}",
                check_name=check_name,
                severity=severity,
                message=message,
                artifact=artifact,
                field_name=field_name,
            )
        )

    _check_required_artifacts(artifact_paths, add_finding)
    _check_matching_counts(
        "Snapshot",
        artifact_paths.get("snapshots_json", []),
        artifact_paths.get("snapshots_md", []),
        add_finding,
    )
    _check_matching_counts(
        "Alert",
        artifact_paths.get("alerts_json", []),
        artifact_paths.get("alerts_md", []),
        add_finding,
    )
    _check_matching_counts(
        "Watchdog",
        artifact_paths.get("watchdog_json", []),
        artifact_paths.get("watchdog_md", []),
        add_finding,
    )
    _check_matching_counts(
        "Write-audit",
        artifact_paths.get("write_audit_json", []),
        artifact_paths.get("write_audit_md", []),
        add_finding,
    )
    _check_matching_counts(
        "Boot readiness",
        artifact_paths.get("boot_json", []),
        artifact_paths.get("boot_md", []),
        add_finding,
    )
    if artifact_paths.get("recovery_events_json") or artifact_paths.get(
        "recovery_events_md"
    ):
        _check_matching_counts(
            "Recovery event",
            artifact_paths.get("recovery_events_json", []),
            artifact_paths.get("recovery_events_md", []),
            add_finding,
        )

    collector_payloads = _load_payloads(
        artifact_paths.get("collector_reports", []),
        add_finding,
        expected_schema=COLLECTOR_REPORT_SCHEMA,
    )
    snapshot_payloads = _load_payloads(
        artifact_paths.get("snapshots_json", []),
        add_finding,
        expected_schema=SNAPSHOT_SCHEMA_VERSION,
        schema_field="metadata.schema_version",
    )
    alert_payloads = _load_payloads(
        artifact_paths.get("alerts_json", []),
        add_finding,
        expected_schema=ALERT_REPORT_SCHEMA_VERSION,
    )
    heartbeat_payloads = _load_payloads(
        artifact_paths.get("heartbeat", []),
        add_finding,
        expected_schema=HEARTBEAT_SCHEMA,
    )
    coordinator_events = _load_coordinator_events(
        artifact_paths.get("coordinator_events", []),
        add_finding,
    )
    state_payloads = _load_payloads(
        artifact_paths.get("state", []),
        add_finding,
        expected_schema=STATE_SCHEMA,
    )
    state_payload = state_payloads[0][1] if state_payloads else None
    heartbeat_payload = heartbeat_payloads[0][1] if heartbeat_payloads else None
    watchdog_payloads = _load_payloads(
        artifact_paths.get("watchdog_json", []),
        add_finding,
        expected_schema=WATCHDOG_REPORT_SCHEMA,
    )
    write_audit_payloads = _load_payloads(
        artifact_paths.get("write_audit_json", []),
        add_finding,
        expected_schema=WRITE_AUDIT_REPORT_SCHEMA,
    )
    boot_payloads = _load_payloads(
        artifact_paths.get("boot_json", []),
        add_finding,
        expected_schema=BOOT_READINESS_SCHEMA,
    )
    recovery_event_payloads = _load_payloads(
        artifact_paths.get("recovery_events_json", []),
        add_finding,
        expected_schema=RECOVERY_EVENT_SCHEMA,
    )

    for path, payload in collector_payloads:
        _check_no_side_effects(path, payload, add_finding)

    snapshot_timestamps: list[datetime] = []
    for path, payload in snapshot_payloads:
        _check_no_side_effects(path, payload, add_finding)
        ts = _check_snapshot_payload(path, payload, add_finding)
        if ts is not None:
            snapshot_timestamps.append(ts)

    alert_timestamps: list[datetime] = []
    for path, payload in alert_payloads:
        _check_no_side_effects(path, payload, add_finding)
        ts = _check_alert_payload(path, payload, add_finding)
        if ts is not None:
            alert_timestamps.append(ts)

    for path, payload in heartbeat_payloads:
        _check_no_side_effects(path, payload, add_finding)
        try:
            _parse_ts(payload.get("current_run_at_utc", ""), "current_run_at_utc")
            add_finding(
                f"{path.name} current_run_at_utc",
                "pass",
                "current_run_at_utc is valid",
                artifact=path.name,
                field_name="current_run_at_utc",
            )
        except OpsValidationError as exc:
            add_finding(
                f"{path.name} current_run_at_utc",
                "fail",
                str(exc),
                artifact=path.name,
                field_name="current_run_at_utc",
            )

    for path, payload in state_payloads:
        _check_no_side_effects(path, payload, add_finding)

    _check_coordinator_events(coordinator_events, add_finding, is_final=is_final)

    _check_sleep_lifecycle_completeness(
        coordinator_events, state_payload, add_finding, is_final=is_final
    )

    _check_lifecycle_runner_state_consistency(
        coordinator_events,
        state_payload,
        len(snapshot_payloads),
        add_finding,
    )

    recovered_fail_reports, recovery_limit_exceeded = _check_recovery_events(
        recovery_event_payloads,
        add_finding,
    )

    watchdog_timestamps = _check_verdict_series(
        "Watchdog",
        watchdog_payloads,
        add_finding,
        covered_fail_reports=recovered_fail_reports,
    )
    _check_watchdog_coordinator_liveness(watchdog_payloads, add_finding)
    for path, payload in watchdog_payloads:
        _check_no_side_effects(path, payload, add_finding)

    write_audit_timestamps = _check_verdict_series(
        "Write-audit",
        write_audit_payloads,
        add_finding,
        covered_fail_reports=recovered_fail_reports,
    )
    for path, payload in write_audit_payloads:
        _check_no_side_effects(path, payload, add_finding)

    boot_timestamps: list[datetime] = []
    for path, payload in boot_payloads:
        _check_no_side_effects(path, payload, add_finding)
        ts = _check_boot_payload(path, payload, add_finding)
        if ts is not None:
            boot_timestamps.append(ts)

    expected_cycles = _expected_min_cycles(
        required_window_hours, runner_cadence_seconds
    )
    _check_count_floor(
        "Collector report", len(collector_payloads), expected_cycles, add_finding
    )
    _check_count_floor("Snapshot", len(snapshot_payloads), expected_cycles, add_finding)
    _check_count_floor("Alert", len(alert_payloads), expected_cycles, add_finding)
    _check_count_floor("Watchdog", len(watchdog_payloads), expected_cycles, add_finding)
    _check_count_floor(
        "Write-audit", len(write_audit_payloads), expected_cycles, add_finding
    )
    if recovery_limit_exceeded:
        add_finding(
            "Recovery restart ceiling",
            "fail",
            "Recovery restart ceiling was exceeded during the run",
        )

    observed_start, observed_end, observed_hours = _check_window_coverage(
        snapshot_timestamps, required_window_hours, add_finding
    )
    if snapshot_timestamps:
        _check_cadence_series(
            "Snapshot", snapshot_timestamps, runner_cadence_seconds, add_finding
        )
    if alert_timestamps:
        _check_cadence_series(
            "Alert", alert_timestamps, runner_cadence_seconds, add_finding
        )
    if watchdog_timestamps:
        _check_cadence_series(
            "Watchdog", watchdog_timestamps, runner_cadence_seconds, add_finding
        )
    if write_audit_timestamps:
        _check_cadence_series(
            "Write-audit",
            write_audit_timestamps,
            runner_cadence_seconds,
            add_finding,
        )

    latest_snapshot_ts = max(snapshot_timestamps) if snapshot_timestamps else None
    _check_runner_state(
        heartbeat_payload,
        state_payload,
        latest_snapshot_ts,
        expected_min_cycles=expected_cycles,
        cadence_seconds=runner_cadence_seconds,
        add_finding=add_finding,
    )

    report_start = window_start_utc or observed_start or _now_utc()
    report_end = window_end_utc or observed_end or report_start
    observed_counts = {key: len(list(paths)) for key, paths in artifact_paths.items()}
    fail_count = sum(1 for finding in findings if finding.severity == "fail")
    warn_count = sum(1 for finding in findings if finding.severity == "warn")
    pass_count = sum(1 for finding in findings if finding.severity == "pass")
    if fail_count:
        verdict = "FAIL"
    elif warn_count:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return OpsValidationReport(
        schema_version=OPS_VALIDATION_SCHEMA_VERSION,
        validated_at_utc=_format_ts(_now_utc()),
        artifact_dir=str(artifact_dir),
        window_start_utc=_format_ts(report_start),
        window_end_utc=_format_ts(report_end),
        observed_window_hours=round(observed_hours, 3),
        required_window_hours=required_window_hours,
        cadence_seconds=runner_cadence_seconds,
        expected_min_cycles=expected_cycles,
        observed_counts=observed_counts,
        findings=tuple(
            sorted(
                findings,
                key=lambda item: (
                    {"fail": 0, "warn": 1, "pass": 2}.get(item.severity, 9),
                    item.check_id,
                ),
            )
        ),
        summary=OpsValidationSummary(
            verdict=verdict,
            total_checks=len(findings),
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
        ),
        runtime_handoff=_build_runtime_handoff(
            required_window_hours=required_window_hours,
            cadence_seconds=runner_cadence_seconds,
        ),
    )


def validate_72h_window_from_dir(
    artifact_dir: Path,
    *,
    window_start_utc: datetime | None = None,
    window_end_utc: datetime | None = None,
    required_window_hours: int = DEFAULT_REQUIRED_WINDOW_HOURS,
    runner_cadence_seconds: int = DEFAULT_RUNNER_CADENCE_SECONDS,
    is_final: bool = True,
) -> OpsValidationReport:
    if not artifact_dir.exists():
        raise OpsValidationError(f"Artifact directory does not exist: {artifact_dir}")
    if not artifact_dir.is_dir():
        raise OpsValidationError(f"Path is not a directory: {artifact_dir}")
    return validate_72h_window(
        _collect_artifact_paths(artifact_dir),
        artifact_dir=artifact_dir,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        required_window_hours=required_window_hours,
        runner_cadence_seconds=runner_cadence_seconds,
        is_final=is_final,
    )


def _render_finding(finding: OpsValidationFinding) -> str:
    artifact_part = f" [{finding.artifact}]" if finding.artifact else ""
    field_part = f" ({finding.field_name})" if finding.field_name else ""
    return (
        f"- [{finding.severity.upper()}] {finding.check_name}{artifact_part}"
        f"{field_part}: {finding.message}"
    )


def report_to_markdown(report: OpsValidationReport) -> str:
    payload = report.to_dict()
    handoff = payload["runtime_handoff"]
    lines = [
        "# 72h Ops Validation Report",
        "",
        "## Metadata",
        f"- Schema version: {payload['schema_version']}",
        f"- Validated at (UTC): {payload['validated_at_utc']}",
        f"- Artifact directory: `{payload['artifact_dir']}`",
        f"- Window start (UTC): {payload['window_start_utc']}",
        f"- Window end (UTC): {payload['window_end_utc']}",
        f"- Observed window hours: {payload['observed_window_hours']}",
        f"- Required window hours: {payload['required_window_hours']}",
        f"- Cadence seconds: {payload['cadence_seconds']}",
        f"- Expected minimum cycles: {payload['expected_min_cycles']}",
        "",
        "## Summary",
        f"- Verdict: **{payload['summary']['verdict']}**",
        f"- Total checks: {payload['summary']['total_checks']}",
        f"- Pass: {payload['summary']['pass_count']}",
        f"- Warn: {payload['summary']['warn_count']}",
        f"- Fail: {payload['summary']['fail_count']}",
        "",
        "## Observed Counts",
    ]
    for key, value in sorted(payload["observed_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Findings",
        ]
    )
    for item in payload["findings"]:
        lines.append(_render_finding(OpsValidationFinding(**item)))
    lines.extend(
        [
            "",
            "## 72h Validation Contract",
            "- PASS requires >=72h coverage, continuous runner evidence cadence, lifecycle telemetry, no FAIL in watchdog/write-audit/boot, consistent cycle counts, and no side effects.",
            "- WARN allows minor cadence drift, a justified boot/watchdog warning with no FAIL findings, or missing lifecycle telemetry in non-final validation.",
            "- FAIL means the always-on dry operation is not proven fail-closed.",
            "",
            "## Runtime Handoff",
            f"- Artifact dir template: `{handoff['artifact_dir_template']}`",
            f"- Seed fixture: `{handoff['seed_fixture']}`",
            f"- Runner cadence seconds: {handoff['runner_cadence_seconds']}",
            f"- Required window hours: {handoff['required_window_hours']}",
            f"- Expected minimum cycles: {handoff['expected_min_cycles']}",
            "- Watchdog after each runner cycle: yes",
            "- Write-audit after each runner cycle: yes",
            "",
            "### Required Artifacts",
        ]
    )
    for item in handoff["required_artifacts"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Boot Preflight Commands"])
    for item in handoff["boot_preflight_commands"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Enable Commands"])
    for item in handoff["enable_commands"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Start Commands"])
    for item in handoff["start_commands"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Stop Commands"])
    for item in handoff["stop_commands"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Side-Effect Checklist"])
    for item in handoff["side_effect_checklist"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "### Operator Approval Checkpoint",
            f"- {handoff['operator_approval_checkpoint']}",
            "",
            "### Safety Statement",
            f"- {handoff['safety_statement']}",
        ]
    )
    if handoff["notes"]:
        lines.append("")
        lines.append("### Notes")
        for item in handoff["notes"]:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Safety Boundaries",
            "- No actual 72h run is started by this module.",
            "- No Windows Task install, no Docker/runtime/DB/secrets mutation.",
            "- No GitHub writes from module code.",
            "- No LR-Go, no Live-Go, no Echtgeld-Go.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> Any:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate the final >=72h evidence harvester always-on dry run."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    dir_parser = subparsers.add_parser(
        "validate-dir",
        help="Validate a directory containing >=72h evidence harvester artifacts.",
    )
    dir_parser.add_argument(
        "--artifact-dir",
        type=Path,
        required=True,
        help="Directory containing the 72h ops validation artifacts.",
    )
    dir_parser.add_argument(
        "--window-start-utc",
        help="Optional explicit window start for reporting.",
    )
    dir_parser.add_argument(
        "--window-end-utc",
        help="Optional explicit window end for reporting.",
    )
    dir_parser.add_argument(
        "--required-window-hours",
        type=int,
        default=DEFAULT_REQUIRED_WINDOW_HOURS,
        help="Required coverage window in hours (default: 72).",
    )
    dir_parser.add_argument(
        "--runner-cadence-seconds",
        type=int,
        default=DEFAULT_RUNNER_CADENCE_SECONDS,
        help="Expected runner cadence in seconds (default: 900).",
    )
    dir_parser.add_argument(
        "--is-final",
        action="store_true",
        default=True,
        dest="is_final",
        help="Treat this as final >=72h validation (default: True).",
    )
    dir_parser.add_argument(
        "--no-final",
        action="store_false",
        dest="is_final",
        help="Treat this as non-final bounded validation.",
    )
    dir_parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional JSON output path for the ops validation report.",
    )
    dir_parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional Markdown output path for the ops validation report.",
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
    report = validate_72h_window_from_dir(
        args.artifact_dir,
        window_start_utc=window_start,
        window_end_utc=window_end,
        required_window_hours=args.required_window_hours,
        runner_cadence_seconds=args.runner_cadence_seconds,
        is_final=args.is_final,
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
            json_text + ("" if json_text.endswith("\n") else "\n"),
            encoding="utf-8",
        )
    if args.markdown_output:
        args.markdown_output.write_text(report_to_markdown(report), encoding="utf-8")
    if args.json_output or args.markdown_output:
        print(report_to_markdown(report))
    else:
        print(json_text)
    return 0 if report.summary.verdict != "FAIL" else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
