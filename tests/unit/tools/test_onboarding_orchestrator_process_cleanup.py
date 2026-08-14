from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from tools import onboarding_orchestrator


@pytest.mark.unit
def test_run_cmd_timeout_terminates_windows_process_tree_and_drains_pipes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A timeout must close the child tree before captured pipes are drained."""
    process = MagicMock()
    process.pid = 4242
    # `communicate()` can time out on a descendant-held pipe after the direct
    # child already exited. The timeout cleanup must still run in that case.
    process.poll.return_value = 0
    process.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd=["child"], timeout=0.2),
        ("", ""),
    ]
    taskkill = MagicMock()
    monkeypatch.setattr(onboarding_orchestrator.os, "name", "nt")
    monkeypatch.setattr(
        onboarding_orchestrator.subprocess, "Popen", MagicMock(return_value=process)
    )
    monkeypatch.setattr(onboarding_orchestrator.subprocess, "run", taskkill)

    rc, stdout, stderr = onboarding_orchestrator._run_cmd(["child"], timeout=0.2)

    assert (rc, stdout) == (-1, "")
    assert "timed out after 0.2s" in stderr
    taskkill.assert_called_once_with(
        ["taskkill", "/PID", "4242", "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert process.communicate.call_args_list[1].kwargs == {"timeout": 5}
