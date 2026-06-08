"""Tests for create_basic_plugin.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_help_exits_zero() -> None:
    """Script --help should exit 0."""
    script = (
        Path(__file__).resolve().parents[2]
        / ".codex"
        / "cdb_skills"
        / ".system"
        / "plugin-creator"
        / "scripts"
        / "create_basic_plugin.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_marketplace_variable_initialized(tmp_path: Path) -> None:
    """Script with --with-marketplace must not raise UnboundLocalError."""
    script = (
        Path(__file__).resolve().parents[2]
        / ".codex"
        / "cdb_skills"
        / ".system"
        / "plugin-creator"
        / "scripts"
        / "create_basic_plugin.py"
    )
    plugin_dir = tmp_path / "my_plugin"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "test-plugin",
            "--path",
            str(tmp_path),
            "--with-marketplace",
            "--marketplace-path",
            str(tmp_path / "marketplace.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "Created plugin scaffold" in result.stdout


def test_no_marketplace_no_crash(tmp_path: Path) -> None:
    """Script without --with-marketplace must not crash."""
    script = (
        Path(__file__).resolve().parents[2]
        / ".codex"
        / "cdb_skills"
        / ".system"
        / "plugin-creator"
        / "scripts"
        / "create_basic_plugin.py"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "bare-plugin",
            "--path",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "Created plugin scaffold" in result.stdout
