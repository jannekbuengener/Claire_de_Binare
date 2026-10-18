"""Governance stage ruleset API fallback for Sample-Brain-style main protection."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.stages import governance as gov

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_probe_main_ruleset_api_false_on_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProc:
        returncode = 1
        stderr = "gh: Resource not accessible by integration (HTTP 403)"
        stdout = ""

    monkeypatch.setattr(gov.subprocess, "run", lambda *a, **k: FakeProc())
    assert gov.probe_main_ruleset_api("example/owner-repo") is False


def test_probe_main_ruleset_api_true_on_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeProc:
        returncode = 0
        stderr = ""
        stdout = '{"name":"main-strict","bypass_actors":[]}'

    monkeypatch.setattr(gov.subprocess, "run", lambda *a, **k: FakeProc())
    assert gov.probe_main_ruleset_api("example/owner-repo") is True


def test_probe_main_ruleset_api_false_when_bypass_actors_are_permission_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProc:
        returncode = 0
        stderr = ""
        stdout = '{"name":"main-strict"}'

    monkeypatch.setattr(gov.subprocess, "run", lambda *a, **k: FakeProc())
    assert gov.probe_main_ruleset_api("example/owner-repo") is False


def test_drift_command_uses_offline_ruleset_baseline_when_api_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    reports = tmp_path / "reports"
    reports.mkdir()
    baseline = (
        repo / "docs" / "evidence" / "reports" / "BRANCH_PROTECTION_BASELINE_main.json"
    )
    baseline.parent.mkdir(parents=True)
    baseline.write_text(
        '{"id":11617228,"name":"main-strict","enforcement":"active"}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(gov, "probe_main_ruleset_api", lambda *a, **k: False)
    cmd = gov.build_drift_checks_command(
        python_exe="python", repo_root=repo, reports_dir=reports
    )
    assert cmd[:2] == ["python", "scripts/governance/run_ci_drift_checks.py"]
    assert "--branch-protection-current-json" in cmd
    offline = Path(cmd[cmd.index("--branch-protection-current-json") + 1])
    assert offline.exists()
    assert offline.read_text(encoding="utf-8") == baseline.read_text(encoding="utf-8")
    disclosure = reports / "branch-protection-live-unavailable.json"
    text = disclosure.read_text(encoding="utf-8")
    assert "ruleset" in text.lower()
    assert "main-strict" in text


def test_drift_command_live_when_ruleset_api_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gov, "probe_main_ruleset_api", lambda *a, **k: True)
    cmd = gov.build_drift_checks_command(
        python_exe="python", repo_root=tmp_path, reports_dir=tmp_path / "reports"
    )
    assert "--branch-protection-current-json" not in cmd
