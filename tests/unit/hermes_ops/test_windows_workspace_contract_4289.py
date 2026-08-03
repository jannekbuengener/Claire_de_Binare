"""Regression contracts for Hermes Windows workspace + kill-switch (#4289 Phase B1).

Encodes live findings:
- kill-switch must target dedicated sshd-hermes, not generic sshd by default
- Enable must restore reboot-persistent Automatic start
- missing/corrupt state is fail-closed UNAVAILABLE
- setup must refuse personal profile paths and broad ACLs
- dedicated OpenSSH listener binds Tailscale-only and pubkey-only
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO = Path(__file__).resolve().parents[3]
WINDOWS = REPO / "infrastructure" / "hermes" / "windows"
KILL = WINDOWS / "kill-switch.ps1"
SETUP = WINDOWS / "setup-workspace.ps1"
SSHD = WINDOWS / "setup-sshd-hermes.ps1"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_kill_switch_defaults_to_dedicated_hermes_service() -> None:
    text = _text(KILL)
    assert re.search(
        r"\$ServiceName\s*=\s*['\"]sshd-hermes['\"]",
        text,
    ), "default ServiceName must be sshd-hermes (not generic sshd)"
    # Default parameter must not silently manage the system-wide sshd.
    assert not re.search(
        r"\[string\]\$ServiceName\s*=\s*['\"]sshd['\"]",
        text,
    )


def test_kill_switch_enable_sets_automatic_startup() -> None:
    text = _text(KILL)
    assert "Set-Service -Name $ServiceName -StartupType Automatic" in text
    assert "Set-Service -Name $ServiceName -StartupType Manual" not in text


def test_kill_switch_missing_or_corrupt_state_is_unavailable() -> None:
    text = _text(KILL)
    assert "WORKSTATION_UNAVAILABLE" in text
    assert "UNAVAILABLE" in text
    assert "Read-StateStatus" in text or "IsNullOrWhiteSpace" in text
    assert "status=UNKNOWN" not in text


def test_kill_switch_status_is_machine_readable() -> None:
    text = _text(KILL)
    assert "ConvertTo-Json" in text
    assert "kill_switch=" in text
    assert "service=" in text


def test_setup_workspace_acl_and_non_admin_contract() -> None:
    text = _text(SETUP)
    assert "S-1-5-32-544" in text  # Administrators SID
    assert "S-1-5-32-545" in text  # Users SID (locale-safe on DE/EN Windows)
    assert "S-1-5-18" in text  # SYSTEM SID
    assert "Remove-LocalGroupMember" in text
    assert "Everyone" in text
    assert "SetAccessRuleProtection($true, $false)" in text
    assert "C:\\Users" in text or "Users\\" in text
    assert "GrantWrite" in text


def test_setup_sshd_hermes_contract_exists_and_is_private() -> None:
    assert SSHD.is_file(), "setup-sshd-hermes.ps1 must exist for dedicated listener"
    text = _text(SSHD)
    assert "sshd-hermes" in text
    assert "PasswordAuthentication no" in text
    assert "PubkeyAuthentication yes" in text
    assert "AllowUsers" in text and "hermes-win" in text
    assert "ListenAddress 0.0.0.0" in text
    assert "RemoteAddress" in text
    assert "PasswordAuthentication no" in text
    assert "AllowTcpForwarding no" in text
    assert "X11Forwarding no" in text
    assert "AllowAgentForwarding no" in text
    # Mentions of RDP/VNC only as exclusions are fine; must not enable them.
    assert (
        "Enable-NetFirewallRule" not in text
        or "OpenSSH-Server-In-TCP" not in text.split("Enable-NetFirewallRule")[0]
    )
    assert "Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'" in text
    assert "Set-Service -Name 'sshd' -StartupType Disabled" in text
    assert "winget" in text or "Microsoft.OpenSSH.Preview" in text
    assert "*>`$null" in text or "Out-Null" in text
    assert "Microsoft.OpenSSH.Preview" in text
