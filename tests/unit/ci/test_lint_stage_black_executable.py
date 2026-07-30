"""Contracts for the explicit local Black executable override."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.stages.lint import _black_command

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_black_command_defaults_to_active_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CDB_BLACK_EXECUTABLE", raising=False)
    assert _black_command("python.exe") == ["python.exe", "-m", "black"]


def test_black_command_accepts_existing_explicit_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "black.exe"
    executable.write_bytes(b"test")
    monkeypatch.setenv("CDB_BLACK_EXECUTABLE", str(executable))
    assert _black_command("python.exe") == [str(executable)]


def test_black_command_rejects_missing_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "missing-black.exe"
    monkeypatch.setenv("CDB_BLACK_EXECUTABLE", str(missing))
    with pytest.raises(RuntimeError, match="existing executable"):
        _black_command("python.exe")
