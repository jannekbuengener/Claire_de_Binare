from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .contract import QUEUE_STATE_SCHEMA_VERSION

QUEUE_STATE_FILENAME = "queue_state.json"
QUEUE_EVENTS_FILENAME = "queue_events.jsonl"
HEARTBEAT_FILENAME = "heartbeat.json"

EVENT_SCHEMA = "cdb.arvp_vacation.queue_event.v1"
HEARTBEAT_SCHEMA = "cdb.arvp_vacation.heartbeat.v1"


class QueueStoreError(ValueError):
    pass


def _now_utc_iso() -> str:
    now = cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _format_json(payload: Mapping[str, Any], pretty: bool = False) -> str:
    if pretty:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def atomic_write_json(path: Path, payload: Mapping[str, Any], *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(_format_json(payload, pretty), encoding="utf-8")
    tmp.replace(path)


def append_event(events_path: Path, event: Mapping[str, Any]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(event), sort_keys=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_queue_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise QueueStoreError(f"missing queue state: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QueueStoreError(f"malformed queue state: {path}") from exc
    if not isinstance(payload, dict):
        raise QueueStoreError("queue state root must be an object")
    return payload


def write_queue_state(path: Path, payload: Mapping[str, Any], *, pretty: bool = False) -> None:
    body = dict(payload)
    body["schema_version"] = QUEUE_STATE_SCHEMA_VERSION
    body["updated_at_utc"] = _now_utc_iso()
    atomic_write_json(path, body, pretty=pretty)


def write_heartbeat(path: Path, payload: Mapping[str, Any]) -> None:
    body = {
        "schema_version": HEARTBEAT_SCHEMA,
        "updated_at_utc": _now_utc_iso(),
        **dict(payload),
    }
    atomic_write_json(path, body)


def emit_event(
    events_path: Path,
    *,
    campaign_id: str,
    event_type: str,
    job_id: str | None = None,
    details: Mapping[str, Any] | None = None,
    now_fn: Callable[[], str] | None = None,
) -> None:
    event = {
        "schema_version": EVENT_SCHEMA,
        "event_at_utc": (now_fn or _now_utc_iso)(),
        "campaign_id": campaign_id,
        "event_type": event_type,
        "job_id": job_id,
        "details": dict(details or {}),
    }
    append_event(events_path, event)


def job_dir(campaign_dir: Path, job_id: str) -> Path:
    return campaign_dir / "jobs" / job_id


def recover_orphan_running_jobs(
    state: dict[str, Any],
    *,
    now_fn: Callable[[], str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Mark orphan RUNNING jobs as INTERRUPTED. Returns updated state and job ids."""
    jobs = state.get("jobs")
    if not isinstance(jobs, list):
        return state, []
    interrupted: list[str] = []
    now = (now_fn or _now_utc_iso)()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") != "RUNNING":
            continue
        job["status"] = "INTERRUPTED"
        job["finished_at_utc"] = now
        job["error_classification"] = "COORDINATOR_ORPHAN"
        interrupted.append(str(job.get("job_id", "")))
    return state, interrupted


def completed_fingerprints(state: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for raw in state.get("completed_fingerprints") or []:
        if isinstance(raw, str):
            result.add(raw.lower())
    for job in state.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        status = job.get("status")
        fingerprint = job.get("fingerprint")
        if status in {"PASS", "FAIL", "INSUFFICIENT_DATA"} and isinstance(fingerprint, str):
            result.add(fingerprint.lower())
    return result


def known_time_windows(state: Mapping[str, Any]) -> set[tuple[int, int]]:
    windows: set[tuple[int, int]] = set()
    for job in state.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        start = job.get("start_ts_ms")
        end = job.get("end_ts_ms")
        if start is not None and end is not None:
            windows.add((int(start), int(end)))
    return windows
