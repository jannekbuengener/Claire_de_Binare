"""Regression contracts for Hermes bootstrap durability fixes (#4329).

These encode the host failures proven on cdb-hermes-01 during #4327:
pin stdout pollution, install.sh 0600, /etc/hermes root:root, ProtectHome=true,
missing web_dist/stamp, and missing per-profile managed Node.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tools.hermes_ops.systemd_contract import validate_unit

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO = Path(__file__).resolve().parents[3]
BOOTSTRAP = REPO / "infrastructure" / "hermes" / "hetzner" / "bootstrap.sh"
UNIT = REPO / "infrastructure" / "hermes" / "systemd" / "hermes-dashboard@.service"


def _bootstrap_text() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8")


def _resolve_bash() -> str:
    """Prefer Git Bash on Windows; WSL system32 bash mishandles multiline -c."""
    if sys.platform.startswith("win"):
        for candidate in (
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
        ):
            if candidate.is_file():
                return str(candidate)
    found = shutil.which("bash")
    if not found:
        pytest.skip("bash not available for pin stdout contract proof")
    if sys.platform.startswith("win") and found.lower().endswith(r"system32\bash.exe"):
        pytest.skip("WSL bash unsuitable for multiline -c; use Git Bash")
    return found


def test_log_function_writes_to_stderr_not_stdout() -> None:
    """Status logs must not pollute command substitution for verify_pin."""
    text = _bootstrap_text()
    assert re.search(
        r'^log\(\)\s*\{\s*printf\s+[\'"]\[hermes-bootstrap\][^\'"]*[\'"]\s+"\$\*"\s+>&2',
        text,
        re.MULTILINE,
    ), "log() must write to stderr (>&2) so verify_pin stdout stays machine-only"


def test_verify_pin_command_substitution_is_machine_only() -> None:
    """verify_pin stdout must be machine-only; logs must not enter the capture."""
    text = _bootstrap_text()
    assert 'pin_pair="$(verify_pin)"' in text
    assert re.search(
        r"^log\(\)\s*\{[^}]*printf[^}]*>&2",
        text,
        re.MULTILINE | re.DOTALL,
    )
    # Behavioral proof of the required log/stdout split (same contract as bootstrap).
    script = textwrap.dedent(r"""
        set -euo pipefail
        log() { printf '[hermes-bootstrap] %s\n' "$*" >&2; }
        verify_pin() {
          log "pin ok: ref=v2026.7.30 commit=cc4cab2f592e..."
          printf '%s %s' "v2026.7.30" "cc4cab2f592e60a197e796506de9168f74baf3ea"
        }
        pair="$(verify_pin)"
        printf '%s' "$pair"
        """)
    proc = subprocess.run(
        [_resolve_bash(), "-c", script],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert proc.stdout == "v2026.7.30 cc4cab2f592e60a197e796506de9168f74baf3ea"
    assert "[hermes-bootstrap]" not in proc.stdout
    assert "pin ok:" in proc.stderr
    # Bootstrap verify_pin must end with the machine printf (no trailing log on stdout).
    vp = text.split("verify_pin()")[1].split("\n}\n")[0]
    assert "printf '%s %s'" in vp or 'printf "%s %s"' in vp


def test_installer_temp_chmod_0644_after_hash_before_sudo_u() -> None:
    text = _bootstrap_text()
    assert "chmod 0644" in text
    hash_idx = text.find('die "install.sh sha256 mismatch')
    chmod_idx = text.find("chmod 0644")
    sudo_idx = text.find('sudo -u "${INSTALL_USER}" bash "${tmp}"')
    assert hash_idx != -1 and chmod_idx != -1 and sudo_idx != -1
    assert (
        hash_idx < chmod_idx < sudo_idx
    ), "chmod 0644 must run after hash PASS and before sudo -u INSTALL_USER"


def test_installer_temp_cleanup_trap_present() -> None:
    text = _bootstrap_text()
    assert re.search(r"trap\s+_cleanup_install_tmp\s+EXIT", text)
    assert "_cleanup_install_tmp()" in text
    assert 'rm -f "${tmp}"' in text


def test_etc_hermes_chown_to_install_user_group() -> None:
    text = _bootstrap_text()
    assert 'chown root:"${INSTALL_USER}" /etc/hermes' in text
    assert "chmod 0750 /etc/hermes" in text
    assert "chmod 0777 /etc/hermes" not in text
    assert "chmod 0775 /etc/hermes" not in text


def test_systemd_protect_home_is_read_only_not_true() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert not any(
        line.strip().startswith("ProtectHome=true") for line in text.splitlines()
    ), "ProtectHome=true blocks uv CPython under /home/hermes/.local (#4329)"
    assert "ProtectHome=read-only" in text
    assert "NoNewPrivileges=true" in text
    assert "ProtectSystem=strict" in text
    assert "--host 127.0.0.1" in text
    assert "ReadOnlyPaths=" in text
    assert "/home/hermes/.local/share/uv" in text
    assert "/opt/hermes" in text
    assert "ReadWritePaths=/var/lib/hermes/profiles/%i" in text
    errors = validate_unit(UNIT)
    assert errors == [], errors


def test_bootstrap_wires_web_ui_and_managed_node_for_active_profiles() -> None:
    text = _bootstrap_text()
    assert "ensure_dashboard_runtime_assets" in text
    assert "web_dist" in text
    assert "web-ui-build-stamp.json" in text
    assert "_installer_home/node" in text or "${INSTALLER_HOME}/node" in text
    assert "nodejs.org/dist/latest" not in text
    main = text.split("main()")[-1]
    assert "ensure_dashboard_runtime_assets" in main
    assert main.find("ensure_dashboard_runtime_assets") < main.find("enable_services")


def test_bootstrap_does_not_enable_validation_chief() -> None:
    text = _bootstrap_text()
    assert "systemctl enable hermes-dashboard@validation-chief" not in text
    assert "systemctl start hermes-dashboard@validation-chief" not in text
    assert "validation-chief/.DISABLED" in text
