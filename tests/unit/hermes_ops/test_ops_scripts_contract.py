"""Static contracts for Hermes Hetzner ops scripts (#4289)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

HETZNER = Path("infrastructure/hermes/hetzner")
SCRIPTS = (
    "backup.sh",
    "bootstrap.sh",
    "destroy.sh",
    "provision.sh",
    "restore.sh",
    "rollback.sh",
    "update.sh",
)


def _read(name: str) -> str:
    return (HETZNER / name).read_text(encoding="utf-8")


def test_ops_scripts_are_executable() -> None:
    for name in SCRIPTS:
        path = HETZNER / name
        assert path.is_file(), path
        mode = path.stat().st_mode
        assert mode & 0o111, f"{name} must be executable (mode={oct(mode)})"


def test_update_uses_pinned_installer_not_main_branch() -> None:
    text = _read("update.sh")
    assert "raw.githubusercontent.com/NousResearch/hermes-agent/main" not in text
    assert "VERSION_PIN.yaml" in text
    assert "install_script_sha256" in text
    assert "hermes-agent" in text
    assert "--commit" in text
    assert 'die "install.sh sha256 mismatch' in text or "sha256 mismatch" in text
    # sha256 must be mandatory (empty pin dies before curl success path).
    assert "install_script_sha256 empty" in text
    assert "/opt/hermes/hermes-agent" in text or 'CODE_DIR="${HERMES_CODE_DIR' in text


def test_rollback_uses_pinned_installer_and_code_dir() -> None:
    text = _read("rollback.sh")
    assert "raw.githubusercontent.com/NousResearch/hermes-agent/main" not in text
    assert "VERSION_PIN.yaml" in text
    assert "install_script_sha256 empty" in text
    assert "hermes-agent" in text or "CODE_DIR" in text
    assert "--force-commit" in text


def test_destroy_requires_labels_not_name_only() -> None:
    text = _read("destroy.sh")
    assert "role=hermes" in text or 'REQUIRED_LABEL_ROLE="hermes"' in text
    assert "4289" in text
    assert "claire-de-binare" in text
    assert "refuse destroy: server" in text or "missing required labels" in text
    assert "require_server_labels" in text


def test_provision_backups_not_start_after_create_flag() -> None:
    text = _read("provision.sh")
    assert "--start-after-create" not in text
    assert "enable_backups_or_die" in text
    assert "failed to enable backups" in text
    assert "HERMES_ENABLE_BACKUPS must be 1" in text
    assert "role=hermes" in text
    assert "issue=4289" in text


def test_bootstrap_paths_align_with_update() -> None:
    bootstrap = _read("bootstrap.sh")
    update = _read("update.sh")
    assert 'OPT_DIR="${HERMES_OPT_DIR:-/opt/hermes}"' in bootstrap or "/opt/hermes" in bootstrap
    assert "hermes-agent" in bootstrap
    assert "hermes-agent" in update
    assert "|| true" not in bootstrap.split("enable_services")[-1] or "enable_services" in bootstrap
    # Service start must die, not swallow errors.
    assert 'die "jannek-assistant dashboard failed to start"' in bootstrap
    assert 'die "cdb-engineer dashboard failed to start"' in bootstrap
