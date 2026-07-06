"""Stack lifecycle script fail-closed contract tests (#3857).

Static PowerShell source inspection — no Docker, no container mutation, no rollbacks.
Refs #3855, #1445, #2985.
"""

from __future__ import annotations

import re

import pytest

from tests.unit.infra._compose_stack_contract_helpers import (
    find_legacy_compose_references,
    read_script_text,
    script_has_operator_gate,
    script_mutating_paths_gated,
    script_secret_echo_violations,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

LIFECYCLE_SCRIPTS: dict[str, str] = {
    "stack_up": "infrastructure/scripts/stack_up.ps1",
    "stack_verify": "infrastructure/scripts/stack_verify.ps1",
    "stack_clean": "infrastructure/scripts/stack_clean.ps1",
    "stack_rollback": "infrastructure/scripts/stack_rollback.ps1",
    "setup_blue_red": "infrastructure/scripts/setup_blue_red.ps1",
    "cdb_stack_doctor": "tools/cdb-stack-doctor.ps1",
}


@pytest.mark.parametrize("name,path", list(LIFECYCLE_SCRIPTS.items()))
def test_lifecycle_script_exists(name: str, path: str) -> None:
    text = read_script_text(path)
    assert text.strip(), f"{name} must not be empty"


def test_setup_blue_red_uses_canonical_compose_files() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["setup_blue_red"])
    assert "compose.blue.yml" in text
    assert "compose.red.yml" in text
    assert "base.yml" not in text or "LEGACY" in text.upper()


def test_cdb_stack_doctor_uses_canonical_compose_files() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["cdb_stack_doctor"])
    assert "compose.blue.yml" in text
    assert "compose.red.yml" in text


def test_stack_up_legacy_topology_findings_are_visible() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_up"])
    findings = find_legacy_compose_references(text, "stack_up.ps1")
    patterns = {f.pattern for f in findings}
    assert "base.yml" in patterns
    assert "dev.yml" in patterns


def test_stack_rollback_legacy_topology_findings_are_visible() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_rollback"])
    findings = find_legacy_compose_references(text, "stack_rollback.ps1")
    patterns = {f.pattern for f in findings}
    assert "base.yml" in patterns


def test_stack_clean_has_deep_clean_and_force_operator_flags() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_clean"])
    assert re.search(r"\[switch\]\$DeepClean", text)
    assert re.search(r"\[switch\]\$Force", text)
    assert "Read-Host" in text
    assert "GO DEEP CLEAN" in text


def test_stack_rollback_has_force_operator_gate() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_rollback"])
    assert re.search(r"\[switch\]\$Force", text)
    assert "Read-Host" in text


def test_setup_blue_red_has_skip_flags_for_partial_dry_paths() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["setup_blue_red"])
    assert re.search(r"\[switch\]\$SkipRed", text)
    assert re.search(r"\[switch\]\$SkipSmokeTest", text)


def test_mutating_scripts_require_operator_gate_or_force_bypass() -> None:
    mutating = ("stack_clean", "stack_rollback")
    for name in mutating:
        text = read_script_text(LIFECYCLE_SCRIPTS[name])
        assert script_has_operator_gate(text), (
            f"{name} mutates Docker state and must expose Read-Host or -Force gate"
        )


def test_stack_up_fails_closed_on_missing_secrets_directory() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_up"])
    assert "FATAL: Secrets directory not found" in text
    assert "exit 1" in text
    assert "FATAL: Missing required secrets" in text


def test_setup_blue_red_fails_closed_on_missing_secrets_path() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["setup_blue_red"])
    assert "Write-Error" in text
    assert "Secrets directory not found" in text


def test_cdb_stack_doctor_fails_closed_on_missing_compose_or_docker() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["cdb_stack_doctor"])
    assert "exit 1" in text
    assert "Docker Desktop is not accessible" in text
    assert "Configuration issues detected" in text


def test_lifecycle_scripts_do_not_echo_secret_values() -> None:
    for name, path in LIFECYCLE_SCRIPTS.items():
        violations = script_secret_echo_violations(read_script_text(path))
        assert not violations, f"{name} secret echo risk patterns: {violations}"


def test_stack_up_load_secrets_only_prints_secret_names_not_values() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_up"])
    assert 'Write-Host "  [OK] $secret"' in text
    assert "Write-Host $value" not in text


def test_runtime_env_loader_reports_length_not_secret_payload() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_up"])
    assert "length: $($value.Length)" in text
    assert "Write-Host $value" not in text


@pytest.mark.parametrize("name,path", list(LIFECYCLE_SCRIPTS.items()))
def test_scripts_do_not_implement_dry_run_switch(name: str, path: str) -> None:
    """Document posture: lifecycle scripts are operator tools, not dry-run CLIs."""
    text = read_script_text(path)
    assert "DryRun" not in text and "-WhatIf" not in text, (
        f"{name}: if dry-run is added, extend contract tests explicitly"
    )


def test_stack_verify_is_read_only_docker_inspection() -> None:
    text = read_script_text(LIFECYCLE_SCRIPTS["stack_verify"])
    assert "docker ps" in text
    assert "docker inspect" in text
    assert "docker compose up" not in text
    assert "docker rm" not in text
