"""Execution-surface capability probe for #4153 (read-only, stdout-only)."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.sensitivity_campaign_dataset_root import (
    DatasetRootIdentity,
    SensitivityDatasetRootError,
    resolve_and_verify_dataset_root,
)

SURFACE_CONTRACT_VERSION = "cdb.sensitivity_campaign_execution_surface.v1"


class SensitivitySurfaceError(ValueError):
    """Fail-closed surface / capability probe error."""


@dataclass(frozen=True, slots=True)
class SurfaceProbeResult:
    surface: dict[str, Any]
    surface_capability_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "surface": dict(self.surface),
            "surface_capability_fingerprint": self.surface_capability_fingerprint,
        }


def _disk_free_bytes(path: Path) -> int:
    usage = shutil.disk_usage(str(path))
    return int(usage.free)


def _coerce_dataset_identity(
    value: DatasetRootIdentity | Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, DatasetRootIdentity):
        return value.as_dict()
    if isinstance(value, Mapping):
        return dict(value)
    raise SensitivitySurfaceError(
        "SURFACE_DATASET_IDENTITY_INVALID: expected DatasetRootIdentity or mapping"
    )


def probe_execution_surface(
    *,
    repo_root: Path,
    dataset_root: Path | None,
    surface_id: str,
    surface_kind: str = "local_owner_workstation",
    network_mode: str = "offline_replay_only",
    exchange_credentials_present: bool = False,
    window_availability: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    dataset_identity: DatasetRootIdentity | Mapping[str, Any] | None = None,
) -> SurfaceProbeResult:
    """Read-only capability probe. Must not create files or mutate state.

    When ``dataset_root`` is provided together with ``manifest`` the resolver
    verifies every window binding under the canonical window-bank layout and
    the resulting :class:`DatasetRootIdentity` is bound into the fingerprint.

    A caller may pass a precomputed ``dataset_identity`` (e.g. from a prior
    resolver call) to avoid double-resolving; in that case ``manifest`` is
    optional. When only ``dataset_root`` is supplied without a manifest we
    fall back to the lightweight path identity (path name + existence) — this
    path is only used by ``plan`` / ``probe-surface``. The execute path must
    always pass ``manifest`` so the full binding is fingerprinted.
    """
    if network_mode != "offline_replay_only":
        raise SensitivitySurfaceError(
            f"network_mode must be offline_replay_only, got {network_mode!r}"
        )
    if exchange_credentials_present:
        raise SensitivitySurfaceError(
            "exchange credentials must be absent/unused for sensitivity campaign"
        )

    cpu_count = os.cpu_count() or 1
    ram_bytes: int | None
    try:
        import psutil  # type: ignore

        ram_bytes = int(psutil.virtual_memory().total)
    except Exception:
        ram_bytes = None

    free_bytes = _disk_free_bytes(repo_root if repo_root.exists() else Path.cwd())

    identity_body: dict[str, Any] | None = None
    if dataset_root is not None:
        precomputed = _coerce_dataset_identity(dataset_identity)
        if precomputed is not None:
            identity_body = precomputed
        elif manifest is not None:
            try:
                resolved = resolve_and_verify_dataset_root(
                    dataset_root=dataset_root,
                    manifest=manifest,
                    repo_root=repo_root,
                )
            except SensitivityDatasetRootError as exc:
                raise SensitivitySurfaceError(
                    f"SURFACE_DATASET_ROOT_{exc.reason_code}: {exc}"
                ) from exc
            identity_body = resolved.as_dict()
        else:
            identity_body = {
                "path_exists": dataset_root.exists(),
                "path_name": dataset_root.name,
            }

    windows = dict(window_availability or {})
    surface = {
        "schema_version": SURFACE_CONTRACT_VERSION,
        "surface_kind": surface_kind,
        "surface_id": surface_id,
        "os": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "repository_sha_binding_required": True,
        "dataset_root_identity": identity_body,
        "window_availability": windows,
        "cpu_count": cpu_count,
        "ram_bytes": ram_bytes,
        "free_artifact_bytes": free_bytes,
        "network_mode": network_mode,
        "exchange_credentials": {
            "required": False,
            "present": False,
            "used": False,
        },
        "sys_platform": sys.platform,
    }
    # Fingerprint excludes volatile free_artifact_bytes so probe identity is
    # stable across free-space jitter; free space is still reported and checked.
    fingerprint_body = {
        k: v for k, v in surface.items() if k not in {"free_artifact_bytes"}
    }
    fp = canonical_hash(fingerprint_body)
    return SurfaceProbeResult(surface=surface, surface_capability_fingerprint=fp)


def assert_surface_matches_authorization(
    *,
    probe: SurfaceProbeResult,
    expected_surface_id: str,
    expected_capability_fingerprint: str,
) -> None:
    if probe.surface.get("surface_id") != expected_surface_id:
        raise SensitivitySurfaceError(
            f"SURFACE_ID_MISMATCH: {probe.surface.get('surface_id')!r} != "
            f"{expected_surface_id!r}"
        )
    if probe.surface_capability_fingerprint != expected_capability_fingerprint:
        raise SensitivitySurfaceError("SURFACE_CAPABILITY_FINGERPRINT_MISMATCH")
