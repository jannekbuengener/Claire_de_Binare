"""Fail-closed resolver for #4421 replay/ARVP bulk payloads.

Versioned ``artifacts/<root>`` files remain inside the checkout.  Consumers
that explicitly opt into bulk payload resolution use this module instead of a
junction, so that a local E: target can never become an implicit fallback.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import Mapping

from tools.storage.bulk_storage_contract import (
    BulkStorageContractError,
    resolve_bulk_storage_path,
)


CONFLICTING_CANON_ROOTS = frozenset(
    {
        "backtests",
        "batch_compare",
        "calibration",
        "candles",
        "context_tool_inventory",
        "controlled_lab_evidence",
        "drift_classification",
        "evidence_harvester",
        "execution_realism",
        "mcp",
        "paper_reference_windows",
        "recheck_2980",
        "regime_scorecards",
        "replay_reports",
        "signal_reproduction",
        "skills",
        "surrealdb",
    }
)

# These are the only non-HOLD junctions observed in the pre-cutover topology
# that do not collide with tracked canonical repository content.  Keeping this
# inventory in version control makes a clean checkout reproducible without
# treating a junction farm as an unreviewable machine-local side effect.
JUNCTION_CUTOVER_ROOTS = (
    "arvp",
    "arvp_loops",
    "arvp_replay_paper_pilot",
    "arvp_vacation",
    "audit-3304",
    "calibration_run_001",
    "campaigns",
    "context-intelligence",
    "datasets",
    "evidence",
    "evidence_scenario_runs",
    "local-branch-cleanup",
    "local-control-followup",
    "local-dev-hygiene",
    "local-hygiene",
    "local-wrapper",
    "loop-check",
    "price_policy_evaluation_3079",
    "redis_aof_recovery_20260529_004112",
    "redis_rebuild_3594_20260701_023436",
    "replay_smoke",
    "replay_vs_paper_compare",
    "shadow_interim",
    "soak_ABORTED_20260322_120002",
    "soak_ABORTED_20260322_181245_premature",
    "soak_test_20260310_172922",
    "soak_test_20260311_000002_FAILED_legacy_migration",
    "soak_test_20260311_124500",
    "soak_test_20260312_000001",
    "soak_test_20260313_110003",
    "soak_test_20260314_100003",
    "soak_test_20260315_110003",
    "soak_test_20260316_110003",
    "soak_test_20260317_000002",
    "soak_test_20260318_090002",
    "soak_test_20260319_000002",
    "soak_test_20260320_110005",
    "soak_test_20260321_120003",
    "soak_test_20260322_181856",
    "soak_test_20260323_000002",
    "soak_test_20260324_000002",
    "soak_test_20260324_224419",
    "soak_test_20260325_114548",
    "soak_test_20260325_121250",
    "soak_test_20260401_114850",
    "soak_validation_20260325_110047",
    "telemetry_sidecar",
    "tmp",
    "validation_1277_20260325_095757",
)

POSTGRES_HOLD_ROOTS = frozenset(
    {"postgres_restore_3600_work", "postgres_rebuild_3600_20260701_024237"}
)


class ReplayArvpStorageError(ValueError):
    """Raised when a replay/ARVP bulk payload cannot be resolved safely."""


def _parts(relative_path: str | Path) -> tuple[str, ...]:
    raw = str(relative_path).replace("\\", "/")
    candidate = PurePosixPath(raw)
    parts = candidate.parts
    if (
        not raw
        or candidate.is_absolute()
        or len(parts) < 2
        or parts[0] != "artifacts"
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ReplayArvpStorageError("REPLAY_ARVP_PAYLOAD_PATH_INVALID")
    return parts


def resolve_replay_arvp_payload_path(
    relative_path: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve a declared conflicting artifact payload below canonical Y: storage.

    This is opt-in: missing configuration is an error and no repository-local
    or E:-drive fallback is permitted.
    """
    parts = _parts(relative_path)
    if parts[1] not in CONFLICTING_CANON_ROOTS:
        raise ReplayArvpStorageError("REPLAY_ARVP_CANON_ROOT_UNMANAGED")
    try:
        bulk_root = resolve_bulk_storage_path("replay-arvp", environ=environ)
    except BulkStorageContractError as exc:
        raise ReplayArvpStorageError(str(exc)) from exc
    return bulk_root.joinpath(*parts[1:])


def resolve_replay_arvp_consumer_path(
    repo_root: Path,
    relative_path: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return repo canon by default, or configured bulk payload when opted in.

    This preserves checked-in evidence for normal repository reads.  An explicit
    ``CDB_BULK_STORAGE_ROOT`` changes only declared conflicting roots and never
    selects E: as a fallback.
    """
    env = os.environ if environ is None else environ
    parts = _parts(relative_path)
    if parts[1] not in CONFLICTING_CANON_ROOTS:
        raise ReplayArvpStorageError("REPLAY_ARVP_CANON_ROOT_UNMANAGED")
    if not env.get("CDB_BULK_STORAGE_ROOT", "").strip():
        return repo_root.joinpath(*parts)
    return resolve_replay_arvp_payload_path(relative_path, environ=env)


def _is_junction(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def apply_replay_arvp_junction_cutover(
    repo_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """Create only the 49 declared safe junctions; never overwrite canon/HOLD.

    The caller must explicitly opt in through the #4419 bulk-root contract.
    Existing non-junction paths are a hard error, making a collision impossible
    to hide behind a successful partial cutover.
    """
    target_root = resolve_bulk_storage_path("replay-arvp", environ=environ)
    artifact_root = repo_root / "artifacts"
    created: list[Path] = []
    for name in JUNCTION_CUTOVER_ROOTS:
        destination = artifact_root / name
        target = target_root / name
        if not target.is_dir():
            raise ReplayArvpStorageError("REPLAY_ARVP_JUNCTION_TARGET_MISSING")
        if destination.exists() or destination.is_symlink():
            if not _is_junction(destination):
                raise ReplayArvpStorageError("REPLAY_ARVP_JUNCTION_COLLISION")
            continue
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(destination), str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
        created.append(destination)
    return tuple(created)
