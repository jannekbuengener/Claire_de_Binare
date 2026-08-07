"""Atomic campaign/run state ledger for #4153 sensitivity campaign."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow

STATE_SCHEMA_VERSION = "cdb.sensitivity_campaign_state.v1"
CAMPAIGN_ENVELOPE_NAME = "campaign_envelope.json"
RUNS_DIRNAME = "runs"
REPRODUCTION_DIRNAME = "reproduction"
LOGICAL_RUN_KEY_SIDECAR = "logical_run_key.txt"
# Windows NTFS forbidden filename characters (and path separators).
_FS_UNSAFE_CHARS = frozenset('<>:"/\\|?*')
_FS_DIRNAME_PREFIX = "rk_"


def fs_dirname_for_run_key(run_key: str) -> str:
    """Deterministic Windows-safe directory name for a logical run_key.

    The logical ``run_key`` (may contain ``|``) is unchanged in envelopes and
    fingerprints. On-disk directories use ``rk_<sha256>`` so NTFS/Win32 paths
    never embed illegal characters (#4384).
    """
    digest = hashlib.sha256(str(run_key).encode("utf-8")).hexdigest()
    return f"{_FS_DIRNAME_PREFIX}{digest}"


def run_key_needs_fs_mapping(run_key: str) -> bool:
    text = str(run_key)
    return any(ch in _FS_UNSAFE_CHARS for ch in text) or text in {".", ".."} or not text


def run_dir(root: Path, run_key: str) -> Path:
    """Resolve the on-disk run directory for ``run_key``.

    Prefers the deterministic safe dirname. Falls back to a legacy raw-key
    directory when it already exists (Linux evidence created before #4384).
    New writes always target the safe path.
    """
    safe = Path(root) / RUNS_DIRNAME / fs_dirname_for_run_key(run_key)
    if safe.exists():
        return safe
    legacy = Path(root) / RUNS_DIRNAME / str(run_key)
    # Only accept legacy dirs that Windows could never have created with
    # unsafe chars as a *new* target; existing Linux trees remain readable.
    if legacy.exists():
        return legacy
    return safe


def write_logical_run_key_sidecar(run_directory: Path, run_key: str) -> Path:
    """Persist the logical run_key next to run artifacts (human/ops index)."""
    run_directory.mkdir(parents=True, exist_ok=True)
    path = run_directory / LOGICAL_RUN_KEY_SIDECAR
    path.write_text(str(run_key) + "\n", encoding="utf-8")
    return path


RUN_STATES = frozenset(
    {"PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}
)
TERMINAL_SUCCESS = "SUCCEEDED"

# Campaign lifecycle phases. Progression is strictly forward except for the
# terminal BLOCKED and COMPLETED states which trap the machine. The initial
# PLANNED alias is accepted for backward compatibility with a freshly written
# envelope (no ``campaign_phase`` field).
CAMPAIGN_PHASE_PLANNED = "PLANNED"
CAMPAIGN_PHASE_PRIMARY_PLANNED = "PRIMARY_PLANNED"
CAMPAIGN_PHASE_PRIMARY_RUNNING = "PRIMARY_RUNNING"
CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE = "PRIMARY_EVIDENCE_COMPLETE"
CAMPAIGN_PHASE_PRIMARY_COMPLETE = "PRIMARY_COMPLETE"
CAMPAIGN_PHASE_REPRODUCTION_PLANNED = "REPRODUCTION_PLANNED"
CAMPAIGN_PHASE_REPRODUCTION_RUNNING = "REPRODUCTION_RUNNING"
CAMPAIGN_PHASE_REPRODUCTION_COMPLETE = "REPRODUCTION_COMPLETE"
CAMPAIGN_PHASE_COMPLETED = "COMPLETED"
CAMPAIGN_PHASE_BLOCKED = "BLOCKED"

CAMPAIGN_PHASES = frozenset(
    {
        CAMPAIGN_PHASE_PLANNED,
        CAMPAIGN_PHASE_PRIMARY_PLANNED,
        CAMPAIGN_PHASE_PRIMARY_RUNNING,
        CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
        CAMPAIGN_PHASE_PRIMARY_COMPLETE,
        CAMPAIGN_PHASE_REPRODUCTION_PLANNED,
        CAMPAIGN_PHASE_REPRODUCTION_RUNNING,
        CAMPAIGN_PHASE_REPRODUCTION_COMPLETE,
        CAMPAIGN_PHASE_COMPLETED,
        CAMPAIGN_PHASE_BLOCKED,
    }
)

# Legal forward transitions. BLOCKED is always reachable from any non-terminal
# phase. COMPLETED and BLOCKED are terminal (self-transition allowed).
# PRIMARY_EVIDENCE_COMPLETE is the governed adoption landing zone for primary
# results produced by a pre-phase-machine runner (see adoption contract v1).
_LEGAL_PHASE_TRANSITIONS: dict[str, frozenset[str]] = {
    CAMPAIGN_PHASE_PLANNED: frozenset(
        {
            CAMPAIGN_PHASE_PRIMARY_RUNNING,
            CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
            CAMPAIGN_PHASE_BLOCKED,
        }
    ),
    CAMPAIGN_PHASE_PRIMARY_PLANNED: frozenset(
        {CAMPAIGN_PHASE_PRIMARY_RUNNING, CAMPAIGN_PHASE_BLOCKED}
    ),
    CAMPAIGN_PHASE_PRIMARY_RUNNING: frozenset(
        {CAMPAIGN_PHASE_PRIMARY_COMPLETE, CAMPAIGN_PHASE_BLOCKED}
    ),
    CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE: frozenset(
        {CAMPAIGN_PHASE_PRIMARY_COMPLETE, CAMPAIGN_PHASE_BLOCKED}
    ),
    CAMPAIGN_PHASE_PRIMARY_COMPLETE: frozenset(
        {
            CAMPAIGN_PHASE_REPRODUCTION_PLANNED,
            CAMPAIGN_PHASE_COMPLETED,
            CAMPAIGN_PHASE_BLOCKED,
        }
    ),
    CAMPAIGN_PHASE_REPRODUCTION_PLANNED: frozenset(
        {CAMPAIGN_PHASE_REPRODUCTION_RUNNING, CAMPAIGN_PHASE_BLOCKED}
    ),
    CAMPAIGN_PHASE_REPRODUCTION_RUNNING: frozenset(
        {CAMPAIGN_PHASE_REPRODUCTION_COMPLETE, CAMPAIGN_PHASE_BLOCKED}
    ),
    CAMPAIGN_PHASE_REPRODUCTION_COMPLETE: frozenset(
        {CAMPAIGN_PHASE_COMPLETED, CAMPAIGN_PHASE_BLOCKED}
    ),
    CAMPAIGN_PHASE_COMPLETED: frozenset({CAMPAIGN_PHASE_COMPLETED}),
    CAMPAIGN_PHASE_BLOCKED: frozenset({CAMPAIGN_PHASE_BLOCKED}),
}


class SensitivityStateError(ValueError):
    """Fail-closed state / resume / idempotency error."""


def _now_utc_iso() -> str:
    now = cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(UTC).isoformat().replace("+00:00", "Z")


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
    return run_dir(root, run_key) / "run_envelope.json"


def result_path(root: Path, run_key: str) -> Path:
    return run_dir(root, run_key) / "result.json"


def completion_marker_path(root: Path, run_key: str) -> Path:
    return run_dir(root, run_key) / "COMPLETED"


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
    write_logical_run_key_sidecar(path.parent, run_key)
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


def update_campaign_phase(
    root: Path,
    *,
    bindings: CampaignBindings,
    phase: str,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    """Atomically transition the campaign envelope to ``phase``.

    Fail-closed on unknown phase, missing envelope, binding mismatch, or
    illegal transition. Terminal phases (COMPLETED, BLOCKED) cannot be left
    once set (self-transition allowed for idempotency).
    """
    if phase not in CAMPAIGN_PHASES:
        raise SensitivityStateError(f"STATE_PHASE_UNKNOWN:{phase}")
    envelope_path = root / CAMPAIGN_ENVELOPE_NAME
    if not envelope_path.exists():
        raise SensitivityStateError("STATE_PHASE_ENVELOPE_MISSING")
    existing = read_json(envelope_path)
    _assert_same_bindings(existing, bindings)
    current = str(existing.get("campaign_phase") or existing.get("status") or "")
    if current == "":
        current = CAMPAIGN_PHASE_PLANNED
    if current not in CAMPAIGN_PHASES:
        # Legacy status like "PLANNED" is aliased above; anything else is bogus.
        raise SensitivityStateError(f"STATE_PHASE_CURRENT_UNKNOWN:{current}")
    allowed = _LEGAL_PHASE_TRANSITIONS.get(current, frozenset())
    if phase == current:
        # Idempotent no-op still records the extra payload.
        updated = dict(existing)
        updated["campaign_phase"] = phase
        updated["phase_updated_at_utc"] = _now_utc_iso()
        for key, value in dict(extra or {}).items():
            updated[key] = value
        atomic_write_json(envelope_path, updated)
        return envelope_path
    if phase not in allowed:
        raise SensitivityStateError(
            f"STATE_PHASE_ILLEGAL_TRANSITION:{current}->{phase}"
        )
    updated = dict(existing)
    updated["campaign_phase"] = phase
    updated["phase_updated_at_utc"] = _now_utc_iso()
    for key, value in dict(extra or {}).items():
        updated[key] = value
    atomic_write_json(envelope_path, updated)
    return envelope_path


def read_campaign_phase(root: Path) -> str:
    """Return the current campaign phase; PLANNED for a freshly written envelope."""
    envelope_path = root / CAMPAIGN_ENVELOPE_NAME
    if not envelope_path.exists():
        return CAMPAIGN_PHASE_PLANNED
    existing = read_json(envelope_path)
    current = str(existing.get("campaign_phase") or "")
    if current == "":
        return CAMPAIGN_PHASE_PLANNED
    return current


def reproduction_dir(root: Path, run_key: str, reproduction_attempt: int) -> Path:
    """Return the canonical reproduction-attempt directory for a primary run key."""
    if reproduction_attempt < 1:
        raise SensitivityStateError("STATE_REPRO_ATTEMPT_INVALID")
    return (
        run_dir(root, run_key)
        / REPRODUCTION_DIRNAME
        / str(int(reproduction_attempt))
    )


def reproduction_envelope_path(
    root: Path, run_key: str, reproduction_attempt: int
) -> Path:
    return reproduction_dir(root, run_key, reproduction_attempt) / "run_envelope.json"


def reproduction_result_path(
    root: Path, run_key: str, reproduction_attempt: int
) -> Path:
    return reproduction_dir(root, run_key, reproduction_attempt) / "result.json"


def reproduction_completion_marker_path(
    root: Path, run_key: str, reproduction_attempt: int
) -> Path:
    return reproduction_dir(root, run_key, reproduction_attempt) / "COMPLETED"


def reproduction_comparison_path(
    root: Path, run_key: str, reproduction_attempt: int
) -> Path:
    return reproduction_dir(root, run_key, reproduction_attempt) / "comparison.json"


def write_reproduction_envelope(
    root: Path,
    *,
    run_key: str,
    reproduction_attempt: int,
    bindings: CampaignBindings,
    status: str,
    attempt: int,
    envelope: Mapping[str, Any],
    exit_code: int | None = None,
    result_fingerprint: str | None = None,
) -> Path:
    if status not in RUN_STATES:
        raise SensitivityStateError(f"STATE_INVALID_RUN_STATUS:{status}")
    path = reproduction_envelope_path(root, run_key, reproduction_attempt)
    payload = {
        "schema_version": STATE_SCHEMA_VERSION,
        "run_key": run_key,
        "reproduction_attempt": int(reproduction_attempt),
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
    if status == "RUNNING":
        payload["started_at_utc"] = _now_utc_iso()
    if status in {"SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}:
        payload["ended_at_utc"] = _now_utc_iso()
    atomic_write_json(path, payload)
    return path


def persist_reproduction_result(
    root: Path,
    *,
    run_key: str,
    reproduction_attempt: int,
    bindings: CampaignBindings,
    result: Mapping[str, Any],
) -> str:
    """Atomically persist reproduction ``result.json`` without success markers.

    Callers must write ``comparison.json`` and only then call
    :func:`commit_successful_reproduction_result` after a PASS comparison.
    """
    result_fp = canonical_hash(dict(result))
    rpath = reproduction_result_path(root, run_key, reproduction_attempt)
    atomic_write_json(
        rpath,
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "run_key": run_key,
            "reproduction_attempt": int(reproduction_attempt),
            "result_fingerprint": result_fp,
            "manifest_fingerprint": bindings.manifest_fingerprint,
            "run_plan_fingerprint": bindings.run_plan_fingerprint,
            "authorization_fingerprint": bindings.authorization_fingerprint,
            "result": dict(result),
        },
    )
    return result_fp


def commit_successful_reproduction_result(
    root: Path,
    *,
    run_key: str,
    reproduction_attempt: int,
    bindings: CampaignBindings,
    attempt: int,
    envelope: Mapping[str, Any],
    result: Mapping[str, Any],
    exit_code: int = 0,
) -> str:
    """Mark reproduction SUCCEEDED only after result (+ comparison) is durable."""
    result_fp = persist_reproduction_result(
        root,
        run_key=run_key,
        reproduction_attempt=reproduction_attempt,
        bindings=bindings,
        result=result,
    )
    write_reproduction_envelope(
        root,
        run_key=run_key,
        reproduction_attempt=reproduction_attempt,
        bindings=bindings,
        status="SUCCEEDED",
        attempt=attempt,
        envelope=envelope,
        exit_code=exit_code,
        result_fingerprint=result_fp,
    )
    marker = reproduction_completion_marker_path(root, run_key, reproduction_attempt)
    atomic_write_json(
        marker,
        {
            "schema_version": STATE_SCHEMA_VERSION,
            "run_key": run_key,
            "reproduction_attempt": int(reproduction_attempt),
            "status": "SUCCEEDED",
            "result_fingerprint": result_fp,
            "completed_at_utc": _now_utc_iso(),
        },
    )
    return result_fp


def write_comparison_evidence(
    root: Path,
    *,
    run_key: str,
    reproduction_attempt: int,
    comparison: Mapping[str, Any],
) -> Path:
    path = reproduction_comparison_path(root, run_key, reproduction_attempt)
    body = {
        "schema_version": STATE_SCHEMA_VERSION,
        "run_key": run_key,
        "reproduction_attempt": int(reproduction_attempt),
        "recorded_at_utc": _now_utc_iso(),
        "comparison": dict(comparison),
    }
    atomic_write_json(path, body)
    return path


def inspect_reproduction_for_resume(
    root: Path,
    *,
    run_key: str,
    reproduction_attempt: int,
    bindings: CampaignBindings,
    max_attempts: int,
    retry_failed: bool,
) -> str:
    """Return 'skip' | 'retry' | 'start' | raise on partial / running / limits.

    Mirrors :func:`inspect_run_for_resume` for the reproduction attempt namespace
    under ``runs/<run_key>/reproduction/<n>/``.
    """
    path = reproduction_envelope_path(root, run_key, reproduction_attempt)
    if not path.exists():
        return "start"
    existing = read_json(path)
    _assert_same_bindings(existing, bindings)
    status = str(existing.get("status") or "")
    attempt = int(existing.get("attempt") or 0)
    if status == "SUCCEEDED":
        marker = reproduction_completion_marker_path(
            root, run_key, reproduction_attempt
        )
        rpath = reproduction_result_path(root, run_key, reproduction_attempt)
        if not marker.exists() or not rpath.exists():
            raise SensitivityStateError("STATE_REPRO_PARTIAL_SUCCESS_BLOCKED")
        stored_fp = existing.get("result_fingerprint")
        result_body = read_json(rpath)
        if result_body.get("result_fingerprint") != stored_fp:
            raise SensitivityStateError("STATE_REPRO_RESULT_FINGERPRINT_MISMATCH")
        if result_body.get("manifest_fingerprint") != bindings.manifest_fingerprint:
            raise SensitivityStateError("STATE_REPRO_RESULT_MANIFEST_MISMATCH")
        if result_body.get("authorization_fingerprint") != (
            bindings.authorization_fingerprint
        ):
            raise SensitivityStateError("STATE_REPRO_RESULT_AUTH_MISMATCH")
        # Completion is gated on an exact-equality PASS comparison.
        cmp_path = reproduction_comparison_path(root, run_key, reproduction_attempt)
        if not cmp_path.exists():
            raise SensitivityStateError("STATE_REPRO_COMPARISON_MISSING")
        cmp_body = read_json(cmp_path)
        comparison = dict(cmp_body.get("comparison") or {})
        if str(comparison.get("status") or "") != "PASS":
            raise SensitivityStateError(
                f"STATE_REPRO_COMPARISON_NOT_PASS:{comparison.get('status')}"
            )
        return "skip"
    if status == "RUNNING":
        # Crash window: result + PASS comparison persisted, success marker not yet.
        # Resume may finalize without re-executing; bare RUNNING remains blocked.
        rpath = reproduction_result_path(root, run_key, reproduction_attempt)
        cmp_path = reproduction_comparison_path(root, run_key, reproduction_attempt)
        if rpath.exists() and cmp_path.exists():
            result_body = read_json(rpath)
            if result_body.get("manifest_fingerprint") != bindings.manifest_fingerprint:
                raise SensitivityStateError("STATE_REPRO_RESULT_MANIFEST_MISMATCH")
            if result_body.get("authorization_fingerprint") != (
                bindings.authorization_fingerprint
            ):
                raise SensitivityStateError("STATE_REPRO_RESULT_AUTH_MISMATCH")
            cmp_body = read_json(cmp_path)
            comparison = dict(cmp_body.get("comparison") or {})
            if str(comparison.get("status") or "") == "PASS":
                return "finalize"
        raise SensitivityStateError("STATE_REPRO_RUNNING_WITHOUT_COMPLETION")
    if status == "FAILED":
        if not retry_failed:
            raise SensitivityStateError("STATE_REPRO_FAILED_NO_RETRY")
        if attempt >= max_attempts:
            raise SensitivityStateError("STATE_REPRO_RETRY_LIMIT_EXCEEDED")
        return "retry"
    if status in {"BLOCKED", "CANCELLED"}:
        raise SensitivityStateError(f"STATE_REPRO_TERMINAL_{status}")
    if status == "PLANNED":
        return "start"
    raise SensitivityStateError(f"STATE_REPRO_UNKNOWN_STATUS:{status}")


def count_primary_succeeded(
    root: Path,
    *,
    bindings: CampaignBindings,
    expected_run_keys: Sequence[str],
) -> int:
    """Count run_keys with a valid, binding-matched SUCCEEDED primary result.

    Fail-closed on binding drift or partial success (missing marker / result).
    """
    count = 0
    for run_key in expected_run_keys:
        env_path = run_envelope_path(root, run_key)
        if not env_path.exists():
            continue
        existing = read_json(env_path)
        _assert_same_bindings(existing, bindings)
        status = str(existing.get("status") or "")
        if status != "SUCCEEDED":
            continue
        marker = completion_marker_path(root, run_key)
        rpath = result_path(root, run_key)
        if not marker.exists() or not rpath.exists():
            raise SensitivityStateError(f"STATE_PARTIAL_SUCCESS_BLOCKED:{run_key}")
        stored_fp = existing.get("result_fingerprint")
        result_body = read_json(rpath)
        if result_body.get("result_fingerprint") != stored_fp:
            raise SensitivityStateError(f"STATE_RESULT_FINGERPRINT_MISMATCH:{run_key}")
        count += 1
    return count
