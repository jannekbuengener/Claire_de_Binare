from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.market_data.historical_common import HistoricalProbeError
from tools.market_data.market_data_storage_guard import (
    DefaultVolumeProbe,
    StorageGuardResult,
    VolumeInfo,
    enforce_market_data_storage,
    validate_market_data_storage,
)


@dataclass
class FakeVolumeProbe:
    repo_volume: VolumeInfo
    target_volume: VolumeInfo
    reparse_paths: frozenset[str] = frozenset()

    def resolve_path(self, path: Path) -> Path:
        return path.resolve()

    def volume_for_path(self, path: Path) -> VolumeInfo:
        resolved = path.resolve()
        if "artifacts" in resolved.parts and "market_data" in resolved.parts:
            return self.target_volume
        return self.repo_volume


def _vol(
    *,
    letter: str = "D",
    label: str = "DevDrive",
    drive_type: str = "Fixed",
    free_bytes: int = 100_000_000_000,
    unique_id: str = "serial:DEADBEEF",
) -> VolumeInfo:
    return VolumeInfo(
        drive_letter=letter,
        unique_id=unique_id,
        file_system_label=label,
        drive_type=drive_type,
        free_bytes=free_bytes,
        total_bytes=free_bytes * 2,
    )


@pytest.mark.unit
def test_storage_guard_same_devdrive_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(repo_volume=_vol(), target_volume=_vol())
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=1_000_000_000,
        volume_probe=probe,
    )
    assert result.allowed is True
    assert result.reason_code == "PASS"


@pytest.mark.unit
def test_storage_guard_external_fixed_drive_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(
        repo_volume=_vol(letter="D", unique_id="serial:AAA"),
        target_volume=_vol(letter="E", unique_id="serial:BBB", label="Backup II"),
    )
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=1_000_000_000,
        volume_probe=probe,
    )
    assert result.allowed is False
    assert result.reason_code == "DIFFERENT_VOLUME"


@pytest.mark.unit
def test_storage_guard_blocked_drive_letter_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(repo_volume=_vol(), target_volume=_vol(letter="E"))
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=1_000,
        volume_probe=probe,
    )
    assert result.allowed is False
    assert result.reason_code in {"DIFFERENT_VOLUME", "BLOCKED_DRIVE"}


@pytest.mark.unit
def test_storage_guard_removable_drive_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(
        repo_volume=_vol(),
        target_volume=_vol(drive_type="Removable"),
    )
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=1_000,
        volume_probe=probe,
    )
    assert result.allowed is False
    assert result.reason_code == "UNSUPPORTED_DRIVE_TYPE"


@pytest.mark.unit
def test_storage_guard_network_drive_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(
        repo_volume=_vol(),
        target_volume=_vol(drive_type="Remote"),
    )
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=1_000,
        volume_probe=probe,
    )
    assert result.allowed is False
    assert result.reason_code == "UNSUPPORTED_DRIVE_TYPE"


@pytest.mark.unit
def test_storage_guard_unknown_volume_id_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(
        repo_volume=_vol(unique_id=None),
        target_volume=_vol(unique_id="serial:OTHER", letter="C"),
    )
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=1_000,
        volume_probe=probe,
    )
    assert result.allowed is False
    assert result.reason_code == "UNKNOWN_VOLUME_ID"


@pytest.mark.unit
def test_storage_guard_insufficient_space_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(
        repo_volume=_vol(free_bytes=1_000),
        target_volume=_vol(free_bytes=1_000),
    )
    result = validate_market_data_storage(
        repo_root=repo,
        required_write_bytes=10_000_000_000,
        volume_probe=probe,
    )
    assert result.allowed is False
    assert result.reason_code == "INSUFFICIENT_SPACE"


@pytest.mark.unit
def test_storage_guard_enforce_raises(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "artifacts" / "market_data").mkdir(parents=True)
    probe = FakeVolumeProbe(
        repo_volume=_vol(),
        target_volume=_vol(letter="E", unique_id="serial:EEE"),
    )
    with pytest.raises(HistoricalProbeError, match="STORAGE_GUARD_BLOCKED"):
        enforce_market_data_storage(
            repo_root=repo,
            required_write_bytes=1_000,
            volume_probe=probe,
        )


@pytest.mark.unit
def test_default_volume_probe_is_constructible() -> None:
    assert DefaultVolumeProbe() is not None
