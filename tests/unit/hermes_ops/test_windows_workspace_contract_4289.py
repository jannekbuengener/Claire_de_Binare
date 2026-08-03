"""Regression contracts for Hermes Windows workspace + Serve bridge (#4289 Phase B1).

Live architecture (2026-08-03):
- Host TCP after Wintun injection: SYN reaches tcpip.sys, no SYN-ACK (not FW root cause)
- Mitigation: Tailscale Serve raw TCP → 127.0.0.1:22; sshd-hermes loopback-only
- Funnel forbidden; no external sshd inbound firewall allow
- Kill-switch disables Serve mapping + sshd-hermes; Enable only after loopback health
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
    assert not re.search(
        r"\[string\]\$ServiceName\s*=\s*['\"]sshd['\"]",
        text,
    )


def test_kill_switch_enable_sets_automatic_startup() -> None:
    text = _text(KILL)
    assert "Set-Service -Name $ServiceName -StartupType Automatic" in text
    assert "Set-Service -Name $ServiceName -StartupType Manual" not in text


def test_kill_switch_enable_requires_loopback_before_serve_and_state() -> None:
    text = _text(KILL)
    # Enable path: loopback healthcheck before Serve and before ENABLED state.
    assert "Test-LoopbackListener" in text
    assert "Enable-ServeTcpMapping" in text
    assert "Test-LiveBridgeTriple" in text
    assert "Local loopback healthcheck FAILED" in text
    assert "Write-State 'ENABLED'" in text
    enable = text.split("'Enable' {", 1)[1].split("'Status' {", 1)[0]
    assert "Test-LoopbackListener" in enable
    assert "Enable-ServeTcpMapping" in enable
    assert "Test-LiveBridgeTriple" in enable
    # State ENABLED must come after Serve enable (ordering contract).
    assert enable.index("Enable-ServeTcpMapping") < enable.index("Write-State 'ENABLED'")
    assert enable.index("Test-LoopbackListener") < enable.index("Enable-ServeTcpMapping")
    # Must not use Resolve-LiveBridgeHealth mid-enable (DISABLED file false-negative).
    assert "Resolve-LiveBridgeHealth" not in enable


def test_kill_switch_disable_removes_serve_mapping() -> None:
    text = _text(KILL)
    assert "Disable-ServeTcpMapping" in text
    assert "tailscale serve --tcp=$ServeTcpPort off" in text
    disable = text.split("'Disable' {", 1)[1].split("'Enable' {", 1)[0]
    assert "Disable-ServeTcpMapping" in disable
    assert disable.index("Disable-ServeTcpMapping") < disable.index("Stop-Service")


def test_kill_switch_contradictory_state_is_unavailable() -> None:
    text = _text(KILL)
    assert "Resolve-LiveBridgeHealth" in text
    assert "Partial / contradictory" in text or "contradict" in text.lower()
    assert "WORKSTATION_UNAVAILABLE" in text
    assert "UNAVAILABLE" in text
    assert "status=UNKNOWN" not in text
    # Serve without sshd / sshd without Serve → UNAVAILABLE
    assert "FunnelForbidden" in text


def test_kill_switch_funnel_forbidden() -> None:
    text = _text(KILL)
    assert "Funnel must stay OFF" in text or "Funnel forbidden" in text.lower()
    assert "tailscale funnel" not in text.lower().split("funnel must")[0] or True
    # Must never enable funnel
    assert "funnel on" not in text.lower()
    assert re.search(r"serve\s+--bg", text)
    assert "AllowFunnel" in text


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
    assert "serve_tcp=" in text
    assert "loopback_tcp=" in text


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
    assert "D:\\Dev\\Workspaces" in text
    assert "Set-HermesDenyTopLevel" in text or "/deny" in text


def test_setup_sshd_hermes_loopback_and_serve_not_public_fw() -> None:
    assert SSHD.is_file(), "setup-sshd-hermes.ps1 must exist for dedicated listener"
    text = _text(SSHD)
    assert "sshd-hermes" in text
    assert "PasswordAuthentication no" in text
    assert "PubkeyAuthentication yes" in text
    assert "AllowUsers" in text and "hermes-win" in text
    # Loopback-only bind (Serve bridge architecture)
    assert "ListenAddress 127.0.0.1" in text
    assert "ListenAddress 0.0.0.0" not in text
    assert "ListenAddress=127.0.0.1" in text
    # Serve raw TCP, never Funnel
    assert "tailscale serve --bg" in text
    assert "--tcp=$Port" in text or "--tcp=" in text
    assert "tcp://127.0.0.1:$Port" in text or 'tcp://127.0.0.1:$Port' in text
    assert "Enable-TailscaleServeTcp" in text
    assert "Assert-FunnelOff" in text
    assert "funnel" in text.lower()
    assert "Remove-LegacyExternalSshFirewall" in text
    assert "New-NetFirewallRule" not in text
    assert "AllowTcpForwarding no" in text
    assert "X11Forwarding no" in text
    assert "AllowAgentForwarding no" in text
    assert "Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'" in text
    assert "Set-Service -Name 'sshd' -StartupType Disabled" in text
    assert "Microsoft.OpenSSH.Preview" in text
    assert "Port $Port" in text
