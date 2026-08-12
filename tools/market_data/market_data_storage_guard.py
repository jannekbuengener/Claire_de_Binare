"""Fail-closed storage guard for historical market_data imports (#4004)."""

from __future__ import annotations

import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from tools.market_data.historical_common import HistoricalProbeError
from tools.storage.bulk_storage_contract import (
    BULK_STORAGE_ROOT_ENV,
    BulkStorageContractError,
    resolve_bulk_storage_path,
)

CANONICAL_RELATIVE = Path("artifacts") / "market_data"
RESERVE_MULTIPLIER = 1.25
BLOCKED_DRIVE_LETTERS = frozenset({"E"})


class VolumeProbeError(HistoricalProbeError):
    """Volume or path resolution could not be completed."""


@dataclass(frozen=True, slots=True)
class VolumeInfo:
    drive_letter: str
    unique_id: str | None
    file_system_label: str | None
    drive_type: str
    free_bytes: int | None
    total_bytes: int | None


class VolumeProbe(Protocol):
    def resolve_path(self, path: Path) -> Path: ...

    def volume_for_path(self, path: Path) -> VolumeInfo: ...


@dataclass(frozen=True, slots=True)
class StorageGuardResult:
    allowed: bool
    reason_code: str
    message: str
    details: dict[str, Any]


def _normalize_drive(letter: str) -> str:
    value = letter.strip().rstrip(":").upper()
    if len(value) != 1 or not value.isalpha():
        raise VolumeProbeError(f"Invalid drive letter: {letter!r}")
    return value


def canonical_market_data_path(repo_root: Path) -> Path:
    return (repo_root / CANONICAL_RELATIVE).resolve()


def resolve_market_data_path(
    repo_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the historical corpus root without an implicit external fallback."""
    env = os.environ if environ is None else environ
    if not env.get(BULK_STORAGE_ROOT_ENV, "").strip():
        return canonical_market_data_path(repo_root)
    return resolve_bulk_storage_path("market-history", environ=env).resolve()


def _is_reparse_point(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def _reparse_in_parent_chain(path: Path) -> list[str]:
    hits: list[str] = []
    current = path
    while True:
        if _is_reparse_point(current):
            hits.append(str(current))
        parent = current.parent
        if parent == current:
            break
        current = parent
    return hits


class DefaultVolumeProbe:
    """Windows-oriented probe with pathlib fallbacks for tests."""

    def resolve_path(self, path: Path) -> Path:
        return path.resolve()

    def volume_for_path(self, path: Path) -> VolumeInfo:
        resolved = self.resolve_path(path)
        drive = resolved.drive
        if not drive:
            raise VolumeProbeError(f"No drive letter for path: {path}")
        letter = _normalize_drive(drive)
        unique_id: str | None = None
        label: str | None = None
        drive_type = "Unknown"
        free_bytes: int | None = None
        total_bytes: int | None = None
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            vol_name = ctypes.create_unicode_buffer(261)
            fs_name = ctypes.create_unicode_buffer(261)
            serial = ctypes.c_uint32()
            max_comp = ctypes.c_uint32()
            flags = ctypes.c_uint32()
            root = f"{letter}:\\"
            if kernel32.GetVolumeInformationW(
                root,
                vol_name,
                ctypes.sizeof(vol_name),
                ctypes.byref(serial),
                ctypes.byref(max_comp),
                ctypes.byref(flags),
                fs_name,
                ctypes.sizeof(fs_name),
            ):
                label = vol_name.value or None
                unique_id = f"serial:{serial.value:08X}"
        except (AttributeError, OSError):
            unique_id = None
        drive_type_map = {
            "DRIVE_UNKNOWN": "Unknown",
            "DRIVE_NO_ROOT_DIR": "NoRoot",
            "DRIVE_REMOVABLE": "Removable",
            "DRIVE_FIXED": "Fixed",
            "DRIVE_REMOTE": "Remote",
            "DRIVE_CDROM": "CDROM",
            "DRIVE_RAMDISK": "RamDisk",
        }
        try:
            import ctypes

            dt = ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\")  # type: ignore[attr-defined]
            drive_type = drive_type_map.get(str(dt), f"Code{dt}")
        except (AttributeError, OSError):
            drive_type = "Unknown"
        try:
            usage = os.statvfs(resolved) if hasattr(os, "statvfs") else None
            if usage is not None:
                free_bytes = usage.f_bavail * usage.f_frsize
                total_bytes = usage.f_blocks * usage.f_frsize
        except OSError:
            free_bytes = None
            total_bytes = None
        if free_bytes is None:
            try:
                import shutil

                usage = shutil.disk_usage(resolved)
                free_bytes = usage.free
                total_bytes = usage.total
            except OSError as exc:
                raise VolumeProbeError(f"disk_usage failed for {resolved}") from exc
        return VolumeInfo(
            drive_letter=letter,
            unique_id=unique_id,
            file_system_label=label,
            drive_type=drive_type,
            free_bytes=free_bytes,
            total_bytes=total_bytes,
        )


def validate_market_data_storage(
    *,
    repo_root: Path,
    target_path: Path | None = None,
    required_write_bytes: int,
    expected_repo_volume_label: str | None = "DevDrive",
    volume_probe: VolumeProbe | None = None,
    environ: Mapping[str, str] | None = None,
) -> StorageGuardResult:
    """Fail-closed guard before historical import writes."""
    probe_impl = volume_probe or DefaultVolumeProbe()
    details: dict[str, Any] = {}
    try:
        repo_resolved = probe_impl.resolve_path(repo_root)
        repo_canonical = canonical_market_data_path(repo_root)
        canonical = resolve_market_data_path(repo_root, environ=environ)
        bulk_mode = canonical != repo_canonical
        target = probe_impl.resolve_path(target_path or canonical)
        details["repo_root"] = str(repo_resolved)
        details["target_path"] = str(target)
        details["canonical_path"] = str(canonical)
        details["storage_mode"] = "bulk" if bulk_mode else "repo"

        if target != canonical:
            return StorageGuardResult(
                allowed=False,
                reason_code="NON_CANONICAL_TARGET",
                message="target must match the configured canonical market-data root",
                details=details,
            )

        if not bulk_mode:
            try:
                target.relative_to(repo_resolved)
            except ValueError:
                return StorageGuardResult(
                    allowed=False,
                    reason_code="TARGET_OUTSIDE_REPO",
                    message="market_data target must live under repository root",
                    details=details,
                )

        reparse_hits = _reparse_in_parent_chain(target)
        details["reparse_points"] = reparse_hits
        if reparse_hits:
            return StorageGuardResult(
                allowed=False,
                reason_code="REPARSE_IN_PATH",
                message="reparse point in path chain to market_data target",
                details=details,
            )

        repo_vol = probe_impl.volume_for_path(repo_resolved)
        target_vol = probe_impl.volume_for_path(target)
        details["repo_volume"] = asdict(repo_vol)
        details["target_volume"] = asdict(target_vol)

        if not bulk_mode:
            if repo_vol.unique_id is None or target_vol.unique_id is None:
                if repo_vol.drive_letter != target_vol.drive_letter:
                    return StorageGuardResult(
                        allowed=False,
                        reason_code="UNKNOWN_VOLUME_ID",
                        message="cannot prove same volume without resolvable volume identity",
                        details=details,
                    )
            elif repo_vol.unique_id != target_vol.unique_id:
                return StorageGuardResult(
                    allowed=False,
                    reason_code="DIFFERENT_VOLUME",
                    message="repository and target are on different volumes",
                    details=details,
                )

        if target_vol.drive_letter in BLOCKED_DRIVE_LETTERS:
            return StorageGuardResult(
                allowed=False,
                reason_code="BLOCKED_DRIVE",
                message=f"target resolves to blocked drive {target_vol.drive_letter}:",
                details=details,
            )

        if target_vol.drive_type in {"Removable", "Remote", "CDROM"}:
            return StorageGuardResult(
                allowed=False,
                reason_code="UNSUPPORTED_DRIVE_TYPE",
                message=f"unsupported drive type: {target_vol.drive_type}",
                details=details,
            )

        if not bulk_mode and expected_repo_volume_label and repo_vol.file_system_label:
            if repo_vol.file_system_label != expected_repo_volume_label:
                return StorageGuardResult(
                    allowed=False,
                    reason_code="UNEXPECTED_REPO_VOLUME_LABEL",
                    message=(
                        f"expected repo volume label {expected_repo_volume_label!r}, "
                        f"got {repo_vol.file_system_label!r}"
                    ),
                    details=details,
                )

        required = int(required_write_bytes * RESERVE_MULTIPLIER)
        details["required_bytes_with_reserve"] = required
        if target_vol.free_bytes is None:
            return StorageGuardResult(
                allowed=False,
                reason_code="UNKNOWN_FREE_SPACE",
                message="free space could not be determined",
                details=details,
            )
        if target_vol.free_bytes < required:
            return StorageGuardResult(
                allowed=False,
                reason_code="INSUFFICIENT_SPACE",
                message="insufficient free space for reserved write requirement",
                details=details,
            )

        return StorageGuardResult(
            allowed=True,
            reason_code="PASS",
            message="storage guard passed",
            details=details,
        )
    except BulkStorageContractError as exc:
        return StorageGuardResult(
            allowed=False,
            reason_code="BULK_STORAGE_CONTRACT_BLOCKED",
            message=str(exc),
            details=details,
        )
    except VolumeProbeError as exc:
        return StorageGuardResult(
            allowed=False,
            reason_code="VOLUME_PROBE_FAILED",
            message=str(exc),
            details=details,
        )


def enforce_market_data_storage(
    *,
    repo_root: Path,
    required_write_bytes: int,
    target_path: Path | None = None,
    volume_probe: VolumeProbe | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    result = validate_market_data_storage(
        repo_root=repo_root,
        target_path=target_path,
        required_write_bytes=required_write_bytes,
        volume_probe=volume_probe,
        environ=environ,
    )
    if not result.allowed:
        raise HistoricalProbeError(
            f"STORAGE_GUARD_BLOCKED [{result.reason_code}]: {result.message}"
        )
