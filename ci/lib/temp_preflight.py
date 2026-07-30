"""Run-scoped temp-root preflight for local CI (Issue #4205).

Probes create/read/rename/delete under an *outside-repo* CI temp root before
pytest collection. Never touches foreign temp trees, global ACLs, or
``.wslconfig``. Roots live under ``C:\\tmp\\cdb-ci\\<run_id>`` (Windows) or
``$TEMP/cdb-ci/<run_id>`` so pytest basetemp files are not mistaken for
repo-relative paths by scanners.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
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
    return f"<ci-temp>/cdb-ci/{run_id}"


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


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def candidate_temp_roots(
    *,
    run_id: str,
    repo_root: Path,
    preferred_root: Path | None = None,
) -> list[Path]:
    """Ordered outside-repo candidates for a run-scoped CI temp root."""
    ordered: list[Path] = []
    if preferred_root is not None:
        ordered.append(Path(preferred_root))
    if os.name == "nt":
        ordered.append(Path(r"C:\tmp\cdb-ci") / run_id)
    ordered.append(Path(tempfile.gettempdir()) / "cdb-ci" / run_id)

    seen: set[Path] = set()
    out: list[Path] = []
    repo = repo_root.resolve()
    for raw in ordered:
        candidate = raw.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if _is_under(candidate, repo):
            continue
        out.append(candidate)
    return out


def _probe_root(temp_root: Path) -> str:
    """Return TEMP_ROOT_OK or a failure reason code after probing temp_root."""
    probe_dir = temp_root / _PROBE_DIR_NAME
    if probe_dir.exists():
        try:
            shutil.rmtree(probe_dir)
        except OSError:
            pass

    try:
        temp_root.mkdir(parents=True, exist_ok=True)
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_file = probe_dir / "probe.txt"
        probe_file.write_text(_PROBE_MARKER, encoding="utf-8")
    except OSError:
        return TEMP_ROOT_CREATE_FAILED

    try:
        data = probe_file.read_text(encoding="utf-8")
        if data != _PROBE_MARKER:
            return TEMP_ROOT_READ_FAILED
    except OSError:
        return TEMP_ROOT_READ_FAILED

    renamed = probe_dir / "probe_renamed.txt"
    try:
        probe_file.rename(renamed)
    except OSError:
        return TEMP_ROOT_RENAME_FAILED

    try:
        renamed.unlink()
    except OSError:
        return TEMP_ROOT_DELETE_FAILED

    basetemp = temp_root / _BASETEMP_NAME
    cache_dir = temp_root / _CACHE_NAME
    try:
        basetemp.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        marker = cache_dir / ".writable"
        marker.write_text("ok\n", encoding="utf-8")
        marker.unlink()
    except OSError:
        return TEMP_ROOT_NOT_WRITABLE

    try:
        if probe_dir.exists():
            remaining = list(probe_dir.iterdir())
            if not remaining:
                probe_dir.rmdir()
            else:
                shutil.rmtree(probe_dir)
    except OSError:
        pass

    return TEMP_ROOT_OK


def prepare_ci_temp_root(
    run_dir: Path,
    run_id: str,
    *,
    repo_root: Path | None = None,
    preferred_root: Path | None = None,
) -> TempRootResult:
    """Probe an outside-repo CI temp root; fail fast with a stable reason code.

    ``run_dir`` remains the evidence directory (reports stay under artifacts).
    ``preferred_root`` is for tests; production tries ``C:\\tmp\\cdb-ci`` then
    ``$TEMP/cdb-ci``.
    """
    if repo_root is not None:
        repo = repo_root.resolve()
    elif run_dir.parent.name == "artifacts" and run_dir.parent.parent.name == "ci":
        repo = run_dir.parents[2].resolve()
    else:
        repo = Path.cwd().resolve()

    redacted = redacted_temp_root(run_id)
    candidates = candidate_temp_roots(
        run_id=run_id, repo_root=repo, preferred_root=preferred_root
    )
    if not candidates:
        empty = (run_dir / "tmp-unavailable").resolve()
        return TempRootResult(
            ok=False,
            reason_code=TEMP_ROOT_CREATE_FAILED,
            temp_root=empty,
            basetemp=empty / _BASETEMP_NAME,
            cache_dir=empty / _CACHE_NAME,
            redacted_root=redacted,
        )

    last_reason = TEMP_ROOT_CREATE_FAILED
    last_root = candidates[0]
    for temp_root in candidates:
        last_root = temp_root
        reason = _probe_root(temp_root)
        if reason == TEMP_ROOT_OK:
            return TempRootResult(
                ok=True,
                reason_code=TEMP_ROOT_OK,
                temp_root=temp_root,
                basetemp=temp_root / _BASETEMP_NAME,
                cache_dir=temp_root / _CACHE_NAME,
                redacted_root=redacted,
            )
        last_reason = reason

    return TempRootResult(
        ok=False,
        reason_code=last_reason,
        temp_root=last_root,
        basetemp=last_root / _BASETEMP_NAME,
        cache_dir=last_root / _CACHE_NAME,
        redacted_root=redacted,
    )


def temp_preflight_as_dict(result: TempRootResult) -> dict[str, object]:
    """Serialize result with pathlib paths as posix strings (tests/helpers)."""
    data = asdict(result)
    data["temp_root"] = result.temp_root.as_posix()
    data["basetemp"] = result.basetemp.as_posix()
    data["cache_dir"] = result.cache_dir.as_posix()
    return data
