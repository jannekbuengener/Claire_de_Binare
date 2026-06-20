from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .alerts import ALERT_REPORT_SCHEMA_VERSION
from .coordinator import COORDINATOR_EVENT_SCHEMA
from .runner import HEARTBEAT_SCHEMA, STATE_SCHEMA
from .snapshot import SNAPSHOT_SCHEMA_VERSION

HEARTBEAT_SCHEMA_EXPECTED = HEARTBEAT_SCHEMA
STATE_SCHEMA_EXPECTED = STATE_SCHEMA
SNAPSHOT_SCHEMA_EXPECTED = SNAPSHOT_SCHEMA_VERSION
ALERT_SCHEMA_EXPECTED = ALERT_REPORT_SCHEMA_VERSION

WATCHDOG_REPORT_SCHEMA = "cdb.evidence_harvester.watchdog_report.v1"
DEFAULT_MAX_AGE_SECONDS = 7200
DEFAULT_WARN_AGE_SECONDS = 5400
DEFAULT_CADENCE_SECONDS = 86400


class WatchdogError(ValueError):
    pass


def _parse_ts(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise WatchdogError(f"{field_name} must not be blank")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise WatchdogError(
                f"{field_name} must be an ISO-8601 UTC timestamp"
            ) from exc
    else:
        raise WatchdogError(f"{field_name} must be an ISO-8601 UTC timestamp")
    if parsed.tzinfo is None:
        raise WatchdogError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now_utc() -> datetime:
    now = cdb_utcnow()
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WatchdogError(f"{field_name} must be an object")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise WatchdogError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise WatchdogError(f"{field_name} must not be blank")
    return text


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise WatchdogError(f"Malformed JSON in {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WatchdogError(f"{path.name} JSON root must be an object")
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_artifact_dir() -> Path:
    return _repo_root() / "artifacts" / "evidence_harvester" / "runner"


def _resolve_artifact_dir(path: Path | None) -> Path:
    return (path or _default_artifact_dir()).resolve()


@dataclass(frozen=True, slots=True)
class WatchdogFinding:
    check_id: str
    check_name: str
    severity: str
    message: str
    artifact: str = ""
    field_name: str = ""


@dataclass(frozen=True, slots=True)
class WatchdogVerdict:
    verdict: str
    total_checks: int
    pass_count: int
    warn_count: int
    fail_count: int


@dataclass(frozen=True, slots=True)
class CoordinatorLiveness:
    classification: str
    severity: str
    reason: str
    coordinator_status_from_state: str
    has_lifecycle_telemetry: bool
    last_heartbeat_age_seconds: float = 0.0
    next_cycle_due_at_utc: str = ""
    has_fatal_stop_event: bool = False
    has_recovery_events: bool = False
    overdue_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


COORDINATOR_LIVENESS_CLASSIFICATIONS: tuple[str, ...] = (
    "RUNNING_HEALTHY",
    "SLEEPING_UNTIL_NEXT_CYCLE",
    "STALE_HEARTBEAT",
    "STALE_NEXT_CYCLE",
    "COORDINATOR_STOPPED",
    "COORDINATOR_UNKNOWN",
    "RECOVERY_IN_PROGRESS",
    "FATAL_STOP",
)


@dataclass(frozen=True, slots=True)
class WatchdogReport:
    schema_version: str
    evaluated_at_utc: str
    artifact_dir: str
    mode: str
    heartbeat_fresh: bool
    runner_state_ok: bool
    required_artifacts_present: bool
    coordinator_liveness: CoordinatorLiveness
    verdict: WatchdogVerdict
    findings: tuple[WatchdogFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_coordinator_events(artifact_dir: Path) -> list[dict[str, Any]]:
    path = artifact_dir / "coordinator_events.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _classify_coordinator_liveness(
    state_payload: dict[str, Any] | None,
    coordinator_events: list[dict[str, Any]],
    heartbeat_payload: dict[str, Any] | None,
    *,
    now: datetime,
    max_age_seconds: int,
    cadence_seconds: int,
) -> CoordinatorLiveness:
    coordinator_status = ""
    next_cycle_due_raw = ""
    if state_payload is not None:
        coordinator_status = str(state_payload.get("coordinator_status", "")).strip()
        next_cycle_due_raw = str(state_payload.get("next_cycle_due_at_utc", "")).strip()

    has_lifecycle = bool(coordinator_events)

    has_fatal_stop_event = any(
        event.get("event_type") == "fatal_stop" for event in coordinator_events
    )
    has_recovery_events = any(
        event.get("event_type") in ("recovery_started", "recovery_completed")
        for event in coordinator_events
    )

    heartbeat_age: float = -1.0
    if heartbeat_payload:
        current_run_raw = heartbeat_payload.get("current_run_at_utc", "")
        if current_run_raw:
            try:
                hb_ts = _parse_ts(current_run_raw, "current_run_at_utc")
                heartbeat_age = (now - hb_ts).total_seconds()
            except WatchdogError:
                pass

    has_fatal_stop = has_fatal_stop_event or coordinator_status == "fatal_stop"
    is_recovering = coordinator_status == "recovering"
    is_stopped = coordinator_status in ("completed", "failed")

    def _make(
        classification: str,
        severity: str,
        reason: str,
        **extra: Any,
    ) -> CoordinatorLiveness:
        return CoordinatorLiveness(
            classification=classification,
            severity=severity,
            reason=reason,
            coordinator_status_from_state=coordinator_status,
            has_lifecycle_telemetry=has_lifecycle,
            last_heartbeat_age_seconds=max(heartbeat_age, 0.0),
            next_cycle_due_at_utc=next_cycle_due_raw,
            has_fatal_stop_event=has_fatal_stop_event,
            has_recovery_events=has_recovery_events,
            overdue_seconds=extra.get("overdue_seconds", 0.0),
        )

    if has_fatal_stop:
        return _make(
            "FATAL_STOP",
            "fail",
            (
                "Coordinator has a fatal stop lifecycle event"
                if has_fatal_stop_event
                else "coordinator_status is fatal_stop"
            ),
        )

    if is_recovering:
        return _make(
            "RECOVERY_IN_PROGRESS",
            "warn",
            "Coordinator status indicates recovery in progress",
        )

    if is_stopped:
        return _make(
            "COORDINATOR_STOPPED",
            "warn" if coordinator_status == "completed" else "fail",
            f"Coordinator has stopped with status {coordinator_status!r}",
        )

    if coordinator_status == "sleeping":
        if not next_cycle_due_raw:
            return _make(
                "STALE_NEXT_CYCLE",
                "fail",
                "Coordinator is sleeping but next_cycle_due_at_utc is missing",
            )
        try:
            due_at = _parse_ts(next_cycle_due_raw, "next_cycle_due_at_utc")
            delta = (now - due_at).total_seconds()
            if delta <= 0:
                return _make(
                    "SLEEPING_UNTIL_NEXT_CYCLE",
                    "pass",
                    "Coordinator is sleeping and next cycle is not yet due",
                )
            if delta <= cadence_seconds:
                return _make(
                    "SLEEPING_UNTIL_NEXT_CYCLE",
                    "warn",
                    f"Sleeping but next_cycle_due_at_utc exceeded by "
                    f"{delta:.0f}s within cadence tolerance",
                    overdue_seconds=delta,
                )
            return _make(
                "STALE_NEXT_CYCLE",
                "fail",
                f"next_cycle_due_at_utc exceeded by {delta:.0f}s "
                f"beyond cadence tolerance {cadence_seconds}s",
                overdue_seconds=delta,
            )
        except WatchdogError:
            return _make(
                "STALE_NEXT_CYCLE",
                "fail",
                f"next_cycle_due_at_utc={next_cycle_due_raw!r} "
                "is not valid ISO-8601",
            )

    running_statuses = (
        "starting",
        "boot_checked",
        "running",
        "cycle_completed",
        "final_validation",
        "",
    )
    if coordinator_status in running_statuses or coordinator_status.startswith(
        "starting"
    ):
        if heartbeat_age >= 0 and heartbeat_age > max_age_seconds:
            return _make(
                "STALE_HEARTBEAT",
                "fail",
                f"Heartbeat is {heartbeat_age:.0f}s old "
                f"(max_age={max_age_seconds}s) while coordinator "
                f"status is {coordinator_status!r}",
                overdue_seconds=heartbeat_age,
            )
        if not coordinator_status and not has_lifecycle:
            return _make(
                "COORDINATOR_UNKNOWN",
                "warn",
                "No coordinator status or lifecycle telemetry available",
            )
        return _make(
            "RUNNING_HEALTHY",
            "pass",
            f"Coordinator status is {coordinator_status!r} " "and heartbeat is fresh",
        )

    return _make(
        "COORDINATOR_UNKNOWN",
        "warn",
        f"Unknown coordinator_status={coordinator_status!r}",
    )


def _check_heartbeat(
    heartbeat_payload: dict[str, Any] | None,
    artifact_dir_label: str,
    *,
    max_age_seconds: int,
    warn_age_seconds: int,
    now: datetime,
) -> list[WatchdogFinding]:
    findings: list[WatchdogFinding] = []
    if heartbeat_payload is None:
        findings.append(
            WatchdogFinding(
                check_id="W001",
                check_name="Heartbeat file exists",
                severity="fail",
                message="runner_heartbeat.json is missing or unreadable",
                artifact=artifact_dir_label,
            )
        )
        return findings

    if heartbeat_payload.get("schema_version") != HEARTBEAT_SCHEMA_EXPECTED:
        findings.append(
            WatchdogFinding(
                check_id="W002",
                check_name="Heartbeat schema version",
                severity="fail",
                message=(
                    f"Expected schema_version={HEARTBEAT_SCHEMA_EXPECTED!r}, "
                    f"got {heartbeat_payload.get('schema_version')!r}"
                ),
                artifact=artifact_dir_label,
                field_name="schema_version",
            )
        )

    current_run_raw = heartbeat_payload.get("current_run_at_utc", "")
    if current_run_raw:
        try:
            current_run_ts = _parse_ts(current_run_raw, "current_run_at_utc")
            age_seconds = (now - current_run_ts).total_seconds()
            if age_seconds > max_age_seconds:
                findings.append(
                    WatchdogFinding(
                        check_id="W003",
                        check_name="Heartbeat freshness",
                        severity="fail",
                        message=(
                            f"Heartbeat is {age_seconds:.0f}s old "
                            f"(max_age={max_age_seconds}s)"
                        ),
                        artifact=artifact_dir_label,
                        field_name="current_run_at_utc",
                    )
                )
            elif age_seconds > warn_age_seconds:
                findings.append(
                    WatchdogFinding(
                        check_id="W003",
                        check_name="Heartbeat freshness",
                        severity="warn",
                        message=(
                            f"Heartbeat is {age_seconds:.0f}s old "
                            f"(warn_age={warn_age_seconds}s)"
                        ),
                        artifact=artifact_dir_label,
                        field_name="current_run_at_utc",
                    )
                )
            else:
                findings.append(
                    WatchdogFinding(
                        check_id="W003",
                        check_name="Heartbeat freshness",
                        severity="pass",
                        message=f"Heartbeat is {age_seconds:.0f}s old (within limit)",
                        artifact=artifact_dir_label,
                        field_name="current_run_at_utc",
                    )
                )
        except WatchdogError:
            findings.append(
                WatchdogFinding(
                    check_id="W003",
                    check_name="Heartbeat freshness",
                    severity="fail",
                    message=(
                        f"current_run_at_utc={current_run_raw!r} is not valid ISO-8601"
                    ),
                    artifact=artifact_dir_label,
                    field_name="current_run_at_utc",
                )
            )
    else:
        findings.append(
            WatchdogFinding(
                check_id="W003",
                check_name="Heartbeat freshness",
                severity="fail",
                message="current_run_at_utc is missing or empty",
                artifact=artifact_dir_label,
                field_name="current_run_at_utc",
            )
        )

    return findings


def _check_runner_state(
    state_payload: dict[str, Any] | None,
    artifact_dir_label: str,
    *,
    max_age_seconds: int,
    warn_age_seconds: int,
    cadence_seconds: int,
    now: datetime,
) -> list[WatchdogFinding]:
    findings: list[WatchdogFinding] = []
    if state_payload is None:
        findings.append(
            WatchdogFinding(
                check_id="W004",
                check_name="Runner state file exists",
                severity="fail",
                message="runner_state.json is missing or unreadable",
                artifact=artifact_dir_label,
            )
        )
        return findings

    if state_payload.get("schema_version") != STATE_SCHEMA_EXPECTED:
        findings.append(
            WatchdogFinding(
                check_id="W005",
                check_name="State schema version",
                severity="fail",
                message=(
                    f"Expected schema_version={STATE_SCHEMA_EXPECTED!r}, "
                    f"got {state_payload.get('schema_version')!r}"
                ),
                artifact=artifact_dir_label,
                field_name="schema_version",
            )
        )

    last_verdict = state_payload.get("last_cycle_verdict", "")
    if last_verdict == "FAIL":
        findings.append(
            WatchdogFinding(
                check_id="W006",
                check_name="Runner last cycle verdict",
                severity="fail",
                message="Last cycle ended with FAIL verdict",
                artifact=artifact_dir_label,
                field_name="last_cycle_verdict",
            )
        )
    elif last_verdict == "PASS":
        findings.append(
            WatchdogFinding(
                check_id="W006",
                check_name="Runner last cycle verdict",
                severity="pass",
                message="Last cycle ended with PASS verdict",
                artifact=artifact_dir_label,
                field_name="last_cycle_verdict",
            )
        )
    else:
        findings.append(
            WatchdogFinding(
                check_id="W006",
                check_name="Runner last cycle verdict",
                severity="warn",
                message=f"Last cycle verdict is {last_verdict!r} (expected PASS or FAIL)",
                artifact=artifact_dir_label,
                field_name="last_cycle_verdict",
            )
        )

    failed_runs = state_payload.get("failed_runs", 0)
    if isinstance(failed_runs, int) and failed_runs > 0:
        total = state_payload.get("total_runs", 0)
        findings.append(
            WatchdogFinding(
                check_id="W007",
                check_name="Runner failure count",
                severity="warn",
                message=(
                    f"Runner has {failed_runs} failed run(s) out of {total} total"
                ),
                artifact=artifact_dir_label,
                field_name="failed_runs",
            )
        )
    else:
        findings.append(
            WatchdogFinding(
                check_id="W007",
                check_name="Runner failure count",
                severity="pass",
                message="No failed runs recorded",
                artifact=artifact_dir_label,
                field_name="failed_runs",
            )
        )

    last_cycle_raw = state_payload.get("last_cycle_ended_at_utc", "")
    if last_cycle_raw:
        try:
            last_cycle_ts = _parse_ts(last_cycle_raw, "last_cycle_ended_at_utc")
            age_seconds = (now - last_cycle_ts).total_seconds()
            if age_seconds > max_age_seconds:
                findings.append(
                    WatchdogFinding(
                        check_id="W016",
                        check_name="Runner state freshness",
                        severity="fail",
                        message=(
                            f"Runner state is {age_seconds:.0f}s old "
                            f"(max_age={max_age_seconds}s)"
                        ),
                        artifact=artifact_dir_label,
                        field_name="last_cycle_ended_at_utc",
                    )
                )
            elif age_seconds > warn_age_seconds:
                findings.append(
                    WatchdogFinding(
                        check_id="W016",
                        check_name="Runner state freshness",
                        severity="warn",
                        message=(
                            f"Runner state is {age_seconds:.0f}s old "
                            f"(warn_age={warn_age_seconds}s)"
                        ),
                        artifact=artifact_dir_label,
                        field_name="last_cycle_ended_at_utc",
                    )
                )
            else:
                findings.append(
                    WatchdogFinding(
                        check_id="W016",
                        check_name="Runner state freshness",
                        severity="pass",
                        message=(
                            f"Runner state is {age_seconds:.0f}s old (within limit)"
                        ),
                        artifact=artifact_dir_label,
                        field_name="last_cycle_ended_at_utc",
                    )
                )
        except WatchdogError:
            findings.append(
                WatchdogFinding(
                    check_id="W016",
                    check_name="Runner state freshness",
                    severity="fail",
                    message=(
                        f"last_cycle_ended_at_utc={last_cycle_raw!r} is not valid ISO-8601"
                    ),
                    artifact=artifact_dir_label,
                    field_name="last_cycle_ended_at_utc",
                )
            )
    else:
        findings.append(
            WatchdogFinding(
                check_id="W016",
                check_name="Runner state freshness",
                severity="fail",
                message="last_cycle_ended_at_utc is missing or empty",
                artifact=artifact_dir_label,
                field_name="last_cycle_ended_at_utc",
            )
        )

    coordinator_status = str(state_payload.get("coordinator_status", "")).strip()
    next_cycle_due_at_utc = str(state_payload.get("next_cycle_due_at_utc", "")).strip()
    if coordinator_status == "sleeping":
        if not next_cycle_due_at_utc:
            findings.append(
                WatchdogFinding(
                    check_id="W017",
                    check_name="Coordinator sleep schedule",
                    severity="fail",
                    message="coordinator_status is sleeping but next_cycle_due_at_utc is missing",
                    artifact=artifact_dir_label,
                    field_name="next_cycle_due_at_utc",
                )
            )
        else:
            try:
                due_at = _parse_ts(next_cycle_due_at_utc, "next_cycle_due_at_utc")
                delta_seconds = (now - due_at).total_seconds()
                if delta_seconds <= 0:
                    findings.append(
                        WatchdogFinding(
                            check_id="W017",
                            check_name="Coordinator sleep schedule",
                            severity="pass",
                            message=(
                                "Coordinator is sleeping until next_cycle_due_at_utc"
                            ),
                            artifact=artifact_dir_label,
                            field_name="next_cycle_due_at_utc",
                        )
                    )
                elif delta_seconds <= cadence_seconds:
                    findings.append(
                        WatchdogFinding(
                            check_id="W017",
                            check_name="Coordinator sleep schedule",
                            severity="warn",
                            message=(
                                f"next_cycle_due_at_utc exceeded by {delta_seconds:.0f}s "
                                f"within cadence tolerance {cadence_seconds}s"
                            ),
                            artifact=artifact_dir_label,
                            field_name="next_cycle_due_at_utc",
                        )
                    )
                else:
                    findings.append(
                        WatchdogFinding(
                            check_id="W017",
                            check_name="Coordinator sleep schedule",
                            severity="fail",
                            message=(
                                f"next_cycle_due_at_utc exceeded by {delta_seconds:.0f}s "
                                f"beyond cadence tolerance {cadence_seconds}s"
                            ),
                            artifact=artifact_dir_label,
                            field_name="next_cycle_due_at_utc",
                        )
                    )
            except WatchdogError:
                findings.append(
                    WatchdogFinding(
                        check_id="W017",
                        check_name="Coordinator sleep schedule",
                        severity="fail",
                        message=(
                            f"next_cycle_due_at_utc={next_cycle_due_at_utc!r} is not valid ISO-8601"
                        ),
                        artifact=artifact_dir_label,
                        field_name="next_cycle_due_at_utc",
                    )
                )

    return findings


def _collect_artifact_paths(artifact_dir: Path) -> dict[str, list[Path]]:
    return {
        "collector_reports": sorted(artifact_dir.glob("collector_report_*.json")),
        "snapshots_json": sorted(artifact_dir.glob("snapshot_*.json")),
        "alerts_json": sorted(artifact_dir.glob("alert_*.json")),
    }


REQUIRED_ARTIFACT_KEYS: dict[str, str] = {
    "collector_reports": "collector_report_*.json",
    "snapshots_json": "snapshot_*.json",
    "alerts_json": "alert_*.json",
}


def _check_required_artifacts(
    artifact_dir: Path,
    artifact_dir_label: str,
    artifact_paths: dict[str, list[Path]] | None = None,
) -> list[WatchdogFinding]:
    findings: list[WatchdogFinding] = []
    if artifact_paths is None:
        artifact_paths = _collect_artifact_paths(artifact_dir)

    for key, pattern in REQUIRED_ARTIFACT_KEYS.items():
        paths = artifact_paths.get(key, [])
        if not paths:
            findings.append(
                WatchdogFinding(
                    check_id="W008",
                    check_name=f"Required artifact: {pattern}",
                    severity="fail",
                    message=f"No files matching {pattern} found in {artifact_dir_label}",
                    artifact=artifact_dir_label,
                )
            )
        else:
            most_recent = max(paths, key=lambda p: p.stat().st_mtime)
            findings.append(
                WatchdogFinding(
                    check_id="W008",
                    check_name=f"Required artifact: {pattern}",
                    severity="pass",
                    message=(
                        f"Found {len(paths)} file(s) matching {pattern}, "
                        f"most recent: {most_recent.name}"
                    ),
                    artifact=artifact_dir_label,
                )
            )

    return findings


def _check_artifact_integrity(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
    *,
    max_age_seconds: int,
    warn_age_seconds: int,
    now: datetime,
) -> list[WatchdogFinding]:
    findings: list[WatchdogFinding] = []
    json_keys = {"collector_reports", "snapshots_json", "alerts_json"}

    snapshot_payloads: dict[Path, dict[str, Any]] = {}
    latest_snapshot_name: str | None = None
    latest_snapshot_ts: datetime | None = None

    for path in artifact_paths.get("snapshots_json", []):
        artifact_label = f"{artifact_dir_label}/{path.name}"
        try:
            payload = _load_json(path)
        except WatchdogError as exc:
            findings.append(
                WatchdogFinding(
                    check_id="W009",
                    check_name=f"Artifact parses as JSON: {path.name}",
                    severity="fail",
                    message=str(exc),
                    artifact=artifact_label,
                )
            )
            continue
        snapshot_payloads[path] = payload
        generated_at = payload.get("metadata", {}).get("generated_at_utc", "")
        if not generated_at:
            continue
        try:
            ts = _parse_ts(generated_at, "generated_at_utc")
        except WatchdogError:
            continue
        if latest_snapshot_ts is None or ts > latest_snapshot_ts:
            latest_snapshot_ts = ts
            latest_snapshot_name = path.name

    for label, paths in artifact_paths.items():
        is_json_artifact = label in json_keys
        for path in paths:
            artifact_label = f"{artifact_dir_label}/{path.name}"
            if not is_json_artifact:
                continue

            if label == "snapshots_json":
                payload = snapshot_payloads.get(path)
                if payload is None:
                    continue
            else:
                try:
                    payload = _load_json(path)
                except WatchdogError as exc:
                    findings.append(
                        WatchdogFinding(
                            check_id="W009",
                            check_name=f"Artifact parses as JSON: {path.name}",
                            severity="fail",
                            message=str(exc),
                            artifact=artifact_label,
                        )
                    )
                    continue

            if label == "snapshots_json":
                schema_ver = payload.get("metadata", {}).get("schema_version", "")
                if schema_ver and schema_ver != SNAPSHOT_SCHEMA_EXPECTED:
                    findings.append(
                        WatchdogFinding(
                            check_id="W010",
                            check_name=f"Snapshot schema: {path.name}",
                            severity="fail",
                            message=(
                                f"Expected {SNAPSHOT_SCHEMA_EXPECTED!r}, "
                                f"got {schema_ver!r}"
                            ),
                            artifact=artifact_label,
                            field_name="metadata.schema_version",
                        )
                    )
                generated_at = payload.get("metadata", {}).get("generated_at_utc", "")
                if generated_at:
                    try:
                        ts = _parse_ts(generated_at, "generated_at_utc")
                        if path.name == latest_snapshot_name:
                            age_seconds = (now - ts).total_seconds()
                            if age_seconds > max_age_seconds:
                                findings.append(
                                    WatchdogFinding(
                                        check_id="W011",
                                        check_name=f"Snapshot freshness: {path.name}",
                                        severity="fail",
                                        message=(
                                            f"Latest snapshot is {age_seconds:.0f}s old "
                                            f"(max_age={max_age_seconds}s)"
                                        ),
                                        artifact=artifact_label,
                                        field_name="metadata.generated_at_utc",
                                    )
                                )
                            elif age_seconds > warn_age_seconds:
                                findings.append(
                                    WatchdogFinding(
                                        check_id="W011",
                                        check_name=f"Snapshot freshness: {path.name}",
                                        severity="warn",
                                        message=(
                                            f"Latest snapshot is {age_seconds:.0f}s old "
                                            f"(warn_age={warn_age_seconds}s)"
                                        ),
                                        artifact=artifact_label,
                                        field_name="metadata.generated_at_utc",
                                    )
                                )
                            else:
                                findings.append(
                                    WatchdogFinding(
                                        check_id="W011",
                                        check_name=f"Snapshot freshness: {path.name}",
                                        severity="pass",
                                        message=(
                                            f"Latest snapshot is {age_seconds:.0f}s old "
                                            "(within limit)"
                                        ),
                                        artifact=artifact_label,
                                        field_name="metadata.generated_at_utc",
                                    )
                                )
                    except WatchdogError:
                        findings.append(
                            WatchdogFinding(
                                check_id="W011",
                                check_name=f"Snapshot freshness: {path.name}",
                                severity="fail",
                                message=(
                                    f"generated_at_utc={generated_at!r} "
                                    "is not valid ISO-8601"
                                ),
                                artifact=artifact_label,
                                field_name="metadata.generated_at_utc",
                            )
                        )

                safety = payload.get("safety", {})
                for sf_key, expected in [
                    ("lr_status", "NO-GO"),
                    ("live_status", "NO-GO"),
                    ("echtgeld_status", "NO-GO"),
                ]:
                    actual = safety.get(sf_key)
                    if actual != expected:
                        findings.append(
                            WatchdogFinding(
                                check_id="W012",
                                check_name=f"Safety flag: {sf_key} in {path.name}",
                                severity="fail",
                                message=(
                                    f"Expected {sf_key}={expected!r}, got {actual!r}"
                                ),
                                artifact=artifact_label,
                                field_name=f"safety.{sf_key}",
                            )
                        )

            if label == "alerts_json":
                schema_ver = payload.get("schema_version", "")
                if schema_ver and schema_ver != ALERT_SCHEMA_EXPECTED:
                    findings.append(
                        WatchdogFinding(
                            check_id="W013",
                            check_name=f"Alert schema: {path.name}",
                            severity="fail",
                            message=(
                                f"Expected {ALERT_SCHEMA_EXPECTED!r}, "
                                f"got {schema_ver!r}"
                            ),
                            artifact=artifact_label,
                            field_name="schema_version",
                        )
                    )
                manual_only = payload.get("manual_escalation_only", True)
                if isinstance(manual_only, bool) and not manual_only:
                    findings.append(
                        WatchdogFinding(
                            check_id="W014",
                            check_name=f"Alert manual escalation: {path.name}",
                            severity="fail",
                            message="manual_escalation_only is false",
                            artifact=artifact_label,
                            field_name="manual_escalation_only",
                        )
                    )

    return findings


def _check_cadence(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
    *,
    cadence_seconds: int,
    now: datetime,
) -> list[WatchdogFinding]:
    findings: list[WatchdogFinding] = []
    timestamps: list[datetime] = []
    for path in artifact_paths.get("snapshots_json", []):
        try:
            payload = _load_json(path)
            ts_raw = payload.get("metadata", {}).get("generated_at_utc", "")
            if ts_raw:
                timestamps.append(_parse_ts(ts_raw, "generated_at_utc"))
        except (WatchdogError, json.JSONDecodeError):
            continue

    if not timestamps:
        if artifact_paths.get("snapshots_json"):
            findings.append(
                WatchdogFinding(
                    check_id="W015",
                    check_name="Snapshot cadence check",
                    severity="fail",
                    message="No valid timestamps found in snapshot metadata",
                    artifact=artifact_dir_label,
                )
            )
        return findings

    latest_ts = max(timestamps)
    gap = (now - latest_ts).total_seconds()
    if gap > cadence_seconds * 2:
        findings.append(
            WatchdogFinding(
                check_id="W015",
                check_name="Snapshot cadence check",
                severity="fail",
                message=(
                    f"Last snapshot was {gap:.0f}s ago "
                    f"(more than 2x cadence of {cadence_seconds}s)"
                ),
                artifact=artifact_dir_label,
            )
        )
    elif gap > cadence_seconds:
        findings.append(
            WatchdogFinding(
                check_id="W015",
                check_name="Snapshot cadence check",
                severity="warn",
                message=(
                    f"Last snapshot was {gap:.0f}s ago "
                    f"(exceeds cadence of {cadence_seconds}s)"
                ),
                artifact=artifact_dir_label,
            )
        )
    else:
        findings.append(
            WatchdogFinding(
                check_id="W015",
                check_name="Snapshot cadence check",
                severity="pass",
                message=(
                    f"Last snapshot was {gap:.0f}s ago "
                    f"(within cadence of {cadence_seconds}s)"
                ),
                artifact=artifact_dir_label,
            )
        )

    return findings


def run_status(
    artifact_dir: Path,
    *,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    warn_age_seconds: int = DEFAULT_WARN_AGE_SECONDS,
    cadence_seconds: int = DEFAULT_CADENCE_SECONDS,
    now: datetime | None = None,
) -> WatchdogReport:
    eval_now = now or _now_utc()
    artifact_dir_label = str(artifact_dir)
    artifact_paths = _collect_artifact_paths(artifact_dir)

    all_findings: list[WatchdogFinding] = []

    heartbeat_payload = None
    state_payload = None
    hb_path = artifact_dir / "runner_heartbeat.json"
    state_path = artifact_dir / "runner_state.json"

    if hb_path.exists():
        try:
            heartbeat_payload = _load_json(hb_path)
        except WatchdogError:
            pass
    if state_path.exists():
        try:
            state_payload = _load_json(state_path)
        except WatchdogError:
            pass

    coordinator_events = _load_coordinator_events(artifact_dir)

    coordinator_liveness = _classify_coordinator_liveness(
        state_payload,
        coordinator_events,
        heartbeat_payload,
        now=eval_now,
        max_age_seconds=max_age_seconds,
        cadence_seconds=cadence_seconds,
    )

    hb_findings = _check_heartbeat(
        heartbeat_payload,
        artifact_dir_label,
        max_age_seconds=max_age_seconds,
        warn_age_seconds=warn_age_seconds,
        now=eval_now,
    )
    all_findings.extend(hb_findings)

    state_findings = _check_runner_state(
        state_payload,
        artifact_dir_label,
        max_age_seconds=max_age_seconds,
        warn_age_seconds=warn_age_seconds,
        cadence_seconds=cadence_seconds,
        now=eval_now,
    )
    all_findings.extend(state_findings)

    artifact_findings = _check_required_artifacts(
        artifact_dir, artifact_dir_label, artifact_paths
    )
    all_findings.extend(artifact_findings)

    integrity_findings = _check_artifact_integrity(
        artifact_paths,
        artifact_dir_label,
        max_age_seconds=max_age_seconds,
        warn_age_seconds=warn_age_seconds,
        now=eval_now,
    )
    all_findings.extend(integrity_findings)

    cadence_findings = _check_cadence(
        artifact_paths,
        artifact_dir_label,
        cadence_seconds=cadence_seconds,
        now=eval_now,
    )
    all_findings.extend(cadence_findings)

    fail_count = sum(1 for f in all_findings if f.severity == "fail")
    warn_count = sum(1 for f in all_findings if f.severity == "warn")
    pass_count = sum(1 for f in all_findings if f.severity == "pass")

    if fail_count:
        verdict = "FAIL"
    elif warn_count:
        verdict = "WARN"
    else:
        verdict = "PASS"

    heartbeat_fresh = not any(
        f.check_id == "W003" and f.severity == "fail" for f in all_findings
    )
    runner_state_ok = not any(
        f.check_id in {"W004", "W005", "W006", "W016", "W017"} and f.severity == "fail"
        for f in all_findings
    )
    required_artifacts_present = not any(
        f.check_id == "W008" and f.severity == "fail" for f in all_findings
    )

    sorted_findings = tuple(
        sorted(
            all_findings,
            key=lambda f: (
                {"fail": 0, "warn": 1, "pass": 2}.get(f.severity, 9),
                f.check_id,
            ),
        )
    )

    return WatchdogReport(
        schema_version=WATCHDOG_REPORT_SCHEMA,
        evaluated_at_utc=_format_ts(eval_now),
        artifact_dir=str(artifact_dir),
        mode="status",
        heartbeat_fresh=heartbeat_fresh,
        runner_state_ok=runner_state_ok,
        required_artifacts_present=required_artifacts_present,
        coordinator_liveness=coordinator_liveness,
        verdict=WatchdogVerdict(
            verdict=verdict,
            total_checks=len(sorted_findings),
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
        ),
        findings=sorted_findings,
    )


def run_check_artifacts(
    artifact_dir: Path,
    *,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    warn_age_seconds: int = DEFAULT_WARN_AGE_SECONDS,
    now: datetime | None = None,
) -> WatchdogReport:
    eval_now = now or _now_utc()
    artifact_dir_label = str(artifact_dir)
    artifact_paths = _collect_artifact_paths(artifact_dir)

    all_findings: list[WatchdogFinding] = []

    artifact_findings = _check_required_artifacts(
        artifact_dir, artifact_dir_label, artifact_paths
    )
    all_findings.extend(artifact_findings)

    integrity_findings = _check_artifact_integrity(
        artifact_paths,
        artifact_dir_label,
        max_age_seconds=max_age_seconds,
        warn_age_seconds=warn_age_seconds,
        now=eval_now,
    )
    all_findings.extend(integrity_findings)

    fail_count = sum(1 for f in all_findings if f.severity == "fail")
    warn_count = sum(1 for f in all_findings if f.severity == "warn")
    pass_count = sum(1 for f in all_findings if f.severity == "pass")

    if fail_count:
        verdict = "FAIL"
    elif warn_count:
        verdict = "WARN"
    else:
        verdict = "PASS"

    required_artifacts_present = not any(
        f.check_id == "W008" and f.severity == "fail" for f in all_findings
    )

    sorted_findings = tuple(
        sorted(
            all_findings,
            key=lambda f: (
                {"fail": 0, "warn": 1, "pass": 2}.get(f.severity, 9),
                f.check_id,
            ),
        )
    )

    coordinator_liveness = CoordinatorLiveness(
        classification="COORDINATOR_UNKNOWN",
        severity="warn",
        reason="Not evaluated in check-artifacts mode",
        coordinator_status_from_state="",
        has_lifecycle_telemetry=False,
    )

    return WatchdogReport(
        schema_version=WATCHDOG_REPORT_SCHEMA,
        evaluated_at_utc=_format_ts(eval_now),
        artifact_dir=str(artifact_dir),
        mode="check-artifacts",
        heartbeat_fresh=False,
        runner_state_ok=False,
        required_artifacts_present=required_artifacts_present,
        coordinator_liveness=coordinator_liveness,
        verdict=WatchdogVerdict(
            verdict=verdict,
            total_checks=len(sorted_findings),
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
        ),
        findings=sorted_findings,
    )


def render_escalation_draft(
    report: WatchdogReport, *, parent_issue: str = "3345"
) -> str:
    payload = report.to_dict()
    lines = [
        "# Evidence Harvester Watchdog — Manual Escalation Draft",
        "",
        "**This is a manual escalation draft only. No automatic GitHub writes were performed.**",
        "",
        "## Watchdog Summary",
        f"- Verdict: `{payload['verdict']['verdict']}`",
        f"- Evaluated at (UTC): `{payload['evaluated_at_utc']}`",
        f"- Artifact directory: `{payload['artifact_dir']}`",
        f"- Mode: `{payload['mode']}`",
        f"- Heartbeat fresh: `{payload['heartbeat_fresh']}`",
        f"- Runner state OK: `{payload['runner_state_ok']}`",
        f"- Required artifacts present: `{payload['required_artifacts_present']}`",
        f"- Checks: total={payload['verdict']['total_checks']}, "
        f"pass={payload['verdict']['pass_count']}, "
        f"warn={payload['verdict']['warn_count']}, "
        f"fail={payload['verdict']['fail_count']}",
    ]
    cl = payload.get("coordinator_liveness", {})
    if cl:
        severity_icon = {
            "pass": "PASS",
            "warn": "WARN",
            "fail": "FAIL",
        }.get(cl.get("severity", ""), "????")
        lines.extend(
            [
                "",
                "## Coordinator Liveness",
                f"- Classification: `{cl.get('classification', 'UNKNOWN')}`",
                f"- Severity: `{severity_icon}`",
                f"- Reason: {cl.get('reason', '')}",
                f"- Coordinator status: `{cl.get('coordinator_status_from_state', '')}`",
                f"- Lifecycle telemetry: `{cl.get('has_lifecycle_telemetry', False)}`",
                f"- Fatal stop event: `{cl.get('has_fatal_stop_event', False)}`",
                f"- Recovery events: `{cl.get('has_recovery_events', False)}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Findings",
        ]
    )

    findings = payload.get("findings", [])
    if findings:
        for item in findings:
            artifact_part = f" [{item['artifact']}]" if item.get("artifact") else ""
            field_part = f" ({item['field_name']})" if item.get("field_name") else ""
            lines.append(
                f"- [{item['severity'].upper()}] {item['check_name']}"
                f"{artifact_part}{field_part}: {item['message']}"
            )
    else:
        lines.append("- No findings.")

    lines.extend(
        [
            "",
            "## Escalation Guidance",
            "- Review findings above before creating any GitHub issue.",
            "- If verdict is FAIL, restart or repair the harvester runner before continuing.",
            "- If verdict is WARN, triage within the next operational window.",
            "- If verdict is PASS, no escalation needed.",
            "",
            "## Safety",
            "- Manual review required before any GitHub action.",
            "- No runtime / no DB execution / no Docker / no secrets.",
            f"- Parent issue: #{parent_issue}",
            "- No LR-Go / No Live-Go / No Echtgeld-Go.",
        ]
    )
    return "\n".join(lines) + "\n"


def _coordinator_liveness_to_markdown(payload: dict[str, Any]) -> list[str]:
    cl = payload.get("coordinator_liveness", {})
    if not cl:
        return []
    severity_icon = {
        "pass": "PASS",
        "warn": "WARN",
        "fail": "FAIL",
    }.get(cl.get("severity", ""), "????")
    lines = [
        "",
        "## Coordinator Liveness",
        f"- Classification: **{cl.get('classification', 'UNKNOWN')}**",
        f"- Severity: `{severity_icon}`",
        f"- Reason: {cl.get('reason', '')}",
        f"- Coordinator status (state): `{cl.get('coordinator_status_from_state', '')}`",
        f"- Lifecycle telemetry: `{cl.get('has_lifecycle_telemetry', False)}`",
    ]
    heartbeat_age = cl.get("last_heartbeat_age_seconds", 0)
    if heartbeat_age:
        lines.append(f"- Last heartbeat age: `{heartbeat_age:.0f}s`")
    next_due = cl.get("next_cycle_due_at_utc", "")
    if next_due:
        lines.append(f"- Next cycle due at (UTC): `{next_due}`")
    lines.append(f"- Fatal stop event: `{cl.get('has_fatal_stop_event', False)}`")
    lines.append(f"- Recovery events: `{cl.get('has_recovery_events', False)}`")
    return lines


def report_to_markdown(report: WatchdogReport) -> str:
    payload = report.to_dict()
    lines = [
        "# Evidence Harvester Watchdog Report",
        "",
        "## Metadata",
        f"- Schema version: `{payload['schema_version']}`",
        f"- Evaluated at (UTC): `{payload['evaluated_at_utc']}`",
        f"- Artifact directory: `{payload['artifact_dir']}`",
        f"- Mode: `{payload['mode']}`",
        "",
        "## Status Flags",
        f"- Heartbeat fresh: `{payload['heartbeat_fresh']}`",
        f"- Runner state OK: `{payload['runner_state_ok']}`",
        f"- Required artifacts present: `{payload['required_artifacts_present']}`",
        "",
        "## Summary",
        f"- Verdict: **{payload['verdict']['verdict']}**",
        f"- Total checks: {payload['verdict']['total_checks']}",
        f"- Pass: {payload['verdict']['pass_count']}",
        f"- Warn: {payload['verdict']['warn_count']}",
        f"- Fail: {payload['verdict']['fail_count']}",
    ]
    lines.extend(_coordinator_liveness_to_markdown(payload))
    lines.extend(
        [
            "",
            "## Findings",
        ]
    )
    for item in payload["findings"]:
        icon = {"fail": "FAIL", "warn": "WARN", "pass": "PASS"}.get(
            item["severity"], "????"
        )
        artifact_part = f" [{item['artifact']}]" if item.get("artifact") else ""
        field_part = f" ({item['field_name']})" if item.get("field_name") else ""
        lines.append(
            f"  [{icon}] {item['check_name']}{artifact_part}{field_part}: {item['message']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- No LR-Go / No Live-Go / No Echtgeld-Go.",
            "- No runtime / no DB execution / no Docker / no secrets.",
            "- Watchdog is read-only and does not modify artifacts.",
            "- No automatic restart, GitHub write, or scheduler install.",
        ]
    )
    return "\n".join(lines) + "\n"


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="Runner artifact directory to watch.",
    )
    parser.add_argument(
        "--max-age-seconds",
        type=int,
        default=DEFAULT_MAX_AGE_SECONDS,
        help="Max heartbeat/snapshot age before FAIL (default: 7200).",
    )
    parser.add_argument(
        "--warn-age-seconds",
        type=int,
        default=DEFAULT_WARN_AGE_SECONDS,
        help="Heartbeat/snapshot age for WARN (default: 5400).",
    )
    parser.add_argument(
        "--cadence-seconds",
        type=int,
        default=DEFAULT_CADENCE_SECONDS,
        help="Expected snapshot cadence in seconds (default: 86400).",
    )
    parser.add_argument(
        "--evaluated-at-utc",
        help="Optional explicit evaluation timestamp for deterministic tests.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for JSON watchdog report.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for Markdown watchdog report.",
    )
    parser.add_argument(
        "--escalation-draft-output",
        type=Path,
        help="Optional path for manual escalation draft.",
    )
    parser.add_argument(
        "--parent-issue",
        default="3345",
        help="Parent issue number for escalation draft (default: 3345).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )


def _handle_status(args: argparse.Namespace) -> int:
    artifact_dir = _resolve_artifact_dir(args.artifact_dir)
    now = _resolve_now(args)
    report = run_status(
        artifact_dir,
        max_age_seconds=args.max_age_seconds,
        warn_age_seconds=args.warn_age_seconds,
        cadence_seconds=args.cadence_seconds,
        now=now,
    )
    _emit_report(args, report)
    return 0 if report.verdict.verdict != "FAIL" else 1


def _handle_check_artifacts(args: argparse.Namespace) -> int:
    artifact_dir = _resolve_artifact_dir(args.artifact_dir)
    now = _resolve_now(args)
    report = run_check_artifacts(
        artifact_dir,
        max_age_seconds=args.max_age_seconds,
        warn_age_seconds=args.warn_age_seconds,
        now=now,
    )
    _emit_report(args, report)
    return 0 if report.verdict.verdict != "FAIL" else 1


def _handle_render_escalation_draft(args: argparse.Namespace) -> int:
    report_json_path = args.report_json.resolve()
    if not report_json_path.exists():
        print(f"Report JSON not found: {report_json_path}", file=sys.stderr)
        return 1
    payload = _load_json(report_json_path)
    cl_raw = payload.get("coordinator_liveness", {})
    coordinator_liveness = CoordinatorLiveness(
        classification=cl_raw.get("classification", "COORDINATOR_UNKNOWN"),
        severity=cl_raw.get("severity", "warn"),
        reason=cl_raw.get("reason", ""),
        coordinator_status_from_state=cl_raw.get("coordinator_status_from_state", ""),
        has_lifecycle_telemetry=bool(cl_raw.get("has_lifecycle_telemetry", False)),
        last_heartbeat_age_seconds=float(cl_raw.get("last_heartbeat_age_seconds", 0.0)),
        next_cycle_due_at_utc=cl_raw.get("next_cycle_due_at_utc", ""),
        has_fatal_stop_event=bool(cl_raw.get("has_fatal_stop_event", False)),
        has_recovery_events=bool(cl_raw.get("has_recovery_events", False)),
    )
    report = WatchdogReport(
        schema_version=payload.get("schema_version", WATCHDOG_REPORT_SCHEMA),
        evaluated_at_utc=payload.get("evaluated_at_utc", ""),
        artifact_dir=payload.get("artifact_dir", ""),
        mode=payload.get("mode", "unknown"),
        heartbeat_fresh=bool(payload.get("heartbeat_fresh", False)),
        runner_state_ok=bool(payload.get("runner_state_ok", False)),
        required_artifacts_present=bool(
            payload.get("required_artifacts_present", False)
        ),
        coordinator_liveness=coordinator_liveness,
        verdict=WatchdogVerdict(
            verdict=payload.get("verdict", {}).get("verdict", "FAIL"),
            total_checks=payload.get("verdict", {}).get("total_checks", 0),
            pass_count=payload.get("verdict", {}).get("pass_count", 0),
            warn_count=payload.get("verdict", {}).get("warn_count", 0),
            fail_count=payload.get("verdict", {}).get("fail_count", 0),
        ),
        findings=tuple(
            WatchdogFinding(
                check_id=item.get("check_id", ""),
                check_name=item.get("check_name", ""),
                severity=item.get("severity", "fail"),
                message=item.get("message", ""),
                artifact=item.get("artifact", ""),
                field_name=item.get("field_name", ""),
            )
            for item in payload.get("findings", [])
        ),
    )
    draft = render_escalation_draft(report, parent_issue=args.parent_issue)
    if args.escalation_draft_output:
        _write_text(args.escalation_draft_output, draft)
    else:
        print(draft)
    return 0


def _resolve_now(args: argparse.Namespace) -> datetime:
    if args.evaluated_at_utc:
        return _parse_ts(args.evaluated_at_utc, "--evaluated-at-utc")
    return _now_utc()


def _emit_report(args: argparse.Namespace, report: WatchdogReport) -> None:
    payload = report.to_dict()
    json_text = json.dumps(
        payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )
    print(json_text)

    if args.json_output:
        _write_text(args.json_output, json_text)
    if args.markdown_output:
        _write_text(args.markdown_output, report_to_markdown(report))
    if args.escalation_draft_output:
        _write_text(
            args.escalation_draft_output,
            render_escalation_draft(report, parent_issue=args.parent_issue),
        )


def _write_text(path: Path, text: str) -> None:
    path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv or [])
    if not argv:
        argv = ["status"]

    parser = argparse.ArgumentParser(
        description="Evidence harvester watchdog — detect stalls and stale evidence."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status",
        help="Full watchdog status: heartbeat, state, artifacts, cadence.",
    )
    _add_shared_args(status_parser)
    status_parser.set_defaults(handler=_handle_status)

    check_parser = subparsers.add_parser(
        "check-artifacts",
        help="Check artifact presence and integrity only.",
    )
    _add_shared_args(check_parser)
    check_parser.set_defaults(handler=_handle_check_artifacts)

    draft_parser = subparsers.add_parser(
        "render-escalation-draft",
        help="Render a manual escalation draft from a watchdog-report JSON.",
    )
    _add_shared_args(draft_parser)
    draft_parser.add_argument(
        "--report-json",
        type=Path,
        required=True,
        help="Path to an existing watchdog_report.json.",
    )
    draft_parser.set_defaults(handler=_handle_render_escalation_draft)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
