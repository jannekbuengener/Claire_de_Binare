"""Run-scoped temp-root preflight for local CI (Issue #4205).

Probes create/read/rename/delete under ``run_dir/tmp`` before pytest collection.
Never touches foreign temp trees, global ACLs, or ``.wslconfig``.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

TEMP_ROOT_CREATE_FAILED = "TEMP_ROOT_CREATE_FAILED"
TEMP_ROOT_READ_FAILED = "TEMP_ROOT_READ_FAILED"
TEMP_ROOT_RENAME_FAILED = "TEMP_ROOT_RENAME_FAILED"
TEMP_ROOT_DELETE_FAILED = "TEMP_ROOT_DELETE_FAILED"
TEMP_ROOT_NOT_WRITABLE = "TEMP_ROOT_NOT_WRITABLE"
TEMP_ROOT_OK = "TEMP_ROOT_OK"

_PROBE_MARKER = "cdb-temp-preflight\n"
_BASETEMP_NAME = "pytest-basetemp"
_CACHE_NAME = "pytest-cache"
_PROBE_DIR_NAME = "_probe"


@dataclass(frozen=True)
class TempRootResult:
    ok: bool
    reason_code: str
    temp_root: Path
    basetemp: Path
    cache_dir: Path
    redacted_root: str


def redacted_temp_root(run_id: str) -> str:
    """Stable evidence path without user-home absolute segments."""
    return f"ci/artifacts/{run_id}/tmp"


def temp_env_for(temp_root: Path) -> dict[str, str]:
    root = str(temp_root)
    return {"TEMP": root, "TMP": root, "TMPDIR": root}


def write_temp_preflight_report(path: Path, result: TempRootResult) -> None:
    """Write redacted preflight evidence (no absolute home paths)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": result.ok,
        "reason_code": result.reason_code,
        "redacted_root": result.redacted_root,
        "basetemp_rel": f"{result.redacted_root}/{_BASETEMP_NAME}",
        "cache_dir_rel": f"{result.redacted_root}/{_CACHE_NAME}",
    }
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def prepare_ci_temp_root(run_dir: Path, run_id: str) -> TempRootResult:
    """Create and probe ``run_dir/tmp``; fail fast with a stable reason code."""
    temp_root = (run_dir / "tmp").resolve()
    basetemp = temp_root / _BASETEMP_NAME
    cache_dir = temp_root / _CACHE_NAME
    redacted = redacted_temp_root(run_id)

    def _result(*, ok: bool, reason_code: str) -> TempRootResult:
        return TempRootResult(
            ok=ok,
            reason_code=reason_code,
            temp_root=temp_root,
            basetemp=basetemp,
            cache_dir=cache_dir,
            redacted_root=redacted,
        )

    probe_dir = temp_root / _PROBE_DIR_NAME
    if probe_dir.exists():
        try:
            shutil.rmtree(probe_dir)
        except OSError:
            # Stale leftovers under our probe dir only; continue into create probe.
            pass

    try:
        temp_root.mkdir(parents=True, exist_ok=True)
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file = probe_dir / "probe.txt"
        probe_file.write_text(_PROBE_MARKER, encoding="utf-8")
    except OSError:
        return _result(ok=False, reason_code=TEMP_ROOT_CREATE_FAILED)

    try:
        data = probe_file.read_text(encoding="utf-8")
        if data != _PROBE_MARKER:
            return _result(ok=False, reason_code=TEMP_ROOT_READ_FAILED)
    except OSError:
        return _result(ok=False, reason_code=TEMP_ROOT_READ_FAILED)

    renamed = probe_dir / "probe_renamed.txt"
    try:
        probe_file.rename(renamed)
    except OSError:
        return _result(ok=False, reason_code=TEMP_ROOT_RENAME_FAILED)

    try:
        renamed.unlink()
    except OSError:
        return _result(ok=False, reason_code=TEMP_ROOT_DELETE_FAILED)

    try:
        basetemp.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        marker = cache_dir / ".writable"
        marker.write_text("ok\n", encoding="utf-8")
        marker.unlink()
    except OSError:
        return _result(ok=False, reason_code=TEMP_ROOT_NOT_WRITABLE)

    try:
        if probe_dir.exists():
            # Remove only our empty probe subdirectory (no foreign temps).
            remaining = list(probe_dir.iterdir())
            if not remaining:
                probe_dir.rmdir()
            else:
                shutil.rmtree(probe_dir)
    except OSError:
        pass

    return _result(ok=True, reason_code=TEMP_ROOT_OK)


def temp_preflight_as_dict(result: TempRootResult) -> dict[str, object]:
    """Serialize result with pathlib paths as posix strings (tests/helpers)."""
    data = asdict(result)
    data["temp_root"] = result.temp_root.as_posix()
    data["basetemp"] = result.basetemp.as_posix()
    data["cache_dir"] = result.cache_dir.as_posix()
    return data
