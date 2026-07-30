"""Governance stage BP API offline fallback for thin ci.yml (#4163)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.stages import governance as gov

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_probe_branch_protection_api_false_on_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProc:
        returncode = 1
        stderr = "gh: Resource not accessible by integration (HTTP 403)"
        stdout = ""

    monkeypatch.setattr(gov.subprocess, "run", lambda *a, **k: FakeProc())
    assert gov.probe_branch_protection_api("example/owner-repo", "main") is False


def test_probe_branch_protection_api_true_on_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProc:
        returncode = 0
        stderr = ""
        stdout = "{}"

    monkeypatch.setattr(gov.subprocess, "run", lambda *a, **k: FakeProc())
    assert gov.probe_branch_protection_api("example/owner-repo", "main") is True


def test_drift_command_uses_offline_baseline_when_api_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    reports = tmp_path / "reports"
    reports.mkdir()
    baseline = (
        repo / "docs" / "evidence" / "reports" / "BRANCH_PROTECTION_BASELINE_main.json"
    )
    baseline.parent.mkdir(parents=True)
    baseline.write_text('{"required_status_checks":{"contexts":["cdb-local-ci"]}}\n')

    monkeypatch.setattr(gov, "probe_branch_protection_api", lambda *a, **k: False)
    cmd = gov.build_drift_checks_command(
        python_exe="python",
        repo_root=repo,
        reports_dir=reports,
    )
    assert cmd[0] == "python"
    assert cmd[1] == "scripts/governance/run_ci_drift_checks.py"
    assert "--branch-protection-current-json" in cmd
    offline = Path(cmd[cmd.index("--branch-protection-current-json") + 1])
    assert offline.exists()
    assert offline.read_text(encoding="utf-8") == baseline.read_text(encoding="utf-8")
    disclosure = reports / "branch-protection-live-unavailable.json"
    assert disclosure.exists()
    text = disclosure.read_text(encoding="utf-8")
    assert "live_unavailable" in text
    assert "cdb-local-ci" in text or "offline" in text


def test_drift_command_live_when_api_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gov, "probe_branch_protection_api", lambda *a, **k: True)
    cmd = gov.build_drift_checks_command(
        python_exe="python",
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports",
    )
    assert "--branch-protection-current-json" not in cmd
