"""Timeout and FAIL-reason contracts for portable Black in the lint stage."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from ci.lib.process import EXIT_CODE_TIMEOUT, CommandResult, run_command
from ci.stages._common import StageContext
from ci.stages.lint import (
    BLACK_EXECUTABLE_INVALID,
    BLACK_NONZERO_EXIT,
    BLACK_TIMEOUT,
    run as lint_run,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _ctx(tmp_path: Path, *, resources: dict | None = None) -> StageContext:
    run_dir = tmp_path / "run"
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "reports").mkdir(parents=True)
    return StageContext(
        repo_root=tmp_path,
        run_dir=run_dir,
        run_id="run_black_timeout_test",
        git=MagicMock(),
        profile="fast",
        resources=resources or {"black_timeout_seconds": 120},
    )


def _ok_result(command: list[str]) -> CommandResult:
    return CommandResult(
        command=command,
        exit_code=0,
        duration_seconds=0.01,
        stdout="",
        stderr="",
        timed_out=False,
    )


def test_run_command_timeout_returns_exit_124_not_raise(
    tmp_path: Path,
) -> None:
    """Hung process → TimeoutExpired caught → exit 124 + COMMAND_TIMEOUT."""
    log_path = tmp_path / "hang.log"
    # Cross-platform sleep via the active interpreter (no shell).
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        log_path=log_path,
        timeout=1,
    )
    assert result.timed_out is True
    assert result.exit_code == EXIT_CODE_TIMEOUT
    text = log_path.read_text(encoding="utf-8")
    assert "reason_code=COMMAND_TIMEOUT" in text
    assert f"exit_code={EXIT_CODE_TIMEOUT}" in text
    # No credential-shaped leakage from the timeout path.
    assert "token" not in text.lower()
    assert "password" not in text.lower()
    assert "secret" not in text.lower()


def test_lint_black_timeout_fails_with_black_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path, resources={"black_timeout_seconds": 1})
    monkeypatch.delenv("CDB_BLACK_EXECUTABLE", raising=False)
    monkeypatch.setattr(
        "ci.stages.lint._changed_python_files",
        lambda _root: ["services/example.py"],
    )

    calls: list[dict[str, Any]] = []

    def fake_run_command(
        command: list[str],
        *,
        cwd: Path,
        log_path: Path,
        env: Any = None,
        timeout: int | None = None,
    ) -> CommandResult:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(command)}\n", encoding="utf-8")
        calls.append({"command": list(command), "timeout": timeout})
        if "-m" in command and "ruff" in command:
            return _ok_result(list(command))
        # Simulate Black hang → timeout contract from process layer.
        log_path.write_text(
            f"$ {' '.join(command)}\n\nreason_code=COMMAND_TIMEOUT\n"
            f"exit_code={EXIT_CODE_TIMEOUT}\n",
            encoding="utf-8",
        )
        return CommandResult(
            command=list(command),
            exit_code=EXIT_CODE_TIMEOUT,
            duration_seconds=1.0,
            stdout="",
            stderr="",
            timed_out=True,
        )

    monkeypatch.setattr("ci.stages.lint.run_command", fake_run_command)
    result = lint_run(ctx)

    assert result.status == "FAIL"
    assert result.exit_code == EXIT_CODE_TIMEOUT
    assert result.skip_reason is None
    assert f"reason_code={BLACK_TIMEOUT}" in result.command_summary
    # Timeout applied only to Black, not ruff.
    assert calls[0]["timeout"] is None
    assert calls[1]["timeout"] == 1
    assert "black" in " ".join(calls[1]["command"]).lower() or any(
        part.endswith("black") or part.endswith("black.exe")
        for part in calls[1]["command"]
    )


def test_lint_black_nonzero_exit_fails_with_reason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path)
    monkeypatch.delenv("CDB_BLACK_EXECUTABLE", raising=False)
    monkeypatch.setattr(
        "ci.stages.lint._changed_python_files",
        lambda _root: ["services/example.py"],
    )

    def fake_run_command(
        command: list[str],
        *,
        cwd: Path,
        log_path: Path,
        env: Any = None,
        timeout: int | None = None,
    ) -> CommandResult:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(command)}\nexit_code=1\n", encoding="utf-8")
        if "-m" in command and "ruff" in command:
            return _ok_result(list(command))
        return CommandResult(
            command=list(command),
            exit_code=1,
            duration_seconds=0.1,
            stdout="",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr("ci.stages.lint.run_command", fake_run_command)
    result = lint_run(ctx)
    assert result.status == "FAIL"
    assert result.exit_code == 1
    assert result.skip_reason is None
    assert f"reason_code={BLACK_NONZERO_EXIT}" in result.command_summary


def test_lint_invalid_executable_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ctx = _ctx(tmp_path)
    monkeypatch.setenv("CDB_BLACK_EXECUTABLE", str(tmp_path / "missing-black.exe"))
    monkeypatch.setattr(
        "ci.stages.lint._changed_python_files",
        lambda _root: ["services/example.py"],
    )

    def fake_run_command(
        command: list[str],
        *,
        cwd: Path,
        log_path: Path,
        env: Any = None,
        timeout: int | None = None,
    ) -> CommandResult:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(command)}\n", encoding="utf-8")
        return _ok_result(list(command))

    monkeypatch.setattr("ci.stages.lint.run_command", fake_run_command)
    result = lint_run(ctx)
    assert result.status == "FAIL"
    assert result.skip_reason is None
    assert f"reason_code={BLACK_EXECUTABLE_INVALID}" in result.command_summary
    # Error text must not leak env secrets / tokens.
    joined = " ".join(result.command_summary) + "\n".join(
        p.read_text(encoding="utf-8") for p in (ctx.logs_dir).glob("*.log")
    )
    assert "GITHUB_TOKEN" not in joined
    assert "password=" not in joined.lower()


def test_lint_identical_changed_set_uses_same_command_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same changed-file set → same argv shape (portable default: python -m black)."""
    ctx = _ctx(tmp_path)
    files = ["core/a.py", "services/b.py"]
    monkeypatch.delenv("CDB_BLACK_EXECUTABLE", raising=False)
    monkeypatch.setattr(
        "ci.stages.lint._changed_python_files",
        lambda _root: list(files),
    )
    captured: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        cwd: Path,
        log_path: Path,
        env: Any = None,
        timeout: int | None = None,
    ) -> CommandResult:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(command)}\n", encoding="utf-8")
        captured.append(list(command))
        return _ok_result(list(command))

    monkeypatch.setattr("ci.stages.lint.run_command", fake_run_command)
    result = lint_run(ctx)
    assert result.status == "PASS"
    black_cmd = captured[1]
    assert black_cmd[1:3] == ["-m", "black"]
    assert "--config" in black_cmd
    assert "pyproject.toml" in black_cmd
    assert "--check" in black_cmd
    assert "--workers" in black_cmd
    assert "1" in black_cmd
    assert black_cmd[-2:] == files
