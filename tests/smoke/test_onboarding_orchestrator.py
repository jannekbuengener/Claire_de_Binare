from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

ORCHESTRATOR_MODULE = "tools.onboarding_orchestrator"


def _run_orchestrator(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", ORCHESTRATOR_MODULE, *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )


class TestOrchestratorSmoke:
    def test_orchestrator_runs(self):
        result = _run_orchestrator()
        assert result.returncode in (0, 1), (
            f"Orchestrator exited with unexpected code {result.returncode}. "
            f"stderr: {result.stderr}"
        )

    def test_orchestrator_output_contains_onboarding(self):
        result = _run_orchestrator()
        assert (
            "CDB Onboarding" in result.stdout
        ), "Output must contain 'CDB Onboarding' header"

    def test_orchestrator_output_contains_status(self):
        result = _run_orchestrator()
        assert "Status:" in result.stdout, "Output must contain 'Status:' line"

    def test_orchestrator_output_status_is_valid(self):
        result = _run_orchestrator()
        valid_statuses = ("PASS", "SETUP_WARN", "BLOCKED")
        found = any(s in result.stdout for s in valid_statuses)
        assert found, (
            f"Output must contain one of {valid_statuses}. "
            f"Got: {result.stdout[:200]}"
        )

    def test_orchestrator_output_keine_aenderungen(self):
        result = _run_orchestrator()
        assert (
            "Keine Änderungen vorgenommen." in result.stdout
        ), "Output must contain 'Keine Änderungen vorgenommen.'"

    def test_orchestrator_output_lr_no_go(self):
        result = _run_orchestrator()
        assert (
            "LR remains NO-GO" in result.stdout
        ), "Output must contain 'LR remains NO-GO'"

    def test_orchestrator_output_trade_capable(self):
        result = _run_orchestrator()
        assert (
            "trade-capable ist kein Live-Go" in result.stdout
        ), "Output must contain 'trade-capable ist kein Live-Go'"

    def test_orchestrator_output_contains_setup_prompt(self):
        result = _run_orchestrator()
        assert (
            "Möchtest du das Onboarding-Setup jetzt ausführen?" in result.stdout
        ), "Output must contain the setup confirmation prompt"

    def test_orchestrator_output_contains_only_two_setup_options(self):
        result = _run_orchestrator()
        assert "1. Ja" in result.stdout
        assert "2. Abbruch" in result.stdout

    def test_orchestrator_does_not_contain_removed_setup_prompt_variants(self):
        result = _run_orchestrator()
        removed_patterns = [
            "Soll ich jetzt den sicheren Onboarding-Workflow starten? (ja/nein)",
            "Oder möchtest du vorher den Setup-Plan ansehen?",
        ]
        for pattern in removed_patterns:
            assert (
                pattern not in result.stdout
            ), f"Output must not contain removed prompt variant: {pattern}"

    def test_orchestrator_does_not_contain_old_options(self):
        result = _run_orchestrator()
        old_patterns = [
            "1. Setup-Plan anzeigen",
            "2. Setup vorbereiten",
            "3. Onboarding-Report schreiben",
            "4. Ersten sicheren Issue-Workflow simulieren",
        ]
        for pattern in old_patterns:
            assert (
                pattern not in result.stdout
            ), f"Output must not contain old numbered option: {pattern}"

    def test_orchestrator_does_not_contain_naechste_optionen_header(self):
        result = _run_orchestrator()
        assert (
            "Nächste Optionen:" not in result.stdout
        ), "Output must not contain 'Nächste Optionen:' header"

    def test_orchestrator_stderr_empty_or_info(self):
        result = _run_orchestrator()
        stderr = result.stderr.strip()
        if stderr:
            assert (
                "ERROR" not in stderr.upper()
            ), f"stderr must not contain ERROR: {stderr}"

    def test_orchestrator_json_format(self):
        result = _run_orchestrator("--format", "json")
        assert result.returncode == 0 or result.returncode == 1
        data = json.loads(result.stdout)
        assert "status" in data
        assert data["status"] in ("PASS", "SETUP_WARN", "BLOCKED")

    def test_orchestrator_json_status_field(self):
        result = _run_orchestrator("--format", "json")
        data = json.loads(result.stdout)
        assert "status" in data
        assert "bootloader" in data
        assert "scenario" in data
        assert "lr_note" in data

    def test_orchestrator_safe_output(self):
        result = _run_orchestrator()
        secret_patterns = [
            "api_key",
            "api_secret",
            "password",
            "ghp_",
            "gho_",
            "ghu_",
            "ghs_",
        ]
        lower = result.stdout.lower()
        for pattern in secret_patterns:
            if pattern in ("ghp_", "gho_", "ghu_", "ghs_"):
                if pattern in result.stdout:
                    pytest.fail(f"Potential GitHub token leak: {pattern}")
            elif pattern in lower:
                pytest.fail(f"Potential secret pattern: {pattern}")
