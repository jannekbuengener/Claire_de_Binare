"""Atomic campaign/run state ledger for #4153 sensitivity campaign."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash

STATE_SCHEMA_VERSION = "cdb.sensitivity_campaign_state.v1"
CAMPAIGN_ENVELOPE_NAME = "campaign_envelope.json"
RUNS_DIRNAME = "runs"

RUN_STATES = frozenset(
    {"PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}
)
TERMINAL_SUCCESS = "SUCCEEDED"


class SensitivityStateError(ValueError):
    """Fail-closed state / resume / idempotency error."""


def _now_utc_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Temp-file + fsync + os.replace (+ parent dir fsync when supported)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        # Best-effort parent-directory durability (POSIX). Windows may no-op.
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def acquire_campaign_lock(
    root: Path,
    *,
    holder_token: str,
    pid: int | None = None,
) -> Path:
    """Exclusive campaign-level claim via O_EXCL create (fail-closed).

    PID alone is not ownership proof — holder_token (auth fingerprint) is required.
    """
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".campaign.lock"
    token = str(holder_token or "").strip()
    if not token:
        raise SensitivityStateError("STATE_LOCK_TOKEN_REQUIRED")
    payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "holder_token": token,
        "pid": int(pid if pid is not None else os.getpid()),
        "acquired_at_utc": _now_utc_iso(),
    }
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_path), flags)
    except FileExistsError as exc:
        existing = {}
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        if existing.get("holder_token") == token:
            # Same authorization may re-enter (resume) — still exclusive per token.
            return lock_path
        raise SensitivityStateError("STATE_CAMPAIGN_LOCK_HELD") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.unlink(str(lock_path))
        except OSError:
            pass
        raise
    return lock_path


def release_campaign_lock(root: Path, *, holder_token: str) -> None:
    lock_path = root / ".campaign.lock"
    if not lock_path.exists():
        return
    try:
        existing = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SensitivityStateError("STATE_LOCK_MALFORMED") from exc
    if existing.get("holder_token") != holder_token:
        raise SensitivityStateError("STATE_LOCK_OWNERSHIP_MISMATCH")
    try:
        os.unlink(str(lock_path))
    except OSError as exc:
        raise SensitivityStateError("STATE_LOCK_RELEASE_FAILED") from exc


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SensitivityStateError(f"STATE_MISSING:{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SensitivityStateError(f"STATE_MALFORMED:{path}") from exc
    if not isinstance(payload, dict):
        raise SensitivityStateError(f"STATE_ROOT_NOT_OBJECT:{path}")
    return payload


def evidence_root_for(
    *,
    base: Path,
    campaign_id: str,
    manifest_fingerprint: str,
    authorization_id: str,
) -> Path:
    return (
        base
        / "artifacts"
        / "arvp_sensitivity"
        / "4153"
        / campaign_id
        / manifest_fingerprint
        / authorization_id
    )


@dataclass(frozen=True, slots=True)
class CampaignBindings:
    campaign_id: str
    manifest_fingerprint: str
    run_plan_fingerprint: str
    authorization_fingerprint: str
    execution_sha: str
    main_sha: str


def write_campaign_envelope(
    root: Path,
    *,
    bindings: CampaignBindings,
    run_count: int,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    path = root / CAMPAIGN_ENVELOPE_NAME
    if path.exists():
        existing = read_json(path)
        _assert_same_bindings(existing, bindings)
        return path
    payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "campaign_id": bindings.campaign_id,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "execution_sha": bindings.execution_sha,
        "main_sha": bindings.main_sha,
        "run_count": run_count,
        "created_at_utc": _now_utc_iso(),
        "status": "PLANNED",
        **dict(extra or {}),
    }
    atomic_write_json(path, payload)
    return path


def _assert_same_bindings(
    existing: Mapping[str, Any], bindings: CampaignBindings
) -> None:
    checks = {
        "campaign_id": bindings.campaign_id,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "execution_sha": bindings.execution_sha,
        "main_sha": bindings.main_sha,
    }
    for key, expected in checks.items():
        if existing.get(key) != expected:
            raise SensitivityStateError(f"STATE_BINDING_MISMATCH:{key}")


def run_envelope_path(root: Path, run_key: str) -> Path:
    return root / RUNS_DIRNAME / run_key / "run_envelope.json"


def result_path(root: Path, run_key: str) -> Path:
    return root / RUNS_DIRNAME / run_key / "result.json"


def completion_marker_path(root: Path, run_key: str) -> Path:
    return root / RUNS_DIRNAME / run_key / "COMPLETED"


def write_run_envelope(
    root: Path,
    *,
    run_key: str,
    bindings: CampaignBindings,
    status: str,
    attempt: int,
    envelope: Mapping[str, Any],
    exit_code: int | None = None,
    result_fingerprint: str | None = None,
) -> Path:
    if status not in RUN_STATES:
        raise SensitivityStateError(f"STATE_INVALID_RUN_STATUS:{status}")
    path = run_envelope_path(root, run_key)
    payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "run_key": run_key,
        "status": status,
        "attempt": attempt,
        "campaign_id": bindings.campaign_id,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "execution_sha": bindings.execution_sha,
        "main_sha": bindings.main_sha,
        "updated_at_utc": _now_utc_iso(),
        "exit_code": exit_code,
        "result_fingerprint": result_fingerprint,
        "envelope": dict(envelope),
    }
    if "started_at_utc" not in payload["envelope"] and status == "RUNNING":
        payload["started_at_utc"] = _now_utc_iso()
    if status in {"SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}:
        payload["ended_at_utc"] = _now_utc_iso()
    atomic_write_json(path, payload)
    return path


def commit_successful_result(
    root: Path,
    *,
    run_key: str,
    bindings: CampaignBindings,
    attempt: int,
    envelope: Mapping[str, Any],
    result: Mapping[str, Any],
    exit_code: int = 0,
) -> str:
    """Write result, then envelope SUCCEEDED, then completion marker (in that order)."""
    result_fp = canonical_hash(dict(result))
    rpath = result_path(root, run_key)
    atomic_write_json(
        rpath,
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "run_key": run_key,
            "result_fingerprint": result_fp,
            "manifest_fingerprint": bindings.manifest_fingerprint,
            "run_plan_fingerprint": bindings.run_plan_fingerprint,
            "authorization_fingerprint": bindings.authorization_fingerprint,
            "result": dict(result),
        },
    )
    write_run_envelope(
        root,
        run_key=run_key,
        bindings=bindings,
        status="SUCCEEDED",
        attempt=attempt,
        envelope=envelope,
        exit_code=exit_code,
        result_fingerprint=result_fp,
    )
    marker = completion_marker_path(root, run_key)
    atomic_write_json(
        marker,
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "run_key": run_key,
            "status": "SUCCEEDED",
            "result_fingerprint": result_fp,
            "completed_at_utc": _now_utc_iso(),
        },
    )
    return result_fp


def inspect_run_for_resume(
    root: Path,
    *,
    run_key: str,
    bindings: CampaignBindings,
    max_attempts: int,
    retry_failed: bool,
) -> str:
    """Return action: skip | retry | start | block:<reason>."""
    path = run_envelope_path(root, run_key)
    if not path.exists():
        return "start"
    existing = read_json(path)
    _assert_same_bindings(
        existing,
        bindings,
    )
    status = str(existing.get("status") or "")
    attempt = int(existing.get("attempt") or 0)
    if status == "SUCCEEDED":
        marker = completion_marker_path(root, run_key)
        rpath = result_path(root, run_key)
        if not marker.exists() or not rpath.exists():
            raise SensitivityStateError("STATE_PARTIAL_SUCCESS_BLOCKED")
        stored_fp = existing.get("result_fingerprint")
        result_body = read_json(rpath)
        if result_body.get("result_fingerprint") != stored_fp:
            raise SensitivityStateError("STATE_RESULT_FINGERPRINT_MISMATCH")
        if result_body.get("manifest_fingerprint") != bindings.manifest_fingerprint:
            raise SensitivityStateError("STATE_RESULT_MANIFEST_MISMATCH")
        if result_body.get("authorization_fingerprint") != (
            bindings.authorization_fingerprint
        ):
            raise SensitivityStateError("STATE_RESULT_AUTH_MISMATCH")
        return "skip"
    if status == "RUNNING":
        raise SensitivityStateError("STATE_RUNNING_WITHOUT_COMPLETION")
    if status == "FAILED":
        if not retry_failed:
            raise SensitivityStateError("STATE_FAILED_NO_RETRY")
        if attempt >= max_attempts:
            raise SensitivityStateError("STATE_RETRY_LIMIT_EXCEEDED")
        return "retry"
    if status in {"BLOCKED", "CANCELLED"}:
        raise SensitivityStateError(f"STATE_TERMINAL_{status}")
    if status == "PLANNED":
        return "start"
    raise SensitivityStateError(f"STATE_UNKNOWN_STATUS:{status}")


def assert_namespace_startable(
    root: Path,
    *,
    bindings: CampaignBindings,
    allow_resume: bool,
) -> str:
    """Return 'fresh' or 'resume'. Fail-closed on foreign/stale evidence."""
    if not root.exists():
        return "fresh"
    children = [p for p in root.iterdir() if not p.name.startswith(".")]
    if not children:
        return "fresh"
    envelope = root / CAMPAIGN_ENVELOPE_NAME
    if not envelope.exists():
        raise SensitivityStateError("STATE_NAMESPACE_COLLISION_NO_ENVELOPE")
    existing = read_json(envelope)
    _assert_same_bindings(existing, bindings)
    if not allow_resume:
        raise SensitivityStateError("STATE_RESUME_NOT_ALLOWED")
    return "resume"
