"""Unit tests for local CI temp-root preflight (#4205)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ci.lib.temp_preflight import (
    TEMP_ROOT_CREATE_FAILED,
    TEMP_ROOT_DELETE_FAILED,
    TEMP_ROOT_NOT_WRITABLE,
    TEMP_ROOT_OK,
    TEMP_ROOT_READ_FAILED,
    TEMP_ROOT_RENAME_FAILED,
    prepare_ci_temp_root,
    redacted_temp_root,
    write_temp_preflight_report,
)

pytestmark = pytest.mark.unit


def test_prepare_ok_creates_controlled_layout(tmp_path: Path) -> None:
    run_id = "run_ok_00001"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is True
    assert result.reason_code == TEMP_ROOT_OK
    assert result.temp_root == (run_dir / "tmp").resolve()
    assert result.basetemp == result.temp_root / "pytest-basetemp"
    assert result.cache_dir == result.temp_root / "pytest-cache"
    assert result.basetemp.is_dir()
    assert result.cache_dir.is_dir()
    assert result.redacted_root == f"ci/artifacts/{run_id}/tmp"
    assert not (result.temp_root / "_probe").exists()


def test_create_failed_reason_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_create_fail"
    run_dir = tmp_path / run_id
    run_dir.mkdir()

    def boom_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        raise OSError("simulated create denial")

    monkeypatch.setattr(Path, "mkdir", boom_mkdir)
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is False
    assert result.reason_code == TEMP_ROOT_CREATE_FAILED


def test_read_failed_reason_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_read_fail"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    real_read = Path.read_text

    def boom_read(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "probe.txt":
            raise OSError("simulated read denial")
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", boom_read)
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is False
    assert result.reason_code == TEMP_ROOT_READ_FAILED


def test_rename_failed_reason_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_rename_fail"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    real_rename = Path.rename

    def boom_rename(self: Path, target: Path) -> Path:
        if self.name == "probe.txt":
            raise OSError("simulated rename denial")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", boom_rename)
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is False
    assert result.reason_code == TEMP_ROOT_RENAME_FAILED


def test_delete_failed_reason_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_delete_fail"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    real_unlink = Path.unlink

    def boom_unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self.name == "probe_renamed.txt":
            raise OSError("simulated delete denial")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", boom_unlink)
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is False
    assert result.reason_code == TEMP_ROOT_DELETE_FAILED


def test_stale_probe_rest_cleaned(tmp_path: Path) -> None:
    run_id = "run_stale_001"
    run_dir = tmp_path / run_id
    probe = run_dir / "tmp" / "_probe"
    probe.mkdir(parents=True)
    leftover = probe / "stale.bin"
    leftover.write_bytes(b"leftover")
    foreign = run_dir / "tmp" / "keep_me.txt"
    foreign.write_text("foreign-not-probe\n", encoding="utf-8")

    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is True
    assert result.reason_code == TEMP_ROOT_OK
    assert not leftover.exists()
    assert not probe.exists()
    assert foreign.exists()


def test_parallel_run_ids_use_distinct_roots(tmp_path: Path) -> None:
    run_a = tmp_path / "run_par_a"
    run_b = tmp_path / "run_par_b"
    run_a.mkdir()
    run_b.mkdir()
    a = prepare_ci_temp_root(run_a, "run_par_a")
    b = prepare_ci_temp_root(run_b, "run_par_b")
    assert a.ok and b.ok
    assert a.temp_root != b.temp_root
    assert a.redacted_root != b.redacted_root
    assert a.temp_root.parent.name == "run_par_a"
    assert b.temp_root.parent.name == "run_par_b"


def test_non_writable_cache_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = "run_nowrite_01"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    real_write = Path.write_text

    def selective_write(self: Path, *args: object, **kwargs: object) -> int:
        if self.name == ".writable":
            raise OSError("simulated cache not writable")
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", selective_write)
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is False
    assert result.reason_code == TEMP_ROOT_NOT_WRITABLE


def test_redacted_manifest_has_no_home_path(tmp_path: Path) -> None:
    run_id = "run_redact_01"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    result = prepare_ci_temp_root(run_dir, run_id)
    report = tmp_path / "temp_preflight.json"
    write_temp_preflight_report(report, result)
    text = report.read_text(encoding="utf-8")
    payload = json.loads(text)
    home = str(Path.home())
    assert home not in text
    assert "Users" not in payload["redacted_root"]
    assert "AppData" not in text
    assert payload["redacted_root"] == redacted_temp_root(run_id)
    assert payload["redacted_root"].startswith("ci/artifacts/")
    assert payload["reason_code"] == TEMP_ROOT_OK


def test_windows_path_normalization_uses_pathlib(tmp_path: Path) -> None:
    run_id = "run_winpath_1"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    result = prepare_ci_temp_root(run_dir, run_id)
    assert result.ok is True
    assert isinstance(result.temp_root, Path)
    assert result.temp_root.is_absolute()
    # pathlib normalize: same as resolve under run_dir/tmp
    assert result.temp_root == Path(os.path.normpath(result.temp_root))
    assert result.temp_root.name == "tmp"
