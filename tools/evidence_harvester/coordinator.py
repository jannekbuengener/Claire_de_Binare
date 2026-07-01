from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .runner import RunnerState

COORDINATOR_EVENT_SCHEMA = "cdb.evidence_harvester.coordinator_event.v1"
RECOVERY_EVENT_SCHEMA = "cdb.evidence_harvester.recovery_event.v1"

DEFAULT_MAX_RESTART_COUNT = 3
DEFAULT_RESTART_BACKOFF_SECONDS = 30
DEFAULT_CADENCE_SECONDS = 900

# Terminal coordinator states that a resume must not silently reopen.
_RESUME_REFUSED_STATUSES = frozenset({"completed", "failed", "fatal_stop"})


class CoordinatorError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RecoveryEvent:
    schema_version: str
    event_at_utc: str
    artifact_dir: str
    cycle_stamp: str
    failure_source: str
    trigger_report_name: str
    trigger_verdict: str
    classification: str
    reason_codes: tuple[str, ...]
    covered_report_names: tuple[str, ...]
    restart_attempted: bool
    restart_count: int
    max_restart_count: int
    backoff_seconds: int
    action: str
    limit_exceeded: bool
    audited: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CoordinatorSummary:
    status: str
    artifact_dir: str
    completed_cycles: int
    recovery_events_written: int
    restart_count: int
    max_restart_count: int
    final_validation_started: bool
    stop_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_utc() -> datetime:
    now = cdb_utcnow()
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _event_stamp(now: datetime | None = None) -> str:
    return (now or _now_utc()).strftime("%Y%m%dT%H%M%SZ")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoordinatorError(f"Malformed JSON in {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CoordinatorError(f"{path.name} JSON root must be an object")
    return payload


def _latest_cycle_stamp(artifact_dir: Path) -> str:
    reports = sorted(artifact_dir.glob("collector_report_*.json"))
    if not reports:
        raise CoordinatorError("No collector_report_*.json found to derive cycle stamp")
    latest = reports[-1].stem
    return latest.removeprefix("collector_report_")


def _coordinator_events_path(artifact_dir: Path) -> Path:
    return artifact_dir / "coordinator_events.jsonl"


def _read_coordinator_events(artifact_dir: Path) -> list[dict[str, Any]]:
    """Read durable coordinator lifecycle events, skipping malformed lines."""
    path = _coordinator_events_path(artifact_dir)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _derive_run_id(artifact_dir: Path) -> str:
    name = artifact_dir.name.strip()
    return name or _event_stamp()


def _read_runner_state(artifact_dir: Path) -> RunnerState | None:
    path = artifact_dir / "runner_state.json"
    if not path.exists():
        return None
    payload = _load_json(path)
    string_fields = {
        "schema_version",
        "last_cycle_verdict",
        "last_cycle_ended_at_utc",
        "run_id",
        "last_cycle_started_at_utc",
        "next_cycle_due_at_utc",
        "last_successful_artifact_stamp",
        "coordinator_status",
    }
    return RunnerState(
        **{
            field: payload.get(field, "" if field in string_fields else 0)
            for field in RunnerState.__dataclass_fields__
        }
    )


def _seed_runner_state(artifact_dir: Path, run_id: str) -> RunnerState:
    existing = _read_runner_state(artifact_dir)
    if existing is None:
        return RunnerState(run_id=run_id)
    if existing.run_id and existing.run_id != run_id:
        return RunnerState(run_id=run_id)
    return RunnerState(
        schema_version=existing.schema_version,
        total_runs=existing.total_runs,
        successful_runs=existing.successful_runs,
        failed_runs=existing.failed_runs,
        last_cycle_verdict=existing.last_cycle_verdict,
        last_cycle_ended_at_utc=existing.last_cycle_ended_at_utc,
        run_id=existing.run_id or run_id,
        total_cycles_started=existing.total_cycles_started,
        total_cycles_completed=existing.total_cycles_completed,
        total_successful_cycles=existing.total_successful_cycles,
        total_failed_cycles=existing.total_failed_cycles,
        last_cycle_started_at_utc=existing.last_cycle_started_at_utc,
        next_cycle_due_at_utc=existing.next_cycle_due_at_utc,
        last_successful_artifact_stamp=existing.last_successful_artifact_stamp,
        coordinator_status=existing.coordinator_status,
    )


def _write_runner_state(artifact_dir: Path, state: RunnerState) -> None:
    (artifact_dir / "runner_state.json").write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _update_runner_state(
    state: RunnerState,
    **changes: Any,
) -> RunnerState:
    payload = state.to_dict()
    payload.update(changes)
    payload["total_runs"] = payload.get("total_cycles_started", payload["total_runs"])
    payload["successful_runs"] = payload.get(
        "total_successful_cycles", payload["successful_runs"]
    )
    payload["failed_runs"] = payload.get("total_failed_cycles", payload["failed_runs"])
    return RunnerState(**payload)


def _last_event_is_stalled_sleep(
    events: Sequence[Mapping[str, Any]],
    coordinator_status: str,
) -> bool:
    """Detect the Slice-B/C/D stall: last durable event is sleep_started."""
    if not events:
        return False
    last_type = str(events[-1].get("event_type", "")).strip()
    if last_type != "sleep_started":
        return False
    return coordinator_status == "sleeping"


def _prepare_resume(artifact_dir: Path, run_id: str) -> tuple[RunnerState, int]:
    """Fail-closed resume preflight: require matching, non-terminal prior state."""
    state = _read_runner_state(artifact_dir)
    if state is None:
        raise CoordinatorError(
            "resume requires an existing runner_state.json in the artifact dir"
        )
    if state.run_id and state.run_id != run_id:
        raise CoordinatorError(
            f"resume run_id mismatch: runner_state.run_id={state.run_id!r} "
            f"but artifact dir implies run_id={run_id!r}"
        )
    if state.coordinator_status in _RESUME_REFUSED_STATUSES:
        raise CoordinatorError(
            "resume refused: coordinator_status is terminal "
            f"({state.coordinator_status!r})"
        )
    completed_cycles = int(state.total_cycles_completed or 0)
    return state, completed_cycles


def _write_coordinator_event(
    artifact_dir: Path,
    *,
    run_id: str,
    event_type: str,
    cycle_index: int | None = None,
    artifact_stamp: str = "",
    verdict: str = "",
    next_cycle_due_at_utc: str = "",
    recovery_attempt: int | None = None,
    error_classification: str = "",
    coordinator_status: str = "",
    stop_reason: str = "",
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": COORDINATOR_EVENT_SCHEMA,
        "event_at_utc": _format_ts(_now_utc()),
        "run_id": run_id,
        "event_type": event_type,
    }
    if cycle_index is not None:
        event["cycle_index"] = cycle_index
    if artifact_stamp:
        event["artifact_stamp"] = artifact_stamp
    if verdict:
        event["verdict"] = verdict
    if next_cycle_due_at_utc:
        event["next_cycle_due_at_utc"] = next_cycle_due_at_utc
    if recovery_attempt is not None:
        event["recovery_attempt"] = recovery_attempt
    if error_classification:
        event["error_classification"] = error_classification
    if coordinator_status:
        event["coordinator_status"] = coordinator_status
    if stop_reason:
        event["stop_reason"] = stop_reason
    with _coordinator_events_path(artifact_dir).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=True) + "\n")
    return event


def _extract_verdict(payload: Mapping[str, Any] | None) -> str:
    if not payload:
        return ""
    verdict = payload.get("verdict")
    if isinstance(verdict, Mapping):
        value = verdict.get("verdict")
        return str(value) if value is not None else ""
    if isinstance(verdict, str):
        return verdict
    return ""


def _classify_failure(
    failure_source: str,
    payload: Mapping[str, Any] | None,
    *,
    exit_code: int,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    if payload is None:
        return (
            "recoverable",
            (f"{failure_source}_exit_nonzero",),
            (),
        )

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        findings = []

    fatal_reasons: list[str] = []
    recoverable_reasons: list[str] = []

    for item in findings:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("severity", "")).lower() != "fail":
            continue
        check_id = str(item.get("check_id", ""))
        field_name = str(item.get("field_name", ""))
        message = str(item.get("message", ""))
        haystack = f"{check_id} {field_name} {message}".lower()

        if field_name.startswith("safety."):
            fatal_reasons.append("safety_flag_violation")
            continue
        if any(
            token in haystack
            for token in (
                "lr_status",
                "live_status",
                "echtgeld_status",
                "runtime_actions",
                "db_execution",
                "trade_executed",
                "order_submitted",
                "position_opened",
                "secret",
                "manual_escalation_only",
            )
        ):
            fatal_reasons.append("safety_or_side_effect_violation")
            continue
        if any(
            token in haystack
            for token in (
                "schema_version",
                "malformed json",
                "json root must be an object",
                "runner_heartbeat.json is missing",
                "runner_state.json is missing",
                "current_run_at_utc",
                "last_cycle_ended_at_utc",
                "not valid iso-8601",
            )
        ):
            fatal_reasons.append("malformed_core_state")
            continue
        if any(
            token in haystack
            for token in ("stale", "freshness", "cadence", "old", "missing")
        ):
            recoverable_reasons.append("stale_or_missing_latest_artifact")
            continue
        recoverable_reasons.append("recoverable_report_failure")

    if fatal_reasons:
        return ("fatal", tuple(sorted(set(fatal_reasons))), ())

    covered_names = []
    report_name = str(payload.get("report_name", "")).strip()
    if report_name:
        covered_names.append(report_name)
    verdict = _extract_verdict(payload)
    if verdict == "FAIL" and not recoverable_reasons:
        recoverable_reasons.append(f"{failure_source}_report_fail")
    if exit_code != 0 and not recoverable_reasons:
        recoverable_reasons.append(f"{failure_source}_exit_nonzero")
    return (
        "recoverable",
        tuple(sorted(set(recoverable_reasons or (f"{failure_source}_fail",)))),
        tuple(sorted(set(covered_names))),
    )


def _write_recovery_event(
    artifact_dir: Path,
    *,
    cycle_stamp: str,
    failure_source: str,
    trigger_report_name: str,
    trigger_verdict: str,
    classification: str,
    reason_codes: tuple[str, ...],
    covered_report_names: tuple[str, ...],
    restart_attempted: bool,
    restart_count: int,
    max_restart_count: int,
    backoff_seconds: int,
    action: str,
    limit_exceeded: bool,
) -> RecoveryEvent:
    event = RecoveryEvent(
        schema_version=RECOVERY_EVENT_SCHEMA,
        event_at_utc=_format_ts(_now_utc()),
        artifact_dir=str(artifact_dir),
        cycle_stamp=cycle_stamp,
        failure_source=failure_source,
        trigger_report_name=trigger_report_name,
        trigger_verdict=trigger_verdict,
        classification=classification,
        reason_codes=reason_codes,
        covered_report_names=covered_report_names,
        restart_attempted=restart_attempted,
        restart_count=restart_count,
        max_restart_count=max_restart_count,
        backoff_seconds=backoff_seconds,
        action=action,
        limit_exceeded=limit_exceeded,
        audited=True,
    )
    stamp = _event_stamp()
    json_path = artifact_dir / f"recovery_event_{stamp}.json"
    md_path = artifact_dir / f"recovery_event_{stamp}.md"
    json_path.write_text(
        json.dumps(event.to_dict(), indent=2, sort_keys=True, ensure_ascii=True),
        encoding="utf-8",
    )
    md_lines = [
        "# Recovery Event",
        "",
        f"- Event at (UTC): `{event.event_at_utc}`",
        f"- Cycle stamp: `{event.cycle_stamp}`",
        f"- Failure source: `{event.failure_source}`",
        f"- Trigger report: `{event.trigger_report_name}`",
        f"- Trigger verdict: `{event.trigger_verdict}`",
        f"- Classification: `{event.classification}`",
        f"- Action: `{event.action}`",
        f"- Restart attempted: `{event.restart_attempted}`",
        f"- Restart count: `{event.restart_count}` / `{event.max_restart_count}`",
        f"- Limit exceeded: `{event.limit_exceeded}`",
        f"- Audited: `{event.audited}`",
        "",
        "## Reasons",
    ]
    for reason in event.reason_codes:
        md_lines.append(f"- `{reason}`")
    if event.covered_report_names:
        md_lines.extend(["", "## Covered Reports"])
        for name in event.covered_report_names:
            md_lines.append(f"- `{name}`")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return event


def _sleep_with_interval_check(
    sleep_fn: Callable[[float], None],
    total_seconds: int,
    chunk_seconds: int = 60,
) -> float:
    """Sleep in chunks, returning overshoot (actual - expected) seconds."""
    if total_seconds <= 0:
        return 0.0
    if chunk_seconds < 1:
        raise CoordinatorError("chunk_seconds must be >= 1")

    started = time.monotonic()
    deadline = started + total_seconds
    requested_sleep = 0.0
    while requested_sleep < total_seconds:
        elapsed_remaining = deadline - time.monotonic()
        requested_remaining = total_seconds - requested_sleep
        if elapsed_remaining <= 0 or requested_remaining <= 0:
            break
        chunk = min(requested_remaining, elapsed_remaining, chunk_seconds)
        sleep_fn(chunk)
        requested_sleep += chunk
        if time.monotonic() >= deadline:
            break
    elapsed = max(time.monotonic() - started, requested_sleep)
    overshoot = elapsed - total_seconds
    return max(overshoot, 0.0)


def _default_boot_runner(
    repo_root: Path, artifact_dir: Path
) -> tuple[int, dict[str, Any] | None]:
    from .boot import _format_json, _render_report_md, _status

    json_path = artifact_dir / "boot_readiness_report.json"
    md_path = artifact_dir / "boot_readiness_report.md"
    report = _status(repo_root, _now_utc())
    payload = report.to_dict()
    json_text = _format_json(payload, pretty=True)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(_render_report_md(report), encoding="utf-8")
    exit_code = 0 if report.verdict.verdict != "FAIL" else 1
    return exit_code, payload


def _default_cycle_runner(
    repo_root: Path,
    fixture_path: Path,
    artifact_dir: Path,
) -> tuple[int, str]:
    from .runner import _now_utc as runner_now
    from .runner import _run_complete_cycle

    try:
        _run_complete_cycle(
            fixture_path=fixture_path,
            output_dir=artifact_dir,
            generated_at_utc=None,
            pretty=False,
            iteration=0,
            started_at=runner_now(),
            existing_heartbeat=None,
            mode="run-once-fixture",
        )
        exit_code = 0
    except Exception:
        exit_code = 1
    return exit_code, _latest_cycle_stamp(artifact_dir)


def _default_watchdog_runner(
    repo_root: Path,
    artifact_dir: Path,
    cycle_stamp: str,
    cadence_seconds: int,
) -> tuple[int, dict[str, Any] | None]:
    from .watchdog import report_to_markdown, run_status

    latest_json = artifact_dir / "watchdog_report.json"
    latest_md = artifact_dir / "watchdog_report.md"
    try:
        report = run_status(
            artifact_dir,
            cadence_seconds=cadence_seconds,
            now=_now_utc(),
        )
        payload_orig = report.to_dict()
        json_text = json.dumps(
            payload_orig, indent=2, sort_keys=True, ensure_ascii=True
        )
        latest_json.write_text(json_text + "\n", encoding="utf-8")
        (artifact_dir / f"watchdog_report_{cycle_stamp}.json").write_text(
            json_text + "\n", encoding="utf-8"
        )
        md_text = report_to_markdown(report)
        latest_md.write_text(md_text, encoding="utf-8")
        (artifact_dir / f"watchdog_report_{cycle_stamp}.md").write_text(
            md_text, encoding="utf-8"
        )
        payload = dict(payload_orig)
        payload["report_name"] = f"watchdog_report_{cycle_stamp}.json"
        exit_code = 0 if report.verdict.verdict != "FAIL" else 1
    except Exception:
        exit_code = 1
        payload = None
    return exit_code, payload


def _default_write_audit_runner(
    repo_root: Path,
    artifact_dir: Path,
    cycle_stamp: str,
) -> tuple[int, dict[str, Any] | None]:
    from .write_audit import report_to_markdown, run_write_audit

    json_path = artifact_dir / f"write_audit_report_{cycle_stamp}.json"
    md_path = artifact_dir / f"write_audit_report_{cycle_stamp}.md"
    try:
        report = run_write_audit(artifact_dir, now=_now_utc())
        payload_orig = report.to_dict()
        json_text = json.dumps(
            payload_orig, indent=2, sort_keys=True, ensure_ascii=True
        )
        json_path.write_text(json_text + "\n", encoding="utf-8")
        md_path.write_text(report_to_markdown(report), encoding="utf-8")
        payload = dict(payload_orig)
        payload["report_name"] = json_path.name
        exit_code = 0 if report.verdict.verdict != "FAIL" else 1
    except Exception:
        exit_code = 1
        payload = None
    return exit_code, payload


def _default_final_validator(
    repo_root: Path, artifact_dir: Path
) -> tuple[int, dict[str, Any] | None]:
    from .ops_validation import report_to_markdown, validate_72h_window_from_dir

    json_path = artifact_dir / "ops_validation_report.json"
    md_path = artifact_dir / "ops_validation_report.md"
    try:
        report = validate_72h_window_from_dir(artifact_dir, is_final=True)
        payload = report.to_dict()
        json_text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
        json_path.write_text(json_text + "\n", encoding="utf-8")
        md_path.write_text(report_to_markdown(report), encoding="utf-8")
        exit_code = 0 if report.summary.verdict != "FAIL" else 1
    except Exception:
        exit_code = 1
        payload = None
    return exit_code, payload


def run_fixture_window(
    *,
    repo_root: Path,
    fixture_path: Path,
    artifact_dir: Path,
    iterations: int,
    cadence_seconds: int = DEFAULT_CADENCE_SECONDS,
    max_restart_count: int = DEFAULT_MAX_RESTART_COUNT,
    restart_backoff_seconds: int = DEFAULT_RESTART_BACKOFF_SECONDS,
    resume: bool = False,
    sleep_fn: Callable[[float], None] = time.sleep,
    boot_runner: Callable[
        [Path, Path], tuple[int, dict[str, Any] | None]
    ] = _default_boot_runner,
    cycle_runner: Callable[[Path, Path, Path], tuple[int, str]] = _default_cycle_runner,
    watchdog_runner: Callable[
        [Path, Path, str, int], tuple[int, dict[str, Any] | None]
    ] = _default_watchdog_runner,
    write_audit_runner: Callable[
        [Path, Path, str], tuple[int, dict[str, Any] | None]
    ] = _default_write_audit_runner,
    final_validator: Callable[
        [Path, Path], tuple[int, dict[str, Any] | None]
    ] = _default_final_validator,
) -> CoordinatorSummary:
    if iterations < 1:
        raise CoordinatorError("iterations must be >= 1")
    if cadence_seconds < 1:
        raise CoordinatorError("cadence_seconds must be >= 1")
    if max_restart_count < 0:
        raise CoordinatorError("max_restart_count must be >= 0")
    if restart_backoff_seconds < 0:
        raise CoordinatorError("restart_backoff_seconds must be >= 0")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    if not fixture_path.exists():
        raise CoordinatorError(f"fixture path does not exist: {fixture_path}")

    run_id = _derive_run_id(artifact_dir)
    recovery_events_written = 0
    restart_count = 0
    completed_cycles = 0
    final_validation_started = False
    stop_reason = ""

    if resume:
        state, completed_cycles = _prepare_resume(artifact_dir, run_id)
        prior_events = _read_coordinator_events(artifact_dir)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="run_resumed",
            coordinator_status="resuming",
        )
        if _last_event_is_stalled_sleep(prior_events, state.coordinator_status):
            resume_cycle_index = int(state.total_cycles_started or 0)
            resume_stamp = state.last_successful_artifact_stamp or _event_stamp()
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="sleep_resumed",
                cycle_index=resume_cycle_index or None,
                artifact_stamp=state.last_successful_artifact_stamp,
                next_cycle_due_at_utc=state.next_cycle_due_at_utc,
                coordinator_status="resuming",
            )
            _write_recovery_event(
                artifact_dir,
                cycle_stamp=resume_stamp,
                failure_source="sleep_stall",
                trigger_report_name="coordinator_events.jsonl",
                trigger_verdict="INCONCLUSIVE",
                classification="recoverable",
                reason_codes=("sleep_started_without_sleep_completed",),
                covered_report_names=(),
                restart_attempted=True,
                restart_count=0,
                max_restart_count=max_restart_count,
                backoff_seconds=0,
                action="resume_cycle_window",
                limit_exceeded=False,
            )
            recovery_events_written += 1
        state = _update_runner_state(
            state,
            run_id=run_id,
            coordinator_status="running",
            next_cycle_due_at_utc="",
        )
        _write_runner_state(artifact_dir, state)
    else:
        state = _seed_runner_state(artifact_dir, run_id)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="run_started",
            coordinator_status="starting",
        )
        state = _update_runner_state(
            state, run_id=run_id, coordinator_status="starting"
        )
        _write_runner_state(artifact_dir, state)

    boot_exit, boot_payload = boot_runner(repo_root, artifact_dir)
    boot_verdict = _extract_verdict(boot_payload) or (
        "PASS" if boot_exit == 0 else "FAIL"
    )
    _write_coordinator_event(
        artifact_dir,
        run_id=run_id,
        event_type="boot_readiness_completed",
        verdict=boot_verdict,
        coordinator_status="boot_checked",
    )
    if boot_exit != 0 or _extract_verdict(boot_payload) == "FAIL":
        stop_reason = "boot_readiness_failed"
        state = _update_runner_state(
            state,
            coordinator_status="fatal_stop",
            last_cycle_verdict="FAIL",
        )
        _write_runner_state(artifact_dir, state)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="fatal_stop",
            verdict="FAIL",
            error_classification="boot_readiness_failed",
            coordinator_status="fatal_stop",
            stop_reason=stop_reason,
        )
        return CoordinatorSummary(
            status="FAIL",
            artifact_dir=str(artifact_dir),
            completed_cycles=0,
            recovery_events_written=0,
            restart_count=0,
            max_restart_count=max_restart_count,
            final_validation_started=False,
            stop_reason=stop_reason,
        )

    while completed_cycles < iterations:
        cycle_index = state.total_cycles_started + 1
        cycle_started_at = _format_ts(_now_utc())
        state = _update_runner_state(
            state,
            total_cycles_started=cycle_index,
            total_runs=cycle_index,
            last_cycle_started_at_utc=cycle_started_at,
            next_cycle_due_at_utc="",
            coordinator_status="running",
        )
        _write_runner_state(artifact_dir, state)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="cycle_started",
            cycle_index=cycle_index,
            coordinator_status="running",
        )
        runner_exit, cycle_stamp = cycle_runner(repo_root, fixture_path, artifact_dir)
        if runner_exit != 0:
            classification, reason_codes, covered = _classify_failure(
                "runner", None, exit_code=runner_exit
            )
            limit_exceeded = restart_count >= max_restart_count
            cycle_ended_at = _format_ts(_now_utc())
            state = _update_runner_state(
                state,
                total_failed_cycles=state.total_failed_cycles + 1,
                failed_runs=state.total_failed_cycles + 1,
                last_cycle_verdict="FAIL",
                last_cycle_ended_at_utc=cycle_ended_at,
                coordinator_status="recovering" if not limit_exceeded else "fatal_stop",
            )
            _write_runner_state(artifact_dir, state)
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="recovery_started",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp if cycle_stamp else "",
                verdict="FAIL",
                recovery_attempt=restart_count + 1,
                error_classification=classification,
                coordinator_status=state.coordinator_status,
            )
            _write_recovery_event(
                artifact_dir,
                cycle_stamp=cycle_stamp if cycle_stamp else _event_stamp(),
                failure_source="runner",
                trigger_report_name="runner",
                trigger_verdict="FAIL",
                classification="fatal" if limit_exceeded else classification,
                reason_codes=reason_codes,
                covered_report_names=covered,
                restart_attempted=not limit_exceeded,
                restart_count=restart_count + 1,
                max_restart_count=max_restart_count,
                backoff_seconds=restart_backoff_seconds,
                action="stop" if limit_exceeded else "restart_cycle",
                limit_exceeded=limit_exceeded,
            )
            recovery_events_written += 1
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="recovery_completed",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp if cycle_stamp else "",
                verdict="FAIL",
                recovery_attempt=restart_count + 1,
                error_classification="fatal" if limit_exceeded else classification,
                coordinator_status="fatal_stop" if limit_exceeded else "recovering",
            )
            if limit_exceeded:
                stop_reason = "restart_limit_exceeded"
                _write_coordinator_event(
                    artifact_dir,
                    run_id=run_id,
                    event_type="fatal_stop",
                    cycle_index=cycle_index,
                    artifact_stamp=cycle_stamp if cycle_stamp else "",
                    verdict="FAIL",
                    error_classification="restart_limit_exceeded",
                    coordinator_status="fatal_stop",
                    stop_reason=stop_reason,
                )
                break
            restart_count += 1
            if restart_backoff_seconds:
                sleep_fn(restart_backoff_seconds)
            continue

        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="runner_cycle_completed",
            cycle_index=cycle_index,
            artifact_stamp=cycle_stamp,
            verdict="PASS",
            coordinator_status="running",
        )

        watchdog_exit, watchdog_payload = watchdog_runner(
            repo_root, artifact_dir, cycle_stamp, cadence_seconds
        )
        watchdog_verdict = _extract_verdict(watchdog_payload)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="watchdog_completed",
            cycle_index=cycle_index,
            artifact_stamp=cycle_stamp,
            verdict=watchdog_verdict or ("PASS" if watchdog_exit == 0 else "FAIL"),
            coordinator_status="running",
        )
        if watchdog_exit != 0 or watchdog_verdict == "FAIL":
            classification, reason_codes, covered = _classify_failure(
                "watchdog", watchdog_payload, exit_code=watchdog_exit
            )
            limit_exceeded = restart_count >= max_restart_count
            cycle_ended_at = _format_ts(_now_utc())
            state = _update_runner_state(
                state,
                total_failed_cycles=state.total_failed_cycles + 1,
                failed_runs=state.total_failed_cycles + 1,
                last_cycle_verdict="FAIL",
                last_cycle_ended_at_utc=cycle_ended_at,
                coordinator_status=(
                    "recovering"
                    if classification == "recoverable" and not limit_exceeded
                    else "fatal_stop"
                ),
            )
            _write_runner_state(artifact_dir, state)
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="recovery_started",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                verdict=watchdog_verdict or "FAIL",
                recovery_attempt=restart_count + 1,
                error_classification=classification,
                coordinator_status=state.coordinator_status,
            )
            _write_recovery_event(
                artifact_dir,
                cycle_stamp=cycle_stamp,
                failure_source="watchdog",
                trigger_report_name=str(
                    (watchdog_payload or {}).get("report_name", "watchdog_report.json")
                ),
                trigger_verdict=watchdog_verdict or "FAIL",
                classification="fatal" if limit_exceeded else classification,
                reason_codes=reason_codes,
                covered_report_names=covered,
                restart_attempted=(
                    classification == "recoverable" and not limit_exceeded
                ),
                restart_count=restart_count + 1,
                max_restart_count=max_restart_count,
                backoff_seconds=restart_backoff_seconds,
                action=(
                    "restart_cycle"
                    if classification == "recoverable" and not limit_exceeded
                    else "stop"
                ),
                limit_exceeded=limit_exceeded,
            )
            recovery_events_written += 1
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="recovery_completed",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                verdict=watchdog_verdict or "FAIL",
                recovery_attempt=restart_count + 1,
                error_classification="fatal" if limit_exceeded else classification,
                coordinator_status=state.coordinator_status,
            )
            if classification == "fatal" or limit_exceeded:
                stop_reason = (
                    "restart_limit_exceeded"
                    if limit_exceeded
                    else "fatal_watchdog_failure"
                )
                _write_coordinator_event(
                    artifact_dir,
                    run_id=run_id,
                    event_type="fatal_stop",
                    cycle_index=cycle_index,
                    artifact_stamp=cycle_stamp,
                    verdict=watchdog_verdict or "FAIL",
                    error_classification=(
                        "restart_limit_exceeded"
                        if limit_exceeded
                        else "fatal_watchdog_failure"
                    ),
                    coordinator_status="fatal_stop",
                    stop_reason=stop_reason,
                )
                break
            restart_count += 1
            if restart_backoff_seconds:
                sleep_fn(restart_backoff_seconds)
            continue

        write_audit_exit, write_audit_payload = write_audit_runner(
            repo_root, artifact_dir, cycle_stamp
        )
        write_audit_verdict = _extract_verdict(write_audit_payload)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="write_audit_completed",
            cycle_index=cycle_index,
            artifact_stamp=cycle_stamp,
            verdict=(
                write_audit_verdict or ("PASS" if write_audit_exit == 0 else "FAIL")
            ),
            coordinator_status="running",
        )
        if write_audit_exit != 0 or write_audit_verdict == "FAIL":
            classification, reason_codes, covered = _classify_failure(
                "write_audit", write_audit_payload, exit_code=write_audit_exit
            )
            limit_exceeded = restart_count >= max_restart_count
            cycle_ended_at = _format_ts(_now_utc())
            state = _update_runner_state(
                state,
                total_failed_cycles=state.total_failed_cycles + 1,
                failed_runs=state.total_failed_cycles + 1,
                last_cycle_verdict="FAIL",
                last_cycle_ended_at_utc=cycle_ended_at,
                coordinator_status=(
                    "recovering"
                    if classification == "recoverable" and not limit_exceeded
                    else "fatal_stop"
                ),
            )
            _write_runner_state(artifact_dir, state)
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="recovery_started",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                verdict=write_audit_verdict or "FAIL",
                recovery_attempt=restart_count + 1,
                error_classification=classification,
                coordinator_status=state.coordinator_status,
            )
            _write_recovery_event(
                artifact_dir,
                cycle_stamp=cycle_stamp,
                failure_source="write_audit",
                trigger_report_name=str(
                    (write_audit_payload or {}).get(
                        "report_name", f"write_audit_report_{cycle_stamp}.json"
                    )
                ),
                trigger_verdict=write_audit_verdict or "FAIL",
                classification="fatal" if limit_exceeded else classification,
                reason_codes=reason_codes,
                covered_report_names=covered,
                restart_attempted=(
                    classification == "recoverable" and not limit_exceeded
                ),
                restart_count=restart_count + 1,
                max_restart_count=max_restart_count,
                backoff_seconds=restart_backoff_seconds,
                action=(
                    "restart_cycle"
                    if classification == "recoverable" and not limit_exceeded
                    else "stop"
                ),
                limit_exceeded=limit_exceeded,
            )
            recovery_events_written += 1
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="recovery_completed",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                verdict=write_audit_verdict or "FAIL",
                recovery_attempt=restart_count + 1,
                error_classification="fatal" if limit_exceeded else classification,
                coordinator_status=state.coordinator_status,
            )
            if classification == "fatal" or limit_exceeded:
                stop_reason = (
                    "restart_limit_exceeded"
                    if limit_exceeded
                    else "fatal_write_audit_failure"
                )
                _write_coordinator_event(
                    artifact_dir,
                    run_id=run_id,
                    event_type="fatal_stop",
                    cycle_index=cycle_index,
                    artifact_stamp=cycle_stamp,
                    verdict=write_audit_verdict or "FAIL",
                    error_classification=(
                        "restart_limit_exceeded"
                        if limit_exceeded
                        else "fatal_write_audit_failure"
                    ),
                    coordinator_status="fatal_stop",
                    stop_reason=stop_reason,
                )
                break
            restart_count += 1
            if restart_backoff_seconds:
                sleep_fn(restart_backoff_seconds)
            continue

        completed_cycles += 1
        cycle_ended_at = _format_ts(_now_utc())
        state = _update_runner_state(
            state,
            total_cycles_completed=completed_cycles,
            total_successful_cycles=state.total_successful_cycles + 1,
            successful_runs=state.total_successful_cycles + 1,
            last_cycle_verdict="PASS",
            last_cycle_ended_at_utc=cycle_ended_at,
            last_successful_artifact_stamp=cycle_stamp,
            coordinator_status="cycle_completed",
        )
        _write_runner_state(artifact_dir, state)
        _write_coordinator_event(
            artifact_dir,
            run_id=run_id,
            event_type="cycle_completed",
            cycle_index=cycle_index,
            artifact_stamp=cycle_stamp,
            verdict="PASS",
            coordinator_status="cycle_completed",
        )
        if completed_cycles < iterations:
            next_due_at = _format_ts(
                datetime.fromtimestamp(_now_utc().timestamp() + cadence_seconds, tz=UTC)
            )
            state = _update_runner_state(
                state,
                next_cycle_due_at_utc=next_due_at,
                coordinator_status="sleeping",
            )
            _write_runner_state(artifact_dir, state)
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="next_cycle_due_at_utc",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                next_cycle_due_at_utc=next_due_at,
                coordinator_status="sleeping",
            )
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="sleep_started",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                next_cycle_due_at_utc=next_due_at,
                coordinator_status="sleeping",
            )
            overshoot = _sleep_with_interval_check(
                sleep_fn, cadence_seconds, chunk_seconds=60
            )
            if overshoot > 60:
                _write_coordinator_event(
                    artifact_dir,
                    run_id=run_id,
                    event_type="sleep_overshoot",
                    cycle_index=cycle_index,
                    artifact_stamp=cycle_stamp,
                    next_cycle_due_at_utc=next_due_at,
                    coordinator_status="sleeping",
                )
            _write_coordinator_event(
                artifact_dir,
                run_id=run_id,
                event_type="sleep_completed",
                cycle_index=cycle_index,
                artifact_stamp=cycle_stamp,
                next_cycle_due_at_utc=next_due_at,
                coordinator_status="sleeping",
            )

    final_validation_started = True
    state = _update_runner_state(
        state,
        next_cycle_due_at_utc="",
        coordinator_status="final_validation",
    )
    _write_runner_state(artifact_dir, state)
    _write_coordinator_event(
        artifact_dir,
        run_id=run_id,
        event_type="final_validation_started",
        coordinator_status="final_validation",
    )
    final_validation_exit, final_validation_payload = final_validator(
        repo_root, artifact_dir
    )
    final_validation_verdict = _extract_verdict(final_validation_payload) or (
        "PASS" if final_validation_exit == 0 else "FAIL"
    )
    _write_coordinator_event(
        artifact_dir,
        run_id=run_id,
        event_type="final_validation_completed",
        verdict=final_validation_verdict,
        coordinator_status="final_validation",
    )

    status = "PASS" if completed_cycles == iterations and not stop_reason else "FAIL"
    if not stop_reason and completed_cycles != iterations:
        stop_reason = "incomplete_cycle_window"
    state = _update_runner_state(
        state,
        next_cycle_due_at_utc="",
        coordinator_status="completed" if status == "PASS" else "failed",
    )
    _write_runner_state(artifact_dir, state)
    return CoordinatorSummary(
        status=status,
        artifact_dir=str(artifact_dir),
        completed_cycles=completed_cycles,
        recovery_events_written=recovery_events_written,
        restart_count=restart_count,
        max_restart_count=max_restart_count,
        final_validation_started=final_validation_started,
        stop_reason=stop_reason,
    )


def _add_window_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fixture", type=Path, required=True, help="Collector-input fixture path."
    )
    parser.add_argument(
        "--artifact-dir", type=Path, required=True, help="Output artifact directory."
    )
    parser.add_argument(
        "--iterations",
        type=int,
        required=True,
        help="Number of successful cycles required.",
    )
    parser.add_argument(
        "--cadence-seconds",
        type=int,
        default=DEFAULT_CADENCE_SECONDS,
        help=f"Cycle cadence in seconds (default: {DEFAULT_CADENCE_SECONDS}).",
    )
    parser.add_argument(
        "--max-restart-count",
        type=int,
        default=DEFAULT_MAX_RESTART_COUNT,
        help=f"Maximum recoverable restarts (default: {DEFAULT_MAX_RESTART_COUNT}).",
    )
    parser.add_argument(
        "--restart-backoff-seconds",
        type=int,
        default=DEFAULT_RESTART_BACKOFF_SECONDS,
        help=f"Backoff between recoverable restarts (default: {DEFAULT_RESTART_BACKOFF_SECONDS}).",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evidence harvester 72h coordinator with bounded recovery."
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run-fixture-window",
        help="Run fixture-backed harvester cycles with watchdog/write-audit recovery.",
    )
    _add_window_args(run_parser)

    resume_parser = subparsers.add_parser(
        "resume-fixture-window",
        help=(
            "Resume an interrupted fixture-backed run from durable state, "
            "recovering a stalled sleep window (sleep_started without "
            "sleep_completed)."
        ),
    )
    _add_window_args(resume_parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command not in ("run-fixture-window", "resume-fixture-window"):
        raise CoordinatorError(f"Unsupported command: {args.command}")
    summary = run_fixture_window(
        repo_root=_repo_root(),
        fixture_path=args.fixture.resolve(),
        artifact_dir=args.artifact_dir.resolve(),
        iterations=args.iterations,
        cadence_seconds=args.cadence_seconds,
        max_restart_count=args.max_restart_count,
        restart_backoff_seconds=args.restart_backoff_seconds,
        resume=(args.command == "resume-fixture-window"),
    )
    payload = summary.to_dict()
    print(
        json.dumps(
            payload,
            indent=2 if args.pretty else None,
            sort_keys=True,
            ensure_ascii=True,
        )
    )
    return 0 if summary.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
